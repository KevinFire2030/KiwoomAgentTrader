from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Protocol


class Transport(Protocol):
    def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        timeout: int = 10,
    ) -> dict[str, Any]:
        ...


class UrllibTransport:
    def request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        timeout: int = 10,
    ) -> dict[str, Any]:
        if params:
            query = urllib.parse.urlencode(params)
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}{query}"
        body = None if json is None else json_dumps_bytes(json)
        request = urllib.request.Request(url=url, data=body, headers=headers or {}, method=method.upper())
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Kiwoom HTTP error {exc.code}: {detail}") from exc
        return json_loads_object(payload)


def json_dumps_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def json_loads_object(payload: str) -> dict[str, Any]:
    data = json.loads(payload or "{}")
    if not isinstance(data, dict):
        raise RuntimeError("Kiwoom response must be a JSON object")
    return data


class KiwoomRestClient:
    def __init__(self, base_url: str, app_key: str, token_provider, transport: Transport | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.app_key = app_key
        self.token_provider = token_provider
        self.transport = transport or UrllibTransport()

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.request("GET", path, params=params)

    def post(self, path: str, payload: dict[str, Any] | None = None, api_id: str | None = None) -> dict[str, Any]:
        return self.request("POST", path, payload=payload, api_id=api_id)

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None, params: dict[str, Any] | None = None, api_id: str | None = None) -> dict[str, Any]:
        token = self.token_provider()
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": f"{token.token_type} {token.access_token}",
            "appkey": self.app_key,
        }
        if api_id:
            headers["api-id"] = api_id
        return self.transport.request(method, self._url(path), headers=headers, json=payload, params=params)

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"
