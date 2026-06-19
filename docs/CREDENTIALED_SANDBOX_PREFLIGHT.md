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

GitHub Actions owner-run mode:

1. Add repository secrets `TELEGRAM_BOT_TOKEN`, `TELEGRAM_APPROVAL_CHAT_ID`,
   `TELEGRAM_WEBHOOK_SECRET`, and/or `BITRIX24_WEBHOOK_URL`.
2. Open **Actions -> Credentialed Sandbox Preflight**.
3. Run the workflow manually with target `telegram`, `bitrix24`, or `all`.
4. Download the `credentialed-sandbox-preflight-*` artifact and inspect the sanitized JSON/text.

The workflow uses the same script, keeps Telegram and Bitrix24 dry-run flags enabled, checks that
the sanitized artifacts do not contain configured secret values, and uploads only the redacted
evidence files.

Current committed live Telegram evidence:

```text
run=https://github.com/AlexGerlitz/ai-ops-workflow-kit/actions/runs/27797326178
mode=live
required_targets=telegram missing_required_targets=none
public_base_url=https://saleops.duckdns.org
telegram=configured=True get_me=passed webhook=passed
bitrix24=configured=False profile=skipped origin=None
secret_boundaries=secrets_printed=False mutating_external_calls=False
```

Bitrix24 now also has a separate sanitized read-only sandbox artifact in `docs/evidence/`. The
committed public workflow still avoids CRM writes; production writes remain gated by
`BITRIX24_DRY_RUN=false` and the outbox worker rollout checklist.

Generated evidence:

| Artifact | Purpose |
| --- | --- |
| [`docs/evidence/credentialed-sandbox-preflight.sanitized.json`](./evidence/credentialed-sandbox-preflight.sanitized.json) | Machine-readable credential boundary result. |
| [`docs/evidence/credentialed-sandbox-preflight.txt`](./evidence/credentialed-sandbox-preflight.txt) | Human-readable summary of the same preflight. |
| [`scripts/credentialed_sandbox_preflight.py`](../scripts/credentialed_sandbox_preflight.py) | Recreates the preflight. |
| [`.github/workflows/credentialed-sandbox-preflight.yml`](../.github/workflows/credentialed-sandbox-preflight.yml) | Manual owner-run workflow that produces sanitized private sandbox evidence from repository secrets. |

## What It Checks

| Check | External behavior |
| --- | --- |
| Telegram `getMe` | Verifies that the bot token is accepted by Telegram. |
| Telegram `getWebhookInfo` | Verifies whether Telegram is pointed at `PUBLIC_BASE_URL/webhooks/telegram/approval`. |
| Bitrix24 `profile` | Verifies that the incoming webhook URL can call a read-only Bitrix24 REST method. |
| Bitrix24 `crm.lead.fields` | Verifies that the incoming webhook has CRM scope without creating or updating records. |

Current committed live Bitrix24 evidence:

```text
mode=live
required_targets=bitrix24 missing_required_targets=none
bitrix24=configured=True profile=passed crm_lead_fields=passed origin=https://b24-jgkzt9.bitrix24.ru
secret_boundaries=secrets_printed=False mutating_external_calls=False
```

Read the sanitized artifacts:

- [`docs/evidence/bitrix24-sandbox-preflight.sanitized.json`](./evidence/bitrix24-sandbox-preflight.sanitized.json)
- [`docs/evidence/bitrix24-sandbox-preflight.txt`](./evidence/bitrix24-sandbox-preflight.txt)
- [`docs/evidence/bitrix24-contract.sanitized.json`](./evidence/bitrix24-contract.sanitized.json)
- [`docs/evidence/bitrix24-contract.txt`](./evidence/bitrix24-contract.txt)

## Safety Boundary

- The script does not print `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, or the Bitrix24 webhook token.
- The Bitrix24 output keeps only the portal origin, not the full webhook URL.
- The Telegram checks do not send messages.
- The Bitrix24 checks use read-only REST methods and do not create or update CRM records.
- `--require-target telegram` and `--require-target bitrix24` let reviewers validate one sandbox
  account at a time without weakening the stricter `--require-credentials` mode.
- Public CI runs this in skipped/no-secret mode so the evidence proves the handoff path without
  depending on private accounts.
- The manual GitHub Actions workflow runs only when triggered by the owner and uploads sanitized
  artifacts instead of committing private credential evidence.

Use the production readiness drill for local failure-mode behavior and this preflight when a
credentialed sandbox is available.
