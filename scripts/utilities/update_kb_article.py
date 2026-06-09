#!/usr/bin/env python3
"""
Update Existing KB Article in ChromaDB
Usage: python update_kb_article.py
"""

import sys
sys.path.append('/vector_service')
from vector_service import VectorKnowledgeBase

def update_kb_article():
    """Update an existing KB article"""
    
    vkb = VectorKnowledgeBase()
    
    article_id = "KB-001"  # Article to update
    
    # Get existing article first
    try:
        existing = vkb.kb_articles.get(ids=[article_id])
        if not existing['ids']:
            print(f"❌ Article {article_id} not found")
            return
        
        print(f"Found existing article: {article_id}")
        print(f"Current content preview: {existing['documents'][0][:100]}...")
        print()
    except Exception as e:
        print(f"Error: {e}")
        return
    
    # Delete old version
    print(f"Deleting old version...")
    vkb.kb_articles.delete(ids=[article_id])
    
    # Add updated version
    print(f"Adding updated version...")
    
    title = "BGP Session Down Troubleshooting (Updated)"
    
    content = """
BGP session down indicates loss of connectivity with BGP neighbor.

Common Causes:
1. Physical link failure (60%) - Interface down, fiber cut, SFP failure
2. Incorrect BGP configuration (20%) - Wrong neighbor IP, AS mismatch
3. Authentication failure (10%) - MD5 password mismatch
4. Access-list blocking TCP 179 (5%)
5. Route flapping causing hold timer expiry (5%)

**NEW** 6. Maximum prefix limit exceeded (2%)
**NEW** 7. Peer shutdown command applied (1%)

Diagnostic Steps:
1. Verify IP connectivity: ping <neighbor-ip>
2. Check interface status: show interface <interface>
3. Verify BGP configuration: show ip bgp summary
4. Check authentication: show ip bgp neighbors | include password
5. Review logs: show logging | include BGP
**NEW** 6. Check prefix limit: show ip bgp neighbors | include prefix
**NEW** 7. Verify admin state: show ip bgp neighbors | include shutdown

Remediation:
- If interface down: Check physical connection, replace SFP if needed
- If config issue: Correct neighbor statement, verify AS numbers
- If auth failure: Ensure matching MD5 passwords on both sides
- If ACL blocking: Permit TCP 179 in access-list
- If flapping: Investigate route stability, adjust timers
**NEW** - If prefix limit: Increase maximum-prefix limit or investigate route leak
**NEW** - If admin shutdown: Remove 'neighbor <ip> shutdown' command

Best Practices:
- Enable BGP logging for troubleshooting
- Use BFD for faster failure detection
- Implement route dampening for stability
"""
    
    metadata = {
        'event_type': 'BGP_SESSION_DOWN',
        'vendor': 'generic',
        'success_rate': 0.92,  # Updated success rate
        'category': 'troubleshooting'
    }
    
    success = vkb.add_kb_article(
        article_id=article_id,
        title=title,
        content=content.strip(),
        metadata=metadata
    )
    
    if success:
        print(f"✅ Successfully updated: {article_id}")
        print(f"   New title: {title}")
        print(f"   New success rate: {metadata['success_rate']}")
    else:
        print(f"❌ Failed to update article")

if __name__ == '__main__':
    update_kb_article()
