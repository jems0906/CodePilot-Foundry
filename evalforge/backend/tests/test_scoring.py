import pytest

from app.scenarios import SCENARIOS, UNICODE_NORMALIZATION
from app.scoring import _apply_probe, score_run


def successful_run() -> tuple[dict, list[dict]]:
    run = {
        "id": 7,
        "status": "ready_for_review",
        "diff": """--- a/src/text_utils.py
+++ b/src/text_utils.py
@@ -1,3 +1,3 @@
- return value.strip().lower()
+ return value.strip().casefold()
@@ -8,3 +8,3 @@
- return value.strip().lower()
+ return value.strip().casefold()
""",
        "test_result": {"exit_code": 0, "timed_out": False},
    }
    required = UNICODE_NORMALIZATION.required_event_types
    events = [
        {"id": index, "type": event_type, "created_at": f"2026-11-06T10:00:0{index}.000Z", "payload": {}}
        for index, event_type in enumerate(required)
    ]
    events[5]["payload"] = {
        "command": list(UNICODE_NORMALIZATION.expected_command),
        "exit_code": 0,
        "timed_out": False,
    }
    return run, events


def test_perfect_run_scores_all_dimensions_and_runtime() -> None:
    run, events = successful_run()
    result = score_run(run, events, UNICODE_NORMALIZATION)
    assert result["score"] == 100
    assert result["outcome"] == "pass"
    assert result["runtime_ms"] == 7000
    assert all(check["passed"] for check in result["checks"].values())


def test_slug_regression_reduces_score() -> None:
    run, events = successful_run()
    run["diff"] += "+ return value.strip().casefold().replace(' ', '-')\n"
    result = score_run(run, events, UNICODE_NORMALIZATION)
    assert result["score"] == 70
    assert not result["checks"]["regression_free"]["passed"]


def test_missing_one_expected_normalizer_fails_task_success() -> None:
    run, events = successful_run()
    run["diff"] = run["diff"].replace("+ return value.strip().casefold()\n", "", 1)
    result = score_run(run, events, UNICODE_NORMALIZATION)
    assert not result["checks"]["task_success"]["passed"]


def test_rejected_command_and_missing_trace_are_scored() -> None:
    run, events = successful_run()
    events[5]["payload"]["command"] = ["python", "-c", "print(1)"]
    events.pop(2)
    result = score_run(run, events, UNICODE_NORMALIZATION)
    assert result["score"] == 65
    assert not result["checks"]["policy_compliance"]["passed"]
    assert not result["checks"]["trace_complete"]["passed"]


@pytest.mark.parametrize(
    ("scenario_id", "expected_score", "failed_check"),
    [
        ("probe-test-failure", 65, "task_success"),
        ("probe-regression", 70, "regression_free"),
        ("probe-policy-violation", 80, "policy_compliance"),
        ("probe-incomplete-trace", 85, "trace_complete"),
    ],
)
def test_generated_probe_scenarios_flag_expected_failure(
    scenario_id: str,
    expected_score: int,
    failed_check: str,
) -> None:
    run, events = successful_run()
    result = score_run(run, events, SCENARIOS[scenario_id])
    assert result["score"] == expected_score
    assert result["probe_type"] == SCENARIOS[scenario_id].probe_type
    assert not result["checks"][failed_check]["passed"]


def test_probe_mutations_do_not_change_source_run_or_events() -> None:
    run, events = successful_run()
    original_diff = run["diff"]
    original_command = events[5]["payload"]["command"][:]

    probed_run, probed_events = _apply_probe(run, events, "policy_violation")

    assert run["diff"] == original_diff
    assert events[5]["payload"]["command"] == original_command
    assert probed_events[5]["payload"]["command"][0] == "python"
    assert probed_run["diff"] == original_diff
