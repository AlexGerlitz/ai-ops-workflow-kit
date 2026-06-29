import json

from scripts.hiring_signal_brief import build_report, format_text


def test_hiring_signal_brief_combines_replay_and_readiness() -> None:
    report = build_report()

    assert report["schema"] == "hiring_signal_brief_v1"
    assert report["ok"] is True
    assert report["high_bar_checks"]["business_workflow_to_backend_state"] is True
    assert report["high_bar_checks"]["rag_quality_reviewable"] is True
    assert report["high_bar_checks"]["privacy_boundary_owned"] is True
    assert report["high_bar_checks"]["approval_to_crm_handoff_controlled"] is True
    assert report["high_bar_checks"]["external_writes_gated"] is True
    assert report["high_bar_checks"]["failure_modes_tested"] is True
    assert report["high_bar_checks"]["worker_guarded_in_dry_run"] is True
    assert report["proof_summary"]["rag_quality"]["passed"] == 2
    assert report["proof_summary"]["crm_handoff"]["idempotency_key_present"] is True
    assert (
        report["proof_summary"]["production_readiness"]["bitrix_retry_dead_letter"][
            "second_dispatch"
        ]["event_status"]
        == "dead_letter"
    )

    text = format_text(report)

    assert "hiring signal brief passed" in text
    assert "quality_gate=rag_ok=True passed=2/2 citations_present=True" in text
    assert "retry_dead_letter=dead_letter" in text
    assert "worker_active=False" in text


def test_hiring_signal_brief_keeps_public_output_sanitized() -> None:
    report = build_report()
    serialized = json.dumps(report) + format_text(report)

    assert "maria.petrov@example.com" not in serialized
    assert "+41 44 555 12 34" not in serialized
    assert "BITRIX24_WEBHOOK_URL" not in serialized
    assert "TELEGRAM_BOT_TOKEN" not in serialized
    assert "sk-" not in serialized
