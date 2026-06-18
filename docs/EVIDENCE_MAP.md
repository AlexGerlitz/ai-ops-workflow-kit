# Evidence Map

This map connects the repository to the work expected from an AI automation engineer.

| Requirement | Evidence |
| --- | --- |
| AI workflow orchestration | `app/main.py`, `infra/n8n/call-transcript-approval.json`, `docs/N8N_APPROVAL_FLOW.md` |
| RAG and embeddings | `app/chunking.py`, `app/embeddings.py`, `app/store.py`, `POST /documents`, `POST /query` |
| pgvector-ready persistence | `app/store.py`, `docker-compose.yml`, `docs/ARCHITECTURE.md` |
| Transcript analysis and scoring | `app/scoring.py`, `app/sales_workflow.py`, `demo/call-transcript.json` |
| Human approval flow | `POST /approvals`, `POST /approvals/{id}/approve`, `tests/test_core.py` |
| Telegram approval contract | `app/integrations.py`, `POST /approvals/{id}/notify/telegram`, `docs/INTEGRATION_SKELETON.md` |
| Bitrix24 handoff contract | `app/integrations.py`, `POST /integration-events/{id}/dispatch/bitrix24` |
| Self-hosted runtime | `Dockerfile`, `docker-compose.yml`, `docs/LIVE_DEMO.md`, `docs/OPERATIONS.md` |
| Public proof | `https://saleops.duckdns.org/`, `scripts/smoke_live_demo.sh` |
| Verification discipline | `scripts/verify_public.sh`, `.github/workflows/ci.yml`, `tests/` |

## Design Signals

- n8n is treated as workflow orchestration, not as the place where core state lives.
- The backend owns retrieval, scoring, approvals, and integration contracts.
- External integrations are dry-run by default, so a public reviewer can inspect payloads without secrets.
- Local embeddings are deterministic, so tests and demo output are repeatable without API keys.
- CRM handoff is queued only after an explicit approval transition.

## Review Order

1. Open the live demo: `https://saleops.duckdns.org/`.
2. Run `bash scripts/smoke_live_demo.sh`.
3. Run `bash scripts/verify_public.sh`.
4. Read `docs/ARCHITECTURE.md`.
5. Read `docs/INTEGRATION_SKELETON.md`.
