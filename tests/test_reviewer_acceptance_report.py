from scripts.reviewer_acceptance_report import (
    format_text,
    latest_run_for_workflow,
    parse_key_value_lines,
    profile_page_check,
    workflow_runs_url,
    workflow_status,
)


def test_parse_key_value_lines_keeps_smoke_signals() -> None:
    text = "\n".join(
        [
            "live demo smoke passed",
            "base_url=https://saleops.duckdns.org",
            "score=100",
            "rag_eval=2/2",
            "telegram_callback=rejected",
            "bitrix24_drain=31",
        ]
    )

    parsed = parse_key_value_lines(text)

    assert parsed["score"] == "100"
    assert parsed["rag_eval"] == "2/2"
    assert parsed["telegram_callback"] == "rejected"
    assert parsed["bitrix24_drain"] == "31"


def test_workflow_status_requires_active_workflow_path() -> None:
    workflows = [
        {
            "id": 123,
            "name": "Credentialed Sandbox Preflight",
            "path": ".github/workflows/credentialed-sandbox-preflight.yml",
            "state": "active",
            "html_url": "https://github.com/example/actions/workflows/x.yml",
        }
    ]

    assert (
        workflow_status(workflows, ".github/workflows/credentialed-sandbox-preflight.yml")[
            "status"
        ]
        == "passed"
    )
    assert workflow_status(workflows, ".github/workflows/missing.yml")["status"] == "failed"


def test_workflow_runs_url_targets_specific_workflow() -> None:
    url = workflow_runs_url(
        "AlexGerlitz/ai-ops-workflow-kit",
        {
            "id": 12345,
            "path": ".github/workflows/credentialed-sandbox-preflight.yml",
        },
        branch=None,
    )

    assert url == (
        "https://api.github.com/repos/AlexGerlitz/ai-ops-workflow-kit/"
        "actions/workflows/12345/runs?per_page=20"
    )


def test_latest_run_for_workflow_uses_workflow_run_endpoint(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def fake_fetch_json_url(url: str, _timeout: float) -> dict:
        captured["url"] = url
        return {
            "workflow_runs": [
                {
                    "name": "Credentialed Sandbox Preflight",
                    "conclusion": "success",
                    "head_sha": "abc123",
                    "html_url": "https://github.com/example/runs/1",
                    "created_at": "2026-06-27T00:00:00Z",
                }
            ]
        }

    monkeypatch.setattr(
        "scripts.reviewer_acceptance_report.fetch_json_url",
        fake_fetch_json_url,
    )

    result = latest_run_for_workflow(
        "AlexGerlitz/ai-ops-workflow-kit",
        {"status": "passed", "id": 12345, "name": "Credentialed Sandbox Preflight"},
        branch=None,
        timeout=1.0,
    )

    assert result["status"] == "passed"
    assert result["conclusion"] == "success"
    assert "actions/workflows/12345/runs?per_page=20" in captured["url"]


def test_profile_page_check_reports_missing_markers(monkeypatch) -> None:
    monkeypatch.setattr(
        "scripts.reviewer_acceptance_report.fetch_text_url",
        lambda _url, _timeout: "AI Ops proof status credentialed-sandbox-preflight.yml",
    )

    passed = profile_page_check("https://example.test", ["AI Ops proof status"], 1.0)
    failed = profile_page_check("https://example.test", ["not present"], 1.0)

    assert passed["status"] == "passed"
    assert failed["status"] == "failed"
    assert failed["missing_markers"] == ["not present"]


def test_format_text_summarizes_acceptance_boundaries() -> None:
    report = {
        "ok": True,
        "evidence_schema": "reviewer_acceptance_report_v1",
        "base_url": "https://saleops.duckdns.org",
        "checks": {
            "live_snapshot": "passed",
            "live_smoke": "passed",
            "github": "passed",
            "profile_pages": "passed",
            "bitrix24_contract": "passed",
            "live_telegram_approval": "passed",
        },
        "live_snapshot": {
            "git_sha": "abc123",
            "llm": {"selected_provider": "local"},
        },
        "live_smoke": {
            "signals": {
                "score": "100",
                "rag_eval": "2/2",
                "telegram_callback": "rejected",
                "bitrix24_drain": "31",
            }
        },
        "github": {
            "latest_checked_ci_run": {
                "conclusion": "success",
                "head_sha": "abc123",
            },
            "latest_checked_sandbox_run": {
                "conclusion": "success",
                "head_sha": "abc123",
            },
            "credentialed_sandbox_workflow": {"state": "active"},
        },
        "profile": {"pages": [{}, {}]},
        "bitrix24_contract": {
            "method": "crm.lead.update",
            "request_shape": True,
            "secret_token_leaked": False,
        },
        "live_telegram_approval": {
            "telegram_live": True,
            "approval_status": "approved",
            "crm_event_status": "queued",
            "bitrix24_dry_run": True,
        },
        "secret_boundaries": {
            "secrets_printed": False,
            "mutating_external_calls": False,
        },
        "private_sandbox_next_step": "Run the manual workflow.",
    }

    text = format_text(report)

    assert "reviewer acceptance report passed" in text
    assert "live_smoke=passed score=100 rag_eval=2/2 telegram_callback=rejected bitrix24_drain=31" in text
    assert "sandbox_run=success" in text
    assert "bitrix24_contract=passed method=crm.lead.update request_shape=True" in text
    assert "live_telegram_approval=passed telegram_live=True approval=approved" in text
    assert "secret_boundaries=secrets_printed=False mutating_external_calls=False" in text
