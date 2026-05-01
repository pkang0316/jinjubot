# Research Pipeline

This directory now has two tracks:

- the original JS prototypes used to move quickly inside the existing Next.js repo
- the newer Python path that is meant to become the real backend and AWS deployment target

## Current scripts

- `generate-update.mjs`
  Placeholder digest writer from the earliest scaffold.
- `eventbrite-nova.mjs`
  First end-to-end prototype that fetches the Eventbrite Northern Virginia listing, asks the planner which URLs deserve a deeper fetch, and writes normalized event items back into `content/research-digest.json`.

## Preferred backend path

The long-term ingestion backend now lives in:

- `research/python/`

That Python package is designed to support both:

- local research runs against `localhost:8080` or `https://llm.jinjubot.io`
- AWS durable Lambda execution

Start there if you are extending the backend instead of just tweaking the earlier prototype.
