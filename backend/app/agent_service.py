from __future__ import annotations

import difflib
import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from app.config import Settings, settings
from app.database import connect
from app.providers.base import AgentProvider, CodeChange
from app.providers.mock import MockProvider
from app.recorder.event_log import EventLog
from app.sandbox.executor import SandboxExecutor
from app.sandbox.remote_executor import RemoteSandboxExecutor


def get_provider(provider_name: str) -> AgentProvider:
    if provider_name == "mock":
        return MockProvider()
    if provider_name == "openai":
        from app.providers.openai_provider import OpenAIProvider

        return OpenAIProvider()
    raise ValueError(f"Unsupported AGENT_PROVIDER: {provider_name}")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _target_file(target_root: Path, relative_path: str) -> Path:
    candidate = (target_root / relative_path).resolve(strict=True)
    if target_root.resolve() not in candidate.parents or not candidate.is_file():
        raise ValueError("Agent changes must target an existing file inside the synthetic codebase")
    return candidate


def _run_dict(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "task_id": row["task_id"],
        "provider": row["provider"],
        "status": row["status"],
        "plan": json.loads(row["plan_json"]),
        "diff": row["diff"],
        "self_review": row["self_review"],
        "test_result": json.loads(row["test_result_json"]),
        "created_at": row["created_at"],
    }


def create_run(task_id: int, config: Settings = settings) -> dict[str, Any]:
    with connect(config.database_path) as connection:
        task = connection.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if task is None:
            raise LookupError("Task not found")
        cursor = connection.execute(
            "INSERT INTO agent_runs(task_id, provider, status) VALUES (?, ?, 'running') RETURNING id",
            (task_id, config.provider),
        )
        run_id = int(cursor.fetchone()["id"])
        connection.execute("UPDATE tasks SET status = 'running' WHERE id = ?", (task_id,))

    log = EventLog(config.database_path)
    log.append(run_id, "run_started", {"task_id": task_id, "provider": config.provider})
    try:
        provider = get_provider(config.provider)
        plan = provider.generate_plan(task["description"])
        log.append(run_id, "plan_generated", {"steps": plan})

        source = _target_file(config.target_root, "src/text_utils.py")
        original = source.read_bytes().decode("utf-8")
        original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
        log.append(run_id, "file_read", {"path": "src/text_utils.py", "content": original, "sha256": original_hash})

        change: CodeChange = provider.propose_code_change(task["description"], plan, {"src/text_utils.py": original})
        proposed_path = _target_file(config.target_root, change.path)
        if proposed_path != source:
            raise ValueError("Provider may only change src/text_utils.py in this MVP")
        diff = "".join(difflib.unified_diff(
            original.splitlines(keepends=True),
            change.content.splitlines(keepends=True),
            fromfile=f"a/{change.path}",
            tofile=f"b/{change.path}",
        ))
        log.append(run_id, "change_proposed", {"path": change.path, "diff": diff})

        log.append(run_id, "snapshot_created", {"base": "synthetic target", "changed_path": change.path})
        with tempfile.TemporaryDirectory(prefix="codepilot-run-") as temporary_directory:
            snapshot_root = Path(temporary_directory) / "target"
            shutil.copytree(config.target_root, snapshot_root)
            snapshot_file = (snapshot_root / change.path).resolve(strict=True)
            if snapshot_root.resolve() not in snapshot_file.parents:
                raise ValueError("Proposed file escaped the isolated snapshot")
            snapshot_file.write_text(change.content, encoding="utf-8")
            if config.sandbox_mode == "container":
                result = RemoteSandboxExecutor(
                    config.sandbox_runner_url, config.sandbox_timeout_seconds
                ).execute(snapshot_root, run_id)
            elif config.sandbox_mode == "local":
                result = SandboxExecutor(config.sandbox_timeout_seconds).execute(
                    ["pytest", "-q", "tests"], workspace=snapshot_root
                )
            else:
                raise RuntimeError(f"Unsupported SANDBOX_MODE: {config.sandbox_mode}")
        test_result = {
            "command": list(result.command),
            "exit_code": result.exit_code,
            "stdout": result.stdout[-12000:],
            "stderr": result.stderr[-12000:],
            "timed_out": result.timed_out,
            "sandbox_policy": result.sandbox_policy,
        }
        log.append(run_id, "command_executed", test_result)
        self_review = provider.self_review(diff, test_result)
        log.append(run_id, "self_reviewed", {"review": self_review})

        status = "ready_for_review"
        with connect(config.database_path) as connection:
            connection.execute(
                """UPDATE agent_runs SET status = ?, plan_json = ?, diff = ?, self_review = ?,
                   test_result_json = ?, change_path = ?, original_content = ?, proposed_content = ?, original_hash = ?
                   WHERE id = ?""",
                (status, json.dumps(plan), diff, self_review, json.dumps(test_result), change.path,
                 original, change.content, original_hash, run_id),
            )
            connection.execute(
                "INSERT INTO code_snapshots(run_id, path, original_hash, original_content, proposed_content) VALUES (?, ?, ?, ?, ?)",
                (run_id, change.path, original_hash, original, change.content),
            )
            row = connection.execute("SELECT * FROM agent_runs WHERE id = ?", (run_id,)).fetchone()
        log.append(run_id, "run_ready_for_review", {"status": status})
        with connect(config.database_path) as connection:
            row = connection.execute("SELECT * FROM agent_runs WHERE id = ?", (run_id,)).fetchone()
        return _run_dict(row)
    except Exception as error:
        log.append(run_id, "run_failed", {"error": str(error)[:500]})
        with connect(config.database_path) as connection:
            connection.execute("UPDATE agent_runs SET status = 'failed' WHERE id = ?", (run_id,))
            connection.execute("UPDATE tasks SET status = 'failed' WHERE id = ?", (task_id,))
        raise
