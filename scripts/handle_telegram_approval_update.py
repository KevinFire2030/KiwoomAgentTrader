from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config.dotenv import load_dotenv
from app.telegram.approval_gateway import TelegramApprovalConfig, TelegramApprovalGateway
from app.telegram.client import TelegramBotClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Handle one Telegram update JSON for Kiwoom trade approval.")
    parser.add_argument("--send", action="store_true", help="Send Telegram reply via Bot API. Default prints only.")
    parser.add_argument("--mode", default=None, help="Override approval mode, e.g. paper")
    args = parser.parse_args()

    load_dotenv()
    load_dotenv(Path.home() / ".hermes" / ".env")
    update = json.load(sys.stdin)
    config = TelegramApprovalConfig.from_env()
    if args.mode:
        config = TelegramApprovalConfig(
            db_path=config.db_path,
            mode=args.mode,
            chat_id=config.chat_id,
            message_thread_id=config.message_thread_id,
            bot_token=config.bot_token,
        )
    client = TelegramBotClient(config.bot_token) if args.send and config.bot_token else None
    response = TelegramApprovalGateway(config, telegram_client=client).handle_update(update, send_reply=args.send)
    print(response.text)
    if response.handled and not response.should_reply:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
