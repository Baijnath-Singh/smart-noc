# Vector Service Setup Script
# Quick start script for Vector DB and Knowledge Base

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Smart NOC - Vector Service Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Start ChromaDB
Write-Host "[1/4] Starting ChromaDB..." -ForegroundColor Yellow
docker compose up -d chromadb

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to start ChromaDB" -ForegroundColor Red
    exit 1
}

Write-Host "✓ ChromaDB started" -ForegroundColor Green
Write-Host ""

# Step 2: Wait for ChromaDB to be ready
Write-Host "[2/4] Waiting for ChromaDB to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

$maxRetries = 10
$retry = 0
$ready = $false

while ($retry -lt $maxRetries -and -not $ready) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/heartbeat" -TimeoutSec 2 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $ready = $true
        }
    }
    catch {
        $retry++
        Write-Host "  Waiting... ($retry/$maxRetries)" -ForegroundColor Gray
        Start-Sleep -Seconds 3
    }
}

if ($ready) {
    Write-Host "✓ ChromaDB is ready" -ForegroundColor Green
}
else {
    Write-Host "✗ ChromaDB failed to start" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 3: Build and start Vector Service
Write-Host "[3/4] Building and starting Vector Service..." -ForegroundColor Yellow
docker compose up -d --build vector-service

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to start Vector Service" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Vector Service started" -ForegroundColor Green
Write-Host ""

# Step 4: Populate Knowledge Base
Write-Host "[4/4] Populating Knowledge Base with 20 articles..." -ForegroundColor Yellow
Start-Sleep -Seconds 5  # Wait for service to initialize

docker compose exec -T vector-service python populate_kb.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to populate Knowledge Base" -ForegroundColor Red
    Write-Host ""
    Write-Host "Check logs with: docker compose logs vector-service" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "✓ Vector Service Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Services running:" -ForegroundColor Cyan
Write-Host "  - ChromaDB:       http://localhost:8000" -ForegroundColor White
Write-Host "  - Vector Service: Running in background" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. View logs:  docker compose logs -f vector-service" -ForegroundColor White
Write-Host "  2. Check stats: docker compose logs vector-service | Select-String 'Statistics'" -ForegroundColor White
Write-Host "  3. Test search: (see services/vector-service/README.md)" -ForegroundColor White
Write-Host ""
