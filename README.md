# Agentic Research Site

This repository is the foundation for a content-driven website that is updated on a schedule by research automation.

## Structure

- `site/`: Astro + React frontend that renders the public website.
- `content/`: Generated content artifacts committed to Git.
- `research/`: Scripts that produce or refresh content.
- `infra/terraform/`: Cloudflare infrastructure as code.
- `.github/workflows/`: CI and scheduled automation.

## Current Flow

1. A scheduled workflow runs `research/generate-update.mjs`.
2. The research script writes a content snapshot to `content/research-digest.json`.
3. Astro reads that content file at build time and turns it into static HTML.
4. CI builds the site and keeps the generated content in version control.

## Next Steps

1. Replace the placeholder research script with your real agent pipeline.
2. Decide whether deployments should go to Cloudflare Pages or a Worker-based static site.
3. Fill in the Terraform variables for your Cloudflare account and zone.
4. Add a deploy workflow once the Cloudflare target is chosen.
