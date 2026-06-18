#!/usr/bin/env python3
import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any


def normalize_base_url(value: str) -> str:
    return value.rstrip("/")


def fetch_json(base_url: str, method: str, path: str, timeout: float) -> Any:
    request = urllib.request.Request(
        normalize_base_url(base_url) + path,
        method=method,
        headers={"accept": "application/json"},
    )
    if method == "POST":
        request.add_header("content-type", "application/json")
        request.data = b"{}"
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_text(base_url: str, path: str, timeout: float) -> str:
    with urllib.request.urlopen(normalize_base_url(base_url) + path, timeout=timeout) as response:
        return response.read().decode("utf-8")


def provider_required_env(llm_runtime: dict[str, Any]) -> set[str]:
    return {
        env
        for provider in llm_runtime.get("providers", [])
        for env in provider.get("required_env", [])
    }


def integration_mode(runtime: dict[str, Any], adapter_key: str) -> str:
    integrations = runtime.get("integrations", {})
    adapter = integrations.get(adapter_key, {})
    if adapter.get("dry_run") is True:
        return "dry_run"
    if adapter.get("configured") is True:
        return "configured"
    return "not_configured"


def assert_snapshot(snapshot: dict[str, Any]) -> None:
    runtime = snapshot["runtime_raw"]
    llm_runtime = snapshot["llm_runtime_raw"]
    demo = snapshot["demo_raw"]
    metrics = snapshot["metrics_raw"]

    assert runtime["ok"] is True
    assert runtime["storage"] in {"memory", "postgres"}
    assert runtime["llm"]["selected_provider"] in {"local", "openai", "claude", "gemini"}
    assert set(runtime["llm"]["supported_providers"]) == {"local", "openai", "claude", "gemini"}
    assert llm_runtime["selected_provider"] == runtime["llm"]["selected_provider"]
    assert {"OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"} <= provider_required_env(
        llm_runtime
    )
    assert runtime["workers"]["bitrix24_outbox"]["active"] is False
    assert "aiops_runtime_info" in metrics
    assert "aiops_demo_runs_total" in metrics

    assert demo["runtime"]["ok"] is True
    assert demo["runtime"]["llm"]["selected_provider"] == runtime["llm"]["selected_provider"]
    assert demo["google_drive_import"]["source"].startswith("gdrive://")
    assert demo["google_drive_import"]["chunks"] >= 1
    assert demo["rag_context_sources"], "RAG returned no source context"
    assert demo["call_analysis"]["score"] >= 80
    assert demo["approval"]["status"] == "approved"
    assert demo["telegram_approval"]["status"] == "dry_run"
    assert demo["crm_handoff"]["status"] == "queued"
    assert demo["crm_handoff"]["idempotency_key"]
    assert demo["bitrix24_dispatch"]["status"] == "dry_run"
    assert demo["bitrix24_dispatch"]["event_status"] == "queued"


def build_snapshot(base_url: str, timeout: float) -> dict[str, Any]:
    runtime = fetch_json(base_url, "GET", "/runtime", timeout)
    llm_runtime = fetch_json(base_url, "GET", "/llm/runtime", timeout)
    integrations = fetch_json(base_url, "GET", "/integrations/runtime", timeout)
    metrics = fetch_text(base_url, "/metrics", timeout)
    demo = fetch_json(base_url, "POST", "/demo/run", timeout)

    snapshot = {
        "base_url": normalize_base_url(base_url),
        "runtime_raw": runtime,
        "llm_runtime_raw": llm_runtime,
        "integrations_raw": integrations,
        "metrics_raw": metrics,
        "demo_raw": demo,
    }
    assert_snapshot(snapshot)

    providers = [
        {
            "provider": provider["provider"],
            "configured": provider["configured"],
            "selected": provider["selected"],
            "required_env": provider["required_env"],
        }
        for provider in llm_runtime["providers"]
    ]
    capabilities = {
        item["adapter_key"]: {
            "configured": item["configured"],
            "dry_run": item["dry_run"],
        }
        for item in integrations.get("capabilities", [])
    }

    return {
        "base_url": normalize_base_url(base_url),
        "ok": True,
        "version": runtime["version"],
        "git_sha": runtime["git_sha"],
        "storage": runtime["storage"],
        "public_base_url": runtime["public_base_url"],
        "llm": {
            "requested_provider": llm_runtime["requested_provider"],
            "selected_provider": llm_runtime["selected_provider"],
            "fallback": llm_runtime["fallback"],
            "supported_providers": llm_runtime["supported_providers"],
            "providers": providers,
        },
        "integrations": {
            "google_drive": capabilities.get("google_drive")
            or {"mode": integration_mode(runtime, "google_drive")},
            "telegram": capabilities.get("telegram.approval")
            or {"mode": integration_mode(runtime, "telegram.approval")},
            "bitrix24": capabilities.get("bitrix24")
            or {"mode": integration_mode(runtime, "bitrix24")},
        },
        "workflow": {
            "google_drive_source": demo["google_drive_import"]["source"],
            "rag_context_sources": demo["rag_context_sources"],
            "score": demo["call_analysis"]["score"],
            "risk_level": demo["call_analysis"]["risk_level"],
            "approval_status": demo["approval"]["status"],
            "telegram_status": demo["telegram_approval"]["status"],
            "crm_event_status": demo["crm_handoff"]["status"],
            "crm_idempotency_key": demo["crm_handoff"]["idempotency_key"],
            "bitrix24_status": demo["bitrix24_dispatch"]["status"],
            "bitrix24_event_status": demo["bitrix24_dispatch"]["event_status"],
        },
        "worker": runtime["workers"]["bitrix24_outbox"],
        "metrics": {
            "runtime_info": "aiops_runtime_info" in metrics,
            "demo_runs_total": "aiops_demo_runs_total" in metrics,
        },
        "reviewer_conclusion": [
            "deployed API responds with runtime identity",
            "LLM boundary exposes OpenAI, Claude, Gemini, and local fallback without secrets",
            "demo imports Google Drive text into RAG and returns source context",
            "transcript analysis produces a high lead score and approval item",
            "Telegram and Bitrix24 remain dry-run in public mode",
            "CRM handoff is queued with an idempotency key after approval",
            "worker state and Prometheus-style metrics are inspectable",
        ],
    }


def format_text(snapshot: dict[str, Any]) -> str:
    provider_lines = [
        f"  - {item['provider']}: configured={item['configured']} selected={item['selected']}"
        for item in snapshot["llm"]["providers"]
    ]
    integration_lines = [
        f"  - {name}: configured={value.get('configured')} dry_run={value.get('dry_run')}"
        for name, value in snapshot["integrations"].items()
    ]
    conclusion_lines = [f"  - {item}" for item in snapshot["reviewer_conclusion"]]
    workflow = snapshot["workflow"]
    worker = snapshot["worker"]
    worker_dry_run = worker.get("dry_run_blocked", worker.get("dry_run"))
    return "\n".join(
        [
            "technical reviewer snapshot passed",
            f"base_url={snapshot['base_url']}",
            f"version={snapshot['version']}",
            f"git_sha={snapshot['git_sha']}",
            f"storage={snapshot['storage']}",
            f"public_base_url={snapshot['public_base_url']}",
            (
                "llm="
                f"{snapshot['llm']['selected_provider']} "
                f"requested={snapshot['llm']['requested_provider']} "
                f"fallback={snapshot['llm']['fallback']}"
            ),
            "providers:",
            *provider_lines,
            "integrations:",
            *integration_lines,
            (
                "workflow="
                f"source={workflow['google_drive_source']} "
                f"score={workflow['score']} "
                f"risk={workflow['risk_level']} "
                f"approval={workflow['approval_status']} "
                f"telegram={workflow['telegram_status']} "
                f"bitrix24={workflow['bitrix24_status']} "
                f"crm={workflow['crm_event_status']}"
            ),
            f"crm_idempotency_key={workflow['crm_idempotency_key']}",
            (
                "worker="
                f"enabled={worker['enabled']} "
                f"active={worker['active']} "
                f"dry_run_blocked={worker_dry_run}"
            ),
            (
                "metrics="
                f"runtime_info={snapshot['metrics']['runtime_info']} "
                f"demo_runs_total={snapshot['metrics']['demo_runs_total']}"
            ),
            "reviewer_conclusion:",
            *conclusion_lines,
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a reviewer-facing live API snapshot.")
    parser.add_argument(
        "base_url",
        nargs="?",
        default="https://saleops.duckdns.org",
        help="API base URL to verify, defaults to the public live demo.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON instead of text.")
    parser.add_argument("--timeout", type=float, default=15.0, help="HTTP timeout in seconds.")
    args = parser.parse_args()

    try:
        snapshot = build_snapshot(args.base_url, args.timeout)
    except (AssertionError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        print(f"technical reviewer snapshot failed: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(snapshot, indent=2, ensure_ascii=False))
    else:
        print(format_text(snapshot))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
