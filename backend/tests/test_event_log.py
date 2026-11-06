import sqlite3
from pathlib import Path

import pytest

from app.database import connect, initialize_database
from app.recorder.event_log import EventLog


def test_event_log_is_ordered_and_immutable(tmp_path: Path) -> None:
    database_path = tmp_path / "foundry.sqlite3"
    initialize_database(database_path)
    with connect(database_path) as connection:
        task_id = connection.execute("INSERT INTO tasks(title, description) VALUES ('test', 'test task') RETURNING id").fetchone()["id"]
        run_id = connection.execute(
            "INSERT INTO agent_runs(task_id, provider, status) VALUES (?, 'mock', 'running') RETURNING id", (task_id,)
        ).fetchone()["id"]

    event_log = EventLog(database_path)
    first_id = event_log.append(run_id, "task_started", {"task_id": task_id})
    second_id = event_log.append(run_id, "plan_created", {"step": "inspect"})
    events = event_log.list_for_run(run_id)
    assert [event["id"] for event in events] == [first_id, second_id]
    assert [event["type"] for event in events] == ["task_started", "plan_created"]

    with connect(database_path) as connection:
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute("UPDATE events SET event_type = 'rewritten' WHERE id = ?", (first_id,))
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute("DELETE FROM events WHERE id = ?", (first_id,))
