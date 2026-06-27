import json
import time
from pathlib import Path
from uuid import UUID

import httpx
from fastapi.testclient import TestClient

from app.llm import (
    LLMClient,
    build_claude_payload,
    build_gemini_payload,
    build_openai_payload,
    parse_claude_response,
    parse_gemini_response,
    parse_openai_response,
)
from app.main import app, queue_crm_handoff_if_needed, settings, store
from app.schemas import (
    CallAudioWebhookIn,
    RetrievedContext,
    TranscriptionOut,
    TranscriptionSegmentOut,
    TranscriptionStatus,
)
from app.settings import Settings
from app.transcription import transcribe_call_audio_with_client


def test_health_endpoint_reports_runtime() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_runtime_and_metrics_endpoints_expose_operational_evidence() -> None:
    with TestClient(app) as client:
        runtime = client.get("/runtime")
        metrics = client.get("/metrics")
    assert runtime.status_code == 200
    body = runtime.json()
    assert body["ok"] is True
    assert body["version"]
    assert body["git_sha"]
    assert body["storage"] in {"memory", "postgres"}
    assert "demo_runs_total" in body["counters"]
    assert body["workers"]["bitrix24_outbox"]["enabled"] is False
    assert body["workers"]["bitrix24_outbox"]["active"] is False
    assert body["llm"]["selected_provider"] in {"local", "openai", "claude", "gemini"}
    assert set(body["llm"]["supported_providers"]) == {"local", "openai", "claude", "gemini"}
    assert metrics.status_code == 200
    assert "aiops_runtime_info" in metrics.text
    assert "aiops_demo_runs_total" in metrics.text


def test_llm_runtime_endpoint_exposes_provider_boundary_without_secrets() -> None:
    with TestClient(app) as client:
        response = client.get("/llm/runtime")
    assert response.status_code == 200
    body = response.json()
    assert body["requested_provider"] in {"auto", "local", "openai", "claude", "gemini"}
    assert body["selected_provider"] in {"local", "openai", "claude", "gemini"}
    provider_names = {provider["provider"] for provider in body["providers"]}
    assert provider_names == {"local", "openai", "claude", "gemini"}
    required_env = {
        provider["provider"]: provider["required_env"] for provider in body["providers"]
    }
    assert required_env["openai"] == ["OPENAI_API_KEY"]
    assert required_env["claude"] == ["ANTHROPIC_API_KEY"]
    assert required_env["gemini"] == ["GEMINI_API_KEY"]
    serialized = json.dumps(body)
    assert "sk-" not in serialized
    assert "AAG" not in serialized


def test_transcription_runtime_exposes_provider_boundary_without_secrets() -> None:
    with TestClient(app) as client:
        response = client.get("/transcription/runtime")
    assert response.status_code == 200
    body = response.json()
    assert body["selected_provider"] in {"local_stub", "openai_whisper", "deepgram"}
    assert body["dry_run"] is True
    provider_names = {provider["provider"] for provider in body["providers"]}
    assert provider_names == {"local_stub", "openai_whisper", "deepgram"}
    required_env = {
        provider["provider"]: provider["required_env"] for provider in body["providers"]
    }
    assert required_env["local_stub"] == []
    assert required_env["openai_whisper"] == ["OPENAI_API_KEY"]
    assert required_env["deepgram"] == ["DEEPGRAM_API_KEY"]
    serialized = json.dumps(body)
    assert "sk-" not in serialized
    assert "AAG" not in serialized


def test_openai_whisper_live_transcription_contract_is_parsed() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "GET":
            return httpx.Response(200, content=b"fake mp3 bytes")
        assert request.url == "https://api.openai.com/v1/audio/transcriptions"
        assert request.headers["authorization"] == "Bearer openai-test-key"
        assert request.headers["content-type"].startswith("multipart/form-data")
        return httpx.Response(
            200,
            json={
                "text": "Manager: Budget approved.\nClient: Start this month.",
                "segments": [
                    {"start": 0.0, "end": 2.5, "text": "Manager: Budget approved."},
                    {"start": 2.5, "end": 5.0, "text": "Client: Start this month."},
                ],
            },
        )

    payload = CallAudioWebhookIn(
        call_id="CALL-OPENAI-1",
        customer_id="LEAD-OPENAI-1",
        audio_uri="https://storage.example/calls/openai.mp3",
        audio_mime_type="audio/mpeg",
        language="en",
    )
    config = Settings(
        transcription_provider="openai_whisper",
        transcription_dry_run=False,
        openai_api_key="openai-test-key",
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        result = transcribe_call_audio_with_client(payload, config, http_client)

    assert [request.method for request in requests] == ["GET", "POST"]
    assert result.status == "transcribed"
    assert result.provider == "openai_whisper"
    assert "Budget approved" in result.transcript
    assert len(result.segments) == 2
    assert result.request_contract["secret_fields"] == ["OPENAI_API_KEY"]
    assert "openai-test-key" not in json.dumps(result.model_dump())


def test_deepgram_live_transcription_contract_is_parsed() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.url.host == "api.deepgram.com"
        assert request.headers["authorization"] == "Token deepgram-test-key"
        return httpx.Response(
            200,
            json={
                "results": {
                    "channels": [
                        {
                            "alternatives": [
                                {
                                    "transcript": "Budget approved. Start this month.",
                                    "confidence": 0.93,
                                    "words": [
                                        {
                                            "word": "Budget",
                                            "punctuated_word": "Budget",
                                            "start": 0.0,
                                            "end": 0.3,
                                            "speaker": 0,
                                        },
                                        {
                                            "word": "approved",
                                            "punctuated_word": "approved.",
                                            "start": 0.3,
                                            "end": 0.8,
                                            "speaker": 0,
                                        },
                                        {
                                            "word": "Start",
                                            "punctuated_word": "Start",
                                            "start": 0.8,
                                            "end": 1.1,
                                            "speaker": 1,
                                        },
                                        {
                                            "word": "month",
                                            "punctuated_word": "month.",
                                            "start": 1.1,
                                            "end": 1.7,
                                            "speaker": 1,
                                        },
                                    ],
                                }
                            ]
                        }
                    ]
                }
            },
        )

    payload = CallAudioWebhookIn(
        call_id="CALL-DEEPGRAM-1",
        customer_id="LEAD-DEEPGRAM-1",
        audio_uri="https://storage.example/calls/deepgram.mp3",
        audio_mime_type="audio/mpeg",
        language="en",
    )
    config = Settings(
        transcription_provider="deepgram",
        transcription_dry_run=False,
        deepgram_api_key="deepgram-test-key",
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as http_client:
        result = transcribe_call_audio_with_client(payload, config, http_client)

    assert len(requests) == 1
    assert requests[0].headers["content-type"] == "application/json"
    assert result.status == "transcribed"
    assert result.provider == "deepgram"
    assert result.confidence == 0.93
    assert [segment.speaker for segment in result.segments] == ["speaker_0", "speaker_1"]
    assert "deepgram-test-key" not in json.dumps(result.model_dump())


def test_llm_client_selects_configured_provider_and_falls_back_locally() -> None:
    local_client = LLMClient(provider="auto")
    assert local_client.selected_provider == "local"
    assert local_client.runtime()["fallback"] is True

    openai_client = LLMClient(provider="auto", openai_api_key="openai-test-key")
    assert openai_client.selected_provider == "openai"
    assert openai_client.runtime()["configured_providers"] == ["openai"]

    claude_client = LLMClient(provider="anthropic", anthropic_api_key="anthropic-test-key")
    assert claude_client.selected_provider == "claude"

    gemini_client = LLMClient(provider="gemini", gemini_api_key="gemini-test-key")
    assert gemini_client.selected_provider == "gemini"

    missing_key_client = LLMClient(provider="openai")
    assert missing_key_client.selected_provider == "local"
    assert missing_key_client.runtime()["fallback"] is True


def test_llm_provider_payloads_and_response_parsers_are_contract_tested() -> None:
    context = RetrievedContext(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        source="gdrive://sales-playbook",
        text="Discovery should confirm budget and next step.",
        metadata={"team": "sales"},
        score=0.91,
    )

    openai_payload = build_openai_payload("What should discovery confirm?", [context], "gpt-x")
    claude_payload = build_claude_payload("What should discovery confirm?", [context], "claude-x")
    gemini_payload = build_gemini_payload("What should discovery confirm?", [context], "gemini-x")

    assert openai_payload["model"] == "gpt-x"
    assert openai_payload["messages"][0]["role"] == "system"
    assert "gdrive://sales-playbook" in openai_payload["messages"][1]["content"]
    assert claude_payload["model"] == "claude-x"
    assert claude_payload["max_tokens"] > 0
    assert claude_payload["messages"][0]["role"] == "user"
    assert gemini_payload["contents"][0]["parts"][0]["text"].startswith("Answer from")
    assert gemini_payload["generationConfig"]["temperature"] == 0.2

    assert (
        parse_openai_response({"choices": [{"message": {"content": "OpenAI answer"}}]})
        == "OpenAI answer"
    )
    assert parse_claude_response({"content": [{"type": "text", "text": "Claude answer"}]}) == (
        "Claude answer"
    )
    assert parse_gemini_response(
        {"candidates": [{"content": {"parts": [{"text": "Gemini answer"}]}}]}
    ) == "Gemini answer"


def test_public_demo_page_is_available() -> None:
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "AI Sales Ops Control Tower" in response.text
    assert "Run demo workflow" in response.text
    assert "Document/CRM knowledge intake" in response.text
    assert "Telegram callback approval" in response.text
    assert "Outbox drain" in response.text
    assert "Worker state" in response.text
    assert "Transcribe uploaded call" in response.text
    assert "/integrations/google-drive/import" in response.text
    assert "/integrations/bitrix24/drain" in response.text
    assert "/demo/audio/upload" in response.text


def test_integration_runtime_reports_dry_run_capabilities() -> None:
    with TestClient(app) as client:
        response = client.get("/integrations/runtime")
    assert response.status_code == 200
    body = response.json()
    capabilities = {item["adapter_key"]: item for item in body["capabilities"]}
    assert capabilities["telegram.approval"]["dry_run"] is True
    assert capabilities["google_drive"]["dry_run"] is True
    assert capabilities["google_drive"]["configured"] is False
    assert capabilities["bitrix24"]["dry_run"] is True
    assert capabilities["telegram.approval"]["webhook_secret_configured"] is False


def test_n8n_workflow_artifacts_cover_drive_import_and_transcript_analysis() -> None:
    workflow_dir = Path("infra/n8n")
    transcript_workflow = json.loads(
        (workflow_dir / "call-transcript-approval.json").read_text(encoding="utf-8")
    )
    drive_workflow = json.loads(
        (workflow_dir / "google-drive-sales-ops-approval.json").read_text(encoding="utf-8")
    )
    audio_workflow = json.loads(
        (workflow_dir / "call-audio-transcription-approval.json").read_text(encoding="utf-8")
    )

    transcript_urls = {
        node.get("parameters", {}).get("url")
        for node in transcript_workflow["nodes"]
        if node["type"] == "n8n-nodes-base.httpRequest"
    }
    assert "http://api:8080/webhooks/n8n/call-transcript" in transcript_urls

    drive_nodes = {node["name"]: node for node in drive_workflow["nodes"]}
    assert drive_nodes["Sales Ops Webhook"]["type"] == "n8n-nodes-base.webhook"
    assert (
        drive_nodes["Import Google Drive Text"]["parameters"]["url"]
        == "http://api:8080/integrations/google-drive/import"
    )
    assert (
        drive_nodes["Analyze Transcript"]["parameters"]["url"]
        == "http://api:8080/webhooks/n8n/call-transcript"
    )
    assert "Drive source:" in drive_nodes["Build Telegram Approval Payload"]["parameters"][
        "assignments"
    ]["assignments"][2]["value"]
    assert drive_workflow["connections"]["Sales Ops Webhook"]["main"][0][0]["node"] == (
        "Import Google Drive Text"
    )
    assert drive_workflow["connections"]["Import Google Drive Text"]["main"][0][0]["node"] == (
        "Analyze Transcript"
    )

    audio_urls = {
        node.get("parameters", {}).get("url")
        for node in audio_workflow["nodes"]
        if node["type"] == "n8n-nodes-base.httpRequest"
    }
    assert "http://api:8080/webhooks/n8n/call-audio" in audio_urls
    assert audio_workflow["connections"]["Call Audio Webhook"]["main"][0][0]["node"] == (
        "Transcribe And Analyze Audio"
    )


def test_public_demo_run_proves_workflow_contract() -> None:
    with TestClient(app) as client:
        response = client.post("/demo/run")
    assert response.status_code == 200
    body = response.json()
    assert body["runtime"]["ok"] is True
    assert body["ingestion"]["chunks"] >= 1
    assert body["google_drive_import"]["adapter_key"] == "google_drive"
    assert body["google_drive_import"]["source"] == "gdrive://demo-sales-playbook"
    assert body["google_drive_import"]["chunks"] == body["ingestion"]["chunks"]
    assert body["rag_context_sources"]
    assert body["rag_quality"]["ok"] is True
    assert body["rag_quality"]["total"] == 2
    assert body["rag_quality"]["passed"] == 2
    assert all(result["passed"] for result in body["rag_quality"]["results"])
    assert all(result["citations"] for result in body["rag_quality"]["results"])
    assert body["transcription"]["provider"] == "local_stub"
    assert body["transcription"]["status"] == "dry_run"
    assert body["transcription"]["audio_uri"].startswith("gdrive://")
    assert body["transcription"]["segments"]
    assert body["privacy"]["redacted"] is True
    assert body["privacy"]["raw_text_stored"] is False
    assert body["privacy"]["safe_logging"] is True
    assert body["privacy"]["replacement_counts"] == {"email": 1, "phone": 1}
    serialized = json.dumps(body)
    assert "maria.petrov@example.com" not in serialized
    assert "+41 44 555 12 34" not in serialized
    assert "[redacted-email]" in serialized
    assert "[redacted-phone]" in serialized
    assert body["transcription"]["request_contract"]["secret_fields"] == []
    assert body["call_analysis"]["score"] >= 80
    assert body["approval"]["status"] == "approved"
    assert body["telegram_approval"]["status"] == "dry_run"
    assert body["telegram_approval"]["callback_contract"]["approve"]["url"].endswith("/approve")
    assert body["crm_handoff"]["status"] == "queued"
    assert body["crm_handoff"]["idempotency_key"]
    assert body["crm_handoff"]["next_retry_at"] is None
    assert body["bitrix24_dispatch"]["status"] == "dry_run"
    runtime = client.get("/runtime").json()
    assert runtime["counters"]["demo_runs_total"] >= 1
    assert runtime["counters"]["rag_evaluations_total"] >= 1
    assert runtime["counters"]["rag_eval_failures_total"] == 0
    assert runtime["counters"]["audio_transcriptions_total"] >= 1
    assert runtime["counters"]["crm_handoffs_queued_total"] >= 1
    assert runtime["counters"]["privacy_redacted_transcripts_total"] >= 1
    assert runtime["counters"]["privacy_redactions_total"] >= 2


def test_public_demo_run_replaces_synthetic_rag_sources() -> None:
    with TestClient(app) as client:
        first = client.post("/demo/run")
        second = client.post("/demo/run")

    assert first.status_code == 200
    assert second.status_code == 200
    chunks = getattr(store, "chunks", None)
    assert chunks is not None
    demo_sources = [
        chunk.source
        for chunk in chunks
        if chunk.source in {"gdrive://demo-sales-playbook", "call://CALL-LIVE-DEMO-1"}
    ]
    assert demo_sources.count("gdrive://demo-sales-playbook") == 1
    assert demo_sources.count("call://CALL-LIVE-DEMO-1") == 1


def test_call_transcript_redacts_pii_before_rag_approval_and_crm() -> None:
    raw_email = "buyer.ops@example.com"
    raw_phone = "+41 79 555 10 20"
    with TestClient(app) as client:
        response = client.post(
            "/webhooks/n8n/call-transcript",
            json={
                "call_id": "CALL-PRIVACY-1",
                "customer_id": "LEAD-PRIVACY-1",
                "transcript": (
                    "The director approved the budget and needs delivery this month. "
                    "The next step is a technical review tomorrow. "
                    f"Send recap to {raw_email} and call {raw_phone}."
                ),
                "metadata": {"source": "privacy-test"},
            },
        )
        assert response.status_code == 200
        body = response.json()
        approval = client.get(f"/approvals/{body['approval']['id']}").json()
        query = client.post(
            "/query",
            json={"question": "Where should the recap be sent?", "top_k": 10},
        )
        approved = client.post(
            f"/approvals/{body['approval']['id']}/approve",
            json={"reviewer": "privacy-reviewer", "notes": "Safe to queue"},
        )
        assert approved.status_code == 200
        events = client.get("/integration-events", params={"adapter_key": "bitrix24.mock"})

    serialized = json.dumps(
        {
            "webhook": body,
            "approval": approval,
            "query": query.json(),
            "events": events.json(),
        },
    )
    assert body["privacy"]["redacted"] is True
    assert body["privacy"]["replacement_counts"] == {"email": 1, "phone": 1}
    assert raw_email not in serialized
    assert raw_phone not in serialized
    assert "[redacted-email]" in serialized
    assert "[redacted-phone]" in serialized
    assert approval["context"]["privacy"]["raw_text_stored"] is False
    assert approval["context"]["crm_update"]["comment"].endswith("[redacted-phone].")


def test_ingest_query_and_approval_flow() -> None:
    with TestClient(app) as client:
        ingest = client.post(
            "/documents",
            json={
                "source": "drive://playbook",
                "text": "Discovery calls should confirm budget, authority, need, timing, and next step.",
                "metadata": {"team": "sales"},
            },
        )
        assert ingest.status_code == 200
        assert ingest.json()["chunks"] == 1

        query = client.post(
            "/query",
            json={"question": "What should discovery confirm?", "top_k": 1},
        )
        assert query.status_code == 200
        assert query.json()["contexts"][0]["source"] == "drive://playbook"

        evaluation = client.post(
            "/rag/eval",
            json={
                "questions": [
                    {
                        "question": "What should discovery calls confirm?",
                        "expected_source": "drive://playbook",
                        "required_terms": ["budget", "authority", "need", "timing"],
                        "top_k": 10,
                        "score_floor": 0.05,
                    }
                ]
            },
        )
        assert evaluation.status_code == 200
        evaluation_body = evaluation.json()
        assert evaluation_body["ok"] is True
        assert evaluation_body["passed"] == 1
        assert evaluation_body["results"][0]["matched_source"] is True
        assert evaluation_body["results"][0]["missing_terms"] == []

        approval = client.post(
            "/approvals",
            json={
                "kind": "content_review",
                "title": "Review follow-up",
                "draft": "Send recap.",
                "context": {"lead_id": "L-1"},
            },
        )
        assert approval.status_code == 200
        approval_id = approval.json()["id"]

        approved = client.post(
            f"/approvals/{approval_id}/approve",
            json={"reviewer": "owner", "notes": "approved"},
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == "approved"


def test_google_drive_import_contract_feeds_rag_store() -> None:
    with TestClient(app) as client:
        drive_import = client.post(
            "/integrations/google-drive/import",
            json={
                "file_id": "playbook-google-drive-1",
                "name": "Google Drive Sales Playbook",
                "mime_type": "application/vnd.google-apps.document",
                "text": "Google Drive playbooks should be exported, normalized, chunked, and queried through RAG.",
                "web_url": "https://drive.google.com/file/d/playbook-google-drive-1",
                "metadata": {"team": "sales", "folder": "knowledge-base"},
            },
        )
        assert drive_import.status_code == 200
        imported = drive_import.json()
        assert imported["adapter_key"] == "google_drive"
        assert imported["operation"] == "import_exported_text"
        assert imported["dry_run"] is True
        assert imported["source"] == "gdrive://playbook-google-drive-1"
        assert imported["metadata"]["adapter"] == "google_drive"
        assert imported["chunks"] >= 1

        query = client.post(
            "/query",
            json={"question": "What should Google Drive playbooks do?", "top_k": 10},
        )
        assert query.status_code == 200
        assert any(
            context["source"] == "gdrive://playbook-google-drive-1"
            for context in query.json()["contexts"]
        )

        runtime = client.get("/runtime").json()
        assert runtime["counters"]["google_drive_imports_total"] >= 1


def test_call_audio_webhook_transcribes_and_continues_to_approval_flow() -> None:
    with TestClient(app) as client:
        playbook = client.post(
            "/documents",
            json={
                "source": "drive://audio-sales-playbook",
                "text": "Audio call follow-up should be reviewed before CRM updates are sent.",
                "metadata": {"team": "sales", "demo": True},
            },
        )
        assert playbook.status_code == 200

        response = client.post(
            "/webhooks/n8n/call-audio",
            json={
                "call_id": "CALL-AUDIO-1",
                "customer_id": "LEAD-42",
                "audio_uri": "gdrive://calls/CALL-AUDIO-1.mp3",
                "audio_mime_type": "audio/mpeg",
                "duration_seconds": 90,
                "language": "en",
                "transcript_hint": (
                    "Manager: The director approved the budget. "
                    "Client: We need the workflow this month. "
                    "Manager: The next step is a meeting tomorrow."
                ),
                "metadata": {"source": "audio-webhook-test"},
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["transcription"]["status"] == "dry_run"
        assert body["transcription"]["provider"] == "local_stub"
        assert body["transcription"]["segments"]
        assert body["transcript_result"]["call_id"] == "CALL-AUDIO-1"
        assert body["transcript_result"]["score"] >= 80
        assert body["transcript_result"]["approval"]["status"] == "pending"
        assert body["transcript_result"]["analysis"]["crm_update"]["customer_id"] == "LEAD-42"
        assert body["transcript_result"]["analysis"]["crm_update"]["adapter"] == "bitrix24.mock"

        runtime = client.get("/runtime").json()
        assert runtime["counters"]["audio_webhooks_total"] >= 1
        assert runtime["counters"]["audio_transcriptions_total"] >= 1
        assert runtime["counters"]["transcript_webhooks_total"] >= 1


def test_audio_upload_endpoint_runs_live_pipeline_without_exposing_temp_path(monkeypatch) -> None:
    seen: dict[str, str] = {}

    def fake_transcribe(payload: CallAudioWebhookIn, config: Settings) -> TranscriptionOut:
        seen["audio_uri"] = payload.audio_uri
        assert Path(payload.audio_uri).exists()
        assert payload.audio_mime_type == "audio/mp4"
        assert payload.provider == "deepgram"
        assert config.transcription_provider == "deepgram"
        assert config.transcription_dry_run is False
        return TranscriptionOut(
            provider="deepgram",
            status=TranscriptionStatus.transcribed,
            audio_uri=payload.audio_uri,
            audio_mime_type=payload.audio_mime_type,
            language=payload.language,
            duration_seconds=None,
            transcript=(
                "Manager: The director approved the budget. "
                "Client: We need the workflow this month. "
                "Manager: The next step is a meeting tomorrow."
            ),
            segments=[
                TranscriptionSegmentOut(
                    speaker="speaker_0",
                    start_seconds=0.0,
                    end_seconds=5.0,
                    text="Manager: The director approved the budget.",
                )
            ],
            confidence=0.98,
            detail="Fake upload transcript.",
            request_contract={
                "method": "POST",
                "url": "https://api.deepgram.com/v1/listen",
                "audio_uri": payload.audio_uri,
                "secret_fields": ["DEEPGRAM_API_KEY"],
            },
        )

    monkeypatch.setattr("app.main.transcribe_call_audio", fake_transcribe)

    with TestClient(app) as client:
        response = client.post(
            "/demo/audio/upload",
            data={
                "call_id": "CALL-UPLOAD-1",
                "customer_id": "LEAD-UPLOAD-1",
                "language": "en",
                "provider": "deepgram",
            },
            files={"file": ("sales-call.m4a", b"fake m4a bytes", "audio/mp4")},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["upload"]["filename"] == "sales-call.m4a"
    assert body["upload"]["stored"] == "temporary"
    assert body["transcription"]["provider"] == "deepgram"
    assert body["transcription"]["status"] == "transcribed"
    assert body["transcription"]["audio_uri"] == "upload://sales-call.m4a"
    assert body["transcription"]["request_contract"]["audio_uri"] == "upload://sales-call.m4a"
    assert body["transcription"]["request_contract"]["body"] == {"file": "uploaded audio bytes"}
    assert body["transcript_result"]["score"] >= 80
    assert body["transcript_result"]["approval"]["status"] == "pending"
    assert body["telegram_approval"]["adapter_key"] == "telegram.approval"
    assert body["telegram_approval"]["status"] == "dry_run"
    assert Path(seen["audio_uri"]).is_absolute()
    assert not Path(seen["audio_uri"]).exists()
    assert seen["audio_uri"] not in json.dumps(body)


def test_telegram_approval_notification_dry_run_contract() -> None:
    with TestClient(app) as client:
        approval = client.post(
            "/approvals",
            json={
                "kind": "content_review",
                "title": "Review follow-up",
                "draft": "Send recap.",
                "context": {"lead_id": "L-telegram"},
            },
        )
        assert approval.status_code == 200
        approval_id = approval.json()["id"]

        notify = client.post(f"/approvals/{approval_id}/notify/telegram")
        assert notify.status_code == 200
        body = notify.json()
        assert body["adapter_key"] == "telegram.approval"
        assert body["status"] == "dry_run"
        assert body["payload"]["reply_markup"]["inline_keyboard"]
        assert body["payload"]["callback_contract"]["approve"]["method"] == "POST"
        assert body["payload"]["callback_contract"]["telegram_webhook"]["url"].endswith(
            "/webhooks/telegram/approval"
        )


def test_telegram_callback_approves_item_and_queues_crm_handoff() -> None:
    with TestClient(app) as client:
        webhook = client.post(
            "/webhooks/n8n/call-transcript",
            json={
                "call_id": "CALL-TELEGRAM-1",
                "customer_id": "LEAD-TG-42",
                "transcript": (
                    "The director approved the budget. They need the rollout this month "
                    "and agreed that the next step is a short implementation call tomorrow."
                ),
                "metadata": {"source": "telegram-test"},
            },
        )
        assert webhook.status_code == 200
        approval_id = webhook.json()["approval"]["id"]

        callback = client.post(
            "/webhooks/telegram/approval",
            json={
                "update_id": 1001,
                "callback_query": {
                    "id": "callback-1",
                    "from": {"id": 7001, "username": "saleslead"},
                    "data": f"approve:{approval_id}",
                    "message": {"message_id": 55, "chat": {"id": 12345, "type": "private"}},
                },
            },
        )
        assert callback.status_code == 200
        body = callback.json()
        assert body["ok"] is True
        assert body["action"] == "approve"
        assert body["approval_status"] == "approved"
        assert body["reviewer"] == "saleslead"
        assert body["crm_handoff_event_id"]

        events = client.get("/integration-events", params={"adapter_key": "bitrix24.mock"})
        assert events.status_code == 200
        assert any(item["source_approval_id"] == approval_id for item in events.json())
        runtime = client.get("/runtime").json()
        assert runtime["counters"]["telegram_callbacks_total"] >= 1


def test_telegram_callback_secret_is_enforced_when_configured(monkeypatch) -> None:
    monkeypatch.setattr(settings, "telegram_webhook_secret", "expected-secret")
    with TestClient(app) as client:
        approval = client.post(
            "/approvals",
            json={
                "kind": "content_review",
                "title": "Secret protected approval",
                "draft": "Reject this item.",
                "context": {"source": "secret-test"},
            },
        )
        assert approval.status_code == 200
        approval_id = approval.json()["id"]
        callback_payload = {
            "update_id": 2001,
            "callback_query": {
                "id": "callback-secret",
                "from": {"id": 7002, "username": "saleslead"},
                "data": f"reject:{approval_id}",
            },
        }

        rejected = client.post("/webhooks/telegram/approval", json=callback_payload)
        assert rejected.status_code == 403

        accepted = client.post(
            "/webhooks/telegram/approval",
            json=callback_payload,
            headers={"X-Telegram-Bot-Api-Secret-Token": "expected-secret"},
        )
        assert accepted.status_code == 200
        assert accepted.json()["approval_status"] == "rejected"


def test_telegram_callback_answers_query_when_live(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    class Response:
        def raise_for_status(self) -> None:
            return None

    def fake_post(url: str, json: dict[str, object], timeout: float) -> Response:
        calls.append({"url": url, "json": json, "timeout": timeout})
        return Response()

    monkeypatch.setattr(settings, "telegram_dry_run", False)
    monkeypatch.setattr(settings, "telegram_bot_token", "token-for-test")
    monkeypatch.setattr("app.integrations.httpx.post", fake_post)

    with TestClient(app) as client:
        approval = client.post(
            "/approvals",
            json={
                "kind": "content_review",
                "title": "Answer callback",
                "draft": "Approve this item.",
                "context": {"source": "callback-answer-test"},
            },
        )
        assert approval.status_code == 200
        approval_id = approval.json()["id"]

        callback = client.post(
            "/webhooks/telegram/approval",
            json={
                "update_id": 3001,
                "callback_query": {
                    "id": "callback-answer",
                    "from": {"id": 7003, "username": "saleslead"},
                    "data": f"approve:{approval_id}",
                },
            },
        )

    assert callback.status_code == 200
    assert calls == [
        {
            "url": "https://api.telegram.org/bottoken-for-test/answerCallbackQuery",
            "json": {"callback_query_id": "callback-answer", "text": "Approve"},
            "timeout": 5,
        }
    ]


def test_telegram_callback_repeated_click_answers_without_error(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    class Response:
        def raise_for_status(self) -> None:
            return None

    def fake_post(url: str, json: dict[str, object], timeout: float) -> Response:
        calls.append({"url": url, "json": json, "timeout": timeout})
        return Response()

    monkeypatch.setattr(settings, "telegram_dry_run", False)
    monkeypatch.setattr(settings, "telegram_bot_token", "token-for-test")
    monkeypatch.setattr("app.integrations.httpx.post", fake_post)

    with TestClient(app) as client:
        approval = client.post(
            "/approvals",
            json={
                "kind": "content_review",
                "title": "Repeated callback",
                "draft": "Approve once, tap twice.",
                "context": {"source": "callback-repeat-test"},
            },
        )
        assert approval.status_code == 200
        approval_id = approval.json()["id"]

        first = client.post(
            "/webhooks/telegram/approval",
            json={
                "update_id": 3101,
                "callback_query": {
                    "id": "callback-repeat-1",
                    "from": {"id": 7004, "username": "saleslead"},
                    "data": f"approve:{approval_id}",
                },
            },
        )
        second = client.post(
            "/webhooks/telegram/approval",
            json={
                "update_id": 3102,
                "callback_query": {
                    "id": "callback-repeat-2",
                    "from": {"id": 7004, "username": "saleslead"},
                    "data": f"approve:{approval_id}",
                },
            },
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["approval_status"] == "approved"
    assert calls == [
        {
            "url": "https://api.telegram.org/bottoken-for-test/answerCallbackQuery",
            "json": {"callback_query_id": "callback-repeat-1", "text": "Approve"},
            "timeout": 5,
        },
        {
            "url": "https://api.telegram.org/bottoken-for-test/answerCallbackQuery",
            "json": {"callback_query_id": "callback-repeat-2", "text": "Already approved"},
            "timeout": 5,
        },
    ]


def test_offer_demo_call_transcript_queues_crm_handoff_after_approval(monkeypatch) -> None:
    monkeypatch.setattr(settings, "top_k", 50)
    with TestClient(app) as client:
        playbook = client.post(
            "/documents",
            json={
                "source": "drive://sales-playbook-demo",
                "text": (
                    "After a sales call, the manager should review the AI summary, "
                    "confirm budget, authority, need, timing, and next step, then send "
                    "a concise follow-up only after human approval."
                ),
                "metadata": {"team": "sales", "demo": True},
            },
        )
        assert playbook.status_code == 200

        webhook = client.post(
            "/webhooks/n8n/call-transcript",
            json={
                "call_id": "CALL-DEMO-1",
                "customer_id": "LEAD-42",
                "transcript": (
                    "Client says the price may be expensive, but the director approved "
                    "the budget. They need the workflow this month and agreed that the "
                    "next step is a short meeting tomorrow."
                ),
                "metadata": {"source": "demo"},
            },
        )
        assert webhook.status_code == 200
        body = webhook.json()
        assert body["score"] >= 80
        assert body["analysis"]["crm_update"]["adapter"] == "bitrix24.mock"
        assert any(
            context["source"] == "drive://sales-playbook-demo"
            for context in body["analysis"]["knowledge_context"]
        )

        approval_id = body["approval"]["id"]
        approved = client.post(
            f"/approvals/{approval_id}/approve",
            json={"reviewer": "sales-lead", "notes": "Follow-up approved"},
        )
        assert approved.status_code == 200

        events = client.get("/integration-events", params={"adapter_key": "bitrix24.mock"})
        assert events.status_code == 200
        matching_events = [
            item for item in events.json() if item["source_approval_id"] == approval_id
        ]
        assert matching_events
        assert matching_events[0]["operation"] == "upsert_lead_follow_up"
        assert matching_events[0]["payload"]["customer_id"] == "LEAD-42"
        assert matching_events[0]["idempotency_key"]

        dispatch = client.post(
            f"/integration-events/{matching_events[0]['id']}/dispatch/bitrix24"
        )
        assert dispatch.status_code == 200
        dispatch_body = dispatch.json()
        assert dispatch_body["adapter_key"] == "bitrix24"
        assert dispatch_body["status"] == "dry_run"
        assert dispatch_body["event_status"] == "queued"
        assert dispatch_body["attempt_count"] == 0
        assert dispatch_body["payload"]["method"] == "crm.lead.update"
        assert dispatch_body["payload"]["bitrix_request"]["id"] == "42"
        assert "COMMENTS" in dispatch_body["payload"]["bitrix_request"]["fields"]


def test_bitrix24_dispatch_records_retry_state_and_dead_letter(monkeypatch) -> None:
    monkeypatch.setattr(settings, "bitrix24_dry_run", False)
    monkeypatch.setattr(settings, "bitrix24_webhook_url", None)
    monkeypatch.setattr(settings, "integration_max_attempts", 2)

    with TestClient(app) as client:
        webhook = client.post(
            "/webhooks/n8n/call-transcript",
            json={
                "call_id": "CALL-BITRIX-RETRY-1",
                "customer_id": "LEAD-BITRIX-RETRY",
                "transcript": (
                    "The client confirmed budget and authority. They need rollout this "
                    "month and agreed that the next step is a technical call tomorrow."
                ),
                "metadata": {"source": "bitrix-retry-test"},
            },
        )
        assert webhook.status_code == 200
        approval_id = webhook.json()["approval"]["id"]

        approved = client.post(
            f"/approvals/{approval_id}/approve",
            json={"reviewer": "sales-lead", "notes": "Queue CRM handoff"},
        )
        assert approved.status_code == 200

        events = client.get("/integration-events", params={"adapter_key": "bitrix24.mock"})
        assert events.status_code == 200
        event = next(
            item for item in events.json() if item["source_approval_id"] == approval_id
        )
        assert event["attempt_count"] == 0
        assert event["last_error"] is None

        first_dispatch = client.post(
            f"/integration-events/{event['id']}/dispatch/bitrix24"
        )
        assert first_dispatch.status_code == 200
        first_body = first_dispatch.json()
        assert first_body["status"] == "not_configured"
        assert first_body["event_status"] == "retry"
        assert first_body["attempt_count"] == 1
        assert first_body["max_attempts"] == 2

        second_dispatch = client.post(
            f"/integration-events/{event['id']}/dispatch/bitrix24"
        )
        assert second_dispatch.status_code == 200
        second_body = second_dispatch.json()
        assert second_body["status"] == "not_configured"
        assert second_body["event_status"] == "dead_letter"
        assert second_body["attempt_count"] == 2

        updated_events = client.get("/integration-events", params={"adapter_key": "bitrix24.mock"})
        assert updated_events.status_code == 200
        updated_event = next(
            item for item in updated_events.json() if item["id"] == event["id"]
        )
        assert updated_event["status"] == "dead_letter"
        assert updated_event["attempt_count"] == 2
        assert "Bitrix24 webhook URL is not configured" in updated_event["last_error"]
        assert updated_event["next_retry_at"] is None

        runtime = client.get("/runtime").json()
        assert runtime["counters"]["bitrix24_dispatch_failures_total"] >= 2
        assert runtime["counters"]["integration_dead_letters_total"] >= 1


def test_crm_handoff_is_idempotent_per_approval() -> None:
    with TestClient(app) as client:
        webhook = client.post(
            "/webhooks/n8n/call-transcript",
            json={
                "call_id": "CALL-IDEMPOTENT-1",
                "customer_id": "LEAD-IDEMPOTENT",
                "transcript": (
                    "The buyer confirmed budget and authority. They need the result this "
                    "month and agreed the next step is a technical review tomorrow."
                ),
                "metadata": {"source": "idempotency-test"},
            },
        )
        assert webhook.status_code == 200
        approval_id = webhook.json()["approval"]["id"]

        approved = client.post(
            f"/approvals/{approval_id}/approve",
            json={"reviewer": "sales-lead", "notes": "Approved once"},
        )
        assert approved.status_code == 200
        approval = store.get_approval(UUID(approval_id))
        queue_crm_handoff_if_needed(approval)

        events = client.get("/integration-events", params={"adapter_key": "bitrix24.mock"})
        assert events.status_code == 200
        matching_events = [
            item for item in events.json() if item["source_approval_id"] == approval_id
        ]
        assert len(matching_events) == 1
        assert matching_events[0]["idempotency_key"]


def test_bitrix24_drain_respects_next_retry_at(monkeypatch) -> None:
    monkeypatch.setattr(settings, "bitrix24_dry_run", False)
    monkeypatch.setattr(settings, "bitrix24_webhook_url", None)
    monkeypatch.setattr(settings, "integration_max_attempts", 3)
    monkeypatch.setattr(settings, "integration_retry_delay_seconds", 300)

    with TestClient(app) as client:
        webhook = client.post(
            "/webhooks/n8n/call-transcript",
            json={
                "call_id": "CALL-DRAIN-RETRY-1",
                "customer_id": "LEAD-DRAIN-RETRY",
                "transcript": (
                    "The client has budget and authority. They need launch this month "
                    "and accepted the next step as an implementation review."
                ),
                "metadata": {"source": "drain-retry-test"},
            },
        )
        assert webhook.status_code == 200
        approval_id = webhook.json()["approval"]["id"]
        approved = client.post(
            f"/approvals/{approval_id}/approve",
            json={"reviewer": "sales-lead", "notes": "Queue for drain"},
        )
        assert approved.status_code == 200

        first_drain = client.post("/integrations/bitrix24/drain", params={"limit": 100})
        assert first_drain.status_code == 200
        first_body = first_drain.json()
        assert first_body["selected"] >= 1
        assert first_body["retry"] >= 1

        events = client.get(
            "/integration-events",
            params={"adapter_key": "bitrix24.mock", "status": "retry"},
        )
        assert events.status_code == 200
        event = next(
            item for item in events.json() if item["source_approval_id"] == approval_id
        )
        assert event["attempt_count"] == 1
        assert event["next_retry_at"] is not None

        second_drain = client.post("/integrations/bitrix24/drain", params={"limit": 100})
        assert second_drain.status_code == 200
        second_body = second_drain.json()
        assert event["id"] not in second_body["event_ids"]


def test_bitrix24_background_worker_drains_due_events(monkeypatch) -> None:
    monkeypatch.setattr(settings, "integration_worker_enabled", True)
    monkeypatch.setattr(settings, "integration_worker_interval_seconds", 1.0)
    monkeypatch.setattr(settings, "integration_worker_batch_size", 100)
    monkeypatch.setattr(settings, "bitrix24_dry_run", False)
    monkeypatch.setattr(settings, "bitrix24_webhook_url", None)
    monkeypatch.setattr(settings, "integration_max_attempts", 2)
    monkeypatch.setattr(settings, "integration_retry_delay_seconds", 0)

    with TestClient(app) as client:
        runtime = client.get("/runtime")
        assert runtime.status_code == 200
        assert runtime.json()["workers"]["bitrix24_outbox"]["active"] is True

        webhook = client.post(
            "/webhooks/n8n/call-transcript",
            json={
                "call_id": "CALL-WORKER-1",
                "customer_id": "LEAD-WORKER",
                "transcript": (
                    "The client approved budget and authority. They need launch this "
                    "month and agreed the next step is an implementation call."
                ),
                "metadata": {"source": "worker-test"},
            },
        )
        assert webhook.status_code == 200
        approval_id = webhook.json()["approval"]["id"]

        approved = client.post(
            f"/approvals/{approval_id}/approve",
            json={"reviewer": "sales-lead", "notes": "Queue for worker"},
        )
        assert approved.status_code == 200

        deadline = time.time() + 4.0
        worker_event = None
        while time.time() < deadline:
            events = client.get("/integration-events", params={"adapter_key": "bitrix24.mock"})
            assert events.status_code == 200
            worker_event = next(
                (
                    item
                    for item in events.json()
                    if item["source_approval_id"] == approval_id
                ),
                None,
            )
            if worker_event and worker_event["status"] == "dead_letter":
                break
            time.sleep(0.2)

        assert worker_event is not None
        assert worker_event["status"] == "dead_letter"
        assert worker_event["attempt_count"] >= 2
        runtime_after = client.get("/runtime").json()
        assert runtime_after["counters"]["integration_worker_ticks_total"] >= 1
        assert runtime_after["counters"]["integration_worker_errors_total"] == 0
