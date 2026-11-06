import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import REPOSITORY_ROOT, Settings
from app.main import create_app


def test_mock_request_run_review_flow(tmp_path: Path) -> None:
    target_root = tmp_path / "target_codebase"
    shutil.copytree(REPOSITORY_ROOT / "target_codebase", target_root)
    source = target_root / "src" / "text_utils.py"
    original_bytes = source.read_bytes()
    config = Settings(
        provider="mock",
        database_path=tmp_path / "foundry.sqlite3",
        target_root=target_root,
        sandbox_timeout_seconds=10,
    )
    with TestClient(create_app(config)) as client:
        task = client.post("/api/tasks", json={"title": "Normalize Unicode", "description": "Use Unicode-aware case folding for labels and tags."})
        assert task.status_code == 201
        run = client.post("/api/runs", json={"task_id": task.json()["id"]})
        assert run.status_code == 201, run.text
        run_data = run.json()
        assert run_data["status"] == "ready_for_review"
        assert run_data["test_result"]["exit_code"] == 0, run_data["test_result"]
        assert "+    return value.strip().casefold().replace" not in run_data["diff"]

        events = client.get(f"/api/runs/{run_data['id']}/events").json()
        event_types = [event["type"] for event in events]
        assert event_types[0] == "run_started"
        assert event_types[-1] == "run_ready_for_review"
        assert {"file_read", "change_proposed", "snapshot_created", "command_executed", "self_reviewed"} <= set(event_types)

        rejected = client.post(f"/api/reviews/{run_data['id']}", json={"decision": "rejected", "note": "Keep the baseline for comparison."})
        assert rejected.status_code == 201
        assert source.read_bytes() == original_bytes

        second_task = client.post("/api/tasks", json={"title": "Fold labels", "description": "Make the synthetic label normalizer Unicode aware."}).json()
        second_run = client.post("/api/runs", json={"task_id": second_task["id"]}).json()
        approved = client.post(f"/api/reviews/{second_run['id']}", json={"decision": "approved", "note": "Tests pass."})
        assert approved.status_code == 201, approved.text
        assert approved.json()["patch_applied"] is True
        assert b"casefold()" in source.read_bytes()
