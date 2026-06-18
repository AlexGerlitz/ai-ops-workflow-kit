# Architecture

AI Ops Workflow Kit separates orchestration from durable application logic.

## Boundaries

| Layer | Responsibility |
| --- | --- |
| n8n | Webhooks, connector routing, retries, scheduling, Telegram notifications, CRM handoff. |
| FastAPI service | RAG ingestion/query, transcript scoring, approval state, integration contracts. |
| PostgreSQL + pgvector | Durable document chunks, metadata, vector search, approval records. |
| LLM adapter | Optional generation layer with a deterministic fallback for local operation. |
| Integration event store | Queue-style boundary for CRM handoff after human approval. |

## Core Flows

### Document Ingestion

1. A workflow receives a Google Drive, CRM, or internal content event.
2. n8n sends normalized text and metadata to `POST /documents`.
3. The API chunks the text, computes embeddings, and persists chunks.
4. Retrieval quality can be tested independently from LLM generation.

### RAG Query

1. A caller sends `POST /query`.
2. The API embeds the question.
3. The vector store returns top matching chunks.
4. The LLM adapter receives only the selected context.
5. The response includes the answer draft and source context for review.

### Call Transcript Review

1. Telephony or n8n sends a normalized transcript event.
2. The API retrieves sales-playbook context before storing the transcript.
3. The API stores the transcript as searchable context.
4. A deterministic scorer extracts basic sales signals.
5. The sales workflow layer builds a structured analysis: summary, objections, missing signals,
   next action, follow-up draft, and CRM update payload.
6. The API creates an approval item for follow-up, CRM update, or manager review.
7. n8n routes the approval item to Telegram.
8. After approval, the backend queues an integration event for the CRM adapter.

### CRM Handoff

Approval and CRM mutation are separate steps. This keeps the workflow auditable:

1. `POST /webhooks/n8n/call-transcript` creates a pending approval.
2. `POST /approvals/{id}/approve` records the reviewer decision.
3. The backend queues a `bitrix24.mock/upsert_lead_follow_up` integration event.
4. A real adapter can later send that payload to Bitrix24, retry failures, and dead-letter unsafe
   cases without changing the analysis contract.

## Production Concerns

- Keep prompts versioned and observable.
- Maintain a small evaluation set for retrieval quality.
- Track approval outcomes to improve scoring and prompt behavior.
- Keep API contracts stable; change n8n workflows at the edge.
- Prefer explicit state transitions over hidden node-level side effects.
- Queue CRM handoffs after approval so retries and audit can be handled outside the user-facing webhook.
