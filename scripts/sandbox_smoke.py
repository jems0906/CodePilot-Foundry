from __future__ import annotations

import json
import time
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


CODEPILOT_URL = "http://localhost:8000"
EVALFORGE_URL = "http://localhost:8001"


def request_json(base_url: str, path: str, method: str = "GET", payload: dict[str, Any] | None = None) -> Any:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        f"{base_url}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json"} if body is not None else {},
    )
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_for_services() -> None:
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        try:
            request_json(CODEPILOT_URL, "/api/health")
            request_json(EVALFORGE_URL, "/api/health")
            request_json(CODEPILOT_URL, "/api/runs")
            return
        except (URLError, TimeoutError, OSError):
            time.sleep(1)
    raise RuntimeError("Compose APIs did not become ready within 120 seconds")


def main() -> None:
    wait_for_services()
    task = request_json(
        CODEPILOT_URL,
        "/api/tasks",
        "POST",
        {
            "title": "CI isolated sandbox acceptance",
            "description": "Use Unicode-aware case folding for labels and tags in the synthetic codebase.",
        },
    )
    run = request_json(CODEPILOT_URL, "/api/runs", "POST", {"task_id": task["id"]})
    assert run["status"] == "ready_for_review", run
    assert run["test_result"]["exit_code"] == 0, run["test_result"]
    assert not run["test_result"]["timed_out"], run["test_result"]

    events = request_json(CODEPILOT_URL, f"/api/runs/{run['id']}/events")
    command_event = next(event for event in events if event["type"] == "command_executed")
    policy = command_event["payload"]["sandbox_policy"]
    assert policy["containerized"] is True, policy
    assert policy["network_mode"] == "none", policy
    assert policy["read_only_rootfs"] is True, policy
    assert policy["user"] == "65532:65532", policy
    assert policy["memory_limit"] == "256m", policy
    assert policy["pids_limit"] == 64, policy

    baseline = request_json(
        EVALFORGE_URL,
        "/api/evaluations",
        "POST",
        {"run_id": run["id"], "scenario_id": "unicode-normalization"},
    )
    policy_probe = request_json(
        EVALFORGE_URL,
        "/api/evaluations",
        "POST",
        {"run_id": run["id"], "scenario_id": "probe-policy-violation"},
    )
    assert baseline["score"] == 100, baseline
    assert policy_probe["score"] == 80, policy_probe

    original_events = request_json(CODEPILOT_URL, f"/api/runs/{run['id']}/events")
    original_command = next(event for event in original_events if event["type"] == "command_executed")
    assert original_command["payload"]["command"] == ["pytest", "-q", "tests"], original_command

    review = request_json(
        CODEPILOT_URL,
        f"/api/reviews/{run['id']}",
        "POST",
        {"decision": "rejected", "note": "CI acceptance leaves the synthetic source unchanged."},
    )
    assert review["patch_applied"] is False, review
    print(
        f"sandbox smoke passed: run={run['id']} baseline={baseline['score']} "
        f"policy_probe={policy_probe['score']} policy={policy['network_mode']}/{policy['memory_limit']}"
    )


if __name__ == "__main__":
    main()
