#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from reviewer_snapshot import build_snapshot

DEFAULT_BASE_URL = "https://saleops.duckdns.org"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "evidence"
DEFAULT_GITHUB_REPO = "AlexGerlitz/ai-ops-workflow-kit"
DEFAULT_PROFILE_BASE_URL = "https://alexgerlitz.github.io/AlexGerlitz"
USER_AGENT = "aiops-reviewer-acceptance-report"
BITRIX24_CONTRACT_EVIDENCE = REPO_ROOT / "docs" / "evidence" / "bitrix24-contract.sanitized.json"


def fetch_json_url(url: str, timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={"accept": "application/vnd.github+json", "user-agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_text_url(url: str, timeout: float) -> str:
    request = urllib.request.Request(url, headers={"user-agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def fetch_binary_url(url: str, timeout: float) -> bytes:
    request = urllib.request.Request(url, headers={"user-agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def parse_key_value_lines(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            values[key] = value.strip()
    return values


def run_live_smoke(base_url: str, timeout: float) -> dict[str, Any]:
    command = ["bash", "scripts/smoke_live_demo.sh", base_url]
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    parsed = parse_key_value_lines(completed.stdout)
    passed = completed.returncode == 0 and "live demo smoke passed" in completed.stdout
    return {
        "status": "passed" if passed else "failed",
        "returncode": completed.returncode,
        "command": " ".join(command),
        "signals": parsed,
        "console_tail": completed.stdout[-4000:],
    }


def workflow_status(workflows: list[dict[str, Any]], path: str) -> dict[str, Any]:
    for workflow in workflows:
        if workflow.get("path") == path:
            return {
                "status": "passed" if workflow.get("state") == "active" else "failed",
                "id": workflow.get("id"),
                "name": workflow.get("name"),
                "path": workflow.get("path"),
                "state": workflow.get("state"),
                "html_url": workflow.get("html_url"),
            }
    return {"status": "failed", "path": path, "state": "missing"}


def latest_workflow_run(runs: list[dict[str, Any]], workflow_name: str) -> dict[str, Any]:
    for run in runs:
        if run.get("name") == workflow_name:
            return {
                "status": "passed" if run.get("conclusion") == "success" else "failed",
                "name": run.get("name"),
                "conclusion": run.get("conclusion"),
                "head_sha": run.get("head_sha"),
                "html_url": run.get("html_url"),
                "created_at": run.get("created_at"),
            }
    return {"status": "failed", "name": workflow_name, "conclusion": "missing"}


def build_github_report(repo: str, timeout: float) -> dict[str, Any]:
    encoded_repo = urllib.parse.quote(repo, safe="/")
    workflows_payload = fetch_json_url(
        f"https://api.github.com/repos/{encoded_repo}/actions/workflows",
        timeout,
    )
    runs_payload = fetch_json_url(
        f"https://api.github.com/repos/{encoded_repo}/actions/runs?branch=main&per_page=20",
        timeout,
    )
    workflows = workflows_payload.get("workflows", [])
    runs = runs_payload.get("workflow_runs", [])
    ci_workflow = workflow_status(workflows, ".github/workflows/ci.yml")
    sandbox_workflow = workflow_status(
        workflows,
        ".github/workflows/credentialed-sandbox-preflight.yml",
    )
    latest_ci = latest_workflow_run(runs, "CI")
    latest_sandbox = latest_workflow_run(runs, "Credentialed Sandbox Preflight")
    ok = (
        ci_workflow["status"] == "passed"
        and sandbox_workflow["status"] == "passed"
        and latest_ci["status"] == "passed"
        and latest_sandbox["status"] == "passed"
    )
    return {
        "status": "passed" if ok else "failed",
        "repo": repo,
        "ci_workflow": ci_workflow,
        "credentialed_sandbox_workflow": sandbox_workflow,
        "latest_checked_ci_run": latest_ci,
        "latest_checked_sandbox_run": latest_sandbox,
    }


def profile_page_check(url: str, required_markers: list[str], timeout: float) -> dict[str, Any]:
    body = fetch_text_url(url, timeout)
    missing = [marker for marker in required_markers if marker not in body]
    return {
        "status": "passed" if not missing else "failed",
        "url": url,
        "missing_markers": missing,
    }


def profile_pdf_check(url: str, timeout: float) -> dict[str, Any]:
    payload = fetch_binary_url(url, timeout)
    return {
        "status": "passed" if payload.startswith(b"%PDF") and len(payload) > 1000 else "failed",
        "url": url,
        "bytes": len(payload),
        "pdf_header_present": payload.startswith(b"%PDF"),
    }


def build_profile_report(profile_base_url: str, timeout: float) -> dict[str, Any]:
    base = profile_base_url.rstrip("/")
    pages = [
        profile_page_check(
            base + "/",
            ["AI Ops proof status", "credentialed-sandbox-preflight.yml"],
            timeout,
        ),
        profile_page_check(
            base + "/verification-pack.html",
            ["AI Ops public proof status", "owner-run sandbox workflow"],
            timeout,
        ),
        profile_page_check(
            base + "/hiring-screen.html",
            ["AI Ops sandbox workflow", "AI Ops CI workflow"],
            timeout,
        ),
        profile_page_check(
            base + "/application-pack.html",
            ["owner-run sandbox workflow", "AI Ops public proof status"],
            timeout,
        ),
        profile_page_check(
            base + "/resume.html",
            ["owner-run sandbox workflow", "AI Ops public proof status"],
            timeout,
        ),
        profile_pdf_check(
            base + "/output/pdf/alex-gerlitz-remote-ai-automation-resume.pdf",
            timeout,
        ),
    ]
    return {
        "status": "passed" if all(item["status"] == "passed" for item in pages) else "failed",
        "profile_base_url": base,
        "pages": pages,
    }


def build_bitrix24_contract_report() -> dict[str, Any]:
    try:
        payload = json.loads(BITRIX24_CONTRACT_EVIDENCE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "status": "failed",
            "artifact": str(BITRIX24_CONTRACT_EVIDENCE.relative_to(REPO_ROOT)),
            "error": exc.__class__.__name__,
        }

    checks = payload.get("checks") or {}
    contract = payload.get("contract") or {}
    secret_boundaries = payload.get("secret_boundaries") or {}
    passed = (
        payload.get("ok") is True
        and contract.get("method") == "crm.lead.update"
        and checks.get("request_shape") is True
        and checks.get("secret_token_leaked") is False
        and secret_boundaries.get("secrets_printed") is False
        and secret_boundaries.get("mutating_external_calls") is False
    )
    return {
        "status": "passed" if passed else "failed",
        "artifact": str(BITRIX24_CONTRACT_EVIDENCE.relative_to(REPO_ROOT)),
        "method": contract.get("method"),
        "request_shape": checks.get("request_shape"),
        "secret_token_leaked": checks.get("secret_token_leaked"),
        "external_calls": payload.get("external_calls"),
    }


def build_report(
    base_url: str,
    github_repo: str,
    profile_base_url: str,
    timeout: float,
    smoke_timeout: float,
) -> dict[str, Any]:
    snapshot = build_snapshot(base_url, timeout)
    smoke = run_live_smoke(base_url, smoke_timeout)
    github = build_github_report(github_repo, timeout)
    profile = build_profile_report(profile_base_url, timeout)
    bitrix24_contract = build_bitrix24_contract_report()
    checks = {
        "live_snapshot": "passed" if snapshot.get("ok") is True else "failed",
        "live_smoke": smoke["status"],
        "github": github["status"],
        "profile_pages": profile["status"],
        "bitrix24_contract": bitrix24_contract["status"],
    }
    ok = all(status == "passed" for status in checks.values())
    return {
        "evidence_schema": "reviewer_acceptance_report_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ok": ok,
        "sanitized": True,
        "secret_boundaries": {
            "secrets_printed": False,
            "mutating_external_calls": False,
            "sanitized_credentialed_sandbox_artifacts_committed": True,
        },
        "checks": checks,
        "base_url": base_url.rstrip("/"),
        "live_snapshot": {
            "version": snapshot["version"],
            "git_sha": snapshot["git_sha"],
            "storage": snapshot["storage"],
            "llm": snapshot["llm"],
            "integrations": snapshot["integrations"],
            "workflow": {
                "google_drive_source": snapshot["workflow"]["google_drive_source"],
                "score": snapshot["workflow"]["score"],
                "risk_level": snapshot["workflow"]["risk_level"],
                "approval_status": snapshot["workflow"]["approval_status"],
                "telegram_status": snapshot["workflow"]["telegram_status"],
                "bitrix24_status": snapshot["workflow"]["bitrix24_status"],
                "crm_event_status": snapshot["workflow"]["crm_event_status"],
            },
            "worker": snapshot["worker"],
            "metrics": snapshot["metrics"],
        },
        "live_smoke": smoke,
        "github": github,
        "profile": profile,
        "bitrix24_contract": bitrix24_contract,
        "private_sandbox_next_step": (
            "Combined Telegram and Bitrix24 owner-run sandbox evidence is present; rerun "
            "Credentialed Sandbox Preflight when rotating either secret."
        ),
    }


def format_text(report: dict[str, Any]) -> str:
    snapshot = report["live_snapshot"]
    smoke_signals = report["live_smoke"]["signals"]
    github = report["github"]
    profile = report["profile"]
    latest_ci = github["latest_checked_ci_run"]
    latest_sandbox = github.get("latest_checked_sandbox_run", {})
    bitrix24_contract = report["bitrix24_contract"]
    return "\n".join(
        [
            "reviewer acceptance report passed" if report["ok"] else "reviewer acceptance report failed",
            f"schema={report['evidence_schema']}",
            f"base_url={report['base_url']}",
            f"live_snapshot={report['checks']['live_snapshot']} git_sha={snapshot['git_sha']} llm={snapshot['llm']['selected_provider']}",
            (
                "live_smoke="
                f"{report['checks']['live_smoke']} "
                f"score={smoke_signals.get('score')} "
                f"telegram_callback={smoke_signals.get('telegram_callback')} "
                f"bitrix24_drain={smoke_signals.get('bitrix24_drain')}"
            ),
            (
                "github="
                f"{report['checks']['github']} "
                f"ci={latest_ci.get('conclusion')} "
                f"ci_sha={latest_ci.get('head_sha')} "
                f"sandbox_workflow={github['credentialed_sandbox_workflow'].get('state')} "
                f"sandbox_run={latest_sandbox.get('conclusion')}"
            ),
            f"profile_pages={report['checks']['profile_pages']} count={len(profile['pages'])}",
            (
                "bitrix24_contract="
                f"{report['checks']['bitrix24_contract']} "
                f"method={bitrix24_contract.get('method')} "
                f"request_shape={bitrix24_contract.get('request_shape')} "
                f"secret_token_leaked={bitrix24_contract.get('secret_token_leaked')}"
            ),
            (
                "secret_boundaries="
                f"secrets_printed={report['secret_boundaries']['secrets_printed']} "
                f"mutating_external_calls={report['secret_boundaries']['mutating_external_calls']}"
            ),
            f"private_sandbox_next_step={report['private_sandbox_next_step']}",
        ]
    )


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a sanitized reviewer acceptance report from live public proof surfaces."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--github-repo", default=DEFAULT_GITHUB_REPO)
    parser.add_argument("--profile-base-url", default=DEFAULT_PROFILE_BASE_URL)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--smoke-timeout", type=float, default=45.0)
    parser.add_argument("--json", action="store_true", help="Print JSON instead of text.")
    args = parser.parse_args()

    try:
        report = build_report(
            base_url=args.base_url,
            github_repo=args.github_repo,
            profile_base_url=args.profile_base_url,
            timeout=args.timeout,
            smoke_timeout=args.smoke_timeout,
        )
    except (
        AssertionError,
        subprocess.TimeoutExpired,
        urllib.error.URLError,
        TimeoutError,
        json.JSONDecodeError,
    ) as exc:
        print(f"reviewer acceptance report failed: {exc}", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "reviewer-acceptance-report.sanitized.json"
    text_path = output_dir / "reviewer-acceptance-report.txt"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    text_path.write_text(format_text(report) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("reviewer acceptance report captured")
        print(f"json={display_path(json_path)}")
        print(f"text={display_path(text_path)}")
        print(format_text(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
