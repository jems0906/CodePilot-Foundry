from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class CodeChange:
    path: str
    content: str


class AgentProvider(Protocol):
    def generate_plan(self, task: str) -> list[str]: ...

    def propose_code_change(self, task: str, plan: list[str], files: dict[str, str]) -> CodeChange: ...

    def self_review(self, diff: str, test_result: dict[str, object]) -> str: ...
