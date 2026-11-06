import io
import tarfile

import app.main as runner


class FakeVolume:
    name = "snapshot-volume"

    def __init__(self) -> None:
        self.removed = False

    def remove(self, force: bool = False) -> None:
        self.removed = True


class FakeContainer:
    def __init__(self, command: list[str], options: dict[str, object]) -> None:
        self.command = command
        self.options = options
        self.status = "created"
        self.attrs = {"State": {"ExitCode": 137}}
        self.killed = False
        self.removed = False

    def start(self) -> None:
        self.status = "running"

    def put_archive(self, path: str, archive: bytes) -> bool:
        return path == "/workspace" and bool(archive)

    def reload(self) -> None:
        if self.killed:
            self.status = "exited"

    def kill(self) -> None:
        self.killed = True

    def wait(self, timeout: int) -> dict[str, int]:
        return {"StatusCode": 137}

    def logs(self, stdout: bool, stderr: bool) -> bytes:
        return b""

    def remove(self, force: bool = False) -> None:
        self.removed = True


class FakeContainerCollection:
    def __init__(self) -> None:
        self.created: list[FakeContainer] = []

    def create(self, image: str, command: list[str], **options: object) -> FakeContainer:
        container = FakeContainer(command, options)
        self.created.append(container)
        return container


class FakeClient:
    def __init__(self) -> None:
        self.containers = FakeContainerCollection()
        self.volume = FakeVolume()
        self.volumes = self
        self.closed = False

    def create(self, name: str, labels: dict[str, str]) -> FakeVolume:
        return self.volume

    def close(self) -> None:
        self.closed = True


def make_archive() -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        member = tarfile.TarInfo("tests/test_sample.py")
        content = b"def test_sample():\n    assert True\n"
        member.size = len(content)
        archive.addfile(member, io.BytesIO(content))
    return buffer.getvalue()


def test_timeout_kills_ephemeral_container_with_isolation_limits(monkeypatch) -> None:
    client = FakeClient()
    monkeypatch.setattr(runner.docker, "from_env", lambda timeout: client)
    monkeypatch.setattr(runner, "SANDBOX_TIMEOUT_SECONDS", 0.01)

    result = runner.execute_snapshot(make_archive(), run_id=7)

    uploader, test_container = client.containers.created
    options = test_container.options
    assert result["timed_out"] is True
    assert result["exit_code"] is None
    assert test_container.killed and test_container.removed
    assert uploader.removed
    assert client.volume.removed and client.closed
    assert options["network_mode"] == "none"
    assert options["read_only"] is True
    assert options["user"] == "65532:65532"
    assert options["cap_drop"] == ["ALL"]
    assert options["security_opt"] == ["no-new-privileges:true"]
    assert options["mem_limit"] == "256m"
    assert options["nano_cpus"] == 500_000_000
    assert options["pids_limit"] == 64
    assert options["volumes"]["snapshot-volume"]["mode"] == "ro"
