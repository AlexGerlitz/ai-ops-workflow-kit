# n8n Approval Flow

This project keeps n8n useful at the edge while the backend owns durable workflow state.

## Importable Workflow

Import:

```text
infra/n8n/call-transcript-approval.json
```

The example workflow does four things:

1. accepts a normalized transcript webhook;
2. sends it to `POST /webhooks/n8n/call-transcript`;
3. builds a Telegram-ready approval payload;
4. returns the approval item and CRM operation summary.

When n8n runs inside `docker compose`, the API URL is:

```text
http://api:8080/webhooks/n8n/call-transcript
```

When n8n runs outside Docker, use the host API URL instead:

```text
http://127.0.0.1:8080/webhooks/n8n/call-transcript
```

For the public demo callback contract, use:

```text
https://saleops.duckdns.org
```

## Input Contract

```json
{
  "call_id": "CALL-2026-001",
  "customer_id": "LEAD-ACME-42",
  "transcript": "Client transcript text...",
  "metadata": {
    "source": "telephony",
    "manager": "sales-demo"
  }
}
```

## Backend Response

The backend returns:

- lead score;
- extracted sales signals;
- structured analysis;
- follow-up draft;
- approval item;
- CRM update payload inside the approval context.

The n8n workflow creates a Telegram-ready text payload from this response. A real Telegram node can
send that text with approve/reject buttons or links.

The backend also exposes a direct dry-run Telegram skeleton:

```bash
curl -X POST http://127.0.0.1:8080/approvals/{approval_id}/notify/telegram
```

## Approval Callback

Telegram approval should call the backend approval endpoint:

```bash
curl -X POST http://127.0.0.1:8080/approvals/{approval_id}/approve \
  -H 'content-type: application/json' \
  -d '{"reviewer":"sales-lead","notes":"Approved from Telegram"}'
```

Rejection uses the same contract:

```bash
curl -X POST http://127.0.0.1:8080/approvals/{approval_id}/reject \
  -H 'content-type: application/json' \
  -d '{"reviewer":"sales-lead","notes":"Needs rewrite"}'
```

## CRM Handoff Rule

The backend queues a `bitrix24.mock/upsert_lead_follow_up` integration event only after approval.
That separation is intentional:

- the transcript webhook can be retried without mutating CRM state;
- the reviewer decision is auditable;
- the CRM adapter can retry or dead-letter safely;
- n8n can notify people without owning backend state.

## Production Adapter Shape

A real Bitrix24 adapter would consume queued integration events and update:

- lead score;
- risk level;
- missing qualification signals;
- follow-up task;
- manager notes;
- target CRM stage.

The mock adapter key keeps the public demo safe while preserving the production contract.

The backend dispatch skeleton can inspect the mapped Bitrix24 payload without sending it:

```bash
curl -X POST http://127.0.0.1:8080/integration-events/{event_id}/dispatch/bitrix24
```
