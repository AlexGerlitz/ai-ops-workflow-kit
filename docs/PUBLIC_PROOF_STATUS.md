# Public Proof Status

Last checked: 2026-06-27

This page is the shortest route to the current public evidence for AI Ops Workflow Kit.

| Surface | Current proof |
| --- | --- |
| Repository state | Current public `main` branch; this file is part of the reviewed tree |
| CI workflow | https://github.com/AlexGerlitz/ai-ops-workflow-kit/actions/workflows/ci.yml |
| Stable reviewer route | Start here, then run `PYTHON_BIN=.venv/bin/python bash scripts/verify_public.sh`; this path does not depend on the external VPS edge being reachable |
| Reviewer acceptance report | `python3 scripts/reviewer_acceptance_report.py` checks live API, live smoke, GitHub Actions state, Pages route, and public PDF when the live runtime is reachable |
| Local public gate | `PYTHON_BIN=.venv/bin/python bash scripts/verify_public.sh` -> `45 passed`, `public verification passed` |
| Privacy boundary | `docs/PRIVACY_BOUNDARY.md`; public demo proves transcript email/phone redaction before RAG ingestion, approval context, CRM handoff, demo JSON, and reviewer snapshots |
| Committed live-smoke evidence | `docs/evidence/reviewer-acceptance-report.txt` and `.sanitized.json` record the last captured `live demo smoke passed`, `score=100`, `transcription=local_stub:dry_run`, `telegram_callback=rejected`, and positive Bitrix24 drain counter |
| Runtime smoke | `bash scripts/smoke_live_demo.sh https://saleops.duckdns.org` is the live VPS check; run it after confirming the edge is reachable |
| Live audio upload | `POST /demo/audio/upload` from the browser demo accepts `.m4a/.mp3/.wav` uploads and runs live STT when `DEEPGRAM_API_KEY` is configured |
| Live Telegram owner approval | `docs/evidence/live-telegram-approval.txt` -> real Telegram approval callback `approved`, CRM outbox event `queued`, Bitrix24 remains dry-run |
| Runtime demo | https://saleops.duckdns.org/ |
| Lead score alias | https://leadscore.duckdns.org/ |
| LLM runtime | https://saleops.duckdns.org/llm/runtime |
| Transcription runtime | https://saleops.duckdns.org/transcription/runtime |
| Credential preflight | Public no-secret evidence plus target-specific modes: `--require-target telegram` and `--require-target bitrix24` |
| Owner-run sandbox workflow | https://github.com/AlexGerlitz/ai-ops-workflow-kit/actions/workflows/credentialed-sandbox-preflight.yml |
| Latest live combined sandbox run | https://github.com/AlexGerlitz/ai-ops-workflow-kit/actions/runs/27799329429 -> `telegram=configured=True get_me=passed webhook=passed`, `bitrix24 profile=passed`, `crm_lead_fields=passed`; focused committed artifacts cover live Telegram approval and Bitrix24 read-only checks |
| Bitrix24 contract evidence | `docs/evidence/bitrix24-contract.txt` -> `method=crm.lead.update`, `request_shape=True`, `secret_token_leaked=False` |
| Live Bitrix24 read-only sandbox | `docs/evidence/bitrix24-sandbox-preflight.txt` -> `profile=passed`, `crm_lead_fields=passed`, `origin=https://b24-jgkzt9.bitrix24.ru` |
| Profile Pages route | https://alexgerlitz.github.io/AlexGerlitz/ |
| Public resume PDF | Published from the profile repo and linked from the Pages route |

## Reviewer Route

1. Run `PYTHON_BIN=.venv/bin/python bash scripts/verify_public.sh`.
2. Open the CI workflow: https://github.com/AlexGerlitz/ai-ops-workflow-kit/actions/workflows/ci.yml
3. Read the committed reviewer acceptance evidence in `docs/evidence/reviewer-acceptance-report.txt`.
4. Read [Technical Review Packet](./TECHNICAL_REVIEW_PACKET.md).
5. Read [Reviewer Evidence Pack](./REVIEWER_EVIDENCE_PACK.md).
6. Read [Live Owner Proof](./LIVE_OWNER_PROOF.md).
7. Read [Production Readiness Drill](./PRODUCTION_READINESS_DRILL.md).
8. Read [Credentialed Sandbox Preflight](./CREDENTIALED_SANDBOX_PREFLIGHT.md).
9. Inspect the latest live combined sandbox run: https://github.com/AlexGerlitz/ai-ops-workflow-kit/actions/runs/27799329429
10. Inspect `docs/evidence/live-telegram-approval.txt`, `docs/evidence/bitrix24-contract.txt`, and `docs/evidence/bitrix24-sandbox-preflight.txt`.
11. If `https://saleops.duckdns.org/` is reachable, run `python3 scripts/reviewer_acceptance_report.py`.
12. If the alias is needed, run `bash scripts/smoke_live_demo.sh https://leadscore.duckdns.org`.

## Public Boundary

- Public synthetic demo mode intentionally avoids customer data, real call recordings, real Telegram sends, real Bitrix24 writes, and committed secrets.
- Live runtime may report an older deployed app Git SHA when the latest repository changes are docs, tests, or verification scripts only. CI and the local gate prove repository changes; runtime smoke proves the deployed workflow when the external VPS edge is reachable.
- Telegram sandbox credentials have been validated through the manual sandbox workflow; operator-triggered approval messages can be live while `/demo/run` remains dry-run.
- Bitrix24 sandbox evidence validates the incoming webhook with read-only `profile` and CRM `crm.lead.fields`; public CRM writes remain dry-run and production-gated.
- Synthetic smoke stays dry-run/public-safe through the local fixture; the browser upload flow can use live Deepgram for owner-provided recordings without committing secrets or permanent audio files.
- Private sandbox artifacts should be generated through the manual GitHub Actions workflow or a local run, then inspected as sanitized evidence instead of committing secrets.
