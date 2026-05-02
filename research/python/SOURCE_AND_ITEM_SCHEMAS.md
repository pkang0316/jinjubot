# Source And Item Schemas

This document describes the backend shape we want for JinjuBot as the crawler grows beyond one Eventbrite listing.

## Core workflows

### 1. Source scan workflow

```text
cron -> durable lambda -> load active sources -> fetch seed page
     -> deterministic candidate extraction -> LLM picks follow-up pages
     -> fetch follow-up HTML -> extract normalized items
     -> dedupe/upsert -> publish feed.json
```

Use this for:

- marketplaces like Eventbrite
- venue calendars
- local guide pages
- recurring deal hubs

### 2. Freshness refresh workflow

```text
cron -> durable lambda -> load recently seen items -> revisit detail URLs
     -> confirm still live / changed / expired -> update items -> republish
```

Use this to keep recurring or long-lived items fresh without rediscovering them from scratch.

### 3. Topic sweep workflow

```text
manual trigger or cron -> pick a theme -> scan a curated source set
     -> extract only theme-relevant items -> publish a themed feed slice
```

Use this later for editorial collections like holiday events or brunch guides.

## Source schema

Each source definition should live in DynamoDB and describe how the shared crawl engine may interact with that source.

### Required fields

```json
{
  "source_id": "eventbrite:northern-virginia",
  "source_kind": "discovery_source",
  "enabled": true,
  "label": "Eventbrite Northern Virginia",
  "category": "events",
  "listing_url": "https://www.eventbrite.com/d/va--northern-virginia/events/",
  "source_type": "event_marketplace_listing",
  "candidate_strategy": "eventbrite_listing",
  "extract_strategy": "event_eventbrite_detail",
  "source_name": "Eventbrite",
  "allowed_domains": ["eventbrite.com", "www.eventbrite.com"],
  "max_candidate_urls": 10,
  "max_follow_up_pages": 4
}
```

Another valid source row can point at a venue or community calendar:

```json
{
  "source_id": "mosaicdistrict:events",
  "source_kind": "discovery_source",
  "enabled": true,
  "label": "Mosaic District Events",
  "category": "events",
  "listing_url": "https://mosaicdistrict.com/events/",
  "source_type": "community_calendar",
  "candidate_strategy": "mosaic_event_listing",
  "extract_strategy": "event_local_calendar_detail",
  "source_name": "Mosaic District",
  "allowed_domains": ["mosaicdistrict.com", "www.mosaicdistrict.com"],
  "max_candidate_urls": 12,
  "max_follow_up_pages": 4
}
```

### Optional operational fields

```json
{
  "notes": "Primary NOVA events marketplace seed.",
  "priority": 50,
  "last_checked_at": "2026-04-30T19:48:08.886998Z",
  "last_success_at": "2026-04-30T19:48:08.886998Z",
  "yield_count": 4,
  "last_failure_at": "",
  "last_failure_reason": ""
}
```

### Design rules

- `source_id` is the stable key.
- `source_kind=discovery_source` marks rows that are actual source configs, not unrelated metadata.
- `candidate_strategy` chooses deterministic link extraction.
- `extract_strategy` chooses the extraction prompt/normalizer.
- `enabled=false` disables a source without deleting it.

## Item schema

Items should be normalized for feed publishing and future dedupe/upsert logic.

### Core item shape

```json
{
  "id": "event-example",
  "version": 1,
  "category": "events",
  "title": "Wine and Dine at Wolf Trap",
  "description": "A short assistant-style summary that explains why this is worth a look instead of copying the page.",
  "url": "https://example.com/event",
  "image_url": "https://cdn.example.com/event.jpg",
  "source": {
    "name": "Eventbrite",
    "url": "https://example.com/event",
    "type": "event_marketplace"
  },
  "discovered_at": "2026-04-30T19:48:08.886998Z",
  "updated_at": "2026-04-30T19:48:08.886998Z",
  "last_seen_at": "2026-04-30T19:48:08.886998Z",
  "tags": ["music", "vienna"],
  "interest_rating": 80,
  "confidence": 0.82,
  "status": "active",
  "reason": "Picked because the detail page clearly describes an in-person local event."
}
```

### Event timing extensions

Events also need normalized time metadata.

```json
{
  "start_at": "2026-05-03T19:30:00-04:00",
  "end_at": "2026-05-03T22:00:00-04:00",
  "time_summary": "Sat, May 3 at 7:30 PM",
  "times": [
    {
      "label": "Sat, May 3 at 7:30 PM",
      "start_at": "2026-05-03T19:30:00-04:00",
      "end_at": "2026-05-03T22:00:00-04:00"
    }
  ]
}
```

### Description rules

Descriptions should:

- read like an assistant summary, not page copy
- explain why someone might care
- stay compact, ideally 1-2 sentences
- avoid hype, quote marks, and pasted marketing blurbs

## Scaling strategy

The crawl engine should stay shared. Scaling should mostly mean adding source rows and, when needed, adding one new strategy implementation.

### What should be data-driven

- active sources
- crawl limits
- allowed domains
- source/category metadata
- strategy selection

### What should stay in code

- deterministic HTML fetch behavior
- candidate extraction implementations
- extraction prompt builders
- dedupe/upsert logic
- artifact persistence and feed publishing
