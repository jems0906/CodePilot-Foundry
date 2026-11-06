from __future__ import annotations

import re
from collections.abc import Mapping


SAFE_ENV_KEYS = frozenset({"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "COMSPEC"})


def filtered_environment(source: Mapping[str, str]) -> dict[str, str]:
    return {key: value for key, value in source.items() if key.upper() in SAFE_ENV_KEYS}


def secret_environment_values(source: Mapping[str, str]) -> dict[str, str]:
    marker = re.compile(r"(?i)(secret|token|password|credential|api[_-]?key)")
    return {key: value for key, value in source.items() if value and marker.search(key)}


def redact_text(text: str, secrets: Mapping[str, str]) -> str:
    redacted = text
    values = sorted({value for value in secrets.values() if value}, key=len, reverse=True)
    for value in values:
        redacted = redacted.replace(value, "[REDACTED]")
    return re.sub(r"(?i)(api[_-]?key|token|password|secret)(\s*[=:]\s*)[^\s,;]+", r"\1\2[REDACTED]", redacted)
