Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $repoRoot "infra\\.env.local"
$examplePath = Join-Path $repoRoot "infra\\.env.example"

if (-not (Test-Path $envPath)) {
  Write-Host "Infra env file not found at $envPath"
  Write-Host "Create it from the template first:"
  Write-Host "  Copy-Item `"$examplePath`" `"$envPath`""
  exit 1
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

Write-Host "Loaded infra env vars into the current PowerShell session."
Write-Host "OLLAMA_BASE_MODEL=$env:OLLAMA_BASE_MODEL"
Write-Host "CF_LLM_GATEWAY_URL=$env:CF_LLM_GATEWAY_URL"
