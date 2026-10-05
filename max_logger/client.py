from __future__ import annotations

import json
from typing import Any
from urllib import error, parse, request


class MaxClientError(RuntimeError):
    pass


class MaxClient:
    def __init__(self, token: str, base_url: str = "https://platform-api2.max.ru", timeout: float = 60.0):
        self._token = token
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @property
    def token(self) -> str:
        return self._token

    @property
    def auth_headers(self) -> dict[str, str]:
        return {"Authorization": self._token}

    def close(self) -> None:
        return None

    def __enter__(self) -> "MaxClient":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Any:
        url = self._build_url(path, params)
        data: bytes | None = None
        headers = dict(self.auth_headers)

        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        http_request = request.Request(url=url, data=data, headers=headers, method=method.upper())
        resolved_timeout = self.timeout if timeout is None else timeout

        try:
            with request.urlopen(http_request, timeout=resolved_timeout) as response:
                raw_text = response.read().decode(response.headers.get_content_charset() or "utf-8")
                return self._parse_response_body(raw_text)
        except error.HTTPError as exc:
            raw_text = exc.read().decode(exc.headers.get_content_charset() or "utf-8", errors="replace")
            payload = self._parse_response_body(raw_text)
            raise MaxClientError(
                f"Max API request failed with status {exc.code}: {payload}"
            ) from exc
        except error.URLError as exc:
            raise MaxClientError(f"Max API request failed: {exc.reason}") from exc

    def get_me(self) -> dict[str, Any]:
        payload = self.request("GET", "me")
        if not isinstance(payload, dict):
            raise MaxClientError(f"Unexpected Max API response format: {payload}")
        return payload

    def send_message(
        self,
        *,
        user_id: int | None = None,
        chat_id: int | None = None,
        text: str | None = None,
        attachments: list[dict[str, Any]] | None = None,
        link: dict[str, Any] | None = None,
        notify: bool | None = None,
        format: str | None = None,
        disable_link_preview: bool | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        if user_id is None and chat_id is None:
            raise ValueError("Either user_id or chat_id must be provided.")

        if text is None and attachments is None and link is None:
            raise ValueError("At least one of text, attachments or link must be provided.")

        params = {
            "user_id": user_id,
            "chat_id": chat_id,
            "disable_link_preview": disable_link_preview,
        }
        body = {
            "text": text,
            "attachments": attachments,
            "link": link,
            "notify": notify,
            "format": format,
        }

        payload = self.request(
            "POST",
            "messages",
            params={key: value for key, value in params.items() if value is not None},
            json_body={key: value for key, value in body.items() if value is not None},
            timeout=timeout,
        )

        if isinstance(payload, dict) and "message" in payload and isinstance(payload["message"], dict):
            return payload["message"]

        raise MaxClientError(f"Unexpected Max API response format: {payload}")

    def _build_url(self, path: str, params: dict[str, Any] | None = None) -> str:
        url = f"{self.base_url}/{path.lstrip('/')}"
        if not params:
            return url

        filtered_params = {key: value for key, value in params.items() if value is not None}
        if not filtered_params:
            return url

        query_string = parse.urlencode(filtered_params)
        return f"{url}?{query_string}"

    @staticmethod
    def _parse_response_body(raw_text: str) -> Any:
        if raw_text == "":
            return None

        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            return raw_text
