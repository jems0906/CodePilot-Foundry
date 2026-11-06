from pathlib import Path

import pytest

from app.sandbox.policy import CommandPolicy, SandboxPolicyError


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    return tmp_path


def test_allows_only_named_binaries(workspace: Path) -> None:
    policy = CommandPolicy()
    assert policy.validate(["pytest", "-q"], workspace).binary == "pytest"
    with pytest.raises(SandboxPolicyError, match="not allowlisted"):
        policy.validate(["powershell", "-Command", "whoami"], workspace)


@pytest.mark.parametrize("argument", ["../outside", "src/../../outside", r"src\\..\\outside", "C:/outside"])
def test_rejects_traversal_and_absolute_arguments(workspace: Path, argument: str) -> None:
    with pytest.raises(SandboxPolicyError):
        CommandPolicy().validate(["pytest", argument], workspace)


def test_restricts_git_to_read_only_inspection(workspace: Path) -> None:
    with pytest.raises(SandboxPolicyError, match="git status and git diff"):
        CommandPolicy().validate(["git", "commit", "-am", "change"], workspace)


def test_rejects_working_directory_outside_workspace(tmp_path: Path) -> None:
    root = tmp_path / "target"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    with pytest.raises(SandboxPolicyError, match="inside the workspace"):
        CommandPolicy.resolve_working_directory(root, outside)
