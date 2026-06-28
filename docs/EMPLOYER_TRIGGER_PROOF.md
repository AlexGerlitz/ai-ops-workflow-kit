# Employer Trigger Proof

This page maps the hiring and project triggers from the public profile route to concrete, inspectable proof in this repository.

Use it when the first question is not "what does the demo do?" but "what employer problem can this prove quickly?"

## Current Freshness

- Last checked: 2026-06-28.
- Current CI route: https://github.com/AlexGerlitz/ai-ops-workflow-kit/actions/workflows/ci.yml.
- Local public gate: `PYTHON_BIN=.venv/bin/python bash scripts/verify_public.sh` -> `49 passed`, `public verification passed`.
- Visual proof route: `docs/DEMO_WALKTHROUGH.md` with `docs/assets/drive-operator-demo.gif`.

## Trigger To Proof

| Employer trigger | Employer pain | Proof in this repo | First result this repo demonstrates |
| --- | --- | --- | --- |
| AI workflow / RAG | Documents, transcripts, calls, or leads need retrieval, structured analysis, scoring, and human approval. | `POST /demo/run`, `POST /rag/eval`, `app/rag_eval.py`, `app/sales_workflow.py`, `docs/OFFER_DEMO.md`, and `infra/n8n/call-audio-transcription-approval.json`. | One backend-owned workflow slice with document intake, RAG citations, transcript analysis, score/risk/next action, approval state, tests, logs, and operator handoff. |
| CRM/ERP/API integration | Business systems are connected through brittle manual steps, hidden automation state, or unclear ownership. | `app/integrations.py`, `app/store.py`, `POST /integration-events/{id}/dispatch/bitrix24`, `POST /integrations/bitrix24/drain`, `docs/LIVE_OWNER_PROOF.md`, and `docs/evidence/bitrix24-contract.txt`. | Adapter contract, idempotent CRM handoff, queued outbox state, retries/dead-letter behavior, audit trail, and rollback notes before enabling real writes. |
| Backend/platform ownership | The team needs records, state, API contracts, approval boundaries, integration boundaries, and runtime clarity. | `app/main.py`, `app/store.py`, `app/schemas.py`, `docker-compose.yml`, `GET /runtime`, `GET /metrics`, `docs/ARCHITECTURE.md`, and `docs/ROLE_REQUIREMENTS_MAP.md`. | FastAPI/PostgreSQL-ready slice with typed records, explicit state transitions, API contract, runtime identity, metrics, CI, docs, and demo route. |
| DevOps / reliability | A workflow needs Docker, health checks, smoke tests, public-safe evidence, recovery behavior, and a runbook. | `.github/workflows/ci.yml`, `scripts/verify_public.sh`, `scripts/reviewer_acceptance_report.py`, `scripts/production_readiness_drill.py`, `docs/PRODUCTION_READINESS_DRILL.md`, and `docs/OPERATIONS.md`. | Verified deployment/recovery path with public gate, live smoke route, failure-mode drill, metrics/log notes, runbook, and release gate. |

## Fast Verification Path

```bash
python3 -m pip install -r requirements.txt
bash scripts/verify_public.sh
python3 scripts/run_offer_demo.py
python3 scripts/production_readiness_drill.py
```

Expected local gate:

```text
49 passed
public verification passed
```

Expected workflow signals:

```text
rag_quality.ok=true
passed=2/2
privacy.redacted=True
approval.status=approved
crm_handoff.status=queued
bitrix24_dispatch.status=dry_run
```

## Review Boundary

- The public demo proves contracts, state, RAG quality, approval flow, outbox handoff, privacy redaction, and failure behavior without real customer data.
- n8n stays at the orchestration edge; backend code owns durable state, scoring, retrieval, approvals, adapter contracts, retries, and audit-friendly records.
- Telegram and Bitrix24 live credentials are handled through owner-run or manual sandbox checks; public synthetic review remains dry-run and secret-free.
- The strongest first paid or role slice is an AI workflow where one messy document/transcript/lead path becomes a verified backend-owned system with tests, logs, docs, and handoff.
