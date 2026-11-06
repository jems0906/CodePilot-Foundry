import json
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.scenarios import UNICODE_NORMALIZATION


def codepilot_response(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/api/runs/12":
        return httpx.Response(200, json={
            "id": 12,
            "status": "ready_for_review",
            "diff": """--- a/src/text_utils.py
+++ b/src/text_utils.py
+ return value.strip().casefold()
+ return value.strip().casefold()
""",
            "test_result": {"exit_code": 0, "timed_out": False},
        })
    if request.url.path == "/api/runs/12/events":
        events = [
            {"id": index, "type": event_type, "created_at": f"2026-11-06T10:00:0{index}.000Z", "payload": {}}
            for index, event_type in enumerate(UNICODE_NORMALIZATION.required_event_types)
        ]
        events[5]["payload"] = {
            "command": list(UNICODE_NORMALIZATION.expected_command), "exit_code": 0, "timed_out": False
        }
        return httpx.Response(200, json=events)
    if request.url.path == "/api/runs":
        return httpx.Response(200, json=[{"id": 12, "status": "ready_for_review", "provider": "mock"}])
    return httpx.Response(404)


def test_api_ingests_run_and_returns_metrics(tmp_path: Path) -> None:
    config = Settings(codepilot_api_url="http://codepilot", database_path=tmp_path / "evalforge.sqlite3")
    transport = httpx.MockTransport(codepilot_response)
    with TestClient(create_app(config, transport)) as client:
        scenarios = client.get("/api/scenarios").json()
        assert len(scenarios) == 5
        assert {scenario["probe_type"] for scenario in scenarios} == {
            "baseline", "test_failure", "regression", "policy_violation", "incomplete_trace"
        }
        source_runs = client.get("/api/source-runs")
        assert source_runs.json()[0]["id"] == 12

        response = client.post("/api/evaluations", json={"run_id": 12})
        assert response.status_code == 201
        result = response.json()
        assert result["score"] == 100
        assert result["runtime_ms"] == 7000

        repeated = client.post("/api/evaluations", json={"run_id": 12})
        assert repeated.json()["id"] == result["id"]
        probe = client.post("/api/evaluations", json={"run_id": 12, "scenario_id": "probe-policy-violation"})
        assert probe.json()["score"] == 80
        assert not probe.json()["checks"]["policy_compliance"]["passed"]
        source_events = client.get("/api/source-runs").json()
        assert source_events[0]["id"] == 12
        metrics = client.get("/api/metrics").json()
        assert metrics["evaluations"] == 2
        assert metrics["average_score"] == 90
        assert metrics["pass_rate"] == 50
