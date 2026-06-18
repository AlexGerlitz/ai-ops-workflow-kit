# Evidence Map

This map connects the repository to the work expected from an AI automation engineer.
For a vacancy-style checklist with verification commands and production boundaries, read
[AI Automation Role Requirements Map](./ROLE_REQUIREMENTS_MAP.md).

| Requirement | Evidence |
| --- | --- |
| AI workflow orchestration | `app/main.py`, `infra/n8n/call-transcript-approval.json`, `infra/n8n/google-drive-sales-ops-approval.json`, `docs/N8N_APPROVAL_FLOW.md` |
| Google Drive intake | `POST /integrations/google-drive/import`, `GoogleDriveImportIn`, `docs/INTEGRATION_SKELETON.md` |
| RAG and embeddings | `app/chunking.py`, `app/embeddings.py`, `app/store.py`, `POST /documents`, `POST /query` |
| pgvector-ready persistence | `app/store.py`, `docker-compose.yml`, `docs/ARCHITECTURE.md` |
| Transcript analysis and scoring | `app/scoring.py`, `app/sales_workflow.py`, `demo/call-transcript.json` |
| Human approval flow | `POST /approvals`, `POST /approvals/{id}/approve`, `tests/test_core.py` |
| Telegram approval contract | `app/integrations.py`, `POST /approvals/{id}/notify/telegram`, `POST /webhooks/telegram/approval`, `scripts/configure_telegram_webhook.sh`, `docs/INTEGRATION_SKELETON.md` |
| Bitrix24 handoff contract | `app/integrations.py`, `app/store.py`, `POST /integration-events/{id}/dispatch/bitrix24`, `POST /integrations/bitrix24/drain` |
| Self-hosted runtime | `Dockerfile`, `docker-compose.yml`, `docs/LIVE_DEMO.md`, `docs/OPERATIONS.md` |
| Runtime observability | `GET /runtime`, `GET /metrics`, worker state, `app/observability.py`, `scripts/smoke_live_demo.sh` |
| Public proof | `https://saleops.duckdns.org/`, `scripts/smoke_live_demo.sh` |
| Verification discipline | `scripts/verify_public.sh`, `.github/workflows/ci.yml`, `tests/` |

## Design Signals

- n8n is treated as workflow orchestration, not as the place where core state lives.
- The backend owns retrieval, scoring, approvals, and integration contracts.
- External integrations are dry-run by default, so a public reviewer can inspect payloads without secrets.
- Google Drive import is normalized before RAG storage, so connector code does not own retrieval logic.
- Local embeddings are deterministic, so tests and demo output are repeatable without API keys.
- CRM handoff is queued only after an explicit approval transition.
- Bitrix24 handoff is modeled as an outbox event with idempotency keys, attempt counters, `next_retry_at`, retry-safe drain, and `dead_letter` state.
- Runtime identity, worker state, and counters are public, so a reviewer can verify the deployed build without server access.
- Telegram callbacks can be verified with Telegram's webhook secret header in production.

## Review Order

1. Open the live demo: `https://saleops.duckdns.org/`.
2. Run `bash scripts/smoke_live_demo.sh`.
3. Run `bash scripts/verify_public.sh`.
4. Read `docs/ARCHITECTURE.md`.
5. Read `docs/INTEGRATION_SKELETON.md`.
