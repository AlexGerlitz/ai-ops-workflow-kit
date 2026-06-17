from fastapi.testclient import TestClient

from app.main import app


def test_health_endpoint_reports_runtime() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_ingest_query_and_approval_flow() -> None:
    with TestClient(app) as client:
        ingest = client.post(
            "/documents",
            json={
                "source": "drive://playbook",
                "text": "Discovery calls should confirm budget, authority, need, timing, and next step.",
                "metadata": {"team": "sales"},
            },
        )
        assert ingest.status_code == 200
        assert ingest.json()["chunks"] == 1

        query = client.post(
            "/query",
            json={"question": "What should discovery confirm?", "top_k": 1},
        )
        assert query.status_code == 200
        assert query.json()["contexts"][0]["source"] == "drive://playbook"

        approval = client.post(
            "/approvals",
            json={
                "kind": "content_review",
                "title": "Review follow-up",
                "draft": "Send recap.",
                "context": {"lead_id": "L-1"},
            },
        )
        assert approval.status_code == 200
        approval_id = approval.json()["id"]

        approved = client.post(
            f"/approvals/{approval_id}/approve",
            json={"reviewer": "owner", "notes": "approved"},
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == "approved"

