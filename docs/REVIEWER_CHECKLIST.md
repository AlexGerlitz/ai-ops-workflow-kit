# Reviewer Checklist

This checklist is the fastest way to verify that AI Ops Workflow Kit is more than a prompt wrapper.

## 1. Run The Live Reviewer Snapshot

```bash
python3 scripts/reviewer_snapshot.py
```

Expected result:

```text
technical reviewer snapshot passed
```

The snapshot checks the public deployment, `/runtime`, `/llm/runtime`, `/integrations/runtime`,
`/metrics`, and `/demo/run`. It summarizes the deployed Git SHA, selected LLM provider, supported
providers, Google Drive/RAG source, score, approval state, Telegram dry-run state, Bitrix24 dry-run
state, CRM idempotency key, worker state, and metrics availability.

Read: [Technical Review Packet](./TECHNICAL_REVIEW_PACKET.md).

## 2. Run The Public Gate

```bash
python3 -m pip install -r requirements.txt
bash scripts/verify_public.sh
```

Expected result:

```text
24 passed
public verification passed
```

The gate runs the test suite, runs the offer demo, parses the demo output, and asserts that the
workflow produced:

- RAG context sources;
- Google Drive import into the same RAG store;
- OpenAI, Claude/Anthropic, Gemini, and local fallback provider boundary;
- transcript score;
- structured call analysis;
- approved human review item;
- dry-run Telegram approval payload;
- Telegram callback webhook for inline approve/reject decisions;
- optional Telegram webhook secret verification;
- queued `bitrix24.mock` CRM handoff.
- dry-run Bitrix24 dispatch payload.
- Bitrix24 idempotency, retry scheduling, drain, opt-in worker, and dead-letter state for failed production dispatches.
- runtime identity and metrics surface.

## 3. Inspect The Offer Demo

```bash
python3 scripts/run_offer_demo.py
```

The demo does not require Docker or external API keys. It uses deterministic local embeddings and
in-memory storage so the reviewer can inspect the behavior quickly.

Read: [Offer Demo](./OFFER_DEMO.md).

## 4. Inspect The Live Demo

Open:

- Sales Ops Control Tower: https://saleops.duckdns.org/
- Lead score alias: https://leadscore.duckdns.org/

Or run:

```bash
python3 scripts/reviewer_snapshot.py
bash scripts/smoke_live_demo.sh
```

Read: [Live Demo](./LIVE_DEMO.md).

## 5. Inspect The Browser Demo Locally

Run the API and open the one-click demo surface:

```bash
docker compose up --build
```

Then open:

- Sales Ops Control Tower: http://127.0.0.1:8080/

## 6. Inspect The Runtime Boundary

Run the Docker stack when you want to inspect the API with PostgreSQL/pgvector and n8n:

```bash
cp .env.example .env
docker compose up --build
```

Then open:

- API health: http://127.0.0.1:8080/health
- Runtime evidence: http://127.0.0.1:8080/runtime
- LLM provider evidence: http://127.0.0.1:8080/llm/runtime
- Metrics: http://127.0.0.1:8080/metrics
- FastAPI docs: http://127.0.0.1:8080/docs
- n8n UI: http://127.0.0.1:5678

## 7. Review The Engineering Decisions

| File | What to check |
| --- | --- |
| [README](../README.md) | Reviewer snapshot, API surface, repository layout, and checks. |
| [Technical Review Packet](./TECHNICAL_REVIEW_PACKET.md) | Live snapshot, architecture decisions, failure modes, production rollout checklist, and public demo boundary. |
| [Evidence Map](./EVIDENCE_MAP.md) | Requirement-by-requirement proof map for AI automation roles. |
| [Role Requirements Map](./ROLE_REQUIREMENTS_MAP.md) | Vacancy-style AI automation requirements mapped to files, endpoints, commands, and production boundaries. |
| [Live Demo](./LIVE_DEMO.md) | Public deployment URL and public smoke checks. |
| [Architecture](./ARCHITECTURE.md) | FastAPI/n8n/PostgreSQL/LLM boundaries and state ownership. |
| [Operations](./OPERATIONS.md) | Local runtime, health checks, smoke test, logs, and handoff. |
| [n8n Approval Flow](./N8N_APPROVAL_FLOW.md) | How importable transcript and Google Drive workflow routing, Telegram payloads, and approval callbacks connect. |
| [Integration Skeleton](./INTEGRATION_SKELETON.md) | How Google Drive, Telegram, and Bitrix24 dry-run contracts become real credentials later. |
| [Tests](../tests/) | Deterministic coverage for retrieval, scoring, approval, CRM handoff, idempotency, drain, background worker, and integration retry/dead-letter behavior. |

## 8. What This Proves

- AI workflow logic is backend-owned and testable.
- The project has a browser-visible demo, not only README claims.
- n8n is used as orchestration glue and connector routing, not as hidden domain logic.
- LLM/RAG behavior has deterministic local fallbacks and OpenAI/Claude/Gemini provider contracts for repeatable review.
- CRM mutation is queued only after explicit human approval.
- CRM dispatch failures become retry/dead-letter state with `next_retry_at`, not invisible log-only errors.
- Google Drive, Telegram, and Bitrix24 adapters expose dry-run contracts before credentials are connected.
- Telegram inline callbacks have a backend endpoint that applies approve/reject state transitions.
- Production Telegram callbacks can be protected with `X-Telegram-Bot-Api-Secret-Token`.
- Runtime and metrics endpoints expose deploy identity and workflow counters.
- `/llm/runtime` exposes provider state without exposing secrets.
- Runtime exposes whether the Bitrix24 outbox worker is enabled and active.
- The project has a public verification command and CI gate.
