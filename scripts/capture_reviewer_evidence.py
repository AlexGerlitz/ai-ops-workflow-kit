#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from reviewer_snapshot import build_snapshot, format_text


DEFAULT_BASE_URL = "https://saleops.duckdns.org"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "evidence"
IDEMPOTENCY_PLACEHOLDER = "<generated-idempotency-key>"


def redacted_snapshot(snapshot: dict[str, Any], command: str) -> dict[str, Any]:
    redacted = json.loads(json.dumps(snapshot))
    redacted["evidence_schema"] = "reviewer_live_snapshot_v1"
    redacted["capture_command"] = command
    redacted["sanitized"] = True
    redacted["dynamic_fields_redacted"] = ["workflow.crm_idempotency_key"]
    redacted["workflow"]["crm_idempotency_key"] = IDEMPOTENCY_PLACEHOLDER
    return redacted


def output_paths(output_dir: Path) -> tuple[Path, Path]:
    return (
        output_dir / "reviewer-snapshot.sanitized.json",
        output_dir / "reviewer-snapshot.txt",
    )


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture a sanitized reviewer evidence pack from the live API."
    )
    parser.add_argument(
        "base_url",
        nargs="?",
        default=None,
        help=f"API base URL to verify, defaults to {DEFAULT_BASE_URL}.",
    )
    parser.add_argument(
        "--base-url",
        dest="base_url_option",
        default=None,
        help="API base URL to verify. Overrides the optional positional value.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for generated evidence artifacts.",
    )
    parser.add_argument("--timeout", type=float, default=15.0, help="HTTP timeout in seconds.")
    args = parser.parse_args()

    base_url = args.base_url_option or args.base_url or DEFAULT_BASE_URL
    output_dir = Path(args.output_dir)
    command = f"python3 scripts/capture_reviewer_evidence.py --base-url {base_url}"

    snapshot = build_snapshot(base_url, args.timeout)
    redacted = redacted_snapshot(snapshot, command)

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path, text_path = output_paths(output_dir)
    json_path.write_text(json.dumps(redacted, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    text_path.write_text(format_text(redacted) + "\n", encoding="utf-8")

    print("reviewer evidence captured")
    print(f"base_url={redacted['base_url']}")
    print(f"json={display_path(json_path)}")
    print(f"text={display_path(text_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
