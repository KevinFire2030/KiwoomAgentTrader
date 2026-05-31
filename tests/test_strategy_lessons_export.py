import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.analysis.strategy_lessons import StrategyLessonExporter, build_strategy_lessons_markdown
from app.storage.repository import PostTradeAnalysisRecord, TradingRepository

KST = ZoneInfo("Asia/Seoul")


def record_analysis(
    repo: TradingRepository,
    ticket_id: str,
    symbol: str,
    outcome: str,
    pnl: int,
    created_at: datetime,
    lessons: list[str],
) -> None:
    repo.record_post_trade_analysis(
        PostTradeAnalysisRecord(
            ticket_id=ticket_id,
            run_id=f"run-{ticket_id}",
            symbol=symbol,
            outcome=outcome,
            realized_pnl_krw=pnl,
            summary=f"{ticket_id} summary",
            lessons=lessons,
            created_at=created_at,
        )
    )


class StrategyLessonExportTest(unittest.TestCase):
    def test_builds_markdown_grouped_by_kst_date_symbol_and_outcome_with_ticket_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = TradingRepository(Path(tmp) / "trading.db")
            repo.initialize()
            record_analysis(
                repo,
                "TT-loss-001",
                "498270",
                "loss",
                -8_000,
                datetime(2026, 6, 1, 15, 0, tzinfo=KST),
                ["손절 조건 재검토", "위험 한도 확인"],
            )
            record_analysis(
                repo,
                "TT-loss-002",
                "498270",
                "loss",
                -2_000,
                datetime(2026, 6, 1, 15, 30, tzinfo=KST),
                ["손절 조건 재검토"],
            )
            record_analysis(
                repo,
                "TT-win-001",
                "498270",
                "win",
                12_000,
                datetime(2026, 5, 31, 16, 30, tzinfo=ZoneInfo("UTC")),
                ["진입 규칙 보존"],
            )

            markdown = build_strategy_lessons_markdown(repo, generated_at=datetime(2026, 6, 2, 8, 0, tzinfo=KST))

            self.assertIn("# Kiwoom Agent Trader Strategy Lessons", markdown)
            self.assertIn("Generated at: 2026-06-02 08:00:00 KST", markdown)
            self.assertIn("## 2026-06-01 / 498270 / loss", markdown)
            self.assertIn("## 2026-06-01 / 498270 / win", markdown)
            self.assertIn("Tickets: `TT-loss-001`, `TT-loss-002`", markdown)
            self.assertIn("Total realized P&L: -10,000원", markdown)
            self.assertIn("- 손절 조건 재검토 (2회; tickets: `TT-loss-001`, `TT-loss-002`)", markdown)
            self.assertIn("- 위험 한도 확인 (1회; tickets: `TT-loss-001`)", markdown)
            self.assertIn("Tickets: `TT-win-001`", markdown)
            self.assertNotIn("63***96", markdown)

    def test_export_preserves_existing_manual_notes_and_replaces_generated_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = TradingRepository(Path(tmp) / "trading.db")
            repo.initialize()
            record_analysis(repo, "TT-001", "498270", "flat", 0, datetime(2026, 6, 1, 10, 0, tzinfo=KST), ["수수료 확인"])
            output_path = Path(tmp) / "strategy-lessons.md"
            output_path.write_text("# Manual Notes\n\nkeep this operator note\n\n", encoding="utf-8")

            result = StrategyLessonExporter(repo).export(output_path, generated_at=datetime(2026, 6, 2, 8, 0, tzinfo=KST))
            second = StrategyLessonExporter(repo).export(output_path, generated_at=datetime(2026, 6, 2, 9, 0, tzinfo=KST))
            text = output_path.read_text(encoding="utf-8")

            self.assertEqual(result.groups_exported, 1)
            self.assertEqual(second.groups_exported, 1)
            self.assertIn("keep this operator note", text)
            self.assertEqual(text.count("<!-- KIWOOM_STRATEGY_LESSONS:START -->"), 1)
            self.assertEqual(text.count("## 2026-06-01 / 498270 / flat"), 1)
            self.assertIn("Generated at: 2026-06-02 09:00:00 KST", text)

    def test_cli_exports_strategy_lessons_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "trading.db"
            output_path = Path(tmp) / "strategy-lessons.md"
            repo = TradingRepository(db_path)
            repo.initialize()
            record_analysis(repo, "TT-cli", "498270", "win", 3_000, datetime(2026, 6, 1, 10, 0, tzinfo=KST), ["CLI export"])

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/export_strategy_lessons.py",
                    "--db",
                    str(db_path),
                    "--output",
                    str(output_path),
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("groups_exported: 1", result.stdout)
            self.assertIn("TT-cli", output_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
