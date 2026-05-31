from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config.dotenv import load_dotenv
from app.telegram.approval_gateway import TelegramApprovalConfig, TelegramApprovalGateway
from app.telegram.client import TelegramBotClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Telegram long-polling approval bridge for Kiwoom trade tickets.")
    parser.add_argument("--once", action="store_true", help="Poll once and exit")
    parser.add_argument("--mode", default=None, help="Override approval mode, e.g. paper")
    parser.add_argument("--no-send", action="store_true", help="Process updates but do not send Telegram replies")
    parser.add_argument("--poll-timeout", type=int, default=30)
    args = parser.parse_args()

    load_dotenv()
    load_dotenv(Path.home() / ".hermes" / ".env")
    config = TelegramApprovalConfig.from_env()
    if args.mode:
        config = TelegramApprovalConfig(
            db_path=config.db_path,
            mode=args.mode,
            chat_id=config.chat_id,
            message_thread_id=config.message_thread_id,
            bot_token=config.bot_token,
        )
    client = TelegramBotClient(config.bot_token or "")
    gateway = TelegramApprovalGateway(config, telegram_client=None if args.no_send else client)

    offset: int | None = None
    print("Telegram approval bridge started. Press Ctrl+C to stop.")
    try:
        while True:
            updates = client.get_updates(offset=offset, timeout=args.poll_timeout)
            for update in updates:
                update_id = int(update["update_id"])
                offset = update_id + 1
                response = gateway.handle_update(update, send_reply=not args.no_send)
                if response.handled:
                    print(response.text)
            if args.once:
                break
            if not updates:
                time.sleep(1)
    except KeyboardInterrupt:
        print("Telegram approval bridge stopped.")


if __name__ == "__main__":
    main()
