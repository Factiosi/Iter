#Requires -Version 5.1
<#
.SYNOPSIS
  Build Iter Portal archive and deploy to factiosi.com (Docker).

.PARAMETER RemoteHost
  SSH target. Prompted in interactive mode when empty.

.PARAMETER SkipTests
  Skip pytest before packaging.

.PARAMETER DryRun
  Print steps without scp/ssh.

.PARAMETER BuildScope
  full | api | web

.PARAMETER NonInteractive
  Use defaults; no prompts.

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
    return $answer.Trim().ToLowerInvariant() -in @("y", "yes", "d", "da")
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
    Write-Host "Invalid choice, using default." -ForegroundColor Yellow
    return $Choices[$DefaultIndex]
}

function Get-BuildScopeLabel([string]$Scope) {
    switch ($Scope) {
        "api" { return "api only" }
        "web" { return "web only" }
        default { return "api + web" }
    }
}

function Invoke-DeployMenu {
    Write-Host ""
    Write-Host "=== Iter Portal deploy ===" -ForegroundColor Green
    Write-Host "Press Enter for the value in square brackets."
    Write-Host ""

    if (-not $PSBoundParameters.ContainsKey("RemoteHost") -or [string]::IsNullOrWhiteSpace($RemoteHost)) {
        $entered = Read-Host "SSH host [$DefaultRemoteHost]"
        if ([string]::IsNullOrWhiteSpace($entered)) {
            $script:RemoteHost = $DefaultRemoteHost
        } else {
            $script:RemoteHost = $entered.Trim()
        }
    }

    if (-not $PSBoundParameters.ContainsKey("SkipTests")) {
        $script:SkipTests = -not (Read-YesNo "Run pytest before packaging?" $true)
    }

    if (-not $PSBoundParameters.ContainsKey("BuildScope") -or [string]::IsNullOrWhiteSpace($BuildScope)) {
        $script:BuildScope = Read-Option "Rebuild on server?" @("full", "api", "web") 0
    }

    if (-not $PSBoundParameters.ContainsKey("DryRun")) {
        $script:DryRun = Read-YesNo "Dry-run (no scp/ssh)?" $false
    }

    Write-Host ""
    Write-Host "Plan:" -ForegroundColor Yellow
    Write-Host "  Host:      $RemoteHost"
    Write-Host "  pytest:    $(if ($SkipTests) { 'skip' } else { 'run' })"
    Write-Host "  Build:     $(Get-BuildScopeLabel $BuildScope)"
    Write-Host "  Dry-run:   $(if ($DryRun) { 'yes' } else { 'no' })"
    Write-Host ""

    if (-not (Read-YesNo "Start deploy?" $true)) {
        Write-Host "Cancelled." -ForegroundColor Yellow
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
    Write-Host "pytest skipped." -ForegroundColor Yellow
}

Write-Step "Creating archive $Archive"
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
        --exclude='ops/corpvpn' `
        docker-compose.yml .dockerignore .gitignore .env.example apps assets ops scripts
    $size = (Get-Item $Archive).Length
    Write-Host "Archive: $([math]::Round($size / 1KB)) KB"
} finally {
    Pop-Location
}

Write-Step "Upload to server"
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
echo Deploy OK
"@

Write-Step "Remote deploy (backup DB -> extract -> $(Get-BuildScopeLabel $BuildScope))"
if ($DryRun) {
    Write-Host "[dry-run] ssh $RemoteHost bash -s"
    Write-Host $RemoteScript
} else {
    $RemoteScript | ssh $RemoteHost "bash -s"
}

Write-Step "Done"
Write-Host "Throne check (replace slug):" -ForegroundColor Yellow
Write-Host 'curl -fsS -H "User-Agent: Throne/1.0" https://iter.factiosi.com/config/<slug> | python -m json.tool | head'
