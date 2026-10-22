"""CLI for deterministic 1D OHLCV checks."""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path

from .core import validate_candles


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="closed-candle-guard", description="Validate daily closed-candle OHLCV data")
    parser.add_argument("csv_file", type=Path, help="CSV containing open_time_utc,open,high,low,close,volume")
    parser.add_argument("--as-of", required=True, help="An ISO-8601 timestamp with timezone, e.g. 2026-10-20T00:05:00Z")
    parser.add_argument("--delay-seconds", type=int, default=300, help="Seconds after close before data is treated as known (default: 300)")
    args = parser.parse_args(argv)
    try:
        with args.csv_file.open(newline="", encoding="utf-8-sig") as stream:
            report = validate_candles(csv.DictReader(stream), as_of=args.as_of, delay_seconds=args.delay_seconds)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    return 0 if report.ok else 1
