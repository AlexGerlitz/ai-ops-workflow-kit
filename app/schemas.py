from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentIn(BaseModel):
    source: str = Field(min_length=1, max_length=300)
    text: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentOut(BaseModel):
    source: str
    chunks: int


class GoogleDriveImportIn(BaseModel):
    file_id: str = Field(min_length=1, max_length=160)
    name: str = Field(min_length=1, max_length=300)
    mime_type: str = Field(default="text/plain", min_length=1, max_length=160)
    text: str = Field(min_length=1)
    web_url: str | None = Field(default=None, max_length=500)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GoogleDriveImportOut(BaseModel):
    adapter_key: str
    operation: str
    dry_run: bool
    source: str
    file_id: str
    name: str
    mime_type: str
    chunks: int
    metadata: dict[str, Any]


class QueryIn(BaseModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class RetrievedContext(BaseModel):
    id: UUID
    source: str
    text: str
    metadata: dict[str, Any]
    score: float


class CallAnalysisOut(BaseModel):
    summary: str
    risk_level: str
    missing_signals: list[str]
    objections: list[str]
    next_action: str
    follow_up_draft: str
    crm_update: dict[str, Any]
    knowledge_context: list[RetrievedContext]


class QueryOut(BaseModel):
    answer: str
    contexts: list[RetrievedContext]
    top_k: int


class ApprovalStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class IntegrationEventStatus(str, Enum):
    queued = "queued"
    retry = "retry"
    sent = "sent"
    failed = "failed"
    dead_letter = "dead_letter"


class IntegrationDispatchStatus(str, Enum):
    dry_run = "dry_run"
    sent = "sent"
    not_configured = "not_configured"
    failed = "failed"


class ApprovalIn(BaseModel):
    kind: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=240)
    draft: str = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)


class ApprovalDecision(BaseModel):
    reviewer: str = Field(default="system", max_length=120)
    notes: str = Field(default="", max_length=1000)


class ApprovalOut(BaseModel):
    id: UUID
    kind: str
    title: str
    draft: str
    context: dict[str, Any]
    status: ApprovalStatus
    reviewer: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class TranscriptWebhookIn(BaseModel):
    call_id: str = Field(min_length=1, max_length=160)
    customer_id: str = Field(min_length=1, max_length=160)
    transcript: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TranscriptWebhookOut(BaseModel):
    call_id: str
    customer_id: str
    score: int
    signals: dict[str, bool]
    analysis: CallAnalysisOut
    approval: ApprovalOut


class TranscriptionStatus(str, Enum):
    dry_run = "dry_run"
    transcribed = "transcribed"
    not_configured = "not_configured"
    failed = "failed"


class CallAudioWebhookIn(BaseModel):
    call_id: str = Field(min_length=1, max_length=160)
    customer_id: str = Field(min_length=1, max_length=160)
    audio_uri: str = Field(min_length=1, max_length=500)
    audio_mime_type: str = Field(default="audio/mpeg", min_length=1, max_length=120)
    duration_seconds: float | None = Field(default=None, ge=0)
    language: str = Field(default="ru", min_length=2, max_length=16)
    provider: str | None = Field(default=None, max_length=80)
    transcript_hint: str | None = Field(default=None, min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TranscriptionSegmentOut(BaseModel):
    speaker: str | None = None
    start_seconds: float | None = None
    end_seconds: float | None = None
    text: str


class TranscriptionOut(BaseModel):
    provider: str
    status: TranscriptionStatus
    audio_uri: str
    audio_mime_type: str
    language: str
    duration_seconds: float | None = None
    transcript: str
    segments: list[TranscriptionSegmentOut]
    confidence: float | None = None
    detail: str
    request_contract: dict[str, Any]


class CallAudioWebhookOut(BaseModel):
    call_id: str
    customer_id: str
    transcription: TranscriptionOut
    transcript_result: TranscriptWebhookOut


class TranscriptionProviderRuntimeOut(BaseModel):
    provider: str
    configured: bool
    selected: bool
    dry_run: bool
    required_env: list[str]
    notes: str


class TranscriptionRuntimeOut(BaseModel):
    requested_provider: str
    selected_provider: str
    dry_run: bool
    supported_providers: list[str]
    providers: list[TranscriptionProviderRuntimeOut]


class TelegramUser(BaseModel):
    id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None


class TelegramChat(BaseModel):
    id: int
    type: str | None = None


class TelegramMessage(BaseModel):
    message_id: int | None = None
    chat: TelegramChat | None = None


class TelegramCallbackQuery(BaseModel):
    id: str
    from_user: TelegramUser = Field(alias="from")
    data: str = Field(min_length=1)
    message: TelegramMessage | None = None


class TelegramWebhookIn(BaseModel):
    update_id: int | None = None
    callback_query: TelegramCallbackQuery | None = None


class TelegramWebhookOut(BaseModel):
    ok: bool
    action: str
    approval_id: UUID
    approval_status: ApprovalStatus
    reviewer: str
    crm_handoff_event_id: UUID | None = None


class IntegrationEventOut(BaseModel):
    id: UUID
    adapter_key: str
    operation: str
    status: IntegrationEventStatus
    payload: dict[str, Any]
    source_approval_id: UUID | None = None
    idempotency_key: str
    attempt_count: int = 0
    last_error: str | None = None
    next_retry_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class IntegrationCapabilityOut(BaseModel):
    adapter_key: str
    configured: bool
    dry_run: bool
    webhook_secret_configured: bool = False
    required_env: list[str]
    notes: str


class IntegrationRuntimeOut(BaseModel):
    public_base_url: str
    capabilities: list[IntegrationCapabilityOut]


class LLMProviderRuntimeOut(BaseModel):
    provider: str
    model: str
    configured: bool
    selected: bool
    required_env: list[str]
    notes: str


class LLMRuntimeOut(BaseModel):
    requested_provider: str
    selected_provider: str
    fallback: bool
    configured_providers: list[str]
    supported_providers: list[str]
    providers: list[LLMProviderRuntimeOut]


class IntegrationDispatchOut(BaseModel):
    adapter_key: str
    operation: str
    status: IntegrationDispatchStatus
    payload: dict[str, Any]
    detail: str = ""
    event_status: IntegrationEventStatus | None = None
    attempt_count: int | None = None
    max_attempts: int | None = None


class CallAudioUploadOut(BaseModel):
    upload: dict[str, Any]
    transcription: TranscriptionOut
    transcript_result: TranscriptWebhookOut
    telegram_approval: IntegrationDispatchOut


class IntegrationDrainOut(BaseModel):
    adapter_key: str
    selected: int
    dispatched: int
    sent: int
    retry: int
    dead_letter: int
    dry_run: int
    event_ids: list[UUID]


class OfferDemoRunOut(BaseModel):
    runtime: dict[str, Any]
    integrations: IntegrationRuntimeOut
    ingestion: DocumentOut
    google_drive_import: GoogleDriveImportOut
    rag_context_sources: list[dict[str, Any]]
    transcription: dict[str, Any]
    call_analysis: dict[str, Any]
    approval: dict[str, Any]
    telegram_approval: dict[str, Any]
    crm_handoff: dict[str, Any]
    bitrix24_dispatch: dict[str, Any]
