import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.automation.krx_calendar import KRXHolidayCalendar, load_krx_holidays_from_env


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class KRXHolidayCalendarTest(unittest.TestCase):
    def test_fetches_api_holidays_and_writes_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            calendar = KRXHolidayCalendar(cache_dir=Path(tmp), api_template="https://example.test/{year}")
            payload = [{"date": "2026-01-01", "localName": "New Year's Day"}, {"date": "2026-02-17"}]

            with patch("urllib.request.urlopen", return_value=FakeResponse(payload)):
                result = calendar.load(years=(2026,), manual_holidays={"20260216"})

            self.assertEqual(result.source, "api+manual")
            self.assertIn("2026-01-01", result.holidays)
            self.assertIn("2026-02-16", result.holidays)
            self.assertTrue((Path(tmp) / "kr_holidays_2026.json").exists())

    def test_falls_back_to_cache_when_api_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache_path = Path(tmp) / "kr_holidays_2026.json"
            cache_path.write_text(json.dumps({"holidays": ["2026-03-01"]}), encoding="utf-8")
            calendar = KRXHolidayCalendar(cache_dir=Path(tmp), api_template="https://example.test/{year}")

            with patch("urllib.request.urlopen", side_effect=OSError("network down")):
                result = calendar.load(years=(2026,))

            self.assertEqual(result.source, "cache")
            self.assertIn("2026-03-01", result.holidays)
            self.assertTrue(result.warnings)

    def test_manual_source_does_not_call_api(self):
        with tempfile.TemporaryDirectory() as tmp:
            calendar = KRXHolidayCalendar(cache_dir=Path(tmp))

            with patch("urllib.request.urlopen") as urlopen:
                result = calendar.load(years=(2026,), manual_holidays={"20260101"}, source="manual")

            urlopen.assert_not_called()
            self.assertEqual(result.source, "manual")
            self.assertEqual(result.holidays, frozenset({"2026-01-01"}))

    def test_env_loader_combines_years_and_manual_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {
                "KRX_HOLIDAY_SOURCE": "manual",
                "KRX_HOLIDAYS": "20260101,20260216",
                "KRX_HOLIDAY_YEARS": "2026,2027",
                "KRX_HOLIDAY_CACHE_DIR": tmp,
            }
            with patch.dict(os.environ, env, clear=False):
                result = load_krx_holidays_from_env()

            self.assertEqual(result.years, (2026, 2027))
            self.assertEqual(result.source, "manual")
            self.assertIn("2026-02-16", result.holidays)


if __name__ == "__main__":
    unittest.main()
