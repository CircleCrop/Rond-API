"""应用配置加载。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, tzinfo
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv


class ConfigError(ValueError):
    """配置相关错误。"""


@dataclass(frozen=True, slots=True)
class AppConfig:
    """应用运行配置。"""

    db_path: Path
    timezone: tzinfo
    timezone_name: str


def load_app_config(
    db_path: str | None = None,
    timezone_name: str | None = None,
) -> AppConfig:
    """加载应用配置。"""

    load_dotenv(override=False)
    resolved_db_path = resolve_db_path(db_path)
    resolved_timezone, resolved_timezone_name = resolve_timezone(timezone_name)
    return AppConfig(
        db_path=resolved_db_path,
        timezone=resolved_timezone,
        timezone_name=resolved_timezone_name,
    )


def resolve_db_path(db_path: str | None = None) -> Path:
    """解析数据库路径，优先级：参数 > 环境变量 > 测试库。"""

    if db_path:
        candidate = _normalize_path(db_path)
        if not candidate.exists():
            raise ConfigError(f"Database path does not exist: {candidate}")
        return candidate

    env_path = os.getenv("ROND_DB_PATH")
    if env_path:
        candidate = _normalize_path(env_path)
        if candidate.exists():
            return candidate

    project_root = Path(__file__).resolve().parents[2]
    test_db_path = project_root / "tests" / "LifeEasy.sqlite"
    if test_db_path.exists():
        return test_db_path.resolve()

    raise ConfigError(
        "Unable to resolve database path. Set ROND_DB_PATH or pass --db-path."
    )


def resolve_timezone(timezone_name: str | None = None) -> tuple[tzinfo, str]:
    """解析时区，默认使用系统时区。"""

    if timezone_name:
        try:
            zone = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise ConfigError(f"Unknown timezone: {timezone_name}") from exc
        return zone, timezone_name

    local_timezone = datetime.now().astimezone().tzinfo
    if local_timezone is None:
        raise ConfigError("Unable to determine system timezone.")

    zone_key = getattr(local_timezone, "key", None)
    if isinstance(zone_key, str) and zone_key:
        return local_timezone, zone_key

    zone_name = datetime.now().astimezone().tzname() or "local"
    return local_timezone, zone_name


def _normalize_path(raw_path: str) -> Path:
    """标准化路径。"""

    return Path(raw_path).expanduser().resolve()
