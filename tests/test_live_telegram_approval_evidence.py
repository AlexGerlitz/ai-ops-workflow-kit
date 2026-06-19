from scripts.live_telegram_approval_evidence import build_report, format_text


def test_live_telegram_approval_evidence_is_sanitized(monkeypatch) -> None:
    approval_id = "approval-1"

    def fake_fetch_json(url: str, *, method: str = "GET", timeout: float = 15.0):
        if url.endswith("/runtime"):
            return {
                "ok": True,
                "git_sha": "sha",
                "storage": "memory",
                "transcription": {
                    "providers": [
                        {"provider": "deepgram", "configured": True},
                    ]
                },
                "integrations": {
                    "capabilities": [
                        {
                            "adapter_key": "telegram.approval",
                            "configured": True,
                            "dry_run": False,
                        },
                        {
                            "adapter_key": "bitrix24",
                            "configured": False,
                            "dry_run": True,
                        },
                    ]
                },
            }
        if url.endswith(f"/approvals/{approval_id}"):
            return {
                "id": approval_id,
                "title": "Owner live approval",
                "kind": "call_follow_up",
                "status": "approved",
                "reviewer": "owner",
                "notes": "Approved from Telegram callback",
            }
        if url.endswith("/integration-events"):
            return [
                {
                    "id": "event-1",
                    "adapter_key": "bitrix24.mock",
                    "operation": "upsert_lead_follow_up",
                    "status": "queued",
                    "attempt_count": 0,
                    "source_approval_id": approval_id,
                }
            ]
        if "/getWebhookInfo" in url:
            return {
                "ok": True,
                "result": {
                    "url": "https://saleops.duckdns.org/webhooks/telegram/approval",
                    "pending_update_count": 0,
                    "allowed_updates": ["callback_query"],
                },
            }
        raise AssertionError(url)

    monkeypatch.setattr("scripts.live_telegram_approval_evidence.fetch_json", fake_fetch_json)

    report = build_report(
        "https://saleops.duckdns.org",
        approval_id,
        timeout=1.0,
        token="secret-token",
    )
    text = format_text(report)

    assert report["ok"] is True
    assert report["secret_boundaries"]["secrets_printed"] is False
    assert report["runtime"]["telegram"] == {"configured": True, "dry_run": False}
    assert report["runtime"]["bitrix24"] == {"configured": False, "dry_run": True}
    assert report["telegram_webhook"]["status"] == "passed"
    assert report["crm_event"]["adapter_key"] == "bitrix24.mock"
    assert "secret-token" not in text
    assert "live telegram approval evidence passed" in text
