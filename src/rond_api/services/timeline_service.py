"""时间线服务。"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone, tzinfo
from typing import Literal, cast

from rond_api.config import load_app_config
from rond_api.db.sqlite_client import SQLiteReadClient
from rond_api.domain.timeline_types import (
    MovementEvent,
    OutputMode,
    TimelineEvent,
    TimelineResult,
    TransportMode,
    VisitEvent,
)
from rond_api.repositories.timeline_repository import TimelineRepository

CORE_DATA_UNIX_EPOCH_OFFSET = 978307200
TRANSPORT_MODE_BY_TYPE: dict[int, TransportMode] = {
    0: "unknown",
    2: "walk",
    3: "run",
    4: "drive",
    5: "public_transit",
    6: "bike",
}


class TimelineService:
    """时间线业务服务。"""

    def __init__(self, repository: TimelineRepository) -> None:
        self._repository = repository

    def build_timeline(self, query_date: date, tz: tzinfo, timezone_name: str) -> TimelineResult:
        """构建指定日期时间线。"""

        day_start = datetime.combine(query_date, time.min, tzinfo=tz)
        day_end = day_start + timedelta(days=1)
        day_start_core = _to_core_data_seconds(day_start)
        day_end_core = _to_core_data_seconds(day_end)

        visit_rows = self._repository.fetch_visits(day_start_core, day_end_core)
        movement_rows = self._repository.fetch_movements(day_start_core, day_end_core)

        visit_ids = [int(row["visit_id"]) for row in visit_rows]
        location_ids = sorted(
            {
                int(row["location_id"])
                for row in visit_rows
                if row.get("location_id") is not None
            }
        )
        visit_tags_map = self._repository.fetch_visit_tags(visit_ids)
        location_tags_map = self._repository.fetch_location_tags(location_ids)

        events: list[TimelineEvent] = []
        for row in visit_rows:
            visit_id = int(row["visit_id"])
            location_id = row.get("location_id")
            arrival_at = _from_core_data_seconds(float(row["arrival_core"]), tz)
            departure_at = _from_core_data_seconds(float(row["departure_core"]), tz)

            merged_tags = set(visit_tags_map.get(visit_id, set()))
            if location_id is not None:
                merged_tags.update(location_tags_map.get(int(location_id), set()))

            events.append(
                VisitEvent(
                    visit_id=visit_id,
                    location_name=str(row["location_name"]),
                    category_name=str(row["category_name"]),
                    tags=sorted(merged_tags),
                    arrival_at=arrival_at,
                    departure_at=departure_at,
                    is_cross_day=arrival_at.date() != departure_at.date(),
                )
            )

        for row in movement_rows:
            start_at = _from_core_data_seconds(float(row["start_core"]), tz)
            end_at = _from_core_data_seconds(float(row["end_core"]), tz)
            movement_type = int(row["movement_type"]) if row["movement_type"] is not None else 0
            transport_mode = TRANSPORT_MODE_BY_TYPE.get(movement_type, "unknown")
            raw_transport_name = row.get("transport_name")
            transport_name = str(raw_transport_name).strip() if raw_transport_name else ""
            if not transport_name:
                transport_name = transport_mode

            duration_minutes = int(max((end_at - start_at).total_seconds(), 0) // 60)
            events.append(
                MovementEvent(
                    movement_id=int(row["movement_id"]),
                    transport_name=transport_name,
                    transport_mode=cast(TransportMode, transport_mode),
                    start_at=start_at,
                    end_at=end_at,
                    duration_minutes=duration_minutes,
                    from_location_name=_normalize_text(row.get("from_location_name")),
                    to_location_name=_normalize_text(row.get("to_location_name")),
                )
            )

        events.sort(
            key=lambda event: (
                _event_start_at(event),
                0 if event.event_type == "visit" else 1,
                _event_stable_id(event),
            )
        )
        return TimelineResult(query_date=query_date, timezone=timezone_name, events=events)


def get_timeline(
    date_expr: str,
    db_path: str | None = None,
    output: OutputMode = "pretty",
    emoji: bool = True,
) -> TimelineResult:
    """获取指定日期时间线。"""

    _validate_output_mode(output)
    if not isinstance(emoji, bool):
        raise ValueError("emoji must be bool.")

    config = load_app_config(db_path=db_path)
    query_date = parse_query_date(date_expr, config.timezone)
    client = SQLiteReadClient(config.db_path)
    repository = TimelineRepository(client)
    service = TimelineService(repository)
    return service.build_timeline(query_date=query_date, tz=config.timezone, timezone_name=config.timezone_name)


def parse_query_date(date_expr: str, tz: tzinfo) -> date:
    """解析 today/yesterday/ISO 日期。"""

    normalized = date_expr.strip().lower()
    today = datetime.now(tz).date()
    if normalized == "today":
        return today
    if normalized == "yesterday":
        return today - timedelta(days=1)

    try:
        return date.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(
            f"Invalid date expression: {date_expr}. Use today, yesterday or YYYY-MM-DD."
        ) from exc


def _validate_output_mode(output: str) -> Literal["pretty", "json", "both"]:
    """校验输出模式。"""

    allowed: set[str] = {"pretty", "json", "both"}
    if output not in allowed:
        raise ValueError(f"Invalid output mode: {output}. Allowed: pretty, json, both.")
    return cast(Literal["pretty", "json", "both"], output)


def _to_core_data_seconds(value: datetime) -> float:
    """时区时间转 Core Data 秒。"""

    unix_seconds = value.astimezone(timezone.utc).timestamp()
    return unix_seconds - CORE_DATA_UNIX_EPOCH_OFFSET


def _from_core_data_seconds(value: float, tz: tzinfo) -> datetime:
    """Core Data 秒转时区时间。"""

    unix_seconds = value + CORE_DATA_UNIX_EPOCH_OFFSET
    return datetime.fromtimestamp(unix_seconds, tz=timezone.utc).astimezone(tz)


def _normalize_text(value: object | None) -> str | None:
    """标准化文本字段。"""

    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _event_start_at(event: TimelineEvent) -> datetime:
    """事件起始时间。"""

    if isinstance(event, VisitEvent):
        return event.arrival_at
    return event.start_at


def _event_stable_id(event: TimelineEvent) -> int:
    """稳定排序 ID。"""

    if isinstance(event, VisitEvent):
        return event.visit_id
    return event.movement_id
