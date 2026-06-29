#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
DEMO_OUTPUT="${DEMO_OUTPUT:-/tmp/aiops-offer-demo.json}"

"$PYTHON_BIN" -m pytest -q
"$PYTHON_BIN" -m py_compile scripts/reviewer_snapshot.py
"$PYTHON_BIN" -m py_compile scripts/capture_reviewer_evidence.py
"$PYTHON_BIN" -m py_compile scripts/production_readiness_drill.py
"$PYTHON_BIN" -m py_compile scripts/credentialed_sandbox_preflight.py
"$PYTHON_BIN" -m py_compile scripts/bitrix24_contract_evidence.py
"$PYTHON_BIN" -m py_compile scripts/reviewer_acceptance_report.py
"$PYTHON_BIN" -m py_compile scripts/live_telegram_approval_evidence.py
"$PYTHON_BIN" -m py_compile scripts/build_demo_gif.py
"$PYTHON_BIN" -m py_compile scripts/business_scenario_replay.py
"$PYTHON_BIN" scripts/run_offer_demo.py > "$DEMO_OUTPUT"
"$PYTHON_BIN" scripts/business_scenario_replay.py --output-dir /tmp/aiops-business-scenario-replay > /tmp/aiops-business-scenario-replay.txt
"$PYTHON_BIN" scripts/production_readiness_drill.py --output-dir /tmp/aiops-production-readiness-drill > /tmp/aiops-production-readiness-drill.txt
"$PYTHON_BIN" scripts/credentialed_sandbox_preflight.py --output-dir /tmp/aiops-credentialed-sandbox-preflight > /tmp/aiops-credentialed-sandbox-preflight.txt
"$PYTHON_BIN" scripts/bitrix24_contract_evidence.py --output-dir /tmp/aiops-bitrix24-contract > /tmp/aiops-bitrix24-contract.txt
grep -q "business scenario replay passed" /tmp/aiops-business-scenario-replay.txt
grep -q "rag_quality=ok=True passed=2/2 citations_present=True" /tmp/aiops-business-scenario-replay.txt
grep -q "crm_handoff=adapter=bitrix24.mock status=queued" /tmp/aiops-business-scenario-replay.txt
grep -q "bitrix24_dispatch=adapter=bitrix24 status=dry_run" /tmp/aiops-business-scenario-replay.txt
grep -q "credentialed sandbox preflight passed" /tmp/aiops-credentialed-sandbox-preflight.txt
grep -q "mode=skipped_no_credentials" /tmp/aiops-credentialed-sandbox-preflight.txt
grep -q "secrets_printed=False" /tmp/aiops-credentialed-sandbox-preflight.txt
grep -q "bitrix24 contract evidence passed" /tmp/aiops-bitrix24-contract.txt
grep -q "secret_token_leaked=False" /tmp/aiops-bitrix24-contract.txt
grep -q "Employer Trigger Proof" README.md
grep -q "First Slice Playbook" README.md
grep -q "Demo walkthrough" README.md
grep -q "docs/assets/drive-operator-demo.gif" README.md
grep -q "Employer Trigger Proof" docs/PUBLIC_PROOF_STATUS.md
grep -q "First slice playbook" docs/PUBLIC_PROOF_STATUS.md
grep -q "Business scenario replay" docs/PUBLIC_PROOF_STATUS.md
grep -q "Demo Walkthrough" docs/PUBLIC_PROOF_STATUS.md
grep -q "docs/assets/drive-operator-demo.gif" docs/PUBLIC_PROOF_STATUS.md
grep -q "Employer Trigger Proof" docs/ROLE_REQUIREMENTS_MAP.md
grep -q "Employer Trigger Proof" docs/TECHNICAL_REVIEW_PACKET.md
grep -q "DriveDesk AI Operator demo GIF" docs/DEMO_WALKTHROUGH.md
grep -q "Transcript -> RAG -> approval -> CRM-safe handoff" docs/DEMO_WALKTHROUGH.md
grep -q "python3 scripts/build_demo_gif.py" docs/DEMO_WALKTHROUGH.md
grep -q "Last checked: 2026-06-29" docs/PUBLIC_PROOF_STATUS.md
grep -q "CI status route" docs/PUBLIC_PROOF_STATUS.md
grep -q "Checked on 2026-06-29" docs/PUBLIC_PROOF_STATUS.md
grep -q "AI workflow / RAG" docs/EMPLOYER_TRIGGER_PROOF.md
grep -q "CRM/ERP/API integration" docs/EMPLOYER_TRIGGER_PROOF.md
grep -q "Backend/platform ownership" docs/EMPLOYER_TRIGGER_PROOF.md
grep -q "DevOps / reliability" docs/EMPLOYER_TRIGGER_PROOF.md
grep -q "Current Freshness" docs/EMPLOYER_TRIGGER_PROOF.md
grep -q "Current CI route" docs/EMPLOYER_TRIGGER_PROOF.md
grep -q "Visual proof route" docs/EMPLOYER_TRIGGER_PROOF.md
grep -q "One backend-owned workflow slice" docs/EMPLOYER_TRIGGER_PROOF.md
grep -q "Adapter contract, idempotent CRM handoff" docs/EMPLOYER_TRIGGER_PROOF.md
grep -q "First Slice Playbook" docs/EMPLOYER_TRIGGER_PROOF.md
grep -q "RAG / transcript workflow slice" docs/FIRST_SLICE_PLAYBOOK.md
grep -q "CRM handoff slice" docs/FIRST_SLICE_PLAYBOOK.md
grep -q "Human approval slice" docs/FIRST_SLICE_PLAYBOOK.md
grep -q "Reliability slice" docs/FIRST_SLICE_PLAYBOOK.md
grep -q "one runnable command or live route" docs/FIRST_SLICE_PLAYBOOK.md
grep -q "Best First Message" docs/FIRST_SLICE_PLAYBOOK.md
grep -q "business scenario replay" docs/FIRST_SLICE_PLAYBOOK.md
grep -q "52 passed" docs/EMPLOYER_TRIGGER_PROOF.md
grep -q "public verification passed" docs/EMPLOYER_TRIGGER_PROOF.md
grep -q "reviewer observability snapshot" README.md
grep -q "GET /reviewer/observability" README.md
grep -q "reviewer_observability_v1" docs/TECHNICAL_REVIEW_PACKET.md
grep -q "GET /reviewer/observability" docs/PUBLIC_PROOF_STATUS.md

"$PYTHON_BIN" - "$DEMO_OUTPUT" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
gif = Path("docs/assets/drive-operator-demo.gif")
gif_data = gif.read_bytes()
assert gif_data.startswith((b"GIF87a", b"GIF89a"))
assert len(gif_data) > 80_000

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
assert payload["rag_quality"]["ok"] is True
assert payload["rag_quality"]["total"] == 2
assert payload["rag_quality"]["passed"] == 2
assert payload["rag_quality"]["failed"] == 0
assert all(result["passed"] for result in payload["rag_quality"]["results"])
assert all(result["citations"] for result in payload["rag_quality"]["results"])
assert payload["privacy"]["redacted"] is True
assert payload["privacy"]["raw_text_stored"] is False
assert payload["privacy"]["safe_logging"] is True
assert payload["privacy"]["replacement_counts"] == {"email": 1, "phone": 1}
serialized_payload = json.dumps(payload)
assert "maria.petrov@example.com" not in serialized_payload
assert "+41 44 555 12 34" not in serialized_payload
assert "[redacted-email]" in serialized_payload
assert "[redacted-phone]" in serialized_payload
assert payload["transcription"]["provider"] in {"local_stub", "openai_whisper", "deepgram"}
assert payload["transcription"]["status"] == "dry_run"
assert payload["transcription"]["segments"], "Transcription returned no segments"
assert payload["transcription"]["request_contract"]["method"]
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
assert payload["bitrix24_dispatch"]["bitrix_request"]["id"] == "42"
assert "COMMENTS" in payload["bitrix24_dispatch"]["bitrix_request"]["fields"]

workflow_dir = Path("infra/n8n")
for workflow_name in (
    "call-audio-transcription-approval.json",
    "call-transcript-approval.json",
    "google-drive-sales-ops-approval.json",
):
    workflow = json.loads((workflow_dir / workflow_name).read_text(encoding="utf-8"))
    node_urls = {
        node.get("parameters", {}).get("url")
        for node in workflow["nodes"]
        if node["type"] == "n8n-nodes-base.httpRequest"
    }
    if workflow_name.startswith("call-audio"):
        assert "http://api:8080/webhooks/n8n/call-audio" in node_urls
        assert "Call Audio Webhook" in workflow["connections"]
    else:
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
    rag_eval = client.post(
        "/rag/eval",
        json={
            "questions": [
                {
                    "question": "What should Google Drive imports feed?",
                    "expected_source": "gdrive://verify-public-playbook",
                    "required_terms": ["Google Drive imports", "RAG store"],
                    "top_k": 10,
                    "score_floor": 0.05,
                }
            ]
        },
    )
    assert rag_eval.status_code == 200
    rag_eval_body = rag_eval.json()
    assert rag_eval_body["ok"] is True
    assert rag_eval_body["passed"] == 1
    assert rag_eval_body["results"][0]["missing_terms"] == []
    runtime = client.get("/runtime").json()
    reviewer_observability_response = client.get("/reviewer/observability")
    assert reviewer_observability_response.status_code == 200
    reviewer_observability = reviewer_observability_response.json()
    assert reviewer_observability["schema"] == "reviewer_observability_v1"
    assert reviewer_observability["read_only"] is True
    assert reviewer_observability["quality_gates"]["privacy"]["raw_text_stored"] is False
    assert reviewer_observability["quality_gates"]["rag_quality"]["expected_source_eval"] is True
    assert "GET /reviewer/observability" in reviewer_observability["reviewer_actions"]
    llm_runtime_response = client.get("/llm/runtime")
    assert llm_runtime_response.status_code == 200
    llm_runtime = llm_runtime_response.json()
    transcription_runtime_response = client.get("/transcription/runtime")
    assert transcription_runtime_response.status_code == 200
    transcription_runtime = transcription_runtime_response.json()
    audio_response = client.post(
        "/webhooks/n8n/call-audio",
        json={
            "call_id": "VERIFY-AUDIO-1",
            "customer_id": "VERIFY-LEAD-1",
            "audio_uri": "gdrive://verify-audio-1.mp3",
            "audio_mime_type": "audio/mpeg",
            "duration_seconds": 64,
            "language": "en",
            "transcript_hint": (
                "Manager: The buyer approved budget and wants delivery this month.\n"
                "Client: The next step is a technical review tomorrow."
            ),
            "metadata": {"source": "verify_public"},
        },
    )
    assert audio_response.status_code == 200
    audio_body = audio_response.json()
    assert audio_body["transcription"]["status"] == "dry_run"
    assert audio_body["transcription"]["segments"]
    assert audio_body["transcript_result"]["score"] >= 80
    metrics = client.get("/metrics").text

assert runtime["ok"] is True
assert runtime["llm"]["selected_provider"] in {"local", "openai", "claude", "gemini"}
assert set(runtime["llm"]["supported_providers"]) == {"local", "openai", "claude", "gemini"}
assert llm_runtime["selected_provider"] == runtime["llm"]["selected_provider"]
assert transcription_runtime["selected_provider"] in {"local_stub", "openai_whisper", "deepgram"}
assert set(transcription_runtime["supported_providers"]) == {
    "local_stub",
    "openai_whisper",
    "deepgram",
}
assert "OPENAI_API_KEY" in {
    env for provider in llm_runtime["providers"] for env in provider["required_env"]
}
assert "ANTHROPIC_API_KEY" in {
    env for provider in llm_runtime["providers"] for env in provider["required_env"]
}
assert "GEMINI_API_KEY" in {
    env for provider in llm_runtime["providers"] for env in provider["required_env"]
}
assert "DEEPGRAM_API_KEY" in {
    env for provider in transcription_runtime["providers"] for env in provider["required_env"]
}
assert runtime["counters"]["demo_runs_total"] >= 1
assert runtime["counters"]["rag_evaluations_total"] >= 1
assert runtime["counters"]["rag_eval_failures_total"] == 0
assert runtime["counters"]["crm_handoffs_queued_total"] >= 1
assert runtime["counters"]["telegram_callbacks_total"] >= 1
assert runtime["counters"]["audio_transcriptions_total"] >= 1
assert runtime["counters"]["privacy_redacted_transcripts_total"] >= 1
assert runtime["counters"]["privacy_redactions_total"] >= 2
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
assert "aiops_rag_evaluations_total" in metrics
assert "aiops_audio_transcriptions_total" in metrics

print("public verification passed")
PY
