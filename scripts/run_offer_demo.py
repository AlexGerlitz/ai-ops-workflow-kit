#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
from typing import Any

os.environ["DATABASE_URL"] = ""
os.environ.setdefault("PUBLIC_BASE_URL", "http://saleops.duckdns.org")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


PLAYBOOK_PATH = ROOT / "demo" / "sales-playbook.md"
TRANSCRIPT_PATH = ROOT / "demo" / "call-transcript.json"


def request_json(client: TestClient, method: str, path: str, **kwargs: Any) -> dict[str, Any] | list[Any]:
    response = getattr(client, method)(path, **kwargs)
    if response.status_code >= 400:
        raise SystemExit(f"{method.upper()} {path} failed: {response.status_code} {response.text}")
    return response.json()


def main() -> None:
    playbook = PLAYBOOK_PATH.read_text(encoding="utf-8")
    transcript_payload = json.loads(TRANSCRIPT_PATH.read_text(encoding="utf-8"))

    with TestClient(app) as client:
        health = request_json(client, "get", "/health")
        integrations = request_json(client, "get", "/integrations/runtime")
        document = request_json(
            client,
            "post",
            "/documents",
            json={
                "source": "drive://demo/sales-playbook",
                "text": playbook,
                "metadata": {"team": "sales", "public_demo": True},
            },
        )
        rag = request_json(
            client,
            "post",
            "/query",
            json={
                "question": "What should happen before a follow-up reaches the CRM?",
                "top_k": 3,
            },
        )
        analysis = request_json(
            client,
            "post",
            "/webhooks/n8n/call-transcript",
            json=transcript_payload,
        )
        approval_id = analysis["approval"]["id"]
        telegram = request_json(
            client,
            "post",
            f"/approvals/{approval_id}/notify/telegram",
        )
        approved = request_json(
            client,
            "post",
            f"/approvals/{approval_id}/approve",
            json={"reviewer": "sales-lead", "notes": "Synthetic demo approval"},
        )
        events = request_json(
            client,
            "get",
            "/integration-events",
            params={"adapter_key": "bitrix24.mock"},
        )

    crm_event = next(
        event for event in events if event.get("source_approval_id") == approval_id
    )
    with TestClient(app) as client:
        bitrix24 = request_json(
            client,
            "post",
            f"/integration-events/{crm_event['id']}/dispatch/bitrix24",
        )
    result = {
        "runtime": health,
        "integrations": integrations,
        "ingestion": document,
        "rag_context_sources": [
            {"source": context["source"], "score": context["score"]}
            for context in rag["contexts"]
        ],
        "call_analysis": {
            "call_id": analysis["call_id"],
            "customer_id": analysis["customer_id"],
            "score": analysis["score"],
            "risk_level": analysis["analysis"]["risk_level"],
            "missing_signals": analysis["analysis"]["missing_signals"],
            "objections": analysis["analysis"]["objections"],
            "next_action": analysis["analysis"]["next_action"],
            "follow_up_draft": analysis["analysis"]["follow_up_draft"],
        },
        "approval": {
            "id": approval_id,
            "status": approved["status"],
            "reviewer": approved["reviewer"],
        },
        "telegram_approval": {
            "adapter_key": telegram["adapter_key"],
            "operation": telegram["operation"],
            "status": telegram["status"],
            "callback_contract": telegram["payload"]["callback_contract"],
        },
        "crm_handoff": {
            "event_id": crm_event["id"],
            "adapter_key": crm_event["adapter_key"],
            "operation": crm_event["operation"],
            "status": crm_event["status"],
            "target_stage": crm_event["payload"]["target_stage"],
            "task": crm_event["payload"]["task"],
        },
        "bitrix24_dispatch": {
            "adapter_key": bitrix24["adapter_key"],
            "operation": bitrix24["operation"],
            "status": bitrix24["status"],
            "method": bitrix24["payload"]["method"],
        },
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
