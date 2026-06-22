# AI Automation Role Requirements Map

This map connects common AI automation role requirements to concrete proof in this repository.
It is written for technical reviewers who want to verify implementation depth instead of reading
generic AI claims.

## Requirement To Evidence

| Role requirement | Evidence in this repo | How to verify | Production boundary |
| --- | --- | --- | --- |
| AI workflow orchestration | `POST /webhooks/n8n/call-audio`, `POST /webhooks/n8n/call-transcript`, `infra/n8n/call-audio-transcription-approval.json`, `infra/n8n/call-transcript-approval.json`, `infra/n8n/google-drive-sales-ops-approval.json`, `docs/N8N_APPROVAL_FLOW.md` | Open the n8n workflow JSON files, then run `bash scripts/verify_public.sh`. | n8n owns routing, Drive export, and notifications; the backend owns transcription, state, scoring, retrieval, approvals, and integration contracts. |
| LLM API integration boundary | `app/llm.py`, `GET /llm/runtime`, `tests/test_api.py`, `docs/OFFER_DEMO.md` | Run `bash scripts/verify_public.sh`, then inspect `/llm/runtime`. | The demo uses deterministic local behavior for public review; OpenAI, Claude/Anthropic, and Gemini payload contracts are isolated behind one provider boundary without moving workflow state into prompts. |
| RAG and embeddings | `app/chunking.py`, `app/embeddings.py`, `app/store.py`, `POST /documents`, `POST /query` | Run `bash scripts/verify_public.sh` and inspect the demo output for `rag_context_sources`. | Deterministic local embeddings keep tests repeatable; PostgreSQL/pgvector is the durable runtime path. |
| Document intake / Google Drive API adapter | `POST /integrations/google-drive/import`, `GoogleDriveImportIn`, `infra/n8n/google-drive-sales-ops-approval.json`, `app/integrations.py`, `docs/INTEGRATION_SKELETON.md` | Run `bash scripts/verify_public.sh` and inspect `google_drive_import` in the offer demo output. | Public mode accepts exported Drive document text without credentials; production mode connects OAuth/service-account export in n8n or a connector and sends normalized text to the backend. |
| PostgreSQL, Supabase, pgvector readiness | `docker-compose.yml`, `app/store.py`, `docs/ARCHITECTURE.md`, `docs/OPERATIONS.md` | Run `docker compose up --build`, then open `/runtime`, `/documents`, and `/query`. | The public demo can run in memory for inspectability; the storage boundary is designed around PostgreSQL with pgvector. |
| Whisper / Deepgram / diarization boundary | `app/transcription.py`, `GET /transcription/runtime`, `POST /webhooks/n8n/call-audio`, `infra/n8n/call-audio-transcription-approval.json`, `tests/test_api.py` | Run `bash scripts/verify_public.sh`, inspect `/transcription/runtime`, and send a payload with `audio_uri` plus `transcript_hint` to `/webhooks/n8n/call-audio`. | Public mode uses a deterministic local fixture without secrets; live mode calls OpenAI Whisper or Deepgram, parses text/speaker segments, and keeps downstream transcript analysis unchanged. |
| Transcript ingestion and call analysis | `demo/call-transcript.json`, `app/sales_workflow.py`, `app/scoring.py`, `POST /webhooks/n8n/call-transcript` | Run the offer demo or send the sample transcript to the n8n webhook endpoint. | Transcript analysis produces structured fields, score, risk level, next action, and approval context instead of free-form text only. |
| AI scoring and content routing | `app/scoring.py`, `app/sales_workflow.py`, approval payload context | Run `python3 scripts/run_offer_demo.py` and inspect `call_analysis.score`, `risk_level`, and `next_action`. | Scoring is explicit and testable; it can later be replaced or calibrated without changing the approval and CRM contracts. |
| Telegram approval bot flow | `POST /approvals/{id}/notify/telegram`, `POST /webhooks/telegram/approval`, `scripts/configure_telegram_webhook.sh`, `docs/INTEGRATION_SKELETON.md`, `docs/LIVE_OWNER_PROOF.md`, `docs/evidence/live-telegram-approval.sanitized.json`, `docs/evidence/credentialed-sandbox-preflight.sanitized.json` | Run `bash scripts/smoke_live_demo.sh` and confirm `telegram_callback=rejected`; inspect `docs/evidence/live-telegram-approval.txt` for the real Telegram approval callback. | The synthetic public demo builds dry-run Telegram payloads; operator-triggered approvals can send to the real bot, repeated taps are idempotent, and production mode can require `X-Telegram-Bot-Api-Secret-Token`. |
| Bitrix24 / CRM handoff | `POST /integration-events/{id}/dispatch/bitrix24`, `POST /integrations/bitrix24/drain`, `app/integrations.py`, `app/store.py`, `docs/evidence/bitrix24-contract.sanitized.json`, `docs/evidence/bitrix24-sandbox-preflight.sanitized.json` | Run the offer demo, inspect `crm_handoff`, `bitrix24_dispatch`, and run `python3 scripts/bitrix24_contract_evidence.py`; read the Bitrix24 sandbox artifact for `profile=passed` and `crm_lead_fields=passed`. | CRM writes are queued after approval with idempotency keys, attempts, retry timing, last error, and dead-letter state; the real sandbox proof is read-only and production writes remain gated. |
| Approval flow and human review | `POST /approvals`, `POST /approvals/{id}/approve`, `POST /approvals/{id}/reject`, `tests/test_core.py` | Run `bash scripts/verify_public.sh`; inspect approval tests and API endpoints. | Risky external actions happen only after explicit state transitions. |
| Production-ready deployment | `Dockerfile`, `docker-compose.yml`, `.github/workflows/ci.yml`, `.github/workflows/credentialed-sandbox-preflight.yml`, `scripts/verify_public.sh`, `scripts/reviewer_acceptance_report.py`, `scripts/smoke_live_demo.sh`, `scripts/capture_reviewer_evidence.py`, `scripts/production_readiness_drill.py`, `scripts/credentialed_sandbox_preflight.py`, `docs/OPERATIONS.md` | Open the latest CI run, run the public acceptance report, run the public smoke command against `https://saleops.duckdns.org`, regenerate `docs/evidence/reviewer-snapshot.sanitized.json`, run the production readiness drill, run the credentialed sandbox preflight, and use the manual preflight workflow when repository secrets exist. | The app exposes health, runtime identity, metrics, public callback base URL, integration readiness, worker state, reproducible evidence, failure-mode behavior, read-only credential boundary checks, owner-run sanitized sandbox evidence, and one-command public acceptance evidence. |
| Self-host / cloud operation | `docs/LIVE_DEMO.md`, `docs/OPERATIONS.md`, `/runtime`, `/metrics` | Run `curl -fsS https://saleops.duckdns.org/runtime` and `curl -fsS https://saleops.duckdns.org/metrics`. | The live demo is deployed behind HTTPS; secrets are not committed and integrations stay dry-run until credentials are configured. |
| AI architecture beyond node wiring | `docs/ARCHITECTURE.md`, `docs/EVIDENCE_MAP.md`, backend state model, outbox model | Review the architecture docs and source boundaries in `app/`. | Workflow tooling is kept thin. Durable state, audit, retries, validation, and integration contracts live in code with tests. |

## Fast Verification Commands

```bash
python3 -m pip install -r requirements.txt
bash scripts/verify_public.sh
python3 scripts/reviewer_acceptance_report.py
python3 scripts/capture_reviewer_evidence.py
python3 scripts/production_readiness_drill.py
python3 scripts/credentialed_sandbox_preflight.py
python3 scripts/credentialed_sandbox_preflight.py --require-target telegram
python3 scripts/credentialed_sandbox_preflight.py --require-target bitrix24
python3 scripts/bitrix24_contract_evidence.py
bash scripts/smoke_live_demo.sh https://saleops.duckdns.org
bash scripts/smoke_live_demo.sh https://leadscore.duckdns.org
curl -fsS https://saleops.duckdns.org/runtime
curl -fsS https://saleops.duckdns.org/llm/runtime
curl -fsS https://saleops.duckdns.org/transcription/runtime
```

Expected local gate result:

```text
36 passed
public verification passed
```

Expected live smoke signals:

```text
live demo smoke passed
llm=local
score=100
google_drive=gdrive://demo-sales-playbook
transcription=local_stub:dry_run
approval=approved
telegram_callback=rejected
bitrix24_drain=<positive dry-run drain count>
```

Expected evidence capture signal:

```text
reviewer evidence captured
json=docs/evidence/reviewer-snapshot.sanitized.json
text=docs/evidence/reviewer-snapshot.txt
```

Expected readiness drill signal:

```text
production readiness drill captured
production readiness drill passed
```

Expected credentialed preflight signal:

```text
credentialed sandbox preflight passed
mode=live
required_targets=telegram missing_required_targets=none
telegram=configured=True get_me=passed webhook=passed
secret_boundaries=secrets_printed=False mutating_external_calls=False
```

Expected Bitrix24 sandbox and contract signals:

```text
bitrix24=configured=True profile=passed crm_lead_fields=passed origin=https://b24-jgkzt9.bitrix24.ru
bitrix24 contract evidence passed
method=crm.lead.update
request_shape=True
secret_token_leaked=False
```

When only one real sandbox is connected, `--require-target telegram` or `--require-target bitrix24`
turns that specific missing credential into a hard failure while leaving the other target optional.
With repository secrets configured, the manual `Credentialed Sandbox Preflight` GitHub Actions
workflow runs the same read-only checks and uploads sanitized artifacts for review.

## Known Public Demo Boundaries

- Google Drive and Bitrix24 are dry-run by default so reviewers can inspect contracts without credentials.
- The synthetic public demo keeps Telegram dry-run; live Telegram approval is proven through the owner-run evidence artifact.
- The knowledge-source import is dry-run/public-safe: the demo accepts exported text and metadata, not live Drive credentials.
- Transcription is dry-run/public-safe by default: the demo accepts audio metadata and returns normalized segments through a local fixture, while live OpenAI Whisper/Deepgram provider calls are contract-tested behind the same boundary.
- The public demo does not store real customer calls, CRM data, bot tokens, or Google credentials.
- The Bitrix24 outbox worker is visible but disabled in the public dry-run deployment.
- Bitrix24 has read-only sandbox proof for webhook/CRM scope; public CRM writes are still disabled.
- Local deterministic embeddings are intentional for repeatable review; PostgreSQL/pgvector is the durable storage path.
- `LLM_PROVIDER=auto` selects a configured OpenAI, Claude/Anthropic, or Gemini API key; without keys the public demo uses the local extractive fallback.
- Production integrations require server-side secrets, webhook verification, rollout notes, and real CRM field mapping.

## What A Reviewer Should Conclude

This is not a thin chatbot wrapper. The repository demonstrates an AI workflow system with backend-owned
state, document and connector intake, RAG boundaries, approval transitions, Telegram callback handling,
OpenAI/Claude/Gemini provider boundaries, Whisper/Deepgram transcription boundaries, CRM outbox
semantics, runtime evidence, Docker deployment, CI, and public smoke checks.
