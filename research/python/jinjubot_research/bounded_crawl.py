from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from .config import DiscoveryConfig
from .eventbrite import (
    call_gateway,
    extract_candidate_event_urls,
    extract_event_record_from_content,
    html_to_condensed_text,
    parse_og_image,
    parse_title_from_html,
)
from .gateway import DEFAULT_WEB_HEADERS, fetch_text


@dataclass(frozen=True)
class SourceDefinition:
    source_id: str
    label: str
    category: str
    listing_url: str
    extract_strategy: str
    source_type: str
    candidate_strategy: str
    source_name: str
    allowed_domains: tuple[str, ...]
    max_candidate_urls: int
    max_follow_up_pages: int

    def to_payload(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "source_kind": "discovery_source",
            "enabled": True,
            "label": self.label,
            "category": self.category,
            "listing_url": self.listing_url,
            "extract_strategy": self.extract_strategy,
            "source_type": self.source_type,
            "candidate_strategy": self.candidate_strategy,
            "source_name": self.source_name,
            "allowed_domains": list(self.allowed_domains),
            "max_candidate_urls": self.max_candidate_urls,
            "max_follow_up_pages": self.max_follow_up_pages,
        }


def get_default_sources(config: DiscoveryConfig) -> list[dict[str, Any]]:
    return [
        SourceDefinition(
            source_id="eventbrite:northern-virginia",
            label="Eventbrite Northern Virginia",
            category="events",
            listing_url=config.listing_url,
            extract_strategy="event_eventbrite_detail",
            source_type="event_marketplace_listing",
            candidate_strategy="eventbrite_listing",
            source_name="Eventbrite",
            allowed_domains=("eventbrite.com", "www.eventbrite.com"),
            max_candidate_urls=config.max_candidate_urls,
            max_follow_up_pages=config.max_deep_fetches,
        ).to_payload()
    ]


def _is_allowed_url(url: str, allowed_domains: list[str]) -> bool:
    hostname = urlparse(url).hostname or ""
    return any(hostname == domain or hostname.endswith(f".{domain}") for domain in allowed_domains)


def _extract_candidate_urls(source: dict[str, Any], raw_html: str) -> list[str]:
    strategy = str(source.get("candidate_strategy", "")).strip()
    listing_url = str(source.get("listing_url", "")).strip()
    max_candidate_urls = int(source.get("max_candidate_urls", 0) or 0)

    if strategy == "eventbrite_listing":
        return extract_candidate_event_urls(raw_html, listing_url, max_candidate_urls)

    return []


def fetch_listing_artifact(source: dict[str, Any]) -> dict[str, Any]:
    listing_url = str(source.get("listing_url", "")).strip()
    raw_html = fetch_text(listing_url, headers=DEFAULT_WEB_HEADERS)
    candidate_urls = [
        url
        for url in _extract_candidate_urls(source, raw_html)
        if _is_allowed_url(url, list(source.get("allowed_domains", [])))
    ]

    return {
        "source_id": source["source_id"],
        "page_kind": "listing",
        "url": listing_url,
        "title": parse_title_from_html(raw_html),
        "image_url": parse_og_image(raw_html),
        "content_excerpt": html_to_condensed_text(raw_html)[:12000],
        "candidate_urls": candidate_urls,
    }


def plan_follow_up_fetches(
    config: DiscoveryConfig,
    source: dict[str, Any],
    listing_artifact: dict[str, Any],
) -> list[str]:
    candidate_urls = [
        url
        for url in listing_artifact.get("candidate_urls", [])
        if isinstance(url, str) and _is_allowed_url(url, list(source.get("allowed_domains", [])))
    ]
    max_follow_up_pages = int(source.get("max_follow_up_pages", 0) or 0)
    if not candidate_urls or max_follow_up_pages <= 0:
        return []

    response = call_gateway(
        config,
        "/plan",
        {
            "context": "\n".join(
                [
                    f"Source ID: {source['source_id']}",
                    f"Source label: {source['label']}",
                    f"Seed page: {listing_artifact['url']}",
                    f"Category: {source['category']}",
                    "",
                    "Seed page excerpt:",
                    str(listing_artifact.get("content_excerpt", "")),
                    "",
                    "Available follow-up links:",
                    *[f"- {candidate_url}" for candidate_url in candidate_urls],
                ]
            ),
            "budget": max_follow_up_pages,
            "additional_instructions": " ".join(
                [
                    "You are reviewing a fetched seed page and deciding which follow-up HTML pages to request next.",
                    "Return only tasks that fetch more HTML from the available follow-up links.",
                    "Use action='fetch_html' and target equal to one of the available URLs exactly.",
                    "Prefer real in-person Northern Virginia events over generic category pages, waitlists, or multi-city signup pages.",
                    f"Return at most {max_follow_up_pages} follow-up fetches.",
                ]
            ),
        },
    )

    parsed = response.get("parsed") if isinstance(response, dict) else None
    tasks = parsed.get("tasks") if isinstance(parsed, dict) else None
    if not isinstance(tasks, list):
        return candidate_urls[:max_follow_up_pages]

    selected: list[str] = []
    allowed_actions = {"fetch_html", "deep_fetch_event", "deep_fetch", "follow_link"}
    for task in tasks:
        if not isinstance(task, dict):
            continue
        action = str(task.get("action", "")).strip().lower()
        target = str(task.get("target", "")).strip()
        if action in allowed_actions and target in candidate_urls and target not in selected:
            selected.append(target)

    return selected[:max_follow_up_pages] if selected else candidate_urls[:max_follow_up_pages]


def fetch_follow_up_artifact(source: dict[str, Any], url: str) -> dict[str, Any]:
    if not _is_allowed_url(url, list(source.get("allowed_domains", []))):
        raise ValueError(f"Refusing to fetch out-of-scope URL for source {source['source_id']}: {url}")

    raw_html = fetch_text(url, headers=DEFAULT_WEB_HEADERS)
    return {
        "source_id": source["source_id"],
        "page_kind": "detail",
        "url": url,
        "title": parse_title_from_html(raw_html),
        "image_url": parse_og_image(raw_html),
        "content_excerpt": html_to_condensed_text(raw_html)[:18000],
    }


def extract_item_from_artifact(
    config: DiscoveryConfig,
    source: dict[str, Any],
    page_artifact: dict[str, Any],
    generated_at: str,
) -> dict[str, Any] | None:
    if str(source.get("extract_strategy", "")).strip() == "event_eventbrite_detail":
        return extract_event_record_from_content(
            config,
            event_url=str(page_artifact["url"]),
            content=str(page_artifact.get("content_excerpt", "")),
            generated_at=generated_at,
            html_fallbacks={
                "title": page_artifact.get("title"),
                "image_url": page_artifact.get("image_url"),
            },
        )

    return None


def summarize_source_run(
    source: dict[str, Any],
    listing_artifact: dict[str, Any],
    selected_urls: list[str],
    page_artifacts: list[dict[str, Any]],
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "source_id": source["source_id"],
        "label": source["label"],
        "category": source["category"],
        "seed_url": source["listing_url"],
        "candidate_count": len(listing_artifact.get("candidate_urls", [])),
        "selected_urls": selected_urls,
        "fetched_pages": [
            {
                "url": artifact["url"],
                "title": artifact.get("title"),
                "page_kind": artifact.get("page_kind"),
            }
            for artifact in page_artifacts
        ],
        "items_created": len(items),
    }


def run_bounded_source_scan(config: DiscoveryConfig, generated_at: str) -> dict[str, Any]:
    source_runs: list[dict[str, Any]] = []
    all_items: list[dict[str, Any]] = []

    for source in get_default_sources(config):
        listing_artifact = fetch_listing_artifact(source)
        selected_urls = plan_follow_up_fetches(config, source, listing_artifact)
        page_artifacts = [fetch_follow_up_artifact(source, url) for url in selected_urls]
        items = [
            item
            for item in (
                extract_item_from_artifact(config, source, page_artifact, generated_at)
                for page_artifact in page_artifacts
            )
            if item
        ]
        source_runs.append(summarize_source_run(source, listing_artifact, selected_urls, page_artifacts, items))
        all_items.extend(items)

    return {
        "source_runs": source_runs,
        "items": all_items,
        "summary": " ".join(
            [
                f"Bounded crawl run at {generated_at}.",
                "Each source fetched a seed page, asked the LLM which follow-up HTML pages to inspect,",
                "and extracted objects only from the selected follow-up pages.",
            ]
        ),
    }
