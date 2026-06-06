#!/usr/bin/env python3
"""
Add or Update Knowledge Base Articles in ChromaDB
Usage: python add_kb_article.py
"""

import sys
sys.path.append('/vector_service')
from vector_service import VectorKnowledgeBase

def add_kb_article():
    """Add a new KB article to ChromaDB"""
    
    vkb = VectorKnowledgeBase(
        chromadb_host='chromadb',
        chromadb_port=8000
    )
    
    # Define your new article
    article_id = "KB-024"
    title = "OSPF Neighbor Not Forming"
    
    content = """
OSPF neighbor relationship not forming between routers.

Common Causes:
1. Area mismatch (40%) - Neighbors in different OSPF areas
2. Hello/Dead timer mismatch (25%) - Timers don't match
3. Network type mismatch (15%) - Point-to-point vs broadcast
4. Authentication mismatch (10%) - Different MD5 keys
5. MTU mismatch (10%) - Different interface MTUs

Diagnostic Steps:
1. Check OSPF status: show ip ospf neighbor
2. Verify area: show ip ospf interface <interface>
3. Check timers: show ip ospf interface <interface> | include Timer
4. Verify auth: show ip ospf interface <interface> | include auth
5. Check MTU: show interface <interface> | include MTU

Remediation:
- If area mismatch: Correct OSPF area on interface
- If timer mismatch: Set matching hello/dead timers
- If network type: Configure matching network type
- If auth mismatch: Ensure matching authentication keys
- If MTU: Set matching MTU (typically 1500)
"""
    
    metadata = {
        'event_type': 'OSPF_NEIGHBOR_DOWN',
        'vendor': 'generic',  # or 'cisco', 'juniper'
        'success_rate': 0.90,
        'category': 'troubleshooting'
    }
    
    # Add to ChromaDB
    success = vkb.add_kb_article(
        article_id=article_id,
        title=title,
        content=content.strip(),
        metadata=metadata
    )
    
    if success:
        print(f"✅ Successfully added: {article_id} - {title}")
        
        # Verify
        stats = vkb.get_stats()
        print(f"\nCurrent KB stats: {stats['kb_articles']} articles")
        
        # Test search
        print("\nTesting search...")
        results = vkb.find_relevant_kb(
            query_text="OSPF neighbor not coming up",
            event_type='OSPF_NEIGHBOR_DOWN',
            top_k=1
        )
        if results:
            print(f"✓ Found article: {results[0]['metadata']['title']}")
    else:
        print(f"❌ Failed to add article")

if __name__ == '__main__':
    add_kb_article()
