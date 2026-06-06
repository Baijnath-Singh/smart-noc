#!/usr/bin/env python3
"""
Test Phase 2 ChromaDB Semantic Search
"""
import sys
sys.path.append('/vector_service')

from vector_service import VectorKnowledgeBase

def test_semantic_search():
    """Test semantic similarity search for remediation lessons"""
    
    print("=" * 60)
    print("Phase 2 Semantic Search Test")
    print("=" * 60)
    print()
    
    vkb = VectorKnowledgeBase(chromadb_host='chromadb', chromadb_port=8000)
    
    # Test queries (simulating different incident types)
    test_queries = [
        {
            'name': 'BGP Routing Issue',
            'query': 'BGP session problem routing connectivity',
            'expected': 'Should find BGP, ROUTING, CONNECTIVITY lessons'
        },
        {
            'name': 'Interface Down',
            'query': 'interface down link failure',
            'expected': 'Should find INTERFACE_FLAPPING, CONNECTIVITY lessons'
        },
        {
            'name': 'Network Connectivity',
            'query': 'network connection lost unable to reach',
            'expected': 'Should find CONNECTIVITY, INTERFACE, BGP lessons'
        },
        {
            'name': 'Unknown Problem',
            'query': 'UNKNOWN incident type troubleshooting',
            'expected': 'Should find UNKNOWN and general fixes'
        }
    ]
    
    for i, test in enumerate(test_queries, 1):
        print(f"\n{i}. Test Query: '{test['name']}'")
        print(f"   Search: '{test['query']}'")
        print(f"   Expected: {test['expected']}")
        print()
        
        # Generate query embedding
        query_embedding = vkb.model.encode(test['query']).tolist()
        
        # Search remediation_commands collection
        results = vkb.commands.query(
            query_embeddings=[query_embedding],
            n_results=3
        )
        
        # Display results
        if results['ids'][0]:
            print(f"   Found {len(results['ids'][0])} similar remediation lessons:")
            for j in range(len(results['ids'][0])):
                distance = results['distances'][0][j]
                similarity = 1 - distance
                doc_text = results['documents'][0][j]
                metadata = results['metadatas'][0][j]
                
                # Extract incident type from doc
                lines = doc_text.split('\n')
                incident_type = lines[0].replace('Incident Type: ', '')
                device = lines[1].replace('Device: ', '')
                
                print(f"\n   [{j+1}] Similarity: {similarity:.3f} ({similarity*100:.1f}%)")
                print(f"       Incident Type: {incident_type}")
                print(f"       Device: {device}")
                print(f"       Resolution Time: {metadata.get('resolution_time_seconds')}s")
                print(f"       Actions: {metadata.get('actions_count')}")
        else:
            print("   ❌ No results found")
        
        print()
        print("   " + "-" * 50)
    
    print("\n" + "=" * 60)
    print("✅ Semantic Search Test Complete!")
    print("=" * 60)
    print()
    print("Key Observations:")
    print("  • Similar incidents found across different types")
    print("  • Semantic similarity scores show relevance")
    print("  • Cross-incident-type learning enabled (Phase 2 benefit!)")
    print()
    print("Next: Generate a real incident to test full pipeline")

if __name__ == '__main__':
    test_semantic_search()
