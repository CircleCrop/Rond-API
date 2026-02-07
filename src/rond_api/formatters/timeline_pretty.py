"""可读时间线格式化。"""

from __future__ import annotations

import unicodedata
from datetime import date, datetime, time, timedelta
from typing import Literal

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

CATEGORY_EMOJI_EXACT = {
    "家": "🏠",
    "学校": "🏫",
    "茶饮": "🥤",
    "餐厅": "🍽️",
    "银行": "🏦",
    "商场": "🛍️",
    "机厅": "🎮",
    "医院": "🏥",
    "病院": "🏥",
    "健身": "💪",
    "图书馆": "📚",
    "影院": "🎬",
    "博物馆": "🏛️",
    "酒店": "🏨",
    "超市": "🛒",
    "机场": "🛫",
    "别人家": "🏡",
}
LOCATION_TYPE_EMOJI = {
    0: "📍",
    1: "🛣️",
    2: "📌",
    3: "🏢",
}
POI_CATEGORY_EMOJI = {
    "MKPOICategoryFitnessCenter": "💪",
    "MKPOICategoryPublicTransport": "🚉",
    "MKPOICategoryCafe": "🥤",
    "MKPOICategoryRestaurant": "🍽️",
    "MKPOICategoryUniversity": "🏫",
    "MKPOICategorySchool": "🏫",
    "MKPOICategoryBeauty": "💇",
    "MKPOICategoryHotel": "🏨",
    "MKPOICategoryMovieTheater": "🎬",
    "MKPOICategoryPark": "🌳",
    "MKPOICategoryBakery": "🥐",
    "MKPOICategoryLandmark": "🗽",
    "MKPOICategoryMuseum": "🏛️",
    "MKPOICategorySpa": "🧖",
    "MKPOICategoryAirport": "🛫",
    "MKPOICategoryNationalMonument": "🏛️",
    "MKPOICategoryLibrary": "📚",
    "MKPOICategoryFortress": "🏰",
    "MKPOICategoryNationalPark": "🏞️",
    "MKPOICategoryMusicVenue": "🎵",
    "MKPOICategoryCastle": "🏰",
    "MKPOICategoryStore": "🛍️",
    "MKPOICategoryBank": "🏦",
    "MKPOICategoryATM": "🏧",
    "MKPOICategoryFoodMarket": "🛒",
    "MKPOICategoryConventionCenter": "🏛️",
    "MKPOICategoryTheater": "🎭",
    "MKPOICategoryPostOffice": "📮",
    "MKPOICategoryHospital": "🏥",
    "MKPOICategoryPharmacy": "💊",
}
KEYWORD_EMOJI_RULES: list[tuple[tuple[str, ...], str]] = [
    (("家", "宿舍", "小区"), "🏠"),
    (("学校", "大学", "学院", "校区"), "🏫"),
    (("车站", "地铁", "高铁", "火车", "铁路", "枢纽", "站"), "🚉"),
    (("机场", "航站", "空港"), "🛫"),
    (("酒店", "宾馆", "旅馆", "民宿"), "🏨"),
    (("餐厅", "饭", "面", "火锅", "烧烤", "寿司", "居酒屋", "吃"), "🍽️"),
    (("茶饮", "咖啡", "奶茶", "甜品"), "🥤"),
    (("商场", "商店", "超市", "便利店", "唐吉诃德"), "🛍️"),
    (("银行", "atm"), "🏦"),
    (("医院", "病院", "诊所", "药店", "医"), "🏥"),
    (("图书馆", "书店"), "📚"),
    (("健身", "体育", "球馆"), "💪"),
    (("博物馆", "美术馆", "展览馆"), "🏛️"),
    (("公园", "绿地"), "🌳"),
    (("影院", "电影院"), "🎬"),
    (("机厅", "电玩", "游戏"), "🎮"),
    (("办公室", "公司", "写字楼"), "🏢"),
]
DurationUnitStyle = Literal["compact", "cn", "en"]


def render_timeline_pretty(
    timeline: TimelineResult,
    emoji: bool = True,
    complex_mode: bool = False,
    duration_unit_style: DurationUnitStyle = "compact",
) -> str:
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
            lines.extend(
                _format_visit_event(
                    event,
                    query_date=timeline.query_date,
                    emoji=emoji,
                    complex_mode=complex_mode,
                    duration_unit_style=duration_unit_style,
                )
            )
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
            lines.extend(
                _format_movement_group(
                    movement_group,
                    next_visit,
                    emoji=emoji,
                    complex_mode=complex_mode,
                    duration_unit_style=duration_unit_style,
                )
            )
        lines.append("")

    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def _format_visit_event(
    event: VisitEvent,
    query_date: date,
    emoji: bool,
    complex_mode: bool,
    duration_unit_style: DurationUnitStyle,
) -> list[str]:
    end_text = "停留中" if event.is_ongoing else f"{event.departure_at:%Y-%m-%d %H:%M}"
    duration_text = _format_duration(
        event.arrival_at,
        event.departure_at,
        style=duration_unit_style,
    )
    marker_text = _visit_marker_text(
        event=event,
        query_date=query_date,
        duration_text=duration_text,
    )

    category_emoji = _category_emoji(
        event.category_name,
        event.location_name,
        event.location_type,
        event.poi_category,
        emoji=emoji,
    )
    if complex_mode:
        marker = category_emoji if emoji else "[visit]"
        category_part = event.category_name
        if event.tags:
            category_part = f"{category_part} 🏷️ {'、'.join(event.tags)}"
        detail_line = f"   {category_part} | {event.location_name}"
        lines = [
            f"{marker} {event.arrival_at:%Y-%m-%d %H:%M} -> {end_text} ({marker_text})",
            detail_line,
        ]
        return lines

    marker = "📍" if emoji else "[visit]"
    lines = [
        f"{marker} {event.arrival_at:%Y-%m-%d %H:%M} -> {end_text} ({marker_text})",
    ]
    lines.extend(
        [
            f"   地点: {event.location_name}",
            f"   分类: {category_emoji} {event.category_name}",
        ]
    )
    if event.tags:
        lines.append(f"   标签: {', '.join(event.tags)}")
    return lines


def _visit_marker_text(event: VisitEvent, query_date: date, duration_text: str) -> str:
    if event.arrival_at.date() == event.departure_at.date():
        return duration_text

    day_start = datetime.combine(query_date, time.min, tzinfo=event.arrival_at.tzinfo)
    day_end = day_start + timedelta(days=1)
    is_full_day = event.arrival_at <= day_start and event.departure_at >= day_end
    if is_full_day:
        return f"☀️ 全天 🌙 跨天 {duration_text}"
    return f"🌙 跨天 {duration_text}"


def _format_movement_group(
    group: list[MovementEvent],
    next_visit: VisitEvent | None,
    emoji: bool,
    complex_mode: bool,
    duration_unit_style: DurationUnitStyle,
) -> list[str]:
    dominant = max(group, key=lambda item: item.duration_minutes)
    marker = _movement_emoji(dominant, emoji=emoji)

    start_at = group[0].start_at
    end_at = group[-1].end_at
    total_duration_text = _format_duration(
        start_at.replace(second=0, microsecond=0),
        end_at.replace(second=0, microsecond=0),
        style=duration_unit_style,
    )

    from_location_name = group[0].from_location_name or "未知地点"
    to_location_name = group[-1].to_location_name
    if not to_location_name and next_visit is not None:
        to_location_name = next_visit.location_name
    if not to_location_name:
        to_location_name = "未知地点"

    transport_parts = [
        _movement_part_text(item, emoji=emoji, duration_unit_style=duration_unit_style)
        for item in group
    ]
    wrapped_transport_lines = _wrap_parts(transport_parts, max_width=64)

    lines = [
        f"{marker} {start_at:%Y-%m-%d %H:%M} -> {end_at:%Y-%m-%d %H:%M} ({total_duration_text})",
    ]
    if not complex_mode:
        lines.append(f"   路线: {from_location_name} -> {to_location_name}")

    if complex_mode:
        movement_prefix = "   "
        if wrapped_transport_lines:
            compact_lines = [f"{movement_prefix}{wrapped_transport_lines[0]}"]
            indent = " " * _display_width(movement_prefix)
            compact_lines.extend(f"{indent}{line}" for line in wrapped_transport_lines[1:])
            return compact_lines
        else:
            return [f"{movement_prefix}无"]

    transport_prefix = "   交通: "
    if wrapped_transport_lines:
        lines.append(f"{transport_prefix}{wrapped_transport_lines[0]}")
        indent = " " * _display_width(transport_prefix)
        lines.extend(f"{indent}{line}" for line in wrapped_transport_lines[1:])
    else:
        lines.append(f"{transport_prefix}无")
    return lines


def _movement_part_text(
    event: MovementEvent,
    emoji: bool,
    duration_unit_style: DurationUnitStyle,
) -> str:
    icon = _movement_emoji(event, emoji=emoji)
    duration_text = _format_duration(
        event.start_at,
        event.end_at,
        style=duration_unit_style,
    )
    if emoji:
        return f"{icon} {event.transport_name} ({duration_text})"
    return f"{event.transport_name} ({duration_text})"


def _movement_emoji(event: MovementEvent, emoji: bool) -> str:
    if not emoji:
        return "[movement]"

    name = event.transport_name
    if _contains_any(name, ("地铁", "电车", "高铁", "火车", "轻轨", "有轨", "公交")):
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


def _category_emoji(
    category_name: str,
    location_name: str,
    location_type: int | None,
    poi_category: str | None,
    emoji: bool,
) -> str:
    if not emoji:
        return "[分类]"

    emoji_value = LOCATION_TYPE_EMOJI.get(location_type, "📂")

    if poi_category:
        poi_emoji = POI_CATEGORY_EMOJI.get(poi_category)
        if poi_emoji:
            emoji_value = poi_emoji

    keyword_text = f"{category_name} {location_name}".lower()
    for keywords, icon in KEYWORD_EMOJI_RULES:
        if any(keyword in keyword_text for keyword in keywords):
            emoji_value = icon
            break

    direct = CATEGORY_EMOJI_EXACT.get(category_name)
    if direct:
        emoji_value = direct
    return emoji_value


def _contains_any(source: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in source for keyword in keywords)


def _wrap_parts(parts: list[str], max_width: int) -> list[str]:
    """按显示宽度换行，保持箭头连接。"""

    lines: list[str] = []
    current = ""
    delimiter = " -> "
    continuation_delimiter = "-> "
    delimiter_width = _display_width(delimiter)
    continuation_width = _display_width(continuation_delimiter)
    for part in parts:
        part_width = _display_width(part)
        if not current:
            current = part
            continue

        candidate_width = _display_width(current) + delimiter_width + part_width
        if candidate_width <= max_width:
            current = f"{current}{delimiter}{part}"
            continue

        lines.append(current)
        if continuation_width + part_width <= max_width:
            current = f"{continuation_delimiter}{part}"
        else:
            current = part

    if current:
        lines.append(current)
    return [line.strip() for line in lines]


def _display_width(text: str) -> int:
    width = 0
    for char in text:
        if unicodedata.combining(char):
            continue
        east_asian = unicodedata.east_asian_width(char)
        width += 2 if east_asian in {"W", "F"} else 1
    return width


def _format_duration(
    start_at: datetime,
    end_at: datetime,
    style: DurationUnitStyle,
) -> str:
    total_minutes = int(max((end_at - start_at).total_seconds(), 0) // 60)
    days = total_minutes // (24 * 60)
    hours = (total_minutes % (24 * 60)) // 60
    minutes = total_minutes % 60

    if style == "cn":
        return _format_duration_cn(days, hours, minutes)
    if style == "en":
        return _format_duration_en(days, hours, minutes)
    return _format_duration_compact(days, hours, minutes)


def _format_duration_compact(days: int, hours: int, minutes: int) -> str:
    parts: list[str] = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts)


def _format_duration_cn(days: int, hours: int, minutes: int) -> str:
    parts: list[str] = []
    if days > 0:
        parts.append(f"{days} 天")
    if hours > 0:
        parts.append(f"{hours} 时")
    parts.append(f"{minutes} 分")
    return " ".join(parts)


def _format_duration_en(days: int, hours: int, minutes: int) -> str:
    parts: list[str] = []
    if days > 0:
        parts.append(f"{days} {_plural(days, 'day')}")
    if hours > 0:
        parts.append(f"{hours} {_plural(hours, 'hour')}")
    parts.append(f"{minutes} {_plural(minutes, 'minute')}")
    return " ".join(parts)


def _plural(value: int, unit: str) -> str:
    return unit if value == 1 else f"{unit}s"
