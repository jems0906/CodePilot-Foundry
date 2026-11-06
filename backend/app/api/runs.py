from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.agent_service import _run_dict, create_run
from app.database import connect
from app.recorder.event_log import EventLog

router = APIRouter(prefix="/api/runs", tags=["runs"])


class RunCreate(BaseModel):
    task_id: int


@router.post("", status_code=201)
def execute_run(payload: RunCreate, request: Request) -> dict[str, object]:
    try:
        return create_run(payload.task_id, request.app.state.settings)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except (ValueError, RuntimeError, FileNotFoundError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("")
def list_runs(request: Request) -> list[dict[str, object]]:
    with connect(request.app.state.settings.database_path) as connection:
        rows = connection.execute("SELECT * FROM agent_runs ORDER BY id DESC").fetchall()
    return [_run_dict(row) for row in rows]


@router.get("/{run_id}")
def get_run(run_id: int, request: Request) -> dict[str, object]:
    with connect(request.app.state.settings.database_path) as connection:
        row = connection.execute("SELECT * FROM agent_runs WHERE id = ?", (run_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return _run_dict(row)


@router.get("/{run_id}/events")
def list_events(run_id: int, request: Request) -> list[dict[str, object]]:
    with connect(request.app.state.settings.database_path) as connection:
        exists = connection.execute("SELECT 1 FROM agent_runs WHERE id = ?", (run_id,)).fetchone()
    if not exists:
        raise HTTPException(status_code=404, detail="Run not found")
    return EventLog(request.app.state.settings.database_path).list_for_run(run_id)
