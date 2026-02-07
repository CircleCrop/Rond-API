from __future__ import annotations

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def sqlite_url(db_path: Path) -> str:
    # SQLAlchemy expects a file path without URL encoding for local SQLite.
    return f"sqlite+pysqlite:///{db_path}"


def create_sqlite_engine(db_path: Path) -> Engine:
    return create_engine(sqlite_url(db_path), future=True)
