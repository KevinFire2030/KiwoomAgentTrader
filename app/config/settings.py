from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

TradingMode = Literal["advisory", "paper", "live_manual", "live_auto"]


class SettingsError(ValueError):
    pass


@dataclass(frozen=True)
class KiwoomSettings:
    app_key: str
    secret_key: str
    account_no: str
    base_url: str = "https://api.kiwoom.com"
    trading_mode: TradingMode = "paper"
    enable_live_trading: bool = False

    @classmethod
    def from_env(cls) -> "KiwoomSettings":
        app_key = _required_env("KIWOOM_APP_KEY")
        secret_key = _required_env("KIWOOM_SECRET_KEY")
        account_no = _required_env("KIWOOM_ACCOUNT_NO")
        base_url = os.getenv("KIWOOM_BASE_URL", cls.base_url).rstrip("/")
        trading_mode = os.getenv("TRADING_MODE", "paper")
        if trading_mode not in {"advisory", "paper", "live_manual", "live_auto"}:
            raise SettingsError(f"Unsupported TRADING_MODE: {trading_mode}")
        enable_live_trading = _env_bool("ENABLE_LIVE_TRADING", False)
        if trading_mode.startswith("live") and not enable_live_trading:
            raise SettingsError("Live trading mode requires ENABLE_LIVE_TRADING=true")
        return cls(
            app_key=app_key,
            secret_key=secret_key,
            account_no=account_no,
            base_url=base_url,
            trading_mode=trading_mode,  # type: ignore[arg-type]
            enable_live_trading=enable_live_trading,
        )


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SettingsError(f"Missing required environment variable: {name}")
    return value


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}
