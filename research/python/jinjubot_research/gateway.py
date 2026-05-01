from __future__ import annotations

import json
from typing import Any
from urllib import error, request


DEFAULT_WEB_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_text(url: str, headers: dict[str, str] | None = None, timeout: float = 60.0) -> str:
    req = request.Request(url, headers=headers or DEFAULT_WEB_HEADERS)
    try:
        with request.urlopen(req, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Request to {url} failed: {exc.code} {exc.reason}: {body[:300]}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Request to {url} failed: {exc.reason}") from exc


def post_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float = 120.0) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request_headers = {
        **DEFAULT_WEB_HEADERS,
        **headers,
    }
    req = request.Request(url, data=body, headers=request_headers, method="POST")
    try:
        with request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return json.loads(raw)
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gateway request to {url} failed: {exc.code} {exc.reason}: {body[:300]}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Gateway request to {url} failed: {exc.reason}") from exc
