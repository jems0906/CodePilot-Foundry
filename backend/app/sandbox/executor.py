from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from app.sandbox.env_filter import filtered_environment, redact_text, secret_environment_values
from app.sandbox.policy import CommandPolicy


@dataclass(frozen=True)
class ExecutionResult:
    command: tuple[str, ...]
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool
    sandbox_policy: dict[str, object] | None = None


class SandboxExecutor:
    def __init__(self, timeout_seconds: float = 20.0, policy: CommandPolicy | None = None):
        self.timeout_seconds = timeout_seconds
        self.policy = policy or CommandPolicy()

    def execute(
        self,
        command: Sequence[str],
        workspace: Path,
        cwd: Path | None = None,
        secrets: Mapping[str, str] | None = None,
    ) -> ExecutionResult:
        validated = self.policy.validate(command, workspace)
        working_directory = self.policy.resolve_working_directory(workspace, cwd)
        executable = shutil.which(validated.binary)
        if executable is None:
            raise FileNotFoundError(f"Allowlisted executable is not installed: {validated.binary}")

        safe_command = (executable, *validated.arguments)
        secret_values = secrets if secrets is not None else secret_environment_values(os.environ)
        try:
            completed = subprocess.run(
                safe_command,
                cwd=working_directory,
                env=filtered_environment(os.environ),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
                shell=False,
                check=False,
            )
            stdout, stderr = completed.stdout, completed.stderr
            return_code, timed_out = completed.returncode, False
        except subprocess.TimeoutExpired as error:
            stdout = error.stdout.decode("utf-8", "replace") if isinstance(error.stdout, bytes) else (error.stdout or "")
            stderr = error.stderr.decode("utf-8", "replace") if isinstance(error.stderr, bytes) else (error.stderr or "")
            return_code, timed_out = None, True

        return ExecutionResult(
            command=(validated.binary, *validated.arguments),
            exit_code=return_code,
            stdout=redact_text(stdout, secret_values),
            stderr=redact_text(stderr, secret_values),
            timed_out=timed_out,
        )
