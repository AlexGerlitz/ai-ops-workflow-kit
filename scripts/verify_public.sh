#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
DEMO_OUTPUT="${DEMO_OUTPUT:-/tmp/aiops-offer-demo.json}"

"$PYTHON_BIN" -m pytest -q
"$PYTHON_BIN" scripts/run_offer_demo.py > "$DEMO_OUTPUT"

"$PYTHON_BIN" - "$DEMO_OUTPUT" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

assert payload["runtime"]["ok"] is True
assert payload["runtime"]["storage"] == "memory"
assert payload["ingestion"]["chunks"] >= 1
assert payload["rag_context_sources"], "RAG retrieval returned no sources"
assert payload["call_analysis"]["score"] >= 80
assert payload["approval"]["status"] == "approved"
assert payload["telegram_approval"]["adapter_key"] == "telegram.approval"
assert payload["telegram_approval"]["status"] == "dry_run"
assert "approve" in payload["telegram_approval"]["callback_contract"]
assert payload["crm_handoff"]["adapter_key"] == "bitrix24.mock"
assert payload["crm_handoff"]["operation"] == "upsert_lead_follow_up"
assert payload["crm_handoff"]["status"] == "queued"
assert payload["crm_handoff"]["attempt_count"] == 0
assert payload["crm_handoff"]["last_error"] is None
assert payload["bitrix24_dispatch"]["adapter_key"] == "bitrix24"
assert payload["bitrix24_dispatch"]["status"] == "dry_run"
assert payload["bitrix24_dispatch"]["event_status"] == "queued"
assert payload["bitrix24_dispatch"]["attempt_count"] == 0
assert payload["bitrix24_dispatch"]["max_attempts"] >= 1
assert payload["bitrix24_dispatch"]["method"] == "crm.lead.update"

from fastapi.testclient import TestClient
from app.main import app

with TestClient(app) as client:
    demo_response = client.post("/demo/run")
    assert demo_response.status_code == 200
    approval_response = client.post(
        "/approvals",
        json={
            "kind": "content_review",
            "title": "Verify Telegram callback",
            "draft": "Reject this public verification item.",
            "context": {"source": "verify_public"},
        },
    )
    assert approval_response.status_code == 200
    approval_id = approval_response.json()["id"]
    telegram_callback = client.post(
        "/webhooks/telegram/approval",
        json={
            "update_id": 9001,
            "callback_query": {
                "id": "verify-public-callback",
                "from": {"id": 9001, "username": "verify-public"},
                "data": f"reject:{approval_id}",
            },
        },
    )
    assert telegram_callback.status_code == 200
    assert telegram_callback.json()["approval_status"] == "rejected"
    runtime = client.get("/runtime").json()
    metrics = client.get("/metrics").text

assert runtime["ok"] is True
assert runtime["counters"]["demo_runs_total"] >= 1
assert runtime["counters"]["crm_handoffs_queued_total"] >= 1
assert runtime["counters"]["telegram_callbacks_total"] >= 1
assert "bitrix24_dispatch_failures_total" in runtime["counters"]
assert "integration_dead_letters_total" in runtime["counters"]
assert "aiops_runtime_info" in metrics
assert "aiops_demo_runs_total" in metrics

print("public verification passed")
PY
