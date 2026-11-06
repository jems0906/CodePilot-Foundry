from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

from app.config import Settings, settings
from app.database import connect
from app.recorder.event_log import EventLog


def submit_review(run_id: int, decision: str, note: str, config: Settings = settings) -> dict[str, object]:
    with connect(config.database_path) as connection:
        run = connection.execute("SELECT * FROM agent_runs WHERE id = ?", (run_id,)).fetchone()
        if run is None:
            raise LookupError("Run not found")
        if run["status"] != "ready_for_review":
            raise ValueError("Only completed runs can be reviewed")
        existing = connection.execute("SELECT id FROM reviews WHERE run_id = ?", (run_id,)).fetchone()
        if existing:
            raise ValueError("This run already has a review decision")

    applied = False
    if decision == "approved":
        test_result = json.loads(run["test_result_json"])
        if test_result.get("exit_code") != 0 or test_result.get("timed_out"):
            raise ValueError("A change with failed or timed-out tests cannot be approved")
        target = (config.target_root / run["change_path"]).resolve(strict=True)
        if config.target_root.resolve() not in target.parents or not target.is_file():
            raise ValueError("Snapshot path is outside the synthetic codebase")
        current_hash = hashlib.sha256(target.read_bytes()).hexdigest()
        if current_hash != run["original_hash"]:
            raise ValueError("Synthetic source changed since the agent snapshot; refusing to overwrite it")
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=target.parent, delete=False) as temporary:
            temporary.write(run["proposed_content"])
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, target)
        applied = True

    with connect(config.database_path) as connection:
        cursor = connection.execute(
            "INSERT INTO reviews(run_id, decision, note) VALUES (?, ?, ?) RETURNING id", (run_id, decision, note)
        )
        review_id = cursor.fetchone()["id"]
        connection.execute("UPDATE agent_runs SET status = ? WHERE id = ?", (decision, run_id))
        connection.execute(
            "UPDATE tasks SET status = ? WHERE id = (SELECT task_id FROM agent_runs WHERE id = ?)",
            (decision, run_id),
        )
        row = connection.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
    EventLog(config.database_path).append(run_id, "review_submitted", {"decision": decision, "note": note, "patch_applied": applied})
    return {"id": row["id"], "run_id": row["run_id"], "decision": row["decision"], "note": row["note"], "created_at": row["created_at"], "patch_applied": applied}
