"""SQLite read client tests."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from rond_api.db.sqlite_client import DatabaseReadError, SQLiteReadClient


def test_sqlite_read_client_retries_when_locked(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "retry.db"
    _init_demo_database(db_path)

    calls = {"count": 0}
    original_execute_once = SQLiteReadClient._execute_once

    def flaky_execute_once(self: SQLiteReadClient, sql: str, params: tuple[object, ...]):
        if calls["count"] == 0:
            calls["count"] += 1
            raise sqlite3.OperationalError("database is locked")
        return original_execute_once(self, sql, params)

    monkeypatch.setattr(SQLiteReadClient, "_execute_once", flaky_execute_once)
    monkeypatch.setattr("rond_api.db.sqlite_client.time.sleep", lambda _seconds: None)

    client = SQLiteReadClient(db_path=db_path, max_retries=3, retry_backoff_seconds=0.0)
    rows = client.execute_query("SELECT value FROM demo LIMIT 1;")
    assert rows[0]["value"] == "ok"
    assert calls["count"] == 1


def test_sqlite_read_client_raises_after_non_retryable_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "error.db"
    _init_demo_database(db_path)

    def failing_execute_once(self: SQLiteReadClient, sql: str, params: tuple[object, ...]):
        raise sqlite3.OperationalError("no such table: missing")

    monkeypatch.setattr(SQLiteReadClient, "_execute_once", failing_execute_once)
    client = SQLiteReadClient(db_path=db_path, max_retries=3, retry_backoff_seconds=0.0)

    with pytest.raises(DatabaseReadError):
        client.execute_query("SELECT * FROM missing;")


def _init_demo_database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE demo (value TEXT);")
        connection.execute("INSERT INTO demo (value) VALUES ('ok');")
        connection.commit()
