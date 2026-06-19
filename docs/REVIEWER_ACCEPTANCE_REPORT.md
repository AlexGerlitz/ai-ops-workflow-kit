# Reviewer Acceptance Report

This report is the fastest technical acceptance pass for the public AI Ops proof surface. It checks
the live deployment, GitHub Actions state, profile Pages route, public resume PDF availability, and
the owner-run sandbox workflow link in one command.

## Run

```bash
python3 scripts/reviewer_acceptance_report.py
```

Generated evidence:

| Artifact | Purpose |
| --- | --- |
| `docs/evidence/reviewer-acceptance-report.sanitized.json` | Machine-readable acceptance result for live proof surfaces. |
| `docs/evidence/reviewer-acceptance-report.txt` | Human-readable acceptance summary. |
| `scripts/reviewer_acceptance_report.py` | Recreates the report. |

## What It Checks

| Check | Evidence |
| --- | --- |
| Live API snapshot | `/runtime`, `/llm/runtime`, `/integrations/runtime`, `/metrics`, and `/demo/run` through `scripts/reviewer_snapshot.py`. |
| Live browser/workflow smoke | `scripts/smoke_live_demo.sh https://saleops.duckdns.org`, including Telegram callback rejection and Bitrix24 dry-run drain. |
| GitHub proof state | Public CI workflow, latest checked CI run, owner-run `Credentialed Sandbox Preflight` workflow, and latest checked sandbox run are successful. |
| Profile proof route | GitHub Pages surfaces link to AI Ops public proof status and owner-run sandbox workflow. |
| Resume artifact | Public PDF resume is present and downloadable. |

## Expected Summary

```text
reviewer acceptance report captured
reviewer acceptance report passed
live_snapshot=passed
live_smoke=passed
github=passed
sandbox_run=success
profile_pages=passed
secret_boundaries=secrets_printed=False mutating_external_calls=False
```

## Boundary

- The report does not use or print private API keys.
- Public mode stays dry-run for Telegram and Bitrix24 external actions.
- Telegram owner-run sandbox evidence is present as a sanitized artifact. Bitrix24 remains a separate
  target-specific proof until a `BITRIX24_WEBHOOK_URL` repository secret is configured.
