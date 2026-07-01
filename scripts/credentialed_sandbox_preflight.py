#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT))

from app.settings import Settings


DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "evidence"


def join_url(base_url: str, path: str) -> str:
    return urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def redacted_url_origin(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.hostname:
        return "<invalid-url>"
    return "<redacted-bitrix24-origin>"


def status_is_failure(check: dict[str, Any]) -> bool:
    return check.get("status") == "failed"


def telegram_get_me(client: httpx.Client, token: str | None) -> dict[str, Any]:
    if not token:
        return {"status": "skipped", "reason": "TELEGRAM_BOT_TOKEN is not configured"}

    try:
        response = client.get(f"https://api.telegram.org/bot{token}/getMe")
    except httpx.HTTPError as exc:
        return {
            "status": "failed",
            "error": f"telegram_request_failed:{exc.__class__.__name__}",
        }
    try:
        body = response.json()
    except json.JSONDecodeError:
        return {
            "status": "failed",
            "http_status": response.status_code,
            "error": "telegram_response_was_not_json",
        }

    if not body.get("ok"):
        return {
            "status": "failed",
            "http_status": response.status_code,
            "telegram_error_code": body.get("error_code"),
        }

    result = body.get("result") or {}
    return {
        "status": "passed",
        "http_status": response.status_code,
        "bot_id_present": bool(result.get("id")),
        "bot_username_present": bool(result.get("username")),
        "can_join_groups": result.get("can_join_groups"),
        "supports_inline_queries": result.get("supports_inline_queries"),
    }


def telegram_webhook_info(
    client: httpx.Client,
    token: str | None,
    public_base_url: str,
) -> dict[str, Any]:
    expected_url = join_url(public_base_url, "/webhooks/telegram/approval")
    if not token:
        return {
            "status": "skipped",
            "reason": "TELEGRAM_BOT_TOKEN is not configured",
            "expected_webhook_url": expected_url,
        }

    try:
        response = client.get(f"https://api.telegram.org/bot{token}/getWebhookInfo")
    except httpx.HTTPError as exc:
        return {
            "status": "failed",
            "error": f"telegram_request_failed:{exc.__class__.__name__}",
            "expected_webhook_url": expected_url,
        }
    try:
        body = response.json()
    except json.JSONDecodeError:
        return {
            "status": "failed",
            "http_status": response.status_code,
            "error": "telegram_response_was_not_json",
            "expected_webhook_url": expected_url,
        }

    if not body.get("ok"):
        return {
            "status": "failed",
            "http_status": response.status_code,
            "telegram_error_code": body.get("error_code"),
            "expected_webhook_url": expected_url,
        }

    result = body.get("result") or {}
    configured_url = result.get("url") or ""
    matches_expected = configured_url == expected_url
    status = "passed" if matches_expected else "needs_configuration"
    return {
        "status": status,
        "http_status": response.status_code,
        "expected_webhook_url": expected_url,
        "configured_url_matches_expected": matches_expected,
        "configured_url_present": bool(configured_url),
        "pending_update_count": result.get("pending_update_count"),
        "allowed_updates": result.get("allowed_updates") or [],
        "last_error_present": bool(result.get("last_error_message")),
    }


def bitrix24_profile(client: httpx.Client, webhook_url: str | None) -> dict[str, Any]:
    if not webhook_url:
        return {"status": "skipped", "reason": "BITRIX24_WEBHOOK_URL is not configured"}

    parsed = urlparse(webhook_url)
    if not parsed.scheme or not parsed.hostname:
        return {
            "status": "failed",
            "error": "BITRIX24_WEBHOOK_URL is not a valid URL",
            "webhook_origin": "<invalid-url>",
        }

    try:
        response = client.post(join_url(webhook_url, "/profile.json"))
    except httpx.HTTPError as exc:
        return {
            "status": "failed",
            "error": f"bitrix24_request_failed:{exc.__class__.__name__}",
            "webhook_origin": redacted_url_origin(webhook_url),
        }
    try:
        body = response.json()
    except json.JSONDecodeError:
        return {
            "status": "failed",
            "http_status": response.status_code,
            "error": "bitrix24_response_was_not_json",
            "webhook_origin": redacted_url_origin(webhook_url),
        }

    if response.status_code >= 400 or body.get("error"):
        return {
            "status": "failed",
            "http_status": response.status_code,
            "bitrix_error": body.get("error") or "http_error",
            "webhook_origin": redacted_url_origin(webhook_url),
        }

    result = body.get("result") or {}
    return {
        "status": "passed",
        "http_status": response.status_code,
        "webhook_origin": redacted_url_origin(webhook_url),
        "profile_id_present": bool(result.get("ID") or result.get("id")),
        "profile_name_present": bool(result.get("NAME") or result.get("name")),
    }


def bitrix24_crm_lead_fields(client: httpx.Client, webhook_url: str | None) -> dict[str, Any]:
    if not webhook_url:
        return {"status": "skipped", "reason": "BITRIX24_WEBHOOK_URL is not configured"}

    parsed = urlparse(webhook_url)
    if not parsed.scheme or not parsed.hostname:
        return {
            "status": "failed",
            "error": "BITRIX24_WEBHOOK_URL is not a valid URL",
            "webhook_origin": "<invalid-url>",
        }

    try:
        response = client.post(join_url(webhook_url, "/crm.lead.fields.json"))
    except httpx.HTTPError as exc:
        return {
            "status": "failed",
            "error": f"bitrix24_request_failed:{exc.__class__.__name__}",
            "webhook_origin": redacted_url_origin(webhook_url),
        }
    try:
        body = response.json()
    except json.JSONDecodeError:
        return {
            "status": "failed",
            "http_status": response.status_code,
            "error": "bitrix24_response_was_not_json",
            "webhook_origin": redacted_url_origin(webhook_url),
        }

    if response.status_code >= 400 or body.get("error"):
        return {
            "status": "failed",
            "http_status": response.status_code,
            "bitrix_error": body.get("error") or "http_error",
            "webhook_origin": redacted_url_origin(webhook_url),
        }

    result = body.get("result") or {}
    return {
        "status": "passed",
        "http_status": response.status_code,
        "webhook_origin": redacted_url_origin(webhook_url),
        "lead_fields_present": bool(result),
        "core_fields_present": all(field in result for field in ("ID", "TITLE", "STATUS_ID")),
    }


def missing_required_targets(
    required_targets: set[str],
    telegram_configured: bool,
    bitrix_configured: bool,
) -> list[str]:
    missing: list[str] = []
    if "telegram" in required_targets and not telegram_configured:
        missing.append("telegram")
    if "bitrix24" in required_targets and not bitrix_configured:
        missing.append("bitrix24")
    return missing


def build_report(settings: Settings, timeout: float, required_targets: set[str]) -> dict[str, Any]:
    telegram_configured = bool(settings.telegram_bot_token)
    bitrix_configured = bool(settings.bitrix24_webhook_url)
    missing_required = missing_required_targets(
        required_targets,
        telegram_configured,
        bitrix_configured,
    )

    with httpx.Client(timeout=timeout) as client:
        checks = {
            "telegram_get_me": telegram_get_me(client, settings.telegram_bot_token),
            "telegram_webhook_info": telegram_webhook_info(
                client,
                settings.telegram_bot_token,
                settings.public_base_url,
            ),
            "bitrix24_profile": bitrix24_profile(client, settings.bitrix24_webhook_url),
            "bitrix24_crm_lead_fields": bitrix24_crm_lead_fields(
                client,
                settings.bitrix24_webhook_url,
            ),
        }

    failures = [name for name, check in checks.items() if status_is_failure(check)]
    mode = "live" if telegram_configured or bitrix_configured else "skipped_no_credentials"
    ok = not failures and not missing_required
    return {
        "evidence_schema": "credentialed_sandbox_preflight_v1",
        "ok": ok,
        "mode": mode,
        "sanitized": True,
        "external_calls": "read_only_when_credentials_present",
        "secret_boundaries": {
            "secrets_printed": False,
            "mutating_external_calls": False,
            "telegram_token_redacted": True,
            "bitrix24_webhook_token_redacted": True,
        },
        "environment": {
            "public_base_url": settings.public_base_url,
            "telegram_bot_token_configured": telegram_configured,
            "telegram_approval_chat_id_configured": bool(settings.telegram_approval_chat_id),
            "telegram_webhook_secret_configured": bool(settings.telegram_webhook_secret),
            "telegram_dry_run": settings.telegram_dry_run,
            "bitrix24_webhook_url_configured": bitrix_configured,
            "bitrix24_webhook_origin": redacted_url_origin(settings.bitrix24_webhook_url),
            "bitrix24_dry_run": settings.bitrix24_dry_run,
            "integration_worker_enabled": settings.integration_worker_enabled,
        },
        "checks": checks,
        "failures": failures,
        "required_targets": sorted(required_targets),
        "missing_required_targets": missing_required,
        "missing_required_credentials": bool(missing_required),
    }


def format_text(report: dict[str, Any]) -> str:
    checks = report["checks"]
    environment = report["environment"]
    return "\n".join(
        [
            (
                "credentialed sandbox preflight passed"
                if report["ok"]
                else "credentialed sandbox preflight failed"
            ),
            f"schema={report['evidence_schema']}",
            f"mode={report['mode']}",
            (
                "required_targets="
                f"{','.join(report['required_targets']) if report['required_targets'] else 'none'} "
                "missing_required_targets="
                f"{','.join(report['missing_required_targets']) if report['missing_required_targets'] else 'none'}"
            ),
            f"public_base_url={environment['public_base_url']}",
            (
                "telegram="
                f"configured={environment['telegram_bot_token_configured']} "
                f"get_me={checks['telegram_get_me']['status']} "
                f"webhook={checks['telegram_webhook_info']['status']}"
            ),
            (
                "bitrix24="
                f"configured={environment['bitrix24_webhook_url_configured']} "
                f"profile={checks['bitrix24_profile']['status']} "
                f"crm_lead_fields={checks['bitrix24_crm_lead_fields']['status']} "
                f"origin={environment['bitrix24_webhook_origin']}"
            ),
            (
                "dry_run="
                f"telegram={environment['telegram_dry_run']} "
                f"bitrix24={environment['bitrix24_dry_run']} "
                f"worker_enabled={environment['integration_worker_enabled']}"
            ),
            (
                "secret_boundaries="
                f"secrets_printed={report['secret_boundaries']['secrets_printed']} "
                f"mutating_external_calls={report['secret_boundaries']['mutating_external_calls']}"
            ),
        ]
    )


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run a read-only Telegram/Bitrix24 credentialed sandbox preflight and write sanitized evidence."
        )
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for generated evidence artifacts.",
    )
    parser.add_argument("--timeout", type=float, default=15.0, help="HTTP timeout in seconds.")
    parser.add_argument(
        "--require-credentials",
        action="store_true",
        help="Fail when Telegram or Bitrix24 credentials are missing.",
    )
    parser.add_argument(
        "--require-target",
        action="append",
        choices=("telegram", "bitrix24"),
        default=[],
        help=(
            "Fail only when the selected credential target is missing. "
            "Can be passed more than once."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Print JSON instead of text.")
    args = parser.parse_args()

    required_targets = set(args.require_target)
    if args.require_credentials:
        required_targets.update({"telegram", "bitrix24"})

    report = build_report(Settings(), args.timeout, required_targets)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "credentialed-sandbox-preflight.sanitized.json"
    text_path = output_dir / "credentialed-sandbox-preflight.txt"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    text_path.write_text(format_text(report) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("credentialed sandbox preflight captured")
        print(f"json={display_path(json_path)}")
        print(f"text={display_path(text_path)}")
        print(format_text(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
