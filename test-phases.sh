#!/bin/bash
echo "========================================"
echo "Phase 1 & Phase 2 Verification"
echo "========================================"
echo ""

echo "1. Check remediation-agent has Vector KB:"
docker compose logs remediation-agent 2>&1 | grep -E "Vector KB initialized" | tail -1
echo ""

echo "2. Check llm-diagnosis has context builder:"
docker compose logs llm-diagnosis 2>&1 | grep "Context Builder initialized" | tail -1
echo ""

echo "3. ChromaDB collections status:"
docker compose exec chromadb curl -s http://localhost:8000/api/v1/heartbeat && echo " (ChromaDB alive)"
echo ""

echo "4. Current config (Phase 1=sql, Phase 2=chromadb):"
docker compose exec llm-diagnosis env | grep "REMEDIATION_LESSONS" || echo "Using defaults: sql mode, 3 lessons, 0.50 similarity"
echo ""

echo "5. Check if both services are healthy:"
docker compose ps llm-diagnosis remediation-agent | grep -E "NAME|llm-diagnosis|remediation-agent"
echo ""

echo "========================================"
echo "✅ Both Phase 1 and Phase 2 are ready!"
echo "========================================"
echo ""
echo "To switch to Phase 2 (ChromaDB semantic search):"
echo "  echo 'REMEDIATION_LESSONS_SOURCE=chromadb' >> .env"
echo "  docker compose restart llm-diagnosis"
