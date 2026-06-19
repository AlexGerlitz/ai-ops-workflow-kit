# Architecture

AI Ops Workflow Kit separates orchestration from durable application logic.

## Boundaries

| Layer | Responsibility |
| --- | --- |
| n8n | Webhooks, connector routing, scheduling, Telegram notifications, and external workflow edges. |
| FastAPI service | Google Drive import, RAG ingestion/query, call-audio transcription boundary, transcript scoring, approval state, integration contracts. |
| PostgreSQL + pgvector | Durable document chunks, metadata, vector search, approval records. |
| LLM adapter | Provider boundary for OpenAI, Claude/Anthropic, Gemini, and deterministic local fallback. |
| Transcription adapter | Provider boundary for local fixture, OpenAI Whisper, and Deepgram/diarization contracts. |
| Integration event store | Idempotent outbox boundary for CRM handoff after human approval. |
| Integration adapters | Dry-run or real Google Drive import, Telegram approval, and Bitrix24 dispatch clients. |

## Core Flows

### Document Ingestion

1. A workflow receives a Google Drive, CRM, or internal content event.
2. For Drive-backed knowledge, n8n or a connector exports text and sends it to
   `POST /integrations/google-drive/import`.
3. Generic content can still use `POST /documents`.
4. The API chunks the text, computes embeddings, and persists chunks with source metadata.
5. Retrieval quality can be tested independently from LLM generation.

### RAG Query

1. A caller sends `POST /query`.
2. The API embeds the question.
3. The vector store returns top matching chunks.
4. The LLM adapter receives only the selected context and routes it through the selected provider boundary.
5. The response includes the answer draft and source context for review.

`GET /llm/runtime` exposes the requested provider, selected provider, configured provider names, and
required environment variables without exposing secrets. This keeps provider wiring inspectable in
public demos while API keys stay in deployment configuration.

### Call Audio To Transcript

1. Telephony, Google Drive, or n8n sends call audio metadata to `POST /webhooks/n8n/call-audio`.
2. The API selects the transcription provider: deterministic local fixture for public demos, or an
   OpenAI Whisper/Deepgram contract when configured.
3. The transcription adapter returns normalized transcript text, speaker segments, language,
   duration, status, and the provider request contract without leaking secrets.
4. The API stores audio provenance in transcript metadata and continues into the same transcript
   analysis path.

`GET /transcription/runtime` exposes the requested provider, selected provider, supported providers,
required environment variables, and dry-run state. Public mode does not call external audio services;
it proves the boundary and the downstream business workflow.

### Call Transcript Review

1. Telephony, n8n, or the call-audio route sends a normalized transcript event.
2. The API retrieves sales-playbook context before storing the transcript.
3. The API stores the transcript as searchable context.
4. A deterministic scorer extracts basic sales signals.
5. The sales workflow layer builds a structured analysis: summary, objections, missing signals,
   next action, follow-up draft, and CRM update payload.
6. The API creates an approval item for follow-up, CRM update, or manager review.
7. n8n routes the approval item to Telegram.
8. After approval, the backend queues an integration event for the CRM adapter.

The backend also exposes `POST /approvals/{id}/notify/telegram` for a direct Telegram approval
adapter path. In public mode it returns the exact outgoing payload in dry-run mode.

### CRM Handoff

Approval and CRM mutation are separate steps. This keeps the workflow auditable:

1. `POST /webhooks/n8n/call-audio` or `POST /webhooks/n8n/call-transcript` creates a pending approval.
2. `POST /approvals/{id}/approve` records the reviewer decision.
3. The backend queues a `bitrix24.mock/upsert_lead_follow_up` integration event.
4. The event has a deterministic idempotency key so repeated approval handoff code does not create
   duplicate CRM writes.
5. A real adapter can later send that payload to Bitrix24, schedule retries with `next_retry_at`,
   and dead-letter unsafe cases without changing the analysis contract.

The skeleton endpoint `POST /integration-events/{id}/dispatch/bitrix24` maps the internal handoff
event into a Bitrix24 REST payload. It is dry-run by default until `BITRIX24_DRY_RUN=false` and
`BITRIX24_WEBHOOK_URL` are configured.

The worker-style endpoint `POST /integrations/bitrix24/drain` processes due `queued` and `retry`
events. Dry-run drain proves the queue surface without consuming attempts; production drain records
attempt counts, last error, next retry time, and dead-letter state.

An optional in-process worker can call the same drain path on an interval. It starts only when
`INTEGRATION_WORKER_ENABLED=true` and `BITRIX24_DRY_RUN=false`, which keeps public/demo environments
inspectable without accidentally consuming synthetic events.

## Production Concerns

- Keep prompts and provider payload contracts versioned and observable.
- Maintain a small evaluation set for retrieval quality.
- Track approval outcomes to improve scoring and prompt behavior.
- Keep API contracts stable; change n8n workflows at the edge.
- Prefer explicit state transitions over hidden node-level side effects.
- Queue CRM handoffs after approval so idempotency, retry timing, dead-letter state, and audit can
  be handled outside the user-facing webhook.
- Keep background workers explicit and observable through runtime metadata.
- Keep speech-to-text as an adapter boundary so Whisper, Deepgram, storage signed URLs, and
  diarization quality can evolve without rewriting the sales workflow.
