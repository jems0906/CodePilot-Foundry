from __future__ import annotations

import json
from typing import Any

from app.database import connect
from pathlib import Path


class EventLog:
    def __init__(self, database_path: Path):
        self.database_path = database_path

    def append(self, run_id: int, event_type: str, payload: dict[str, Any]) -> int:
        with connect(self.database_path) as connection:
            cursor = connection.execute(
                "INSERT INTO events(run_id, event_type, payload_json) VALUES (?, ?, ?) RETURNING id",
                (run_id, event_type, json.dumps(payload, sort_keys=True)),
            )
            return int(cursor.fetchone()["id"])

    def list_for_run(self, run_id: int) -> list[dict[str, Any]]:
        with connect(self.database_path) as connection:
            rows = connection.execute(
                "SELECT id, event_type, payload_json, created_at FROM events WHERE run_id = ? ORDER BY id",
                (run_id,),
            ).fetchall()
        return [
            {"id": row["id"], "type": row["event_type"], "payload": json.loads(row["payload_json"]), "created_at": row["created_at"]}
            for row in rows
        ]
