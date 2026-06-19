# Technical Review Packet

This packet is for reviewers who want to evaluate whether this is a production-minded AI workflow
system rather than a ChatGPT wrapper or a no-code node chain.

## Fastest Review Path

Run the live snapshot:

```bash
python3 scripts/reviewer_snapshot.py
```

Expected high-level output:

```text
technical reviewer snapshot passed
base_url=https://saleops.duckdns.org
llm=local requested=auto fallback=True
workflow=source=gdrive://demo-sales-playbook score=100 risk=<risk-level> approval=approved telegram=dry_run bitrix24=dry_run crm=queued
```

Then run the local public gate:

```bash
python3 -m pip install -r requirements.txt
bash scripts/verify_public.sh
```

Expected result:

```text
31 passed
public verification passed
```

For a single acceptance pass across the live API, live smoke, GitHub Actions, Pages, and public PDF,
run:

```bash
python3 scripts/reviewer_acceptance_report.py
```

For a committed evidence artifact plus the regeneration command, read
[Reviewer Evidence Pack](./REVIEWER_EVIDENCE_PACK.md).
For the acceptance report route, read
[Reviewer Acceptance Report](./REVIEWER_ACCEPTANCE_REPORT.md).
For current CI, live smoke, local gate, Pages route, and public boundary status, read
[Public Proof Status](./PUBLIC_PROOF_STATUS.md).
For deterministic failure-mode evidence, read
[Production Readiness Drill](./PRODUCTION_READINESS_DRILL.md).
For the real-credential boundary, read
[Credentialed Sandbox Preflight](./CREDENTIALED_SANDBOX_PREFLIGHT.md).
For private sandbox evidence from repository secrets, inspect the live Telegram owner-run at
https://github.com/AlexGerlitz/ai-ops-workflow-kit/actions/runs/27797326178 or use the manual
`Credentialed Sandbox Preflight` GitHub Actions workflow.

## What The Snapshot Proves

| Signal | Evidence |
| --- | --- |
| Deployed service is real | `GET /runtime` returns version, Git SHA, storage mode, callback base URL, counters, and worker state. |
| LLM boundary is inspectable | `GET /llm/runtime` returns requested provider, selected provider, supported providers, required env vars, and local fallback without secrets. |
| Provider contracts exist | Tests cover OpenAI, Claude/Anthropic, and Gemini payload builders and response parsers. |
| RAG is not prompt-only | Demo imports Google Drive text, chunks it, retrieves source context, and returns `rag_context_sources`. |
| Human approval is explicit | The workflow creates a pending approval, applies an approve/reject state transition, and only then queues CRM handoff. |
| Telegram is a real contract surface | Public smoke creates a synthetic approval and verifies Telegram callback handling through `POST /webhooks/telegram/approval`. |
| Bitrix24 handoff is safe | CRM writes are modeled as idempotent outbox events with attempt counters, retry timing, and dead-letter state. |
| Bitrix24 sandbox is real | Sanitized evidence proves the incoming webhook can call read-only `profile` and CRM `crm.lead.fields`; the committed contract shows the `crm.lead.update` request body. |
| Public mode is safe | Google Drive, Telegram, and Bitrix24 stay dry-run until production credentials are configured. |
| Operations are visible | `/runtime`, `/metrics`, smoke scripts, Docker, CI, and docs give a reviewer reproducible evidence. |
| Acceptance can be checked in one pass | `scripts/reviewer_acceptance_report.py` verifies live API, smoke, GitHub Actions workflows, Pages links, and public PDF. |
| Evidence is reproducible | `scripts/capture_reviewer_evidence.py` writes a sanitized live snapshot to `docs/evidence/`. |
| Failure behavior is testable | `scripts/production_readiness_drill.py` proves webhook auth, retry/dead-letter, retry scheduling, idempotency, and worker dry-run guard. |
| Credential handoff is safe | `scripts/credentialed_sandbox_preflight.py` validates Telegram/Bitrix24 credentials through read-only calls and sanitized output. |
| Private sandbox evidence is bounded | `.github/workflows/credentialed-sandbox-preflight.yml` runs the same read-only preflight from repository secrets, checks sanitized artifacts for secret leakage, and uploads only redacted evidence; the latest Telegram sandbox run passed against `https://saleops.duckdns.org`. |

## Architecture Decisions

### Why not build everything inside n8n?

n8n is useful for webhooks, external connectors, scheduling, and human notification routing. It is
not the right place to hide durable domain state, retrieval quality, scoring rules, CRM idempotency,
or production audit. This project keeps n8n at the edge and keeps core workflow state in FastAPI and
PostgreSQL/pgvector.

### Why have a local LLM fallback?

Public review and CI must be deterministic and must not require API keys. The local extractive
fallback proves retrieval, context selection, approval routing, and integration handoff. When
`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `GEMINI_API_KEY` is configured, the same provider boundary
can route generation to the external model.

### Why return source context?

RAG quality cannot be evaluated from a final answer alone. Query responses include retrieved context
sources so a reviewer can check whether the answer was grounded in the imported Google Drive or
transcript content.

### Why queue CRM handoff?

External CRM writes should not happen inside an analysis prompt or hidden workflow node. The backend
queues a handoff event after approval, attaches an idempotency key, and records dispatch status. That
allows retry, dead-letter handling, and audit without changing the LLM/RAG contract.

## Failure Mode Coverage

| Failure mode | Current behavior |
| --- | --- |
| No LLM API key | `LLM_PROVIDER=auto` selects local fallback; `/llm/runtime` reports fallback and required env vars. |
| External LLM unavailable | Provider calls are isolated in `app/llm.py`; fallback behavior is testable and does not move workflow state into prompts. |
| Empty or weak retrieval | Query responses expose retrieved source context; tests assert RAG sources are returned. |
| Duplicate approval handoff | CRM event gets deterministic idempotency key. |
| Bitrix24 temporary failure | Dispatch records attempt count, `last_error`, `next_retry_at`, and can move to `dead_letter`. |
| Bitrix24 permission drift | Credentialed preflight checks both generic `profile` and CRM `crm.lead.fields`, so missing CRM scope is visible before enabling writes. |
| Unsafe public integration writes | Google Drive, Telegram, and Bitrix24 are dry-run by default. |
| Background worker accidentally mutates demo data | Worker starts only when explicitly enabled and Bitrix24 dry-run is disabled. |
| Telegram callback spoofing in production | Webhook secret support is available through `TELEGRAM_WEBHOOK_SECRET`. |
| Deployment drift | `/runtime` exposes deployed Git SHA, version, worker state, integration state, and counters. |

## Production Rollout Checklist

Before connecting real business data:

1. Use PostgreSQL with pgvector enabled.
2. Configure `PUBLIC_BASE_URL` to the production HTTPS URL.
3. Configure one or more LLM provider keys and verify `GET /llm/runtime`.
4. Configure Google Drive export in n8n or a connector and send normalized text to `POST /integrations/google-drive/import`.
5. Configure Telegram bot token and webhook secret; run `scripts/configure_telegram_webhook.sh`.
6. Configure Bitrix24 webhook URL and field mapping.
7. Run `python3 scripts/credentialed_sandbox_preflight.py --require-credentials`.
8. Keep `BITRIX24_DRY_RUN=true` for the first payload validation pass.
9. Run `bash scripts/verify_public.sh`.
10. Run `bash scripts/smoke_live_demo.sh <production-url>`.
11. Disable dry-run only after the payload map, approval policy, and rollback path are reviewed.
12. Enable the Bitrix24 outbox worker only after dry-run validation.
13. Monitor `/runtime`, `/metrics`, API logs, and dead-letter counts during rollout.

## Review Commands

```bash
python3 scripts/capture_reviewer_evidence.py
python3 scripts/reviewer_snapshot.py
python3 scripts/production_readiness_drill.py
python3 scripts/credentialed_sandbox_preflight.py
python3 scripts/credentialed_sandbox_preflight.py --require-target telegram
python3 scripts/credentialed_sandbox_preflight.py --require-target bitrix24
python3 scripts/bitrix24_contract_evidence.py
python3 scripts/reviewer_snapshot.py https://leadscore.duckdns.org
bash scripts/smoke_live_demo.sh
bash scripts/smoke_live_demo.sh https://leadscore.duckdns.org
bash scripts/verify_public.sh
curl -fsS https://saleops.duckdns.org/runtime
curl -fsS https://saleops.duckdns.org/llm/runtime
curl -fsS https://saleops.duckdns.org/metrics
```

For local Docker review:

```bash
cp .env.example .env
docker compose up --build
python3 scripts/reviewer_snapshot.py http://127.0.0.1:8080
```

## Main Files To Inspect

| File | Reason |
| --- | --- |
| `app/main.py` | API boundary, demo route, runtime endpoints, approvals, webhooks, and integration handoff. |
| `app/llm.py` | OpenAI, Claude/Anthropic, Gemini, and local fallback provider boundary. |
| `app/store.py` | In-memory/PostgreSQL storage boundary, approvals, and integration events. |
| `app/sales_workflow.py` | Transcript analysis, scoring context, approval payload, and CRM payload shape. |
| `app/integrations.py` | Google Drive, Telegram, and Bitrix24 adapter contracts. |
| `infra/n8n/` | Importable workflow artifacts that keep n8n as orchestration glue. |
| `tests/` | Deterministic coverage for RAG, LLM provider contracts, approvals, webhooks, outbox, and worker behavior. |

## Public Demo Boundary

The public deployment is intentionally credential-free:

- no real customer calls;
- no real Google Drive credentials;
- no real Telegram token in the repository;
- no real Bitrix24 writes;
- no LLM API keys exposed.

The point of the public demo is to prove architecture, contracts, state transitions, observability,
and deployment readiness without leaking secrets or mutating external systems.
