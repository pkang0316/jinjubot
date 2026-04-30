param(
  [Parameter(Mandatory = $true)]
  [ValidateSet("bootstrap", "health", "smoke")]
  [string]$Command
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$infraRoot = Join-Path $repoRoot "infra"
$envPath = Join-Path $infraRoot ".env.local"
$examplePath = Join-Path $infraRoot ".env.example"
$composeFile = Join-Path $repoRoot "infra\\local-llm\\docker-compose.yml"

function Import-InfraEnv {
  if (-not (Test-Path $envPath)) {
    Copy-Item $examplePath $envPath
    Write-Host "Created local env file at $envPath"
  }

  Get-Content $envPath | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#")) {
      return
    }

    $parts = $line -split "=", 2
    if ($parts.Count -ne 2) {
      return
    }

    $name = $parts[0].Trim()
    $value = $parts[1].Trim()
    [Environment]::SetEnvironmentVariable($name, $value, "Process")
  }
}

function Invoke-LlmHealthcheck {
  $port = if ($env:GATEWAY_PORT) { $env:GATEWAY_PORT } else { "8080" }
  $url = "http://localhost:$port/health"

  Write-Host "Waiting for gateway health endpoint on $url ..."

  for ($attempt = 1; $attempt -le 30; $attempt++) {
    try {
      $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 3
      if ($response.StatusCode -eq 200) {
        Write-Host "Gateway is healthy."
        return
      }
    } catch {
      Start-Sleep -Seconds 2
    }
  }

  Write-Error "Gateway did not become healthy in time."
}

Import-InfraEnv

switch ($Command) {
  "bootstrap" {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
      Write-Error "Docker is not installed or not on PATH. Install Docker Desktop with the WSL2 backend first."
    }

    $composeArgs = @(
      "--env-file",
      $envPath,
      "-f",
      $composeFile
    )

    Write-Host "Starting local LLM stack..."
    docker compose @composeArgs up -d --build
    if ($LASTEXITCODE -ne 0) {
      Write-Error "Docker Compose failed. Make sure Docker Desktop is running with the WSL2 backend before retrying."
    }

    Invoke-LlmHealthcheck

    Write-Host ""
    Write-Host "Local LLM stack is ready."
    Write-Host "Gateway: http://localhost:$($env:GATEWAY_PORT)"
    Write-Host "Ollama:  http://localhost:$($env:OLLAMA_PORT)"
  }

  "health" {
    Invoke-LlmHealthcheck
  }

  "smoke" {
    $port = if ($env:GATEWAY_PORT) { $env:GATEWAY_PORT } else { "8080" }
    $url = "http://localhost:$port/extract"

    $body = @{
      source_url  = "https://example.com/test"
      schema_hint = '{"records":[{"title":"","description":"","url":"","category":"","tags":[],"reason":""}]}'
      content     = @"
Title: Spring market in Arlington
Description: Saturday pop-up with coffee, pastries, local ceramics, and live music.
URL: https://example.com/arlington-market
"@
    } | ConvertTo-Json -Depth 5

    $response = Invoke-RestMethod -Uri $url -Method Post -ContentType "application/json" -Body $body
    $response | ConvertTo-Json -Depth 8
  }
}
