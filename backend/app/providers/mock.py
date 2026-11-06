from __future__ import annotations

from app.providers.base import CodeChange


class MockProvider:
    def generate_plan(self, task: str) -> list[str]:
        return [
            "Inspect the requested synthetic source file.",
            "Apply one focused, reviewable change.",
            "Run the synthetic pytest suite and report the result.",
        ]

    def propose_code_change(self, task: str, plan: list[str], files: dict[str, str]) -> CodeChange:
        path = "src/text_utils.py"
        original = files.get(path)
        if original is None:
            raise ValueError(f"Synthetic target file is missing: {path}")
        updated_lines = []
        current_function = ""
        for line in original.splitlines(keepends=True):
            if line.startswith("def "):
                current_function = line[4:].partition("(")[0]
            if current_function in {"normalize_label", "normalize_tag"}:
                line = line.replace("value.strip().lower()", "value.strip().casefold()", 1)
            updated_lines.append(line)
        updated = "".join(updated_lines)
        return CodeChange(path=path, content=updated)

    def self_review(self, diff: str, test_result: dict[str, object]) -> str:
        if test_result.get("timed_out"):
            return "The test command timed out; do not approve until it is investigated."
        if test_result.get("exit_code") != 0:
            return "The test suite did not pass; review the output before considering approval."
        return "The normalization now uses Unicode-aware case folding. The focused synthetic test suite passed."
