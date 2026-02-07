from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    db_path: Path


def load_settings() -> Settings:
    db_path = os.environ.get("APP_CONTAINER_DB_PATH")
    if not db_path:
        raise RuntimeError("APP_CONTAINER_DB_PATH is not set")
    return Settings(db_path=Path(db_path))
