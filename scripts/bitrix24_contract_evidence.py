#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import UUID

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT))

from app.integrations import build_bitrix24_handoff_payload, dispatch_bitrix24_event
from app.schemas import IntegrationEventOut, IntegrationEventStatus
from app.settings import Settings


DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "evidence"
DEFAULT_SAMPLE_WEBHOOK_URL = "https://example.bitrix24.ru/rest/42/synthetic-secret-token/"
SAMPLE_EVENT_ID = UUID("9f807e01-2b42-4c38-a67d-a5dcb2cf3b0e")
SAMPLE_APPROVAL_ID = UUID("f8b09f2d-7f06-4b93-840b-61f4de8b9f74")
SAMPLE_CREATED_AT = datetime(2026, 6, 19, 0, 0, tzinfo=UTC)


def sample_crm_update() -> dict[str, Any]:
    return {
        "adapter": "bitrix24.mock",
        "operation": "upsert_lead_follow_up",
        "customer_id": "LEAD-42",
        "call_id": "CALL-2026-06-19-001",
        "lead_score": 92,
        "risk_level": "low",
        "target_stage": "qualified",
        "fields": {
            "AI Lead Score": 92,
            "AI Risk Level": "low",
            "AI Missing Signals": [],
        },
        "comment": "Buyer confirmed budget, authority, timeline, and a dated next step.",
        "task": {
            "title": "Follow up after call CALL-2026-06-19-001",
            "description": "Send recap, confirm terms, and move the lead to the next CRM stage.",
            "priority": "normal",
        },
        "objections": ["no explicit objection detected"],
    }


def sample_event() -> IntegrationEventOut:
    return IntegrationEventOut(
        id=SAMPLE_EVENT_ID,
        adapter_key="bitrix24.mock",
        operation="upsert_lead_follow_up",
        status=IntegrationEventStatus.queued,
        payload=sample_crm_update(),
        source_approval_id=SAMPLE_APPROVAL_ID,
        idempotency_key=(
            f"approval:{SAMPLE_APPROVAL_ID}:bitrix24.mock:upsert_lead_follow_up"
        ),
        attempt_count=0,
        last_error=None,
        next_retry_at=None,
        created_at=SAMPLE_CREATED_AT,
        updated_at=SAMPLE_CREATED_AT,
    )


def redacted_origin(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return "<invalid-url>"
    return f"{parsed.scheme}://{parsed.netloc}"


def redacted_method_url(webhook_url: str, method: str) -> str:
    parsed = urlparse(webhook_url)
    if not parsed.scheme or not parsed.netloc:
        return "<invalid-url>"
    path_parts = [part for part in parsed.path.split("/") if part]
    if len(path_parts) >= 3 and path_parts[0] == "rest":
        redacted_path = "/rest/<user_id>/<webhook_token>/"
    else:
        redacted_path = "/<webhook_path>/"
    return f"{parsed.scheme}://{parsed.netloc}{redacted_path}{method}.json"


def secret_token_leaked(payload: object, token: str) -> bool:
    return token in json.dumps(payload, ensure_ascii=False)


def extract_token(webhook_url: str) -> str:
    parsed = urlparse(webhook_url)
    parts = [part for part in parsed.path.split("/") if part]
    return parts[2] if len(parts) >= 3 and parts[0] == "rest" else ""


def build_report(sample_webhook_url: str) -> dict[str, Any]:
    event = sample_event()
    contract = build_bitrix24_handoff_payload(event)
    dry_run_dispatch = dispatch_bitrix24_event(
        event,
        Settings(bitrix24_webhook_url=sample_webhook_url, bitrix24_dry_run=True),
    )
    method = str(contract["method"])
    token = extract_token(sample_webhook_url)
    expected_request_keys = {"id", "fields", "params"}
    bitrix_request = contract["bitrix_request"]
    checks = {
        "method_mapping": method == "crm.lead.update",
        "request_shape": (
            isinstance(bitrix_request, dict)
            and expected_request_keys.issubset(bitrix_request.keys())
            and isinstance(bitrix_request.get("fields"), dict)
            and "COMMENTS" in bitrix_request["fields"]
        ),
        "idempotency_key_present": bool(event.idempotency_key),
        "dry_run_does_not_call_bitrix": dry_run_dispatch.status.value == "dry_run",
        "dry_run_does_not_consume_event": dry_run_dispatch.event_status is None,
        "secret_token_leaked": secret_token_leaked(
            {
                "contract": contract,
                "dry_run_detail": dry_run_dispatch.detail,
                "redacted_method_url": redacted_method_url(sample_webhook_url, method),
            },
            token,
        )
        if token
        else False,
    }
    ok = all(value is True for key, value in checks.items() if key != "secret_token_leaked") and (
        checks["secret_token_leaked"] is False
    )
    return {
        "evidence_schema": "bitrix24_contract_evidence_v1",
        "ok": ok,
        "sanitized": True,
        "external_calls": "none_contract_only",
        "secret_boundaries": {
            "secrets_printed": False,
            "mutating_external_calls": False,
            "bitrix24_webhook_token_redacted": True,
        },
        "activation_boundary": {
            "required_env": ["BITRIX24_WEBHOOK_URL", "BITRIX24_DRY_RUN=false"],
            "webhook_origin": redacted_origin(sample_webhook_url),
            "method_url": redacted_method_url(sample_webhook_url, method),
            "credentialed_read_only_check": (
                "scripts/credentialed_sandbox_preflight.py --require-target bitrix24"
            ),
            "portal_access_note": (
                "Real Bitrix24 sandbox proof requires an incoming webhook URL from the target portal."
            ),
        },
        "contract": {
            "adapter_key": "bitrix24",
            "source_adapter_key": event.adapter_key,
            "operation": event.operation,
            "method": method,
            "event_status": event.status.value,
            "attempt_count": event.attempt_count,
            "idempotency_key_present": bool(event.idempotency_key),
            "source_approval_id_present": event.source_approval_id is not None,
            "crm_update_fields": sorted(event.payload.keys()),
            "bitrix_request": bitrix_request,
        },
        "dry_run_dispatch": {
            "status": dry_run_dispatch.status.value,
            "detail": dry_run_dispatch.detail,
            "event_status": (
                dry_run_dispatch.event_status.value if dry_run_dispatch.event_status else None
            ),
            "attempt_count": dry_run_dispatch.attempt_count,
            "max_attempts": dry_run_dispatch.max_attempts,
        },
        "checks": checks,
    }


def format_text(report: dict[str, Any]) -> str:
    checks = report["checks"]
    contract = report["contract"]
    activation = report["activation_boundary"]
    return "\n".join(
        [
            "bitrix24 contract evidence passed" if report["ok"] else "bitrix24 contract evidence failed",
            f"schema={report['evidence_schema']}",
            f"method={contract['method']}",
            f"request_shape={checks['request_shape']}",
            f"idempotency_key_present={contract['idempotency_key_present']}",
            f"dry_run_status={report['dry_run_dispatch']['status']}",
            f"method_url={activation['method_url']}",
            (
                "secret_boundaries="
                f"secrets_printed={report['secret_boundaries']['secrets_printed']} "
                f"mutating_external_calls={report['secret_boundaries']['mutating_external_calls']} "
                f"secret_token_leaked={checks['secret_token_leaked']}"
            ),
            f"credentialed_read_only_check={activation['credentialed_read_only_check']}",
        ]
    )


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate sanitized Bitrix24 contract evidence without external calls."
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--sample-webhook-url", default=DEFAULT_SAMPLE_WEBHOOK_URL)
    parser.add_argument("--json", action="store_true", help="Print JSON instead of text.")
    args = parser.parse_args()

    report = build_report(args.sample_webhook_url)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "bitrix24-contract.sanitized.json"
    text_path = output_dir / "bitrix24-contract.txt"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    text_path.write_text(format_text(report) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("bitrix24 contract evidence captured")
        print(f"json={display_path(json_path)}")
        print(f"text={display_path(text_path)}")
        print(format_text(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
