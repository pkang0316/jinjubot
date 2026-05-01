from __future__ import annotations

from typing import Any

from .eventbrite import normalize_eventbrite_image_url


DEFAULT_SITE_TITLE = "JinjuBot"
DEFAULT_TAGLINE = "A Washington-area weekend guide that can pivot between events, food, and deals without turning into a cluttered dashboard."


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
        normalized_item = dict(item)
        image_url = normalized_item.get("image_url")
        if isinstance(image_url, str) and image_url.strip():
            normalized_item["image_url"] = normalize_eventbrite_image_url(image_url) or image_url
        normalized_items.append(normalized_item)

    ranked_items = sorted(
        normalized_items,
        key=lambda item: (
            float(item.get("interest_rating", 0) or 0),
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
