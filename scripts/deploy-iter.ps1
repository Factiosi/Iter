#Requires -Version 5.1
<#
.SYNOPSIS
  Сборка архива Iter Portal и деплой на factiosi.com (Docker).

.PARAMETER RemoteHost
  SSH target, по умолчанию factiosi@factiosi.com

.PARAMETER SkipTests
  Пропустить pytest перед упаковкой.

.PARAMETER DryRun
  Только показать шаги без scp/ssh на сервер.

.EXAMPLE
  .\scripts\deploy-iter.ps1
  .\scripts\deploy-iter.ps1 -SkipTests
#>
param(
    [string]$RemoteHost = "factiosi@factiosi.com",
    [switch]$SkipTests,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Archive = Join-Path $RepoRoot "iter-docker-upload.tar.gz"
$RemoteArchive = "~/iter-docker-upload.tar.gz"

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

Write-Step "SSH preflight ($RemoteHost)"
if ($DryRun) {
    Write-Host "[dry-run] ssh -o BatchMode=yes $RemoteHost hostname"
} else {
    ssh -o BatchMode=yes -o ConnectTimeout=15 $RemoteHost "hostname && whoami && test -d ~/iter-portal"
}

if (-not $SkipTests) {
    Write-Step "pytest (apps/api)"
    Push-Location (Join-Path $RepoRoot "apps\api")
    try {
        python -m pytest -q
        if ($LASTEXITCODE -ne 0) { throw "pytest failed with exit code $LASTEXITCODE" }
    } finally {
        Pop-Location
    }
}

Write-Step "Создание архива $Archive"
if (Test-Path $Archive) { Remove-Item $Archive -Force }
Push-Location $RepoRoot
try {
    tar -czf $Archive `
        --exclude='apps/web/node_modules' `
        --exclude='apps/web/dist' `
        --exclude='apps/api/.venv' `
        --exclude='apps/api/data' `
        --exclude='apps/api/.env' `
        --exclude='apps/api/__pycache__' `
        --exclude='apps/api/.pytest_cache' `
        --exclude='.git' `
        docker-compose.yml .dockerignore .gitignore .env.example apps assets ops scripts
    $size = (Get-Item $Archive).Length
    Write-Host "Архив: $([math]::Round($size / 1KB)) KB"
} finally {
    Pop-Location
}

Write-Step "Загрузка на сервер"
if ($DryRun) {
    Write-Host "[dry-run] scp $Archive ${RemoteHost}:$RemoteArchive"
} else {
    scp $Archive "${RemoteHost}:${RemoteArchive}"
}

$RemoteScript = @'
set -euo pipefail
cd ~/iter-portal
TS=$(date +%Y%m%d-%H%M%S)
mkdir -p ~/iter-backups
cp -a apps/api/data/iter.db ~/iter-backups/iter.db.$TS
tar -xzf ~/iter-docker-upload.tar.gz -C ~/iter-portal --overwrite
docker compose build
docker compose up -d
sleep 3
curl -fsS https://iter.factiosi.com/health
docker compose ps
rm -f ~/iter-docker-upload.tar.gz
echo "Deploy OK"
'@

Write-Step "Деплой на сервере (backup DB → extract → docker compose)"
if ($DryRun) {
    Write-Host "[dry-run] ssh $RemoteHost bash -s (remote script)"
} else {
    $RemoteScript | ssh $RemoteHost "bash -s"
}

Write-Step "Готово"
Write-Host "Проверка Throne (подставьте slug):" -ForegroundColor Yellow
Write-Host 'curl -fsS -H "User-Agent: Throne/1.0" https://iter.factiosi.com/config/<slug> | python -m json.tool | head'
