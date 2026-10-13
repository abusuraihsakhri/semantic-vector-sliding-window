"""Integration tests for the non-browser demonstration API."""
from fastapi.testclient import TestClient

from agents.api import app


def test_health_metrics_and_private_audit_logs(monkeypatch):
    client = TestClient(app)
    assert client.get("/health").status_code == 200
    assert client.get("/api/audit/logs").status_code == 403
    monkeypatch.setenv("AUDIT_ACCESS_TOKEN", "test-audit-token")
    assert client.get("/api/audit/logs", headers={"x-audit-token": "incorrect"}).status_code == 403

    resp = client.post("/api/audit", json={
        "task_id": "API-TEST", "target_identifier": "KEY-TEST",
        "primary_metric": 10, "secondary_metric": 2, "status_descriptor": "NOMINAL",
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["overall_urgency"] == "ROUTINE"
    assert client.get("/api/audit/logs", headers={"x-audit-token": "test-audit-token"}).json()["verified"] is True

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "system_tasks_total" in metrics.text
    assert "text/plain" in metrics.headers["content-type"]


def test_api_rejects_recognized_identifiers_without_leaking_patterns():
    client = TestClient(app)
    resp = client.post("/api/audit", json={
        "task_id": "Patient MRN-123456", "target_identifier": "KEY-TEST",
        "primary_metric": 1,
    })
    assert resp.status_code == 422
    assert "pattern" not in resp.text.lower()


def test_api_rejects_nonfinite_metrics():
    client = TestClient(app)
    response = client.post("/api/audit", json={
        "task_id": "FINITE-TEST", "target_identifier": "KEY-TEST",
        "primary_metric": "NaN",
    })
    assert response.status_code == 422
