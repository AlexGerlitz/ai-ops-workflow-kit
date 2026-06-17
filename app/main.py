from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException

from app.chunking import chunk_text
from app.embeddings import HashEmbeddingProvider
from app.llm import LLMClient
from app.schemas import (
    ApprovalDecision,
    ApprovalIn,
    ApprovalOut,
    DocumentIn,
    DocumentOut,
    QueryIn,
    QueryOut,
    TranscriptWebhookIn,
    TranscriptWebhookOut,
)
from app.scoring import score_transcript
from app.settings import settings
from app.store import ChunkRecord, build_store

embedding_provider = HashEmbeddingProvider(settings.embedding_dim)
store = build_store(settings.database_url, settings.embedding_dim)
llm = LLMClient(api_key=settings.openai_api_key, model=settings.openai_model)


@asynccontextmanager
async def lifespan(_: FastAPI):
    store.init()
    yield


app = FastAPI(
    title="AI Ops Workflow Kit",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "ok": True,
        "storage": store.name,
        "embedding_dim": settings.embedding_dim,
    }


@app.post("/documents", response_model=DocumentOut)
def ingest_document(document: DocumentIn) -> DocumentOut:
    chunks = [
        ChunkRecord(
            id=uuid4(),
            source=document.source,
            text=chunk,
            metadata=document.metadata,
            embedding=embedding_provider.embed(chunk),
        )
        for chunk in chunk_text(document.text)
    ]
    store.add_chunks(chunks)
    return DocumentOut(source=document.source, chunks=len(chunks))


@app.post("/query", response_model=QueryOut)
async def query(payload: QueryIn) -> QueryOut:
    embedding = embedding_provider.embed(payload.question)
    contexts = store.search(embedding, payload.top_k)
    answer = await llm.answer(payload.question, contexts)
    return QueryOut(answer=answer, contexts=contexts, top_k=payload.top_k)


@app.post("/approvals", response_model=ApprovalOut)
def create_approval(payload: ApprovalIn) -> ApprovalOut:
    return store.create_approval(payload)


@app.post("/approvals/{item_id}/approve", response_model=ApprovalOut)
def approve(item_id: UUID, decision: ApprovalDecision) -> ApprovalOut:
    try:
        return store.approve(item_id, decision.reviewer, decision.notes)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/approvals/{item_id}/reject", response_model=ApprovalOut)
def reject(item_id: UUID, decision: ApprovalDecision) -> ApprovalOut:
    try:
        return store.reject(item_id, decision.reviewer, decision.notes)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/webhooks/n8n/call-transcript", response_model=TranscriptWebhookOut)
def call_transcript_webhook(payload: TranscriptWebhookIn) -> TranscriptWebhookOut:
    ingest_document(
        DocumentIn(
            source=f"call://{payload.call_id}",
            text=payload.transcript,
            metadata={
                "customer_id": payload.customer_id,
                "call_id": payload.call_id,
                **payload.metadata,
            },
        )
    )
    transcript_score = score_transcript(payload.transcript)
    approval = store.create_approval(
        ApprovalIn(
            kind="call_follow_up",
            title=f"Review follow-up for call {payload.call_id}",
            draft=build_follow_up_draft(payload.transcript, transcript_score.score),
            context={
                "customer_id": payload.customer_id,
                "call_id": payload.call_id,
                "score": transcript_score.score,
                "signals": transcript_score.signals,
            },
        )
    )
    return TranscriptWebhookOut(
        call_id=payload.call_id,
        customer_id=payload.customer_id,
        score=transcript_score.score,
        signals=transcript_score.signals,
        approval=approval,
    )


def build_follow_up_draft(transcript: str, score: int) -> str:
    excerpt = transcript.strip().replace("\n", " ")[:500]
    return (
        f"Call score: {score}/100.\n\n"
        "Suggested next action: confirm unresolved buying criteria, send a concise recap, "
        "and ask for a dated next step.\n\n"
        f"Transcript excerpt: {excerpt}"
    )

