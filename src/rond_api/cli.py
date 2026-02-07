"""CLI 入口。"""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from rond_api.config import ConfigError
from rond_api.db.sqlite_client import DatabaseReadError
from rond_api.domain.timeline_types import OutputMode, TimelineResult
from rond_api.formatters.timeline_json import render_timeline_json
from rond_api.formatters.timeline_pretty import render_timeline_pretty
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
        required=True,
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

    output_mode: OutputMode = output
    _render_output(timeline=timeline, output=output_mode, emoji=not args.no_emoji)
    return 0


def _render_output(
    timeline: TimelineResult,
    output: OutputMode,
    emoji: bool,
) -> None:
    if output in ("pretty", "both"):
        print(render_timeline_pretty(timeline, emoji=emoji))
    if output == "both":
        print()
    if output in ("json", "both"):
        print(render_timeline_json(timeline))


if __name__ == "__main__":
    raise SystemExit(main())
