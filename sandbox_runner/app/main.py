from __future__ import annotations

import os
import time
import uuid
from typing import Any

import docker
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app.archive_policy import SnapshotArchiveError, validate_snapshot_archive


class ExecutionResponse(BaseModel):
    exit_code: int | None
    stdout: str
    stderr: str
    timed_out: bool
    sandbox_policy: dict[str, object]


SANDBOX_IMAGE = os.getenv("SANDBOX_IMAGE", "codepilot-sandbox:local")
SANDBOX_TIMEOUT_SECONDS = float(os.getenv("SANDBOX_TIMEOUT_SECONDS", "20"))
MAX_OUTPUT_CHARS = 16000
MEMORY_LIMIT = "256m"
CPU_LIMIT_NANOS = 500_000_000
PIDS_LIMIT = 64
SANDBOX_POLICY = {
    "containerized": True,
    "network_mode": "none",
    "read_only_rootfs": True,
    "workspace_mount": "read-only ephemeral volume",
    "user": "65532:65532",
    "capabilities_dropped": ["ALL"],
    "no_new_privileges": True,
    "memory_limit": MEMORY_LIMIT,
    "cpu_limit": "0.5 CPU",
    "pids_limit": PIDS_LIMIT,
    "timeout_seconds": SANDBOX_TIMEOUT_SECONDS,
}


def _text_log(container: Any, stdout: bool, stderr: bool) -> str:
    data = container.logs(stdout=stdout, stderr=stderr)
    text = data.decode("utf-8", "replace") if isinstance(data, bytes) else str(data)
    return text[-MAX_OUTPUT_CHARS:]


def execute_snapshot(archive: bytes, run_id: int) -> dict[str, object]:
    client = docker.from_env(timeout=5)
    container = None
    uploader = None
    volume = None
    timed_out = False
    try:
        volume = client.volumes.create(
            name=f"codepilot-snapshot-{run_id}-{uuid.uuid4().hex}",
            labels={"codepilot.run_id": str(run_id), "codepilot.ephemeral": "true"},
        )
        uploader = client.containers.create(
            image=SANDBOX_IMAGE,
            command=["python", "-c", "import time; time.sleep(3600)"],
            working_dir="/workspace",
            user="65532:65532",
            network_mode="none",
            cap_drop=["ALL"],
            security_opt=["no-new-privileges:true"],
            volumes={volume.name: {"bind": "/workspace", "mode": "rw"}},
            labels={"codepilot.run_id": str(run_id), "codepilot.snapshot_uploader": "true"},
            detach=True,
            stdin_open=False,
            tty=False,
        )
        uploader.start()
        if not uploader.put_archive("/workspace", archive):
            raise RuntimeError("Sandbox rejected the synthetic snapshot")
        uploader.remove(force=True)
        uploader = None

        container = client.containers.create(
            image=SANDBOX_IMAGE,
            command=["pytest", "-q", "tests", "-p", "no:cacheprovider"],
            working_dir="/workspace",
            user="65532:65532",
            network_mode="none",
            read_only=True,
            cap_drop=["ALL"],
            security_opt=["no-new-privileges:true"],
            mem_limit=MEMORY_LIMIT,
            memswap_limit=MEMORY_LIMIT,
            nano_cpus=CPU_LIMIT_NANOS,
            pids_limit=PIDS_LIMIT,
            tmpfs={"/tmp": "rw,noexec,nosuid,size=32m"},
            volumes={volume.name: {"bind": "/workspace", "mode": "ro"}},
            environment={
                "HOME": "/tmp",
                "PYTHONPATH": "/workspace",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            },
            labels={"codepilot.run_id": str(run_id), "codepilot.ephemeral": "true"},
            detach=True,
            stdin_open=False,
            tty=False,
        )
        container.start()
        deadline = time.monotonic() + SANDBOX_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            container.reload()
            if container.status == "exited":
                break
            time.sleep(0.1)
        else:
            timed_out = True
            container.kill()
            container.wait(timeout=5)
        container.reload()
        exit_code = None if timed_out else int(container.attrs["State"]["ExitCode"])
        return {
            "exit_code": exit_code,
            "stdout": _text_log(container, stdout=True, stderr=False),
            "stderr": _text_log(container, stdout=False, stderr=True),
            "timed_out": timed_out,
            "sandbox_policy": SANDBOX_POLICY,
        }
    finally:
        if container is not None:
            try:
                container.remove(force=True)
            except docker.errors.NotFound:
                pass
        if uploader is not None:
            try:
                uploader.remove(force=True)
            except docker.errors.NotFound:
                pass
        if volume is not None:
            try:
                volume.remove(force=True)
            except docker.errors.NotFound:
                pass
        client.close()


app = FastAPI(title="CodePilot Isolated Sandbox", version="0.1.0")


@app.get("/api/health")
def health() -> dict[str, str]:
    try:
        client = docker.from_env(timeout=2)
        client.ping()
        client.close()
    except docker.errors.DockerException as error:
        raise HTTPException(status_code=503, detail="Container runtime unavailable") from error
    return {"status": "ok"}


@app.post("/api/execute", response_model=ExecutionResponse)
async def execute(request: Request, x_run_id: int = Header(gt=0)) -> dict[str, object]:
    chunks = []
    total_bytes = 0
    async for chunk in request.stream():
        total_bytes += len(chunk)
        if total_bytes > 8 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Snapshot exceeds the upload limit")
        chunks.append(chunk)
    archive = b"".join(chunks)
    try:
        validate_snapshot_archive(archive)
    except SnapshotArchiveError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    try:
        return await run_in_threadpool(execute_snapshot, archive, x_run_id)
    except docker.errors.DockerException as error:
        raise HTTPException(status_code=503, detail="Isolated sandbox execution failed") from error
