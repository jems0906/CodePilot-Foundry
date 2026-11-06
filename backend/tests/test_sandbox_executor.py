from pathlib import Path

from app.sandbox.env_filter import filtered_environment, redact_text
from app.sandbox.executor import SandboxExecutor


def test_environment_filter_excludes_secrets() -> None:
    assert filtered_environment({"PATH": "safe", "API_TOKEN": "fake-secret"}) == {"PATH": "safe"}


def test_captured_output_redacts_planted_secret(tmp_path: Path) -> None:
    script = tmp_path / "print_secret.js"
    script.write_text('process.stdout.write("fake-secret-123")', encoding="utf-8")
    result = SandboxExecutor().execute(
        ["node", script.name],
        workspace=tmp_path,
        secrets={"API_TOKEN": "fake-secret-123"},
    )
    assert result.exit_code == 0
    assert result.stdout == "[REDACTED]"


def test_timeout_is_reported(tmp_path: Path) -> None:
    script = tmp_path / "slow.js"
    script.write_text("while (true) {}", encoding="utf-8")
    result = SandboxExecutor(timeout_seconds=0.1).execute(["node", script.name], workspace=tmp_path)
    assert result.timed_out
    assert result.exit_code is None


def test_named_credentials_in_output_are_redacted() -> None:
    assert redact_text("API_KEY=abc123", {}) == "API_KEY=[REDACTED]"
