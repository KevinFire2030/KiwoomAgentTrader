import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app.automation.fill_sync import KiwoomFillSync, derive_realized_pnl_event_from_row
from app.storage.repository import TradingRepository

KST = ZoneInfo("Asia/Seoul")


class KiwoomFillSyncTest(unittest.TestCase):
    def test_derives_realized_pnl_event_from_broker_row_without_leaking_account(self):
        row = {
            "ord_no": "ORD-001",
            "cntr_no": "FILL-001",
            "stk_cd": "498270",
            "rlzt_pnl": "-55000",
            "trde_dt": "20260601",
            "trde_tm": "101530",
            "rmrk_nm": "ticket TT-live-001 account 63123456",
            "acnt_no": "63123456",
        }

        event = derive_realized_pnl_event_from_row(row)

        self.assertIsNotNone(event)
        if event is None:
            self.fail("expected realized pnl event")
        self.assertEqual(event.symbol, "498270")
        self.assertEqual(event.realized_pnl_krw, -55_000)
        self.assertEqual(event.source, "kiwoom_fill_sync")
        self.assertEqual(event.raw["ticket_id"], "TT-live-001")
        self.assertEqual(event.raw["broker_order_id"], "ORD-001")
        self.assertEqual(event.raw["broker_fill_id"], "FILL-001")
        self.assertNotIn("63123456", json.dumps(event.raw, ensure_ascii=False))

    def test_sync_is_idempotent_and_records_raw_snapshot_separately(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = TradingRepository(Path(tmp) / "trading.db")
            repo.initialize()
            rows = [
                {
                    "ord_no": "ORD-001",
                    "cntr_no": "FILL-001",
                    "stk_cd": "498270",
                    "rlzt_pnl": "+12000",
                    "trde_dt": "20260601",
                    "trde_tm": "101530",
                    "rmrk_nm": "TT-paper-001",
                },
                {
                    "ord_no": "ORD-002",
                    "cntr_no": "FILL-002",
                    "stk_cd": "498270",
                    "rlzt_pnl": "0",
                    "trde_dt": "20260601",
                    "trde_tm": "110000",
                    "rmrk_nm": "flat TT-paper-002",
                },
            ]

            first = KiwoomFillSync(repo).sync_rows(rows, apply=True, now=datetime(2026, 6, 1, 12, 0, tzinfo=KST))
            second = KiwoomFillSync(repo).sync_rows(rows, apply=True, now=datetime(2026, 6, 1, 12, 5, tzinfo=KST))

            self.assertEqual(first.rows_seen, 2)
            self.assertEqual(first.events_derived, 2)
            self.assertEqual(first.events_recorded, 2)
            self.assertEqual(first.duplicates_skipped, 0)
            self.assertEqual(second.events_recorded, 0)
            self.assertEqual(second.duplicates_skipped, 2)
            self.assertEqual(repo.count_realized_pnl_events(), 2)
            self.assertEqual(repo.count_broker_fill_sync_snapshots(), 2)

    def test_cli_dry_run_uses_sample_json_and_does_not_write_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "trading.db"
            sample_path = Path(tmp) / "fills.json"
            sample_path.write_text(
                json.dumps(
                    [
                        {
                            "ord_no": "ORD-CLI",
                            "cntr_no": "FILL-CLI",
                            "stk_cd": "498270",
                            "rlzt_pnl": "3000",
                            "trde_dt": "20260601",
                            "rmrk_nm": "TT-cli",
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/sync_kiwoom_fills.py",
                    "--db",
                    str(db_path),
                    "--sample-json",
                    str(sample_path),
                    "--dry-run",
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                check=False,
            )
            repo = TradingRepository(db_path)
            repo.initialize()

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("apply: False", result.stdout)
            self.assertIn("events_derived: 1", result.stdout)
            self.assertIn("events_recorded: 0", result.stdout)
            self.assertEqual(repo.count_realized_pnl_events(), 0)


if __name__ == "__main__":
    unittest.main()
