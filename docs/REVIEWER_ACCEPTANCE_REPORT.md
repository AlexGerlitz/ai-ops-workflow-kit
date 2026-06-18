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
| GitHub proof state | Public CI workflow, latest checked CI run, and owner-run `Credentialed Sandbox Preflight` workflow are active. |
| Profile proof route | GitHub Pages surfaces link to AI Ops public proof status and owner-run sandbox workflow. |
| Resume artifact | Public PDF resume is present and downloadable. |

## Expected Summary

```text
reviewer acceptance report captured
reviewer acceptance report passed
live_snapshot=passed
live_smoke=passed
github=passed
profile_pages=passed
secret_boundaries=secrets_printed=False mutating_external_calls=False
```

## Boundary

- The report does not use or print private API keys.
- Public mode stays dry-run for Telegram and Bitrix24 external actions.
- The report does not replace the private sandbox run. The final external proof is still the manual
  `Credentialed Sandbox Preflight` workflow with real repository secrets and sanitized artifacts.
