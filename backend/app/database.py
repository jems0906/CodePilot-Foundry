from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE TABLE IF NOT EXISTS agent_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL REFERENCES tasks(id),
    provider TEXT NOT NULL,
    status TEXT NOT NULL,
    plan_json TEXT NOT NULL DEFAULT '[]',
    diff TEXT NOT NULL DEFAULT '',
    self_review TEXT NOT NULL DEFAULT '',
    test_result_json TEXT NOT NULL DEFAULT '{}',
    change_path TEXT NOT NULL DEFAULT '',
    original_content TEXT NOT NULL DEFAULT '',
    proposed_content TEXT NOT NULL DEFAULT '',
    original_hash TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE TABLE IF NOT EXISTS code_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL UNIQUE REFERENCES agent_runs(id),
    path TEXT NOT NULL,
    original_hash TEXT NOT NULL,
    original_content TEXT NOT NULL,
    proposed_content TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL UNIQUE REFERENCES agent_runs(id),
    decision TEXT NOT NULL CHECK(decision IN ('approved', 'rejected')),
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES agent_runs(id),
    event_type TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events
BEGIN SELECT RAISE(ABORT, 'events are immutable'); END;
CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events
BEGIN SELECT RAISE(ABORT, 'events are immutable'); END;
"""


POSTGRES_SCHEMA = (
    """CREATE TABLE IF NOT EXISTS tasks (
        id BIGSERIAL PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'queued', created_at TEXT NOT NULL DEFAULT
        to_char(clock_timestamp() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"'))""",
    """CREATE TABLE IF NOT EXISTS agent_runs (
        id BIGSERIAL PRIMARY KEY, task_id BIGINT NOT NULL REFERENCES tasks(id), provider TEXT NOT NULL,
        status TEXT NOT NULL, plan_json TEXT NOT NULL DEFAULT '[]', diff TEXT NOT NULL DEFAULT '',
        self_review TEXT NOT NULL DEFAULT '', test_result_json TEXT NOT NULL DEFAULT '{}',
        change_path TEXT NOT NULL DEFAULT '', original_content TEXT NOT NULL DEFAULT '',
        proposed_content TEXT NOT NULL DEFAULT '', original_hash TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT to_char(clock_timestamp() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"'))""",
    """CREATE TABLE IF NOT EXISTS code_snapshots (
        id BIGSERIAL PRIMARY KEY, run_id BIGINT NOT NULL UNIQUE REFERENCES agent_runs(id), path TEXT NOT NULL,
        original_hash TEXT NOT NULL, original_content TEXT NOT NULL, proposed_content TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS reviews (
        id BIGSERIAL PRIMARY KEY, run_id BIGINT NOT NULL UNIQUE REFERENCES agent_runs(id),
        decision TEXT NOT NULL CHECK(decision IN ('approved', 'rejected')), note TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL DEFAULT to_char(clock_timestamp() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"'))""",
    """CREATE TABLE IF NOT EXISTS events (
        id BIGSERIAL PRIMARY KEY, run_id BIGINT NOT NULL REFERENCES agent_runs(id), event_type TEXT NOT NULL,
        payload_json TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT to_char(clock_timestamp() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"'))""",
    """CREATE OR REPLACE FUNCTION prevent_event_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'events are immutable'; END; $$""",
    "DROP TRIGGER IF EXISTS events_no_update ON events",
    "CREATE TRIGGER events_no_update BEFORE UPDATE ON events FOR EACH ROW EXECUTE FUNCTION prevent_event_mutation()",
    "DROP TRIGGER IF EXISTS events_no_delete ON events",
    "CREATE TRIGGER events_no_delete BEFORE DELETE ON events FOR EACH ROW EXECUTE FUNCTION prevent_event_mutation()",
)


class PostgresConnection:
    def __init__(self, database_url: str):
        import psycopg
        from psycopg.rows import dict_row

        self.connection = psycopg.connect(database_url, row_factory=dict_row)

    def __enter__(self) -> PostgresConnection:
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        try:
            if exc_type is None:
                self.connection.commit()
            else:
                self.connection.rollback()
        finally:
            self.connection.close()

    def execute(self, query: str, parameters: tuple[Any, ...] = ()) -> Any:
        return self.connection.execute(query.replace("?", "%s"), parameters)


def connect(database_path: Path | str) -> sqlite3.Connection | PostgresConnection:
    if isinstance(database_path, str) and database_path.startswith(("postgres://", "postgresql://")):
        return PostgresConnection(database_path)
    database_path = Path(database_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(database_path: Path | str) -> None:
    if isinstance(database_path, str) and database_path.startswith(("postgres://", "postgresql://")):
        with connect(database_path) as connection:
            for statement in POSTGRES_SCHEMA:
                connection.execute(statement)
        return
    with connect(database_path) as connection:
        connection.executescript(SCHEMA)
