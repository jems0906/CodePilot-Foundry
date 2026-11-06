from pathlib import Path

from app.sandbox.executor import SandboxExecutor


def test_timeout_terminates_command_and_reports_result(tmp_path: Path) -> None:
    script = tmp_path / "slow.js"
    script.write_text("while (true) {}", encoding="utf-8")
    result = SandboxExecutor(timeout_seconds=0.1).execute(["node", script.name], workspace=tmp_path)
    assert result.timed_out
    assert result.exit_code is None
