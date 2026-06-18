# AI Ops Workflow Kit

[![CI](https://github.com/AlexGerlitz/ai-ops-workflow-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/AlexGerlitz/ai-ops-workflow-kit/actions/workflows/ci.yml)

Production-minded reference implementation for AI workflow orchestration around business operations:
document ingestion, RAG retrieval, transcript analysis, approval queues, and n8n/Telegram integration surfaces.

The project keeps the workflow engine thin and moves stateful logic into a backend service. n8n can own
webhooks, retries, notifications, and human-in-the-loop routing while the API owns RAG, scoring, audit-friendly
state transitions, and integration contracts.

![AI Sales Ops Control Tower](docs/assets/live-demo-control-tower.png)

## 60-Second Reviewer Snapshot

This repository is public proof for AI workflow automation work where the output must be more than a
prompt demo.

| What to check | Why it matters |
| --- | --- |
| [Live demo](https://saleops.duckdns.org/) | Public one-click proof of the deployed Sales Ops workflow. |
| [Evidence map](docs/EVIDENCE_MAP.md) | Maps the repo to AI automation, RAG, approval flow, Bitrix24, Telegram, and self-hosting requirements. |
| [Role requirements map](docs/ROLE_REQUIREMENTS_MAP.md) | Maps common AI automation vacancy requirements to exact files, endpoints, verification commands, and production boundaries. |
| [Offer demo](docs/OFFER_DEMO.md) | One-command proof of transcript -> RAG -> scoring -> Telegram approval -> idempotent outbox drain -> mock Bitrix CRM handoff. |
| [Reviewer checklist](docs/REVIEWER_CHECKLIST.md) | Single public gate for tests, offer demo, and output validation. |
| [Live demo notes](docs/LIVE_DEMO.md) | Public URLs and smoke checks for the deployed service. |
| [Architecture notes](docs/ARCHITECTURE.md) | Shows the FastAPI/n8n/PostgreSQL boundary and why stateful logic stays in the backend. |
| [Operations notes](docs/OPERATIONS.md) | Shows how the system is run, checked, and handed off. |
| [n8n approval flow](docs/N8N_APPROVAL_FLOW.md) | Shows the webhook, Telegram payload, approval callback, and CRM handoff boundary. |
| [Integration skeleton](docs/INTEGRATION_SKELETON.md) | Shows dry-run Telegram, Bitrix24, idempotency, retry scheduling, drain, opt-in worker, and dead-letter contracts before credentials are connected. |
| [Tests](tests/) | Shows deterministic coverage around chunking, retrieval, approvals, and API behavior. |
| [CI workflow](.github/workflows/ci.yml) | Shows the public verification gate. |
| `infra/n8n/` | Shows how automation/workflow tooling connects without taking over core domain state. |

Best-fit evidence:

- RAG/backend ownership: ingestion, chunking, retrieval, pgvector-ready storage, and LLM boundary;
- human-in-the-loop workflow ownership: approval queue, explicit state transitions, and Telegram/n8n
  integration shape;
- business automation ownership: transcript webhook, scoring, context capture, and review routing;
- engineering discipline: deterministic local embeddings, tests, Docker runtime, docs, and CI.

Fast evaluation path:

1. Open `https://saleops.duckdns.org/` and run the browser demo.
2. Run `bash scripts/smoke_live_demo.sh`.
3. Run `bash scripts/verify_public.sh`.
4. Read `docs/ROLE_REQUIREMENTS_MAP.md`.
5. Read `docs/EVIDENCE_MAP.md`.
6. Read `docs/OFFER_DEMO.md`.
7. Review `infra/n8n/` to see the external workflow boundary.

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
- Browser-visible Sales Ops Control Tower demo at `/`.
- RAG ingestion and retrieval with deterministic local embeddings for repeatable development.
- pgvector-ready schema and Docker Compose runtime.
- Transcript webhook that produces a structured analysis and a human approval item.
- Mock Bitrix24 CRM handoff event queued only after human approval.
- CRM outbox state with idempotency keys, attempt counters, retry scheduling, last error, and dead-letter handling.
- Optional background worker for Bitrix24 outbox drain, disabled in public dry-run mode.
- Dry-run Telegram approval and Bitrix24 dispatch contracts ready for real credentials.
- Telegram callback webhook for inline approve/reject decisions.
- Optional Telegram webhook secret verification for production callbacks.
- Approval state machine for Telegram, CRM, or internal review loops.
- n8n workflow example for webhook-to-API-to-approval routing.
- Runtime evidence endpoints for version, deploy environment, counters, and Prometheus-style metrics.
- Tests around chunking, embeddings, retrieval, and approval state transitions.

## Offer Demo

```bash
python3 -m pip install -r requirements.txt
python3 scripts/run_offer_demo.py
```

The script runs a complete synthetic sales workflow without external API keys:

```text
sales playbook -> RAG retrieval -> call transcript webhook -> AI scoring
-> follow-up approval -> Telegram callback -> outbox drain -> mock Bitrix24 CRM handoff event
```

See [docs/OFFER_DEMO.md](docs/OFFER_DEMO.md) for the reviewer path and expected output shape.

Full public verification gate:

```bash
bash scripts/verify_public.sh
```

Live deployment smoke:

```bash
bash scripts/smoke_live_demo.sh
bash scripts/smoke_live_demo.sh https://leadscore.duckdns.org
```

## Local Run

```bash
cp .env.example .env
docker compose up --build
```

Demo UI:

```text
http://127.0.0.1:8080/
```

Public demo:

```text
https://saleops.duckdns.org/
https://leadscore.duckdns.org/
```

API:

```bash
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/runtime
curl http://127.0.0.1:8080/metrics
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
| `GET /` | Browser-visible Sales Ops Control Tower demo. |
| `GET /health` | Runtime health and active storage mode. |
| `GET /runtime` | Runtime version, build SHA, deploy environment, public callback URL, integrations, worker state, and counters. |
| `GET /metrics` | Prometheus-style runtime and workflow counters. |
| `GET /integrations/runtime` | Inspect Telegram and Bitrix24 adapter configuration/dry-run status. |
| `POST /demo/run` | Run the synthetic transcript -> RAG -> approval -> Telegram/Bitrix dry-run demo. |
| `POST /documents` | Chunk and ingest text into the vector store. |
| `POST /query` | Retrieve context and produce an answer draft. |
| `POST /approvals` | Create a human-in-the-loop approval item. |
| `GET /approvals` | List approval items, optionally filtered by status. |
| `GET /approvals/{id}` | Inspect one approval item. |
| `POST /approvals/{id}/notify/telegram` | Build or send a Telegram approval message. |
| `POST /webhooks/telegram/approval` | Accept Telegram inline button callbacks and apply approve/reject decisions. |
| `POST /approvals/{id}/approve` | Approve an item and attach reviewer notes. |
| `POST /approvals/{id}/reject` | Reject an item and attach reviewer notes. |
| `GET /integration-events` | Inspect CRM/integration handoff events, optionally filtered by adapter or status. |
| `POST /integration-events/{id}/dispatch/bitrix24` | Dry-run or send a queued CRM event through Bitrix24, recording attempts and dead-letter state outside dry-run mode. |
| `POST /integrations/bitrix24/drain` | Worker-style drain for due queued/retry CRM events. |
| `POST /webhooks/n8n/call-transcript` | Accept a transcript event, score it, ingest it, and create approval work. |

## Repository Layout

```text
app/              FastAPI application, workflow domain code, and browser demo payloads
demo/             Synthetic reference playbook and transcript fixtures
infra/n8n/        Importable n8n workflow example
docs/             Offer demo, reviewer checklist, architecture, n8n, integrations and operations notes
scripts/          Reviewer-facing demo runner and public verification gate
tests/            Unit tests for the core behavior
docker-compose.yml
Dockerfile
```

## Checks

```bash
python3 -m pip install -r requirements.txt
bash scripts/verify_public.sh
```

## Design Notes

- The default local embedding provider is deterministic, so tests and development runs are stable without API keys.
- LLM calls are isolated behind a client boundary. Without `OPENAI_API_KEY`, the API returns an extractive draft from retrieved context.
- Postgres/pgvector owns durable retrieval data; n8n owns workflow routing and external connectors.
- Approval transitions are explicit and narrow: `pending -> approved` or `pending -> rejected`.
- The webhook contract is structured so Bitrix, telephony, Google Drive, or Telegram can be connected without rewriting RAG logic.
- Telegram and Bitrix24 are dry-run by default, so public checks prove payload shape without exposing secrets.
- Real Bitrix24 dispatches are recorded as integration attempts; retryable failures set `next_retry_at`, and repeated failures move the event to `dead_letter` with `last_error`.
- The Bitrix24 worker is opt-in and starts only when dry-run is disabled, so public demos cannot accidentally consume synthetic events.
- `/runtime` and `/metrics` expose deploy evidence without requiring log access.
