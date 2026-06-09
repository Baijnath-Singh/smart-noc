#!/bin/bash
#
# Smart NOC - Automated Teardown Script (WSL/Linux)
#
# Purpose: Safely tears down the Smart NOC environment including:
#   - Graceful service shutdown
#   - Container removal
#   - Volume cleanup (optional)
#   - Network cleanup
#   - Validation of cleanup
#
# Author: Smart NOC Team
# Version: 1.0
# Last Updated: April 25, 2026
#

set -e  # Exit on error

# Color output functions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

success() { echo -e "${GREEN}✓ $1${NC}"; }
info() { echo -e "${CYAN}ℹ $1${NC}"; }
warning() { echo -e "${YELLOW}⚠ $1${NC}"; }
error() { echo -e "${RED}✗ $1${NC}"; }
step() { echo -e "\n${MAGENTA}═══ $1 ═══${NC}"; }

# Parse arguments
FORCE=false
KEEP_DATA=false
KEEP_IMAGES=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --force) FORCE=true; shift ;;
        --keep-data) KEEP_DATA=true; shift ;;
        --keep-images) KEEP_IMAGES=true; shift ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --force          Skip confirmation prompts"
            echo "  --keep-data      Preserve database volumes"
            echo "  --keep-images    Don't remove Docker images"
            echo "  -h, --help       Show this help message"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

START_TIME=$(date +%s)

cat << "EOF"

╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║          🛑 SMART NOC TEARDOWN SCRIPT v1.0               ║
║                                                           ║
║        Safe Cleanup & Environment Destruction            ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

EOF

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ══════════════════════════════════════════════════════════
# STEP 1: Confirmation
# ══════════════════════════════════════════════════════════
if [ "$FORCE" = false ]; then
    step "STEP 1: Confirmation"
    
    warning "This will stop and remove all Smart NOC containers"
    
    if [ "$KEEP_DATA" = false ]; then
        warning "⚠  Database volumes will be DELETED (all incident data will be lost)"
    else
        info "Database volumes will be preserved"
    fi
    
    if [ "$KEEP_IMAGES" = false ]; then
        warning "Docker images will be removed"
    else
        info "Docker images will be preserved"
    fi
    
    echo ""
    read -p "Are you sure you want to continue? (yes/no): " -r
    
    if [[ ! $REPLY == "yes" ]]; then
        info "Teardown cancelled"
        exit 0
    fi
    
    echo ""
fi

# ══════════════════════════════════════════════════════════
# STEP 2: Check Running Services
# ══════════════════════════════════════════════════════════
step "STEP 2: Checking Running Services"

CONTAINER_COUNT=$(docker compose ps -q 2>/dev/null | wc -l)

if [ "$CONTAINER_COUNT" -eq 0 ]; then
    info "No running Smart NOC services found"
else
    info "Found $CONTAINER_COUNT running service(s):"
    docker compose ps --format "table {{.Service}}\t{{.State}}" | tail -n +2 | while read line; do
        echo "   - $line"
    done
fi

# ══════════════════════════════════════════════════════════
# STEP 3: Export Database (Optional Backup)
# ══════════════════════════════════════════════════════════
step "STEP 3: Data Backup (Optional)"

if [ "$KEEP_DATA" = false ] && [ "$FORCE" = false ]; then
    read -p "Would you like to backup the database before deletion? (y/N): " -r
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        info "Creating database backup..."
        
        BACKUP_DIR="backups"
        mkdir -p "$BACKUP_DIR"
        
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        BACKUP_FILE="$BACKUP_DIR/smart_noc_backup_$TIMESTAMP.sql"
        
        if docker compose exec -T postgres pg_dump -U noc_admin smart_noc > "$BACKUP_FILE" 2>/dev/null; then
            FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
            success "Database backed up: $BACKUP_FILE ($FILE_SIZE)"
        else
            warning "Backup failed"
            read -p "Continue with teardown anyway? (y/N): " -r
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi
    else
        info "Skipping backup"
    fi
else
    info "Backup skipped (keeping data or forced teardown)"
fi

# ══════════════════════════════════════════════════════════
# STEP 4: Stop Services Gracefully
# ══════════════════════════════════════════════════════════
step "STEP 4: Stopping Services"

info "Stopping application services..."
docker compose stop llm-diagnosis correlation-engine anomaly-detector vector-service 2>&1 | grep -v "^WARN" || true

info "Waiting for graceful shutdown (5s)..."
sleep 5

info "Stopping monitoring services..."
docker compose stop grafana kafka-ui 2>&1 | grep -v "^WARN" || true

info "Stopping data pipeline services..."
docker compose stop logstash 2>&1 | grep -v "^WARN" || true

info "Waiting for pipeline drain (3s)..."
sleep 3

info "Stopping infrastructure services..."
docker compose stop kafka elasticsearch redis postgres chromadb 2>&1 | grep -v "^WARN" || true

success "All services stopped"

# ══════════════════════════════════════════════════════════
# STEP 5: Remove Containers
# ══════════════════════════════════════════════════════════
step "STEP 5: Removing Containers"

if [ "$KEEP_DATA" = true ]; then
    info "Removing containers (preserving volumes)..."
    docker compose down 2>&1 | grep -v "^WARN" || true
else
    info "Removing containers and volumes..."
    docker compose down -v 2>&1 | grep -v "^WARN" || true
fi

success "Containers removed"

# ══════════════════════════════════════════════════════════
# STEP 6: Remove Networks
# ══════════════════════════════════════════════════════════
step "STEP 6: Cleaning Up Networks"

info "Removing Docker networks..."
NETWORKS=$(docker network ls --filter name=smart-noc --format "{{.Name}}" 2>/dev/null)

if [ -n "$NETWORKS" ]; then
    echo "$NETWORKS" | while read network; do
        if docker network rm "$network" 2>/dev/null; then
            success "Removed network: $network"
        else
            warning "Could not remove network: $network (may be in use)"
        fi
    done
else
    info "No Smart NOC networks found"
fi

# ══════════════════════════════════════════════════════════
# STEP 7: Remove Images (Optional)
# ══════════════════════════════════════════════════════════
if [ "$KEEP_IMAGES" = false ]; then
    step "STEP 7: Removing Docker Images"
    
    info "Finding Smart NOC images..."
    IMAGES=$(docker images --filter reference="smart-noc*" --format "{{.Repository}}:{{.Tag}}" 2>/dev/null)
    
    if [ -n "$IMAGES" ]; then
        IMAGE_COUNT=$(echo "$IMAGES" | wc -l)
        info "Removing $IMAGE_COUNT image(s)..."
        echo "$IMAGES" | while read image; do
            docker rmi "$image" 2>&1 | grep -v "^WARN" || true
            success "Removed: $image"
        done
    else
        info "No Smart NOC images found"
    fi
else
    step "STEP 7: Preserving Docker Images"
    info "Skipping image removal (use without --keep-images to remove)"
fi

# ══════════════════════════════════════════════════════════
# STEP 8: Clean Python Environment (Optional)
# ══════════════════════════════════════════════════════════
step "STEP 8: Python Environment Cleanup"

if [ -d "venv" ]; then
    if [ "$FORCE" = false ]; then
        read -p "Remove Python virtual environment? (y/N): " -r
    else
        REPLY='n'
    fi
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        info "Removing virtual environment..."
        rm -rf venv
        success "Virtual environment removed"
    else
        info "Virtual environment preserved"
    fi
else
    info "No virtual environment found"
fi

# ══════════════════════════════════════════════════════════
# STEP 9: Validation
# ══════════════════════════════════════════════════════════
step "STEP 9: Validating Cleanup"

# Check for remaining containers
REMAINING=$(docker compose ps -q 2>/dev/null | wc -l)
if [ "$REMAINING" -eq 0 ]; then
    success "No containers running"
else
    warning "Some containers still exist:"
    docker compose ps --format "   - {{.Service}}"
fi

# Check for any smart-noc containers (even stopped ones)
ALL_CONTAINERS=$(docker ps -a --filter name=smart-noc --format "{{.Names}}" 2>/dev/null)
if [ -n "$ALL_CONTAINERS" ]; then
    warning "Stopped containers found (cleaning up):"
    echo "$ALL_CONTAINERS" | while read container; do
        echo "   - $container"
        docker rm -f "$container" 2>&1 | grep -v "^WARN" || true
    done
    success "Forced removal complete"
else
    success "No lingering containers"
fi

# Check for volumes (if they should be removed)
if [ "$KEEP_DATA" = false ]; then
    VOLUMES=$(docker volume ls --filter name=smart-noc --format "{{.Name}}" 2>/dev/null)
    if [ -n "$VOLUMES" ]; then
        warning "Some volumes still exist - removing forcefully:"
        echo "$VOLUMES" | while read volume; do
            echo "   - $volume"
            docker volume rm "$volume" 2>&1 | grep -v "^WARN" || true
        done
        success "All volumes removed"
    else
        success "All volumes removed"
    fi
else
    info "Volumes preserved (--keep-data flag)"
fi

# Final check for any smart-noc resources
FINAL_CHECK=$(docker ps -a --filter name=smart-noc --format "{{.Names}}" 2>/dev/null | wc -l)
if [ "$FINAL_CHECK" -eq 0 ]; then
    success "Environment completely clean - no resources remaining"
else
    warning "Some resources may still exist - manual cleanup may be needed"
fi

# ══════════════════════════════════════════════════════════
# STEP 10: Summary
# ══════════════════════════════════════════════════════════
step "STEP 10: Teardown Complete!"

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

cat << EOF

╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║              ✓ TEARDOWN COMPLETED!                       ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

⏱  Teardown Duration: ${MINUTES}m ${SECONDS}s

📊 CLEANUP SUMMARY:
   
   ✓ Containers:     Removed
   ✓ Networks:       Cleaned
EOF

if [ "$KEEP_DATA" = true ]; then
    echo -e "   ${CYAN}ℹ Volumes:        Preserved${NC}"
else
    echo -e "   ${GREEN}✓ Volumes:        Removed${NC}"
fi

if [ "$KEEP_IMAGES" = true ]; then
    echo -e "   ${CYAN}ℹ Images:         Preserved${NC}"
else
    echo -e "   ${GREEN}✓ Images:         Removed${NC}"
fi

cat << EOF

📋 NEXT STEPS:
   
   - To restart NOC: ./setup-noc.sh
   - To remove all data: ./teardown-noc.sh --force
   - To keep data: ./teardown-noc.sh --keep-data

EOF

if [ "$KEEP_DATA" = false ] && [ -d "backups" ]; then
    RECENT_BACKUPS=$(ls -t backups/*.sql 2>/dev/null | head -3)
    if [ -n "$RECENT_BACKUPS" ]; then
        echo -e "${CYAN}💾 RECENT BACKUPS:${NC}"
        echo "$RECENT_BACKUPS" | while read backup; do
            SIZE=$(du -h "$backup" | cut -f1)
            echo "   - $(basename "$backup") ($SIZE)"
        done
        echo ""
    fi
fi

success "Environment cleaned successfully!"
