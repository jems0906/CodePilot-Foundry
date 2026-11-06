from __future__ import annotations

from copy import deepcopy
from collections import Counter
from datetime import datetime
from typing import Any

from app.scenarios import Scenario


ALLOWED_COMMANDS = {
    "pytest": ("-q", "tests"),
    "ruff": ("check", "."),
    "node": (),
    "git": (),
}


def _timestamp(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None


def _runtime_ms(events: list[dict[str, Any]]) -> float | None:
    started = next((event for event in events if event.get("type") == "run_started"), None)
    completed = next((event for event in reversed(events) if event.get("type") in {"run_ready_for_review", "run_failed"}), None)
    if not started or not completed:
        return None
    start_time = _timestamp(started.get("created_at", ""))
    end_time = _timestamp(completed.get("created_at", ""))
    if not start_time or not end_time:
        return None
    return max(0.0, (end_time - start_time).total_seconds() * 1000)


def _policy_compliant(events: list[dict[str, Any]], expected_command: tuple[str, ...]) -> bool:
    command_events = [event for event in events if event.get("type") == "command_executed"]
    if len(command_events) != 1:
        return False
    payload = command_events[0].get("payload", {})
    command = payload.get("command", [])
    if not command or command[0] not in ALLOWED_COMMANDS:
        return False
    if tuple(command) != expected_command:
        return False
    return not payload.get("timed_out", False)


def _apply_probe(
    run: dict[str, Any],
    events: list[dict[str, Any]],
    probe_type: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    probed_run = deepcopy(run)
    probed_events = deepcopy(events)
    command_event = next((event for event in probed_events if event.get("type") == "command_executed"), None)

    if probe_type == "test_failure":
        probed_run.setdefault("test_result", {})["exit_code"] = 1
        if command_event:
            command_event.setdefault("payload", {})["exit_code"] = 1
    elif probe_type == "regression":
        probed_run["diff"] = probed_run.get("diff", "") + "+ return value.strip().casefold().replace(' ', '-')\n"
    elif probe_type == "policy_violation" and command_event:
        command_event.setdefault("payload", {})["command"] = ["python", "-c", "print(1)"]
    elif probe_type == "incomplete_trace":
        probed_events = [event for event in probed_events if event.get("type") != "file_read"]

    return probed_run, probed_events


def score_run(run: dict[str, Any], events: list[dict[str, Any]], scenario: Scenario) -> dict[str, Any]:
    run, events = _apply_probe(run, events, scenario.probe_type)
    diff_lines = run.get("diff", "").splitlines()
    added_lines = [line[1:] for line in diff_lines if line.startswith("+") and not line.startswith("+++")]
    added_text = "\n".join(added_lines)
    test_result = run.get("test_result", {})

    task_success = (
        test_result.get("exit_code") == 0
        and not test_result.get("timed_out", False)
        and all(
            added_text.count(fragment) >= required_count
            for fragment, required_count in Counter(scenario.required_added_fragments).items()
        )
    )
    regression_free = not any(fragment in added_text for fragment in scenario.forbidden_added_fragments)
    policy_compliance = _policy_compliant(events, scenario.expected_command)

    event_types = [event.get("type") for event in events]
    required_positions = []
    for event_type in scenario.required_event_types:
        try:
            required_positions.append(event_types.index(event_type))
        except ValueError:
            required_positions = []
            break
    trace_complete = bool(required_positions) and required_positions == sorted(required_positions)

    checks = {
        "task_success": task_success,
        "regression_free": regression_free,
        "policy_compliance": policy_compliance,
        "trace_complete": trace_complete,
    }
    score = round(sum(weight * 100 for name, weight in scenario.weights if checks[name]))
    runtime_ms = _runtime_ms(events)
    return {
        "scenario_id": scenario.id,
        "scenario_name": scenario.name,
        "probe_type": scenario.probe_type,
        "run_id": run.get("id"),
        "score": score,
        "outcome": "pass" if score == 100 else "needs_attention",
        "checks": {
            name: {"passed": checks[name], "weight": weight}
            for name, weight in scenario.weights
        },
        "runtime_ms": runtime_ms,
        "event_count": len(events),
    }
