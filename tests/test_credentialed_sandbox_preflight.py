from app.settings import Settings
from scripts.credentialed_sandbox_preflight import (
    build_report,
    format_text,
    missing_required_targets,
)


def test_missing_required_targets_are_granular() -> None:
    assert missing_required_targets(set(), False, False) == []
    assert missing_required_targets({"telegram"}, False, False) == ["telegram"]
    assert missing_required_targets({"bitrix24"}, False, False) == ["bitrix24"]
    assert missing_required_targets({"telegram", "bitrix24"}, True, False) == ["bitrix24"]


def test_public_preflight_stays_ok_without_required_targets() -> None:
    report = build_report(
        Settings(
            public_base_url="https://saleops.duckdns.org",
            telegram_bot_token=None,
            bitrix24_webhook_url=None,
        ),
        timeout=1.0,
        required_targets=set(),
    )

    assert report["ok"] is True
    assert report["mode"] == "skipped_no_credentials"
    assert report["required_targets"] == []
    assert report["missing_required_targets"] == []
    assert report["missing_required_credentials"] is False
    assert report["checks"]["telegram_get_me"]["status"] == "skipped"
    assert report["checks"]["bitrix24_profile"]["status"] == "skipped"

    text = format_text(report)
    assert "required_targets=none" in text
    assert "missing_required_targets=none" in text
    assert "secrets_printed=False" in text


def test_target_required_preflight_fails_only_for_missing_target() -> None:
    report = build_report(
        Settings(
            public_base_url="https://saleops.duckdns.org",
            telegram_bot_token=None,
            bitrix24_webhook_url=None,
        ),
        timeout=1.0,
        required_targets={"telegram"},
    )

    assert report["ok"] is False
    assert report["required_targets"] == ["telegram"]
    assert report["missing_required_targets"] == ["telegram"]
    assert report["missing_required_credentials"] is True
    assert "required_targets=telegram missing_required_targets=telegram" in format_text(report)
