# Terraform Notes

This directory is a starting point for codifying Cloudflare infrastructure.

The current configuration intentionally focuses on stable, low-risk primitives:

- provider configuration
- account and zone variables
- zone lookup
- example DNS records for the eventual site

Once the deployment target is finalized, we can extend this to include the app-specific resources and deployment bindings.
