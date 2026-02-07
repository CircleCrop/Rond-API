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
    "flight": "✈️",
}


def render_timeline_pretty(timeline: TimelineResult, emoji: bool = True) -> str:
    """渲染可读时间线。"""

    lines: list[str] = []
    if emoji:
        lines.append(f"🗓️ 时间线 {timeline.query_date.isoformat()} ({timeline.timezone})")
    else:
        lines.append(f"Timeline {timeline.query_date.isoformat()} ({timeline.timezone})")

    lines.append("─" * 72)

    if not timeline.events:
        lines.append("无数据")
        return "\n".join(lines)

    index = 0
    while index < len(timeline.events):
        event = timeline.events[index]
        if isinstance(event, VisitEvent):
            lines.extend(_format_visit_event(event, emoji))
            index += 1
        else:
            movement_group: list[MovementEvent] = []
            while index < len(timeline.events) and isinstance(
                timeline.events[index], MovementEvent
            ):
                movement_group.append(timeline.events[index])
                index += 1
            next_visit = (
                timeline.events[index]
                if index < len(timeline.events)
                and isinstance(timeline.events[index], VisitEvent)
                else None
            )
            lines.extend(_format_movement_group(movement_group, next_visit, emoji))
        lines.append("")

    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def _format_visit_event(event: VisitEvent, emoji: bool) -> list[str]:
    marker = "📍" if emoji else "[visit]"
    cross_day_marker = " 🌙 跨天" if event.is_cross_day else ""
    end_text = "进行中" if event.is_ongoing else f"{event.departure_at:%Y-%m-%d %H:%M}"
    lines = [
        f"{marker} {event.arrival_at:%Y-%m-%d %H:%M} -> {end_text}{cross_day_marker}",
        f"   地点: {event.location_name}",
        f"   分类: {event.category_name}",
    ]
    if event.is_ongoing:
        lines.append("   状态: 停留中")
    if event.tags:
        lines.append(f"   标签: {', '.join(event.tags)}")
    return lines


def _format_movement_group(
    group: list[MovementEvent],
    next_visit: VisitEvent | None,
    emoji: bool,
) -> list[str]:
    dominant = max(group, key=lambda item: item.duration_minutes)
    marker = _movement_emoji(dominant, emoji=emoji)

    start_at = group[0].start_at
    end_at = group[-1].end_at
    start_floor = start_at.replace(second=0, microsecond=0)
    end_floor = end_at.replace(second=0, microsecond=0)
    total_minutes = int(max((end_floor - start_floor).total_seconds(), 0) // 60)

    from_location_name = group[0].from_location_name or "未知地点"
    to_location_name = group[-1].to_location_name
    if not to_location_name and next_visit is not None:
        to_location_name = next_visit.location_name
    if not to_location_name:
        to_location_name = "未知地点"

    transport_parts = [_movement_part_text(item, emoji=emoji) for item in group]
    wrapped_transport_lines = _wrap_parts(transport_parts, max_width=48)
    transport_prefix = "   交通: "

    lines = [
        f"{marker} {start_at:%Y-%m-%d %H:%M} -> {end_at:%Y-%m-%d %H:%M} ({total_minutes}m)",
        f"   路线: {from_location_name} -> {to_location_name}",
    ]
    if wrapped_transport_lines:
        lines.append(f"{transport_prefix}{wrapped_transport_lines[0]}")
        indent = " " * len(transport_prefix)
        lines.extend(f"{indent}{line}" for line in wrapped_transport_lines[1:])
    else:
        lines.append(f"{transport_prefix}无")
    return lines


def _movement_part_text(event: MovementEvent, emoji: bool) -> str:
    icon = _movement_emoji(event, emoji=emoji)
    if emoji:
        return f"{icon} {event.transport_name} ({event.duration_minutes}m)"
    return f"{event.transport_name} ({event.duration_minutes}m)"


def _movement_emoji(event: MovementEvent, emoji: bool) -> str:
    if not emoji:
        return "[movement]"

    name = event.transport_name
    if _contains_any(name, ("地铁", "电车", "高铁", "火车", "轻轨", "有轨")):
        return "🚇"
    if _contains_any(name, ("步行",)):
        return "🚶"
    if _contains_any(name, ("跑",)):
        return "🏃"
    if _contains_any(name, ("骑", "单车", "自行车", "电瓶")):
        return "🚴"
    if _contains_any(name, ("飞", "航班", "飞机")):
        return "✈️"
    if _contains_any(name, ("车", "驾", "打车")):
        return "🚗"
    return EMOJI_BY_TRANSPORT_MODE.get(event.transport_mode, "🛣️")


def _contains_any(source: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in source for keyword in keywords)


def _wrap_parts(parts: list[str], max_width: int) -> list[str]:
    """按最大宽度换行，保持箭头连接。"""

    lines: list[str] = []
    current = ""
    for part in parts:
        candidate = part if not current else f"{current} -> {part}"
        if len(candidate) <= max_width or not current:
            current = candidate
            continue
        lines.append(current)
        current = part
    if current:
        lines.append(current)
    return [
        line.strip()
        for line in lines
    ]
