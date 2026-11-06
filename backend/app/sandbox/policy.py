from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


class SandboxPolicyError(ValueError):
    pass


@dataclass(frozen=True)
class ValidatedCommand:
    binary: str
    arguments: tuple[str, ...]


class CommandPolicy:
    ALLOWED_BINARIES = frozenset({"pytest", "ruff", "node", "git"})
    _SAFE_GIT_COMMANDS = frozenset({"status", "diff"})

    def validate(self, command: Sequence[str], workspace: Path) -> ValidatedCommand:
        if not command or not all(isinstance(part, str) and part for part in command):
            raise SandboxPolicyError("Command must contain a binary and non-empty string arguments")

        binary = Path(command[0].replace("\\", "/")).name.lower()
        if binary.endswith(".exe"):
            binary = binary[:-4]
        if binary not in self.ALLOWED_BINARIES:
            raise SandboxPolicyError(f"Binary is not allowlisted: {binary}")

        arguments = tuple(command[1:])
        for argument in arguments:
            if "\x00" in argument or re.search(r"(^|[/\\])\.\.($|[/\\])", argument):
                raise SandboxPolicyError("Path traversal and null bytes are not allowed")
            if Path(argument).is_absolute() or re.match(r"^[A-Za-z]:", argument):
                raise SandboxPolicyError("Absolute paths are not allowed in command arguments")

        if binary == "git" and (not arguments or arguments[0] not in self._SAFE_GIT_COMMANDS):
            raise SandboxPolicyError("Only git status and git diff are allowed")
        if binary == "node" and (not arguments or arguments[0].startswith("-")):
            raise SandboxPolicyError("node must run a script inside the workspace")
        if binary == "ruff" and (not arguments or arguments[0] != "check"):
            raise SandboxPolicyError("Only ruff check is allowed")

        root = workspace.resolve(strict=True)
        if not root.is_dir():
            raise SandboxPolicyError("Workspace must be a directory")
        return ValidatedCommand(binary=binary, arguments=arguments)

    @staticmethod
    def resolve_working_directory(workspace: Path, requested: Path | None = None) -> Path:
        root = workspace.resolve(strict=True)
        candidate = (requested or root).resolve(strict=True)
        if os.path.commonpath((str(root), str(candidate))) != str(root) or not candidate.is_dir():
            raise SandboxPolicyError("Working directory must be inside the workspace")
        return candidate
