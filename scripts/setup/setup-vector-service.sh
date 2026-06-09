#!/bin/bash
# Vector Service Setup Script
# Quick start script for Vector DB and Knowledge Base

# Colors
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
GRAY='\033[0;37m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

echo -e "${CYAN}========================================"
echo -e "Smart NOC - Vector Service Setup"
echo -e "========================================${NC}"
echo ""

# Step 1: Start ChromaDB
echo -e "${YELLOW}[1/4] Starting ChromaDB...${NC}"
docker compose up -d chromadb

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Failed to start ChromaDB${NC}"
    exit 1
fi

echo -e "${GREEN}✓ ChromaDB started${NC}"
echo ""

# Step 2: Wait for ChromaDB to be ready
echo -e "${YELLOW}[2/4] Waiting for ChromaDB to be ready...${NC}"
sleep 5

max_retries=12
retry=0
ready=false

while [ $retry -lt $max_retries ] && [ "$ready" = "false" ]; do
    if docker compose exec chromadb curl -s http://localhost:8000/api/v1/heartbeat 2>/dev/null | grep -q "heartbeat"; then
        ready=true
    else
        ((retry++))
        echo -e "${GRAY}  Waiting... ($retry/$max_retries)${NC}"
        sleep 3
    fi
done

if [ "$ready" = "true" ]; then
    echo -e "${GREEN}✓ ChromaDB is ready${NC}"
else
    echo -e "${RED}✗ ChromaDB failed to start${NC}"
    exit 1
fi
echo ""

# Step 3: Build and start Vector Service
echo -e "${YELLOW}[3/4] Building and starting Vector Service...${NC}"
docker compose up -d --build vector-service

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Failed to start Vector Service${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Vector Service started${NC}"
echo ""

# Step 4: Populate Knowledge Base
echo -e "${YELLOW}[4/4] Populating Knowledge Base with 20 articles...${NC}"
sleep 5  # Wait for service to initialize

docker compose exec -T vector-service python populate_kb.py

if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Failed to populate Knowledge Base${NC}"
    echo ""
    echo -e "${YELLOW}Check logs with: docker compose logs vector-service${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}========================================"
echo -e "✓ Vector Service Setup Complete!"
echo -e "========================================${NC}"
echo ""
echo -e "${CYAN}Services running:${NC}"
echo -e "${WHITE}  - ChromaDB:       http://localhost:8000${NC}"
echo -e "${WHITE}  - Vector Service: Running in background${NC}"
echo -e "${WHITE}  - Knowledge Base: 20 articles loaded${NC}"
echo ""
echo -e "${CYAN}Next steps:${NC}"
echo -e "${WHITE}  1. Rebuild LLM service: docker compose build llm-diagnosis${NC}"
echo -e "${WHITE}  2. Restart LLM service: docker compose up -d llm-diagnosis${NC}"
echo -e "${WHITE}  3. View logs:  docker compose logs -f vector-service${NC}"
echo -e "${WHITE}  4. Check stats: docker compose logs vector-service | grep 'Statistics'${NC}"
echo -e "${WHITE}  5. Test search: (see services/vector-service/README.md)${NC}"
echo ""
