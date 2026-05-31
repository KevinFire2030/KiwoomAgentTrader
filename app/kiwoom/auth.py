from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.kiwoom.client import Transport, UrllibTransport


@dataclass(frozen=True)
class KiwoomToken:
    token_type: str
    access_token: str
    expires_in: int


class KiwoomAuthClient:
    def __init__(self, base_url: str, app_key: str, secret_key: str, transport: Transport | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.app_key = app_key
        self.secret_key = secret_key
        self.transport = transport or UrllibTransport()

    def issue_token(self) -> KiwoomToken:
        response = self.transport.request(
            "POST",
            f"{self.base_url}/oauth2/token",
            headers={"Content-Type": "application/json;charset=UTF-8"},
            json={"grant_type": "client_credentials", "appkey": self.app_key, "secretkey": self.secret_key},
        )
        token_value = response.get("access_token") or response.get("token")
        if not token_value:
            raise RuntimeError(f"Kiwoom token response did not include token: return_code={response.get('return_code')} return_msg={response.get('return_msg')}")
        return KiwoomToken(
            token_type=str(response.get("token_type", "Bearer")),
            access_token=str(token_value),
            expires_in=int(response.get("expires_in", 0)),
        )
