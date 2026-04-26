# Agentic Research Site

This repository is the foundation for a content-driven website that is updated on a schedule by research automation.

The public site is a static Next.js build deployed through Cloudflare Pages from the `main` branch.

## Structure

- `site/`: Next.js frontend that renders the public website.
- `content/`: Generated content artifacts committed to Git.
- `research/`: Scripts that produce or refresh content.
- `infra/terraform/`: Cloudflare infrastructure as code.
- `.github/workflows/`: CI and scheduled automation.

## Current Flow

1. A scheduled workflow runs `research/generate-update.mjs`.
2. The research script writes a content snapshot to `content/research-digest.json`.
3. Next.js reads that content file at build time and turns it into static HTML.
4. CI builds the site and keeps the generated content in version control.

## Next Steps

1. Replace the placeholder research script with your real agent pipeline.
2. Move the canonical content store from committed JSON into the future AWS-backed ingestion pipeline.
3. Add Terraform for the AWS workflow stack alongside the Cloudflare setup.
4. Tighten the homepage presentation as the real data model grows.
