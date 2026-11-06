from dataclasses import dataclass
import os
from pathlib import Path


EVALFORGE_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    codepilot_api_url: str = os.getenv("CODEPILOT_API_URL", "http://localhost:8000").rstrip("/")
    database_path: Path = Path(os.getenv("EVALFORGE_DATABASE_PATH", str(EVALFORGE_ROOT / "data" / "evalforge.sqlite3")))
