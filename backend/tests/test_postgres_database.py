import os
import uuid

import pytest

from app.database import connect, initialize_database
from app.recorder.event_log import EventLog


def test_postgres_records_ordered_immutable_events() -> None:
    database_url = os.getenv("POSTGRES_TEST_URL")
    if not database_url:
        pytest.skip("POSTGRES_TEST_URL is not configured")
    initialize_database(database_url)
    with connect(database_url) as connection:
        task_id = connection.execute(
            "INSERT INTO tasks(title, description) VALUES (?, ?) RETURNING id",
            (f"postgres-{uuid.uuid4()}", "test PostgreSQL persistence"),
        ).fetchone()["id"]
        run_id = connection.execute(
            "INSERT INTO agent_runs(task_id, provider, status) VALUES (?, ?, ?) RETURNING id",
            (task_id, "mock", "running"),
        ).fetchone()["id"]

    events = EventLog(database_url)
    first_id = events.append(run_id, "started", {"provider": "mock"})
    second_id = events.append(run_id, "finished", {"ok": True})
    recorded = events.list_for_run(run_id)
    assert [event["id"] for event in recorded] == [first_id, second_id]

    with connect(database_url) as connection:
        with pytest.raises(Exception, match="immutable"):
            connection.execute("UPDATE events SET event_type = ? WHERE id = ?", ("changed", first_id))
