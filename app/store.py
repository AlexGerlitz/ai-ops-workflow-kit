from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row

from app.embeddings import vector_literal
from app.schemas import (
    ApprovalIn,
    ApprovalOut,
    ApprovalStatus,
    IntegrationEventOut,
    IntegrationEventStatus,
    RetrievedContext,
)


@dataclass
class ChunkRecord:
    id: UUID
    source: str
    text: str
    metadata: dict[str, Any]
    embedding: list[float]


class Store(Protocol):
    name: str

    def init(self) -> None: ...

    def add_chunks(self, chunks: list[ChunkRecord]) -> None: ...

    def delete_sources(self, sources: list[str]) -> None: ...

    def search(self, embedding: list[float], top_k: int) -> list[RetrievedContext]: ...

    def create_approval(self, item: ApprovalIn) -> ApprovalOut: ...

    def get_approval(self, item_id: UUID) -> ApprovalOut: ...

    def list_approvals(self, status: ApprovalStatus | None = None) -> list[ApprovalOut]: ...

    def approve(self, item_id: UUID, reviewer: str, notes: str) -> ApprovalOut: ...

    def reject(self, item_id: UUID, reviewer: str, notes: str) -> ApprovalOut: ...

    def create_integration_event(
        self,
        *,
        adapter_key: str,
        operation: str,
        payload: dict[str, Any],
        idempotency_key: str,
        source_approval_id: UUID | None = None,
    ) -> IntegrationEventOut: ...

    def get_integration_event(self, event_id: UUID) -> IntegrationEventOut: ...

    def list_integration_events(
        self,
        adapter_key: str | None = None,
        status: IntegrationEventStatus | None = None,
    ) -> list[IntegrationEventOut]: ...

    def list_due_integration_events(
        self,
        *,
        adapter_key: str,
        now: datetime,
        limit: int,
    ) -> list[IntegrationEventOut]: ...

    def record_integration_dispatch_result(
        self,
        event_id: UUID,
        *,
        status: IntegrationEventStatus,
        last_error: str | None,
        next_retry_at: datetime | None,
        increment_attempt: bool,
    ) -> IntegrationEventOut: ...


class InMemoryStore:
    name = "memory"

    def __init__(self) -> None:
        self.chunks: list[ChunkRecord] = []
        self.approvals: dict[UUID, ApprovalOut] = {}
        self.integration_events: dict[UUID, IntegrationEventOut] = {}

    def init(self) -> None:
        return None

    def add_chunks(self, chunks: list[ChunkRecord]) -> None:
        self.delete_sources([chunk.source for chunk in chunks])
        self.chunks.extend(chunks)

    def delete_sources(self, sources: list[str]) -> None:
        source_set = set(sources)
        if not source_set:
            return
        self.chunks = [chunk for chunk in self.chunks if chunk.source not in source_set]

    def search(self, embedding: list[float], top_k: int) -> list[RetrievedContext]:
        scored = []
        for chunk in self.chunks:
            score = sum(left * right for left, right in zip(embedding, chunk.embedding, strict=False))
            scored.append((score, chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [
            RetrievedContext(
                id=chunk.id,
                source=chunk.source,
                text=chunk.text,
                metadata=chunk.metadata,
                score=round(score, 6),
            )
            for score, chunk in scored[:top_k]
        ]

    def create_approval(self, item: ApprovalIn) -> ApprovalOut:
        now = datetime.now(UTC)
        approval = ApprovalOut(
            id=uuid4(),
            kind=item.kind,
            title=item.title,
            draft=item.draft,
            context=item.context,
            status=ApprovalStatus.pending,
            created_at=now,
            updated_at=now,
        )
        self.approvals[approval.id] = approval
        return approval

    def get_approval(self, item_id: UUID) -> ApprovalOut:
        return self.approvals[item_id]

    def list_approvals(self, status: ApprovalStatus | None = None) -> list[ApprovalOut]:
        approvals = list(self.approvals.values())
        if status is not None:
            approvals = [approval for approval in approvals if approval.status == status]
        return sorted(approvals, key=lambda approval: approval.created_at)

    def approve(self, item_id: UUID, reviewer: str, notes: str) -> ApprovalOut:
        return self._transition(item_id, ApprovalStatus.approved, reviewer, notes)

    def reject(self, item_id: UUID, reviewer: str, notes: str) -> ApprovalOut:
        return self._transition(item_id, ApprovalStatus.rejected, reviewer, notes)

    def _transition(self, item_id: UUID, status: ApprovalStatus, reviewer: str, notes: str) -> ApprovalOut:
        current = self.approvals[item_id]
        if current.status != ApprovalStatus.pending:
            raise ValueError(f"approval item is already {current.status}")
        updated = current.model_copy(
            update={
                "status": status,
                "reviewer": reviewer,
                "notes": notes,
                "updated_at": datetime.now(UTC),
            }
        )
        self.approvals[item_id] = updated
        return updated

    def create_integration_event(
        self,
        *,
        adapter_key: str,
        operation: str,
        payload: dict[str, Any],
        idempotency_key: str,
        source_approval_id: UUID | None = None,
    ) -> IntegrationEventOut:
        for existing in self.integration_events.values():
            if existing.idempotency_key == idempotency_key:
                return existing
        now = datetime.now(UTC)
        event = IntegrationEventOut(
            id=uuid4(),
            adapter_key=adapter_key,
            operation=operation,
            status=IntegrationEventStatus.queued,
            payload=payload,
            source_approval_id=source_approval_id,
            idempotency_key=idempotency_key,
            attempt_count=0,
            last_error=None,
            next_retry_at=None,
            created_at=now,
            updated_at=now,
        )
        self.integration_events[event.id] = event
        return event

    def get_integration_event(self, event_id: UUID) -> IntegrationEventOut:
        return self.integration_events[event_id]

    def list_integration_events(
        self,
        adapter_key: str | None = None,
        status: IntegrationEventStatus | None = None,
    ) -> list[IntegrationEventOut]:
        events = list(self.integration_events.values())
        if adapter_key is not None:
            events = [event for event in events if event.adapter_key == adapter_key]
        if status is not None:
            events = [event for event in events if event.status == status]
        return sorted(events, key=lambda event: event.created_at)

    def list_due_integration_events(
        self,
        *,
        adapter_key: str,
        now: datetime,
        limit: int,
    ) -> list[IntegrationEventOut]:
        events = [
            event
            for event in self.integration_events.values()
            if event.adapter_key == adapter_key
            and event.status in {IntegrationEventStatus.queued, IntegrationEventStatus.retry}
            and (event.next_retry_at is None or event.next_retry_at <= now)
        ]
        return sorted(events, key=lambda event: event.created_at)[:limit]

    def record_integration_dispatch_result(
        self,
        event_id: UUID,
        *,
        status: IntegrationEventStatus,
        last_error: str | None,
        next_retry_at: datetime | None,
        increment_attempt: bool,
    ) -> IntegrationEventOut:
        current = self.integration_events[event_id]
        updated = current.model_copy(
            update={
                "status": status,
                "attempt_count": current.attempt_count + int(increment_attempt),
                "last_error": last_error,
                "next_retry_at": next_retry_at,
                "updated_at": datetime.now(UTC),
            }
        )
        self.integration_events[event_id] = updated
        return updated


class PostgresVectorStore:
    name = "postgres"

    def __init__(self, database_url: str, embedding_dim: int) -> None:
        self.database_url = database_url
        self.embedding_dim = embedding_dim

    def init(self) -> None:
        with self._connect() as conn:
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id uuid PRIMARY KEY,
                    source text NOT NULL,
                    text text NOT NULL,
                    metadata jsonb NOT NULL DEFAULT '{{}}',
                    embedding vector({self.embedding_dim}) NOT NULL,
                    created_at timestamptz NOT NULL DEFAULT now()
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS approval_items (
                    id uuid PRIMARY KEY,
                    kind text NOT NULL,
                    title text NOT NULL,
                    draft text NOT NULL,
                    context jsonb NOT NULL DEFAULT '{}',
                    status text NOT NULL,
                    reviewer text,
                    notes text,
                    created_at timestamptz NOT NULL DEFAULT now(),
                    updated_at timestamptz NOT NULL DEFAULT now()
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS integration_events (
                    id uuid PRIMARY KEY,
                    adapter_key text NOT NULL,
                    operation text NOT NULL,
                    idempotency_key text NOT NULL,
                    status text NOT NULL,
                    payload jsonb NOT NULL DEFAULT '{}',
                    source_approval_id uuid,
                    attempt_count integer NOT NULL DEFAULT 0,
                    last_error text,
                    next_retry_at timestamptz,
                    created_at timestamptz NOT NULL DEFAULT now(),
                    updated_at timestamptz NOT NULL DEFAULT now()
                )
                """
            )
            conn.execute("ALTER TABLE integration_events ADD COLUMN IF NOT EXISTS idempotency_key text")
            conn.execute("UPDATE integration_events SET idempotency_key = id::text WHERE idempotency_key IS NULL")
            conn.execute("ALTER TABLE integration_events ALTER COLUMN idempotency_key SET NOT NULL")
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS integration_events_idempotency_key_idx ON integration_events (idempotency_key)"
            )
            conn.execute(
                "ALTER TABLE integration_events ADD COLUMN IF NOT EXISTS attempt_count integer NOT NULL DEFAULT 0"
            )
            conn.execute(
                "ALTER TABLE integration_events ADD COLUMN IF NOT EXISTS last_error text"
            )
            conn.execute(
                "ALTER TABLE integration_events ADD COLUMN IF NOT EXISTS next_retry_at timestamptz"
            )

    def add_chunks(self, chunks: list[ChunkRecord]) -> None:
        with self._connect() as conn:
            self._delete_sources(conn, [chunk.source for chunk in chunks])
            with conn.cursor() as cur:
                for chunk in chunks:
                    cur.execute(
                        """
                        INSERT INTO document_chunks (id, source, text, metadata, embedding)
                        VALUES (%s, %s, %s, %s::jsonb, %s::vector)
                        """,
                        (
                            chunk.id,
                            chunk.source,
                            chunk.text,
                            json.dumps(chunk.metadata),
                            vector_literal(chunk.embedding),
                        ),
                    )

    def delete_sources(self, sources: list[str]) -> None:
        with self._connect() as conn:
            self._delete_sources(conn, sources)

    def _delete_sources(self, conn: psycopg.Connection[Any], sources: list[str]) -> None:
        for source in set(sources):
            conn.execute("DELETE FROM document_chunks WHERE source = %s", (source,))

    def search(self, embedding: list[float], top_k: int) -> list[RetrievedContext]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, source, text, metadata, 1 - (embedding <=> %s::vector) AS score
                FROM document_chunks
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (vector_literal(embedding), vector_literal(embedding), top_k),
            ).fetchall()
        return [
            RetrievedContext(
                id=row["id"],
                source=row["source"],
                text=row["text"],
                metadata=row["metadata"],
                score=round(float(row["score"]), 6),
            )
            for row in rows
        ]

    def create_approval(self, item: ApprovalIn) -> ApprovalOut:
        approval_id = uuid4()
        with self._connect() as conn:
            row = conn.execute(
                """
                INSERT INTO approval_items (id, kind, title, draft, context, status)
                VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                RETURNING *
                """,
                (
                    approval_id,
                    item.kind,
                    item.title,
                    item.draft,
                    json.dumps(item.context),
                    ApprovalStatus.pending.value,
                ),
            ).fetchone()
        return self._approval_from_row(row)

    def get_approval(self, item_id: UUID) -> ApprovalOut:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM approval_items WHERE id = %s",
                (item_id,),
            ).fetchone()
        if row is None:
            raise KeyError(str(item_id))
        return self._approval_from_row(row)

    def list_approvals(self, status: ApprovalStatus | None = None) -> list[ApprovalOut]:
        with self._connect() as conn:
            if status is None:
                rows = conn.execute(
                    "SELECT * FROM approval_items ORDER BY created_at ASC",
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM approval_items WHERE status = %s ORDER BY created_at ASC",
                    (status.value,),
                ).fetchall()
        return [self._approval_from_row(row) for row in rows]

    def approve(self, item_id: UUID, reviewer: str, notes: str) -> ApprovalOut:
        return self._transition(item_id, ApprovalStatus.approved, reviewer, notes)

    def reject(self, item_id: UUID, reviewer: str, notes: str) -> ApprovalOut:
        return self._transition(item_id, ApprovalStatus.rejected, reviewer, notes)

    def _transition(self, item_id: UUID, status: ApprovalStatus, reviewer: str, notes: str) -> ApprovalOut:
        with self._connect() as conn:
            row = conn.execute(
                """
                UPDATE approval_items
                SET status = %s, reviewer = %s, notes = %s, updated_at = now()
                WHERE id = %s AND status = 'pending'
                RETURNING *
                """,
                (status.value, reviewer, notes, item_id),
            ).fetchone()
        if row is None:
            raise ValueError("approval item not found or already closed")
        return self._approval_from_row(row)

    def _approval_from_row(self, row: dict[str, Any]) -> ApprovalOut:
        return ApprovalOut(
            id=row["id"],
            kind=row["kind"],
            title=row["title"],
            draft=row["draft"],
            context=row["context"],
            status=ApprovalStatus(row["status"]),
            reviewer=row["reviewer"],
            notes=row["notes"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def create_integration_event(
        self,
        *,
        adapter_key: str,
        operation: str,
        payload: dict[str, Any],
        idempotency_key: str,
        source_approval_id: UUID | None = None,
    ) -> IntegrationEventOut:
        event_id = uuid4()
        with self._connect() as conn:
            row = conn.execute(
                """
                INSERT INTO integration_events
                    (id, adapter_key, operation, idempotency_key, status, payload, source_approval_id)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)
                ON CONFLICT (idempotency_key) DO UPDATE
                SET idempotency_key = EXCLUDED.idempotency_key
                RETURNING *
                """,
                (
                    event_id,
                    adapter_key,
                    operation,
                    idempotency_key,
                    IntegrationEventStatus.queued.value,
                    json.dumps(payload),
                    source_approval_id,
                ),
            ).fetchone()
        return self._event_from_row(row)

    def get_integration_event(self, event_id: UUID) -> IntegrationEventOut:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM integration_events WHERE id = %s",
                (event_id,),
            ).fetchone()
        if row is None:
            raise KeyError(str(event_id))
        return self._event_from_row(row)

    def list_integration_events(
        self,
        adapter_key: str | None = None,
        status: IntegrationEventStatus | None = None,
    ) -> list[IntegrationEventOut]:
        with self._connect() as conn:
            if adapter_key is None and status is None:
                rows = conn.execute(
                    "SELECT * FROM integration_events ORDER BY created_at ASC",
                ).fetchall()
            elif status is None:
                rows = conn.execute(
                    "SELECT * FROM integration_events WHERE adapter_key = %s ORDER BY created_at ASC",
                    (adapter_key,),
                ).fetchall()
            elif adapter_key is None:
                rows = conn.execute(
                    "SELECT * FROM integration_events WHERE status = %s ORDER BY created_at ASC",
                    (status.value,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM integration_events
                    WHERE adapter_key = %s AND status = %s
                    ORDER BY created_at ASC
                    """,
                    (adapter_key, status.value),
                ).fetchall()
        return [self._event_from_row(row) for row in rows]

    def list_due_integration_events(
        self,
        *,
        adapter_key: str,
        now: datetime,
        limit: int,
    ) -> list[IntegrationEventOut]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM integration_events
                WHERE adapter_key = %s
                  AND status IN ('queued', 'retry')
                  AND (next_retry_at IS NULL OR next_retry_at <= %s)
                ORDER BY created_at ASC
                LIMIT %s
                """,
                (adapter_key, now, limit),
            ).fetchall()
        return [self._event_from_row(row) for row in rows]

    def record_integration_dispatch_result(
        self,
        event_id: UUID,
        *,
        status: IntegrationEventStatus,
        last_error: str | None,
        next_retry_at: datetime | None,
        increment_attempt: bool,
    ) -> IntegrationEventOut:
        with self._connect() as conn:
            row = conn.execute(
                """
                UPDATE integration_events
                SET
                    status = %s,
                    attempt_count = attempt_count + %s,
                    last_error = %s,
                    next_retry_at = %s,
                    updated_at = now()
                WHERE id = %s
                RETURNING *
                """,
                (status.value, int(increment_attempt), last_error, next_retry_at, event_id),
            ).fetchone()
        if row is None:
            raise KeyError(str(event_id))
        return self._event_from_row(row)

    def _event_from_row(self, row: dict[str, Any]) -> IntegrationEventOut:
        return IntegrationEventOut(
            id=row["id"],
            adapter_key=row["adapter_key"],
            operation=row["operation"],
            status=IntegrationEventStatus(row["status"]),
            payload=row["payload"],
            source_approval_id=row["source_approval_id"],
            idempotency_key=row["idempotency_key"],
            attempt_count=row["attempt_count"],
            last_error=row["last_error"],
            next_retry_at=row["next_retry_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self.database_url, row_factory=dict_row)


def build_store(database_url: str | None, embedding_dim: int) -> Store:
    if database_url:
        return PostgresVectorStore(database_url, embedding_dim)
    return InMemoryStore()
