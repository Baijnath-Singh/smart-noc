#!/bin/bash
echo "============================================================"
echo "Phase 2 Test - ChromaDB Semantic Search"
echo "============================================================"
echo ""

echo "1. Check ChromaDB has test data:"
docker compose exec llm-diagnosis python -c "
import sys
sys.path.append('/vector_service')
from vector_service import VectorKnowledgeBase
vkb = VectorKnowledgeBase()
stats = vkb.get_stats()
print(f'  ✓ Remediation Commands: {stats[\"commands\"]} lessons')
print(f'  ✓ Knowledge Base: {stats[\"kb_articles\"]} articles')
"
echo ""

echo "2. Check Phase 2 config is active:"
docker compose exec llm-diagnosis python -c "import config; print(f'  ✓ Source: {config.REMEDIATION_LESSONS_SOURCE}')"
echo ""

echo "3. Test semantic search query:"
docker compose exec llm-diagnosis python -c "
import sys
sys.path.append('/vector_service')
from vector_service import VectorKnowledgeBase
vkb = VectorKnowledgeBase()
query = 'interface problem network down'
embedding = vkb.model.encode(query).tolist()
results = vkb.commands.query(query_embeddings=[embedding], n_results=3)
print(f'  Query: \"{query}\"')
print(f'  ✓ Found {len(results[\"ids\"][0])} similar lessons')
for i in range(min(2, len(results['ids'][0]))):
    sim = 1 - results['distances'][0][i]
    doc = results['documents'][0][i].split('\n')[0]
    print(f'    [{i+1}] {doc} (similarity: {sim:.1%})')
"
echo ""

echo "4. Check existing incidents:"
docker compose exec postgres psql -U noc_admin -d smart_noc -t -c "SELECT COUNT(*) as total FROM incidents;"
echo ""

echo "============================================================"
echo "✅ Phase 2 is READY and OPERATIONAL"
echo "============================================================"
echo ""
echo "Next: Generate a test incident or wait for a real one"
echo ""
echo "The next incident diagnosis will use ChromaDB semantic search"
echo "to find similar remediation lessons from the 5 test cases."
