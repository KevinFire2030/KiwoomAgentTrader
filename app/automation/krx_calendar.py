from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
DEFAULT_HOLIDAY_API_TEMPLATE = "https://date.nager.at/api/v3/PublicHolidays/{year}/KR"


@dataclass(frozen=True)
class HolidayLoadResult:
    holidays: frozenset[str]
    source: str
    years: tuple[int, ...]
    warnings: tuple[str, ...] = ()


class KRXHolidayCalendar:
    """Load Korea/KRX holiday dates with a safe cache + manual fallback.

    The public API source is intentionally used only for holiday *dates* and is
    cached locally. If network/API fetch fails, scheduler safety falls back to
    cached data and/or manually configured KRX_HOLIDAYS instead of pretending a
    day is open.
    """

    def __init__(
        self,
        *,
        cache_dir: Path = Path("data") / "calendar",
        api_template: str = DEFAULT_HOLIDAY_API_TEMPLATE,
        timeout_seconds: int = 10,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.api_template = api_template
        self.timeout_seconds = timeout_seconds

    def load(
        self,
        *,
        years: list[int] | tuple[int, ...],
        manual_holidays: set[str] | frozenset[str] | None = None,
        source: str = "auto",
    ) -> HolidayLoadResult:
        normalized_manual = frozenset(_normalize_holiday(value) for value in (manual_holidays or set()) if value)
        if source == "manual":
            return HolidayLoadResult(normalized_manual, "manual", tuple(years))
        if source not in {"auto", "api"}:
            raise ValueError(f"Unsupported KRX holiday source: {source}")

        warnings: list[str] = []
        loaded: set[str] = set(normalized_manual)
        used_sources: set[str] = {"manual"} if normalized_manual else set()
        for year in years:
            try:
                year_dates = self._fetch_year(year)
                if year_dates:
                    loaded.update(year_dates)
                    used_sources.add("api")
                    self._write_cache(year, year_dates)
                    continue
                warnings.append(f"{year}: API returned no holidays")
            except Exception as exc:  # pragma: no cover - exact network exceptions vary
                warnings.append(f"{year}: API fetch failed: {exc}")

            cached = self._read_cache(year)
            if cached:
                loaded.update(cached)
                used_sources.add("cache")
            elif source == "api":
                warnings.append(f"{year}: no cache fallback available")

        source_label = "+".join(sorted(used_sources)) if used_sources else "empty"
        return HolidayLoadResult(frozenset(sorted(loaded)), source_label, tuple(years), tuple(warnings))

    def _fetch_year(self, year: int) -> set[str]:
        url = self.api_template.format(year=year)
        request = urllib.request.Request(url, headers={"User-Agent": "KiwoomAgentTrader/1.0"})
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            raw = response.read().decode("utf-8")
        data = json.loads(raw)
        if not isinstance(data, list):
            raise ValueError(f"Unexpected holiday API payload for {year}: {type(data).__name__}")
        dates: set[str] = set()
        for item in data:
            if isinstance(item, dict) and isinstance(item.get("date"), str):
                dates.add(_normalize_holiday(item["date"]))
        return dates

    def _cache_path(self, year: int) -> Path:
        return self.cache_dir / f"kr_holidays_{year}.json"

    def _write_cache(self, year: int, holidays: set[str]) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "year": year,
            "source": self.api_template.format(year=year),
            "fetched_at": datetime.now(tz=KST).isoformat(),
            "holidays": sorted(holidays),
        }
        self._cache_path(year).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _read_cache(self, year: int) -> set[str]:
        path = self._cache_path(year)
        if not path.exists():
            return set()
        data = json.loads(path.read_text(encoding="utf-8"))
        holidays = data.get("holidays", [])
        if not isinstance(holidays, list):
            return set()
        return {_normalize_holiday(str(value)) for value in holidays if value}


def load_krx_holidays_from_env(today: date | None = None) -> HolidayLoadResult:
    today = today or datetime.now(tz=KST).date()
    manual = frozenset(_normalize_holiday(value) for value in _split_csv(os.getenv("KRX_HOLIDAYS", "")))
    years = _years_from_env(today.year)
    source = os.getenv("KRX_HOLIDAY_SOURCE", "auto").strip().lower() or "auto"
    cache_dir = Path(os.getenv("KRX_HOLIDAY_CACHE_DIR", str(Path("data") / "calendar")))
    timeout_seconds = int(os.getenv("KRX_HOLIDAY_TIMEOUT_SECONDS", "10"))
    calendar = KRXHolidayCalendar(cache_dir=cache_dir, timeout_seconds=timeout_seconds)
    return calendar.load(years=years, manual_holidays=manual, source=source)


def _years_from_env(default_year: int) -> tuple[int, ...]:
    raw = os.getenv("KRX_HOLIDAY_YEARS", "").strip()
    if not raw:
        return (default_year, default_year + 1)
    years = []
    for value in _split_csv(raw):
        years.append(int(value))
    return tuple(sorted(set(years)))


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _normalize_holiday(value: str) -> str:
    value = value.strip()
    if len(value) == 8 and value.isdigit():
        return f"{value[:4]}-{value[4:6]}-{value[6:]}"
    return value
