"""Timeline service tests."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from rond_api.domain.timeline_types import MovementEvent, TimelineResult, VisitEvent
from rond_api.formatters.timeline_json import render_timeline_json
from rond_api.formatters.timeline_pretty import _category_emoji, render_timeline_pretty
from rond_api.services.timeline_service import TimelineService, parse_query_date

CORE_DATA_UNIX_EPOCH_OFFSET = 978307200


class FakeTimelineRepository:
    """测试用时间线仓储。"""

    def __init__(self) -> None:
        self._visit_rows = self._build_visit_rows()
        self._movement_rows = self._build_movement_rows()
        self._visit_tags = {101: {"示例标签A", "共享标签"}}
        self._location_tags = {501: {"示例地点标签", "共享标签"}}
        self._nearby_locations = {
            (32.0, 119.0): [
                {
                    "location_id": 901,
                    "location_name": "示例住宅B",
                    "location_type": 3,
                    "poi_category": "MKPOICategoryStore",
                    "latitude": 32.0,
                    "longitude": 119.0,
                    "home_visit_count": 3,
                    "visit_count": 10,
                }
            ]
        }

    def fetch_visits(self, _day_start_core: float, _day_end_core: float) -> list[dict[str, object]]:
        return list(self._visit_rows)

    def fetch_movements(self, _day_start_core: float, _day_end_core: float) -> list[dict[str, object]]:
        return list(self._movement_rows)

    def fetch_visit_tags(self, _visit_ids: list[int]) -> dict[int, set[str]]:
        return self._visit_tags

    def fetch_location_tags(self, _location_ids: list[int]) -> dict[int, set[str]]:
        return self._location_tags

    def fetch_nearby_locations(
        self,
        latitude: float,
        longitude: float,
        limit: int = 25,
    ) -> list[dict[str, object]]:
        _ = limit
        return self._nearby_locations.get((round(latitude, 4), round(longitude, 4)), [])

    def fetch_latest_open_raw_visit(self, _day_end_core: float) -> dict[str, object] | None:
        return None

    @staticmethod
    def _build_visit_rows() -> list[dict[str, object]]:
        tz = ZoneInfo("UTC")
        return [
            {
                "visit_id": 102,
                "location_id": None,
                "arrival_core": _to_core_seconds(datetime(2026, 1, 28, 23, 50, tzinfo=tz)),
                "departure_core": _to_core_seconds(datetime(2026, 1, 29, 0, 20, tzinfo=tz)),
                "raw_name": "未知地点",
                "raw_thoroughfare": "示例道路",
                "raw_latitude": 32.0,
                "raw_longitude": 119.0,
                "location_type": None,
                "poi_category": None,
                "location_name": "未知地点",
                "category_name": "未分类",
            },
            {
                "visit_id": 101,
                "location_id": 501,
                "arrival_core": _to_core_seconds(datetime(2026, 1, 29, 8, 0, tzinfo=tz)),
                "departure_core": _to_core_seconds(datetime(2026, 1, 29, 9, 0, tzinfo=tz)),
                "raw_name": None,
                "raw_thoroughfare": None,
                "raw_latitude": None,
                "raw_longitude": None,
                "location_type": 0,
                "poi_category": "MKPOICategoryStore",
                "location_name": "示例地点A",
                "category_name": "商场",
            },
        ]

    @staticmethod
    def _build_movement_rows() -> list[dict[str, object]]:
        tz = ZoneInfo("UTC")
        return [
            {
                "movement_id": 202,
                "start_core": _to_core_seconds(datetime(2026, 1, 29, 9, 20, tzinfo=tz)),
                "end_core": _to_core_seconds(datetime(2026, 1, 29, 9, 50, tzinfo=tz)),
                "movement_type": 4,
                "transport_name": "",
                "from_location_name": "示例地点A",
                "to_location_name": "示例地点C",
            },
            {
                "movement_id": 201,
                "start_core": _to_core_seconds(datetime(2026, 1, 29, 9, 0, tzinfo=tz)),
                "end_core": _to_core_seconds(datetime(2026, 1, 29, 9, 20, tzinfo=tz)),
                "movement_type": 2,
                "transport_name": None,
                "from_location_name": "示例地点A",
                "to_location_name": "示例地点B",
            },
        ]


def _to_core_seconds(value: datetime) -> float:
    unix_seconds = value.astimezone(timezone.utc).timestamp()
    return unix_seconds - CORE_DATA_UNIX_EPOCH_OFFSET


def _build_synthetic_timeline() -> TimelineResult:
    query_date = date(2026, 1, 29)
    tz = ZoneInfo("UTC")
    service = TimelineService(FakeTimelineRepository())
    return service.build_timeline(
        query_date=query_date,
        tz=tz,
        timezone_name="中国/江苏",
    )


def test_parse_query_date_supports_today_and_yesterday() -> None:
    tz = ZoneInfo("UTC")
    today = datetime.now(tz).date()
    assert parse_query_date("today", tz) == today
    assert parse_query_date("yesterday", tz) == today - timedelta(days=1)


def test_parse_query_date_supports_iso_date() -> None:
    tz = ZoneInfo("UTC")
    assert parse_query_date("2026-01-29", tz).isoformat() == "2026-01-29"
    assert parse_query_date("2026-1-1", tz).isoformat() == "2026-01-01"


def test_parse_query_date_supports_month_day_without_year() -> None:
    tz = ZoneInfo("UTC")
    today = datetime.now(tz).date()
    parsed = parse_query_date("1-1", tz)
    assert parsed.year == today.year
    assert parsed.month == 1
    assert parsed.day == 1


def test_parse_query_date_invalid_value_raises_error() -> None:
    tz = ZoneInfo("UTC")
    with pytest.raises(ValueError):
        parse_query_date("2026/01/29", tz)


def test_timeline_mixes_visits_and_movements_in_chronological_order() -> None:
    timeline = _build_synthetic_timeline()

    assert timeline.query_date.isoformat() == "2026-01-29"
    events = timeline.events
    assert events
    assert any(isinstance(event, VisitEvent) for event in events)
    assert any(isinstance(event, MovementEvent) for event in events)

    for previous, current in zip(events, events[1:]):
        previous_start = previous.arrival_at if isinstance(previous, VisitEvent) else previous.start_at
        current_start = current.arrival_at if isinstance(current, VisitEvent) else current.start_at
        assert previous_start <= current_start
        if previous_start == current_start:
            previous_rank = 0 if previous.event_type == "visit" else 1
            current_rank = 0 if current.event_type == "visit" else 1
            assert previous_rank <= current_rank


def test_cross_day_visits_are_not_missed() -> None:
    timeline = _build_synthetic_timeline()
    events = timeline.events
    cross_day_visits = [event for event in events if isinstance(event, VisitEvent) and event.is_cross_day]
    assert cross_day_visits
    assert cross_day_visits[0].location_name == "示例住宅B"
    assert cross_day_visits[0].category_name == "家"


def test_visit_tags_merge_and_deduplicate_visit_and_location_tags() -> None:
    timeline = _build_synthetic_timeline()
    events = timeline.events
    target = next(event for event in events if isinstance(event, VisitEvent) and event.visit_id == 101)
    assert set(target.tags) == {"示例标签A", "示例地点标签", "共享标签"}


def test_movement_transport_falls_back_to_type_mapping() -> None:
    timeline = _build_synthetic_timeline()
    events = timeline.events
    movements = [event for event in events if isinstance(event, MovementEvent)]
    movement_map = {event.movement_id: event for event in movements}
    assert movement_map[201].transport_name == "步行"
    assert movement_map[202].transport_name == "机动车"


def test_pretty_and_json_renderers_work() -> None:
    timeline = _build_synthetic_timeline()

    pretty_output = render_timeline_pretty(timeline, emoji=True)
    assert "时间线" in pretty_output
    assert "路线:" in pretty_output
    assert "交通:" in pretty_output
    assert "[walk]" not in pretty_output
    assert "[public_transit]" not in pretty_output

    json_output = render_timeline_json(timeline)
    payload = json.loads(json_output)
    assert payload["query_date"] == "2026-01-29"
    assert isinstance(payload["events"], list)


def test_category_emoji_type_priority_then_keyword() -> None:
    # type=1 road + POI station should give station emoji first
    assert (
        _category_emoji("未分类", "某某路", 1, "MKPOICategoryPublicTransport", emoji=True)
        == "🚉"
    )
    # keyword can further refine after POI
    assert (
        _category_emoji("未分类", "江苏机场", 1, "MKPOICategoryPublicTransport", emoji=True)
        == "🛫"
    )
    # no poi/no keyword keeps type-based emoji
    assert _category_emoji("未分类", "某某路", 1, None, emoji=True) == "🛣️"
