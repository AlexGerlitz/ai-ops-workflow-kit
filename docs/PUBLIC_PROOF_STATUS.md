# Public Proof Status

Last checked: 2026-06-19

This page is the shortest route to the current public evidence for AI Ops Workflow Kit.

| Surface | Current proof |
| --- | --- |
| Repository state | Current public `main` branch; this file is part of the reviewed tree |
| CI workflow | https://github.com/AlexGerlitz/ai-ops-workflow-kit/actions/workflows/ci.yml |
| Local public gate | `PYTHON_BIN=.venv/bin/python bash scripts/verify_public.sh` -> `27 passed`, `public verification passed` |
| Live smoke | `bash scripts/smoke_live_demo.sh https://saleops.duckdns.org` -> `live demo smoke passed`, `score=100`, `telegram_callback=rejected`, positive Bitrix24 drain counter |
| Live demo | https://saleops.duckdns.org/ |
| Lead score alias | https://leadscore.duckdns.org/ |
| LLM runtime | https://saleops.duckdns.org/llm/runtime |
| Credential preflight | Public no-secret evidence plus target-specific modes: `--require-target telegram` and `--require-target bitrix24` |
| Profile Pages route | https://alexgerlitz.github.io/AlexGerlitz/ |
| Public resume PDF | Published from the profile repo and linked from the Pages route |

## Reviewer Route

1. Open the live demo: https://saleops.duckdns.org/
2. Open the CI workflow: https://github.com/AlexGerlitz/ai-ops-workflow-kit/actions/workflows/ci.yml
3. Read [Technical Review Packet](./TECHNICAL_REVIEW_PACKET.md).
4. Read [Reviewer Evidence Pack](./REVIEWER_EVIDENCE_PACK.md).
5. Read [Production Readiness Drill](./PRODUCTION_READINESS_DRILL.md).
6. Read [Credentialed Sandbox Preflight](./CREDENTIALED_SANDBOX_PREFLIGHT.md).
7. Run `bash scripts/smoke_live_demo.sh https://saleops.duckdns.org`.
8. Run `PYTHON_BIN=.venv/bin/python bash scripts/verify_public.sh`.

## Public Boundary

- Public demo mode intentionally avoids customer data, real Telegram sends, real Bitrix24 writes, and committed secrets.
- Live runtime may report an older deployed app Git SHA when the latest repository changes are docs, tests, or verification scripts only. CI proves those repository changes; live smoke proves the deployed workflow remains healthy.
- Real sandbox credentials should be validated with `python3 scripts/credentialed_sandbox_preflight.py --require-target telegram` and `python3 scripts/credentialed_sandbox_preflight.py --require-target bitrix24` before enabling writes.
