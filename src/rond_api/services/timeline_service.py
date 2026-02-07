"""时间线服务。"""

from __future__ import annotations

import math
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
    5: "flight",
    6: "bike",
}
TRANSPORT_FALLBACK_NAME_BY_MODE: dict[TransportMode, str] = {
    "unknown": "未知交通",
    "walk": "步行",
    "run": "跑步",
    "bike": "骑行",
    "drive": "机动车",
    "flight": "飞行",
    "public_transit": "公共交通",
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
        nearby_cache: dict[tuple[float, float], list[dict[str, object]]] = {}

        events: list[TimelineEvent] = []
        for row in visit_rows:
            visit_id = int(row["visit_id"])
            location_id = row.get("location_id")
            arrival_at = _from_core_data_seconds(float(row["arrival_core"]), tz)
            departure_at = _from_core_data_seconds(float(row["departure_core"]), tz)
            location_name, category_name = self._resolve_visit_location_and_category(
                row,
                nearby_cache=nearby_cache,
            )

            merged_tags = set(visit_tags_map.get(visit_id, set()))
            if location_id is not None:
                merged_tags.update(location_tags_map.get(int(location_id), set()))

            events.append(
                VisitEvent(
                    visit_id=visit_id,
                    location_name=location_name,
                    category_name=category_name,
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
                transport_name = TRANSPORT_FALLBACK_NAME_BY_MODE[cast(TransportMode, transport_mode)]

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

        today = datetime.now(tz).date()
        if query_date == today:
            self._append_ongoing_stay_event(
                events=events,
                day_end_core=day_end_core,
                tz=tz,
                nearby_cache=nearby_cache,
            )

        events.sort(
            key=lambda event: (
                _event_start_at(event),
                0 if event.event_type == "visit" else 1,
                _event_stable_id(event),
            )
        )
        return TimelineResult(query_date=query_date, timezone=timezone_name, events=events)

    def _resolve_visit_location_and_category(
        self,
        row: dict[str, object],
        nearby_cache: dict[tuple[float, float], list[dict[str, object]]],
    ) -> tuple[str, str]:
        """解析到访地点与分类，必要时回退可能地点。"""

        category_name = _normalize_text(row.get("category_name")) or "未分类"
        location_name = _normalize_text(row.get("location_name"))
        if location_name and location_name != "未知地点":
            return location_name, category_name

        raw_name = _normalize_text(row.get("raw_name"))
        raw_road = _normalize_text(row.get("raw_thoroughfare"))
        latitude = _to_float(row.get("raw_latitude"))
        longitude = _to_float(row.get("raw_longitude"))

        nearest = self._resolve_nearest_location(
            latitude=latitude,
            longitude=longitude,
            nearby_cache=nearby_cache,
            max_distance_m=280.0,
        )
        if nearest:
            nearest_name = _normalize_text(nearest.get("location_name"))
            nearest_home_count = int(nearest.get("home_visit_count") or 0)
            if nearest_name:
                resolved_category = "家" if nearest_home_count > 0 else category_name
                return nearest_name, resolved_category

        fallback_name = raw_name or raw_road or "未知地点"
        return fallback_name, category_name

    def _append_ongoing_stay_event(
        self,
        events: list[TimelineEvent],
        day_end_core: float,
        tz: tzinfo,
        nearby_cache: dict[tuple[float, float], list[dict[str, object]]],
    ) -> None:
        """补充停留中地点。"""

        raw_open = self._repository.fetch_latest_open_raw_visit(day_end_core)
        if raw_open is None:
            return

        arrival_core = raw_open.get("arrival_core")
        if arrival_core is None:
            return
        arrival_at = _from_core_data_seconds(float(arrival_core), tz)
        now_at = datetime.now(tz)
        if now_at < arrival_at:
            now_at = arrival_at

        if self._is_time_covered_by_visit(events, arrival_at):
            return

        latitude = _to_float(raw_open.get("raw_latitude"))
        longitude = _to_float(raw_open.get("raw_longitude"))
        nearest = self._resolve_nearest_location(
            latitude=latitude,
            longitude=longitude,
            nearby_cache=nearby_cache,
            max_distance_m=280.0,
        )
        raw_name = _normalize_text(raw_open.get("raw_name"))
        raw_road = _normalize_text(raw_open.get("raw_thoroughfare"))
        location_name = _normalize_text(nearest.get("location_name")) if nearest else None
        home_visit_count = int(nearest.get("home_visit_count") or 0) if nearest else 0
        category_name = "家" if home_visit_count > 0 else "未分类"

        events.append(
            VisitEvent(
                visit_id=-int(raw_open.get("raw_id", 0) or 0),
                location_name=location_name or raw_name or raw_road or "未知地点",
                category_name=category_name,
                tags=[],
                arrival_at=arrival_at,
                departure_at=now_at,
                is_cross_day=arrival_at.date() != now_at.date(),
                is_ongoing=True,
            )
        )

    def _is_time_covered_by_visit(self, events: list[TimelineEvent], target_at: datetime) -> bool:
        """检查时刻是否已被现有到访覆盖。"""

        for event in events:
            if not isinstance(event, VisitEvent):
                continue
            if event.arrival_at <= target_at <= event.departure_at:
                return True
        return False

    def _resolve_nearest_location(
        self,
        latitude: float | None,
        longitude: float | None,
        nearby_cache: dict[tuple[float, float], list[dict[str, object]]],
        max_distance_m: float,
    ) -> dict[str, object] | None:
        """获取阈值内最近地点。"""

        if latitude is None or longitude is None:
            return None

        cache_key = (round(latitude, 6), round(longitude, 6))
        nearby_locations = nearby_cache.get(cache_key)
        if cache_key not in nearby_cache:
            nearby_locations = self._repository.fetch_nearby_locations(
                latitude=latitude,
                longitude=longitude,
                limit=25,
            )
            nearby_cache[cache_key] = nearby_locations

        if not nearby_locations:
            return None

        filtered: list[dict[str, object]] = []
        for item in nearby_locations:
            item_lat = _to_float(item.get("latitude"))
            item_lon = _to_float(item.get("longitude"))
            if item_lat is None or item_lon is None:
                continue
            distance_m = _distance_meters(latitude, longitude, item_lat, item_lon)
            if distance_m <= max_distance_m:
                candidate = dict(item)
                candidate["distance_m"] = distance_m
                filtered.append(candidate)

        if not filtered:
            return None

        home_candidates = [
            item for item in filtered if int(item.get("home_visit_count") or 0) > 0
        ]
        if home_candidates:
            home_candidates.sort(
                key=lambda item: (
                    -int(item.get("home_visit_count") or 0),
                    float(item.get("distance_m") or 0),
                )
            )
            return home_candidates[0]

        filtered.sort(key=lambda item: float(item.get("distance_m") or 0))
        return filtered[0]


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


def _to_float(value: object | None) -> float | None:
    """安全转换为浮点数。"""

    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """两点球面距离（米）。"""

    radius_m = 6_371_000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    hav = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * (math.sin(dlambda / 2) ** 2)
    )
    return 2 * radius_m * math.atan2(math.sqrt(hav), math.sqrt(1 - hav))


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
