"""JSON 输出格式化。"""

from __future__ import annotations

import json
from typing import Any

from rond_api.domain.timeline_types import MovementEvent, TimelineResult, VisitEvent


def timeline_to_dict(timeline: TimelineResult) -> dict[str, Any]:
    """时间线结果转字典。"""

    events: list[dict[str, Any]] = []
    for event in timeline.events:
        if isinstance(event, VisitEvent):
            events.append(
                {
                    "event_type": "visit",
                    "visit_id": event.visit_id,
                    "location_name": event.location_name,
                    "category_name": event.category_name,
                    "tags": event.tags,
                    "arrival_at": event.arrival_at.isoformat(),
                    "departure_at": event.departure_at.isoformat(),
                    "is_cross_day": event.is_cross_day,
                    "is_ongoing": event.is_ongoing,
                }
            )
            continue

        if isinstance(event, MovementEvent):
            events.append(
                {
                    "event_type": "movement",
                    "movement_id": event.movement_id,
                    "transport_name": event.transport_name,
                    "transport_mode": event.transport_mode,
                    "start_at": event.start_at.isoformat(),
                    "end_at": event.end_at.isoformat(),
                    "duration_minutes": event.duration_minutes,
                    "from_location_name": event.from_location_name,
                    "to_location_name": event.to_location_name,
                }
            )

    return {
        "query_date": timeline.query_date.isoformat(),
        "timezone": timeline.timezone,
        "events": events,
    }


def render_timeline_json(timeline: TimelineResult) -> str:
    """渲染 JSON 文本。"""

    payload = timeline_to_dict(timeline)
    return json.dumps(payload, ensure_ascii=False, indent=2)
