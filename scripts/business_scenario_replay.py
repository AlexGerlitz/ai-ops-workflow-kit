#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "evidence"
sys.path.insert(0, str(REPO_ROOT))


def run_demo() -> dict[str, Any]:
    os.environ.setdefault("DATABASE_URL", "")
    os.environ.setdefault("PUBLIC_BASE_URL", "https://saleops.duckdns.org")

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        response = client.post("/demo/run")
        response.raise_for_status()
        return response.json()


def build_report(payload: dict[str, Any]) -> dict[str, Any]:
    rag_quality = payload["rag_quality"]
    call_analysis = payload["call_analysis"]
    privacy = payload["privacy"]
    transcription = payload["transcription"]
    approval = payload["approval"]
    crm_handoff = payload["crm_handoff"]
    bitrix24_dispatch = payload["bitrix24_dispatch"]
    telegram_approval = payload["telegram_approval"]

    ok = (
        rag_quality["ok"] is True
        and privacy["redacted"] is True
        and privacy["raw_text_stored"] is False
        and call_analysis["score"] >= 80
        and approval["status"] == "approved"
        and crm_handoff["status"] == "queued"
        and bitrix24_dispatch["status"] == "dry_run"
    )

    return {
        "schema": "business_scenario_replay_v1",
        "ok": ok,
        "scenario": "sales_support_call_to_reviewed_crm_handoff",
        "business_input": {
            "knowledge_source": "gdrive://demo-sales-playbook",
            "call_source": transcription["audio_uri"],
            "lead_context": [
                "pricing concern",
                "approved budget",
                "workflow needed this month",
                "implementation call as the next step",
            ],
            "raw_personal_data_stored": False,
        },
        "backend_route": [
            {
                "step": "knowledge ingestion",
                "surface": "Google Drive import and document chunks",
                "status": "passed",
            },
            {
                "step": "retrieval quality gate",
                "surface": "RAG expected-source eval with citations",
                "status": "passed" if rag_quality["ok"] else "failed",
            },
            {
                "step": "call analysis",
                "surface": "structured score, objections, risk, next action",
                "status": "passed" if call_analysis["score"] >= 80 else "failed",
            },
            {
                "step": "human approval",
                "surface": "approval state and Telegram callback contract",
                "status": approval["status"],
            },
            {
                "step": "CRM-safe handoff",
                "surface": "queued outbox event with idempotency and retry contract",
                "status": crm_handoff["status"],
            },
            {
                "step": "Bitrix24 adapter boundary",
                "surface": "dry-run crm.lead.update request shape",
                "status": bitrix24_dispatch["status"],
            },
        ],
        "proof_signals": {
            "rag_quality": {
                "ok": rag_quality["ok"],
                "passed": rag_quality["passed"],
                "total": rag_quality["total"],
                "citations_present": all(
                    bool(result["citations"]) for result in rag_quality["results"]
                ),
            },
            "transcription": {
                "provider": transcription["provider"],
                "status": transcription["status"],
                "segments": len(transcription["segments"]),
            },
            "call_analysis": {
                "score": call_analysis["score"],
                "risk_level": call_analysis["risk_level"],
                "objections": call_analysis["objections"],
                "missing_signals": call_analysis["missing_signals"],
            },
            "privacy": {
                "redacted": privacy["redacted"],
                "raw_text_stored": privacy["raw_text_stored"],
                "safe_logging": privacy["safe_logging"],
                "replacement_counts": privacy["replacement_counts"],
            },
            "approval": {
                "status": approval["status"],
                "telegram_status": telegram_approval["status"],
                "telegram_callback_contract": sorted(
                    telegram_approval["callback_contract"].keys()
                ),
            },
            "crm_handoff": {
                "adapter_key": crm_handoff["adapter_key"],
                "operation": crm_handoff["operation"],
                "status": crm_handoff["status"],
                "idempotency_key_present": bool(crm_handoff["idempotency_key"]),
                "attempt_count": crm_handoff["attempt_count"],
                "last_error": crm_handoff["last_error"],
                "target_stage": crm_handoff["target_stage"],
            },
            "bitrix24_dispatch": {
                "adapter_key": bitrix24_dispatch["adapter_key"],
                "status": bitrix24_dispatch["status"],
                "event_status": bitrix24_dispatch["event_status"],
                "method": bitrix24_dispatch["method"],
                "attempt_count": bitrix24_dispatch["attempt_count"],
                "max_attempts": bitrix24_dispatch["max_attempts"],
                "request_fields": sorted(
                    bitrix24_dispatch["bitrix_request"]["fields"].keys()
                ),
            },
        },
        "first_slice_result": (
            "A sales/support transcript becomes a cited RAG answer, structured lead "
            "analysis, approved follow-up, queued CRM handoff, and dry-run Bitrix24 "
            "request without storing raw personal data in public evidence."
        ),
        "reviewer_commands": [
            "python3 scripts/business_scenario_replay.py",
            "python3 scripts/run_offer_demo.py",
            "bash scripts/verify_public.sh",
        ],
        "handoff_artifacts": [
            "docs/OFFER_DEMO.md",
            "docs/FIRST_SLICE_PLAYBOOK.md",
            "docs/PRIVACY_BOUNDARY.md",
            "docs/evidence/business-scenario-replay.txt",
            "docs/evidence/business-scenario-replay.sanitized.json",
        ],
    }


def format_text(report: dict[str, Any]) -> str:
    rag = report["proof_signals"]["rag_quality"]
    analysis = report["proof_signals"]["call_analysis"]
    privacy = report["proof_signals"]["privacy"]
    approval = report["proof_signals"]["approval"]
    crm = report["proof_signals"]["crm_handoff"]
    bitrix = report["proof_signals"]["bitrix24_dispatch"]

    route = " -> ".join(step["step"] for step in report["backend_route"])
    objections = ", ".join(analysis["objections"]) or "none"
    missing = ", ".join(analysis["missing_signals"]) or "none"

    lines = [
        "business scenario replay passed" if report["ok"] else "business scenario replay failed",
        f"schema={report['schema']}",
        f"scenario={report['scenario']}",
        f"backend_route={route}",
        (
            "rag_quality="
            f"ok={rag['ok']} passed={rag['passed']}/{rag['total']} "
            f"citations_present={rag['citations_present']}"
        ),
        (
            "call_analysis="
            f"score={analysis['score']} risk={analysis['risk_level']} "
            f"objections={objections} missing_signals={missing}"
        ),
        (
            "privacy="
            f"redacted={privacy['redacted']} raw_text_stored={privacy['raw_text_stored']} "
            f"safe_logging={privacy['safe_logging']} replacements={privacy['replacement_counts']}"
        ),
        (
            "approval="
            f"status={approval['status']} telegram_status={approval['telegram_status']} "
            f"callbacks={','.join(approval['telegram_callback_contract'])}"
        ),
        (
            "crm_handoff="
            f"adapter={crm['adapter_key']} status={crm['status']} "
            f"idempotency_key_present={crm['idempotency_key_present']} "
            f"attempt_count={crm['attempt_count']} target_stage={crm['target_stage']}"
        ),
        (
            "bitrix24_dispatch="
            f"adapter={bitrix['adapter_key']} status={bitrix['status']} "
            f"event_status={bitrix['event_status']} method={bitrix['method']} "
            f"attempt_count={bitrix['attempt_count']} max_attempts={bitrix['max_attempts']}"
        ),
        f"first_slice_result={report['first_slice_result']}",
    ]
    return "\n".join(lines) + "\n"


def write_report(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "business-scenario-replay.sanitized.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "business-scenario-replay.txt").write_text(
        format_text(report),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write a public-safe business scenario replay from the offer demo."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for business-scenario-replay evidence files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(run_demo())
    write_report(report, args.output_dir)
    print(format_text(report), end="")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
