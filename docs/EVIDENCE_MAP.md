# Evidence Map

This map connects the repository to the work expected from an AI automation engineer.
For a role-level checklist with verification commands and production boundaries, read
[AI Automation Role Requirements Map](./ROLE_REQUIREMENTS_MAP.md). For a 10-15 minute reviewer route,
read [Technical Review Packet](./TECHNICAL_REVIEW_PACKET.md).
For current CI, live smoke, local gate, and public boundary status, read
[Public Proof Status](./PUBLIC_PROOF_STATUS.md).

| Requirement | Evidence |
| --- | --- |
| AI workflow orchestration | `app/main.py`, `infra/n8n/call-audio-transcription-approval.json`, `infra/n8n/call-transcript-approval.json`, `infra/n8n/google-drive-sales-ops-approval.json`, `docs/N8N_APPROVAL_FLOW.md` |
| Document intake / Google Drive adapter | `POST /integrations/google-drive/import`, `GoogleDriveImportIn`, `docs/INTEGRATION_SKELETON.md` |
| LLM API provider boundary | `app/llm.py`, `GET /llm/runtime`, OpenAI, Claude/Anthropic, Gemini payload tests |
| Call-audio transcription boundary | `app/transcription.py`, `GET /transcription/runtime`, `POST /webhooks/n8n/call-audio`, `POST /demo/audio/upload`, `infra/n8n/call-audio-transcription-approval.json` |
| RAG and embeddings | `app/chunking.py`, `app/embeddings.py`, `app/store.py`, `POST /documents`, `POST /query` |
| pgvector-ready persistence | `app/store.py`, `docker-compose.yml`, `docs/ARCHITECTURE.md` |
| Transcript analysis and scoring | `app/scoring.py`, `app/sales_workflow.py`, `demo/call-transcript.json` |
| Human approval flow | `POST /approvals`, `POST /approvals/{id}/approve`, `tests/test_core.py` |
| Telegram approval contract | `app/integrations.py`, `POST /approvals/{id}/notify/telegram`, `POST /webhooks/telegram/approval`, `scripts/configure_telegram_webhook.sh`, `docs/INTEGRATION_SKELETON.md`, `docs/LIVE_OWNER_PROOF.md`, `docs/evidence/live-telegram-approval.sanitized.json` |
| Bitrix24 handoff contract | `app/integrations.py`, `app/store.py`, `POST /integration-events/{id}/dispatch/bitrix24`, `POST /integrations/bitrix24/drain`, `docs/evidence/bitrix24-contract.sanitized.json`, `docs/evidence/bitrix24-sandbox-preflight.sanitized.json` |
| Self-hosted runtime | `Dockerfile`, `docker-compose.yml`, `docs/LIVE_DEMO.md`, `docs/OPERATIONS.md` |
| Runtime observability | `GET /runtime`, `GET /metrics`, worker state, `app/observability.py`, `scripts/smoke_live_demo.sh` |
| Reviewer acceptance report | `docs/REVIEWER_ACCEPTANCE_REPORT.md`, `scripts/reviewer_acceptance_report.py` |
| Technical reviewer snapshot | `scripts/reviewer_snapshot.py`, `docs/TECHNICAL_REVIEW_PACKET.md`, `GET /runtime`, `GET /llm/runtime`, `POST /demo/run` |
| Reviewer evidence pack | `docs/REVIEWER_EVIDENCE_PACK.md`, `docs/evidence/reviewer-snapshot.sanitized.json`, `scripts/capture_reviewer_evidence.py` |
| Failure-mode evidence | `docs/PRODUCTION_READINESS_DRILL.md`, `docs/evidence/production-readiness-drill.sanitized.json`, `scripts/production_readiness_drill.py` |
| Credentialed sandbox boundary | `docs/CREDENTIALED_SANDBOX_PREFLIGHT.md`, `docs/evidence/credentialed-sandbox-preflight.sanitized.json`, `scripts/credentialed_sandbox_preflight.py`, `.github/workflows/credentialed-sandbox-preflight.yml` |
| Current public proof status | `docs/PUBLIC_PROOF_STATUS.md`, latest CI, live smoke output, public gate output, profile Pages route |
| Public proof | `https://saleops.duckdns.org/`, `scripts/reviewer_snapshot.py`, `scripts/smoke_live_demo.sh` |
| Verification discipline | `scripts/verify_public.sh`, `.github/workflows/ci.yml`, `tests/` |

## Design Signals

- n8n is treated as workflow orchestration, not as the place where core state lives.
- The backend owns retrieval, scoring, approvals, and integration contracts.
- External write integrations are dry-run by default, so a public reviewer can inspect payloads without secrets.
- The synthetic public demo keeps Telegram dry-run; owner-run evidence proves the real Telegram approval callback path.
- Document intake through the Google Drive adapter is normalized before RAG storage, so connector code does not own retrieval logic.
- Local embeddings and LLM fallback are deterministic, so tests and demo output are repeatable without API keys.
- OpenAI, Claude/Anthropic, and Gemini provider wiring is contract-tested without committing secrets.
- OpenAI Whisper and Deepgram transcription wiring is implemented behind a provider boundary; deterministic smoke uses a local fixture, and the browser upload endpoint can process a real temporary recording when a provider key is configured.
- CRM handoff is queued only after an explicit approval transition.
- Bitrix24 handoff is modeled as an outbox event with idempotency keys, attempt counters, `next_retry_at`, retry-safe drain, and `dead_letter` state.
- Bitrix24 proof covers both the production request contract and a real read-only sandbox check for `profile` plus CRM `crm.lead.fields`.
- Runtime identity, worker state, and counters are public, so a reviewer can verify the deployed build without server access.
- Reviewer acceptance report combines live API, smoke, GitHub Actions, Pages, and PDF checks in one command.
- Telegram callbacks can be verified with Telegram's webhook secret header in production.
- Repeated Telegram approval taps are handled idempotently so the client receives a callback answer instead of spinning.
- Failure-mode evidence is captured without external credentials, so reviewers can inspect retry,
  dead-letter, drain scheduling, idempotency, and worker guard behavior locally or in CI.
- Credentialed sandbox preflight uses read-only Telegram and Bitrix24 calls when secrets exist, and
  records skipped/no-secret evidence in public mode without printing tokens.
- The manual credentialed preflight workflow lets the owner generate sanitized private sandbox
  artifacts from repository secrets without committing credentials.

## Review Order

1. Open the live demo: `https://saleops.duckdns.org/`.
2. Open `docs/PUBLIC_PROOF_STATUS.md`.
3. Run `python3 scripts/reviewer_acceptance_report.py`.
4. Open `docs/REVIEWER_EVIDENCE_PACK.md`.
5. Run `python3 scripts/capture_reviewer_evidence.py`.
6. Run `python3 scripts/reviewer_snapshot.py`.
7. Run `python3 scripts/production_readiness_drill.py`.
8. Run `python3 scripts/credentialed_sandbox_preflight.py`.
9. Open `docs/LIVE_OWNER_PROOF.md`.
10. Run `python3 scripts/bitrix24_contract_evidence.py`.
11. If repository secrets exist, run the manual `Credentialed Sandbox Preflight` GitHub Actions workflow.
12. Run `bash scripts/smoke_live_demo.sh`.
13. Open `https://saleops.duckdns.org/llm/runtime`.
14. Open `https://saleops.duckdns.org/transcription/runtime`.
15. Run `bash scripts/verify_public.sh`.
16. Read `docs/TECHNICAL_REVIEW_PACKET.md`.
17. Read `docs/ARCHITECTURE.md`.
18. Read `docs/INTEGRATION_SKELETON.md`.
