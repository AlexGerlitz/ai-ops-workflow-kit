# Reviewer Acceptance Report

This report is the fastest live-runtime acceptance pass for the public AI Ops evidence surface. It checks
the live deployment, GitHub Actions state, profile Pages route, public resume PDF availability, and
the owner-run sandbox workflow link in one command when the VPS edge is reachable.

For a stable review path that does not depend on the external live edge, start with
`docs/PUBLIC_PROOF_STATUS.md` and run `PYTHON_BIN=.venv/bin/python bash scripts/verify_public.sh`.

## Run

```bash
python3 scripts/reviewer_acceptance_report.py
```

Generated evidence:

| Artifact | Purpose |
| --- | --- |
| `docs/evidence/reviewer-acceptance-report.sanitized.json` | Machine-readable acceptance result from the last captured live evidence surface. |
| `docs/evidence/reviewer-acceptance-report.txt` | Human-readable acceptance summary from the last captured live evidence surface. |
| `scripts/reviewer_acceptance_report.py` | Recreates the report. |

## What It Checks

| Check | Evidence |
| --- | --- |
| Live API snapshot | `/runtime`, `/llm/runtime`, `/transcription/runtime`, `/integrations/runtime`, `/metrics`, and `/demo/run` through `scripts/reviewer_snapshot.py` when the live runtime is reachable. |
| Live browser/workflow smoke | `scripts/smoke_live_demo.sh https://saleops.duckdns.org`, including Telegram callback rejection and Bitrix24 dry-run drain, when the live runtime is reachable. |
| GitHub evidence state | Public CI workflow, latest checked CI run, owner-run `Credentialed Sandbox Preflight` workflow, and latest checked sandbox run are successful. |
| Profile review route | GitHub Pages surfaces link to AI Ops public evidence status and owner-run sandbox workflow. |
| Resume artifact | Public PDF resume is present and downloadable. |
| Bitrix24 contract artifact | Committed sanitized evidence for `crm.lead.update` request shape, dry-run guard, and token redaction. |
| Live Telegram approval artifact | Committed sanitized evidence for a real Telegram approval callback that queued a CRM handoff while Bitrix24 stayed dry-run. |

## Expected Summary

```text
reviewer acceptance report captured
reviewer acceptance report passed
live_snapshot=passed
live_smoke=passed
github=passed
sandbox_run=success
profile_pages=passed
bitrix24_contract=passed
live_telegram_approval=passed
secret_boundaries=secrets_printed=False mutating_external_calls=False
```

## Boundary

- The report does not use or print private API keys.
- The synthetic public workflow stays dry-run for Telegram and Bitrix24 external actions.
- The live-runtime command is intentionally allowed to fail when the external VPS edge is unavailable; use the local public gate and committed sanitized evidence as the stable evidence route.
- Telegram owner-run sandbox evidence and live approval evidence are present as sanitized artifacts.
- Bitrix24 has sanitized read-only sandbox evidence for `profile` and `crm.lead.fields`, plus a
  committed contract artifact for the production dispatch request shape.
