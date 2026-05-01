from __future__ import annotations

from datetime import datetime, timezone
import os
from typing import Any

from aws_durable_execution_sdk_python import DurableContext, durable_execution, durable_step

from .aws_runtime import ensure_source_definitions, list_active_sources, put_items, put_json, upsert_source_status
from .bounded_crawl import (
    extract_item_from_artifact,
    fetch_follow_up_artifact,
    fetch_listing_artifact,
    get_default_sources,
    plan_follow_up_fetches,
    summarize_source_run,
)
from .config import DiscoveryConfig
from .published_feed import build_feed_payload
from .secrets import get_cloudflare_access_secret


def _build_request(event: dict[str, Any]) -> dict[str, Any]:
    request = dict(event)
    config = DiscoveryConfig.from_mapping(request)

    request.setdefault("EVENTBRITE_LISTING_URL", config.listing_url)
    request.setdefault("EVENTBRITE_MAX_CANDIDATES", config.max_candidate_urls)
    request.setdefault("EVENTBRITE_MAX_DEEP_FETCHES", config.max_deep_fetches)
    request.setdefault("JINJUBOT_GATEWAY_URL", config.gateway_base_url)
    request.setdefault("SNAPSHOT_BUCKET", os.getenv("SNAPSHOT_BUCKET", ""))
    request.setdefault("SNAPSHOT_KEY", os.getenv("SNAPSHOT_KEY", "snapshots/eventbrite-nova.json"))
    request.setdefault("PUBLIC_FEED_BUCKET", os.getenv("PUBLIC_FEED_BUCKET", ""))
    request.setdefault("PUBLIC_FEED_KEY", os.getenv("PUBLIC_FEED_KEY", "public/feed.json"))
    request.setdefault("ITEMS_TABLE_NAME", os.getenv("ITEMS_TABLE_NAME", ""))
    request.setdefault("SOURCES_TABLE_NAME", os.getenv("SOURCES_TABLE_NAME", ""))
    if os.getenv("CF_ACCESS_SECRET_ARN"):
        request.setdefault("CF_ACCESS_SECRET_ARN", os.getenv("CF_ACCESS_SECRET_ARN", ""))
    return request


def _config_from_request(request: dict[str, Any]) -> DiscoveryConfig:
    return DiscoveryConfig.from_mapping(request)


@durable_step
def start_run_step(step_context) -> str:
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    step_context.logger.info(f"Starting durable run at {generated_at}")
    return generated_at


@durable_step
def resolve_access_credentials_step(step_context, request: dict[str, Any]) -> dict[str, Any]:
    client_id = str(request.get("CF_ACCESS_CLIENT_ID", "")).strip()
    client_secret = str(request.get("CF_ACCESS_CLIENT_SECRET", "")).strip()
    secret_arn = str(request.get("CF_ACCESS_SECRET_ARN", "")).strip()

    if client_id and client_secret:
        return request

    if not secret_arn:
        return request

    step_context.logger.info("Resolving Cloudflare Access credentials from Secrets Manager")
    secret = get_cloudflare_access_secret(secret_arn)
    resolved = dict(request)
    resolved["CF_ACCESS_CLIENT_ID"] = secret["client_id"]
    resolved["CF_ACCESS_CLIENT_SECRET"] = secret["client_secret"]
    return resolved


@durable_step
def load_sources_step(step_context, request: dict[str, Any]) -> list[dict[str, Any]]:
    config = _config_from_request(request)
    default_sources = get_default_sources(config)
    sources_table_name = str(request.get("SOURCES_TABLE_NAME", "")).strip()

    if sources_table_name:
        ensure_source_definitions(sources_table_name, default_sources)
        sources = list_active_sources(sources_table_name)
    else:
        sources = default_sources

    if not sources:
        sources = default_sources

    step_context.logger.info(f"Loaded {len(sources)} source(s) for this run")
    return sources


@durable_step
def load_source_listing_step(step_context, source: dict[str, Any]) -> dict[str, Any]:
    step_context.logger.info(f"Fetching seed page for {source['source_id']}: {source['listing_url']}")
    return fetch_listing_artifact(source)


@durable_step
def plan_source_fetches_step(
    step_context,
    request: dict[str, Any],
    source: dict[str, Any],
    listing_artifact: dict[str, Any],
) -> list[str]:
    config = _config_from_request(request)
    candidate_urls = listing_artifact.get("candidate_urls", [])
    step_context.logger.info(f"Planning follow-up fetches for {source['source_id']} across {len(candidate_urls)} candidate URLs")
    return plan_follow_up_fetches(config, source, listing_artifact)


@durable_step
def fetch_follow_up_page_step(step_context, source: dict[str, Any], event_url: str) -> dict[str, Any]:
    step_context.logger.info(f"Fetching follow-up HTML from {event_url}")
    return fetch_follow_up_artifact(source, event_url)


@durable_step
def extract_source_item_step(
    step_context,
    request: dict[str, Any],
    source: dict[str, Any],
    page_artifact: dict[str, Any],
    generated_at: str,
) -> dict[str, Any] | None:
    config = _config_from_request(request)
    step_context.logger.info(f"Extracting object from {page_artifact['url']}")
    return extract_item_from_artifact(config, source, page_artifact, generated_at)


@durable_step
def persist_results_step(
    step_context,
    request: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    snapshot_bucket = str(request.get("SNAPSHOT_BUCKET", "")).strip()
    snapshot_key = str(request.get("SNAPSHOT_KEY", "snapshots/eventbrite-nova.json")).strip()
    public_feed_bucket = str(request.get("PUBLIC_FEED_BUCKET", "")).strip()
    public_feed_key = str(request.get("PUBLIC_FEED_KEY", "public/feed.json")).strip()
    items_table_name = str(request.get("ITEMS_TABLE_NAME", "")).strip()
    sources_table_name = str(request.get("SOURCES_TABLE_NAME", "")).strip()

    if snapshot_bucket:
        put_json(snapshot_bucket, snapshot_key, result)
        step_context.logger.info(f"Wrote snapshot to s3://{snapshot_bucket}/{snapshot_key}")

    published_feed = build_feed_payload(
        items=result.get("items", []) if isinstance(result.get("items"), list) else [],
        generated_at=str(result["generated_at"]),
        summary=str(result.get("summary", "")).strip(),
    )
    if public_feed_bucket:
        put_json(public_feed_bucket, public_feed_key, published_feed)
        step_context.logger.info(f"Wrote published feed to s3://{public_feed_bucket}/{public_feed_key}")

    items = result.get("items", [])
    if items_table_name and isinstance(items, list) and items:
        put_items(items_table_name, items)
        step_context.logger.info(f"Upserted {len(items)} items into {items_table_name}")

    source_runs = result.get("source_runs", [])
    sources_written = 0
    if sources_table_name and isinstance(source_runs, list):
        for source_run in source_runs:
            if not isinstance(source_run, dict):
                continue
            upsert_source_status(
                sources_table_name,
                str(source_run["source_id"]),
                {
                    "status": "active" if source_run.get("items_created", 0) else "idle",
                    "last_checked_at": result["generated_at"],
                    "last_success_at": result["generated_at"] if source_run.get("items_created", 0) else "",
                    "yield_count": int(source_run.get("items_created", 0) or 0),
                    "notes": "AWS durable bounded crawl workflow.",
                },
            )
            sources_written += 1
        if sources_written:
            step_context.logger.info(f"Updated {sources_written} source registry entr{'' if sources_written == 1 else 'ies'} in {sources_table_name}")

    return {
        "snapshot_bucket": snapshot_bucket or None,
        "snapshot_key": snapshot_key if snapshot_bucket else None,
        "public_feed_bucket": public_feed_bucket or None,
        "public_feed_key": public_feed_key if public_feed_bucket else None,
        "items_written": len(items) if items_table_name else 0,
        "source_written": sources_written,
    }


@durable_execution
def lambda_handler(event: dict[str, Any], context: DurableContext) -> dict[str, Any]:
    request = context.step(resolve_access_credentials_step(_build_request(event)))
    generated_at = context.step(start_run_step())
    sources = context.step(load_sources_step(request))

    if not sources:
        return {
            "status": "no_sources",
            "generated_at": generated_at,
            "source_runs": [],
            "items": [],
        }

    items: list[dict[str, Any]] = []
    source_runs: list[dict[str, Any]] = []

    for source in sources:
        listing_artifact = context.step(load_source_listing_step(source))
        selected_urls = context.step(plan_source_fetches_step(request, source, listing_artifact))

        page_artifacts: list[dict[str, Any]] = []
        for event_url in selected_urls:
            page_artifacts.append(context.step(fetch_follow_up_page_step(source, event_url)))

        source_items: list[dict[str, Any]] = []
        for page_artifact in page_artifacts:
            item = context.step(extract_source_item_step(request, source, page_artifact, generated_at))
            if item:
                source_items.append(item)

        source_runs.append(summarize_source_run(source, listing_artifact, selected_urls, page_artifacts, source_items))
        items.extend(source_items)

    result = {
        "status": "ok" if items else "no_items",
        "generated_at": generated_at,
        "summary": " ".join(
            [
                f"Bounded durable crawl run at {generated_at}.",
                "The workflow fetched seed pages, let the LLM request bounded follow-up HTML,",
                "and extracted objects only from the reviewed follow-up pages.",
            ]
        ),
        "source_runs": source_runs,
        "items": items,
    }

    persistence = context.step(persist_results_step(request, result))
    result["persistence"] = persistence
    return result
