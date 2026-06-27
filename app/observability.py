from datetime import UTC, datetime
from threading import Lock


class RuntimeStats:
    def __init__(self) -> None:
        self.started_at = datetime.now(UTC)
        self._lock = Lock()
        self._counters: dict[str, int] = {
            "demo_runs_total": 0,
            "documents_ingested_total": 0,
            "google_drive_imports_total": 0,
            "query_requests_total": 0,
            "audio_webhooks_total": 0,
            "audio_transcriptions_total": 0,
            "transcript_webhooks_total": 0,
            "privacy_redacted_transcripts_total": 0,
            "privacy_redactions_total": 0,
            "approvals_created_total": 0,
            "approvals_approved_total": 0,
            "approvals_rejected_total": 0,
            "telegram_dispatches_total": 0,
            "telegram_callbacks_total": 0,
            "telegram_callback_auth_failures_total": 0,
            "bitrix24_dispatches_total": 0,
            "bitrix24_dispatch_failures_total": 0,
            "crm_handoffs_queued_total": 0,
            "integration_dead_letters_total": 0,
            "integration_events_drained_total": 0,
            "integration_worker_errors_total": 0,
            "integration_worker_ticks_total": 0,
            "integration_retries_scheduled_total": 0,
        }

    def increment(self, key: str) -> None:
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + 1

    def increment_by(self, key: str, amount: int) -> None:
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + amount

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counters)

    def uptime_seconds(self) -> int:
        return int((datetime.now(UTC) - self.started_at).total_seconds())


def prometheus_metrics(
    *,
    stats: RuntimeStats,
    app_version: str,
    git_sha: str,
    deploy_environment: str,
    storage: str,
) -> str:
    counters = stats.snapshot()
    lines = [
        "# HELP aiops_runtime_info Runtime build and storage metadata.",
        "# TYPE aiops_runtime_info gauge",
        (
            'aiops_runtime_info{'
            f'version="{app_version}",'
            f'git_sha="{git_sha}",'
            f'environment="{deploy_environment}",'
            f'storage="{storage}"'
            "} 1"
        ),
        "# HELP aiops_uptime_seconds Runtime uptime in seconds.",
        "# TYPE aiops_uptime_seconds gauge",
        f"aiops_uptime_seconds {stats.uptime_seconds()}",
    ]
    for key in sorted(counters):
        metric_name = f"aiops_{key}"
        lines.extend(
            [
                f"# HELP {metric_name} AI Ops workflow counter.",
                f"# TYPE {metric_name} counter",
                f"{metric_name} {counters[key]}",
            ]
        )
    return "\n".join(lines) + "\n"
