from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.analysis.strategy_lessons import StrategyLessonExporter
from app.config.dotenv import load_dotenv
from app.storage.repository import TradingRepository


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export accumulated Kiwoom post-trade lessons to a strategy markdown artifact.")
    parser.add_argument("--db", default=None, help="Trading SQLite DB path, default KIWOOM_TRADING_DB or data/trading.db")
    parser.add_argument("--output", default="docs/strategy-lessons.md", help="Markdown output path")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    db_path = Path(args.db or os.getenv("KIWOOM_TRADING_DB", str(Path("data") / "trading.db")))
    output_path = Path(args.output)
    result = StrategyLessonExporter(TradingRepository(db_path)).export(output_path)
    print(f"output_path: {result.output_path}")
    print(f"groups_exported: {result.groups_exported}")


if __name__ == "__main__":
    main()
