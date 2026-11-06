import io
import tarfile

import pytest

from app.archive_policy import SnapshotArchiveError, validate_snapshot_archive


def make_archive(name: str = "src/text_utils.py", content: bytes = b"print('synthetic')\n", kind: bytes = tarfile.REGTYPE) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        member = tarfile.TarInfo(name)
        member.type = kind
        if kind == tarfile.REGTYPE:
            member.size = len(content)
            archive.addfile(member, io.BytesIO(content))
        else:
            member.linkname = "../../outside"
            archive.addfile(member)
    return buffer.getvalue()


def test_accepts_regular_workspace_file() -> None:
    validate_snapshot_archive(make_archive())


@pytest.mark.parametrize("name", ["../outside", "/etc/passwd", r"src\\..\\outside"])
def test_rejects_archive_path_escape(name: str) -> None:
    with pytest.raises(SnapshotArchiveError, match="outside the workspace"):
        validate_snapshot_archive(make_archive(name))


def test_rejects_symbolic_links() -> None:
    with pytest.raises(SnapshotArchiveError, match="unsupported file type"):
        validate_snapshot_archive(make_archive("src/link", kind=tarfile.SYMTYPE))


def test_rejects_non_tar_payload() -> None:
    with pytest.raises(SnapshotArchiveError, match="invalid"):
        validate_snapshot_archive(b"not a tar archive")
