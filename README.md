# AI Ops Workflow Kit

Production-minded reference implementation for AI workflow orchestration around business operations:
document ingestion, RAG retrieval, transcript analysis, approval queues, and n8n/Telegram integration surfaces.

The project keeps the workflow engine thin and moves stateful logic into a backend service. n8n can own
webhooks, retries, notifications, and human-in-the-loop routing while the API owns RAG, scoring, audit-friendly
state transitions, and integration contracts.

## System Shape

```mermaid
flowchart LR
  Drive[Google Drive / CRM / transcripts] --> N8N[n8n workflows]
  Telegram[Telegram approval bot] <--> N8N
  N8N --> API[FastAPI workflow API]
  API --> Vector[(PostgreSQL + pgvector)]
  API --> LLM[LLM API adapter]
  API --> Queue[Approval queue]
  Queue --> N8N
```

## What It Demonstrates

- FastAPI service boundary for AI workflow orchestration.
- RAG ingestion and retrieval with deterministic local embeddings for repeatable development.
- pgvector-ready schema and Docker Compose runtime.
- Transcript webhook that produces a structured analysis and a human approval item.
- Approval state machine for Telegram, CRM, or internal review loops.
- n8n workflow example for webhook-to-API-to-approval routing.
- Tests around chunking, embeddings, retrieval, and approval state transitions.

## Local Run

```bash
cp .env.example .env
docker compose up --build
```

API:

```bash
curl http://127.0.0.1:8080/health
```

Ingest a document:

```bash
curl -X POST http://127.0.0.1:8080/documents \
  -H 'content-type: application/json' \
  -d '{"source":"drive://sales-playbook","text":"Discovery calls should confirm budget, authority, need, timing, and next step.","metadata":{"team":"sales"}}'
```

Ask a RAG-backed question:

```bash
curl -X POST http://127.0.0.1:8080/query \
  -H 'content-type: application/json' \
  -d '{"question":"What should be confirmed during discovery calls?","top_k":3}'
```

Create an approval item:

```bash
curl -X POST http://127.0.0.1:8080/approvals \
  -H 'content-type: application/json' \
  -d '{"kind":"content_review","title":"Approve generated follow-up","draft":"Send a follow-up with budget, timeline, and next step.","context":{"lead_id":"L-1024"}}'
```

## API Surface

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Runtime health and active storage mode. |
| `POST /documents` | Chunk and ingest text into the vector store. |
| `POST /query` | Retrieve context and produce an answer draft. |
| `POST /approvals` | Create a human-in-the-loop approval item. |
| `POST /approvals/{id}/approve` | Approve an item and attach reviewer notes. |
| `POST /approvals/{id}/reject` | Reject an item and attach reviewer notes. |
| `POST /webhooks/n8n/call-transcript` | Accept a transcript event, score it, ingest it, and create approval work. |

## Repository Layout

```text
app/              FastAPI application and workflow domain code
infra/n8n/        Importable n8n workflow example
docs/             Architecture and operations notes
tests/            Unit tests for the core behavior
docker-compose.yml
Dockerfile
```

## Checks

```bash
python -m pip install -r requirements.txt
pytest -q
```

## Design Notes

- The default local embedding provider is deterministic, so tests and development runs are stable without API keys.
- LLM calls are isolated behind a client boundary. Without `OPENAI_API_KEY`, the API returns an extractive draft from retrieved context.
- Postgres/pgvector owns durable retrieval data; n8n owns workflow routing and external connectors.
- Approval transitions are explicit and narrow: `pending -> approved` or `pending -> rejected`.
- The webhook contract is structured so Bitrix, telephony, Google Drive, or Telegram can be connected without rewriting RAG logic.

