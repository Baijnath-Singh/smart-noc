#!/usr/bin/env python3
"""
Direct test of enhanced multi-query search inside container
"""
import sys
sys.path.insert(0, '/app')

from vector_service import VectorKnowledgeBase
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Initialize
vkb = VectorKnowledgeBase(chromadb_host="chromadb", chromadb_port=8000)

print("\n" + "="*80)
print("TESTING ENHANCED MULTI-QUERY VECTOR SEARCH")
print("="*80)

# Test case: EXOS interface flapping
query = "Interface keeps going up and down repeatedly causing network disruption"
event_type = "INTERFACE_FLAPPING"
vendor = "extreme"
platform = "exos"

print(f"\nTest Query: {query}")
print(f"Filters: event_type={event_type}, vendor={vendor}, platform={platform}")

# Single-query search
print("\n--- SINGLE-QUERY SEARCH (Legacy) ---")
single_results = vkb.find_relevant_kb(
    query_text=query,
    top_k=3,
    event_type=event_type,
    vendor=vendor,
    platform=platform,
    use_multi_query=False,
    min_relevance=0.50
)

for i, r in enumerate(single_results, 1):
    print(f"  {i}. {r['article_id']}: {r['metadata']['title']}")
    print(f"     Relevance: {r['relevance']:.3f}")

# Multi-query search
print("\n--- MULTI-QUERY SEARCH (Enhanced) ---")
multi_results = vkb.find_relevant_kb(
    query_text=query,
    top_k=3,
    event_type=event_type,
    vendor=vendor,
    platform=platform,
    use_multi_query=True,
    min_relevance=0.50
)

for i, r in enumerate(multi_results, 1):
    print(f"  {i}. {r['article_id']}: {r['metadata']['title']}")
    print(f"     Relevance: {r['relevance']:.3f}")
    print(f"     Matched Queries: {r.get('matched_queries', 1)}")
    print(f"     Query Types: {', '.join(r.get('query_types', ['original']))}")

# Compare
if single_results and multi_results:
    single_avg = sum(r['relevance'] for r in single_results) / len(single_results)
    multi_avg = sum(r['relevance'] for r in multi_results) / len(multi_results)
    improvement = ((multi_avg - single_avg) / single_avg * 100) if single_avg > 0 else 0
    
    print(f"\n📊 COMPARISON:")
    print(f"   Single-query avg relevance: {single_avg:.3f}")
    print(f"   Multi-query avg relevance:  {multi_avg:.3f}")
    print(f"   Improvement: {improvement:+.1f}%")

print("\n✅ Enhanced search test completed!")
