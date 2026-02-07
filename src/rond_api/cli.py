"""CLI 入口。"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Sequence

from rond_api.config import ConfigError
from rond_api.db.sqlite_client import DatabaseReadError
from rond_api.domain.timeline_types import OutputMode, TimelineResult
from rond_api.formatters.timeline_json import render_timeline_json
from rond_api.formatters.timeline_pretty import DurationUnitStyle, render_timeline_pretty
from rond_api.services.timeline_service import get_timeline


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""

    parser = argparse.ArgumentParser(prog="rond-api", description="Rond API CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    timeline_parser = subparsers.add_parser(
        "timeline",
        help="Get timeline for a date.",
    )
    timeline_parser.add_argument(
        "--date",
        default="today",
        help="Date expression: today | yesterday | YYYY-MM-DD",
    )
    timeline_parser.add_argument(
        "--db-path",
        help="Path to Rond sqlite database file.",
    )
    timeline_parser.add_argument(
        "--output",
        choices=["pretty", "json", "both"],
        default="pretty",
        help="Output format.",
    )
    timeline_parser.add_argument(
        "--no-emoji",
        action="store_true",
        help="Disable emoji in pretty output.",
    )
    complex_group = timeline_parser.add_mutually_exclusive_group()
    complex_group.add_argument(
        "--complex",
        dest="complex_mode",
        action="store_true",
        help="Enable complex pretty mode.",
    )
    complex_group.add_argument(
        "--simple",
        dest="complex_mode",
        action="store_false",
        help="Disable complex pretty mode.",
    )
    timeline_parser.set_defaults(complex_mode=None)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI 主入口。"""

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "timeline":
        return _run_timeline(args)

    parser.print_help()
    return 1


def _run_timeline(args: argparse.Namespace) -> int:
    output = args.output
    assert output in {"pretty", "json", "both"}

    try:
        timeline = get_timeline(
            date_expr=args.date,
            db_path=args.db_path,
            output=output,
            emoji=not args.no_emoji,
        )
    except (ConfigError, DatabaseReadError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    complex_mode = _resolve_complex_mode(args.complex_mode)
    duration_unit_style = _resolve_duration_unit_style()
    output_mode: OutputMode = output
    _render_output(
        timeline=timeline,
        output=output_mode,
        emoji=not args.no_emoji,
        complex_mode=complex_mode,
        duration_unit_style=duration_unit_style,
    )
    return 0


def _render_output(
    timeline: TimelineResult,
    output: OutputMode,
    emoji: bool,
    complex_mode: bool,
    duration_unit_style: DurationUnitStyle,
) -> None:
    if output in ("pretty", "both"):
        print(
            render_timeline_pretty(
                timeline,
                emoji=emoji,
                complex_mode=complex_mode,
                duration_unit_style=duration_unit_style,
            )
        )
    if output == "both":
        print()
    if output in ("json", "both"):
        print(render_timeline_json(timeline))


def _resolve_complex_mode(cli_value: bool | None) -> bool:
    if cli_value is not None:
        return cli_value

    raw_env_value = os.getenv("complex")
    if raw_env_value is None:
        raw_env_value = os.getenv("COMPLEX", "0")
    raw_env_value = raw_env_value.strip().lower()
    return raw_env_value in {"1", "true", "yes", "on"}


def _resolve_duration_unit_style() -> DurationUnitStyle:
    raw = os.getenv("duration_units")
    if raw is None:
        raw = os.getenv("DURATION_UNITS", "compact")
    value = raw.strip().lower()

    if value in {"compact", "short", "dhm"}:
        return "compact"
    if value in {"cn", "zh", "chinese"}:
        return "cn"
    if value in {"en", "english", "words"}:
        return "en"
    return "compact"


if __name__ == "__main__":
    raise SystemExit(main())
