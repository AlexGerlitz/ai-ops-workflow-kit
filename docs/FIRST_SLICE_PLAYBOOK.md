# First Slice Playbook

Use this when the first question is: what can I ship first, and how do we know it is real?

The useful first result is not a broad AI transformation plan. It is one backend-owned workflow slice
that turns a messy business path into records, state, approvals, integration contracts, tests, logs,
docs, and a handoff route.

## First Response Contract

For a role, project, or technical review, the first response should be concrete:

- fit or no-fit against AI workflow, backend/platform, CRM/API integration, or DevOps reliability work;
- risky assumptions and missing access/data/system context;
- smallest responsible first slice;
- review path to inspect before committing more time or budget;
- handoff artifact: tests, logs, docs, runbook, smoke check, deployment note, or support boundary.

## First Slice Options

| First slice | When it fits | What I would ship first | Evidence in this repo |
| --- | --- | --- | --- |
| RAG / transcript workflow slice | Documents, calls, transcripts, tickets, or leads need retrieval, structured analysis, scoring, and review. | Ingestion endpoint, RAG retrieval with citations, deterministic eval, structured JSON analysis, approval item, tests, and reviewer notes. | `POST /demo/run`, `POST /rag/eval`, `app/rag_eval.py`, `app/sales_workflow.py`, `docs/OFFER_DEMO.md` |
| CRM handoff slice | A CRM/ERP/API write is risky, duplicated, manual, or hidden inside automation glue. | Adapter contract, dry-run payload, idempotency key, queued outbox event, retry/dead-letter behavior, audit state, and rollout note. | `app/integrations.py`, `app/store.py`, `POST /integration-events/{id}/dispatch/bitrix24`, `docs/evidence/bitrix24-contract.txt` |
| Human approval slice | AI output needs a human review point before customer, CRM, or operator action. | Approval queue, approve/reject transitions, Telegram callback contract, safe context payload, and post-approval handoff. | `POST /approvals`, `POST /webhooks/telegram/approval`, `docs/LIVE_OWNER_PROOF.md`, `infra/n8n/call-transcript-approval.json` |
| Reliability slice | A workflow already exists but is hard to trust, deploy, retry, observe, or recover. | Docker/runtime check, smoke command, metrics/runtime endpoint, failure-mode drill, retry/dead-letter evidence, and runbook update. | `scripts/verify_public.sh`, `scripts/production_readiness_drill.py`, `GET /runtime`, `GET /metrics`, `docs/OPERATIONS.md` |

## Done Criteria

A first slice is done when it has:

- one runnable command or live route;
- one clear success condition;
- structured output or state that can be inspected;
- test or smoke coverage;
- privacy/safe-logging boundary when business data is involved;
- dry-run or sandbox boundary before external writes;
- docs/runbook/handoff notes that explain how to operate the slice after the demo.

## Business Scenario Replay

For a fast review, start with the business scenario replay before reading the full demo JSON:

```bash
python3 scripts/business_scenario_replay.py
```

It summarizes the same offer-demo route as business input, backend route, evidence signals, and handoff
artifacts:

```text
business scenario replay passed
rag_quality=ok=True passed=2/2 citations_present=True
approval=status=approved
crm_handoff=adapter=bitrix24.mock status=queued
bitrix24_dispatch=adapter=bitrix24 status=dry_run
```

## Fast Verification

```bash
python3 -m pip install -r requirements.txt
bash scripts/verify_public.sh
python3 scripts/business_scenario_replay.py
python3 scripts/run_offer_demo.py
python3 scripts/production_readiness_drill.py
```

Expected signals:

```text
rag_quality.ok=true
approval.status=approved
crm_handoff.status=queued
bitrix24_dispatch.status=dry_run
business scenario replay passed
public verification passed
```

## Best First Message

Send one workflow, one success condition, and the systems involved. The strongest first context names
the risky boundary: retrieval quality, AI output review, CRM/API write, approval path, deployment
recovery, or operator handoff.
