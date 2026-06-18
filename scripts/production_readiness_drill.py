#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi.testclient import TestClient

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT))

from app.main import app, queue_crm_handoff_if_needed, settings, store


DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "evidence"
IDEMPOTENCY_PLACEHOLDER = "<generated-idempotency-key>"
RETRY_TIMESTAMP_PLACEHOLDER = "<scheduled-retry-timestamp>"


@contextmanager
def temporary_settings(**overrides: Any):
    previous = {name: getattr(settings, name) for name in overrides}
    try:
        for name, value in overrides.items():
            setattr(settings, name, value)
        yield
    finally:
        for name, value in previous.items():
            setattr(settings, name, value)


def transcript_payload(call_id: str, customer_id: str, source: str) -> dict[str, Any]:
    return {
        "call_id": call_id,
        "customer_id": customer_id,
        "transcript": (
            "The director confirmed budget and authority. They need launch this month "
            "and agreed that the next step is a technical implementation review tomorrow."
        ),
        "metadata": {"source": source},
    }


def queue_handoff(client: TestClient, *, call_id: str, customer_id: str, source: str) -> tuple[str, dict[str, Any]]:
    webhook = client.post(
        "/webhooks/n8n/call-transcript",
        json=transcript_payload(call_id, customer_id, source),
    )
    assert webhook.status_code == 200, webhook.text
    approval_id = webhook.json()["approval"]["id"]

    approved = client.post(
        f"/approvals/{approval_id}/approve",
        json={"reviewer": "readiness-drill", "notes": "Queue CRM handoff"},
    )
    assert approved.status_code == 200, approved.text

    events = client.get("/integration-events", params={"adapter_key": "bitrix24.mock"})
    assert events.status_code == 200, events.text
    event = next(item for item in events.json() if item["source_approval_id"] == approval_id)
    return approval_id, event


def telegram_secret_drill(client: TestClient) -> dict[str, Any]:
    with temporary_settings(telegram_webhook_secret="expected-secret"):
        approval = client.post(
            "/approvals",
            json={
                "kind": "content_review",
                "title": "Reject unsigned Telegram callback",
                "draft": "This item exists only for webhook-secret verification.",
                "context": {"source": "production-readiness-drill"},
            },
        )
        assert approval.status_code == 200, approval.text
        approval_id = approval.json()["id"]

        payload = {
            "update_id": 99001,
            "callback_query": {
                "id": "readiness-secret-check",
                "from": {"id": 99001, "username": "readiness"},
                "data": f"reject:{approval_id}",
            },
        }
        rejected = client.post("/webhooks/telegram/approval", json=payload)
        accepted = client.post(
            "/webhooks/telegram/approval",
            json=payload,
            headers={"X-Telegram-Bot-Api-Secret-Token": "expected-secret"},
        )
        assert rejected.status_code == 403, rejected.text
        assert accepted.status_code == 200, accepted.text
        body = accepted.json()
        assert body["approval_status"] == "rejected"

        runtime = client.get("/runtime").json()
        assert runtime["counters"]["telegram_callback_auth_failures_total"] >= 1
        return {
            "unsigned_callback_status_code": rejected.status_code,
            "signed_callback_status_code": accepted.status_code,
            "approval_status": body["approval_status"],
            "auth_failure_counter_present": True,
        }


def bitrix_retry_dead_letter_drill(client: TestClient) -> dict[str, Any]:
    with temporary_settings(
        bitrix24_dry_run=False,
        bitrix24_webhook_url=None,
        integration_max_attempts=2,
        integration_retry_delay_seconds=0,
    ):
        _, event = queue_handoff(
            client,
            call_id="CALL-READINESS-DEADLETTER",
            customer_id="LEAD-READINESS-DEADLETTER",
            source="production-readiness-dead-letter",
        )
        first = client.post(f"/integration-events/{event['id']}/dispatch/bitrix24")
        second = client.post(f"/integration-events/{event['id']}/dispatch/bitrix24")
        assert first.status_code == 200, first.text
        assert second.status_code == 200, second.text
        first_body = first.json()
        second_body = second.json()
        assert first_body["status"] == "not_configured"
        assert first_body["event_status"] == "retry"
        assert first_body["attempt_count"] == 1
        assert second_body["status"] == "not_configured"
        assert second_body["event_status"] == "dead_letter"
        assert second_body["attempt_count"] == 2

        events = client.get("/integration-events", params={"adapter_key": "bitrix24.mock"})
        stored = next(item for item in events.json() if item["id"] == event["id"])
        assert stored["status"] == "dead_letter"
        assert "Bitrix24 webhook URL is not configured" in stored["last_error"]
        return {
            "first_dispatch": {
                "status": first_body["status"],
                "event_status": first_body["event_status"],
                "attempt_count": first_body["attempt_count"],
            },
            "second_dispatch": {
                "status": second_body["status"],
                "event_status": second_body["event_status"],
                "attempt_count": second_body["attempt_count"],
            },
            "stored_event": {
                "status": stored["status"],
                "attempt_count": stored["attempt_count"],
                "last_error_contains": "Bitrix24 webhook URL is not configured",
            },
        }


def drain_retry_schedule_drill(client: TestClient) -> dict[str, Any]:
    with temporary_settings(
        bitrix24_dry_run=False,
        bitrix24_webhook_url=None,
        integration_max_attempts=3,
        integration_retry_delay_seconds=300,
    ):
        approval_id, event = queue_handoff(
            client,
            call_id="CALL-READINESS-DRAIN",
            customer_id="LEAD-READINESS-DRAIN",
            source="production-readiness-drain",
        )
        first = client.post("/integrations/bitrix24/drain", params={"limit": 100})
        assert first.status_code == 200, first.text
        first_body = first.json()
        assert first_body["retry"] >= 1
        assert event["id"] in first_body["event_ids"]

        retry_events = client.get(
            "/integration-events",
            params={"adapter_key": "bitrix24.mock", "status": "retry"},
        )
        retry_event = next(
            item for item in retry_events.json() if item["source_approval_id"] == approval_id
        )
        assert retry_event["attempt_count"] == 1
        assert retry_event["next_retry_at"] is not None

        second = client.post("/integrations/bitrix24/drain", params={"limit": 100})
        assert second.status_code == 200, second.text
        second_body = second.json()
        assert event["id"] not in second_body["event_ids"]
        return {
            "first_drain": {
                "selected": first_body["selected"],
                "retry": first_body["retry"],
                "event_was_selected": True,
            },
            "retry_event": {
                "status": retry_event["status"],
                "attempt_count": retry_event["attempt_count"],
                "next_retry_at": RETRY_TIMESTAMP_PLACEHOLDER,
            },
            "second_drain": {
                "event_was_skipped_until_retry_time": True,
                "selected": second_body["selected"],
            },
        }


def idempotency_drill(client: TestClient) -> dict[str, Any]:
    approval_id, event = queue_handoff(
        client,
        call_id="CALL-READINESS-IDEMPOTENCY",
        customer_id="LEAD-READINESS-IDEMPOTENCY",
        source="production-readiness-idempotency",
    )
    approval = store.get_approval(UUID(approval_id))
    queue_crm_handoff_if_needed(approval)
    queue_crm_handoff_if_needed(approval)

    events = client.get("/integration-events", params={"adapter_key": "bitrix24.mock"})
    matching_events = [
        item for item in events.json() if item["source_approval_id"] == approval_id
    ]
    assert len(matching_events) == 1
    assert matching_events[0]["id"] == event["id"]
    return {
        "source_approval_id": "<approval-id>",
        "matching_event_count": len(matching_events),
        "idempotency_key": IDEMPOTENCY_PLACEHOLDER,
        "status": matching_events[0]["status"],
    }


def worker_guard_drill(client: TestClient) -> dict[str, Any]:
    with temporary_settings(integration_worker_enabled=True, bitrix24_dry_run=True):
        runtime = client.get("/runtime")
        assert runtime.status_code == 200, runtime.text
        worker = runtime.json()["workers"]["bitrix24_outbox"]
        assert worker["enabled"] is True
        assert worker["dry_run"] is True
        assert worker["active"] is False
        return {
            "enabled": worker["enabled"],
            "dry_run": worker["dry_run"],
            "active": worker["active"],
            "guard": "worker remains inactive while Bitrix24 dry-run is enabled",
        }


def build_report() -> dict[str, Any]:
    with TestClient(app) as client:
        report = {
            "evidence_schema": "production_readiness_drill_v1",
            "ok": True,
            "storage": client.get("/runtime").json()["storage"],
            "checks": {
                "telegram_secret": telegram_secret_drill(client),
                "bitrix_retry_dead_letter": bitrix_retry_dead_letter_drill(client),
                "drain_retry_schedule": drain_retry_schedule_drill(client),
                "crm_handoff_idempotency": idempotency_drill(client),
                "worker_guard": worker_guard_drill(client),
            },
        }
        runtime = client.get("/runtime").json()
        report["runtime_counters"] = {
            "telegram_callback_auth_failures_total": runtime["counters"][
                "telegram_callback_auth_failures_total"
            ],
            "bitrix24_dispatch_failures_total": runtime["counters"][
                "bitrix24_dispatch_failures_total"
            ],
            "integration_dead_letters_total": runtime["counters"][
                "integration_dead_letters_total"
            ],
            "integration_retries_scheduled_total": runtime["counters"][
                "integration_retries_scheduled_total"
            ],
            "crm_handoffs_queued_total": runtime["counters"]["crm_handoffs_queued_total"],
        }
        assert report["runtime_counters"]["telegram_callback_auth_failures_total"] >= 1
        assert report["runtime_counters"]["bitrix24_dispatch_failures_total"] >= 3
        assert report["runtime_counters"]["integration_dead_letters_total"] >= 1
        assert report["runtime_counters"]["integration_retries_scheduled_total"] >= 2
        return report


def format_text(report: dict[str, Any]) -> str:
    checks = report["checks"]
    return "\n".join(
        [
            "production readiness drill passed",
            f"schema={report['evidence_schema']}",
            f"storage={report['storage']}",
            (
                "telegram_secret="
                f"unsigned={checks['telegram_secret']['unsigned_callback_status_code']} "
                f"signed={checks['telegram_secret']['signed_callback_status_code']} "
                f"approval={checks['telegram_secret']['approval_status']}"
            ),
            (
                "bitrix_retry_dead_letter="
                f"first={checks['bitrix_retry_dead_letter']['first_dispatch']['event_status']} "
                f"second={checks['bitrix_retry_dead_letter']['second_dispatch']['event_status']} "
                f"attempts={checks['bitrix_retry_dead_letter']['second_dispatch']['attempt_count']}"
            ),
            (
                "drain_retry_schedule="
                f"first_selected={checks['drain_retry_schedule']['first_drain']['event_was_selected']} "
                "second_skipped="
                f"{checks['drain_retry_schedule']['second_drain']['event_was_skipped_until_retry_time']}"
            ),
            (
                "crm_handoff_idempotency="
                f"matching_events={checks['crm_handoff_idempotency']['matching_event_count']} "
                f"key={checks['crm_handoff_idempotency']['idempotency_key']}"
            ),
            (
                "worker_guard="
                f"enabled={checks['worker_guard']['enabled']} "
                f"dry_run={checks['worker_guard']['dry_run']} "
                f"active={checks['worker_guard']['active']}"
            ),
            "runtime_counters:",
            *[
                f"  - {key}={value}"
                for key, value in report["runtime_counters"].items()
            ],
        ]
    )


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a local production-readiness drill and capture sanitized evidence."
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for generated evidence artifacts.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON instead of text.")
    args = parser.parse_args()

    report = build_report()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "production-readiness-drill.sanitized.json"
    text_path = output_dir / "production-readiness-drill.txt"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    text_path.write_text(format_text(report) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("production readiness drill captured")
        print(f"json={display_path(json_path)}")
        print(f"text={display_path(text_path)}")
        print(format_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
