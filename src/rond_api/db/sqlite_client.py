"""SQLite 只读客户端。"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import quote


class DatabaseReadError(RuntimeError):
    """数据库读取失败。"""


@dataclass(slots=True)
class SQLiteReadClient:
    """带锁重试的 SQLite 只读客户端。"""

    db_path: Path | str
    busy_timeout_ms: int = 3_000
    max_retries: int = 3
    retry_backoff_seconds: float = 0.05
    _db_uri: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        resolved_path = Path(self.db_path).expanduser().resolve()
        self.db_path = resolved_path
        encoded_path = quote(str(resolved_path), safe="/")
        self._db_uri = f"file:{encoded_path}?mode=ro"

    def execute_query(
        self,
        sql: str,
        params: Sequence[Any] | Mapping[str, Any] | None = None,
    ) -> list[sqlite3.Row]:
        """执行只读查询。"""

        bound_params: Sequence[Any] | Mapping[str, Any]
        if params is None:
            bound_params = ()
        else:
            bound_params = params

        attempts = self.max_retries + 1
        for attempt in range(attempts):
            try:
                return self._execute_once(sql, bound_params)
            except sqlite3.OperationalError as exc:
                if not self._is_retryable(exc) or attempt >= self.max_retries:
                    raise DatabaseReadError(
                        f"SQLite read failed after {attempt + 1} attempt(s): {exc}"
                    ) from exc
                sleep_seconds = self.retry_backoff_seconds * (attempt + 1)
                time.sleep(sleep_seconds)

        raise DatabaseReadError("SQLite read failed unexpectedly.")

    def _execute_once(
        self,
        sql: str,
        params: Sequence[Any] | Mapping[str, Any],
    ) -> list[sqlite3.Row]:
        """执行单次查询。"""

        with sqlite3.connect(self._db_uri, uri=True) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute(f"PRAGMA busy_timeout = {self.busy_timeout_ms};")
            connection.execute("PRAGMA query_only = ON;")
            cursor = connection.execute(sql, params)
            rows = cursor.fetchall()
            cursor.close()
            return rows

    @staticmethod
    def _is_retryable(exc: sqlite3.OperationalError) -> bool:
        """判断是否可重试。"""

        message = str(exc).lower()
        return "locked" in message or "busy" in message
