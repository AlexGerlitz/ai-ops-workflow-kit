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
TELEGRAM_WEBHOOK_SECRET=
TELEGRAM_DRY_RUN=true
BITRIX24_WEBHOOK_URL=
BITRIX24_DRY_RUN=true
INTEGRATION_MAX_ATTEMPTS=3
INTEGRATION_RETRY_DELAY_SECONDS=300
INTEGRATION_WORKER_ENABLED=false
INTEGRATION_WORKER_INTERVAL_SECONDS=60
INTEGRATION_WORKER_BATCH_SIZE=10
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

Production webhook hardening:

```env
TELEGRAM_WEBHOOK_SECRET=<random-secret>
```

When the secret is configured, `POST /webhooks/telegram/approval` requires Telegram's
`X-Telegram-Bot-Api-Secret-Token` header. Configure Telegram with:

```bash
TELEGRAM_BOT_TOKEN=... \
PUBLIC_BASE_URL=https://saleops.duckdns.org \
TELEGRAM_WEBHOOK_SECRET=... \
bash scripts/configure_telegram_webhook.sh
```

The script calls Telegram `setWebhook` without printing the bot token.

## Bitrix24 Handoff Skeleton

Endpoint:

```text
POST /integration-events/{event_id}/dispatch/bitrix24
```

Worker-style drain endpoint:

```text
POST /integrations/bitrix24/drain
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
4. successful sends mark the integration event as `sent`;
5. failed sends increment `attempt_count`, record `last_error`, and set `next_retry_at`;
6. due `queued` and `retry` events can be drained by the worker-style endpoint;
7. repeated failures move the event to `dead_letter` after `INTEGRATION_MAX_ATTEMPTS`.

The optional background worker uses the same drain path. It starts only when
`INTEGRATION_WORKER_ENABLED=true` and `BITRIX24_DRY_RUN=false`, so the public demo cannot
accidentally consume synthetic dry-run events.

The endpoint response includes the adapter result plus the backend event state:

```json
{
  "adapter_key": "bitrix24",
  "status": "not_configured",
  "event_status": "retry",
  "attempt_count": 1,
  "max_attempts": 3
}
```

Dry-run mode leaves the event queued and does not consume attempts. That keeps public checks safe
while preserving the same payload contract a production deployment would send.

Each CRM event has an `idempotency_key` derived from approval id, adapter, and operation. Re-running
the approval handoff path returns the same event instead of creating duplicate CRM writes.

## Why This Shape

- Public demo remains reproducible without secrets.
- External calls are explicit and inspectable.
- Telegram and Bitrix24 credentials stay in `.env` or server secret storage.
- Approval and CRM mutation remain separate auditable steps.
- Integration failures are visible as state, not hidden in logs.
- Retry timing is explicit through `next_retry_at`, so a worker can safely skip events that are not due.
- Background execution is opt-in and visible through `GET /runtime`.
