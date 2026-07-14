$ErrorActionPreference = "Stop"

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "Node.js and npm are required."
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is required. Install it from https://docs.astral.sh/uv/."
}

npm ci
uv sync --project apps/api --all-groups

Write-Host "LEVELS dependencies are installed. Copy .env.example to .env before starting development."
