# Agentic Research Site

This repository is the foundation for a content-driven website that is updated on a schedule by research automation.

The public site is a static Next.js build deployed through Cloudflare Pages from the `main` branch.

## Structure

- `site/`: Next.js frontend that renders the public website.
- `content/`: Generated content artifacts committed to Git.
- `research/`: Scripts and Python packages that produce or refresh content.
- `infra/terraform/`: Cloudflare infrastructure as code.
- `infra/terraform/aws-durable/`: Separate AWS scaffold for the Python durable-Lambda workflow.
- `.github/workflows/`: CI and scheduled automation.

## Current Flow

1. The current public site still reads `content/research-digest.json` at build time.
2. We have a working Eventbrite prototype that can fetch a listing page, plan deeper fetches, extract event records, and update the `events` lane.
3. The preferred backend direction is now Python, with a shared package that can run locally or inside AWS durable Lambda.
4. The local LLM gateway remains the shared `/plan` and `/extract` contract for both paths.

## Next Steps

1. Tighten the Eventbrite pipeline's locality and ranking filters.
2. Move more real-source workflows from JS prototype code into the Python package.
3. Wire the AWS durable-Lambda scaffold to real secret handling and deployment flows.
4. Decide when the canonical content store should move from committed JSON to cloud-managed storage.
