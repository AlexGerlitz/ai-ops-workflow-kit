from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

import psycopg
from psycopg.rows import dict_row

from app.embeddings import vector_literal
from app.schemas import ApprovalIn, ApprovalOut, ApprovalStatus, RetrievedContext


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

    def search(self, embedding: list[float], top_k: int) -> list[RetrievedContext]: ...

    def create_approval(self, item: ApprovalIn) -> ApprovalOut: ...

    def approve(self, item_id: UUID, reviewer: str, notes: str) -> ApprovalOut: ...

    def reject(self, item_id: UUID, reviewer: str, notes: str) -> ApprovalOut: ...


class InMemoryStore:
    name = "memory"

    def __init__(self) -> None:
        self.chunks: list[ChunkRecord] = []
        self.approvals: dict[UUID, ApprovalOut] = {}

    def init(self) -> None:
        return None

    def add_chunks(self, chunks: list[ChunkRecord]) -> None:
        self.chunks.extend(chunks)

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

    def add_chunks(self, chunks: list[ChunkRecord]) -> None:
        with self._connect() as conn:
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

    def _connect(self) -> psycopg.Connection:
        return psycopg.connect(self.database_url, row_factory=dict_row)


def build_store(database_url: str | None, embedding_dim: int) -> Store:
    if database_url:
        return PostgresVectorStore(database_url, embedding_dim)
    return InMemoryStore()

