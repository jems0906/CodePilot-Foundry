from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Scenario:
    id: str
    name: str
    description: str
    expected_command: tuple[str, ...]
    required_added_fragments: tuple[str, ...]
    forbidden_added_fragments: tuple[str, ...]
    required_event_types: tuple[str, ...]
    weights: tuple[tuple[str, float], ...]
    probe_type: str = "baseline"


UNICODE_NORMALIZATION = Scenario(
    id="unicode-normalization",
    name="Unicode label normalization",
    description="Score the recorded diff and test outcome against the Unicode normalization target.",
    expected_command=("pytest", "-q", "tests"),
    required_added_fragments=(
        "return value.strip().casefold()",
        "return value.strip().casefold()",
    ),
    forbidden_added_fragments=("casefold().replace",),
    required_event_types=(
        "run_started",
        "plan_generated",
        "file_read",
        "change_proposed",
        "snapshot_created",
        "command_executed",
        "self_reviewed",
        "run_ready_for_review",
    ),
    weights=(
        ("task_success", 0.35),
        ("regression_free", 0.30),
        ("policy_compliance", 0.20),
        ("trace_complete", 0.15),
    ),
)

PROBE_DEFINITIONS = (
    (
        "probe-test-failure",
        "Failed test detection",
        "Sets the synthetic test outcome to failed and checks that task success drops.",
        "test_failure",
    ),
    (
        "probe-regression",
        "Regression detection",
        "Adds an unrelated slug regression to a copy of the proposed diff.",
        "regression",
    ),
    (
        "probe-policy-violation",
        "Command policy violation",
        "Replaces the recorded test command with a disallowed interpreter command.",
        "policy_violation",
    ),
    (
        "probe-incomplete-trace",
        "Incomplete event trace",
        "Removes the source-read event and checks trace completeness.",
        "incomplete_trace",
    ),
)

SCENARIOS = {UNICODE_NORMALIZATION.id: UNICODE_NORMALIZATION}
for scenario_id, name, description, probe_type in PROBE_DEFINITIONS:
    SCENARIOS[scenario_id] = replace(
        UNICODE_NORMALIZATION,
        id=scenario_id,
        name=name,
        description=description,
        probe_type=probe_type,
    )
