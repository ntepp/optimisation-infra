"""
CLI inbound adapter.

Parses argv, picks a MetricSource, builds the TimeWindow, runs the pipeline,
emits the report via the configured sink. Kept thin: no business logic.
"""
from __future__ import annotations

import argparse
import sys
from datetime import timedelta

from src.adapters.inbound.runner import run_analysis
from src.adapters.outbound.sinks.json_file_sink import JsonFileSink
from src.adapters.outbound.sinks.stdout_sink import StdoutSink
from src.domain.metrics import TimeWindow, _parse_utc
from src.infrastructure.config import Settings
from src.infrastructure.container import build_source


def _build_window(args, points_provider) -> TimeWindow | None:
    if args.mode == "single":
        return None
    if args.all_records:
        return TimeWindow.unbounded()
    anchor_ts = points_provider()
    if anchor_ts is None:
        return TimeWindow.unbounded()
    return TimeWindow(start=anchor_ts, end=anchor_ts + timedelta(minutes=args.window))


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Infrastructure Optimisation Pipeline")
    parser.add_argument("--mode", choices=["single", "batch"], default="batch")
    parser.add_argument("--source", choices=["file", "stdin", "inline"], default="file",
                        help="Where to read JSON metrics from")
    parser.add_argument("--input", default="docs/rapport.json", help="Path to JSON file (--source=file)")
    parser.add_argument("--json", dest="inline_json", default=None,
                        help="Inline JSON string (--source=inline)")
    parser.add_argument("--index", type=int, default=0, help="Record index (single mode only)")
    parser.add_argument("--window", type=int, default=120, help="Batch window in minutes")
    parser.add_argument("--all", dest="all_records", action="store_true", help="Process all records")
    return parser.parse_args(argv)


def run_cli(argv: list[str] | None = None) -> dict:
    args = _parse_args(argv)
    settings = Settings.from_env()
    source = build_source(args.source, input_path=args.input, inline_json=args.inline_json)

    all_points = list(source.fetch(None))
    if not all_points:
        sys.exit("Error: no records found in source.")

    if args.mode == "single":
        if args.index >= len(all_points):
            sys.exit(f"Error: index {args.index} out of range ({len(all_points)} records).")
        selected = [all_points[args.index]]
        window: TimeWindow | None = None
    elif args.all_records:
        selected = all_points
        window = TimeWindow.unbounded()
    else:
        anchor = all_points[0].timestamp
        window = TimeWindow(start=anchor, end=anchor + timedelta(minutes=args.window))
        selected = [p for p in all_points if window.contains(p.timestamp)]

    print(f"Processing {len(selected)} record(s)…", file=sys.stderr)

    # Re-wrap the selected slice as an in-memory source for the runner.
    from src.adapters.outbound.sources.in_memory import InMemorySource
    selected_source = InMemorySource(selected)

    report = run_analysis(
        source=selected_source,
        settings=settings,
        window=None,
        mode_label=args.mode,
    )

    StdoutSink().emit(report)
    path = JsonFileSink(settings.output_dir).emit(report)
    print(f"\nReport saved -> {path}", file=sys.stderr)
    return report


if __name__ == "__main__":
    run_cli()
