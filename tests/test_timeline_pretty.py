"""Timeline pretty formatter tests."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from rond_api.domain.timeline_types import MovementEvent, TimelineResult, VisitEvent
from rond_api.formatters.timeline_pretty import (
    _format_movement_group,
    _format_visit_event,
    _indent_followup,
    render_timeline_pretty,
)


def test_indent_followup_keeps_first_line_and_indents_rest() -> None:
    lines = ["first", "second", "", "third"]
    assert _indent_followup(lines) == ["first", "   second", "", "   third"]


def test_complex_visit_detail_line_uses_three_space_followup_indent() -> None:
    tz = ZoneInfo("UTC")
    event = VisitEvent(
        visit_id=1,
        location_name="示例社区A",
        category_name="家",
        location_type=0,
        poi_category=None,
        tags=["休息"],
        arrival_at=datetime(2026, 2, 7, 22, 7, tzinfo=tz),
        departure_at=datetime(2026, 2, 8, 0, 7, tzinfo=tz),
        is_cross_day=True,
    )

    lines = _format_visit_event(
        event,
        query_date=date(2026, 2, 7),
        emoji=True,
        complex_mode=True,
        duration_unit_style="cn",
    )

    assert len(lines) == 2
    assert lines[1].startswith("   ")
    assert not lines[1].startswith("    ")
    assert "家 🏷️ 休息 | 示例社区A" in lines[1]


def test_complex_movement_multiline_followup_indent_keeps_arrow() -> None:
    tz = ZoneInfo("UTC")
    start = datetime(2026, 2, 7, 19, 53, tzinfo=tz)
    group: list[MovementEvent] = []
    for index, name in enumerate(["步行", "地铁", "步行", "地铁", "步行"]):
        seg_start = start + timedelta(minutes=index * 10)
        seg_end = seg_start + timedelta(minutes=10)
        group.append(
            MovementEvent(
                movement_id=100 + index,
                transport_name=name,
                transport_mode="walk" if name == "步行" else "public_transit",
                start_at=seg_start,
                end_at=seg_end,
                duration_minutes=10,
                from_location_name=None,
                to_location_name=None,
            )
        )

    lines = _format_movement_group(
        group=group,
        next_visit=None,
        emoji=True,
        complex_mode=True,
        duration_unit_style="cn",
    )

    assert len(lines) >= 2
    assert lines[0].startswith("   ")
    assert lines[1].startswith("   ")
    assert lines[1].lstrip().startswith("-> ")


def test_tree_mode_adds_branch_prefix_and_keeps_followup_alignment() -> None:
    tz = ZoneInfo("UTC")
    events = [
        VisitEvent(
            visit_id=1,
            location_name="示例社区A",
            category_name="家",
            location_type=0,
            poi_category=None,
            tags=[],
            arrival_at=datetime(2026, 2, 7, 8, 0, tzinfo=tz),
            departure_at=datetime(2026, 2, 7, 9, 0, tzinfo=tz),
            is_cross_day=False,
        ),
        MovementEvent(
            movement_id=9,
            transport_name="机动车",
            transport_mode="drive",
            start_at=datetime(2026, 2, 7, 9, 0, tzinfo=tz),
            end_at=datetime(2026, 2, 7, 9, 20, tzinfo=tz),
            duration_minutes=20,
            from_location_name="示例社区A",
            to_location_name="示例商场B",
        ),
        VisitEvent(
            visit_id=2,
            location_name="示例商场B",
            category_name="商场",
            location_type=0,
            poi_category="MKPOICategoryStore",
            tags=["购物"],
            arrival_at=datetime(2026, 2, 7, 9, 30, tzinfo=tz),
            departure_at=datetime(2026, 2, 7, 10, 30, tzinfo=tz),
            is_cross_day=False,
        ),
    ]
    timeline = TimelineResult(
        query_date=date(2026, 2, 7),
        timezone="中国/江苏",
        events=events,
    )

    output = render_timeline_pretty(
        timeline,
        emoji=True,
        complex_mode=True,
        duration_unit_style="cn",
        tree=True,
    )

    lines = output.splitlines()
    assert any(line.startswith("├─ ") for line in lines)
    assert any(line.startswith("└─ ") for line in lines)
    assert any(line.startswith("│     ") for line in lines)
    assert "│" in lines
    movement_line = next(line for line in lines if line.startswith("├┈ "))
    assert not movement_line.startswith("├┈    ")
