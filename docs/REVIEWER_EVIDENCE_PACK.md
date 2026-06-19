# Reviewer Evidence Pack

This pack gives reviewers a committed, sanitized snapshot of the live workflow and the exact command
that regenerates it.

## Artifacts

| Artifact | Purpose |
| --- | --- |
| [`docs/evidence/reviewer-snapshot.sanitized.json`](./evidence/reviewer-snapshot.sanitized.json) | Machine-readable live snapshot with dynamic CRM idempotency key redacted. |
| [`docs/evidence/reviewer-snapshot.txt`](./evidence/reviewer-snapshot.txt) | Human-readable summary of the same live snapshot. |
| [`scripts/capture_reviewer_evidence.py`](../scripts/capture_reviewer_evidence.py) | Rebuilds the evidence from `/runtime`, `/llm/runtime`, `/integrations/runtime`, `/metrics`, and `/demo/run`. |
| [`scripts/reviewer_snapshot.py`](../scripts/reviewer_snapshot.py) | Fails fast if the public workflow, RAG context, approval state, dry-run integrations, worker state, or metrics are inconsistent. |
| [`docs/PRODUCTION_READINESS_DRILL.md`](./PRODUCTION_READINESS_DRILL.md) | Complements the live snapshot with deterministic failure-mode evidence. |
| [`docs/CREDENTIALED_SANDBOX_PREFLIGHT.md`](./CREDENTIALED_SANDBOX_PREFLIGHT.md) | Shows the read-only Telegram/Bitrix24 credential boundary and sanitized evidence output, including the latest live Telegram owner-run. |
| [`docs/evidence/bitrix24-contract.sanitized.json`](./evidence/bitrix24-contract.sanitized.json) | Machine-readable Bitrix24 REST contract proof for `crm.lead.update`, dry-run guard, idempotency, and token redaction. |
| [`docs/evidence/bitrix24-sandbox-preflight.sanitized.json`](./evidence/bitrix24-sandbox-preflight.sanitized.json) | Sanitized live read-only Bitrix24 proof for `profile` and CRM `crm.lead.fields`. |

## Regenerate

```bash
python3 scripts/capture_reviewer_evidence.py
```

Alias check:

```bash
python3 scripts/capture_reviewer_evidence.py --base-url https://leadscore.duckdns.org
```

The generated JSON intentionally redacts only the per-run CRM idempotency key. Provider state,
integration dry-run state, RAG source context, score, approval result, Bitrix24 queue state, worker
state, metrics availability, deployed version, and deployed Git SHA stay visible.

## What A Reviewer Should See

- The public API returns runtime identity and worker state.
- The LLM boundary exposes local fallback plus OpenAI, Claude/Anthropic, and Gemini provider slots
  without exposing secrets.
- The demo imports Google Drive text into RAG and returns source context.
- Transcript analysis produces a lead score and approval item.
- Telegram and Bitrix24 contracts are exercised in dry-run mode.
- The owner-run Telegram sandbox preflight proves the real bot token and webhook boundary without sending messages.
- The Bitrix24 sandbox preflight proves the real incoming webhook can call read-only CRM metadata without writing CRM records.
- The Bitrix24 contract artifact shows the exact `crm.lead.update` request shape used by the dispatch adapter.
- CRM handoff is queued after approval and uses an idempotency key.
- Metrics expose runtime and demo counters.

The deployed Git SHA in the evidence is the running application build. Documentation-only commits may
be newer than the deployed build without changing the runtime behavior being verified.
