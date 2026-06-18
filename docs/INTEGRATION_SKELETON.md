# Integration Skeleton

This skeleton prepares the project for a real Telegram approval bot and Bitrix24 CRM handoff without
committing credentials or making public demo runs depend on external accounts.

## Runtime URL

The current public callback base URL is:

```text
https://saleops.duckdns.org
```

Set it through:

```env
PUBLIC_BASE_URL=https://saleops.duckdns.org
```

Telegram approval payloads use this URL to describe the backend approve/reject callback contract.

## Environment Contract

```env
TELEGRAM_BOT_TOKEN=
TELEGRAM_APPROVAL_CHAT_ID=
TELEGRAM_DRY_RUN=true
BITRIX24_WEBHOOK_URL=
BITRIX24_DRY_RUN=true
```

The default is dry-run. In dry-run mode the API returns the exact outgoing payload but does not call
Telegram or Bitrix24.

## Capability Check

```bash
curl http://127.0.0.1:8080/integrations/runtime
```

The response shows whether each adapter is configured and whether dry-run is enabled.

## Telegram Approval Skeleton

Endpoint:

```text
POST /approvals/{approval_id}/notify/telegram
```

Dry-run response includes:

- Telegram `sendMessage` text;
- inline approve/reject button payload;
- backend approve/reject callback URLs;
- Telegram webhook URL for inline `callback_query` updates;
- adapter status.

Production behavior after dry-run is disabled:

1. backend sends the approval message to Telegram;
2. Telegram sends inline button updates to `POST /webhooks/telegram/approval`;
3. approval state changes in the backend;
4. approved CRM updates are queued as integration events.

Telegram callback payload shape:

```json
{
  "update_id": 1001,
  "callback_query": {
    "id": "callback-id",
    "from": { "id": 7001, "username": "saleslead" },
    "data": "approve:{approval_id}"
  }
}
```

Supported callback data:

- `approve:{approval_id}`;
- `reject:{approval_id}`.

## Bitrix24 Handoff Skeleton

Endpoint:

```text
POST /integration-events/{event_id}/dispatch/bitrix24
```

Dry-run response includes:

- Bitrix24 method name;
- source integration event id;
- source approval id;
- CRM update payload.

Production behavior after dry-run is disabled:

1. approved CRM event is loaded from the backend queue;
2. adapter maps the internal `upsert_lead_follow_up` operation to a Bitrix24 REST method;
3. adapter sends the payload through `BITRIX24_WEBHOOK_URL`;
4. failed sends can later be retried or dead-lettered without changing the approval contract.

## Why This Shape

- Public demo remains reproducible without secrets.
- External calls are explicit and inspectable.
- Telegram and Bitrix24 credentials stay in `.env` or server secret storage.
- Approval and CRM mutation remain separate auditable steps.
