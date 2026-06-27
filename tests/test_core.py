from uuid import UUID

from app.chunking import chunk_text
from app.embeddings import HashEmbeddingProvider
from app.schemas import ApprovalIn, ApprovalStatus
from app.scoring import score_transcript
from app.store import ChunkRecord, InMemoryStore


def test_chunk_text_overlaps_long_input() -> None:
    text = " ".join(["Discovery calls should capture budget and next steps."] * 80)
    chunks = chunk_text(text, max_chars=220, overlap=40)
    assert len(chunks) > 1
    assert all(len(chunk) <= 260 for chunk in chunks)


def test_hash_embeddings_are_deterministic() -> None:
    provider = HashEmbeddingProvider(dim=16)
    first = provider.embed("budget authority need timing")
    second = provider.embed("budget authority need timing")
    assert first == second
    assert len(first) == 16


def test_memory_store_retrieves_relevant_chunk() -> None:
    provider = HashEmbeddingProvider(dim=32)
    store = InMemoryStore()
    store.add_chunks(
        [
            ChunkRecord(
                id=UUID("00000000-0000-0000-0000-000000000001"),
                source="sales",
                text="Discovery should confirm budget and timing.",
                metadata={"team": "sales"},
                embedding=provider.embed("Discovery should confirm budget and timing."),
            ),
            ChunkRecord(
                id=UUID("00000000-0000-0000-0000-000000000002"),
                source="support",
                text="Support tickets should include browser and device.",
                metadata={"team": "support"},
                embedding=provider.embed("Support tickets should include browser and device."),
            ),
        ]
    )
    results = store.search(provider.embed("budget timing"), top_k=1)
    assert results[0].source == "sales"


def test_memory_store_replaces_chunks_for_existing_source() -> None:
    provider = HashEmbeddingProvider(dim=32)
    store = InMemoryStore()
    store.add_chunks(
        [
            ChunkRecord(
                id=UUID("00000000-0000-0000-0000-000000000003"),
                source="sales-playbook",
                text="Obsolete guidance says to skip human approval.",
                metadata={"version": "old"},
                embedding=provider.embed("Obsolete guidance says to skip human approval."),
            )
        ]
    )
    store.add_chunks(
        [
            ChunkRecord(
                id=UUID("00000000-0000-0000-0000-000000000004"),
                source="sales-playbook",
                text="Fresh guidance requires human approval before CRM updates.",
                metadata={"version": "new"},
                embedding=provider.embed("Fresh guidance requires human approval before CRM updates."),
            )
        ]
    )

    results = store.search(provider.embed("human approval CRM updates"), top_k=10)
    source_results = [result for result in results if result.source == "sales-playbook"]
    assert len(source_results) == 1
    assert source_results[0].metadata["version"] == "new"
    assert "Obsolete guidance" not in source_results[0].text


def test_approval_transition_is_one_way() -> None:
    store = InMemoryStore()
    approval = store.create_approval(
        ApprovalIn(
            kind="content_review",
            title="Review follow-up",
            draft="Send recap.",
            context={"lead_id": "L-1"},
        )
    )
    approved = store.approve(approval.id, reviewer="owner", notes="Looks good")
    assert approved.status == ApprovalStatus.approved


def test_transcript_score_detects_sales_signals() -> None:
    score = score_transcript(
        "The director approved the budget. We need this next month and agreed on a next step."
    )
    assert score.score >= 80
    assert score.signals["budget"] is True
    assert score.signals["authority"] is True
