# Start FinAlly (idempotent). Usage: .\start_windows.ps1 [-Build] [-NoOpen]
param([switch]$Build, [switch]$NoOpen)
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host 'Created .env from .env.example' }
New-Item -ItemType Directory -Force db | Out-Null
$ErrorActionPreference = 'Continue'
docker image inspect finally *> $null
$have = ($LASTEXITCODE -eq 0)
if ($Build -or -not $have) { docker build -t finally .; if ($LASTEXITCODE) { exit 1 } }
docker rm -f finally *> $null
$ErrorActionPreference = 'Continue'
docker run -d --name finally -p 8000:8000 -v "${PWD}/db:/app/db" --env-file .env finally | Out-Null
if ($LASTEXITCODE) { exit 1 }
$url = 'http://localhost:8000'
Write-Host "FinAlly running at $url"
if (-not $NoOpen) { Start-Process $url }
