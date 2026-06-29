import json

from scripts.business_scenario_replay import build_report, format_text, run_demo


def test_business_scenario_replay_summarizes_offer_demo() -> None:
    report = build_report(run_demo())

    assert report["schema"] == "business_scenario_replay_v1"
    assert report["ok"] is True
    assert report["proof_signals"]["rag_quality"]["ok"] is True
    assert report["proof_signals"]["rag_quality"]["passed"] == 2
    assert report["proof_signals"]["rag_quality"]["citations_present"] is True
    assert report["proof_signals"]["call_analysis"]["score"] >= 80
    assert report["proof_signals"]["privacy"]["redacted"] is True
    assert report["proof_signals"]["privacy"]["raw_text_stored"] is False
    assert report["proof_signals"]["approval"]["status"] == "approved"
    assert report["proof_signals"]["crm_handoff"]["status"] == "queued"
    assert report["proof_signals"]["crm_handoff"]["idempotency_key_present"] is True
    assert report["proof_signals"]["bitrix24_dispatch"]["status"] == "dry_run"
    assert report["proof_signals"]["bitrix24_dispatch"]["method"] == "crm.lead.update"

    text = format_text(report)

    assert "business scenario replay passed" in text
    assert "rag_quality=ok=True passed=2/2 citations_present=True" in text
    assert "crm_handoff=adapter=bitrix24.mock status=queued" in text
    assert "bitrix24_dispatch=adapter=bitrix24 status=dry_run" in text


def test_business_scenario_replay_keeps_public_output_sanitized() -> None:
    report = build_report(run_demo())
    serialized = json.dumps(report) + format_text(report)

    assert "maria.petrov@example.com" not in serialized
    assert "+41 44 555 12 34" not in serialized
    assert "[redacted-email]" not in serialized
    assert "[redacted-phone]" not in serialized
    assert "raw_personal_data_stored" in serialized
