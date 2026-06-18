# Credentialed Sandbox Preflight

This preflight checks the real Telegram and Bitrix24 credential boundary without sending Telegram
messages or writing CRM records. It is safe to run in public CI without secrets: missing credentials
produce a sanitized skipped evidence artifact.

## Run

Public/no-secret mode:

```bash
python3 scripts/credentialed_sandbox_preflight.py
```

Credentialed sandbox mode:

```bash
PUBLIC_BASE_URL=https://saleops.duckdns.org \
TELEGRAM_BOT_TOKEN=... \
TELEGRAM_WEBHOOK_SECRET=... \
BITRIX24_WEBHOOK_URL=... \
python3 scripts/credentialed_sandbox_preflight.py --require-credentials
```

Partial sandbox mode when only one external account is available:

```bash
PUBLIC_BASE_URL=https://saleops.duckdns.org \
TELEGRAM_BOT_TOKEN=... \
python3 scripts/credentialed_sandbox_preflight.py --require-target telegram

BITRIX24_WEBHOOK_URL=... \
python3 scripts/credentialed_sandbox_preflight.py --require-target bitrix24
```

Generated evidence:

| Artifact | Purpose |
| --- | --- |
| [`docs/evidence/credentialed-sandbox-preflight.sanitized.json`](./evidence/credentialed-sandbox-preflight.sanitized.json) | Machine-readable credential boundary result. |
| [`docs/evidence/credentialed-sandbox-preflight.txt`](./evidence/credentialed-sandbox-preflight.txt) | Human-readable summary of the same preflight. |
| [`scripts/credentialed_sandbox_preflight.py`](../scripts/credentialed_sandbox_preflight.py) | Recreates the preflight. |

## What It Checks

| Check | External behavior |
| --- | --- |
| Telegram `getMe` | Verifies that the bot token is accepted by Telegram. |
| Telegram `getWebhookInfo` | Verifies whether Telegram is pointed at `PUBLIC_BASE_URL/webhooks/telegram/approval`. |
| Bitrix24 `profile` | Verifies that the incoming webhook URL can call a read-only Bitrix24 REST method. |

## Safety Boundary

- The script does not print `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, or the Bitrix24 webhook token.
- The Bitrix24 output keeps only the portal origin, not the full webhook URL.
- The Telegram checks do not send messages.
- The Bitrix24 check uses a read-only REST method and does not create or update CRM records.
- `--require-target telegram` and `--require-target bitrix24` let reviewers validate one sandbox
  account at a time without weakening the stricter `--require-credentials` mode.
- Public CI runs this in skipped/no-secret mode so the evidence proves the handoff path without
  depending on private accounts.

Use the production readiness drill for local failure-mode behavior and this preflight when a
credentialed sandbox is available.
