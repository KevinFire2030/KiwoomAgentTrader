import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.analysis.post_trade_digest import PostTradeDigestBuilder, format_post_trade_digest
from app.storage.repository import PostTradeAnalysisRecord, TradingRepository

KST = ZoneInfo("Asia/Seoul")


def record_analysis(
    repo: TradingRepository,
    ticket_id: str,
    outcome: str,
    pnl: int,
    created_at: datetime,
    lessons: list[str] | None = None,
) -> None:
    repo.record_post_trade_analysis(
        PostTradeAnalysisRecord(
            ticket_id=ticket_id,
            run_id=f"run-{ticket_id}",
            symbol="498270",
            outcome=outcome,
            realized_pnl_krw=pnl,
            summary=f"{ticket_id} summary",
            lessons=lessons or [],
            created_at=created_at,
        )
    )


class PostTradeDigestTest(unittest.TestCase):
    def test_aggregates_post_trade_analyses_for_one_kst_day(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = TradingRepository(Path(tmp) / "trading.db")
            repo.initialize()
            # Previous KST day: should be ignored.
            record_analysis(repo, "TT-prev", "win", 99_000, datetime(2026, 5, 31, 23, 59, tzinfo=KST), ["ignored"])
            # Target KST day, including one UTC timestamp that falls on 2026-06-01 KST.
            record_analysis(repo, "TT-win", "win", 12_000, datetime(2026, 6, 1, 9, 30, tzinfo=KST), ["진입 규칙 보존", "위험 한도 확인"])
            record_analysis(repo, "TT-loss", "loss", -8_000, datetime(2026, 6, 1, 15, 0, tzinfo=KST), ["손절 조건 재검토", "위험 한도 확인"])
            record_analysis(repo, "TT-flat", "flat", 0, datetime(2026, 5, 31, 16, 30, tzinfo=ZoneInfo("UTC")), ["수수료 확인"])
            # Next KST day: should be ignored.
            record_analysis(repo, "TT-next", "loss", -1_000, datetime(2026, 6, 2, 0, 0, tzinfo=KST), ["ignored"])
            repo.set_runtime_state("circuit_breaker", "on", "daily loss guard")

            digest = PostTradeDigestBuilder(repo).build_for_date("2026-06-01")

            self.assertEqual(digest.date_kst, "2026-06-01")
            self.assertEqual(digest.ticket_count, 3)
            self.assertEqual(digest.total_realized_pnl_krw, 4_000)
            self.assertEqual(digest.outcome_counts, {"win": 1, "loss": 1, "flat": 1})
            self.assertEqual(digest.best_ticket_id, "TT-win")
            self.assertEqual(digest.best_pnl_krw, 12_000)
            self.assertEqual(digest.worst_ticket_id, "TT-loss")
            self.assertEqual(digest.worst_pnl_krw, -8_000)
            self.assertEqual(digest.circuit_breaker_state, "on")
            self.assertIn("daily loss guard", digest.circuit_breaker_reason)
            self.assertEqual(digest.top_lessons[0], "위험 한도 확인")
            self.assertNotIn("ignored", digest.top_lessons)

    def test_formats_digest_for_telegram_with_signed_krw_and_empty_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = TradingRepository(Path(tmp) / "trading.db")
            repo.initialize()

            digest = PostTradeDigestBuilder(repo).build_for_date("2026-06-01")
            text = format_post_trade_digest(digest)

            self.assertIn("[Kiwoom Agent Trader 일일 사후 분석]", text)
            self.assertIn("날짜: 2026-06-01 KST", text)
            self.assertIn("티켓 수: 0", text)
            self.assertIn("총 실현손익: 0원", text)
            self.assertIn("win/loss/flat: 0/0/0", text)
            self.assertIn("분석된 거래가 없습니다", text)
            self.assertIn("Circuit breaker: off", text)

    def test_no_send_cli_prints_digest_without_requiring_telegram_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "trading.db"
            repo = TradingRepository(db_path)
            repo.initialize()
            record_analysis(repo, "TT-cli", "win", 3_000, datetime(2026, 6, 1, 10, 0, tzinfo=KST), ["CLI smoke"])

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/send_daily_post_trade_digest.py",
                    "--date",
                    "2026-06-01",
                    "--db",
                    str(db_path),
                    "--no-send",
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("TT-cli", result.stdout)
            self.assertIn("+3,000원", result.stdout)
            self.assertIn("notification_sent: False", result.stdout)


if __name__ == "__main__":
    unittest.main()
