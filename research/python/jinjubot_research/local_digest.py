from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_SITE_TITLE = "JinjuBot"
DEFAULT_TAGLINE = (
    "A Washington-area weekend guide that can pivot between events, food, "
    "and deals without turning into a cluttered dashboard."
)


def read_existing_digest(path: Path, generated_at: str) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {
            "siteTitle": DEFAULT_SITE_TITLE,
            "tagline": DEFAULT_TAGLINE,
            "updatedAt": generated_at,
            "summary": "Generated from live research runs.",
            "items": [],
        }


def merge_event_items(
    existing_digest: dict[str, Any],
    event_items: list[dict[str, Any]],
    generated_at: str,
    summary: str,
) -> dict[str, Any]:
    existing_items = existing_digest.get("items", [])
    non_event_items = [item for item in existing_items if item.get("category") != "events"] if isinstance(existing_items, list) else []

    return {
        "siteTitle": existing_digest.get("siteTitle") or DEFAULT_SITE_TITLE,
        "tagline": existing_digest.get("tagline") or DEFAULT_TAGLINE,
        "updatedAt": generated_at,
        "summary": summary,
        "items": [*event_items, *non_event_items],
    }


def write_digest(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")
