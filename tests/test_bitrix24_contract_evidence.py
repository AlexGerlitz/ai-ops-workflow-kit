from app.integrations import build_bitrix24_handoff_payload, bitrix24_lead_id
from scripts.bitrix24_contract_evidence import build_report, format_text, sample_event


def test_bitrix24_lead_id_accepts_demo_and_numeric_values() -> None:
    assert bitrix24_lead_id("LEAD-42") == "42"
    assert bitrix24_lead_id("42") == "42"
    assert bitrix24_lead_id("external-customer") == "external-customer"


def test_bitrix24_handoff_payload_uses_rest_request_shape() -> None:
    payload = build_bitrix24_handoff_payload(sample_event())

    assert payload["method"] == "crm.lead.update"
    assert payload["event_id"]
    assert payload["source_approval_id"]
    assert payload["crm_update"]["operation"] == "upsert_lead_follow_up"
    assert payload["bitrix_request"]["id"] == "42"
    assert set(payload["bitrix_request"]) == {"id", "fields", "params"}
    assert "COMMENTS" in payload["bitrix_request"]["fields"]
    assert payload["bitrix_request"]["params"] == {"REGISTER_SONET_EVENT": "Y"}


def test_bitrix24_contract_evidence_is_sanitized() -> None:
    report = build_report("https://example.bitrix24.ru/rest/42/private-token/")

    assert report["ok"] is True
    assert report["external_calls"] == "none_contract_only"
    assert report["checks"]["method_mapping"] is True
    assert report["checks"]["request_shape"] is True
    assert report["checks"]["secret_token_leaked"] is False
    assert "private-token" not in str(report)

    text = format_text(report)
    assert "bitrix24 contract evidence passed" in text
    assert "crm.lead.update" in text
    assert "private-token" not in text
