# Bounded Durable Crawl Flow

This document describes the first agentic crawl flow for the AWS durable Lambda.

The goal is to keep the crawler flexible without letting the LLM operate as an unbounded browser.

## Desired shape

```text
cron -> durable lambda -> load source list -> fetch seed HTML -> LLM reviews HTML
     -> request bounded follow-up HTML -> fetch follow-up HTML -> extract objects
     -> persist artifacts + normalized items
```

## Core principles

### 1. Deterministic crawler, model-assisted decisions

Code decides:

- which sources are allowed
- which domains are in scope
- how many pages may be fetched
- how many follow-up rounds are allowed
- where artifacts and objects are persisted

The LLM decides:

- which available links are worth fetching next
- which fetched pages contain relevant objects
- how to normalize those pages into final objects

### 2. Persist facts, not chats

We do not rely on conversational memory across LLM invocations.

Instead we persist structured state:

- source metadata
- seed page excerpts
- available follow-up links
- fetched follow-up pages
- extracted objects
- final persistence metadata

Each LLM call is rebuilt from that structured state.

### 3. Bounded follow-up loop

The model may request more HTML, but only inside limits:

- allowed domains only
- known source link set only
- max follow-up pages per source
- first version uses one follow-up round

This keeps the crawl explainable and cheap.

## First-version implementation

The first version keeps the architecture generic but the source registry intentionally small.

### Current source registry

- `eventbrite:northern-virginia`
- `mosaicdistrict:events`

The Lambda now seeds default source definitions into DynamoDB when they are missing, then loads active source rows from the `sources` table. Status updates are written back without overwriting the source config.

### Current steps

1. Load source registry
2. Fetch one seed/listing page per source
3. Extract candidate links deterministically from the seed page
4. Ask the LLM which follow-up links deserve HTML fetches
5. Fetch those follow-up pages
6. Extract one object per relevant follow-up page
7. Persist:
   - snapshot JSON to S3
   - published frontend `feed.json` to S3
   - normalized items to DynamoDB
   - source run status to DynamoDB

### What is generic already

- source registry abstraction
- page artifact abstraction
- bounded follow-up planning step
- per-source run summaries
- durable Lambda persistence contract

### What is still source-specific

- Eventbrite candidate-link extraction
- Eventbrite object extraction prompt shape

## Data model in the run result

The durable execution result now contains:

- `generated_at`
- `summary`
- `source_runs`
- `items`
- `persistence`

Each `source_runs` entry includes:

- `source_id`
- `label`
- `category`
- `seed_url`
- `candidate_count`
- `selected_urls`
- `fetched_pages`
- `items_created`

## What this unlocks next

After this first version is stable, the next extensions should be:

1. Add raw HTML artifact persistence to S3
2. Add more source types with their own candidate-link adapters
3. Add a second bounded follow-up round when needed
4. Add deterministic dedupe:
   - canonical URL
   - item id
   - dedupe fingerprint
5. Add per-source crawl rules in DynamoDB instead of hardcoding them

## Non-goals for v1

This first version does **not** try to do:

- unrestricted recursive crawling
- freeform browser automation by the model
- cross-source dedupe
- long conversational memory between LLM calls
- site-specific raw HTML storage for every page

It is intentionally a bounded crawl with one source and one follow-up round.
