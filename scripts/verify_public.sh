#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
DEMO_OUTPUT="${DEMO_OUTPUT:-/tmp/aiops-offer-demo.json}"

"$PYTHON_BIN" -m pytest -q
"$PYTHON_BIN" scripts/run_offer_demo.py > "$DEMO_OUTPUT"

"$PYTHON_BIN" - "$DEMO_OUTPUT" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

assert payload["runtime"]["ok"] is True
assert payload["runtime"]["storage"] == "memory"
assert payload["ingestion"]["chunks"] >= 1
assert payload["rag_context_sources"], "RAG retrieval returned no sources"
assert payload["call_analysis"]["score"] >= 80
assert payload["approval"]["status"] == "approved"
assert payload["crm_handoff"]["adapter_key"] == "bitrix24.mock"
assert payload["crm_handoff"]["operation"] == "upsert_lead_follow_up"
assert payload["crm_handoff"]["status"] == "queued"

print("public verification passed")
PY
