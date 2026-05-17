# Apply PostgreSQL migrations to existing Smart NOC database
# Usage: .\apply-migrations.ps1 [migration_file]

param(
    [string]$MigrationFile
)

$ErrorActionPreference = "Stop"

$CONTAINER = "smart-noc-postgres"
$USER = "noc_admin"
$DB = "smart_noc"
$MIGRATIONS_DIR = "infrastructure\postgres\migrations"

Write-Host "🔧 Smart NOC - Database Migration Tool" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if postgres container is running
$runningContainers = docker ps --format "{{.Names}}" | Select-String -Pattern "^$CONTAINER$"
if (-not $runningContainers) {
    Write-Host "❌ Error: PostgreSQL container '$CONTAINER' is not running" -ForegroundColor Red
    Write-Host "   Start it with: docker compose up -d postgres" -ForegroundColor Yellow
    exit 1
}

# Function to apply a single migration
function Apply-Migration {
    param([string]$FilePath)
    
    $fileName = Split-Path -Leaf $FilePath
    Write-Host ""
    Write-Host "📝 Applying: $fileName" -ForegroundColor Yellow
    
    try {
        Get-Content $FilePath | docker compose exec -T postgres psql -U $USER -d $DB | Out-Null
        Write-Host "✅ Successfully applied: $fileName" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "❌ Failed to apply: $fileName" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        return $false
    }
}

# If specific migration file provided
if ($MigrationFile) {
    if (Test-Path $MigrationFile) {
        Apply-Migration -FilePath $MigrationFile
    }
    else {
        Write-Host "❌ Error: Migration file '$MigrationFile' not found" -ForegroundColor Red
        exit 1
    }
}
else {
    # Apply all migrations in order
    Write-Host "🔍 Found migrations:" -ForegroundColor Cyan
    $migrations = Get-ChildItem -Path $MIGRATIONS_DIR -Filter "*.sql" -ErrorAction SilentlyContinue
    
    if (-not $migrations) {
        Write-Host "❌ No migration files found in $MIGRATIONS_DIR" -ForegroundColor Red
        exit 1
    }
    
    $migrations | ForEach-Object { Write-Host "   - $($_.Name)" }
    
    Write-Host ""
    Write-Host "📦 Applying all migrations in order..." -ForegroundColor Cyan
    
    foreach ($migration in ($migrations | Sort-Object Name)) {
        if (-not (Apply-Migration -FilePath $migration.FullName)) {
            exit 1
        }
    }
    
    Write-Host ""
    Write-Host "🎉 All migrations applied successfully!" -ForegroundColor Green
}

# Verify tables exist
Write-Host ""
Write-Host "📊 Current database schema:" -ForegroundColor Cyan
docker compose exec postgres psql -U $USER -d $DB -c "\dt" | Select-String -Pattern "incidents|remediation|diagnosis"

Write-Host ""
Write-Host "✅ Migration complete!" -ForegroundColor Green
