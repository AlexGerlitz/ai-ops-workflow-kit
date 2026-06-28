# Demo Walkthrough

This is the short visual proof route for the DriveDesk AI Operator workflow.

![DriveDesk AI Operator demo GIF](./assets/drive-operator-demo.gif)

Short path shown in the GIF: Transcript -> RAG -> approval -> CRM-safe handoff.

## What It Shows

The GIF is generated from the same public-safe offer demo that the verification gate checks:

```bash
PYTHON_BIN=.venv/bin/python python3 scripts/build_demo_gif.py
```

It summarizes the end-to-end workflow:

1. Google Drive-style playbook import into the RAG store.
2. RAG quality evaluation with expected source, required terms, score floor, and citations.
3. Call-audio transcription boundary and structured transcript analysis.
4. Privacy redaction before RAG, approval context, and CRM handoff.
5. Human approval before external system handoff.
6. Bitrix24 CRM-safe outbox handoff with dry-run dispatch, idempotency, retries, and dead-letter state.

## Why It Matters

This is the visual hiring signal for the repository: I am not just connecting workflow nodes.
The backend owns records, RAG, approval state, audit, retries, idempotency, privacy boundaries,
and integration contracts. n8n can orchestrate events, but the stateful system behavior stays
in FastAPI/PostgreSQL-owned code.

## Verification

The GIF is a committed visual artifact, not the source of truth. The source of truth remains:

- `python3 scripts/run_offer_demo.py`
- `bash scripts/verify_public.sh`
- `docs/PUBLIC_PROOF_STATUS.md`
- `docs/EMPLOYER_TRIGGER_PROOF.md`
- `docs/LIVE_OWNER_PROOF.md`

The public verification gate checks that the GIF exists, is a real GIF, and is linked from the
reviewer-facing proof route.
