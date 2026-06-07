#Requires -Version 5.1
<#
.SYNOPSIS
  Сборка архива Iter Portal и деплой на factiosi.com (Docker).

.PARAMETER RemoteHost
  SSH target. Без значения — спросит в интерактивном режиме.

.PARAMETER SkipTests
  Пропустить pytest. В интерактивном режиме можно выбрать в меню.

.PARAMETER DryRun
  Только показать шаги без scp/ssh на сервер.

.PARAMETER BuildScope
  full | api | web — что пересобрать на сервере.

.PARAMETER NonInteractive
  Не задавать вопросы; использовать только переданные параметры и значения по умолчанию.

.EXAMPLE
  .\scripts\deploy-iter.ps1
  .\scripts\deploy-iter.ps1 -SkipTests -BuildScope api
  .\scripts\deploy-iter.ps1 -NonInteractive
#>
param(
    [string]$RemoteHost = "",
    [switch]$SkipTests,
    [switch]$DryRun,
    [ValidateSet("full", "api", "web")]
    [string]$BuildScope = "",
    [switch]$NonInteractive
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Archive = Join-Path $RepoRoot "iter-docker-upload.tar.gz"
$RemoteArchive = "~/iter-docker-upload.tar.gz"
$DefaultRemoteHost = "factiosi@factiosi.com"

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Read-YesNo {
    param(
        [string]$Prompt,
        [bool]$Default = $true
    )
    $suffix = if ($Default) { "[Y/n]" } else { "[y/N]" }
    $answer = Read-Host "$Prompt $suffix"
    if ([string]::IsNullOrWhiteSpace($answer)) {
        return $Default
    }
    return $answer.Trim().ToLowerInvariant() -in @("y", "yes", "д", "да")
}

function Read-Option {
    param(
        [string]$Prompt,
        [string[]]$Choices,
        [int]$DefaultIndex = 0
    )
    for ($i = 0; $i -lt $Choices.Length; $i++) {
        Write-Host ("  {0}) {1}" -f ($i + 1), $Choices[$i])
    }
    $defaultNumber = $DefaultIndex + 1
    $answer = Read-Host "$Prompt [$defaultNumber]"
    if ([string]::IsNullOrWhiteSpace($answer)) {
        return $Choices[$DefaultIndex]
    }
    if ($answer -match '^\d+$') {
        $index = [int]$answer - 1
        if ($index -ge 0 -and $index -lt $Choices.Length) {
            return $Choices[$index]
        }
    }
    $matched = $Choices | Where-Object { $_.ToLowerInvariant() -eq $answer.Trim().ToLowerInvariant() }
    if ($matched) {
        return $matched[0]
    }
    Write-Host "Неверный выбор, использую вариант по умолчанию." -ForegroundColor Yellow
    return $Choices[$DefaultIndex]
}

function Get-DockerDeploySteps([string]$Scope) {
    switch ($Scope) {
        "api" {
            return @(
                "docker compose build api"
                "docker compose up -d api"
            )
        }
        "web" {
            return @(
                "docker compose build web"
                "docker compose up -d web"
            )
        }
        default {
            return @(
                "docker compose build"
                "docker compose up -d"
            )
        }
    }
}

function Get-BuildScopeLabel([string]$Scope) {
    switch ($Scope) {
        "api" { return "только api" }
        "web" { return "только web" }
        default { return "api + web" }
    }
}

function Invoke-DeployMenu {
    Write-Host ""
    Write-Host "=== Деплой Iter Portal ===" -ForegroundColor Green
    Write-Host "Enter — значение по умолчанию в квадратных скобках."
    Write-Host ""

    if (-not $PSBoundParameters.ContainsKey("RemoteHost") -or [string]::IsNullOrWhiteSpace($RemoteHost)) {
        $entered = Read-Host "SSH-хост [$DefaultRemoteHost]"
        if ([string]::IsNullOrWhiteSpace($entered)) {
            $script:RemoteHost = $DefaultRemoteHost
        } else {
            $script:RemoteHost = $entered.Trim()
        }
    }

    if (-not $PSBoundParameters.ContainsKey("SkipTests")) {
        $script:SkipTests = -not (Read-YesNo "Запустить pytest перед упаковкой?" $true)
    }

    if (-not $PSBoundParameters.ContainsKey("BuildScope") -or [string]::IsNullOrWhiteSpace($BuildScope)) {
        $choice = Read-Option "Что пересобрать на сервере?" @(
            "full — api + web (полный деплой)"
            "api — только backend"
            "web — только frontend"
        ) 0
        $script:BuildScope = ($choice -split " — ", 2)[0].Trim()
    }

    if (-not $PSBoundParameters.ContainsKey("DryRun")) {
        $script:DryRun = Read-YesNo "Dry-run (без scp/ssh на сервер)?" $false
    }

    Write-Host ""
    Write-Host "План:" -ForegroundColor Yellow
    Write-Host "  Хост:      $RemoteHost"
    Write-Host "  pytest:    $(if ($SkipTests) { 'пропустить' } else { 'запустить' })"
    Write-Host "  Сборка:    $(Get-BuildScopeLabel $BuildScope)"
    Write-Host "  Dry-run:   $(if ($DryRun) { 'да' } else { 'нет' })"
    Write-Host ""

    if (-not (Read-YesNo "Начать деплой?" $true)) {
        Write-Host "Отменено." -ForegroundColor Yellow
        exit 0
    }
}

if (-not $NonInteractive) {
    Invoke-DeployMenu
}

if ([string]::IsNullOrWhiteSpace($RemoteHost)) {
    $RemoteHost = $DefaultRemoteHost
}
if ([string]::IsNullOrWhiteSpace($BuildScope)) {
    $BuildScope = "full"
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
} else {
    Write-Host "pytest пропущен." -ForegroundColor Yellow
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

$dockerSteps = (Get-DockerDeploySteps $BuildScope) -join "`n"
$RemoteScript = @"
set -euo pipefail
cd ~/iter-portal
TS=`$(date +%Y%m%d-%H%M%S)
mkdir -p ~/iter-backups
cp -a apps/api/data/iter.db ~/iter-backups/iter.db.`$TS
tar -xzf ~/iter-docker-upload.tar.gz -C ~/iter-portal --overwrite
$dockerSteps
sleep 3
curl -fsS https://iter.factiosi.com/health
docker compose ps
rm -f ~/iter-docker-upload.tar.gz
echo "Deploy OK"
"@

Write-Step "Деплой на сервере (backup DB → extract → $(Get-BuildScopeLabel $BuildScope))"
if ($DryRun) {
    Write-Host "[dry-run] ssh $RemoteHost bash -s"
    Write-Host $RemoteScript
} else {
    $RemoteScript | ssh $RemoteHost "bash -s"
}

Write-Step "Готово"
Write-Host "Проверка Throne (подставьте slug):" -ForegroundColor Yellow
Write-Host 'curl -fsS -H "User-Agent: Throne/1.0" https://iter.factiosi.com/config/<slug> | python -m json.tool | head'
