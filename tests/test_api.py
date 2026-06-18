from fastapi.testclient import TestClient

from app.main import app, settings


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
    assert metrics.status_code == 200
    assert "aiops_runtime_info" in metrics.text
    assert "aiops_demo_runs_total" in metrics.text


def test_public_demo_page_is_available() -> None:
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert "AI Sales Ops Control Tower" in response.text
    assert "Run demo workflow" in response.text


def test_integration_runtime_reports_dry_run_capabilities() -> None:
    with TestClient(app) as client:
        response = client.get("/integrations/runtime")
    assert response.status_code == 200
    body = response.json()
    capabilities = {item["adapter_key"]: item for item in body["capabilities"]}
    assert capabilities["telegram.approval"]["dry_run"] is True
    assert capabilities["bitrix24"]["dry_run"] is True
    assert capabilities["telegram.approval"]["webhook_secret_configured"] is False


def test_public_demo_run_proves_workflow_contract() -> None:
    with TestClient(app) as client:
        response = client.post("/demo/run")
    assert response.status_code == 200
    body = response.json()
    assert body["runtime"]["ok"] is True
    assert body["ingestion"]["chunks"] >= 1
    assert body["rag_context_sources"]
    assert body["call_analysis"]["score"] >= 80
    assert body["approval"]["status"] == "approved"
    assert body["telegram_approval"]["status"] == "dry_run"
    assert body["telegram_approval"]["callback_contract"]["approve"]["url"].endswith("/approve")
    assert body["crm_handoff"]["status"] == "queued"
    assert body["bitrix24_dispatch"]["status"] == "dry_run"
    runtime = client.get("/runtime").json()
    assert runtime["counters"]["demo_runs_total"] >= 1
    assert runtime["counters"]["crm_handoffs_queued_total"] >= 1


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


def test_offer_demo_call_transcript_queues_crm_handoff_after_approval() -> None:
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
        assert first_body["event_status"] == "failed"
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

        runtime = client.get("/runtime").json()
        assert runtime["counters"]["bitrix24_dispatch_failures_total"] >= 2
        assert runtime["counters"]["integration_dead_letters_total"] >= 1
