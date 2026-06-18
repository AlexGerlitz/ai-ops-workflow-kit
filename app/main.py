from contextlib import asynccontextmanager
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse

from app.chunking import chunk_text
from app.demo_payloads import DEMO_SALES_PLAYBOOK, DEMO_TRANSCRIPT
from app.embeddings import HashEmbeddingProvider
from app.integrations import (
    dispatch_bitrix24_event,
    dispatch_telegram_approval,
    integration_runtime,
)
from app.llm import LLMClient
from app.observability import RuntimeStats, prometheus_metrics
from app.sales_workflow import build_call_analysis
from app.schemas import (
    ApprovalDecision,
    ApprovalIn,
    ApprovalOut,
    ApprovalStatus,
    DocumentIn,
    DocumentOut,
    IntegrationDispatchOut,
    IntegrationEventOut,
    IntegrationRuntimeOut,
    OfferDemoRunOut,
    QueryIn,
    QueryOut,
    TelegramWebhookIn,
    TelegramWebhookOut,
    TranscriptWebhookIn,
    TranscriptWebhookOut,
)
from app.scoring import score_transcript
from app.settings import settings
from app.store import ChunkRecord, build_store
from app.ui import DEMO_PAGE_HTML

embedding_provider = HashEmbeddingProvider(settings.embedding_dim)
store = build_store(settings.database_url, settings.embedding_dim)
llm = LLMClient(api_key=settings.openai_api_key, model=settings.openai_model)
runtime_stats = RuntimeStats()


@asynccontextmanager
async def lifespan(_: FastAPI):
    store.init()
    yield


app = FastAPI(
    title="AI Ops Workflow Kit",
    version=settings.app_version,
    lifespan=lifespan,
)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def demo_page() -> HTMLResponse:
    return HTMLResponse(DEMO_PAGE_HTML)


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "ok": True,
        "storage": store.name,
        "embedding_dim": settings.embedding_dim,
    }


@app.get("/runtime")
def runtime() -> dict[str, object]:
    return {
        "ok": True,
        "version": settings.app_version,
        "git_sha": settings.git_sha,
        "environment": settings.deploy_environment,
        "started_at": runtime_stats.started_at.isoformat(),
        "uptime_seconds": runtime_stats.uptime_seconds(),
        "storage": store.name,
        "embedding_dim": settings.embedding_dim,
        "public_base_url": settings.public_base_url,
        "integrations": get_integration_runtime(),
        "counters": runtime_stats.snapshot(),
    }


@app.get("/metrics", response_class=PlainTextResponse)
def metrics() -> PlainTextResponse:
    return PlainTextResponse(
        prometheus_metrics(
            stats=runtime_stats,
            app_version=settings.app_version,
            git_sha=settings.git_sha,
            deploy_environment=settings.deploy_environment,
            storage=store.name,
        ),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@app.get("/integrations/runtime", response_model=IntegrationRuntimeOut)
def get_integration_runtime() -> IntegrationRuntimeOut:
    return integration_runtime(settings)


@app.post("/demo/run", response_model=OfferDemoRunOut)
async def run_demo_workflow() -> OfferDemoRunOut:
    runtime_stats.increment("demo_runs_total")
    document = ingest_document(
        DocumentIn(
            source="drive://demo/sales-playbook",
            text=DEMO_SALES_PLAYBOOK,
            metadata={"team": "sales", "public_demo": True},
        )
    )
    rag = await query(
        QueryIn(
            question="What should happen before a follow-up reaches the CRM?",
            top_k=3,
        )
    )
    analysis = call_transcript_webhook(TranscriptWebhookIn(**DEMO_TRANSCRIPT))
    telegram = notify_approval_in_telegram(analysis.approval.id)
    approved = approve(
        analysis.approval.id,
        ApprovalDecision(reviewer="sales-lead", notes="Synthetic demo approval"),
    )
    events = [
        event
        for event in store.list_integration_events("bitrix24.mock")
        if event.source_approval_id == analysis.approval.id
    ]
    if not events:
        raise HTTPException(status_code=500, detail="CRM handoff event was not queued")
    crm_event = events[-1]
    bitrix24 = dispatch_event_to_bitrix24(crm_event.id)
    return OfferDemoRunOut(
        runtime=health(),
        integrations=get_integration_runtime(),
        ingestion=document,
        rag_context_sources=[
            {"source": context.source, "score": context.score}
            for context in rag.contexts
        ],
        call_analysis={
            "call_id": analysis.call_id,
            "customer_id": analysis.customer_id,
            "score": analysis.score,
            "risk_level": analysis.analysis.risk_level,
            "missing_signals": analysis.analysis.missing_signals,
            "objections": analysis.analysis.objections,
            "next_action": analysis.analysis.next_action,
            "follow_up_draft": analysis.analysis.follow_up_draft,
        },
        approval={
            "id": str(analysis.approval.id),
            "status": approved.status.value,
            "reviewer": approved.reviewer,
        },
        telegram_approval={
            "adapter_key": telegram.adapter_key,
            "operation": telegram.operation,
            "status": telegram.status.value,
            "callback_contract": telegram.payload["callback_contract"],
        },
        crm_handoff={
            "event_id": str(crm_event.id),
            "adapter_key": crm_event.adapter_key,
            "operation": crm_event.operation,
            "status": crm_event.status.value,
            "target_stage": crm_event.payload["target_stage"],
            "task": crm_event.payload["task"],
        },
        bitrix24_dispatch={
            "adapter_key": bitrix24.adapter_key,
            "operation": bitrix24.operation,
            "status": bitrix24.status.value,
            "method": bitrix24.payload["method"],
        },
    )


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
    runtime_stats.increment("documents_ingested_total")
    return DocumentOut(source=document.source, chunks=len(chunks))


@app.post("/query", response_model=QueryOut)
async def query(payload: QueryIn) -> QueryOut:
    runtime_stats.increment("query_requests_total")
    embedding = embedding_provider.embed(payload.question)
    contexts = store.search(embedding, payload.top_k)
    answer = await llm.answer(payload.question, contexts)
    return QueryOut(answer=answer, contexts=contexts, top_k=payload.top_k)


@app.post("/approvals", response_model=ApprovalOut)
def create_approval(payload: ApprovalIn) -> ApprovalOut:
    approval = store.create_approval(payload)
    runtime_stats.increment("approvals_created_total")
    return approval


@app.get("/approvals", response_model=list[ApprovalOut])
def list_approvals(status: ApprovalStatus | None = None) -> list[ApprovalOut]:
    return store.list_approvals(status)


@app.get("/approvals/{item_id}", response_model=ApprovalOut)
def get_approval(item_id: UUID) -> ApprovalOut:
    try:
        return store.get_approval(item_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="approval item not found") from exc


@app.post("/approvals/{item_id}/approve", response_model=ApprovalOut)
def approve(item_id: UUID, decision: ApprovalDecision) -> ApprovalOut:
    try:
        approval = store.approve(item_id, decision.reviewer, decision.notes)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    runtime_stats.increment("approvals_approved_total")
    queue_crm_handoff_if_needed(approval)
    return approval


@app.post("/approvals/{item_id}/reject", response_model=ApprovalOut)
def reject(item_id: UUID, decision: ApprovalDecision) -> ApprovalOut:
    try:
        rejected = store.reject(item_id, decision.reviewer, decision.notes)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    runtime_stats.increment("approvals_rejected_total")
    return rejected


@app.post("/approvals/{item_id}/notify/telegram", response_model=IntegrationDispatchOut)
def notify_approval_in_telegram(item_id: UUID) -> IntegrationDispatchOut:
    try:
        approval = store.get_approval(item_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="approval item not found") from exc
    dispatch = dispatch_telegram_approval(approval, settings)
    runtime_stats.increment("telegram_dispatches_total")
    return dispatch


@app.post("/webhooks/telegram/approval", response_model=TelegramWebhookOut)
def telegram_approval_webhook(payload: TelegramWebhookIn) -> TelegramWebhookOut:
    callback = payload.callback_query
    if callback is None:
        raise HTTPException(status_code=400, detail="callback_query is required")

    try:
        action, approval_id_raw = callback.data.split(":", 1)
        approval_id = UUID(approval_id_raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid callback_data") from exc

    reviewer = callback.from_user.username or f"telegram:{callback.from_user.id}"
    if action == "approve":
        approval = approve(
            approval_id,
            ApprovalDecision(reviewer=reviewer, notes="Approved from Telegram callback"),
        )
        events = [
            event
            for event in store.list_integration_events("bitrix24.mock")
            if event.source_approval_id == approval.id
        ]
        crm_handoff_event_id = events[-1].id if events else None
    elif action == "reject":
        approval = reject(
            approval_id,
            ApprovalDecision(reviewer=reviewer, notes="Rejected from Telegram callback"),
        )
        crm_handoff_event_id = None
    else:
        raise HTTPException(status_code=400, detail="unsupported callback action")

    runtime_stats.increment("telegram_callbacks_total")
    return TelegramWebhookOut(
        ok=True,
        action=action,
        approval_id=approval.id,
        approval_status=approval.status,
        reviewer=reviewer,
        crm_handoff_event_id=crm_handoff_event_id,
    )


@app.get("/integration-events", response_model=list[IntegrationEventOut])
def list_integration_events(adapter_key: str | None = None) -> list[IntegrationEventOut]:
    return store.list_integration_events(adapter_key)


@app.post("/integration-events/{event_id}/dispatch/bitrix24", response_model=IntegrationDispatchOut)
def dispatch_event_to_bitrix24(event_id: UUID) -> IntegrationDispatchOut:
    try:
        event = store.get_integration_event(event_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="integration event not found") from exc
    dispatch = dispatch_bitrix24_event(event, settings)
    runtime_stats.increment("bitrix24_dispatches_total")
    return dispatch


@app.post("/webhooks/n8n/call-transcript", response_model=TranscriptWebhookOut)
def call_transcript_webhook(payload: TranscriptWebhookIn) -> TranscriptWebhookOut:
    runtime_stats.increment("transcript_webhooks_total")
    knowledge_context = store.search(
        embedding_provider.embed(payload.transcript),
        settings.top_k,
    )
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
    analysis = build_call_analysis(
        call_id=payload.call_id,
        customer_id=payload.customer_id,
        transcript=payload.transcript,
        transcript_score=transcript_score,
        knowledge_context=knowledge_context,
    )
    approval = store.create_approval(
        ApprovalIn(
            kind="call_follow_up",
            title=f"Review follow-up for call {payload.call_id}",
            draft=analysis.follow_up_draft,
            context={
                "customer_id": payload.customer_id,
                "call_id": payload.call_id,
                "score": transcript_score.score,
                "signals": transcript_score.signals,
                "risk_level": analysis.risk_level,
                "missing_signals": analysis.missing_signals,
                "objections": analysis.objections,
                "next_action": analysis.next_action,
                "crm_update": analysis.crm_update,
                "knowledge_context_sources": [
                    {
                        "source": context.source,
                        "score": context.score,
                        "metadata": context.metadata,
                    }
                    for context in knowledge_context
                ],
            },
        )
    )
    return TranscriptWebhookOut(
        call_id=payload.call_id,
        customer_id=payload.customer_id,
        score=transcript_score.score,
        signals=transcript_score.signals,
        analysis=analysis,
        approval=approval,
    )


def queue_crm_handoff_if_needed(approval: ApprovalOut) -> None:
    crm_update = approval.context.get("crm_update")
    if approval.kind != "call_follow_up" or not isinstance(crm_update, dict):
        return
    adapter_key = str(crm_update.get("adapter") or "bitrix24.mock")
    operation = str(crm_update.get("operation") or "upsert_lead_follow_up")
    store.create_integration_event(
        adapter_key=adapter_key,
        operation=operation,
        payload=crm_update,
        source_approval_id=approval.id,
    )
    runtime_stats.increment("crm_handoffs_queued_total")
