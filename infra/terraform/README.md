# Terraform Notes

This directory codifies the Cloudflare Pages setup for the public website.

## What it manages

- Cloudflare Pages project
- GitHub-backed build configuration
- Optional custom domains attached to the Pages project
- Apex CNAME record pointing at the Pages subdomain when the zone apex is included in `custom_domains`
- `www` CNAME record pointing at the Pages subdomain when `www.<zone>` is included in `custom_domains`

## Prerequisite

Before applying this Terraform, authorize the Cloudflare GitHub integration for the account that will own the Pages project. Terraform can manage the project configuration after that authorization exists, but the account-level GitHub app connection starts as a dashboard authorization step.

## Current defaults

- GitHub repo: `pkang0316/jinjubot`
- Production branch: `main`
- Root directory: `site`
- Build command: `npm run build`
- Build output directory: `out`

## Local usage

Use environment variables for secrets and a local `terraform.tfvars` file for non-secret values.

### 1. Export the Cloudflare API token

PowerShell:

```powershell
$env:TF_VAR_cloudflare_api_token = "replace-me"
```

### 2. Create a local tfvars file

Copy [terraform.tfvars.example](/C:/Users/pkang/Documents/Codex/2026-04-25/i-want-to-create-a-website-3/infra/terraform/terraform.tfvars.example) to `terraform.tfvars` and fill in your real values.

### 3. Initialize and plan

From this directory:

```powershell
terraform init -backend=false
terraform plan
```

## Secret handling

- Keep `cloudflare_api_token` in an environment variable, not in `terraform.tfvars`.
- `terraform.tfvars` should only hold non-secret values like account IDs and domains.
- Terraform state can contain sensitive data, so do not commit any `tfstate` files.
