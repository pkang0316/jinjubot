from __future__ import annotations

import hashlib
import html
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import unquote, urljoin, urlparse, urlunparse

from .config import DiscoveryConfig
from .gateway import DEFAULT_WEB_HEADERS, fetch_text, post_json

# This module started as Eventbrite-specific extraction code, but it now holds
# shared event-source parsing helpers used by multiple local calendars.

USER_TASTE_PROFILE = " ".join(
    [
        "Primary audience: a 26-year-old man based in Reston, Virginia.",
        "Assume recommendations are for him specifically, not for a broad general audience.",
        "He likes nature, animals, gaming, great deals, flip opportunities, and solid date ideas.",
        "His girlfriend is in Rockville, Maryland and likes running, good food, and smart low-key plans.",
        "Prefer things that feel specifically worth the drive or a night out, not generic filler.",
        "Treat spammy promotion, vague hype, and inflated marketing claims as negative signals.",
        "Be skeptical of BS and only surface things that seem genuinely worthwhile.",
    ]
)


@dataclass(frozen=True)
class DiscoveryResult:
    listing_url: str
    candidate_urls: list[str]
    selected_urls: list[str]
    items: list[dict[str, Any]]
    generated_at: str
    summary: str


def _strip_tags(raw_html: str) -> str:
    text = re.sub(r"<script\b[^<]*(?:(?!</script>)<[^<]*)*</script>", " ", raw_html, flags=re.I | re.S)
    text = re.sub(r"<style\b[^<]*(?:(?!</style>)<[^<]*)*</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<noscript\b[^<]*(?:(?!</noscript>)<[^<]*)*</noscript>", " ", text, flags=re.I | re.S)
    return re.sub(r"<[^>]+>", " ", text)


def html_to_condensed_text(raw_html: str) -> str:
    text = html.unescape(_strip_tags(raw_html))
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r" ?([,.;:!?])", r"\1", text)
    return text.strip()


def normalize_eventbrite_url(raw_url: str, listing_url: str) -> str | None:
    try:
        joined = urljoin(listing_url, raw_url)
        parsed = urlparse(joined)
        normalized = parsed._replace(query="", fragment="")
        return urlunparse(normalized)
    except ValueError:
        return None


def normalize_listing_url(raw_url: str, listing_url: str) -> str | None:
    try:
        joined = urljoin(listing_url, raw_url)
        parsed = urlparse(joined)
        normalized = parsed._replace(query="", fragment="")
        return urlunparse(normalized)
    except ValueError:
        return None


def normalize_optional_url(raw_url: str | None, base_url: str) -> str | None:
    if not raw_url or not str(raw_url).strip():
        return None

    raw = str(raw_url).strip()
    normalized_eventbrite_image = normalize_eventbrite_image_url(raw)
    if normalized_eventbrite_image:
        return normalized_eventbrite_image

    try:
        return urljoin(base_url, raw)
    except ValueError:
        return raw


def normalize_eventbrite_image_url(raw_url: str) -> str | None:
    candidate = str(raw_url).strip()
    if not candidate:
        return None

    parsed = urlparse(candidate)
    hostname = (parsed.hostname or "").lower()
    if "eventbrite.com" not in hostname or "/_next/image" not in parsed.path:
        return None

    match = re.search(r"[?&]url=([^&]+)", candidate)
    if not match:
        return None

    decoded = unquote(match.group(1))
    if decoded.startswith("https://img.evbuc.com/"):
        decoded = decoded.removeprefix("https://img.evbuc.com/")
    elif decoded.startswith("http://img.evbuc.com/"):
        decoded = decoded.removeprefix("http://img.evbuc.com/")

    decoded = unquote(decoded)
    cdn_index = decoded.find("https://cdn.evbuc.com/")
    if cdn_index == -1:
        cdn_index = decoded.find("http://cdn.evbuc.com/")
    if cdn_index == -1:
        return None

    canonical = decoded[cdn_index:]
    canonical = canonical.split("&", 1)[0]
    canonical = canonical.split("?", 1)[0]
    return canonical or None


def extract_candidate_event_urls(raw_html: str, listing_url: str, max_candidate_urls: int) -> list[str]:
    matches: set[str] = set()
    patterns = [
        r"https://www\.eventbrite\.com/e/[^\"'`\s<>]+",
        r'href="(/e/[^"]+)"',
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, raw_html, flags=re.I):
            candidate = match.group(1) if match.lastindex else match.group(0)
            normalized = normalize_eventbrite_url(candidate, listing_url)
            if normalized and "/e/" in normalized:
                matches.add(normalized)

    return list(matches)[:max_candidate_urls]


def extract_mosaic_event_urls(raw_html: str, listing_url: str, max_candidate_urls: int) -> list[str]:
    matches: set[str] = set()

    for match in re.finditer(r'href="([^"]+)"', raw_html, flags=re.I):
        candidate = match.group(1)
        normalized = normalize_listing_url(candidate, listing_url)
        if not normalized:
            continue

        parsed = urlparse(normalized)
        hostname = (parsed.hostname or "").lower()
        path = parsed.path.rstrip("/")

        if hostname not in {"mosaicdistrict.com", "www.mosaicdistrict.com"}:
            continue
        if "/event/" not in path:
            continue
        if path in {"/events/event", "/event"}:
            continue

        matches.add(normalized)

    return list(matches)[:max_candidate_urls]


def call_gateway(config: DiscoveryConfig, endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
    return post_json(f"{config.gateway_base_url}{endpoint}", payload, headers=config.gateway_headers())


def choose_event_urls_for_deep_fetch(
    config: DiscoveryConfig,
    listing_text: str,
    candidate_urls: list[str],
) -> list[str]:
    response = call_gateway(
        config,
        "/plan",
        {
            "context": "\n".join(
                [
                    f"Source page: {config.listing_url}",
                    "Candidate event detail URLs:",
                    *[f"- {candidate_url}" for candidate_url in candidate_urls],
                    "",
                    "Listing page text excerpt:",
                    listing_text[:12000],
                ]
            ),
            "budget": config.max_deep_fetches,
            "additional_instructions": " ".join(
                [
                    "Choose the most promising event detail pages to inspect more deeply.",
                    "Prefer real in-person events relevant to Northern Virginia.",
                    "Return tasks with action='deep_fetch_event' and target set to one of the candidate URLs exactly.",
                    f"Choose at most {config.max_deep_fetches} URLs.",
                ]
            ),
        },
    )

    parsed = response.get("parsed") if isinstance(response, dict) else None
    tasks = parsed.get("tasks") if isinstance(parsed, dict) else None
    if not isinstance(tasks, list):
        return candidate_urls[: config.max_deep_fetches]

    selected: list[str] = []
    for task in tasks:
        target = str(task.get("target", "")).strip() if isinstance(task, dict) else ""
        if target in candidate_urls and target not in selected:
            selected.append(target)

    return selected[: config.max_deep_fetches] if selected else candidate_urls[: config.max_deep_fetches]


def parse_title_from_html(raw_html: str) -> str | None:
    match = re.search(r"<title[^>]*>([^<]+)</title>", raw_html, flags=re.I)
    if not match:
        return None
    return html.unescape(match.group(1)).strip()


def parse_og_image(raw_html: str) -> str | None:
    match = re.search(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', raw_html, flags=re.I)
    return match.group(1).strip() if match else None


def clamp_number(value: Any, minimum: float, maximum: float, fallback: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return fallback

    return max(minimum, min(maximum, numeric))


def make_item_id(url: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", re.sub(r"^https?://", "", url)).strip("-").lower()
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
    return f"event-{slug}-{digest}"


def _clean_optional_text(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _normalize_time_slots(record: dict[str, Any] | None) -> tuple[str | None, str | None, str | None, list[dict[str, str | None]]]:
    if not isinstance(record, dict):
        return None, None, None, []

    slots: list[dict[str, str | None]] = []
    raw_slots = record.get("times")
    if isinstance(raw_slots, list):
        for raw_slot in raw_slots:
            if not isinstance(raw_slot, dict):
                continue
            label = _clean_optional_text(raw_slot.get("label"))
            start_at = _clean_optional_text(raw_slot.get("start_at"))
            end_at = _clean_optional_text(raw_slot.get("end_at"))
            if not any([label, start_at, end_at]):
                continue
            slots.append(
                {
                    "label": label,
                    "start_at": start_at,
                    "end_at": end_at,
                }
            )

    start_at = _clean_optional_text(record.get("start_at"))
    end_at = _clean_optional_text(record.get("end_at"))
    time_summary = _clean_optional_text(record.get("time_summary"))

    if not slots and any([start_at, end_at, time_summary]):
        slots.append(
            {
                "label": time_summary,
                "start_at": start_at,
                "end_at": end_at,
            }
        )

    primary_slot = slots[0] if slots else {}
    return (
        start_at or primary_slot.get("start_at"),
        end_at or primary_slot.get("end_at"),
        time_summary or primary_slot.get("label"),
        slots,
    )


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    normalized = value.strip()
    if not normalized:
        return None

    try:
        if normalized.endswith("Z"):
            normalized = f"{normalized[:-1]}+00:00"
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _format_time_summary(start_at: str | None, end_at: str | None) -> str | None:
    start_dt = _parse_iso_datetime(start_at)
    end_dt = _parse_iso_datetime(end_at)
    anchor = start_dt or end_dt
    if not anchor:
        return None

    start_hour = anchor.strftime("%I").lstrip("0") or "12"
    summary = f"{anchor.strftime('%a, %b')} {anchor.day} at {start_hour}:{anchor.strftime('%M %p')}"
    if end_dt and start_dt and start_dt.date() == end_dt.date():
        end_hour = end_dt.strftime("%I").lstrip("0") or "12"
        summary = f"{summary} - {end_hour}:{end_dt.strftime('%M %p')}"
    return summary


def _is_useful_time_summary(time_summary: str | None) -> bool:
    if not time_summary:
        return False

    lowered = time_summary.strip().lower()
    if not lowered:
        return False
    if "passed" in lowered:
        return False
    if re.fullmatch(r"\d+\s*(minute|minutes|hour|hours|day|days)", lowered):
        return False

    return bool(
        re.search(
            r"\b(mon|tue|wed|thu|fri|sat|sun|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d{1,2}/\d{1,2}|\d{4})\b",
            lowered,
        )
    )


def normalize_extracted_record(
    record: dict[str, Any] | None,
    event_url: str,
    generated_at: str,
    html_fallbacks: dict[str, Any],
    *,
    source_name: str,
    source_type: str,
    reason_fallback: str,
) -> dict[str, Any] | None:
    title = str(record.get("title", "")).strip() if isinstance(record, dict) else ""
    if not title:
        title = str(html_fallbacks.get("title", "")).strip()

    if not title:
        return None

    description = (
        str(record.get("description", "")).strip()
        if isinstance(record, dict) and str(record.get("description", "")).strip()
        else "A local event pick surfaced from the latest Northern Virginia discovery run."
    )

    tags: list[str] = []
    if isinstance(record, dict) and isinstance(record.get("tags"), list):
        tags = [str(tag).strip().lower() for tag in record["tags"] if str(tag).strip()]

    start_at, end_at, time_summary, times = _normalize_time_slots(record)
    if not _is_useful_time_summary(time_summary):
        time_summary = _format_time_summary(start_at, end_at)
    if not any([start_at, end_at, time_summary]):
        return None

    interest_rating = 72
    if isinstance(record, dict):
        numeric = clamp_number(record.get("interest_rating"), 0, 100, 72)
        if numeric > 0:
            interest_rating = round(numeric)

    return {
        "id": make_item_id(event_url),
        "version": 1,
        "category": "events",
        "title": title,
        "description": description,
        "url": event_url,
        "image_url": normalize_optional_url(
            (record or {}).get("image_url") if isinstance(record, dict) else None,
            event_url,
        )
        or normalize_optional_url(html_fallbacks.get("image_url"), event_url),
        "source": {
            "name": source_name,
            "url": event_url,
            "type": source_type,
        },
        "start_at": start_at,
        "end_at": end_at,
        "time_summary": time_summary,
        "times": times,
        "discovered_at": generated_at,
        "updated_at": generated_at,
        "last_seen_at": generated_at,
        "tags": tags,
        "interest_rating": interest_rating,
        "confidence": clamp_number((record or {}).get("confidence"), 0, 1, 0.75) if isinstance(record, dict) else 0.75,
        "status": (
            record.get("status")
            if isinstance(record, dict) and record.get("status") in {"active", "expired", "removed"}
            else "active"
        ),
        "reason": (
            str(record.get("reason", "")).strip()
            if isinstance(record, dict) and str(record.get("reason", "")).strip()
            else reason_fallback
        ),
    }


def extract_event_record_from_content(
    config: DiscoveryConfig,
    event_url: str,
    content: str,
    generated_at: str,
    html_fallbacks: dict[str, Any],
    *,
    source_name: str = "Eventbrite",
    source_type: str = "event_marketplace",
    source_description: str = "this Eventbrite event detail page",
    reason_fallback: str = "Selected from the Northern Virginia Eventbrite listing for deeper review.",
) -> dict[str, Any] | None:
    lowered_content = content.lower()
    if "this event has passed" in lowered_content or "event has passed" in lowered_content:
        return None

    response = call_gateway(
        config,
        "/extract",
        {
            "source_url": event_url,
            "schema_hint": json.dumps(
                {
                    "records": [
                        {
                            "title": "",
                            "description": "",
                            "image_url": "",
                            "start_at": "",
                            "end_at": "",
                            "time_summary": "",
                            "times": [
                                {
                                    "label": "",
                                    "start_at": "",
                                    "end_at": "",
                                }
                            ],
                            "tags": [],
                            "reason": "",
                            "interest_rating": 0,
                            "confidence": 0,
                            "status": "active",
                        }
                    ]
                }
            ),
            "additional_instructions": " ".join(
                [
                    f"Extract at most one event record from {source_description}.",
                    "Write the description as a short assistant-style recommendation, not pasted marketing copy.",
                    "Use one or two sentences that explain why someone local might care about the event.",
                    "Summarize it like a smart local assistant, not a promoter.",
                    USER_TASTE_PROFILE,
                    "When setting interest_rating, favor standout date ideas, strong food plans, outdoor or animal-adjacent experiences, gaming culture, genuinely good deals or value, and real flip potential when applicable.",
                    "Be skeptical of spammy or overmarketed events, and score them down rather than rewarding hype.",
                    "Capture the primary event time and include multiple times only when the page clearly lists separate sessions.",
                    "Do not return expired or already-passed events.",
                    "If the page only gives a vague duration and no concrete upcoming date/time, return no record.",
                    "Make time_summary concrete and user-facing, including the date when possible.",
                    "Keep tags short and lowercase.",
                    "Use status=active unless the page clearly indicates the event is no longer available.",
                    'Return {"records": []} if the page does not describe a real event.',
                ]
            ),
            "content": content[:18000],
        },
    )

    parsed = response.get("parsed") if isinstance(response, dict) else None
    records = parsed.get("records") if isinstance(parsed, dict) else None
    record = records[0] if isinstance(records, list) and records else None

    return normalize_extracted_record(
        record if isinstance(record, dict) else None,
        event_url,
        generated_at,
        html_fallbacks,
        source_name=source_name,
        source_type=source_type,
        reason_fallback=reason_fallback,
    )


def extract_event_record(config: DiscoveryConfig, event_url: str, generated_at: str) -> dict[str, Any] | None:
    raw_html = fetch_text(event_url, headers=DEFAULT_WEB_HEADERS)
    title = parse_title_from_html(raw_html)
    image_url = parse_og_image(raw_html)
    content = html_to_condensed_text(raw_html)[:18000]
    return extract_event_record_from_content(
        config,
        event_url,
        content,
        generated_at,
        {"title": title, "image_url": image_url},
    )


def discover_eventbrite_events(config: DiscoveryConfig) -> DiscoveryResult:
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    listing_html = fetch_text(config.listing_url, headers=DEFAULT_WEB_HEADERS)
    candidate_urls = extract_candidate_event_urls(listing_html, config.listing_url, config.max_candidate_urls)

    if not candidate_urls:
        raise RuntimeError("No candidate Eventbrite event URLs were found on the listing page.")

    listing_text = html_to_condensed_text(listing_html)
    selected_urls = choose_event_urls_for_deep_fetch(config, listing_text, candidate_urls)

    items: list[dict[str, Any]] = []
    for event_url in selected_urls:
        try:
            record = extract_event_record(config, event_url, generated_at)
            if record:
                items.append(record)
        except Exception as exc:  # noqa: BLE001
            print(f"Skipping {event_url}: {exc}")

    if not items:
        raise RuntimeError("No event records were extracted from the selected Eventbrite detail pages.")

    return DiscoveryResult(
        listing_url=config.listing_url,
        candidate_urls=candidate_urls,
        selected_urls=selected_urls,
        items=items,
        generated_at=generated_at,
        summary=f"Generated from a live Eventbrite Northern Virginia discovery run at {generated_at}.",
    )
