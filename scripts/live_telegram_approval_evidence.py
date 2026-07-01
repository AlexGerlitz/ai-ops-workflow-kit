#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_BASE_URL = "https://saleops.duckdns.org"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "evidence"


def fetch_json(url: str, *, method: str = "GET", timeout: float = 15.0) -> Any:
    request = urllib.request.Request(url, method=method, headers={"accept": "application/json"})
    if method == "POST":
        request.add_header("content-type", "application/json")
        request.data = b"{}"
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def normalize_base_url(value: str) -> str:
    return value.rstrip("/")


def telegram_webhook_info(token: str | None, timeout: float) -> dict[str, Any]:
    if not token:
        return {
            "status": "skipped",
            "reason": "TELEGRAM_BOT_TOKEN is not configured in the local environment",
        }

    url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
    body = fetch_json(url, timeout=timeout)
    result = body.get("result") or {}
    return {
        "status": "passed" if body.get("ok") else "failed",
        "url_present": bool(result.get("url")),
        "pending_update_count": result.get("pending_update_count"),
        "allowed_updates": result.get("allowed_updates") or [],
        "last_error_present": bool(result.get("last_error_message")),
    }


def latest_crm_event(events: list[dict[str, Any]], approval_id: str) -> dict[str, Any] | None:
    matching = [event for event in events if event.get("source_approval_id") == approval_id]
    return matching[-1] if matching else None


def build_report(
    base_url: str,
    approval_id: str,
    timeout: float,
    token: str | None,
) -> dict[str, Any]:
    base = normalize_base_url(base_url)
    runtime = fetch_json(f"{base}/runtime", timeout=timeout)
    approval = fetch_json(f"{base}/approvals/{approval_id}", timeout=timeout)
    events = fetch_json(f"{base}/integration-events", timeout=timeout)
    crm_event = latest_crm_event(events, approval_id)
    webhook = telegram_webhook_info(token, timeout)

    telegram_capability = next(
        (
            item
            for item in runtime.get("integrations", {}).get("capabilities", [])
            if item.get("adapter_key") == "telegram.approval"
        ),
        {},
    )
    bitrix_capability = next(
        (
            item
            for item in runtime.get("integrations", {}).get("capabilities", [])
            if item.get("adapter_key") == "bitrix24"
        ),
        {},
    )

    ok = (
        runtime.get("ok") is True
        and approval.get("status") == "approved"
        and bool(approval.get("reviewer"))
        and crm_event is not None
        and crm_event.get("status") in {"queued", "retry", "sent"}
        and telegram_capability.get("configured") is True
        and telegram_capability.get("dry_run") is False
        and bitrix_capability.get("dry_run") is True
        and webhook.get("status") in {"passed", "skipped"}
    )
    return {
        "evidence_schema": "live_telegram_approval_evidence_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ok": ok,
        "sanitized": True,
        "base_url": base,
        "external_calls": "read_only_live_api_and_optional_telegram_webhook_info",
        "secret_boundaries": {
            "secrets_printed": False,
            "telegram_token_redacted": True,
            "telegram_chat_id_redacted": True,
            "bitrix24_webhook_token_redacted": True,
            "customer_audio_retained": False,
        },
        "runtime": {
            "git_sha": runtime.get("git_sha"),
            "storage": runtime.get("storage"),
            "telegram": {
                "configured": telegram_capability.get("configured"),
                "dry_run": telegram_capability.get("dry_run"),
            },
            "bitrix24": {
                "configured": bitrix_capability.get("configured"),
                "dry_run": bitrix_capability.get("dry_run"),
            },
            "deepgram_configured": any(
                provider.get("provider") == "deepgram" and provider.get("configured")
                for provider in runtime.get("transcription", {}).get("providers", [])
            ),
        },
        "telegram_webhook": webhook,
        "approval": {
            "id": "<redacted-approval-id>",
            "title": approval.get("title"),
            "kind": approval.get("kind"),
            "status": approval.get("status"),
            "reviewer_present": bool(approval.get("reviewer")),
            "notes_present": bool(approval.get("notes")),
        },
        "crm_event": (
            {
                "id": "<redacted-crm-event-id>",
                "adapter_key": crm_event.get("adapter_key"),
                "operation": crm_event.get("operation"),
                "status": crm_event.get("status"),
                "attempt_count": crm_event.get("attempt_count"),
                "source_approval_id": "<redacted-approval-id>",
            }
            if crm_event
            else None
        ),
        "public_boundary": {
            "synthetic_demo_telegram_remains_dry_run": True,
            "bitrix24_trial_is_not_required_for_public_evidence": True,
            "real_bitrix24_writes_remain_production_gated": True,
        },
    }


def format_text(report: dict[str, Any]) -> str:
    approval = report["approval"]
    runtime = report["runtime"]
    crm_event = report["crm_event"] or {}
    webhook = report["telegram_webhook"]
    return "\n".join(
        [
            (
                "live telegram approval evidence passed"
                if report["ok"]
                else "live telegram approval evidence failed"
            ),
            f"schema={report['evidence_schema']}",
            f"base_url={report['base_url']}",
            f"git_sha={runtime['git_sha']}",
            (
                "telegram="
                f"configured={runtime['telegram']['configured']} "
                f"dry_run={runtime['telegram']['dry_run']} "
                f"webhook={webhook['status']} "
                f"pending_updates={webhook.get('pending_update_count')}"
            ),
            (
                "bitrix24="
                f"configured={runtime['bitrix24']['configured']} "
                f"dry_run={runtime['bitrix24']['dry_run']}"
            ),
            f"deepgram_configured={runtime['deepgram_configured']}",
            (
                "approval="
                f"id={approval['id']} "
                f"kind={approval['kind']} "
                f"status={approval['status']} "
                f"reviewer_present={approval['reviewer_present']}"
            ),
            (
                "crm_event="
                f"adapter={crm_event.get('adapter_key')} "
                f"operation={crm_event.get('operation')} "
                f"status={crm_event.get('status')} "
                f"attempt_count={crm_event.get('attempt_count')}"
            ),
            (
                "secret_boundaries="
                f"secrets_printed={report['secret_boundaries']['secrets_printed']} "
                f"telegram_token_redacted={report['secret_boundaries']['telegram_token_redacted']} "
                f"customer_audio_retained={report['secret_boundaries']['customer_audio_retained']}"
            ),
            (
                "public_boundary="
                "synthetic_demo_telegram_remains_dry_run=True "
                "bitrix24_trial_is_not_required_for_public_evidence=True"
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
        description="Capture sanitized evidence for an owner-run live Telegram approval."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--approval-id", required=True)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--json", action="store_true", help="Print JSON instead of text.")
    args = parser.parse_args()

    report = build_report(
        args.base_url,
        args.approval_id,
        args.timeout,
        os.environ.get("TELEGRAM_BOT_TOKEN"),
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "live-telegram-approval.sanitized.json"
    text_path = output_dir / "live-telegram-approval.txt"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    text_path.write_text(format_text(report) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("live telegram approval evidence captured")
        print(f"json={display_path(json_path)}")
        print(f"text={display_path(text_path)}")
        print(format_text(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
