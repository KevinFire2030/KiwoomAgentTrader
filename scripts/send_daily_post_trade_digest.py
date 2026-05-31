from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.analysis.post_trade_digest import PostTradeDigestBuilder, format_post_trade_digest
from app.config.dotenv import load_dotenv
from app.storage.repository import TradingRepository
from app.telegram.client import TelegramBotClient, TelegramTarget

KST = ZoneInfo("Asia/Seoul")


class NoSendTelegramClient:
    def send_message(self, target: TelegramTarget, text: str) -> dict:
        return {"ok": True, "dry_run": True, "target": target.chat_id}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and optionally send a daily Kiwoom post-trade digest.")
    parser.add_argument("--date", default=None, help="KST date YYYY-MM-DD, default today in KST")
    parser.add_argument("--db", default=None, help="Trading SQLite DB path, default KIWOOM_TRADING_DB or data/trading.db")
    parser.add_argument("--no-send", action="store_true", help="Do not send Telegram; print digest only")
    parser.add_argument("--chat-id", default=None, help="Telegram chat id, default KIWOOM_TELEGRAM_CHAT_ID or TELEGRAM_CHAT_ID")
    parser.add_argument("--thread-id", type=int, default=None, help="Telegram topic/thread id")
    return parser.parse_args()


def main() -> None:
    load_dotenv()
    args = parse_args()
    date_key = args.date or datetime.now(tz=KST).date().isoformat()
    db_path = Path(args.db or os.getenv("KIWOOM_TRADING_DB", str(Path("data") / "trading.db")))
    digest = PostTradeDigestBuilder(TradingRepository(db_path)).build_for_date(date_key)
    text = format_post_trade_digest(digest)

    notification_sent = False
    if not args.no_send:
        chat_id = args.chat_id or os.getenv("KIWOOM_TELEGRAM_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID")
        if not chat_id:
            raise SystemExit("Telegram chat id is required unless --no-send is used")
        thread_raw = args.thread_id
        if thread_raw is None:
            env_thread = os.getenv("KIWOOM_TELEGRAM_THREAD_ID") or os.getenv("TELEGRAM_MESSAGE_THREAD_ID")
            thread_raw = int(env_thread) if env_thread else None
        client = TelegramBotClient(os.getenv("TELEGRAM_BOT_TOKEN", ""))
        client.send_message(TelegramTarget(chat_id=str(chat_id), message_thread_id=thread_raw), text)
        notification_sent = True

    print(text)
    print(f"notification_sent: {notification_sent}")


if __name__ == "__main__":
    main()
