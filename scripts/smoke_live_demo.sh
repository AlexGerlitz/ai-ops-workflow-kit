#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-https://saleops.duckdns.org}"
CALLBACK_BASE_URL="${2:-$BASE_URL}"

if [[ "$BASE_URL" == "https://leadscore.duckdns.org" && "$CALLBACK_BASE_URL" == "$BASE_URL" ]]; then
  CALLBACK_BASE_URL="https://saleops.duckdns.org"
fi

curl -fsS "$BASE_URL/" | grep -q "AI Sales Ops Control Tower"
payload="$(curl -fsS -X POST "$BASE_URL/demo/run")"
PAYLOAD="$payload" python3 - "$BASE_URL" "$CALLBACK_BASE_URL" <<'PY'
import json
import os
import sys

expected_base_url = sys.argv[1].rstrip("/")
expected_callback_base_url = sys.argv[2].rstrip("/")
payload = json.loads(os.environ["PAYLOAD"])

assert payload["runtime"]["ok"] is True
assert payload["call_analysis"]["score"] >= 80
assert payload["approval"]["status"] == "approved"
assert payload["telegram_approval"]["status"] == "dry_run"
assert payload["bitrix24_dispatch"]["status"] == "dry_run"
approve_url = payload["telegram_approval"]["callback_contract"]["approve"]["url"]
assert approve_url.startswith(expected_callback_base_url + "/approvals/"), approve_url

print("live demo smoke passed")
print(f"base_url={expected_base_url}")
print(f"callback_base_url={expected_callback_base_url}")
print(f"score={payload['call_analysis']['score']}")
print(f"approval={payload['approval']['status']}")
print(f"telegram={payload['telegram_approval']['status']}")
print(f"bitrix24={payload['bitrix24_dispatch']['status']}")
PY
