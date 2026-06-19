# Public Proof Status

Last checked: 2026-06-19

This page is the shortest route to the current public evidence for AI Ops Workflow Kit.

| Surface | Current proof |
| --- | --- |
| Repository state | Current public `main` branch; this file is part of the reviewed tree |
| CI workflow | https://github.com/AlexGerlitz/ai-ops-workflow-kit/actions/workflows/ci.yml |
| Reviewer acceptance report | `python3 scripts/reviewer_acceptance_report.py` checks live API, live smoke, GitHub Actions state, Pages route, and public PDF |
| Local public gate | `PYTHON_BIN=.venv/bin/python bash scripts/verify_public.sh` -> `31 passed`, `public verification passed` |
| Live smoke | `bash scripts/smoke_live_demo.sh https://saleops.duckdns.org` -> `live demo smoke passed`, `score=100`, `telegram_callback=rejected`, positive Bitrix24 drain counter |
| Live demo | https://saleops.duckdns.org/ |
| Lead score alias | https://leadscore.duckdns.org/ |
| LLM runtime | https://saleops.duckdns.org/llm/runtime |
| Credential preflight | Public no-secret evidence plus target-specific modes: `--require-target telegram` and `--require-target bitrix24` |
| Owner-run sandbox workflow | https://github.com/AlexGerlitz/ai-ops-workflow-kit/actions/workflows/credentialed-sandbox-preflight.yml |
| Latest live combined sandbox run | https://github.com/AlexGerlitz/ai-ops-workflow-kit/actions/runs/27799329429 -> `telegram=configured=True get_me=passed webhook=passed`, `bitrix24=configured=True profile=passed crm_lead_fields=passed`, sanitized artifact committed in `docs/evidence/` |
| Bitrix24 contract evidence | `docs/evidence/bitrix24-contract.txt` -> `method=crm.lead.update`, `request_shape=True`, `secret_token_leaked=False` |
| Live Bitrix24 read-only sandbox | `docs/evidence/bitrix24-sandbox-preflight.txt` -> `profile=passed`, `crm_lead_fields=passed`, `origin=https://b24-jgkzt9.bitrix24.ru` |
| Profile Pages route | https://alexgerlitz.github.io/AlexGerlitz/ |
| Public resume PDF | Published from the profile repo and linked from the Pages route |

## Reviewer Route

1. Open the live demo: https://saleops.duckdns.org/
2. Open the CI workflow: https://github.com/AlexGerlitz/ai-ops-workflow-kit/actions/workflows/ci.yml
3. Run `python3 scripts/reviewer_acceptance_report.py`.
4. Read [Technical Review Packet](./TECHNICAL_REVIEW_PACKET.md).
5. Read [Reviewer Evidence Pack](./REVIEWER_EVIDENCE_PACK.md).
6. Read [Production Readiness Drill](./PRODUCTION_READINESS_DRILL.md).
7. Read [Credentialed Sandbox Preflight](./CREDENTIALED_SANDBOX_PREFLIGHT.md).
8. Inspect the latest live combined sandbox run: https://github.com/AlexGerlitz/ai-ops-workflow-kit/actions/runs/27799329429
9. Inspect `docs/evidence/bitrix24-contract.txt` and `docs/evidence/bitrix24-sandbox-preflight.txt`.
10. Run `bash scripts/smoke_live_demo.sh https://saleops.duckdns.org`.
11. Run `PYTHON_BIN=.venv/bin/python bash scripts/verify_public.sh`.

## Public Boundary

- Public demo mode intentionally avoids customer data, real Telegram sends, real Bitrix24 writes, and committed secrets.
- Live runtime may report an older deployed app Git SHA when the latest repository changes are docs, tests, or verification scripts only. CI proves those repository changes; live smoke proves the deployed workflow remains healthy.
- Telegram sandbox credentials have been validated through the owner-run workflow.
- Bitrix24 sandbox evidence validates the incoming webhook with read-only `profile` and CRM `crm.lead.fields`; public CRM writes remain dry-run and production-gated.
- Private sandbox artifacts should be generated through the manual GitHub Actions workflow or a local run, then inspected as sanitized evidence instead of committing secrets.
