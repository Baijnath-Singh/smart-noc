<#
.SYNOPSIS
    Smart NOC - Automated Teardown Script
    
.DESCRIPTION
    This script safely tears down the Smart NOC environment including:
    - Graceful service shutdown
    - Container removal
    - Volume cleanup (optional)
    - Network cleanup
    - Validation of cleanup
    
.PARAMETER Force
    Skip confirmation prompts
    
.PARAMETER KeepData
    Preserve database volumes (keep incident data)
    
.PARAMETER KeepImages
    Don't remove Docker images
    
.NOTES
    Author: Smart NOC Team
    Version: 1.0
    Last Updated: April 25, 2026
#>

[CmdletBinding()]
param(
    [switch]$Force,
    [switch]$KeepData,
    [switch]$KeepImages
)

# Color output functions
function Write-Success { param($Message) Write-Host "✓ $Message" -ForegroundColor Green }
function Write-Info { param($Message) Write-Host "ℹ $Message" -ForegroundColor Cyan }
function Write-Warning { param($Message) Write-Host "⚠ $Message" -ForegroundColor Yellow }
function Write-Error { param($Message) Write-Host "✗ $Message" -ForegroundColor Red }
function Write-Step { param($Message) Write-Host "`n═══ $Message ═══" -ForegroundColor Magenta }

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$StartTime = Get-Date

Write-Host @"

╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║          🛑 SMART NOC TEARDOWN SCRIPT v1.0               ║
║                                                           ║
║        Safe Cleanup & Environment Destruction            ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

"@ -ForegroundColor Yellow

try {
    Push-Location $ScriptDir
    
    # ══════════════════════════════════════════════════════════
    # STEP 1: Confirmation
    # ══════════════════════════════════════════════════════════
    if (-not $Force) {
        Write-Step "STEP 1: Confirmation"
        
        Write-Warning "This will stop and remove all Smart NOC containers"
        
        if (-not $KeepData) {
            Write-Warning "⚠  Database volumes will be DELETED (all incident data will be lost)"
        }
        else {
            Write-Info "Database volumes will be preserved"
        }
        
        if (-not $KeepImages) {
            Write-Warning "Docker images will be removed"
        }
        else {
            Write-Info "Docker images will be preserved"
        }
        
        Write-Host ""
        $confirmation = Read-Host "Are you sure you want to continue? (yes/no)"
        
        if ($confirmation -ne "yes") {
            Write-Info "Teardown cancelled"
            exit 0
        }
        
        Write-Host ""
    }
    
    # ══════════════════════════════════════════════════════════
    # STEP 2: Check Running Services
    # ══════════════════════════════════════════════════════════
    Write-Step "STEP 2: Checking Running Services"
    
    $containers = docker compose ps --format json 2>&1 | ConvertFrom-Json
    
    if ($containers.Count -eq 0 -or $null -eq $containers) {
        Write-Info "No running Smart NOC services found"
    }
    else {
        Write-Info "Found $($containers.Count) running service(s):"
        foreach ($container in $containers) {
            Write-Host "   - $($container.Service) ($($container.State))" -ForegroundColor Gray
        }
    }
    
    # ══════════════════════════════════════════════════════════
    # STEP 3: Export Database (Optional Backup)
    # ══════════════════════════════════════════════════════════
    Write-Step "STEP 3: Data Backup (Optional)"
    
    if (-not $KeepData -and -not $Force) {
        $backup = Read-Host "Would you like to backup the database before deletion? (y/N)"
        
        if ($backup -eq 'y') {
            Write-Info "Creating database backup..."
            
            $backupDir = "backups"
            if (-not (Test-Path $backupDir)) {
                New-Item -ItemType Directory -Path $backupDir | Out-Null
            }
            
            $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
            $backupFile = "$backupDir\smart_noc_backup_$timestamp.sql"
            
            try {
                docker compose exec -T postgres pg_dump -U noc_admin smart_noc > $backupFile
                
                if (Test-Path $backupFile) {
                    $fileSize = (Get-Item $backupFile).Length / 1MB
                    Write-Success "Database backed up: $backupFile (${fileSize:N2} MB)"
                }
                else {
                    Write-Warning "Backup file not created"
                }
            }
            catch {
                Write-Warning "Backup failed: $_"
                $continue = Read-Host "Continue with teardown anyway? (y/N)"
                if ($continue -ne 'y') {
                    exit 1
                }
            }
        }
        else {
            Write-Info "Skipping backup"
        }
    }
    else {
        Write-Info "Backup skipped (keeping data or forced teardown)"
    }
    
    # ══════════════════════════════════════════════════════════
    # STEP 4: Stop Services Gracefully
    # ══════════════════════════════════════════════════════════
    Write-Step "STEP 4: Stopping Services"
    
    Write-Info "Stopping application services..."
    docker compose stop llm-diagnosis correlation-engine anomaly-detection 2>&1 | Out-Null
    
    Write-Info "Waiting for graceful shutdown (5s)..."
    Start-Sleep -Seconds 5
    
    Write-Info "Stopping infrastructure services..."
    docker compose stop kafka postgres 2>&1 | Out-Null
    
    Write-Success "All services stopped"
    
    # ══════════════════════════════════════════════════════════
    # STEP 5: Remove Containers
    # ══════════════════════════════════════════════════════════
    Write-Step "STEP 5: Removing Containers"
    
    if ($KeepData) {
        Write-Info "Removing containers (preserving volumes)..."
        docker compose down 2>&1 | Out-Null
    }
    else {
        Write-Info "Removing containers and volumes..."
        docker compose down -v 2>&1 | Out-Null
    }
    
    Write-Success "Containers removed"
    
    # ══════════════════════════════════════════════════════════
    # STEP 6: Remove Networks
    # ══════════════════════════════════════════════════════════
    Write-Step "STEP 6: Cleaning Up Networks"
    
    Write-Info "Removing Docker networks..."
    $networks = docker network ls --filter name=smart-noc --format "{{.Name}}" 2>&1
    
    if ($networks) {
        foreach ($network in $networks) {
            try {
                docker network rm $network 2>&1 | Out-Null
                Write-Success "Removed network: $network"
            }
            catch {
                Write-Warning "Could not remove network: $network (may be in use)"
            }
        }
    }
    else {
        Write-Info "No Smart NOC networks found"
    }
    
    # ══════════════════════════════════════════════════════════
    # STEP 7: Remove Images (Optional)
    # ══════════════════════════════════════════════════════════
    if (-not $KeepImages) {
        Write-Step "STEP 7: Removing Docker Images"
        
        Write-Info "Finding Smart NOC images..."
        $images = docker images --filter reference="smart-noc*" --format "{{.Repository}}:{{.Tag}}" 2>&1
        
        if ($images) {
            Write-Info "Removing $($images.Count) image(s)..."
            foreach ($image in $images) {
                docker rmi $image 2>&1 | Out-Null
                Write-Success "Removed: $image"
            }
        }
        else {
            Write-Info "No Smart NOC images found"
        }
    }
    else {
        Write-Step "STEP 7: Preserving Docker Images"
        Write-Info "Skipping image removal (use without -KeepImages to remove)"
    }
    
    # ══════════════════════════════════════════════════════════
    # STEP 8: Clean Python Environment (Optional)
    # ══════════════════════════════════════════════════════════
    Write-Step "STEP 8: Python Environment Cleanup"
    
    if (Test-Path "venv") {
        if (-not $Force) {
            $removeVenv = Read-Host "Remove Python virtual environment? (y/N)"
        }
        else {
            $removeVenv = 'n'
        }
        
        if ($removeVenv -eq 'y') {
            Write-Info "Removing virtual environment..."
            Remove-Item -Recurse -Force "venv"
            Write-Success "Virtual environment removed"
        }
        else {
            Write-Info "Virtual environment preserved"
        }
    }
    else {
        Write-Info "No virtual environment found"
    }
    
    # ══════════════════════════════════════════════════════════
    # STEP 9: Validation
    # ══════════════════════════════════════════════════════════
    Write-Step "STEP 9: Validating Cleanup"
    
    # Check for remaining containers
    $remainingContainers = docker compose ps --format json 2>&1 | ConvertFrom-Json
    if ($remainingContainers.Count -eq 0 -or $null -eq $remainingContainers) {
        Write-Success "No containers running"
    }
    else {
        Write-Warning "Some containers still exist:"
        foreach ($container in $remainingContainers) {
            Write-Host "   - $($container.Service)" -ForegroundColor Yellow
        }
    }
    
    # Check for volumes (if they should be removed)
    if (-not $KeepData) {
        $volumes = docker volume ls --filter name=smart-noc --format "{{.Name}}" 2>&1
        if ($volumes) {
            Write-Warning "Some volumes still exist (may need manual cleanup)"
        }
        else {
            Write-Success "All volumes removed"
        }
    }
    
    # ══════════════════════════════════════════════════════════
    # STEP 10: Summary
    # ══════════════════════════════════════════════════════════
    Write-Step "STEP 10: Teardown Complete!"
    
    $duration = (Get-Date) - $StartTime
    
    Write-Host @"

╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║              ✓ TEARDOWN COMPLETED!                       ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

⏱  Teardown Duration: $($duration.Minutes)m $($duration.Seconds)s

📊 CLEANUP SUMMARY:
   
   ✓ Containers:     Removed
   ✓ Networks:       Cleaned
"@ -ForegroundColor Green
    
    if ($KeepData) {
        Write-Host "   ℹ Volumes:        Preserved" -ForegroundColor Cyan
    }
    else {
        Write-Host "   ✓ Volumes:        Removed" -ForegroundColor Green
    }
    
    if ($KeepImages) {
        Write-Host "   ℹ Images:         Preserved" -ForegroundColor Cyan
    }
    else {
        Write-Host "   ✓ Images:         Removed" -ForegroundColor Green
    }
    
    Write-Host @"

📋 NEXT STEPS:
   
   - To restart NOC: .\setup-noc.ps1
   - To remove all data: .\teardown-noc.ps1 -Force
   - To keep data: .\teardown-noc.ps1 -KeepData

"@ -ForegroundColor Gray
    
    if (-not $KeepData -and (Test-Path "backups")) {
        $backups = Get-ChildItem "backups" -Filter "*.sql" | Sort-Object LastWriteTime -Descending | Select-Object -First 3
        if ($backups) {
            Write-Host "💾 RECENT BACKUPS:" -ForegroundColor Cyan
            foreach ($backup in $backups) {
                $size = $backup.Length / 1MB
                Write-Host "   - $($backup.Name) (${size:N2} MB)" -ForegroundColor Gray
            }
            Write-Host ""
        }
    }
    
    Write-Host "✅ Environment cleaned successfully!`n" -ForegroundColor Green
    
    Pop-Location
    
}
catch {
    Write-Error "Teardown failed: $_"
    Write-Host $_.ScriptStackTrace -ForegroundColor Red
    
    Write-Host "`n💡 TROUBLESHOOTING:" -ForegroundColor Yellow
    Write-Host "   1. Try forcing removal: docker compose down -v --remove-orphans" -ForegroundColor Gray
    Write-Host "   2. Manual network cleanup: docker network prune" -ForegroundColor Gray
    Write-Host "   3. Check running containers: docker ps -a" -ForegroundColor Gray
    Write-Host ""
    
    Pop-Location
    exit 1
}
