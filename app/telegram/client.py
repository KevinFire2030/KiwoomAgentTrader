from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


class TelegramClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class TelegramTarget:
    chat_id: str
    message_thread_id: int | None = None


class TelegramBotClient:
    """Small Telegram Bot API client used by approval gateway scripts.

    The implementation intentionally depends only on Python stdlib so the
    trading bot can run in the current WSL environment without installing
    additional packages.
    """

    def __init__(self, bot_token: str, timeout_seconds: int = 10) -> None:
        token = (bot_token or "").strip()
        if not token:
            raise TelegramClientError("TELEGRAM_BOT_TOKEN is required")
        self.bot_token = token
        self.timeout_seconds = timeout_seconds
        self.base_url = f"https://api.telegram.org/bot{token}"

    def send_message(self, target: TelegramTarget, text: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "chat_id": target.chat_id,
            "text": text,
        }
        if target.message_thread_id is not None:
            payload["message_thread_id"] = target.message_thread_id
        return self._post("sendMessage", payload)

    def get_updates(self, offset: int | None = None, timeout: int = 30) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {"timeout": timeout, "allowed_updates": json.dumps(["message"])}
        if offset is not None:
            payload["offset"] = offset
        response = self._post("getUpdates", payload, request_timeout=timeout + self.timeout_seconds)
        result = response.get("result", [])
        if not isinstance(result, list):
            raise TelegramClientError(f"Unexpected getUpdates result: {result!r}")
        return result

    def _post(self, method: str, payload: dict[str, Any], request_timeout: int | None = None) -> dict[str, Any]:
        encoded = urllib.parse.urlencode(payload).encode("utf-8")
        request = urllib.request.Request(f"{self.base_url}/{method}", data=encoded, method="POST")
        with urllib.request.urlopen(request, timeout=request_timeout or self.timeout_seconds) as response:
            raw = response.read().decode("utf-8")
        data = json.loads(raw)
        if not data.get("ok"):
            raise TelegramClientError(f"Telegram API {method} failed: {data}")
        return data
