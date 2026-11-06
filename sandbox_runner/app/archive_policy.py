from __future__ import annotations

import io
import tarfile
from pathlib import PurePosixPath


MAX_ARCHIVE_BYTES = 8 * 1024 * 1024
MAX_UNPACKED_BYTES = 24 * 1024 * 1024
MAX_ARCHIVE_FILES = 1000


class SnapshotArchiveError(ValueError):
    pass


def validate_snapshot_archive(data: bytes) -> None:
    if not data or len(data) > MAX_ARCHIVE_BYTES:
        raise SnapshotArchiveError("Snapshot archive is empty or exceeds the upload limit")
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as archive:
            members = archive.getmembers()
    except (tarfile.TarError, OSError) as error:
        raise SnapshotArchiveError("Snapshot archive is invalid") from error

    if not members or len(members) > MAX_ARCHIVE_FILES:
        raise SnapshotArchiveError("Snapshot archive has an invalid file count")
    total_size = 0
    for member in members:
        normalized_name = member.name.replace("\\", "/")
        member_path = PurePosixPath(normalized_name)
        if member_path.is_absolute() or ".." in member_path.parts:
            raise SnapshotArchiveError("Snapshot archive contains a path outside the workspace")
        if member.issym() or member.islnk() or member.isdev() or not (member.isfile() or member.isdir()):
            raise SnapshotArchiveError("Snapshot archive contains an unsupported file type")
        total_size += member.size
    if total_size > MAX_UNPACKED_BYTES:
        raise SnapshotArchiveError("Snapshot archive expands beyond the workspace limit")
