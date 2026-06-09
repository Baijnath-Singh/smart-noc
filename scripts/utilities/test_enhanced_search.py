#!/usr/bin/env python3
"""
Test script for enhanced multi-query vector search

Compares single-query vs multi-query search results
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'services', 'vector-service'))

from vector_service import VectorKnowledgeBase
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_search_comparison():
    """Compare single-query vs multi-query search"""
    
    # Initialize vector service
    logger.info("Connecting to ChromaDB...")
    vector_kb = VectorKnowledgeBase(chromadb_host="localhost", chromadb_port=8000)
    
    # Test queries for different scenarios
    test_cases = [
        {
            "name": "EXOS Interface Flapping",
            "query": "Interface keeps going up and down repeatedly on switch",
            "event_type": "INTERFACE_FLAPPING",
            "vendor": "extreme",
            "platform": "exos"
        },
        {
            "name": "BGP Neighbor Down",
            "query": "BGP neighbor is not establishing connection",
            "event_type": "BGP_DOWN",
            "vendor": None,
            "platform": None
        },
        {
            "name": "VOSS STP Issue",
            "query": "Spanning tree topology changes causing network disruption",
            "event_type": "CONNECTIVITY_ISSUE",
            "vendor": "extreme",
            "platform": "voss"
        },
        {
            "name": "High CPU Usage",
            "query": "Router CPU utilization very high affecting performance",
            "event_type": "PERFORMANCE_ISSUE",
            "vendor": None,
            "platform": None
        }
    ]
    
    for test_case in test_cases:
        logger.info(f"\n{'='*80}")
        logger.info(f"Test Case: {test_case['name']}")
        logger.info(f"Query: {test_case['query']}")
        logger.info(f"Filters: event_type={test_case['event_type']}, vendor={test_case['vendor']}, platform={test_case['platform']}")
        logger.info(f"{'='*80}\n")
        
        # Single-query search
        logger.info("--- SINGLE-QUERY SEARCH ---")
        single_results = vector_kb.find_relevant_kb(
            query_text=test_case['query'],
            top_k=3,
            event_type=test_case['event_type'],
            vendor=test_case['vendor'],
            platform=test_case['platform'],
            use_multi_query=False,
            min_relevance=0.50
        )
        
        logger.info(f"Found {len(single_results)} articles:")
        for i, result in enumerate(single_results, 1):
            logger.info(f"  {i}. {result['article_id']}: {result['metadata']['title']}")
            logger.info(f"     Relevance: {result['relevance']:.3f}")
            logger.info(f"     Vendor: {result['metadata'].get('vendor')}/{result['metadata'].get('platform', 'N/A')}")
        
        # Multi-query search
        logger.info("\n--- MULTI-QUERY SEARCH (ENHANCED) ---")
        multi_results = vector_kb.find_relevant_kb(
            query_text=test_case['query'],
            top_k=3,
            event_type=test_case['event_type'],
            vendor=test_case['vendor'],
            platform=test_case['platform'],
            use_multi_query=True,
            min_relevance=0.50
        )
        
        logger.info(f"Found {len(multi_results)} articles:")
        for i, result in enumerate(multi_results, 1):
            logger.info(f"  {i}. {result['article_id']}: {result['metadata']['title']}")
            logger.info(f"     Relevance: {result['relevance']:.3f}")
            logger.info(f"     Matched Queries: {result.get('matched_queries', 1)}")
            logger.info(f"     Query Types: {', '.join(result.get('query_types', ['original']))}")
            logger.info(f"     Vendor: {result['metadata'].get('vendor')}/{result['metadata'].get('platform', 'N/A')}")
        
        # Calculate improvement
        if single_results and multi_results:
            single_avg = sum(r['relevance'] for r in single_results) / len(single_results)
            multi_avg = sum(r['relevance'] for r in multi_results) / len(multi_results)
            improvement = ((multi_avg - single_avg) / single_avg * 100) if single_avg > 0 else 0
            
            logger.info(f"\n📊 COMPARISON:")
            logger.info(f"   Single-query avg relevance: {single_avg:.3f}")
            logger.info(f"   Multi-query avg relevance:  {multi_avg:.3f}")
            logger.info(f"   Improvement: {improvement:+.1f}%")
        
        logger.info("")

if __name__ == "__main__":
    try:
        test_search_comparison()
        logger.info("\n✅ Enhanced search test completed successfully!")
    except Exception as e:
        logger.error(f"\n❌ Test failed: {e}", exc_info=True)
        sys.exit(1)
