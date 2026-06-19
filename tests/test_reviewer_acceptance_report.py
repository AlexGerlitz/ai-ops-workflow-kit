from scripts.reviewer_acceptance_report import (
    format_text,
    parse_key_value_lines,
    profile_page_check,
    workflow_status,
)


def test_parse_key_value_lines_keeps_smoke_signals() -> None:
    text = "\n".join(
        [
            "live demo smoke passed",
            "base_url=https://saleops.duckdns.org",
            "score=100",
            "telegram_callback=rejected",
            "bitrix24_drain=31",
        ]
    )

    parsed = parse_key_value_lines(text)

    assert parsed["score"] == "100"
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
        },
        "live_snapshot": {
            "git_sha": "abc123",
            "llm": {"selected_provider": "local"},
        },
        "live_smoke": {
            "signals": {
                "score": "100",
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
        "secret_boundaries": {
            "secrets_printed": False,
            "mutating_external_calls": False,
        },
        "private_sandbox_next_step": "Run the manual workflow.",
    }

    text = format_text(report)

    assert "reviewer acceptance report passed" in text
    assert "live_smoke=passed score=100 telegram_callback=rejected bitrix24_drain=31" in text
    assert "sandbox_run=success" in text
    assert "bitrix24_contract=passed method=crm.lead.update request_shape=True" in text
    assert "secret_boundaries=secrets_printed=False mutating_external_calls=False" in text
