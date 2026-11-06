from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    provider: str = os.getenv("AGENT_PROVIDER", "mock").lower()
    database_path: Path | str = os.getenv(
        "DATABASE_URL", str(Path(os.getenv("DATABASE_PATH", str(REPOSITORY_ROOT / "data" / "foundry.sqlite3"))))
    )
    target_root: Path = REPOSITORY_ROOT / "target_codebase"
    sandbox_timeout_seconds: float = float(os.getenv("SANDBOX_TIMEOUT_SECONDS", "20"))
    sandbox_mode: str = os.getenv("SANDBOX_MODE", "local").lower()
    sandbox_runner_url: str = os.getenv("SANDBOX_RUNNER_URL", "http://sandbox-runner:9000")


settings = Settings()
