from __future__ import annotations

from fastapi import APIRouter, Request

from app.database import connect
from app.schemas import TaskCreate

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("")
def list_tasks(request: Request) -> list[dict[str, object]]:
    with connect(request.app.state.settings.database_path) as connection:
        rows = connection.execute("SELECT * FROM tasks ORDER BY id DESC").fetchall()
    return [dict(row) for row in rows]


@router.post("", status_code=201)
def create_task(payload: TaskCreate, request: Request) -> dict[str, object]:
    with connect(request.app.state.settings.database_path) as connection:
        cursor = connection.execute(
            "INSERT INTO tasks(title, description) VALUES (?, ?) RETURNING id", (payload.title.strip(), payload.description.strip())
        )
        row = connection.execute("SELECT * FROM tasks WHERE id = ?", (cursor.fetchone()["id"],)).fetchone()
    return dict(row)
