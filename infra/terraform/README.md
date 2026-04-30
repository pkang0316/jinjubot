# Terraform Notes

This directory codifies the Cloudflare setup for:

- the public Pages website
- the optional Zero Trust endpoint for the local LLM gateway

## What it manages

- Cloudflare Pages project
- GitHub-backed build configuration
- Optional custom domains attached to the Pages project
- Apex CNAME record pointing at the Pages subdomain when the zone apex is included in `custom_domains`
- `www` CNAME record pointing at the Pages subdomain when `www.<zone>` is included in `custom_domains`
- Optional Cloudflare Tunnel for `llm.<zone>`
- Optional Cloudflare Access application + policy + service token for the LLM gateway

## Prerequisite

Before applying this Terraform, authorize the Cloudflare GitHub integration for the account that will own the Pages project. Terraform can manage the project configuration after that authorization exists, but the account-level GitHub app connection starts as a dashboard authorization step.

## Current defaults

- GitHub repo: `pkang0316/jinjubot`
- Production branch: `main`
- Root directory: `site`
- Build command: `npm run build`
- Build output directory: `out`
- LLM gateway hostname: `llm.<zone>`
- LLM gateway origin service: `http://localhost:8080`

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

## Enabling the LLM gateway endpoint

To create a protected public endpoint for the local gateway, set this in `terraform.tfvars`:

```hcl
enable_llm_gateway = true
```

That will create:

- a Cloudflare Tunnel
- a `llm.<zone>` DNS record pointing at the tunnel
- a Cloudflare Access application protecting the hostname
- a service-auth Access policy for automation

The default tunnel target is:

```text
http://localhost:8080
```

After `terraform apply`, you can retrieve the tunnel run token with:

```powershell
terraform output -raw llm_tunnel_token
```

and the Access service-token credentials with:

```powershell
terraform output -raw llm_access_service_token_client_id
terraform output -raw llm_access_service_token_client_secret
```

Those credentials should be sent to the public endpoint using these headers:

- `CF-Access-Client-ID`
- `CF-Access-Client-Secret`

To connect your laptop to the tunnel, install `cloudflared` locally and run:

```powershell
$token = terraform output -raw llm_tunnel_token
cloudflared tunnel run --token $token
```

Once that process is running, the public hostname will forward to the local gateway on `localhost:8080`.

## Manual tunnel operations

For now, the simplest way to bring the public endpoint online is to run `cloudflared` manually on the laptop that is running the gateway.

### 1. Start the local LLM stack

From the repo root:

```powershell
npm run llm:bootstrap
```

That should bring up:

- the gateway on `http://localhost:8080`
- Ollama on `http://localhost:11434`

### 2. Start the Cloudflare Tunnel

From `infra/terraform`, fetch the run token:

```powershell
$token = terraform output -raw llm_tunnel_token
cloudflared tunnel run --token $token
```

While that process is running, `https://llm.jinjubot.io` should forward to the local gateway.

### 3. Test the protected public endpoint

Fetch the Access service-token credentials:

```powershell
$clientId = terraform output -raw llm_access_service_token_client_id
$clientSecret = terraform output -raw llm_access_service_token_client_secret
```

Then call the health endpoint:

```powershell
Invoke-RestMethod `
  -Uri "https://llm.jinjubot.io/health" `
  -Headers @{
    "CF-Access-Client-ID" = $clientId
    "CF-Access-Client-Secret" = $clientSecret
  }
```

If the tunnel and gateway are both healthy, the response should come from the local gateway through Cloudflare Access.

## Saving and reloading Access credentials

To make the Access credentials easier to reuse across terminal sessions:

1. Copy the checked-in template:

```powershell
Copy-Item .\infra\.env.example .\infra\.env.local
```

2. Fill in:

- `CF_ACCESS_CLIENT_ID`
- `CF_ACCESS_CLIENT_SECRET`
- optionally leave `CF_LLM_GATEWAY_URL=https://llm.jinjubot.io`

The local file is gitignored:

- [infra/.env.local](/C:/Users/pkang/Documents/Codex/2026-04-25/i-want-to-create-a-website-3/infra/.env.local)

The template is checked in:

- [infra/.env.example](/C:/Users/pkang/Documents/Codex/2026-04-25/i-want-to-create-a-website-3/infra/.env.example)

3. Load the values into your current shell:

```powershell
.\scripts\load-infra-env.ps1
```

After that, you can call:

```powershell
Invoke-RestMethod `
  -Uri "$env:CF_LLM_GATEWAY_URL/health" `
  -Headers @{
    "CF-Access-Client-ID" = $env:CF_ACCESS_CLIENT_ID
    "CF-Access-Client-Secret" = $env:CF_ACCESS_CLIENT_SECRET
  }
```

## Persistence note

Running:

```powershell
cloudflared tunnel run --token <token>
```

does **not** persist across laptop restarts. It is only a foreground process for the current session.

To make the endpoint survive reboots later, the next step will be:

- install `cloudflared` as a Windows service
- let Docker Desktop start automatically
- rely on the compose `restart: unless-stopped` policy for the gateway/Ollama containers

That service setup is intentionally not automated yet; for now this repo documents the manual flow only.
