from __future__ import annotations

import json
import os

from app.providers.base import CodeChange


class OpenAIProvider:
    """Optional provider; install the openai extra and set OPENAI_API_KEY to enable."""

    def __init__(self) -> None:
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is required when AGENT_PROVIDER=openai")
        try:
            from openai import OpenAI
        except ImportError as error:
            raise RuntimeError("Install backend/requirements-openai.txt to use the OpenAI provider") from error
        self.client = OpenAI()
        self.model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    def _structured(self, name: str, schema: dict[str, object], prompt: str) -> dict[str, object]:
        response = self.client.responses.create(
            model=self.model,
            input=prompt,
            text={"format": {"type": "json_schema", "name": name, "strict": True, "schema": schema}},
        )
        return json.loads(response.output_text)

    def generate_plan(self, task: str) -> list[str]:
        result = self._structured(
            "agent_plan",
            {"type": "object", "properties": {"steps": {"type": "array", "items": {"type": "string"}}}, "required": ["steps"], "additionalProperties": False},
            f"Create a concise plan for this synthetic-codebase task. Do not execute commands.\n{task}",
        )
        return [str(step) for step in result["steps"]]

    def propose_code_change(self, task: str, plan: list[str], files: dict[str, str]) -> CodeChange:
        schema = {
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"],
            "additionalProperties": False,
        }
        result = self._structured(
            "code_change",
            schema,
            f"Return the complete replacement content for exactly one existing file from this synthetic codebase. Never request commands or secrets.\nTask: {task}\nPlan: {plan}\nFiles: {json.dumps(files)}",
        )
        return CodeChange(path=str(result["path"]), content=str(result["content"]))

    def self_review(self, diff: str, test_result: dict[str, object]) -> str:
        result = self._structured(
            "change_review",
            {"type": "object", "properties": {"review": {"type": "string"}}, "required": ["review"], "additionalProperties": False},
            f"Review this proposed synthetic-codebase diff and test result. Identify risks; do not approve it.\nDiff: {diff}\nTests: {json.dumps(test_result)}",
        )
        return str(result["review"])
