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


class QueryIn(BaseModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class RetrievedContext(BaseModel):
    id: UUID
    source: str
    text: str
    metadata: dict[str, Any]
    score: float


class QueryOut(BaseModel):
    answer: str
    contexts: list[RetrievedContext]
    top_k: int


class ApprovalStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


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
    approval: ApprovalOut

