#!/usr/bin/env bash
set -euo pipefail

: "${TELEGRAM_BOT_TOKEN:?TELEGRAM_BOT_TOKEN is required}"

PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-https://saleops.duckdns.org}"
export PUBLIC_BASE_URL

python3 - <<'PY'
import json
import os
import urllib.request

token = os.environ["TELEGRAM_BOT_TOKEN"]
base_url = os.environ["PUBLIC_BASE_URL"].rstrip("/")
secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
webhook_url = f"{base_url}/webhooks/telegram/approval"

payload: dict[str, object] = {
    "url": webhook_url,
    "allowed_updates": ["callback_query"],
}
if secret:
    payload["secret_token"] = secret

request = urllib.request.Request(
    f"https://api.telegram.org/bot{token}/setWebhook",
    data=json.dumps(payload).encode("utf-8"),
    headers={"content-type": "application/json"},
    method="POST",
)

with urllib.request.urlopen(request, timeout=15) as response:
    body = json.loads(response.read().decode("utf-8"))

if not body.get("ok"):
    raise SystemExit(f"Telegram setWebhook failed: {body}")

print("telegram webhook configured")
print(f"url={webhook_url}")
print(f"secret_token_configured={bool(secret)}")
PY
