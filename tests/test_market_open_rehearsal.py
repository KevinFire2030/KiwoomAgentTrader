import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class MarketOpenRehearsalTest(unittest.TestCase):
    def test_rehearsal_runs_read_only_commands_with_sample_fill_sync(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "trading.db"
            sample_path = Path(tmp) / "fills.json"
            sample_path.write_text("[]", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_market_open_rehearsal.py",
                    "--db",
                    str(db_path),
                    "--fill-sample-json",
                    str(sample_path),
                    "--skip-read-api",
                    "--skip-scan",
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("step: automation_status", result.stdout)
            self.assertIn("step: fill_sync_dry_run", result.stdout)
            self.assertIn("market_open_rehearsal: OK", result.stdout)
            self.assertIn("주문 API를 호출하지 않습니다", result.stdout)


if __name__ == "__main__":
    unittest.main()
