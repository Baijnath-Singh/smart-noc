#!/bin/bash
#
# Smart NOC Status Verification Script
# Quick check to see if all services are operational
#

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     SMART NOC STATUS CHECK                                ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Container names
CONTAINERS=(
    "smart-noc-kafka"
    "smart-noc-postgres"
    "smart-noc-elasticsearch"
    "smart-noc-redis"
    "smart-noc-logstash"
    "smart-noc-anomaly-detector"
    "smart-noc-correlation-engine"
    "smart-noc-llm-diagnosis"
    "smart-noc-grafana"
    "smart-noc-kafka-ui"
)

echo "═══ Container Status ═══"
echo ""

ALL_RUNNING=true

for container in "${CONTAINERS[@]}"; do
    if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
        # Check if healthy or just running
        health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null)
        if [ "$health" == "healthy" ]; then
            echo -e "${GREEN}✓${NC} $container (healthy)"
        elif [ "$health" == "unhealthy" ]; then
            echo -e "${RED}✗${NC} $container (unhealthy)"
            ALL_RUNNING=false
        else
            echo -e "${GREEN}✓${NC} $container (running)"
        fi
    else
        echo -e "${RED}✗${NC} $container (not running)"
        ALL_RUNNING=false
    fi
done

echo ""
echo "═══ Service Endpoints ═══"
echo ""

# Check endpoints
check_endpoint() {
    local name=$1
    local url=$2
    if curl -s -o /dev/null -w "%{http_code}" "$url" --max-time 2 | grep -q "200\|302"; then
        echo -e "${GREEN}✓${NC} $name: $url"
    else
        echo -e "${YELLOW}⚠${NC} $name: $url (not responding)"
    fi
}

check_endpoint "Elasticsearch" "http://localhost:9200"
check_endpoint "Kafka UI" "http://localhost:8080"
check_endpoint "Grafana" "http://localhost:3000"
check_endpoint "Logstash API" "http://localhost:9600"

echo ""
echo "═══ Kafka Topics ═══"
echo ""

# Check Kafka topics
if docker exec smart-noc-kafka /opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server localhost:9092 \
    --list 2>/dev/null | grep -q "anomalies"; then
    
    topics=$(docker exec smart-noc-kafka /opt/kafka/bin/kafka-topics.sh \
        --bootstrap-server localhost:9092 \
        --list 2>/dev/null | sort)
    
    echo "$topics" | while read -r topic; do
        echo -e "${GREEN}✓${NC} $topic"
    done
else
    echo -e "${RED}✗${NC} Unable to list Kafka topics"
    ALL_RUNNING=false
fi

echo ""
echo "═══ Database Status ═══"
echo ""

# Check PostgreSQL
if docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -c "SELECT 1" &>/dev/null; then
    echo -e "${GREEN}✓${NC} PostgreSQL is accessible"
    
    # Count incidents
    incident_count=$(docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -t -c "SELECT COUNT(*) FROM incidents" 2>/dev/null | tr -d ' ')
    echo -e "  Incidents in database: $incident_count"
else
    echo -e "${RED}✗${NC} PostgreSQL is not accessible"
    ALL_RUNNING=false
fi

echo ""
echo "═══ Service Logs (Last 5 lines) ═══"
echo ""

for container in "smart-noc-anomaly-detector" "smart-noc-correlation-engine" "smart-noc-llm-diagnosis"; do
    echo "--- $container ---"
    docker logs "$container" --tail 5 2>&1 | sed 's/^/  /'
    echo ""
done

echo ""
if [ "$ALL_RUNNING" = true ]; then
    echo -e "${GREEN}✓ Smart NOC is operational!${NC}"
    echo ""
    echo "Access points:"
    echo "  • Grafana:        http://localhost:3000 (admin/admin)"
    echo "  • Kafka UI:       http://localhost:8080"
    echo "  • Elasticsearch:  http://localhost:9200"
else
    echo -e "${RED}⚠ Some services are not running properly${NC}"
    echo ""
    echo "To check specific service logs:"
    echo "  docker logs smart-noc-<service-name>"
    echo ""
    echo "To restart services:"
    echo "  docker compose restart"
fi
