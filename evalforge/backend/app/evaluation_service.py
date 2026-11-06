from __future__ import annotations

import json
import statistics
from typing import Any

import httpx

from app.config import Settings
from app.database import connect
from app.scenarios import SCENARIOS
from app.scoring import score_run


class SourceServiceError(RuntimeError):
    pass


def fetch_run_and_events(run_id: int, config: Settings, transport: httpx.BaseTransport | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        with httpx.Client(base_url=config.codepilot_api_url, transport=transport, timeout=15) as client:
            run_response = client.get(f"/api/runs/{run_id}")
            run_response.raise_for_status()
            events_response = client.get(f"/api/runs/{run_id}/events")
            events_response.raise_for_status()
    except httpx.HTTPStatusError as error:
        if error.response.status_code == 404:
            raise LookupError(f"CodePilot run {run_id} was not found") from error
        raise SourceServiceError(f"CodePilot returned HTTP {error.response.status_code}") from error
    except httpx.HTTPError as error:
        raise SourceServiceError("Could not connect to the CodePilot API") from error
    return run_response.json(), events_response.json()


def _evaluation_record(row: sqlite3.Row) -> dict[str, Any]:
    outcome = json.loads(row["outcome_json"])
    return {
        "id": row["id"],
        "source_run_id": row["source_run_id"],
        "scenario_id": row["scenario_id"],
        "source_status": row["source_status"],
        "score": row["score"],
        "created_at": row["created_at"],
        **outcome,
    }


def evaluate_source_run(
    run_id: int,
    scenario_id: str,
    config: Settings,
    transport: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
    scenario = SCENARIOS.get(scenario_id)
    if scenario is None:
        raise LookupError(f"Unknown scenario: {scenario_id}")

    with connect(config.database_path) as connection:
        existing = connection.execute(
            "SELECT * FROM evaluations WHERE source_run_id = ? AND scenario_id = ?",
            (run_id, scenario_id),
        ).fetchone()
    if existing:
        return _evaluation_record(existing)

    run, events = fetch_run_and_events(run_id, config, transport)
    if run.get("status") in {"running", "failed"}:
        raise ValueError("Only completed CodePilot runs can be evaluated")
    outcome = score_run(run, events, scenario)
    with connect(config.database_path) as connection:
        cursor = connection.execute(
            "INSERT INTO evaluations(source_run_id, scenario_id, source_status, score, outcome_json) VALUES (?, ?, ?, ?, ?)",
            (run_id, scenario_id, run.get("status", "unknown"), outcome["score"], json.dumps(outcome, sort_keys=True)),
        )
        row = connection.execute("SELECT * FROM evaluations WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return _evaluation_record(row)


def list_evaluations(database_path) -> list[dict[str, Any]]:
    with connect(database_path) as connection:
        rows = connection.execute("SELECT * FROM evaluations ORDER BY id DESC").fetchall()
    return [_evaluation_record(row) for row in rows]


def aggregate_metrics(evaluations: list[dict[str, Any]]) -> dict[str, Any]:
    dimensions = ("task_success", "regression_free", "policy_compliance", "trace_complete")
    count = len(evaluations)
    checks = {
        name: round(100 * sum(bool(item["checks"][name]["passed"]) for item in evaluations) / count) if count else 0
        for name in dimensions
    }
    runtimes = [item["runtime_ms"] for item in evaluations if item.get("runtime_ms") is not None]
    return {
        "evaluations": count,
        "average_score": round(sum(item["score"] for item in evaluations) / count) if count else 0,
        "pass_rate": round(100 * sum(item["outcome"] == "pass" for item in evaluations) / count) if count else 0,
        "checks": checks,
        "median_runtime_ms": round(statistics.median(runtimes)) if runtimes else None,
    }
