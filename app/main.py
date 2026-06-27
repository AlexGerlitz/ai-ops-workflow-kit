import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from hmac import compare_digest
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import UUID, uuid4

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse

from app.chunking import chunk_text
from app.demo_payloads import DEMO_CALL_AUDIO, DEMO_RAG_EVAL_QUESTIONS, DEMO_SALES_PLAYBOOK
from app.embeddings import HashEmbeddingProvider
from app.integrations import (
    GOOGLE_DRIVE_ADAPTER_KEY,
    answer_telegram_callback,
    dispatch_bitrix24_event,
    dispatch_telegram_approval,
    integration_runtime,
)
from app.llm import LLMClient
from app.observability import RuntimeStats, prometheus_metrics
from app.privacy import redact_text, redact_transcription
from app.rag_eval import evaluate_retrieval
from app.sales_workflow import build_call_analysis
from app.schemas import (
    ApprovalDecision,
    ApprovalIn,
    ApprovalOut,
    ApprovalStatus,
    CallAudioWebhookIn,
    CallAudioWebhookOut,
    CallAudioUploadOut,
    DocumentIn,
    DocumentOut,
    GoogleDriveImportIn,
    GoogleDriveImportOut,
    IntegrationDrainOut,
    IntegrationDispatchStatus,
    IntegrationDispatchOut,
    IntegrationEventOut,
    IntegrationEventStatus,
    IntegrationRuntimeOut,
    LLMRuntimeOut,
    OfferDemoRunOut,
    QueryIn,
    QueryOut,
    RagEvalIn,
    RagEvalQuestion,
    RagEvaluationOut,
    TelegramWebhookIn,
    TelegramWebhookOut,
    TranscriptWebhookIn,
    TranscriptWebhookOut,
    TranscriptionOut,
    TranscriptionRuntimeOut,
)
from app.scoring import score_transcript
from app.settings import Settings, settings
from app.store import ChunkRecord, build_store
from app.transcription import transcribe_call_audio, transcription_runtime
from app.ui import DEMO_PAGE_HTML

embedding_provider = HashEmbeddingProvider(settings.embedding_dim)
store = build_store(settings.database_url, settings.embedding_dim)
llm = LLMClient(
    provider=settings.llm_provider,
    openai_api_key=settings.openai_api_key,
    openai_model=settings.openai_model,
    anthropic_api_key=settings.anthropic_api_key,
    anthropic_model=settings.anthropic_model,
    gemini_api_key=settings.gemini_api_key,
    gemini_model=settings.gemini_model,
    timeout_seconds=settings.llm_timeout_seconds,
)
runtime_stats = RuntimeStats()
logger = logging.getLogger("aiops.integration_worker")
UPLOAD_CHUNK_BYTES = 1024 * 1024
UPLOAD_AUDIO_MIME_BY_SUFFIX = {
    ".aac": "audio/aac",
    ".m4a": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".mp4": "audio/mp4",
    ".ogg": "audio/ogg",
    ".opus": "audio/ogg",
    ".wav": "audio/wav",
    ".webm": "audio/webm",
}


@asynccontextmanager
async def lifespan(_: FastAPI):
    store.init()
    worker_task: asyncio.Task[None] | None = None
    if bitrix24_worker_is_active():
        worker_task = asyncio.create_task(bitrix24_outbox_worker_loop())
    try:
        yield
    finally:
        if worker_task is not None:
            worker_task.cancel()
            with suppress(asyncio.CancelledError):
                await worker_task


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
        "llm": get_llm_runtime(),
        "transcription": get_transcription_runtime(),
        "integrations": get_integration_runtime(),
        "workers": integration_workers_runtime(),
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


@app.get("/llm/runtime", response_model=LLMRuntimeOut)
def get_llm_runtime() -> LLMRuntimeOut:
    return LLMRuntimeOut(**llm.runtime())


@app.get("/transcription/runtime", response_model=TranscriptionRuntimeOut)
def get_transcription_runtime() -> TranscriptionRuntimeOut:
    return transcription_runtime(settings)


def integration_workers_runtime() -> dict[str, object]:
    return {
        "bitrix24_outbox": {
            "enabled": settings.integration_worker_enabled,
            "active": bitrix24_worker_is_active(),
            "dry_run": settings.bitrix24_dry_run,
            "interval_seconds": settings.integration_worker_interval_seconds,
            "batch_size": settings.integration_worker_batch_size,
            "notes": (
                "Worker is active only when enabled and Bitrix24 dry-run is disabled; "
                "public demo keeps it disabled to avoid consuming synthetic events."
            ),
        }
    }


@app.post("/demo/run", response_model=OfferDemoRunOut)
async def run_demo_workflow() -> OfferDemoRunOut:
    runtime_stats.increment("demo_runs_total")
    store.delete_sources(
        [
            "gdrive://demo-sales-playbook",
            f"call://{DEMO_CALL_AUDIO['call_id']}",
        ]
    )
    drive_import = import_google_drive_document(
        GoogleDriveImportIn(
            file_id="demo-sales-playbook",
            name="Sales playbook",
            mime_type="application/vnd.google-apps.document",
            text=DEMO_SALES_PLAYBOOK,
            web_url="https://drive.google.com/file/d/demo-sales-playbook",
            metadata={"team": "sales", "public_demo": True},
        )
    )
    rag = await query(
        QueryIn(
            question="What should happen before a follow-up reaches the CRM?",
            top_k=3,
        )
    )
    rag_quality = evaluate_rag(
        RagEvalIn(questions=default_rag_eval_questions()),
    )
    audio = call_audio_webhook(CallAudioWebhookIn(**DEMO_CALL_AUDIO))
    analysis = audio.transcript_result
    telegram = dispatch_telegram_approval(
        analysis.approval,
        settings.model_copy(update={"telegram_dry_run": True}),
    )
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
        runtime=runtime(),
        integrations=get_integration_runtime(),
        ingestion=DocumentOut(source=drive_import.source, chunks=drive_import.chunks),
        google_drive_import=drive_import,
        rag_context_sources=[
            {"source": context.source, "score": context.score}
            for context in rag.contexts
        ],
        rag_quality=rag_quality,
        privacy=analysis.privacy.model_dump(mode="json"),
        transcription={
            "provider": audio.transcription.provider,
            "status": audio.transcription.status.value,
            "audio_uri": audio.transcription.audio_uri,
            "language": audio.transcription.language,
            "duration_seconds": audio.transcription.duration_seconds,
            "segments": [
                {
                    "speaker": segment.speaker,
                    "start_seconds": segment.start_seconds,
                    "end_seconds": segment.end_seconds,
                    "text": segment.text,
                }
                for segment in audio.transcription.segments
            ],
            "request_contract": audio.transcription.request_contract,
        },
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
            "idempotency_key": crm_event.idempotency_key,
            "attempt_count": crm_event.attempt_count,
            "last_error": crm_event.last_error,
            "next_retry_at": crm_event.next_retry_at.isoformat() if crm_event.next_retry_at else None,
            "target_stage": crm_event.payload["target_stage"],
            "task": crm_event.payload["task"],
        },
        bitrix24_dispatch={
            "adapter_key": bitrix24.adapter_key,
            "operation": bitrix24.operation,
            "status": bitrix24.status.value,
            "event_status": bitrix24.event_status.value if bitrix24.event_status else None,
            "attempt_count": bitrix24.attempt_count,
            "max_attempts": bitrix24.max_attempts,
            "method": bitrix24.payload["method"],
            "bitrix_request": bitrix24.payload["bitrix_request"],
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


@app.post("/integrations/google-drive/import", response_model=GoogleDriveImportOut)
def import_google_drive_document(payload: GoogleDriveImportIn) -> GoogleDriveImportOut:
    source = f"gdrive://{payload.file_id}"
    metadata = {
        **payload.metadata,
        "adapter": GOOGLE_DRIVE_ADAPTER_KEY,
        "file_id": payload.file_id,
        "name": payload.name,
        "mime_type": payload.mime_type,
    }
    if payload.web_url:
        metadata["web_url"] = payload.web_url
    document = ingest_document(
        DocumentIn(
            source=source,
            text=payload.text,
            metadata=metadata,
        )
    )
    runtime_stats.increment("google_drive_imports_total")
    return GoogleDriveImportOut(
        adapter_key=GOOGLE_DRIVE_ADAPTER_KEY,
        operation="import_exported_text",
        dry_run=settings.google_drive_dry_run,
        source=document.source,
        file_id=payload.file_id,
        name=payload.name,
        mime_type=payload.mime_type,
        chunks=document.chunks,
        metadata=metadata,
    )


@app.post("/query", response_model=QueryOut)
async def query(payload: QueryIn) -> QueryOut:
    runtime_stats.increment("query_requests_total")
    embedding = embedding_provider.embed(payload.question)
    contexts = store.search(embedding, payload.top_k)
    answer = await llm.answer(payload.question, contexts)
    return QueryOut(answer=answer, contexts=contexts, top_k=payload.top_k)


@app.post("/rag/eval", response_model=RagEvaluationOut)
def evaluate_rag(payload: RagEvalIn | None = None) -> RagEvaluationOut:
    runtime_stats.increment("rag_evaluations_total")
    questions = payload.questions if payload and payload.questions else default_rag_eval_questions()
    evaluation = evaluate_retrieval(
        questions=questions,
        embed=embedding_provider.embed,
        search=store.search,
    )
    if not evaluation.ok:
        runtime_stats.increment("rag_eval_failures_total")
    return evaluation


def default_rag_eval_questions() -> list[RagEvalQuestion]:
    return [RagEvalQuestion(**question) for question in DEMO_RAG_EVAL_QUESTIONS]


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
def telegram_approval_webhook(
    payload: TelegramWebhookIn,
    x_telegram_bot_api_secret_token: str | None = Header(
        default=None,
        alias="X-Telegram-Bot-Api-Secret-Token",
    ),
) -> TelegramWebhookOut:
    if settings.telegram_webhook_secret and not compare_digest(
        x_telegram_bot_api_secret_token or "",
        settings.telegram_webhook_secret,
    ):
        runtime_stats.increment("telegram_callback_auth_failures_total")
        raise HTTPException(status_code=403, detail="invalid Telegram webhook secret")

    callback = payload.callback_query
    if callback is None:
        raise HTTPException(status_code=400, detail="callback_query is required")

    try:
        action, approval_id_raw = callback.data.split(":", 1)
        approval_id = UUID(approval_id_raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid callback_data") from exc

    reviewer = callback.from_user.username or f"telegram:{callback.from_user.id}"
    if action not in {"approve", "reject"}:
        raise HTTPException(status_code=400, detail="unsupported callback action")

    try:
        current_approval = store.get_approval(approval_id)
    except KeyError as exc:
        answer_telegram_callback(callback.id, "Approval not found", settings)
        raise HTTPException(status_code=404, detail="approval item not found") from exc

    if current_approval.status != ApprovalStatus.pending:
        crm_handoff_event_id = latest_crm_handoff_event_id(current_approval.id)
        answer_telegram_callback(
            callback.id,
            f"Already {current_approval.status.value}",
            settings,
        )
        runtime_stats.increment("telegram_callbacks_total")
        return TelegramWebhookOut(
            ok=True,
            action=action,
            approval_id=current_approval.id,
            approval_status=current_approval.status,
            reviewer=current_approval.reviewer or reviewer,
            crm_handoff_event_id=crm_handoff_event_id,
        )

    if action == "approve":
        approval = approve(
            approval_id,
            ApprovalDecision(reviewer=reviewer, notes="Approved from Telegram callback"),
        )
        crm_handoff_event_id = latest_crm_handoff_event_id(approval.id)
    elif action == "reject":
        approval = reject(
            approval_id,
            ApprovalDecision(reviewer=reviewer, notes="Rejected from Telegram callback"),
        )
        crm_handoff_event_id = None

    answer_telegram_callback(callback.id, action.title(), settings)
    runtime_stats.increment("telegram_callbacks_total")
    return TelegramWebhookOut(
        ok=True,
        action=action,
        approval_id=approval.id,
        approval_status=approval.status,
        reviewer=reviewer,
        crm_handoff_event_id=crm_handoff_event_id,
    )


def latest_crm_handoff_event_id(approval_id: UUID) -> UUID | None:
    events = [
        event
        for event in store.list_integration_events("bitrix24.mock")
        if event.source_approval_id == approval_id
    ]
    return events[-1].id if events else None


@app.get("/integration-events", response_model=list[IntegrationEventOut])
def list_integration_events(
    adapter_key: str | None = None,
    status: IntegrationEventStatus | None = None,
) -> list[IntegrationEventOut]:
    return store.list_integration_events(adapter_key, status)


@app.post("/integrations/bitrix24/drain", response_model=IntegrationDrainOut)
def drain_bitrix24_events(limit: int = 10) -> IntegrationDrainOut:
    selected_events = store.list_due_integration_events(
        adapter_key="bitrix24.mock",
        now=datetime.now(UTC),
        limit=max(min(limit, 100), 1),
    )
    result = {
        "sent": 0,
        "retry": 0,
        "dead_letter": 0,
        "dry_run": 0,
    }
    event_ids = []
    for event in selected_events:
        dispatch = dispatch_bitrix24_event(event, settings)
        runtime_stats.increment("bitrix24_dispatches_total")
        updated_event = record_bitrix24_dispatch_result(event, dispatch)
        event_ids.append(updated_event.id)
        if dispatch.status == IntegrationDispatchStatus.dry_run:
            result["dry_run"] += 1
        elif updated_event.status == IntegrationEventStatus.sent:
            result["sent"] += 1
        elif updated_event.status == IntegrationEventStatus.dead_letter:
            result["dead_letter"] += 1
        elif updated_event.status == IntegrationEventStatus.retry:
            result["retry"] += 1

    runtime_stats.increment_by("integration_events_drained_total", len(event_ids))
    return IntegrationDrainOut(
        adapter_key="bitrix24",
        selected=len(selected_events),
        dispatched=len(event_ids),
        sent=result["sent"],
        retry=result["retry"],
        dead_letter=result["dead_letter"],
        dry_run=result["dry_run"],
        event_ids=event_ids,
    )


@app.post("/integration-events/{event_id}/dispatch/bitrix24", response_model=IntegrationDispatchOut)
def dispatch_event_to_bitrix24(event_id: UUID) -> IntegrationDispatchOut:
    try:
        event = store.get_integration_event(event_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="integration event not found") from exc
    dispatch = dispatch_bitrix24_event(event, settings)
    runtime_stats.increment("bitrix24_dispatches_total")
    updated_event = record_bitrix24_dispatch_result(event, dispatch)
    return dispatch.model_copy(
        update={
            "event_status": updated_event.status,
            "attempt_count": updated_event.attempt_count,
            "max_attempts": settings.integration_max_attempts,
        }
    )


@app.post("/webhooks/n8n/call-transcript", response_model=TranscriptWebhookOut)
def call_transcript_webhook(payload: TranscriptWebhookIn) -> TranscriptWebhookOut:
    runtime_stats.increment("transcript_webhooks_total")
    redacted = redact_text(payload.transcript)
    privacy = redacted.evidence()
    if privacy.redacted:
        runtime_stats.increment("privacy_redacted_transcripts_total")
        runtime_stats.increment_by(
            "privacy_redactions_total",
            sum(privacy.replacement_counts.values()),
        )
    knowledge_context = store.search(
        embedding_provider.embed(redacted.text),
        settings.top_k,
    )
    ingest_document(
        DocumentIn(
            source=f"call://{payload.call_id}",
            text=redacted.text,
            metadata={
                "customer_id": payload.customer_id,
                "call_id": payload.call_id,
                "privacy": privacy.model_dump(mode="json"),
                **payload.metadata,
            },
        )
    )
    transcript_score = score_transcript(redacted.text)
    analysis = build_call_analysis(
        call_id=payload.call_id,
        customer_id=payload.customer_id,
        transcript=redacted.text,
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
                "privacy": privacy.model_dump(mode="json"),
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
        privacy=privacy,
    )


@app.post("/webhooks/n8n/call-audio", response_model=CallAudioWebhookOut)
def call_audio_webhook(payload: CallAudioWebhookIn) -> CallAudioWebhookOut:
    return process_call_audio(payload, settings)


@app.post("/demo/audio/upload", response_model=CallAudioUploadOut)
async def upload_call_audio_demo(
    file: UploadFile = File(...),
    call_id: str | None = Form(default=None),
    customer_id: str = Form(default="uploaded-lead"),
    language: str = Form(default="ru"),
    provider: str = Form(default="deepgram"),
) -> CallAudioUploadOut:
    temp_path: Path | None = None
    total_bytes = 0
    filename = Path(file.filename or "call-audio").name
    suffix = Path(filename).suffix.lower() or ".audio"
    try:
        with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_path = Path(temp_file.name)
            while chunk := await file.read(UPLOAD_CHUNK_BYTES):
                total_bytes += len(chunk)
                if total_bytes > settings.max_call_audio_upload_bytes:
                    raise HTTPException(status_code=413, detail="call audio upload is too large")
                temp_file.write(chunk)
        if total_bytes == 0:
            raise HTTPException(status_code=400, detail="call audio upload is empty")

        selected_provider = provider.strip() or "deepgram"
        upload_config = settings.model_copy(
            update={
                "transcription_provider": selected_provider,
                "transcription_dry_run": False,
            }
        )
        payload = CallAudioWebhookIn(
            call_id=call_id.strip() if call_id and call_id.strip() else f"upload-{uuid4().hex[:12]}",
            customer_id=customer_id.strip() or "uploaded-lead",
            audio_uri=str(temp_path),
            audio_mime_type=guess_upload_audio_mime(filename, file.content_type),
            duration_seconds=None,
            language=language.strip() or "ru",
            provider=selected_provider,
            metadata={
                "source": "browser-audio-upload",
                "original_filename": filename,
                "upload_bytes": total_bytes,
            },
        )
        result = process_call_audio(payload, upload_config)
        telegram = notify_approval_in_telegram(result.transcript_result.approval.id)
        public_audio_uri = f"upload://{filename}"
        return CallAudioUploadOut(
            upload={
                "filename": filename,
                "bytes": total_bytes,
                "stored": "temporary",
                "provider": selected_provider,
                "language": payload.language,
            },
            transcription=public_upload_transcription(result.transcription, public_audio_uri),
            transcript_result=result.transcript_result,
            telegram_approval=telegram,
        )
    finally:
        await file.close()
        if temp_path is not None:
            with suppress(FileNotFoundError):
                temp_path.unlink()


def guess_upload_audio_mime(filename: str, content_type: str | None) -> str:
    if content_type and content_type != "application/octet-stream":
        return content_type
    return UPLOAD_AUDIO_MIME_BY_SUFFIX.get(Path(filename).suffix.lower(), "application/octet-stream")


def public_upload_transcription(
    transcription: TranscriptionOut,
    public_audio_uri: str,
) -> TranscriptionOut:
    request_contract = {
        **transcription.request_contract,
        "audio_uri": public_audio_uri,
        "body": {"file": "uploaded audio bytes"},
    }
    return transcription.model_copy(
        update={
            "audio_uri": public_audio_uri,
            "request_contract": request_contract,
        }
    )


def process_call_audio(
    payload: CallAudioWebhookIn,
    config: Settings,
) -> CallAudioWebhookOut:
    runtime_stats.increment("audio_webhooks_total")
    try:
        transcription = transcribe_call_audio(payload, config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not transcription.transcript:
        raise HTTPException(
            status_code=503,
            detail=f"transcription unavailable: {transcription.detail}",
        )
    runtime_stats.increment("audio_transcriptions_total")
    public_transcription = redact_transcription(transcription)
    transcript_result = call_transcript_webhook(
        TranscriptWebhookIn(
            call_id=payload.call_id,
            customer_id=payload.customer_id,
            transcript=transcription.transcript,
            metadata={
                **payload.metadata,
                "audio_uri": payload.audio_uri,
                "audio_mime_type": payload.audio_mime_type,
                "transcription_provider": transcription.provider,
                "transcription_status": transcription.status.value,
                "transcription_segments": len(transcription.segments),
            },
        )
    )
    return CallAudioWebhookOut(
        call_id=payload.call_id,
        customer_id=payload.customer_id,
        transcription=public_transcription,
        transcript_result=transcript_result,
    )


def queue_crm_handoff_if_needed(approval: ApprovalOut) -> None:
    crm_update = approval.context.get("crm_update")
    if approval.kind != "call_follow_up" or not isinstance(crm_update, dict):
        return
    adapter_key = str(crm_update.get("adapter") or "bitrix24.mock")
    operation = str(crm_update.get("operation") or "upsert_lead_follow_up")
    idempotency_key = build_integration_idempotency_key(approval, adapter_key, operation)
    store.create_integration_event(
        adapter_key=adapter_key,
        operation=operation,
        payload=crm_update,
        idempotency_key=idempotency_key,
        source_approval_id=approval.id,
    )
    runtime_stats.increment("crm_handoffs_queued_total")


def record_bitrix24_dispatch_result(
    event: IntegrationEventOut,
    dispatch: IntegrationDispatchOut,
) -> IntegrationEventOut:
    if dispatch.status == IntegrationDispatchStatus.dry_run:
        return event

    if dispatch.status == IntegrationDispatchStatus.sent:
        return store.record_integration_dispatch_result(
            event.id,
            status=IntegrationEventStatus.sent,
            last_error=None,
            next_retry_at=None,
            increment_attempt=True,
        )

    runtime_stats.increment("bitrix24_dispatch_failures_total")
    next_attempt_count = event.attempt_count + 1
    max_attempts = max(settings.integration_max_attempts, 1)
    next_status = (
        IntegrationEventStatus.dead_letter
        if next_attempt_count >= max_attempts
        else IntegrationEventStatus.retry
    )
    next_retry_at = None
    if next_status == IntegrationEventStatus.retry:
        next_retry_at = datetime.now(UTC) + timedelta(
            seconds=max(settings.integration_retry_delay_seconds, 0)
        )
    updated = store.record_integration_dispatch_result(
        event.id,
        status=next_status,
        last_error=dispatch.detail,
        next_retry_at=next_retry_at,
        increment_attempt=True,
    )
    if next_status == IntegrationEventStatus.dead_letter and event.status != IntegrationEventStatus.dead_letter:
        runtime_stats.increment("integration_dead_letters_total")
    if next_status == IntegrationEventStatus.retry:
        runtime_stats.increment("integration_retries_scheduled_total")
    return updated


def build_integration_idempotency_key(
    approval: ApprovalOut,
    adapter_key: str,
    operation: str,
) -> str:
    raw_key = f"{approval.id}:{adapter_key}:{operation}"
    return sha256(raw_key.encode("utf-8")).hexdigest()


def bitrix24_worker_is_active() -> bool:
    return settings.integration_worker_enabled and not settings.bitrix24_dry_run


async def bitrix24_outbox_worker_loop() -> None:
    interval_seconds = max(settings.integration_worker_interval_seconds, 1.0)
    batch_size = max(min(settings.integration_worker_batch_size, 100), 1)
    while True:
        await asyncio.sleep(interval_seconds)
        try:
            runtime_stats.increment("integration_worker_ticks_total")
            drain_bitrix24_events(limit=batch_size)
        except Exception:
            runtime_stats.increment("integration_worker_errors_total")
            logger.exception("bitrix24 outbox worker failed")
