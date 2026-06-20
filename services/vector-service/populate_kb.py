"""
Populate Vector Database with Knowledge Base Articles
Run this script to load the 20 KB articles into ChromaDB
"""

import yaml
import sys
import os
import time
from vector_service import VectorKnowledgeBase

def load_kb_articles(yaml_file: str = "knowledge_base.yaml"):
    """Load KB articles from YAML file"""
    print(f"Loading KB articles from {yaml_file}...")
    
    with open(yaml_file, 'r') as f:
        data = yaml.safe_load(f)
    
    articles = data.get('articles', [])
    print(f"Found {len(articles)} articles")
    
    return articles

def populate_vector_db(articles):
    """Populate vector database with KB articles"""
    print("\nInitializing Vector Knowledge Base...")
    
    # Wait for ChromaDB to be ready
    max_retries = 10
    for i in range(max_retries):
        try:
            vector_kb = VectorKnowledgeBase(
                chromadb_host=os.getenv("CHROMADB_HOST", "chromadb"),
                chromadb_port=int(os.getenv("CHROMADB_PORT", "8000"))
            )
            print("✓ Connected to ChromaDB")
            break
        except Exception as e:
            if i < max_retries - 1:
                print(f"Waiting for ChromaDB... ({i+1}/{max_retries})")
                time.sleep(5)
            else:
                print(f"✗ Failed to connect to ChromaDB: {e}")
                return False
    
    # Populate articles
    print(f"\nPopulating {len(articles)} KB articles...")
    success_count = 0
    
    for article in articles:
        article_id = article['id']
        title = article['title']
        content = article['content']
        
        metadata = {
            'event_type': article['event_type'],
            'vendor': article['vendor'],
            'success_rate': article['success_rate'],
            'category': article['category']
        }
        
        # Add platform if present (for vendor-specific articles)
        if 'platform' in article:
            metadata['platform'] = article['platform']
        
        result = vector_kb.add_kb_article(
            article_id=article_id,
            title=title,
            content=content,
            metadata=metadata
        )
        
        if result:
            success_count += 1
            print(f"  ✓ {article_id}: {title}")
        else:
            print(f"  ✗ {article_id}: Failed")
    
    print(f"\n{'='*60}")
    print(f"Successfully loaded {success_count}/{len(articles)} articles")
    print(f"{'='*60}")
    
    # Print stats
    stats = vector_kb.get_stats()
    print(f"\nVector DB Statistics:")
    print(f"  - Incidents: {stats['incidents']}")
    print(f"  - KB Articles: {stats['kb_articles']}")
    print(f"  - Commands: {stats['commands']}")
    print(f"  - Vendor Docs: {stats['vendor_docs']}")
    
    # Test search
    print(f"\n{'='*60}")
    print("Testing semantic search...")
    print(f"{'='*60}")
    
    test_queries = [
        ("BGP neighbor not coming up", "BGP_SESSION_DOWN"),
        ("Interface keeps flapping up and down", "INTERFACE_LINK_FLAP"),
        ("Router CPU is very high", "HIGH_CPU"),
        ("Cannot get IP address from DHCP", "DHCP_POOL_EXHAUSTED")
    ]
    
    for query, expected_type in test_queries:
        print(f"\nQuery: '{query}'")
        results = vector_kb.find_relevant_kb(query_text=query, top_k=2)
        
        if results:
            print(f"  Top result: {results[0]['metadata']['title']}")
            print(f"  Event type: {results[0]['metadata']['event_type']}")
            print(f"  Relevance: {results[0]['relevance']:.3f}")
            
            if results[0]['metadata']['event_type'] == expected_type:
                print(f"  ✓ Correct!")
            else:
                print(f"  ⚠ Expected {expected_type}")
        else:
            print(f"  ✗ No results found")
    
    return True

def main():
    """Main entry point"""
    print("="*60)
    print("Smart NOC - Knowledge Base Population Script")
    print("="*60)
    
    try:
        # Get YAML file from command line argument or use default
        yaml_file = sys.argv[1] if len(sys.argv) > 1 else "knowledge_base.yaml"
        
        # Load articles
        articles = load_kb_articles(yaml_file)
        
        # Populate vector DB
        success = populate_vector_db(articles)
        
        if success:
            print("\n✓ Knowledge base population completed successfully!")
            return 0
        else:
            print("\n✗ Knowledge base population failed!")
            return 1
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
