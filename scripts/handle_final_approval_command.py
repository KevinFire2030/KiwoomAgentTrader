from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.approval.workflow import ApprovalWorkflow
from app.config.dotenv import load_dotenv
from app.config.settings import KiwoomSettings, SettingsError
from app.kiwoom.auth import KiwoomAuthClient
from app.kiwoom.client import KiwoomRestClient
from app.kiwoom.orders import KiwoomOrderClient
from app.storage.repository import TradingRepository


def build_order_client(settings: KiwoomSettings) -> KiwoomOrderClient:
    auth = KiwoomAuthClient(settings.base_url, settings.app_key, settings.secret_key)
    token_cache = {}

    def token_provider():
        if "token" not in token_cache:
            token_cache["token"] = auth.issue_token()
        return token_cache["token"]

    return KiwoomOrderClient(KiwoomRestClient(settings.base_url, settings.app_key, token_provider))


def main() -> None:
    if len(sys.argv) < 2:
        print("사용법: python3 scripts/handle_final_approval_command.py '최종승인 TT-...'")
        raise SystemExit(2)

    load_dotenv()
    try:
        settings = KiwoomSettings.from_env()
    except SettingsError as exc:
        print(f"설정 오류: {exc}")
        print("실주문 제출은 차단됩니다. .env를 확인하세요.")
        raise SystemExit(2)

    repo = TradingRepository(Path(os.getenv("KIWOOM_TRADING_DB", str(Path("data") / "trading.db"))))
    repo.initialize()
    workflow = ApprovalWorkflow(
        repo,
        order_client=build_order_client(settings),
        enable_live_trading=settings.trading_mode == "live_manual" and settings.enable_live_trading,
    )
    result = workflow.handle_text(sys.argv[1], mode="live_manual")
    print(result.message)
    if not result.accepted:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
