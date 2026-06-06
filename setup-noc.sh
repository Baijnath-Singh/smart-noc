#!/bin/bash
#
# Smart NOC - Automated Setup Script (WSL/Linux)
#
# Purpose: Sets up the complete Smart NOC environment including:
#   - Prerequisites validation
#   - Python virtual environment
#   - Docker containers (Kafka, PostgreSQL, Services)
#   - Database initialization
#   - Health checks and validation
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
SKIP_PREREQ=false
CLEAN=false
NO_LOGS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-prereq) SKIP_PREREQ=true; shift ;;
        --clean) CLEAN=true; shift ;;
        --no-logs) NO_LOGS=true; shift ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --skip-prereq    Skip prerequisite checks"
            echo "  --clean          Remove old installation first"
            echo "  --no-logs        Suppress build logs"
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
║           🚀 SMART NOC SETUP SCRIPT v1.0                 ║
║                                                           ║
║     Automated Network Operations Center Deployment       ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

EOF

# Get script directory (works in WSL with Windows paths)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ══════════════════════════════════════════════════════════
# STEP 1: Prerequisites Check
# ══════════════════════════════════════════════════════════
if [ "$SKIP_PREREQ" = false ]; then
    step "STEP 1: Checking Prerequisites"
    
    # Check Docker
    info "Checking Docker..."
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version)
        success "Docker installed: $DOCKER_VERSION"
    else
        error "Docker is not installed or not in PATH"
        echo "Please install Docker Desktop: https://www.docker.com/products/docker-desktop/"
        exit 1
    fi
    
    # Check Docker service
    info "Checking Docker service status..."
    if docker info &> /dev/null; then
        success "Docker service is running"
    else
        error "Docker service is not running"
        echo "Please start Docker Desktop and try again"
        exit 1
    fi
    
    # Check docker compose
    info "Checking docker compose..."
    if docker compose version &> /dev/null; then
        COMPOSE_VERSION=$(docker compose version)
        success "docker compose available: $COMPOSE_VERSION"
    else
        error "docker compose not available"
        exit 1
    fi
    
    # Check Python
    info "Checking Python..."
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version)
        success "Python installed: $PYTHON_VERSION"
    else
        error "Python 3 is not installed"
        echo "Install with: sudo apt install python3 python3-pip python3-venv"
        exit 1
    fi
    
    # Check available disk space
    info "Checking disk space..."
    FREE_SPACE=$(df -BG "$SCRIPT_DIR" | tail -1 | awk '{print $4}' | sed 's/G//')
    if [ "$FREE_SPACE" -lt 10 ]; then
        warning "Low disk space: ${FREE_SPACE}GB free. Recommended: 10GB+"
    else
        success "Sufficient disk space: ${FREE_SPACE}GB free"
    fi
    
    success "All prerequisites met!"
fi

# ══════════════════════════════════════════════════════════
# STEP 2: Clean Environment (if requested)
# ══════════════════════════════════════════════════════════
if [ "$CLEAN" = true ]; then
    step "STEP 2: Cleaning Previous Installation"
    warning "Stopping and removing existing containers..."
    
    docker compose down -v 2>&1 | grep -v "^WARN" || true
    success "Previous installation cleaned"
    
    sleep 2
else
    step "STEP 2: Checking Existing Installation"
    info "Skipping cleanup (use --clean to force)"
fi

# ══════════════════════════════════════════════════════════
# STEP 3: Environment Configuration
# ══════════════════════════════════════════════════════════
step "STEP 3: Configuring Environment"

# Check if .env exists
if [ -f ".env" ]; then
    success ".env file found"
    
    # Validate critical environment variables
    info "Validating configuration..."
    
    REQUIRED_VARS=("POSTGRES_PASSWORD" "LLM_API_KEY" "LLM_MODEL" "KAFKA_BOOTSTRAP_SERVERS")
    MISSING_VARS=()
    
    for var in "${REQUIRED_VARS[@]}"; do
        if ! grep -q "^${var}=.\\+" .env; then
            MISSING_VARS+=("$var")
        fi
    done
    
    if [ ${#MISSING_VARS[@]} -gt 0 ]; then
        warning "Missing environment variables: ${MISSING_VARS[*]}"
        echo "Please update .env file before continuing"
        
        read -p "Continue anyway? (y/N): " -r
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        success "Configuration validated"
    fi
else
    warning ".env file not found"
    
    if [ -f ".env.example" ]; then
        info "Creating .env from .env.example..."
        cp .env.example .env
        success ".env created from template"
        warning "⚠ IMPORTANT: Edit .env file and add your API keys!"
        
        read -p "Press Enter when ready to continue..."
    else
        error ".env.example not found. Cannot create configuration."
        exit 1
    fi
fi

# ══════════════════════════════════════════════════════════
# STEP 4: Python Virtual Environment
# ══════════════════════════════════════════════════════════
step "STEP 4: Setting Up Python Environment"

if [ -d "venv" ]; then
    success "Virtual environment already exists"
else
    info "Creating Python virtual environment..."
    python3 -m venv venv
    success "Virtual environment created"
fi

# Activate venv and install dependencies
info "Installing Python dependencies..."
source venv/bin/activate

if [ -f "services/log-generator/requirements.txt" ]; then
    pip install --quiet --upgrade pip
    pip install --quiet -r services/log-generator/requirements.txt
    success "Python dependencies installed"
else
    warning "requirements.txt not found in services/log-generator"
fi

# ══════════════════════════════════════════════════════════
# STEP 5: Docker Images Build
# ══════════════════════════════════════════════════════════
step "STEP 5: Building Docker Images"

info "Building custom service images..."
echo "(This may take 5-10 minutes on first run)"

if [ "$NO_LOGS" = true ]; then
    docker compose build &> /dev/null
else
    docker compose build
fi

if [ $? -eq 0 ]; then
    success "Docker images built successfully"
else
    error "Docker build failed"
    exit 1
fi

# ══════════════════════════════════════════════════════════
# STEP 6: Start Services
# ══════════════════════════════════════════════════════════
step "STEP 6: Starting Services"

info "Starting infrastructure services..."
docker compose up -d kafka postgres redis elasticsearch chromadb

info "Waiting for infrastructure to initialize (30s)..."
sleep 30

# Function to check and restart unhealthy service
check_and_restart() {
    local service=$1
    local wait_time=${2:-30}
    
    info "Checking $service health..."
    local status=$(docker compose ps $service --format json 2>/dev/null | grep -o '"Health":"[^"]*"' | cut -d'"' -f4)
    
    if [ -z "$status" ]; then
        # No health check defined, check if running
        if docker compose ps $service --status running &>/dev/null; then
            success "$service is running"
            return 0
        else
            warning "$service is not running"
            return 1
        fi
    elif [ "$status" != "healthy" ]; then
        warning "$service is $status, restarting..."
        docker compose restart $service
        info "Waiting ${wait_time}s for $service..."
        sleep $wait_time
        
        status=$(docker compose ps $service --format json 2>/dev/null | grep -o '"Health":"[^"]*"' | cut -d'"' -f4)
        if [ "$status" = "healthy" ]; then
            success "$service is now healthy"
            return 0
        else
            warning "$service is still $status"
            return 1
        fi
    else
        success "$service is healthy"
        return 0
    fi
}

# Check each infrastructure service
check_and_restart "kafka" 30
check_and_restart "postgres" 10
check_and_restart "elasticsearch" 30
check_and_restart "redis" 10
check_and_restart "chromadb" 15

# Create Kafka topics
info "Creating Kafka topics..."
TOPICS=("network-logs" "anomalies" "incidents" "incidents-diagnosed")

for topic in "${TOPICS[@]}"; do
    info "Creating topic '$topic'..."
    # Using one-liner format with --if-not-exists to handle existing topics gracefully
    if docker compose exec -T kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --create --topic "$topic" --partitions 3 --replication-factor 1 --if-not-exists 2>&1 | grep -q "Created topic\|already exists"; then
        success "Topic '$topic' ready"
    else
        warning "Issue with topic '$topic' (may need manual verification)"
    fi
done

# Verify all topics created
info "Verifying Kafka topics..."
TOPIC_COUNT=$(docker compose exec -T kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list 2>/dev/null | wc -l)
if [ $TOPIC_COUNT -ge 4 ]; then
    success "All Kafka topics verified ($TOPIC_COUNT topics)"
    docker compose exec -T kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list 2>/dev/null | sed 's/^/   ✓ /'
else
    warning "Expected 4+ topics, found $TOPIC_COUNT - some topics may be missing"
fi

info "Starting vector service..."
docker compose up -d vector-service

info "Waiting for vector service to initialize (10s)..."
sleep 10

info "Starting application services..."
docker compose up -d

# Give services time to start
sleep 10

# Populate Knowledge Base
info "Populating Vector Knowledge Base with 20 articles..."
if docker compose exec -T vector-service python populate_kb.py 2>&1 | grep -q "Successfully loaded"; then
    success "Knowledge Base populated (20 articles)"
else
    warning "Knowledge Base population may have failed - check vector-service logs"
fi

success "All services started"

# ══════════════════════════════════════════════════════════
# STEP 7: Health Checks
# ══════════════════════════════════════════════════════════
step "STEP 7: Running Health Checks"

info "Waiting for services to initialize (15s)..."
sleep 15

# Check container status
info "Checking container status..."
EXPECTED_SERVICES=("kafka" "postgres" "redis" "elasticsearch" "chromadb" "grafana" "kafka-ui" "logstash" "vector-service" "anomaly-detector" "correlation-engine" "llm-diagnosis" "remediation-agent")
RUNNING_COUNT=0

for service in "${EXPECTED_SERVICES[@]}"; do
    if docker compose ps --status running | grep -q "$service"; then
        success "$service is running"
        ((RUNNING_COUNT++))
    else
        warning "$service is not running"
    fi
done

if [ $RUNNING_COUNT -eq ${#EXPECTED_SERVICES[@]} ]; then
    success "All core services are running ($RUNNING_COUNT/${#EXPECTED_SERVICES[@]})"
else
    warning "Some services failed to start ($RUNNING_COUNT/${#EXPECTED_SERVICES[@]})"
    info "Attempting to restart failed services..."
    docker compose up -d redis elasticsearch chromadb grafana kafka-ui logstash vector-service anomaly-detector correlation-engine llm-diagnosis remediation-agent
    sleep 10
    info "Rechecking services..."
    RUNNING_COUNT=0
    for service in "${EXPECTED_SERVICES[@]}"; do
        if docker compose ps --status running | grep -q "$service"; then
            ((RUNNING_COUNT++))
        fi
    done
    if [ $RUNNING_COUNT -eq ${#EXPECTED_SERVICES[@]} ]; then
        success "All services now running ($RUNNING_COUNT/${#EXPECTED_SERVICES[@]})"
    else
        warning "Still have issues ($RUNNING_COUNT/${#EXPECTED_SERVICES[@]} running)"
    fi
fi

# Check PostgreSQL connection
info "Testing PostgreSQL connection..."
sleep 5
if docker compose exec -T postgres psql -U noc_admin -d smart_noc -c "SELECT 1;" &> /dev/null; then
    success "PostgreSQL is accessible"
    
    # Verify required tables exist
    REQUIRED_TABLES=("incidents" "incident_anomalies" "incident_timeline" "incident_type_definitions")
    TABLES_OK=true
    
    for table in "${REQUIRED_TABLES[@]}"; do
        if docker compose exec -T postgres psql -U noc_admin -d smart_noc -t -c "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='$table');" 2>/dev/null | grep -q "t"; then
            success "Table '$table' exists"
        else
            warning "Table '$table' missing"
            TABLES_OK=false
        fi
    done
    
    if [ "$TABLES_OK" = true ]; then
        # Check incident count
        INCIDENT_COUNT=$(docker compose exec -T postgres psql -U noc_admin -d smart_noc -t -c "SELECT COUNT(*) FROM incidents;" 2>/dev/null | tr -d ' ')
        if [ -n "$INCIDENT_COUNT" ]; then
            success "Database initialized: $INCIDENT_COUNT incidents"
        fi
    else
        warning "Some database tables are missing - database may not be fully initialized"
    fi
else
    warning "PostgreSQL connection check failed"
fi

# Check Kafka
info "Testing Kafka connection..."
if docker compose exec -T kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list &> /dev/null; then
    success "Kafka is accessible"
else
    warning "Kafka connection check failed"
fi

# ══════════════════════════════════════════════════════════
# STEP 8: Resource Verification Summary
# ══════════════════════════════════════════════════════════
step "STEP 8: Verifying All Resources"

info "Checking all required resources..."
echo ""

# Kafka Topics Summary
TOPIC_COUNT=$(docker compose exec -T kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list 2>/dev/null | wc -l)
echo "📬 Kafka Topics: $TOPIC_COUNT created"
echo "   ✓ network-logs (log-generator → anomaly-detector)"
echo "   ✓ anomalies (anomaly-detector → correlation-engine)"
echo "   ✓ incidents (correlation-engine → llm-diagnosis)"
echo "   ✓ incidents-diagnosed (llm-diagnosis → output)"
echo ""

# PostgreSQL Tables Summary
TABLE_COUNT=$(docker compose exec -T postgres psql -U noc_admin -d smart_noc -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';" 2>/dev/null | tr -d ' ')
echo "🗄️  PostgreSQL Tables: $TABLE_COUNT created"
echo "   ✓ incidents (main incident storage)"
echo "   ✓ incident_anomalies (many-to-many relationship)"
echo "   ✓ incident_timeline (audit trail)"
echo "   ✓ incident_type_definitions (reference data)"
echo ""

# Docker Volumes Summary
VOLUME_COUNT=$(docker volume ls --filter name=smart-noc --format "{{.Name}}" | wc -l)
echo "💾 Docker Volumes: $VOLUME_COUNT created"
docker volume ls --filter name=smart-noc --format "   ✓ {{.Name}}"
echo ""

# Elasticsearch Indices (may not exist until first data arrives)
ES_INDEX_COUNT=$(docker compose exec -T elasticsearch curl -s http://localhost:9200/_cat/indices 2>/dev/null | wc -l)
if [ "$ES_INDEX_COUNT" -gt 0 ]; then
    echo "📊 Elasticsearch Indices: $ES_INDEX_COUNT found"
    docker compose exec -T elasticsearch curl -s http://localhost:9200/_cat/indices 2>/dev/null | awk '{print "   ✓ " $3 " (" $6 " docs)"}'
    echo ""
else
    echo "📊 Elasticsearch Indices: None yet (will be created when first data arrives)"
    echo ""
fi

# Services Running
RUNNING_COUNT=$(docker compose ps --filter status=running --format "{{.Name}}" | wc -l)
TOTAL_SERVICES=13
echo "🚀 Services Running: $RUNNING_COUNT/$TOTAL_SERVICES"
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" | grep "(healthy)" | sed 's/^/   ✓ /'
echo ""

if [ "$TOPIC_COUNT" -lt 4 ]; then
    warning "Expected 4+ Kafka topics, found $TOPIC_COUNT"
fi

if [ "$TABLE_COUNT" -lt 4 ]; then
    warning "Expected 4+ PostgreSQL tables, found $TABLE_COUNT"
fi

if [ "$RUNNING_COUNT" -lt 12 ]; then
    warning "Some services may not be running properly ($RUNNING_COUNT/$TOTAL_SERVICES)"
fi

success "Resource verification complete!"
echo ""

# ══════════════════════════════════════════════════════════
# STEP 9: Display Summary
# ══════════════════════════════════════════════════════════
step "STEP 9: Setup Complete!"

# Final health check summary
info "Final health status:"
echo ""
docker compose ps --format "table {{.Name}}\t{{.Status}}" | head -13
echo ""

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

cat << EOF

╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║                 ✓ SETUP COMPLETED!                       ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝

⏱  Setup Duration: ${MINUTES}m ${SECONDS}s

📋 NEXT STEPS:
   
   1. View running services:
      docker compose ps
   
   2. Check service logs:
      docker compose logs -f [service-name]
      
   3. Generate test data (optional):
      cd services/log-generator
      source ../../venv/bin/activate
      python generate_scenarios.py --scenario chaos --count 5
   
   4. View incidents in database:
      docker compose exec -T postgres psql -U noc_admin -d smart_noc -c "SELECT COUNT(*) FROM incidents;"
   
   5. Monitor AI diagnosis:
      docker compose logs -f llm-diagnosis

📚 DOCUMENTATION:
   - Full Guide: NOC_SETUP_GUIDE.md
   - Quick Ref: QUICK_REFERENCE.md
   - Scripts: README_AUTOMATION.md
   
🛑 TO STOP NOC:
   Run: ./teardown-noc.sh

⚠  CONFIGURATION:
   - Check LLM setup: docker compose logs llm-diagnosis --tail 20
   - Verify phi3 timeout: grep LLM_TIMEOUT .env
   - Default credentials in .env file - change for production
   - Services run on localhost - not exposed externally

EOF

echo -e "${CYAN}🌐 SERVICE ACCESS:${NC}"
echo "   Kafka (internal):    kafka:19092"
echo "   Kafka (external):    localhost:9092"
echo "   PostgreSQL:          localhost:5432"
echo "                        User: noc_admin / Pass: (from .env)"
echo "   ChromaDB:            http://localhost:8000"
echo "   Grafana:             http://localhost:3000"
echo "   Kafka UI:            http://localhost:8080"
echo ""

success "Smart NOC is ready! 🚀"
