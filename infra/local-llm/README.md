# Local LLM Setup

This directory gives you a reproducible local LLM stack for Windows using Docker, WSL2, Ollama, and a small gateway service.

## What changed

The stack now runs as two containers:

- `ollama`: the model server
- `gateway`: a thin application-facing API in front of Ollama

The Ollama container is also now a **custom image**. It starts the server, waits for it to become healthy, pulls the base model if needed, and creates the named aliases automatically.

That means you no longer need to:

1. start the container
2. run a second script to create models

Now the main experience is just:

```powershell
.\scripts\llm.ps1 bootstrap
```

## What Docker is doing here

Docker packages software into a **container**.

- `image`: the blueprint for a container
- `container`: the running instance of that image
- `volume`: persistent storage that survives container restarts
- `port mapping`: exposes a port from inside the container to your laptop
- `compose`: describes multiple services so they can start together

In this setup:

- the custom Ollama image extends `ollama/ollama`
- the Ollama container stores model weights in the `ollama-data` volume
- the gateway container exposes a stable API on `localhost:8080`
- the gateway calls Ollama over the Docker network instead of through the public internet

## Why the gateway exists

The gateway is a thin wrapper around Ollama.

It gives you a cleaner contract than exposing the raw model API directly:

- `/health`
- `/extract`
- `/plan`

That makes it easier to:

- pin requests to specific model aliases
- validate request shape
- validate model output later
- refactor the local model runtime without changing every caller

## Model choice

The default base model is now:

- `qwen3:8b`

That is a better fit for your RTX A4000 laptop than the earlier `3.2B` model while still being realistic on `8 GB` VRAM.

Source:
- [Ollama qwen3 library page](https://ollama.com/library/qwen3)

## Files

- [../.env.example](/C:/Users/pkang/Documents/Codex/2026-04-25/i-want-to-create-a-website-3/infra/.env.example)
- [docker-compose.yml](/C:/Users/pkang/Documents/Codex/2026-04-25/i-want-to-create-a-website-3/infra/local-llm/docker-compose.yml)
- [ollama/Dockerfile](/C:/Users/pkang/Documents/Codex/2026-04-25/i-want-to-create-a-website-3/infra/local-llm/ollama/Dockerfile)
- [ollama/init-ollama.sh](/C:/Users/pkang/Documents/Codex/2026-04-25/i-want-to-create-a-website-3/infra/local-llm/ollama/init-ollama.sh)
- [ollama/models/extractor.Modelfile.template](/C:/Users/pkang/Documents/Codex/2026-04-25/i-want-to-create-a-website-3/infra/local-llm/ollama/models/extractor.Modelfile.template)
- [ollama/models/planner.Modelfile.template](/C:/Users/pkang/Documents/Codex/2026-04-25/i-want-to-create-a-website-3/infra/local-llm/ollama/models/planner.Modelfile.template)
- [gateway/Dockerfile](/C:/Users/pkang/Documents/Codex/2026-04-25/i-want-to-create-a-website-3/infra/local-llm/gateway/Dockerfile)
- [gateway/app/main.py](/C:/Users/pkang/Documents/Codex/2026-04-25/i-want-to-create-a-website-3/infra/local-llm/gateway/app/main.py)
- [../../scripts/llm.ps1](/C:/Users/pkang/Documents/Codex/2026-04-25/i-want-to-create-a-website-3/scripts/llm.ps1)
- [../../scripts/load-infra-env.ps1](/C:/Users/pkang/Documents/Codex/2026-04-25/i-want-to-create-a-website-3/scripts/load-infra-env.ps1)

## Prerequisites

1. Install [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/).
2. Enable the WSL2 backend in Docker Desktop.
3. Update WSL:

```powershell
wsl --update
```

4. Make sure Docker can see the NVIDIA GPU.

Relevant docs:
- [Docker GPU support](https://docs.docker.com/desktop/features/gpu/)
- [Docker WSL2 backend](https://docs.docker.com/desktop/features/wsl/)

## First run

From the repo root:

```powershell
Copy-Item .\infra\.env.example .\infra\.env.local
.\scripts\llm.ps1 bootstrap
```

Or with the root npm script:

```powershell
npm run llm:bootstrap
```

What happens:

1. Docker Compose builds the custom Ollama image and the gateway image.
2. Docker starts both containers.
3. Ollama pulls `qwen3:8b` if it is missing.
4. Ollama creates:
   - `jinjubot-extractor`
   - `jinjubot-planner`
5. The healthcheck waits for the gateway to become available.

## Smoke test

```powershell
.\scripts\llm.ps1 smoke
```

Or:

```powershell
npm run llm:smoke
```

This sends a small extraction request to the gateway and prints the response.

## Local endpoints

Gateway:

```text
http://localhost:8080
```

Routes:

- `GET /health`
- `POST /extract`
- `POST /plan`

Ollama remains directly reachable for debugging:

```text
http://localhost:11434
```

## Optional public endpoint through Cloudflare

This stack can also sit behind a protected Cloudflare hostname:

```text
https://llm.jinjubot.io
```

The Cloudflare side is managed from [infra/terraform](/C:/Users/pkang/Documents/Codex/2026-04-25/i-want-to-create-a-website-3/infra/terraform), which creates:

- a Cloudflare Tunnel
- a DNS record for `llm.jinjubot.io`
- a Cloudflare Access application
- a service token for automation

### Manual run flow

1. Start the local LLM stack:

```powershell
npm run llm:bootstrap
```

2. In `infra/terraform`, fetch the tunnel token and start `cloudflared`:

```powershell
$token = terraform output -raw llm_tunnel_token
cloudflared tunnel run --token $token
```

3. Fetch the Access credentials:

```powershell
.\scripts\load-infra-env.ps1
```

4. Test the public endpoint:

```powershell
Invoke-RestMethod `
  -Uri "$env:CF_LLM_GATEWAY_URL/health" `
  -Headers @{
    "CF-Access-Client-ID" = $env:CF_ACCESS_CLIENT_ID
    "CF-Access-Client-Secret" = $env:CF_ACCESS_CLIENT_SECRET
  }
```

### Restart behavior

The tunnel is **not** persistent if you start it manually with:

```powershell
cloudflared tunnel run --token <token>
```

That command only lasts for the current session. If the laptop reboots, sleeps, or the terminal closes, the tunnel stops.

The Docker containers are more durable because Compose uses `restart: unless-stopped`, but they still depend on Docker Desktop being up.

The later production-style setup would be:

- `cloudflared` installed as a Windows service
- Docker Desktop set to launch automatically
- this compose stack allowed to restart itself

For now, the repo documents only the manual startup path.

## Why this is easier to extend

The stack is now split cleanly:

- change model bootstrap logic in the custom Ollama image
- change application behavior in the gateway
- keep a stable external API contract even if the model or runtime changes later

That separation makes the system much easier to refactor than exposing raw Ollama everywhere.
