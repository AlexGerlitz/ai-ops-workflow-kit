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

os.environ.setdefault("DATABASE_URL", "")
os.environ.setdefault("PUBLIC_BASE_URL", "https://saleops.duckdns.org")
sys.path.insert(0, str(REPO_ROOT))

from scripts.business_scenario_replay import build_report as build_replay_report
from scripts.business_scenario_replay import run_demo
from scripts.production_readiness_drill import build_report as build_readiness_report


def build_report() -> dict[str, Any]:
    replay = build_replay_report(run_demo())
    readiness = build_readiness_report()
    readiness_checks = readiness["checks"]

    high_bar_checks = {
        "business_workflow_to_backend_state": replay["ok"] is True,
        "rag_quality_reviewable": replay["proof_signals"]["rag_quality"]["ok"] is True
        and replay["proof_signals"]["rag_quality"]["citations_present"] is True,
        "privacy_boundary_owned": replay["proof_signals"]["privacy"]["redacted"] is True
        and replay["proof_signals"]["privacy"]["raw_text_stored"] is False,
        "approval_to_crm_handoff_controlled": replay["proof_signals"]["approval"]["status"] == "approved"
        and replay["proof_signals"]["crm_handoff"]["status"] == "queued",
        "external_writes_gated": replay["proof_signals"]["bitrix24_dispatch"]["status"] == "dry_run",
        "failure_modes_tested": readiness["ok"] is True
        and readiness_checks["bitrix_retry_dead_letter"]["second_dispatch"]["event_status"]
        == "dead_letter"
        and readiness_checks["crm_handoff_idempotency"]["matching_event_count"] == 1,
        "worker_guarded_in_dry_run": readiness_checks["worker_guard"]["active"] is False,
    }
    ok = all(high_bar_checks.values())

    return {
        "schema": "hiring_signal_brief_v1",
        "ok": ok,
        "shortlist_signal": (
            "backend/platform owner for AI workflow systems where business context, "
            "RAG quality, approval state, CRM/ERP/API handoff, retries, audit, and "
            "operator handoff must be reviewable."
        ),
        "best_fit_roles": [
            "AI Automation Engineer",
            "Backend / Platform Engineer",
            "LLM Workflow / RAG Engineer",
            "CRM / ERP / API Integration Engineer",
            "Internal Tools / Operations Platform Engineer",
            "DevOps / Reliability Engineer for workflow systems",
        ],
        "high_bar_checks": high_bar_checks,
        "proof_summary": {
            "business_route": " -> ".join(step["step"] for step in replay["backend_route"]),
            "rag_quality": replay["proof_signals"]["rag_quality"],
            "privacy": replay["proof_signals"]["privacy"],
            "approval": replay["proof_signals"]["approval"],
            "crm_handoff": replay["proof_signals"]["crm_handoff"],
            "bitrix24_dispatch": replay["proof_signals"]["bitrix24_dispatch"],
            "production_readiness": {
                "telegram_secret": readiness_checks["telegram_secret"],
                "bitrix_retry_dead_letter": readiness_checks["bitrix_retry_dead_letter"],
                "drain_retry_schedule": readiness_checks["drain_retry_schedule"],
                "crm_handoff_idempotency": readiness_checks["crm_handoff_idempotency"],
                "worker_guard": readiness_checks["worker_guard"],
                "runtime_counters": readiness["runtime_counters"],
            },
        },
        "risk_reduction": [
            "hidden automation state becomes backend-owned records, approval state, outbox events, and audit-friendly evidence",
            "untrusted AI output gets RAG expected-source checks, citations, structured analysis, and human approval",
            "brittle CRM handoff gets adapter contracts, idempotency, retry scheduling, and dead-letter behavior",
            "unsafe external writes stay dry-run or approval-gated until credentialed sandbox proof is reviewed",
            "remote review ambiguity is reduced through commands, tests, docs, runbooks, metrics, and sanitized evidence",
        ],
        "first_assignment": (
            "Turn one risky document/transcript/lead workflow into a verified slice with "
            "backend-owned state, RAG quality checks, approval, CRM-safe handoff, metrics, "
            "tests, docs, and operator handoff notes."
        ),
        "reviewer_commands": [
            "python3 scripts/hiring_signal_brief.py",
            "python3 scripts/business_scenario_replay.py",
            "python3 scripts/production_readiness_drill.py",
            "bash scripts/verify_public.sh",
        ],
        "source_artifacts": [
            "docs/evidence/hiring-signal-brief.txt",
            "docs/evidence/hiring-signal-brief.sanitized.json",
            "docs/evidence/business-scenario-replay.txt",
            "docs/evidence/production-readiness-drill.txt",
            "docs/TECHNICAL_REVIEW_PACKET.md",
            "docs/EMPLOYER_TRIGGER_PROOF.md",
        ],
    }


def format_text(report: dict[str, Any]) -> str:
    proof = report["proof_summary"]
    rag = proof["rag_quality"]
    privacy = proof["privacy"]
    approval = proof["approval"]
    crm = proof["crm_handoff"]
    bitrix = proof["bitrix24_dispatch"]
    readiness = proof["production_readiness"]
    checks = report["high_bar_checks"]

    lines = [
        "hiring signal brief passed" if report["ok"] else "hiring signal brief failed",
        f"schema={report['schema']}",
        f"shortlist_signal={report['shortlist_signal']}",
        f"business_route={proof['business_route']}",
        (
            "quality_gate="
            f"rag_ok={rag['ok']} passed={rag['passed']}/{rag['total']} "
            f"citations_present={rag['citations_present']}"
        ),
        (
            "privacy="
            f"redacted={privacy['redacted']} raw_text_stored={privacy['raw_text_stored']} "
            f"safe_logging={privacy['safe_logging']}"
        ),
        (
            "handoff="
            f"approval={approval['status']} crm={crm['status']} "
            f"idempotency_key_present={crm['idempotency_key_present']} "
            f"bitrix24={bitrix['status']}"
        ),
        (
            "production_readiness="
            f"telegram_secret_signed={readiness['telegram_secret']['signed_callback_status_code']} "
            "retry_dead_letter="
            f"{readiness['bitrix_retry_dead_letter']['second_dispatch']['event_status']} "
            "retry_schedule_skips_until_due="
            f"{readiness['drain_retry_schedule']['second_drain']['event_was_skipped_until_retry_time']} "
            "idempotent_events="
            f"{readiness['crm_handoff_idempotency']['matching_event_count']} "
            f"worker_active={readiness['worker_guard']['active']}"
        ),
        "high_bar_checks:",
        *[f"  - {key}={value}" for key, value in checks.items()],
        "risk_reduction:",
        *[f"  - {item}" for item in report["risk_reduction"]],
        f"first_assignment={report['first_assignment']}",
    ]
    return "\n".join(lines) + "\n"


def write_report(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "hiring-signal-brief.sanitized.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "hiring-signal-brief.txt").write_text(
        format_text(report),
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write a public-safe hiring signal brief from replay and readiness evidence."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for hiring-signal-brief evidence files.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON instead of text.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report()
    write_report(report, args.output_dir)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(format_text(report), end="")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
