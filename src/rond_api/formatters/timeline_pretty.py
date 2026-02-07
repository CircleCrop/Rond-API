"""可读时间线格式化。"""

from __future__ import annotations

from rond_api.domain.timeline_types import MovementEvent, TimelineResult, VisitEvent


EMOJI_BY_TRANSPORT_MODE = {
    "unknown": "🛣️",
    "walk": "🚶",
    "run": "🏃",
    "drive": "🚗",
    "public_transit": "🚇",
    "bike": "🚴",
}


def render_timeline_pretty(timeline: TimelineResult, emoji: bool = True) -> str:
    """渲染可读时间线。"""

    lines: list[str] = []
    if emoji:
        lines.append(f"🗓️ 时间线 {timeline.query_date.isoformat()} ({timeline.timezone})")
    else:
        lines.append(f"Timeline {timeline.query_date.isoformat()} ({timeline.timezone})")

    lines.append(f"事件总数: {len(timeline.events)}")
    lines.append("─" * 72)

    if not timeline.events:
        lines.append("无数据")
        return "\n".join(lines)

    for event in timeline.events:
        if isinstance(event, VisitEvent):
            lines.extend(_format_visit_event(event, emoji))
        elif isinstance(event, MovementEvent):
            lines.extend(_format_movement_event(event, emoji))
        lines.append("")

    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def _format_visit_event(event: VisitEvent, emoji: bool) -> list[str]:
    marker = "📍" if emoji else "[visit]"
    cross_day_marker = " 🌙跨天" if event.is_cross_day else ""
    lines = [
        f"{marker} {event.arrival_at:%Y-%m-%d %H:%M} -> {event.departure_at:%Y-%m-%d %H:%M}{cross_day_marker}",
        f"   地点: {event.location_name}",
        f"   分类: {event.category_name}",
    ]
    if event.tags:
        lines.append(f"   标签: {', '.join(event.tags)}")
    return lines


def _format_movement_event(event: MovementEvent, emoji: bool) -> list[str]:
    if emoji:
        marker = EMOJI_BY_TRANSPORT_MODE.get(event.transport_mode, "🛣️")
    else:
        marker = "[movement]"

    from_location_name = event.from_location_name or "未知地点"
    to_location_name = event.to_location_name or "未知地点"
    return [
        f"{marker} {event.start_at:%Y-%m-%d %H:%M} -> {event.end_at:%Y-%m-%d %H:%M} ({event.duration_minutes}m)",
        f"   交通: {event.transport_name} [{event.transport_mode}]",
        f"   路线: {from_location_name} -> {to_location_name}",
    ]
