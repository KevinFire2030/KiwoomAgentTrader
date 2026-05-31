from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.automation.krx_calendar import KRXHolidayCalendar, load_krx_holidays_from_env
from app.config.dotenv import load_dotenv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load Korea/KRX holiday calendar from API/cache/manual config.")
    parser.add_argument("--year", type=int, action="append", help="Year to load. Can be repeated. Default: current and next year from env helper.")
    parser.add_argument("--source", choices=["auto", "api", "manual"], default=None, help="Override KRX_HOLIDAY_SOURCE")
    parser.add_argument("--cache-dir", default=None, help="Override cache directory")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    if args.year:
        calendar = KRXHolidayCalendar(cache_dir=Path(args.cache_dir) if args.cache_dir else Path("data") / "calendar")
        result = calendar.load(years=tuple(args.year), source=args.source or "auto")
    else:
        result = load_krx_holidays_from_env()

    print(f"source: {result.source}")
    print(f"years: {','.join(str(year) for year in result.years)}")
    print(f"count: {len(result.holidays)}")
    for warning in result.warnings:
        print(f"warning: {warning}")
    for day in sorted(result.holidays):
        print(day)


if __name__ == "__main__":
    main()
