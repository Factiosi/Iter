#Requires -Version 5.1
<#
.SYNOPSIS
  Deploy CORP VPN sidecar to /opt/corpvpn-runtime on factiosi.com.

.PARAMETER RemoteHost
  SSH target (default factiosi@factiosi.com).

.PARAMETER SkipTests
  Skip pytest.

.PARAMETER DryRun
  Print steps only.
#>
param(
    [string]$RemoteHost = "factiosi@factiosi.com",
    [switch]$SkipTests,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Archive = Join-Path $RepoRoot "corpvpn-deploy.tar.gz"
$RemoteArchive = "~/corpvpn-deploy.tar.gz"
$MasterUrl = "https://sub.slovovpn.com/sub/1dc84699b6e342d4a153e3da317fb4d3"

function Write-Step([string]$Message) {
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
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
$Staging = Join-Path $env:TEMP "corpvpn-deploy-staging"
if (Test-Path $Staging) { Remove-Item $Staging -Recurse -Force }
New-Item -ItemType Directory -Path (Join-Path $Staging "app\subscription") -Force | Out-Null
Copy-Item (Join-Path $RepoRoot "ops\corpvpn\corpvpn_proxy.py") (Join-Path $Staging "corpvpn_proxy.py")
Copy-Item (Join-Path $RepoRoot "apps\api\app\subscription\*.py") (Join-Path $Staging "app\subscription\")
if (Test-Path $Archive) { Remove-Item $Archive -Force }
Push-Location $Staging
try {
    tar -czf $Archive corpvpn_proxy.py app
    Write-Host "Archive: $([math]::Round((Get-Item $Archive).Length / 1KB)) KB"
} finally {
    Pop-Location
    Remove-Item $Staging -Recurse -Force -ErrorAction SilentlyContinue
}

$ServiceUnit = @"
[Unit]
Description=CORP VPN unified subscription proxy (decoupled runtime)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/corpvpn-runtime
Environment=CORP_APP_PATH=/opt/corpvpn-runtime
Environment=CORP_BIND_HOST=127.0.0.1
Environment=CORP_PORT=8080
Environment=CORP_MASTER_SUBSCRIPTION_URL=$MasterUrl
Environment=CORP_NAME_MODE=slovo
Environment=CORP_OUTPUT_FORMAT_MODE=auto
Environment=CORP_BYPASS_RENDER_MODE=socks
Environment=CORP_HAPP_ROUTING_DEEPLINK=1
Environment="CORP_ROUTE_NAME=CORP Route"
Environment="CORP_PROFILE_PREFIX=CORP VPN"
Environment="CORP_CLASH_GROUP_NAME=CORP VPN"
ExecStart=/opt/corpvpn-runtime/.venv/bin/python /opt/corpvpn-runtime/corpvpn_proxy.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
"@

Write-Step "Upload to server"
if ($DryRun) {
    Write-Host "[dry-run] scp $Archive ${RemoteHost}:$RemoteArchive"
    Write-Host "[dry-run] update systemd + run deploy-corpvpn-remote.sh"
    exit 0
}

scp $Archive "${RemoteHost}:${RemoteArchive}"
scp (Join-Path $RepoRoot "ops\corpvpn\deploy-corpvpn-remote.sh") "${RemoteHost}:~/deploy-corpvpn-remote.sh"

$RemoteScript = @"
set -euo pipefail
sudo tee /etc/systemd/system/corpvpn-proxy.service >/dev/null <<'EOF'
$ServiceUnit
EOF
sudo bash ~/deploy-corpvpn-remote.sh ~/corpvpn-deploy.tar.gz
rm -f ~/corpvpn-deploy.tar.gz ~/deploy-corpvpn-remote.sh
"@

Write-Step "Remote deploy (systemd + runtime)"
$RemoteScript | ssh $RemoteHost "bash -s"

Write-Step "Done"
Write-Host "Happ check:" -ForegroundColor Yellow
Write-Host "curl -fsS -H `"User-Agent: Happ/1.0`" http://127.0.0.1:8080/CorpVpnSubscription1_ | python -m json.tool | head"
