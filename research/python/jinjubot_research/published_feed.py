from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .event_sources import normalize_eventbrite_image_url


DEFAULT_SITE_TITLE = "JinjuBot"
DEFAULT_TAGLINE = "A Washington-area weekend guide that can pivot between events, food, and deals without turning into a cluttered dashboard."

PREFERENCE_KEYWORDS: dict[str, float] = {
    "nature": 10,
    "park": 7,
    "trail": 8,
    "outdoor": 7,
    "garden": 7,
    "animal": 10,
    "zoo": 9,
    "dog": 8,
    "cat": 8,
    "gaming": 10,
    "game": 8,
    "arcade": 8,
    "deal": 12,
    "discount": 10,
    "happy hour": 8,
    "food": 6,
    "brunch": 7,
    "restaurant": 6,
    "running": 8,
    "5k": 8,
    "date": 6,
    "reston": 6,
    "rockville": 4,
}


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value or not str(value).strip():
        return None

    normalized = str(value).strip()
    try:
        if normalized.endswith("Z"):
            normalized = f"{normalized[:-1]}+00:00"
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    except ValueError:
        return None


def _is_expired(item: dict[str, Any], generated_at: str) -> bool:
    if str(item.get("status", "active")).strip().lower() != "active":
        return True

    now = _parse_iso_datetime(generated_at) or datetime.now(timezone.utc)
    end_at = _parse_iso_datetime(item.get("end_at"))
    start_at = _parse_iso_datetime(item.get("start_at"))

    if end_at and end_at < now:
        return True
    if start_at and not end_at and start_at < now:
        return True

    return False


def _preference_boost(item: dict[str, Any]) -> float:
    text_parts = [
        str(item.get("title", "")),
        str(item.get("description", "")),
        str(item.get("reason", "")),
        " ".join(str(tag) for tag in item.get("tags", []) if tag),
        str((item.get("source") or {}).get("name", "")),
        str(item.get("category", "")),
    ]
    haystack = " ".join(text_parts).lower()
    boost = 0.0

    for keyword, weight in PREFERENCE_KEYWORDS.items():
        if keyword in haystack:
            boost += weight

    if item.get("category") == "deals":
        boost += 8
    if item.get("category") == "food":
        boost += 4

    return boost


def build_feed_payload(
    *,
    items: list[dict[str, Any]],
    generated_at: str,
    summary: str,
    site_title: str = DEFAULT_SITE_TITLE,
    tagline: str = DEFAULT_TAGLINE,
) -> dict[str, Any]:
    normalized_items: list[dict[str, Any]] = []
    for item in items:
        if _is_expired(item, generated_at):
            continue

        normalized_item = dict(item)
        image_url = normalized_item.get("image_url")
        if isinstance(image_url, str) and image_url.strip():
            normalized_item["image_url"] = normalize_eventbrite_image_url(image_url) or image_url
        normalized_items.append(normalized_item)

    ranked_items = sorted(
        normalized_items,
        key=lambda item: (
            float(item.get("interest_rating", 0) or 0) + _preference_boost(item),
            float(item.get("confidence", 0) or 0),
            str(item.get("title", "")),
        ),
        reverse=True,
    )

    return {
        "siteTitle": site_title,
        "tagline": tagline,
        "updatedAt": generated_at,
        "summary": summary,
        "items": ranked_items,
    }
