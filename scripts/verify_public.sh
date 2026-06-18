#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
DEMO_OUTPUT="${DEMO_OUTPUT:-/tmp/aiops-offer-demo.json}"

"$PYTHON_BIN" -m pytest -q
"$PYTHON_BIN" -m py_compile scripts/reviewer_snapshot.py
"$PYTHON_BIN" -m py_compile scripts/capture_reviewer_evidence.py
"$PYTHON_BIN" -m py_compile scripts/production_readiness_drill.py
"$PYTHON_BIN" -m py_compile scripts/credentialed_sandbox_preflight.py
"$PYTHON_BIN" -m py_compile scripts/reviewer_acceptance_report.py
"$PYTHON_BIN" scripts/run_offer_demo.py > "$DEMO_OUTPUT"
"$PYTHON_BIN" scripts/production_readiness_drill.py --output-dir /tmp/aiops-production-readiness-drill > /tmp/aiops-production-readiness-drill.txt
"$PYTHON_BIN" scripts/credentialed_sandbox_preflight.py --output-dir /tmp/aiops-credentialed-sandbox-preflight > /tmp/aiops-credentialed-sandbox-preflight.txt
grep -q "credentialed sandbox preflight passed" /tmp/aiops-credentialed-sandbox-preflight.txt
grep -q "mode=skipped_no_credentials" /tmp/aiops-credentialed-sandbox-preflight.txt
grep -q "secrets_printed=False" /tmp/aiops-credentialed-sandbox-preflight.txt

"$PYTHON_BIN" - "$DEMO_OUTPUT" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

assert payload["runtime"]["ok"] is True
assert payload["runtime"]["storage"] == "memory"
assert payload["runtime"]["llm"]["selected_provider"] in {"local", "openai", "claude", "gemini"}
assert set(payload["runtime"]["llm"]["supported_providers"]) == {
    "local",
    "openai",
    "claude",
    "gemini",
}
assert payload["ingestion"]["chunks"] >= 1
assert payload["google_drive_import"]["adapter_key"] == "google_drive"
assert payload["google_drive_import"]["source"].startswith("gdrive://")
assert payload["google_drive_import"]["chunks"] == payload["ingestion"]["chunks"]
assert payload["rag_context_sources"], "RAG retrieval returned no sources"
assert payload["call_analysis"]["score"] >= 80
assert payload["approval"]["status"] == "approved"
assert payload["telegram_approval"]["adapter_key"] == "telegram.approval"
assert payload["telegram_approval"]["status"] == "dry_run"
assert "approve" in payload["telegram_approval"]["callback_contract"]
assert payload["crm_handoff"]["adapter_key"] == "bitrix24.mock"
assert payload["crm_handoff"]["operation"] == "upsert_lead_follow_up"
assert payload["crm_handoff"]["status"] == "queued"
assert payload["crm_handoff"]["idempotency_key"]
assert payload["crm_handoff"]["attempt_count"] == 0
assert payload["crm_handoff"]["last_error"] is None
assert payload["crm_handoff"]["next_retry_at"] is None
assert payload["bitrix24_dispatch"]["adapter_key"] == "bitrix24"
assert payload["bitrix24_dispatch"]["status"] == "dry_run"
assert payload["bitrix24_dispatch"]["event_status"] == "queued"
assert payload["bitrix24_dispatch"]["attempt_count"] == 0
assert payload["bitrix24_dispatch"]["max_attempts"] >= 1
assert payload["bitrix24_dispatch"]["method"] == "crm.lead.update"

workflow_dir = Path("infra/n8n")
for workflow_name in (
    "call-transcript-approval.json",
    "google-drive-sales-ops-approval.json",
):
    workflow = json.loads((workflow_dir / workflow_name).read_text(encoding="utf-8"))
    node_urls = {
        node.get("parameters", {}).get("url")
        for node in workflow["nodes"]
        if node["type"] == "n8n-nodes-base.httpRequest"
    }
    assert "http://api:8080/webhooks/n8n/call-transcript" in node_urls
    if workflow_name.startswith("google-drive"):
        assert "http://api:8080/integrations/google-drive/import" in node_urls
        assert "Sales Ops Webhook" in workflow["connections"]

from fastapi.testclient import TestClient
from app.main import app

with TestClient(app) as client:
    demo_response = client.post("/demo/run")
    assert demo_response.status_code == 200
    drain_response = client.post("/integrations/bitrix24/drain", params={"limit": 100})
    assert drain_response.status_code == 200
    drain_body = drain_response.json()
    assert drain_body["adapter_key"] == "bitrix24"
    assert drain_body["selected"] >= 1
    assert drain_body["dry_run"] >= 1
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
    drive_import = client.post(
        "/integrations/google-drive/import",
        json={
            "file_id": "verify-public-playbook",
            "name": "Verification playbook",
            "mime_type": "application/vnd.google-apps.document",
            "text": "Google Drive imports should feed the same RAG store as direct document ingestion.",
            "metadata": {"source": "verify_public"},
        },
    )
    assert drive_import.status_code == 200
    assert drive_import.json()["source"] == "gdrive://verify-public-playbook"
    drive_query = client.post(
        "/query",
        json={"question": "What should Google Drive imports feed?", "top_k": 10},
    )
    assert drive_query.status_code == 200
    assert any(
        context["source"] == "gdrive://verify-public-playbook"
        for context in drive_query.json()["contexts"]
    )
    runtime = client.get("/runtime").json()
    llm_runtime_response = client.get("/llm/runtime")
    assert llm_runtime_response.status_code == 200
    llm_runtime = llm_runtime_response.json()
    metrics = client.get("/metrics").text

assert runtime["ok"] is True
assert runtime["llm"]["selected_provider"] in {"local", "openai", "claude", "gemini"}
assert set(runtime["llm"]["supported_providers"]) == {"local", "openai", "claude", "gemini"}
assert llm_runtime["selected_provider"] == runtime["llm"]["selected_provider"]
assert "OPENAI_API_KEY" in {
    env for provider in llm_runtime["providers"] for env in provider["required_env"]
}
assert "ANTHROPIC_API_KEY" in {
    env for provider in llm_runtime["providers"] for env in provider["required_env"]
}
assert "GEMINI_API_KEY" in {
    env for provider in llm_runtime["providers"] for env in provider["required_env"]
}
assert runtime["counters"]["demo_runs_total"] >= 1
assert runtime["counters"]["crm_handoffs_queued_total"] >= 1
assert runtime["counters"]["telegram_callbacks_total"] >= 1
assert "bitrix24_dispatch_failures_total" in runtime["counters"]
assert "integration_dead_letters_total" in runtime["counters"]
assert "integration_events_drained_total" in runtime["counters"]
assert "integration_worker_ticks_total" in runtime["counters"]
assert "integration_worker_errors_total" in runtime["counters"]
assert "integration_retries_scheduled_total" in runtime["counters"]
assert runtime["counters"]["google_drive_imports_total"] >= 1
assert runtime["workers"]["bitrix24_outbox"]["enabled"] is False
assert runtime["workers"]["bitrix24_outbox"]["active"] is False
assert "aiops_runtime_info" in metrics
assert "aiops_demo_runs_total" in metrics

print("public verification passed")
PY
