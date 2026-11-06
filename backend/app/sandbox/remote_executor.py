from __future__ import annotations

import io
import os
import tarfile
from pathlib import Path
from typing import Any

import httpx

from app.sandbox.env_filter import redact_text, secret_environment_values
from app.sandbox.executor import ExecutionResult


MAX_SNAPSHOT_BYTES = 8 * 1024 * 1024


def create_snapshot_archive(workspace: Path) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for path in workspace.rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            relative_path = path.relative_to(workspace)
            if any(part in {"__pycache__", ".pytest_cache", ".ruff_cache", ".git"} for part in relative_path.parts):
                continue
            archive.add(path, arcname=relative_path.as_posix(), recursive=False)
    payload = buffer.getvalue()
    if len(payload) > MAX_SNAPSHOT_BYTES:
        raise ValueError("Synthetic snapshot exceeds the sandbox upload limit")
    return payload


class RemoteSandboxExecutor:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float = 20.0,
        transport: httpx.BaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    def execute(self, workspace: Path, run_id: int) -> ExecutionResult:
        archive = create_snapshot_archive(workspace)
        timeout = httpx.Timeout(connect=5.0, read=self.timeout_seconds + 15.0, write=15.0, pool=5.0)
        with httpx.Client(base_url=self.base_url, timeout=timeout, transport=self.transport) as client:
            response = client.post(
                "/api/execute",
                content=archive,
                headers={"Content-Type": "application/x-tar", "X-Run-ID": str(run_id)},
            )
            response.raise_for_status()
        result: dict[str, Any] = response.json()
        secrets = secret_environment_values(os.environ)
        return ExecutionResult(
            command=("pytest", "-q", "tests"),
            exit_code=result.get("exit_code"),
            stdout=redact_text(str(result.get("stdout", "")), secrets),
            stderr=redact_text(str(result.get("stderr", "")), secrets),
            timed_out=bool(result.get("timed_out", False)),
            sandbox_policy=result.get("sandbox_policy"),
        )
