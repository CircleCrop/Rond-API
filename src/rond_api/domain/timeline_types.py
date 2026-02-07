"""时间线领域类型。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

OutputMode = Literal["pretty", "json", "both"]
TransportMode = Literal[
    "unknown",
    "walk",
    "run",
    "drive",
    "public_transit",
    "bike",
    "flight",
]


@dataclass(frozen=True, slots=True)
class VisitEvent:
    """地点到访事件。"""

    visit_id: int
    location_name: str
    category_name: str
    location_type: int | None
    tags: list[str]
    arrival_at: datetime
    departure_at: datetime
    is_cross_day: bool
    is_ongoing: bool = False
    event_type: Literal["visit"] = "visit"

    @property
    def start_at(self) -> datetime:
        return self.arrival_at

    @property
    def end_at(self) -> datetime:
        return self.departure_at


@dataclass(frozen=True, slots=True)
class MovementEvent:
    """交通移动事件。"""

    movement_id: int
    transport_name: str
    transport_mode: TransportMode
    start_at: datetime
    end_at: datetime
    duration_minutes: int
    from_location_name: str | None
    to_location_name: str | None
    event_type: Literal["movement"] = "movement"


TimelineEvent = VisitEvent | MovementEvent


@dataclass(slots=True)
class TimelineResult:
    """时间线结果。"""

    query_date: date
    timezone: str
    events: list[TimelineEvent]
