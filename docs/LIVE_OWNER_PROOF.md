# Live Owner Evidence

This page documents the owner-run live surfaces that sit next to the public-safe synthetic demo.

The public `/demo/run` path remains deterministic and integration-safe:

```text
Google Drive fixture -> RAG -> local transcription fixture -> AI scoring -> approval -> dry-run Telegram payload -> dry-run Bitrix24 dispatch
```

The owner-run path shows that the same backend can cross real integration boundaries without making the public demo depend on paid services:

```text
uploaded call / approval item -> live Telegram approval message -> inline Approve callback -> CRM outbox event -> dry-run Bitrix24 drain
```

## Current Evidence

| Evidence | Purpose |
| --- | --- |
| [`docs/evidence/live-telegram-approval.sanitized.json`](./evidence/live-telegram-approval.sanitized.json) | Machine-readable evidence that a real Telegram approval was approved and queued a CRM handoff. |
| [`docs/evidence/live-telegram-approval.txt`](./evidence/live-telegram-approval.txt) | Human-readable summary of the same live approval evidence. |
| [`scripts/live_telegram_approval_evidence.py`](../scripts/live_telegram_approval_evidence.py) | Regenerates the sanitized evidence from a known approved live approval id. |

## Boundary

- Telegram can be live for operator-triggered approval messages.
- `/demo/run` keeps Telegram dry-run, so public visitors cannot spam the owner bot.
- Bitrix24 stays dry-run by default; the project shows request shape, idempotency, retries, and read-only sandbox access without requiring a paid Bitrix24 subscription.
- Deepgram can run for owner-provided uploaded recordings; uploaded files are temporary and are deleted after processing.
- Tokens, chat ids, Bitrix24 webhook tokens, and customer audio are not committed.

## Regenerate

Use an approval id that has already been approved through the Telegram bot:

```bash
TELEGRAM_BOT_TOKEN=... python3 scripts/live_telegram_approval_evidence.py \
  --approval-id <approved-approval-id>
```

The token is used only to read Telegram webhook status. It is not written to the evidence artifacts.
