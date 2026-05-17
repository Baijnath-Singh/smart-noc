# Setup Scripts for Windows PowerShell

Write-Host "🚀 Smart NOC - Phase 0 Setup Script" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "⚠️  Warning: Not running as Administrator" -ForegroundColor Yellow
    Write-Host "Some operations may require elevated privileges." -ForegroundColor Yellow
    Write-Host ""
}

# Function to check if a command exists
function Test-Command {
    param($Command)
    $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)
}

Write-Host "🔍 Checking prerequisites..." -ForegroundColor Cyan
Write-Host ""

# Check WSL2
Write-Host -NoNewline "Checking WSL2: "
if (Test-Command wsl) {
    $wslVersion = wsl -l -v
    if ($wslVersion -match "Version 2") {
        Write-Host "✅ Installed" -ForegroundColor Green
    }
    else {
        Write-Host "❌ WSL2 not found" -ForegroundColor Red
        Write-Host "Run: wsl --set-default-version 2" -ForegroundColor Yellow
    }
}
else {
    Write-Host "❌ Not installed" -ForegroundColor Red
    Write-Host "Run: wsl --install" -ForegroundColor Yellow
}

# Check Docker Desktop
Write-Host -NoNewline "Checking Docker Desktop: "
if (Test-Command docker) {
    try {
        $dockerVersion = docker --version
        Write-Host "✅ $dockerVersion" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Docker not running" -ForegroundColor Red
        Write-Host "Please start Docker Desktop" -ForegroundColor Yellow
    }
}
else {
    Write-Host "❌ Not installed" -ForegroundColor Red
    Write-Host "Download from: https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
}

# Check Docker Compose
Write-Host -NoNewline "Checking Docker Compose: "
if (Test-Command docker) {
    try {
        $composeVersion = docker compose version
        Write-Host "✅ $composeVersion" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Not available" -ForegroundColor Red
    }
}
else {
    Write-Host "❌ Docker not available" -ForegroundColor Red
}

Write-Host ""
Write-Host "📋 Next Steps:" -ForegroundColor Cyan
Write-Host "1. Ensure all checks show ✅" -ForegroundColor White
Write-Host "2. Open WSL Ubuntu terminal" -ForegroundColor White
Write-Host "3. Navigate to: cd /mnt/c/Users/baisingh/ng-iam/smart-noc" -ForegroundColor White
Write-Host "4. Follow: docs/PHASE-0-SETUP.md" -ForegroundColor White
Write-Host ""

Write-Host "🎯 Quick Links:" -ForegroundColor Cyan
Write-Host "  README.md - Main overview" -ForegroundColor White
Write-Host "  QUICKSTART.md - Fast track guide" -ForegroundColor White
Write-Host "  docs/PHASE-0-SETUP.md - Detailed setup" -ForegroundColor White
Write-Host ""

Write-Host "✨ Ready to build your Smart NOC! ✨" -ForegroundColor Green
