from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from app.approval.commands import parse_approval_command
from app.approval.workflow import ApprovalWorkflow
from app.storage.repository import TradingRepository
from app.telegram.client import TelegramTarget


@dataclass(frozen=True)
class TelegramApprovalConfig:
    db_path: Path = Path("data") / "trading.db"
    mode: str = "paper"
    chat_id: str | None = None
    message_thread_id: int | None = None
    bot_token: str | None = None

    @classmethod
    def from_env(cls) -> "TelegramApprovalConfig":
        thread_raw = os.getenv("KIWOOM_TELEGRAM_THREAD_ID") or os.getenv("TELEGRAM_MESSAGE_THREAD_ID")
        return cls(
            db_path=Path(os.getenv("KIWOOM_TRADING_DB", str(Path("data") / "trading.db"))),
            mode=os.getenv("TRADING_MODE", "paper"),
            chat_id=os.getenv("KIWOOM_TELEGRAM_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID"),
            message_thread_id=int(thread_raw) if thread_raw else None,
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        )


@dataclass(frozen=True)
class TelegramApprovalResponse:
    handled: bool
    should_reply: bool
    chat_id: str | None
    message_thread_id: int | None
    text: str


class TelegramApprovalSender(Protocol):
    def send_message(self, target, text: str) -> dict[str, Any]:
        ...


class TelegramApprovalGateway:
    """Connect Telegram message updates to the approval workflow.

    Non approval/rejection messages are ignored so this can safely sit beside
    normal project chat traffic when connected to a dedicated bot/webhook.
    """

    def __init__(
        self,
        config: TelegramApprovalConfig,
        repository: TradingRepository | None = None,
        telegram_client: TelegramApprovalSender | None = None,
    ) -> None:
        self.config = config
        self.repository = repository or TradingRepository(config.db_path)
        self.repository.initialize()
        self.telegram_client = telegram_client

    def handle_update(self, update: dict[str, Any], *, send_reply: bool = True) -> TelegramApprovalResponse:
        message = update.get("message") or update.get("edited_message") or {}
        text = message.get("text") or ""
        chat = message.get("chat") or {}
        chat_id = str(chat.get("id")) if chat.get("id") is not None else None
        thread_id = message.get("message_thread_id")
        if isinstance(thread_id, str):
            thread_id = int(thread_id) if thread_id.isdigit() else None

        return self.handle_message(text, chat_id=chat_id, message_thread_id=thread_id, send_reply=send_reply)

    def handle_message(
        self,
        text: str,
        *,
        chat_id: str | None,
        message_thread_id: int | None = None,
        send_reply: bool = True,
    ) -> TelegramApprovalResponse:
        if parse_approval_command(text) is None:
            return TelegramApprovalResponse(False, False, chat_id, message_thread_id, "승인/거절 명령이 아니라 무시했습니다.")

        if not self._is_allowed_target(chat_id, message_thread_id):
            configured = self._configured_target_label()
            response = TelegramApprovalResponse(
                True,
                False,
                chat_id,
                message_thread_id,
                f"허용되지 않은 Telegram 대상입니다. 설정 대상: {configured}",
            )
            return response

        result = ApprovalWorkflow(self.repository).handle_text(text, mode=self.config.mode)
        response = TelegramApprovalResponse(True, True, chat_id, message_thread_id, result.message)
        if send_reply and self.telegram_client is not None and chat_id is not None:
            self.telegram_client.send_message(
                TelegramTarget(chat_id=chat_id, message_thread_id=message_thread_id),
                result.message,
            )
        return response

    def _is_allowed_target(self, chat_id: str | None, thread_id: int | None) -> bool:
        if self.config.chat_id and str(self.config.chat_id) != str(chat_id):
            return False
        if self.config.message_thread_id is not None and self.config.message_thread_id != thread_id:
            return False
        return True

    def _configured_target_label(self) -> str:
        return json.dumps(
            {"chat_id": self.config.chat_id, "message_thread_id": self.config.message_thread_id},
            ensure_ascii=False,
        )
