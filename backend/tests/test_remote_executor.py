import io
import tarfile
from pathlib import Path

import httpx

from app.sandbox.remote_executor import RemoteSandboxExecutor


def test_remote_executor_uploads_snapshot_and_parses_runner_result(tmp_path: Path) -> None:
    source = tmp_path / "src" / "text_utils.py"
    source.parent.mkdir()
    source.write_text("value = 'synthetic'\n", encoding="utf-8")
    (tmp_path / "src" / "__pycache__").mkdir()
    (tmp_path / "src" / "__pycache__" / "ignored.pyc").write_bytes(b"not included")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/execute"
        assert request.headers["x-run-id"] == "41"
        with tarfile.open(fileobj=io.BytesIO(request.content), mode="r:gz") as archive:
            assert archive.getnames() == ["src/text_utils.py"]
        return httpx.Response(200, json={
            "exit_code": 0,
            "stdout": "3 passed",
            "stderr": "",
            "timed_out": False,
            "sandbox_policy": {"containerized": True, "network_mode": "none"},
        })

    executor = RemoteSandboxExecutor(
        "http://sandbox-runner:9000", transport=httpx.MockTransport(handler)
    )
    result = executor.execute(tmp_path, run_id=41)
    assert result.command == ("pytest", "-q", "tests")
    assert result.exit_code == 0
    assert result.stdout == "3 passed"
    assert not result.timed_out
    assert result.sandbox_policy == {"containerized": True, "network_mode": "none"}
