# Python Research Path

This directory is the preferred backend path for the research pipeline.

It does two jobs:

- supports local research runs against the same `llm.jinjubot.io` or `localhost:8080` gateway
- provides a shared codebase for the AWS durable-Lambda workflow
- publishes a frontend-shaped feed artifact for the site to consume

## Layout

- `jinjubot_research/config.py`
  Loads env-driven config for local or Lambda execution.
- `BOUNDED_CRAWL_FLOW.md`
  Describes the first bounded agentic crawl loop used by the durable Lambda.
- `SOURCE_AND_ITEM_SCHEMAS.md`
  Defines the source registry shape, item schema, and the next backend workflows for scaling beyond one source.
- `jinjubot_research/bounded_crawl.py`
  Source registry loading, seed fetch, follow-up planning, and bounded HTML crawl helpers.
- `jinjubot_research/eventbrite.py`
  Shared event-source listing, planning, deep-fetch, and normalization helpers, including Eventbrite and Mosaic-specific adapters.
- `jinjubot_research/local_digest.py`
  Merges event results into `content/research-digest.json` for local iteration.
- `jinjubot_research/durable_handler.py`
  AWS durable-Lambda entrypoint.
- `run_eventbrite_nova.py`
  Local CLI for the bounded crawl workflow, currently seeded by the default source registry.

## Local usage

From the repo root:

```powershell
.\scripts\load-infra-env.ps1
py -3 .\research\python\run_eventbrite_nova.py
```

That updates:

- `content/research-digest.json`

using the shared Python pipeline instead of the JS prototype.

## AWS usage

The durable Lambda handler is:

- `jinjubot_research.durable_handler.lambda_handler`

The AWS Terraform scaffold for it lives in:

- `infra/terraform/aws-durable/`

## Dependency note

The shared local pipeline uses only the Python standard library.

The durable handler relies on:

- the AWS-provided `boto3`
- the AWS durable execution SDK available in durable Lambda runtimes

For production, AWS recommends packaging the durable SDK with your function even though the runtime includes it by default.
