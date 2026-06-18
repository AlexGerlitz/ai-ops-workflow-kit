# Production Readiness Drill

This drill gives reviewers a deterministic failure-mode check for the backend-owned workflow. It is
local, secret-free, and safe to run in CI.

## Run

```bash
python3 scripts/production_readiness_drill.py
```

Generated evidence:

| Artifact | Purpose |
| --- | --- |
| [`docs/evidence/production-readiness-drill.sanitized.json`](./evidence/production-readiness-drill.sanitized.json) | Machine-readable result for failure-mode review. |
| [`docs/evidence/production-readiness-drill.txt`](./evidence/production-readiness-drill.txt) | Human-readable summary of the same drill. |
| [`scripts/production_readiness_drill.py`](../scripts/production_readiness_drill.py) | Recreates the drill through the API contract with FastAPI `TestClient`. |

## What It Proves

| Drill | Production signal |
| --- | --- |
| Telegram webhook secret enforcement | Unsigned callback is rejected with `403`; signed callback applies the approval transition. |
| Bitrix24 retry to dead-letter | Missing CRM webhook records a retry attempt, then moves the event to `dead_letter` after max attempts. |
| Drain respects retry timing | A retry event with `next_retry_at` is skipped by a second drain until it becomes due. |
| CRM handoff idempotency | Re-running the approval handoff code for the same approval keeps one CRM event. |
| Worker dry-run guard | Enabling the worker while Bitrix24 dry-run is enabled still keeps the worker inactive. |

## Why This Exists

The live public demo intentionally keeps external integrations in dry-run mode. This drill covers the
parts that are hard to demonstrate safely against public Telegram or Bitrix24 credentials:

- webhook authentication failure;
- retry and dead-letter state;
- explicit retry scheduling;
- idempotent CRM handoff;
- worker guardrails for dry-run deployments.

The output is sanitized: dynamic approval ids, CRM event ids, idempotency keys, and retry timestamps
are either omitted or replaced with stable placeholders.
