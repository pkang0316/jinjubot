from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


def _parse_env_line(line: str) -> tuple[str, str] | None:
    trimmed = line.strip()
    if not trimmed or trimmed.startswith("#") or "=" not in trimmed:
        return None

    key, value = trimmed.split("=", 1)
    return key.strip(), value.strip()


def load_env_file(path: Path, override: bool = False) -> None:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return

    for line in raw.splitlines():
        parsed = _parse_env_line(line)
        if not parsed:
            continue

        key, value = parsed
        if override or key not in os.environ:
            os.environ[key] = value


@dataclass(frozen=True)
class DiscoveryConfig:
    listing_url: str
    max_candidate_urls: int
    max_deep_fetches: int
    gateway_base_url: str
    cf_access_client_id: str | None = None
    cf_access_client_secret: str | None = None

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "DiscoveryConfig":
        return cls.from_mapping({}, env or os.environ)

    @classmethod
    def from_mapping(
        cls,
        values: Mapping[str, object],
        fallback_env: Mapping[str, str] | None = None,
    ) -> "DiscoveryConfig":
        env = fallback_env or os.environ

        def string_value(*keys: str, default: str = "") -> str:
            for key in keys:
                value = values.get(key)
                if value is not None and str(value).strip():
                    return str(value).strip()
                env_value = env.get(key)
                if env_value is not None and str(env_value).strip():
                    return str(env_value).strip()
            return default

        def int_value(*keys: str, default: int) -> int:
            raw = string_value(*keys, default=str(default))
            try:
                return int(raw)
            except ValueError:
                return default

        gateway_base_url = (
            string_value(
                "JINJUBOT_GATEWAY_URL",
                "LOCAL_LLM_GATEWAY_URL",
                "CF_LLM_GATEWAY_URL",
                default="http://localhost:8080",
            ).rstrip("/")
            or "http://localhost:8080"
        )

        return cls(
            listing_url=string_value(
                "EVENTBRITE_LISTING_URL",
                "EVENTBRITE_NOVA_URL",
                default="https://www.eventbrite.com/d/va--northern-virginia/events/",
            ),
            max_candidate_urls=int_value("EVENTBRITE_MAX_CANDIDATES", default=10),
            max_deep_fetches=int_value("EVENTBRITE_MAX_DEEP_FETCHES", "EVENTBRITE_MAX_EVENTS", default=4),
            gateway_base_url=gateway_base_url,
            cf_access_client_id=string_value("CF_ACCESS_CLIENT_ID") or None,
            cf_access_client_secret=string_value("CF_ACCESS_CLIENT_SECRET") or None,
        )

    def gateway_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}

        if self.gateway_base_url.lower().startswith("https://llm."):
            if not self.cf_access_client_id or not self.cf_access_client_secret:
                raise ValueError(
                    "CF_ACCESS_CLIENT_ID and CF_ACCESS_CLIENT_SECRET are required for the public Cloudflare gateway."
                )

            headers["CF-Access-Client-ID"] = self.cf_access_client_id
            headers["CF-Access-Client-Secret"] = self.cf_access_client_secret

        return headers
