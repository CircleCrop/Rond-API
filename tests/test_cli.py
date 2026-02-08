"""CLI tests."""

from __future__ import annotations

import json
from datetime import date, datetime
from zoneinfo import ZoneInfo

import rond_api.cli as cli
from rond_api.cli import _resolve_tree_mode, main
from rond_api.domain.timeline_types import TimelineResult, VisitEvent


def test_cli_timeline_json_output(capsys, monkeypatch) -> None:
    tz = ZoneInfo("UTC")
    timeline = TimelineResult(
        query_date=date(2026, 1, 29),
        timezone="中国/上海",
        events=[
            VisitEvent(
                visit_id=1,
                location_name="示例地点A",
                category_name="示例分类",
                location_type=0,
                poi_category=None,
                tags=["测试标签"],
                arrival_at=datetime(2026, 1, 29, 9, 0, tzinfo=tz),
                departure_at=datetime(2026, 1, 29, 10, 0, tzinfo=tz),
                is_cross_day=False,
            )
        ],
    )

    monkeypatch.setattr(cli, "get_timeline", lambda **_: timeline)

    exit_code = main(
        [
            "timeline",
            "--date",
            "2026-01-29",
            "--output",
            "json",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    payload = json.loads(output)
    assert payload["query_date"] == "2026-01-29"
    assert isinstance(payload["events"], list)


def test_resolve_tree_mode_from_env(monkeypatch) -> None:
    monkeypatch.delenv("tree", raising=False)
    monkeypatch.delenv("TIMELINE_TREE", raising=False)
    monkeypatch.delenv("TREE", raising=False)
    assert _resolve_tree_mode(None) is False

    monkeypatch.setenv("tree", "on")
    assert _resolve_tree_mode(None) is True


def test_resolve_tree_mode_cli_overrides_env(monkeypatch) -> None:
    monkeypatch.setenv("tree", "on")
    assert _resolve_tree_mode(False) is False
