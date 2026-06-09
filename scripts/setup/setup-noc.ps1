<#
.SYNOPSIS
    Smart NOC - Automated Setup Script
    
.DESCRIPTION
    This script sets up the complete Smart NOC environment including:
    - Prerequisites validation
    - Python virtual environment
    - Docker containers (Kafka, PostgreSQL, Services)
    - Database initialization
    - Health checks and validation
    
.NOTES
    Author: Smart NOC Team
    Version: 1.0
    Last Updated: April 25, 2026
#>

[CmdletBinding()]
param(
    [switch]$SkipPrereqCheck,
    [switch]$Clean,
    [switch]$NoLogs
)

# Color output functions
function Write-Success { param($Message) Write-Host "✓ $Message" -ForegroundColor Green }
function Write-Info { param($Message) Write-Host "ℹ $Message" -ForegroundColor Cyan }
function Write-Warning { param($Message) Write-Host "⚠ $Message" -ForegroundColor Yellow }
function Write-Error { param($Message) Write-Host "✗ $Message" -ForegroundColor Red }
function Write-Step { param($Message) Write-Host "`n═══ $Message ═══" -ForegroundColor Magenta }

# Error handling
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

# Script configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$StartTime = Get-Date

Write-Host @"

╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║           🚀 SMART NOC SETUP SCRIPT v1.0                 ║
║                                                           ║
║     Automated Network Operations Center Deployment       ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

"@ -ForegroundColor Cyan

try {
    # ══════════════════════════════════════════════════════════
    # STEP 1: Prerequisites Check
    # ══════════════════════════════════════════════════════════
    if (-not $SkipPrereqCheck) {
        Write-Step "STEP 1: Checking Prerequisites"
        
        # Check Docker
        Write-Info "Checking Docker..."
        try {
            $dockerVersion = docker --version
            Write-Success "Docker installed: $dockerVersion"
        }
        catch {
            Write-Error "Docker is not installed or not in PATH"
            Write-Host "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
            exit 1
        }
        
        # Check Docker service
        Write-Info "Checking Docker service status..."
        try {
            $dockerInfo = docker info 2>&1
            if ($LASTEXITCODE -ne 0) {
                Write-Error "Docker service is not running"
                Write-Host "Please start Docker Desktop and try again" -ForegroundColor Yellow
                exit 1
            }
            Write-Success "Docker service is running"
        }
        catch {
            Write-Error "Cannot connect to Docker daemon"
            exit 1
        }
        
        # Check WSL
        Write-Info "Checking WSL (Windows Subsystem for Linux)..."
        try {
            $wslVersion = wsl --version 2>&1
            Write-Success "WSL is installed"
        }
        catch {
            Write-Warning "WSL not found - required for some features"
            Write-Host "Install with: wsl --install" -ForegroundColor Yellow
        }
        
        # Check Python
        Write-Info "Checking Python..."
        try {
            $pythonVersion = python --version 2>&1
            if ($pythonVersion -match "Python 3\.(9|10|11|12)") {
                Write-Success "Python installed: $pythonVersion"
            }
            else {
                Write-Warning "Python 3.9+ recommended, found: $pythonVersion"
            }
        }
        catch {
            Write-Error "Python is not installed"
            Write-Host "Please install Python 3.9+ from: https://www.python.org/downloads/" -ForegroundColor Yellow
            exit 1
        }
        
        # Check available disk space
        Write-Info "Checking disk space..."
        $drive = (Get-Location).Drive.Name
        $freeSpace = (Get-PSDrive $drive).Free / 1GB
        if ($freeSpace -lt 10) {
            Write-Warning "Low disk space: ${freeSpace}GB free. Recommended: 10GB+"
        }
        else {
            Write-Success "Sufficient disk space: ${freeSpace:N2}GB free"
        }
        
        # Check available memory
        Write-Info "Checking available memory..."
        $mem = Get-CimInstance Win32_OperatingSystem
        $freeMemGB = [math]::Round($mem.FreePhysicalMemory / 1MB, 2)
        if ($freeMemGB -lt 4) {
            Write-Warning "Low memory: ${freeMemGB}GB free. Recommended: 4GB+"
        }
        else {
            Write-Success "Sufficient memory: ${freeMemGB}GB free"
        }
        
        Write-Success "All prerequisites met!"
    }
    
    # ══════════════════════════════════════════════════════════
    # STEP 2: Clean Environment (if requested)
    # ══════════════════════════════════════════════════════════
    if ($Clean) {
        Write-Step "STEP 2: Cleaning Previous Installation"
        Write-Warning "Stopping and removing existing containers..."
        
        Push-Location $ScriptDir
        docker compose down -v 2>&1 | Out-Null
        Write-Success "Previous installation cleaned"
        Pop-Location
        
        Start-Sleep -Seconds 2
    }
    else {
        Write-Step "STEP 2: Checking Existing Installation"
        Write-Info "Skipping cleanup (use -Clean to force)"
    }
    
    # ══════════════════════════════════════════════════════════
    # STEP 3: Environment Configuration
    # ══════════════════════════════════════════════════════════
    Write-Step "STEP 3: Configuring Environment"
    
    Push-Location $ScriptDir
    
    # Check if .env exists
    if (Test-Path ".env") {
        Write-Success ".env file found"
        
        # Validate critical environment variables
        Write-Info "Validating configuration..."
        $envContent = Get-Content ".env" -Raw
        
        $requiredVars = @(
            "POSTGRES_PASSWORD",
            "LLM_API_KEY",
            "LLM_MODEL",
            "KAFKA_BOOTSTRAP_SERVERS"
        )
        
        $missing = @()
        foreach ($var in $requiredVars) {
            if ($envContent -notmatch "$var=.+") {
                $missing += $var
            }
        }
        
        if ($missing.Count -gt 0) {
            Write-Warning "Missing environment variables: $($missing -join ', ')"
            Write-Host "Please update .env file before continuing" -ForegroundColor Yellow
            
            $continue = Read-Host "Continue anyway? (y/N)"
            if ($continue -ne 'y') {
                exit 1
            }
        }
        else {
            Write-Success "Configuration validated"
        }
    }
    else {
        Write-Warning ".env file not found"
        Write-Host "Creating .env from .env.example..." -ForegroundColor Yellow
        
        if (Test-Path ".env.example") {
            Copy-Item ".env.example" ".env"
            Write-Success ".env created from template"
            Write-Warning "⚠ IMPORTANT: Edit .env file and add your API keys!"
            
            $continue = Read-Host "Press Enter when ready to continue..."
        }
        else {
            Write-Error ".env.example not found. Cannot create configuration."
            exit 1
        }
    }
    
    # ══════════════════════════════════════════════════════════
    # STEP 4: Python Virtual Environment
    # ══════════════════════════════════════════════════════════
    Write-Step "STEP 4: Setting Up Python Environment"
    
    if (Test-Path "venv") {
        Write-Success "Virtual environment already exists"
    }
    else {
        Write-Info "Creating Python virtual environment..."
        python -m venv venv
        Write-Success "Virtual environment created"
    }
    
    # Activate venv and install dependencies
    Write-Info "Installing Python dependencies..."
    $activateScript = Join-Path $ScriptDir "venv\Scripts\Activate.ps1"
    
    if (Test-Path $activateScript) {
        & $activateScript
        
        if (Test-Path "services\log-generator\requirements.txt") {
            pip install --quiet -r services\log-generator\requirements.txt
            Write-Success "Python dependencies installed"
        }
        else {
            Write-Warning "requirements.txt not found in services/log-generator"
        }
    }
    else {
        Write-Warning "Could not activate virtual environment"
    }
    
    # ══════════════════════════════════════════════════════════
    # STEP 5: Docker Images Build
    # ══════════════════════════════════════════════════════════
    Write-Step "STEP 5: Building Docker Images"
    
    Write-Info "Building custom service images..."
    Write-Host "(This may take 5-10 minutes on first run)" -ForegroundColor Gray
    
    docker compose build 2>&1 | ForEach-Object {
        if ($_ -match "ERROR" -or $_ -match "failed") {
            Write-Host $_ -ForegroundColor Red
        }
        elseif (-not $NoLogs) {
            Write-Host $_ -ForegroundColor DarkGray
        }
    }
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Docker images built successfully"
    }
    else {
        Write-Error "Docker build failed"
        exit 1
    }
    
    # ══════════════════════════════════════════════════════════
    # STEP 6: Start Services
    # ══════════════════════════════════════════════════════════
    Write-Step "STEP 6: Starting Services"
    
    Write-Info "Starting infrastructure services (Kafka, PostgreSQL)..."
    docker compose up -d kafka postgres
    
    Write-Info "Waiting for infrastructure to be ready (30s)..."
    Start-Sleep -Seconds 30
    
    Write-Info "Starting application services..."
    docker compose up -d
    
    Write-Success "All services started"
    
    # ══════════════════════════════════════════════════════════
    # STEP 7: Health Checks
    # ══════════════════════════════════════════════════════════
    Write-Step "STEP 7: Running Health Checks"
    
    Write-Info "Waiting for services to initialize (15s)..."
    Start-Sleep -Seconds 15
    
    # Check container status
    Write-Info "Checking container status..."
    $containers = docker compose ps --format json | ConvertFrom-Json
    
    $runningCount = 0
    $expectedServices = @(
        "kafka",
        "postgres",
        "anomaly-detection",
        "correlation-engine",
        "llm-diagnosis"
    )
    
    foreach ($service in $expectedServices) {
        $container = $containers | Where-Object { $_.Service -eq $service }
        if ($container -and $container.State -eq "running") {
            Write-Success "$service is running"
            $runningCount++
        }
        else {
            Write-Warning "$service is not running"
        }
    }
    
    if ($runningCount -eq $expectedServices.Count) {
        Write-Success "All core services are running ($runningCount/$($expectedServices.Count))"
    }
    else {
        Write-Warning "Some services failed to start ($runningCount/$($expectedServices.Count))"
    }
    
    # Check PostgreSQL connection
    Write-Info "Testing PostgreSQL connection..."
    Start-Sleep -Seconds 5
    $pgTest = docker compose exec -T postgres psql -U noc_admin -d smart_noc -c "SELECT 1;" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "PostgreSQL is accessible"
        
        # Check incident count
        $incidentCount = docker compose exec -T postgres psql -U noc_admin -d smart_noc -t -c "SELECT COUNT(*) FROM incidents;" 2>&1
        if ($incidentCount -match "\d+") {
            Write-Success "Database initialized: $($incidentCount.Trim()) incidents"
        }
    }
    else {
        Write-Warning "PostgreSQL connection check failed"
    }
    
    # Check Kafka
    Write-Info "Testing Kafka connection..."
    $kafkaTest = docker compose exec -T kafka kafka-topics --bootstrap-server localhost:9092 --list 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Kafka is accessible"
    }
    else {
        Write-Warning "Kafka connection check failed"
    }
    
    # ══════════════════════════════════════════════════════════
    # STEP 8: Display Summary
    # ══════════════════════════════════════════════════════════
    Write-Step "STEP 8: Setup Complete!"
    
    $duration = (Get-Date) - $StartTime
    
    Write-Host @"

╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║                 ✓ SETUP COMPLETED!                       ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

⏱  Setup Duration: $($duration.Minutes)m $($duration.Seconds)s

📋 NEXT STEPS:
   
   1. View running services:
      docker compose ps
   
   2. Check service logs:
      docker compose logs -f [service-name]
      
   3. Generate test data (optional):
      cd services\log-generator
      ..\..\venv\Scripts\activate
      python generate_scenarios.py --scenario chaos --count 5
   
   4. View incidents in database:
      docker compose exec -T postgres psql -U noc_admin -d smart_noc -c "SELECT COUNT(*) FROM incidents;"
   
   5. Monitor AI diagnosis:
      docker compose logs -f llm-diagnosis

📚 DOCUMENTATION:
   - Full Guide: NOC_SETUP_GUIDE.md
   - Quick Ref: QUICK_REFERENCE.md
   
🛑 TO STOP NOC:
   Run: .\teardown-noc.ps1

⚠  IMPORTANT NOTES:
   - LLM diagnosis has rate limit: 150 requests/day (GitHub Models)
   - Default credentials in .env file - change for production
   - Services run on localhost - not exposed externally

"@ -ForegroundColor Green

    # Show service URLs
    Write-Host "🌐 SERVICE ACCESS:" -ForegroundColor Cyan
    Write-Host "   Kafka (internal):    kafka:19092" -ForegroundColor Gray
    Write-Host "   Kafka (external):    localhost:9092" -ForegroundColor Gray
    Write-Host "   PostgreSQL:          localhost:5432" -ForegroundColor Gray
    Write-Host "                        User: noc_admin / Pass: (from .env)" -ForegroundColor Gray
    Write-Host ""
    
    Pop-Location
    
}
catch {
    Write-Error "Setup failed: $_"
    Write-Host $_.ScriptStackTrace -ForegroundColor Red
    
    Write-Host "`n💡 TROUBLESHOOTING:" -ForegroundColor Yellow
    Write-Host "   1. Ensure Docker Desktop is running" -ForegroundColor Gray
    Write-Host "   2. Check .env file exists and has valid values" -ForegroundColor Gray
    Write-Host "   3. Try cleanup: .\teardown-noc.ps1 -Force" -ForegroundColor Gray
    Write-Host "   4. Re-run setup: .\setup-noc.ps1 -Clean" -ForegroundColor Gray
    Write-Host ""
    
    Pop-Location
    exit 1
}
