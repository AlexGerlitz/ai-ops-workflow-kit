#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-https://saleops.duckdns.org}"
CALLBACK_BASE_URL="${2:-$BASE_URL}"

if [[ "$BASE_URL" == "https://leadscore.duckdns.org" && "$CALLBACK_BASE_URL" == "$BASE_URL" ]]; then
  CALLBACK_BASE_URL="https://saleops.duckdns.org"
fi

home_payload="$(curl -fsS "$BASE_URL/")"
grep -q "AI Sales Ops Control Tower" <<<"$home_payload"
grep -q "Google Drive import" <<<"$home_payload"
grep -q "Telegram callback approval" <<<"$home_payload"
grep -q "Outbox drain" <<<"$home_payload"
grep -q "Worker state" <<<"$home_payload"
runtime_payload="$(curl -fsS "$BASE_URL/runtime")"
llm_runtime_payload="$(curl -fsS "$BASE_URL/llm/runtime")"
metrics_payload="$(curl -fsS "$BASE_URL/metrics")"
payload="$(curl -fsS -X POST "$BASE_URL/demo/run")"
approval_payload="$(curl -fsS -X POST "$BASE_URL/approvals" \
  -H "content-type: application/json" \
  -d '{"kind":"content_review","title":"Live Telegram callback smoke","draft":"Reject this synthetic live smoke item.","context":{"source":"live-smoke"}}')"
approval_id="$(APPROVAL_PAYLOAD="$approval_payload" python3 - <<'PY'
import json
import os

print(json.loads(os.environ["APPROVAL_PAYLOAD"])["id"])
PY
)"
telegram_callback_payload="$(python3 - "$approval_id" <<'PY'
import json
import sys

approval_id = sys.argv[1]
print(json.dumps({
    "update_id": 9001,
    "callback_query": {
        "id": "live-smoke-callback",
        "from": {"id": 9001, "username": "live-smoke"},
        "data": f"reject:{approval_id}",
        "message": {"message_id": 1, "chat": {"id": 9001, "type": "private"}},
    },
}))
PY
)"
telegram_callback_response="$(curl -fsS -X POST "$BASE_URL/webhooks/telegram/approval" \
  -H "content-type: application/json" \
  -d "$telegram_callback_payload")"
drain_response="$(curl -fsS -X POST "$BASE_URL/integrations/bitrix24/drain?limit=100")"
RUNTIME_PAYLOAD="$runtime_payload" LLM_RUNTIME_PAYLOAD="$llm_runtime_payload" METRICS_PAYLOAD="$metrics_payload" PAYLOAD="$payload" TELEGRAM_CALLBACK_RESPONSE="$telegram_callback_response" DRAIN_RESPONSE="$drain_response" python3 - "$BASE_URL" "$CALLBACK_BASE_URL" <<'PY'
import json
import os
import sys

expected_base_url = sys.argv[1].rstrip("/")
expected_callback_base_url = sys.argv[2].rstrip("/")
payload = json.loads(os.environ["PAYLOAD"])
runtime_payload = json.loads(os.environ["RUNTIME_PAYLOAD"])
llm_runtime_payload = json.loads(os.environ["LLM_RUNTIME_PAYLOAD"])
metrics_payload = os.environ["METRICS_PAYLOAD"]
telegram_callback_response = json.loads(os.environ["TELEGRAM_CALLBACK_RESPONSE"])
drain_response = json.loads(os.environ["DRAIN_RESPONSE"])

assert runtime_payload["ok"] is True
assert runtime_payload["public_base_url"] == expected_callback_base_url
assert runtime_payload["llm"]["selected_provider"] in {"local", "openai", "claude", "gemini"}
assert set(runtime_payload["llm"]["supported_providers"]) == {
    "local",
    "openai",
    "claude",
    "gemini",
}
assert llm_runtime_payload["selected_provider"] == runtime_payload["llm"]["selected_provider"]
required_env = {
    env for provider in llm_runtime_payload["providers"] for env in provider["required_env"]
}
assert {"OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"} <= required_env
assert "demo_runs_total" in runtime_payload["counters"]
assert runtime_payload["workers"]["bitrix24_outbox"]["enabled"] is False
assert runtime_payload["workers"]["bitrix24_outbox"]["active"] is False
assert "aiops_runtime_info" in metrics_payload
assert payload["runtime"]["ok"] is True
assert payload["runtime"]["llm"]["selected_provider"] == runtime_payload["llm"]["selected_provider"]
assert payload["google_drive_import"]["adapter_key"] == "google_drive"
assert payload["google_drive_import"]["source"].startswith("gdrive://")
assert payload["call_analysis"]["score"] >= 80
assert payload["approval"]["status"] == "approved"
assert payload["telegram_approval"]["status"] == "dry_run"
assert payload["bitrix24_dispatch"]["status"] == "dry_run"
assert payload["crm_handoff"]["status"] == "queued"
assert payload["crm_handoff"]["idempotency_key"]
assert payload["crm_handoff"]["attempt_count"] == 0
assert payload["crm_handoff"]["next_retry_at"] is None
assert payload["bitrix24_dispatch"]["event_status"] == "queued"
assert payload["bitrix24_dispatch"]["attempt_count"] == 0
assert payload["bitrix24_dispatch"]["max_attempts"] >= 1
assert drain_response["adapter_key"] == "bitrix24"
assert drain_response["selected"] >= 1
assert drain_response["dry_run"] >= 1
approve_url = payload["telegram_approval"]["callback_contract"]["approve"]["url"]
assert approve_url.startswith(expected_callback_base_url + "/approvals/"), approve_url
telegram_webhook_url = payload["telegram_approval"]["callback_contract"]["telegram_webhook"]["url"]
assert telegram_webhook_url == expected_callback_base_url + "/webhooks/telegram/approval"
assert telegram_callback_response["ok"] is True
assert telegram_callback_response["action"] == "reject"
assert telegram_callback_response["approval_status"] == "rejected"

print("live demo smoke passed")
print(f"base_url={expected_base_url}")
print(f"callback_base_url={expected_callback_base_url}")
print(f"version={runtime_payload['version']}")
print(f"git_sha={runtime_payload['git_sha']}")
print(f"llm={runtime_payload['llm']['selected_provider']}")
print(f"score={payload['call_analysis']['score']}")
print(f"google_drive={payload['google_drive_import']['source']}")
print(f"approval={payload['approval']['status']}")
print(f"telegram_callback={telegram_callback_response['approval_status']}")
print(f"telegram={payload['telegram_approval']['status']}")
print(f"bitrix24={payload['bitrix24_dispatch']['status']}")
print(f"crm_event_status={payload['bitrix24_dispatch']['event_status']}")
print(f"bitrix24_drain={drain_response['dry_run']}")
print(f"worker_active={runtime_payload['workers']['bitrix24_outbox']['active']}")
PY
