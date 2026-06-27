from app.privacy import redact_text


def test_redact_text_replaces_email_phone_card_and_iban() -> None:
    result = redact_text(
        "Email buyer@example.com, phone +41 44 555 12 34, "
        "card 4111 1111 1111 1111, IBAN CH9300762011623852957."
    )

    assert result.redacted is True
    assert result.counts == {
        "email": 1,
        "payment_card": 1,
        "iban": 1,
        "phone": 1,
    }
    assert "buyer@example.com" not in result.text
    assert "+41 44 555 12 34" not in result.text
    assert "4111 1111 1111 1111" not in result.text
    assert "CH9300762011623852957" not in result.text
    assert "[redacted-email]" in result.text
    assert "[redacted-phone]" in result.text
    assert "[redacted-payment-card]" in result.text
    assert "[redacted-iban]" in result.text


def test_redaction_evidence_is_safe_for_public_logs() -> None:
    evidence = redact_text("No sensitive fields here.").evidence()

    assert evidence.enabled is True
    assert evidence.redacted is False
    assert evidence.categories == []
    assert evidence.replacement_counts == {}
    assert evidence.raw_text_stored is False
    assert evidence.safe_logging is True
