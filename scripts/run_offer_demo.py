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


def request_json(client: TestClient, method: str, path: str, **kwargs: Any) -> dict[str, Any] | list[Any]:
    response = getattr(client, method)(path, **kwargs)
    if response.status_code >= 400:
        raise SystemExit(f"{method.upper()} {path} failed: {response.status_code} {response.text}")
    return response.json()


def main() -> None:
    with TestClient(app) as client:
        result = request_json(client, "post", "/demo/run")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
