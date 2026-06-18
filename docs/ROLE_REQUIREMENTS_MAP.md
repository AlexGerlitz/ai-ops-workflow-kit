# AI Automation Role Requirements Map

This map connects common AI automation role requirements to concrete proof in this repository.
It is written for technical reviewers who want to verify implementation depth instead of reading
generic AI claims.

## Requirement To Evidence

| Role requirement | Evidence in this repo | How to verify | Production boundary |
| --- | --- | --- | --- |
| AI workflow orchestration | `POST /webhooks/n8n/call-transcript`, `infra/n8n/call-transcript-approval.json`, `infra/n8n/google-drive-sales-ops-approval.json`, `docs/N8N_APPROVAL_FLOW.md` | Open the n8n workflow JSON files, then run `bash scripts/verify_public.sh`. | n8n owns routing, Drive export, and notifications; the backend owns state, scoring, retrieval, approvals, and integration contracts. |
| LLM API integration boundary | `app/llm.py`, `GET /llm/runtime`, `tests/test_api.py`, `docs/OFFER_DEMO.md` | Run `bash scripts/verify_public.sh`, then inspect `/llm/runtime`. | The demo uses deterministic local behavior for public review; OpenAI, Claude/Anthropic, and Gemini payload contracts are isolated behind one provider boundary without moving workflow state into prompts. |
| RAG and embeddings | `app/chunking.py`, `app/embeddings.py`, `app/store.py`, `POST /documents`, `POST /query` | Run `bash scripts/verify_public.sh` and inspect the demo output for `rag_context_sources`. | Deterministic local embeddings keep tests repeatable; PostgreSQL/pgvector is the durable runtime path. |
| Google Drive API / document intake | `POST /integrations/google-drive/import`, `GoogleDriveImportIn`, `infra/n8n/google-drive-sales-ops-approval.json`, `app/integrations.py`, `docs/INTEGRATION_SKELETON.md` | Run `bash scripts/verify_public.sh` and inspect `google_drive_import` in the offer demo output. | Public mode accepts exported Drive document text without credentials; production mode connects OAuth/service-account export in n8n or a connector and sends normalized text to the backend. |
| PostgreSQL, Supabase, pgvector readiness | `docker-compose.yml`, `app/store.py`, `docs/ARCHITECTURE.md`, `docs/OPERATIONS.md` | Run `docker compose up --build`, then open `/runtime`, `/documents`, and `/query`. | The public demo can run in memory for inspectability; the storage boundary is designed around PostgreSQL with pgvector. |
| Transcript ingestion and call analysis | `demo/call-transcript.json`, `app/sales_workflow.py`, `app/scoring.py`, `POST /webhooks/n8n/call-transcript` | Run the offer demo or send the sample transcript to the n8n webhook endpoint. | Transcript analysis produces structured fields, score, risk level, next action, and approval context instead of free-form text only. |
| AI scoring and content routing | `app/scoring.py`, `app/sales_workflow.py`, approval payload context | Run `python3 scripts/run_offer_demo.py` and inspect `call_analysis.score`, `risk_level`, and `next_action`. | Scoring is explicit and testable; it can later be replaced or calibrated without changing the approval and CRM contracts. |
| Telegram approval bot flow | `POST /approvals/{id}/notify/telegram`, `POST /webhooks/telegram/approval`, `scripts/configure_telegram_webhook.sh`, `docs/INTEGRATION_SKELETON.md` | Run `bash scripts/smoke_live_demo.sh` and confirm `telegram_callback=rejected`. | Public mode builds dry-run Telegram payloads; production mode can require `X-Telegram-Bot-Api-Secret-Token` for webhook callbacks. |
| Bitrix24 / CRM handoff | `POST /integration-events/{id}/dispatch/bitrix24`, `POST /integrations/bitrix24/drain`, `app/integrations.py`, `app/store.py` | Run the offer demo and inspect `crm_handoff`, `bitrix24_dispatch`, and outbox state. | CRM writes are queued after approval with idempotency keys, attempts, retry timing, last error, and dead-letter state. |
| Approval flow and human review | `POST /approvals`, `POST /approvals/{id}/approve`, `POST /approvals/{id}/reject`, `tests/test_core.py` | Run `bash scripts/verify_public.sh`; inspect approval tests and API endpoints. | Risky external actions happen only after explicit state transitions. |
| Production-ready deployment | `Dockerfile`, `docker-compose.yml`, `.github/workflows/ci.yml`, `scripts/verify_public.sh`, `scripts/smoke_live_demo.sh`, `docs/OPERATIONS.md` | Open the latest CI run and run the public smoke command against `https://saleops.duckdns.org`. | The app exposes health, runtime identity, metrics, public callback base URL, integration readiness, and worker state. |
| Self-host / cloud operation | `docs/LIVE_DEMO.md`, `docs/OPERATIONS.md`, `/runtime`, `/metrics` | Run `curl -fsS https://saleops.duckdns.org/runtime` and `curl -fsS https://saleops.duckdns.org/metrics`. | The live demo is deployed behind HTTPS; secrets are not committed and integrations stay dry-run until credentials are configured. |
| AI architecture beyond node wiring | `docs/ARCHITECTURE.md`, `docs/EVIDENCE_MAP.md`, backend state model, outbox model | Review the architecture docs and source boundaries in `app/`. | Workflow tooling is kept thin. Durable state, audit, retries, validation, and integration contracts live in code with tests. |

## Fast Verification Commands

```bash
python3 -m pip install -r requirements.txt
bash scripts/verify_public.sh
bash scripts/smoke_live_demo.sh https://saleops.duckdns.org
bash scripts/smoke_live_demo.sh https://leadscore.duckdns.org
curl -fsS https://saleops.duckdns.org/runtime
curl -fsS https://saleops.duckdns.org/llm/runtime
```

Expected local gate result:

```text
24 passed
public verification passed
```

Expected live smoke signals:

```text
live demo smoke passed
llm=local
score=100
google_drive=gdrive://demo-sales-playbook
approval=approved
telegram_callback=rejected
bitrix24_drain=<positive dry-run drain count>
```

## Known Public Demo Boundaries

- Google Drive, Telegram, and Bitrix24 are dry-run by default so reviewers can inspect contracts without credentials.
- Google Drive import is dry-run/public-safe: the demo accepts exported text and metadata, not live Drive credentials.
- The public demo does not store real customer calls, CRM data, bot tokens, or Google credentials.
- The Bitrix24 outbox worker is visible but disabled in the public dry-run deployment.
- Local deterministic embeddings are intentional for repeatable review; PostgreSQL/pgvector is the durable storage path.
- `LLM_PROVIDER=auto` selects a configured OpenAI, Claude/Anthropic, or Gemini API key; without keys the public demo uses the local extractive fallback.
- Production integrations require server-side secrets, webhook verification, rollout notes, and real CRM field mapping.

## What A Reviewer Should Conclude

This is not a ChatGPT wrapper. The repository demonstrates an AI workflow system with backend-owned
state, Google Drive document intake, RAG boundaries, approval transitions, Telegram callback handling,
OpenAI/Claude/Gemini provider boundaries, CRM outbox semantics, runtime evidence, Docker deployment,
CI, and public smoke checks.
