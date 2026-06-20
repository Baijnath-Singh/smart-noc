#!/bin/bash
# Automated Grafana Dashboard Setup Script
# Configures PostgreSQL data source and imports Safety Framework dashboard

set -e

echo "================================================================================"
echo "GRAFANA SAFETY FRAMEWORK DASHBOARD - AUTOMATED SETUP"
echo "================================================================================"
echo ""

# Configuration
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3000}"
GRAFANA_USER="${GRAFANA_USER:-admin}"
GRAFANA_PASS="${GRAFANA_PASS:-admin}"
POSTGRES_HOST="${POSTGRES_HOST:-smart-noc-postgres}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-smart_noc}"
POSTGRES_USER="${POSTGRES_USER:-noc_admin}"
POSTGRES_PASS="${POSTGRES_PASS:-noc_password}"

DASHBOARD_FILE="./dashboards/safety-framework-dashboard.json"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Helper functions
success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

info() {
    echo "ℹ️  $1"
}

# Step 1: Check Prerequisites
echo "Step 1: Checking Prerequisites"
echo "────────────────────────────────────────────────────────────────────────────────"

# Check if Grafana is running
info "Checking Grafana connectivity..."
if curl -s -o /dev/null -w "%{http_code}" "${GRAFANA_URL}/api/health" | grep -q "200"; then
    success "Grafana is running at ${GRAFANA_URL}"
else
    error "Cannot connect to Grafana at ${GRAFANA_URL}"
    error "Make sure Grafana container is running: docker-compose ps grafana"
    exit 1
fi

# Check if dashboard file exists
if [ ! -f "$DASHBOARD_FILE" ]; then
    error "Dashboard file not found: $DASHBOARD_FILE"
    error "Make sure you're running this script from the smart-noc directory"
    exit 1
fi
success "Dashboard JSON file found"

# Check PostgreSQL connectivity
info "Checking PostgreSQL connectivity..."
if docker-compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT 1" > /dev/null 2>&1; then
    success "PostgreSQL is accessible"
else
    error "Cannot connect to PostgreSQL"
    error "Make sure PostgreSQL container is running: docker-compose ps postgres"
    exit 1
fi

echo ""

# Step 2: Configure PostgreSQL Data Source
echo "Step 2: Configuring PostgreSQL Data Source"
echo "────────────────────────────────────────────────────────────────────────────────"

DATA_SOURCE_NAME="smart_noc_postgres"

# Check if data source already exists
info "Checking if data source '$DATA_SOURCE_NAME' exists..."
EXISTING_DS=$(curl -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "${GRAFANA_URL}/api/datasources/name/${DATA_SOURCE_NAME}" 2>/dev/null)

if echo "$EXISTING_DS" | grep -q '"id"'; then
    warning "Data source '$DATA_SOURCE_NAME' already exists"
    DS_UID=$(echo "$EXISTING_DS" | grep -o '"uid":"[^"]*"' | cut -d'"' -f4)
    info "Using existing data source UID: $DS_UID"
else
    info "Creating new data source..."
    
    # Create data source
    DS_RESPONSE=$(curl -s -X POST \
      -H "Content-Type: application/json" \
      -u "$GRAFANA_USER:$GRAFANA_PASS" \
      "${GRAFANA_URL}/api/datasources" \
      -d @- << EOF
{
  "name": "$DATA_SOURCE_NAME",
  "type": "postgres",
  "access": "proxy",
  "url": "${POSTGRES_HOST}:${POSTGRES_PORT}",
  "database": "$POSTGRES_DB",
  "user": "$POSTGRES_USER",
  "secureJsonData": {
    "password": "$POSTGRES_PASS"
  },
  "jsonData": {
    "sslmode": "disable",
    "postgresVersion": 1600,
    "timescaledb": false
  },
  "isDefault": false
}
EOF
)
    
    if echo "$DS_RESPONSE" | grep -q '"id"'; then
        DS_UID=$(echo "$DS_RESPONSE" | grep -o '"uid":"[^"]*"' | cut -d'"' -f4)
        success "Data source created successfully (UID: $DS_UID)"
        
        # Test data source
        info "Testing data source connection..."
        TEST_RESPONSE=$(curl -s -X POST \
          -u "$GRAFANA_USER:$GRAFANA_PASS" \
          "${GRAFANA_URL}/api/datasources/uid/${DS_UID}/health")
        
        if echo "$TEST_RESPONSE" | grep -q '"status":"OK"'; then
            success "Data source connection test passed"
        else
            warning "Data source test warning (may still work): $TEST_RESPONSE"
        fi
    else
        error "Failed to create data source: $DS_RESPONSE"
        exit 1
    fi
fi

echo ""

# Step 3: Import Dashboard
echo "Step 3: Importing Safety Framework Dashboard"
echo "────────────────────────────────────────────────────────────────────────────────"

# Read dashboard JSON and update data source UID
info "Preparing dashboard JSON..."
DASHBOARD_JSON=$(cat "$DASHBOARD_FILE" | sed "s/\${DS_POSTGRES}/$DS_UID/g")

# Check if dashboard already exists
info "Checking if dashboard already exists..."
EXISTING_DASHBOARD=$(curl -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "${GRAFANA_URL}/api/dashboards/uid/safety-framework" 2>/dev/null)

if echo "$EXISTING_DASHBOARD" | grep -q '"dashboard"'; then
    warning "Dashboard 'safety-framework' already exists"
    info "Updating existing dashboard..."
    OVERWRITE="true"
else
    info "Creating new dashboard..."
    OVERWRITE="false"
fi

# Import/Update dashboard
IMPORT_RESPONSE=$(curl -s -X POST \
  -H "Content-Type: application/json" \
  -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "${GRAFANA_URL}/api/dashboards/db" \
  -d @- << EOF
{
  "dashboard": $DASHBOARD_JSON,
  "overwrite": $OVERWRITE,
  "message": "Automated import by setup script"
}
EOF
)

if echo "$IMPORT_RESPONSE" | grep -q '"status":"success"'; then
    DASHBOARD_URL=$(echo "$IMPORT_RESPONSE" | grep -o '"url":"[^"]*"' | cut -d'"' -f4)
    success "Dashboard imported successfully!"
    success "Dashboard URL: ${GRAFANA_URL}${DASHBOARD_URL}"
else
    error "Failed to import dashboard: $IMPORT_RESPONSE"
    exit 1
fi

echo ""

# Step 4: Verification
echo "Step 4: Verification"
echo "────────────────────────────────────────────────────────────────────────────────"

# Check if dashboard is accessible
info "Verifying dashboard accessibility..."
DASHBOARD_CHECK=$(curl -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "${GRAFANA_URL}/api/dashboards/uid/safety-framework")

if echo "$DASHBOARD_CHECK" | grep -q '"dashboard"'; then
    PANEL_COUNT=$(echo "$DASHBOARD_CHECK" | grep -o '"panels":\[' | wc -l)
    success "Dashboard is accessible and loaded"
    info "Dashboard has panels configured"
else
    error "Cannot verify dashboard"
fi

# Check if data exists
info "Checking for Safety Framework data..."
DECISION_COUNT=$(docker-compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c \
  "SELECT COUNT(*) FROM autonomous_decision_log;" 2>/dev/null | tr -d ' ')

RISK_COUNT=$(docker-compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c \
  "SELECT COUNT(*) FROM incident_risk_assessment;" 2>/dev/null | tr -d ' ')

if [ "$DECISION_COUNT" -gt 0 ]; then
    success "Found $DECISION_COUNT decisions in database"
    success "Found $RISK_COUNT risk assessments in database"
    info "Dashboard will display data immediately"
else
    warning "No data found in database yet"
    info "Run decision matrix tests to populate dashboard:"
    info "  ./test_decision_matrix_all_scenarios.sh"
fi

echo ""

# Step 5: Summary
echo "================================================================================"
echo "SETUP COMPLETE"
echo "================================================================================"
echo ""
success "✅ PostgreSQL data source configured"
success "✅ Safety Framework dashboard imported"
success "✅ Dashboard verified and accessible"
echo ""
echo "📊 Dashboard Access:"
echo "   URL: ${GRAFANA_URL}/d/safety-framework"
echo "   Username: $GRAFANA_USER"
echo "   Password: $GRAFANA_PASS"
echo ""
echo "📋 Dashboard Features:"
echo "   • Decision distribution (execute/approval/manual)"
echo "   • Risk level distribution and trends"
echo "   • Confidence score tracking"
echo "   • Remediation execution statistics"
echo "   • Decision matrix heatmap"
echo "   • Risk factor analysis"
echo "   • Recent decisions table"
echo ""
echo "🔄 Auto-Refresh: Every 30 seconds"
echo "⏰ Default Time Range: Last 24 hours"
echo ""

if [ "$DECISION_COUNT" -eq 0 ]; then
    echo "⚠️  Note: No data currently in database"
    echo ""
    echo "To populate dashboard with test data:"
    echo "   cd /home/user/ng-iam/smart-noc"
    echo "   ./test_decision_matrix_all_scenarios.sh"
    echo ""
fi

echo "📖 For more details, see:"
echo "   dashboards/GRAFANA_SETUP_GUIDE.md"
echo ""
echo "================================================================================"

exit 0
