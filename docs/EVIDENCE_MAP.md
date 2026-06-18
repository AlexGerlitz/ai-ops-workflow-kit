# Evidence Map

This map connects the repository to the work expected from an AI automation engineer.
For a vacancy-style checklist with verification commands and production boundaries, read
[AI Automation Role Requirements Map](./ROLE_REQUIREMENTS_MAP.md). For a 10-15 minute reviewer route,
read [Technical Review Packet](./TECHNICAL_REVIEW_PACKET.md).
For current CI, live smoke, local gate, and public boundary status, read
[Public Proof Status](./PUBLIC_PROOF_STATUS.md).

| Requirement | Evidence |
| --- | --- |
| AI workflow orchestration | `app/main.py`, `infra/n8n/call-transcript-approval.json`, `infra/n8n/google-drive-sales-ops-approval.json`, `docs/N8N_APPROVAL_FLOW.md` |
| Google Drive intake | `POST /integrations/google-drive/import`, `GoogleDriveImportIn`, `docs/INTEGRATION_SKELETON.md` |
| LLM API provider boundary | `app/llm.py`, `GET /llm/runtime`, OpenAI, Claude/Anthropic, Gemini payload tests |
| RAG and embeddings | `app/chunking.py`, `app/embeddings.py`, `app/store.py`, `POST /documents`, `POST /query` |
| pgvector-ready persistence | `app/store.py`, `docker-compose.yml`, `docs/ARCHITECTURE.md` |
| Transcript analysis and scoring | `app/scoring.py`, `app/sales_workflow.py`, `demo/call-transcript.json` |
| Human approval flow | `POST /approvals`, `POST /approvals/{id}/approve`, `tests/test_core.py` |
| Telegram approval contract | `app/integrations.py`, `POST /approvals/{id}/notify/telegram`, `POST /webhooks/telegram/approval`, `scripts/configure_telegram_webhook.sh`, `docs/INTEGRATION_SKELETON.md` |
| Bitrix24 handoff contract | `app/integrations.py`, `app/store.py`, `POST /integration-events/{id}/dispatch/bitrix24`, `POST /integrations/bitrix24/drain` |
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
- External integrations are dry-run by default, so a public reviewer can inspect payloads without secrets.
- Google Drive import is normalized before RAG storage, so connector code does not own retrieval logic.
- Local embeddings and LLM fallback are deterministic, so tests and demo output are repeatable without API keys.
- OpenAI, Claude/Anthropic, and Gemini provider wiring is contract-tested without committing secrets.
- CRM handoff is queued only after an explicit approval transition.
- Bitrix24 handoff is modeled as an outbox event with idempotency keys, attempt counters, `next_retry_at`, retry-safe drain, and `dead_letter` state.
- Runtime identity, worker state, and counters are public, so a reviewer can verify the deployed build without server access.
- Reviewer acceptance report combines live API, smoke, GitHub Actions, Pages, and PDF checks in one command.
- Telegram callbacks can be verified with Telegram's webhook secret header in production.
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
9. If repository secrets exist, run the manual `Credentialed Sandbox Preflight` GitHub Actions workflow.
10. Run `bash scripts/smoke_live_demo.sh`.
11. Open `https://saleops.duckdns.org/llm/runtime`.
12. Run `bash scripts/verify_public.sh`.
13. Read `docs/TECHNICAL_REVIEW_PACKET.md`.
14. Read `docs/ARCHITECTURE.md`.
15. Read `docs/INTEGRATION_SKELETON.md`.
