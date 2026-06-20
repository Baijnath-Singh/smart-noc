#!/usr/bin/env python3
"""
Import JSON KB articles to ChromaDB
Simple script to import validated KB articles from JSON format
"""

import sys
import os
import json
import time
from pathlib import Path

# Add vector-service to path
sys.path.insert(0, '/home/user/ng-iam/smart-noc/services/vector-service')
from vector_service import VectorKnowledgeBase


def load_json_articles(directory: str):
    """Load KB articles from JSON files"""
    articles_dir = Path(directory)
    articles = []
    
    for json_file in articles_dir.glob("*.json"):
        try:
            with open(json_file, 'r') as f:
                article = json.load(f)
                articles.append(article)
                print(f"  ✓ Loaded: {json_file.name}")
        except Exception as e:
            print(f"  ✗ Failed to load {json_file.name}: {e}")
    
    return articles


def format_article_content(article: dict) -> str:
    """Format article into searchable text"""
    parts = []
    
    # Title
    parts.append(f"Title: {article['title']}")
    
    # Symptoms
    if article.get('symptoms'):
        parts.append("\nSymptoms:")
        for symptom in article['symptoms']:
            parts.append(f"  - {symptom}")
    
    # Root causes
    if article.get('root_causes'):
        parts.append("\nRoot Causes:")
        for cause in article['root_causes']:
            parts.append(f"  - {cause}")
    
    # Diagnostic commands
    if article.get('diagnostic_commands'):
        parts.append("\nDiagnostic Commands:")
        for cmd in article['diagnostic_commands']:
            parts.append(f"  - {cmd}")
    
    # Remediation steps
    if article.get('remediation_steps'):
        parts.append("\nRemediation Steps:")
        for step in article['remediation_steps']:
            parts.append(f"  - {step.get('step', 'Unknown step')}")
            if step.get('commands'):
                for cmd in step['commands']:
                    parts.append(f"    > {cmd}")
    
    return "\n".join(parts)


def import_to_chromadb(articles: list, host: str = "localhost", port: int = 8000):
    """Import articles to ChromaDB"""
    print(f"\nConnecting to ChromaDB at {host}:{port}...")
    
    # Wait for ChromaDB to be ready
    max_retries = 5
    vector_kb = None
    
    for i in range(max_retries):
        try:
            vector_kb = VectorKnowledgeBase(
                chromadb_host=host,
                chromadb_port=port
            )
            print("✓ Connected to ChromaDB")
            break
        except Exception as e:
            if i < max_retries - 1:
                print(f"Waiting for ChromaDB... ({i+1}/{max_retries})")
                time.sleep(3)
            else:
                print(f"✗ Failed to connect to ChromaDB: {e}")
                return False
    
    if not vector_kb:
        print("✗ Could not establish ChromaDB connection")
        return False
    
    # Import articles
    print(f"\nImporting {len(articles)} KB articles...")
    success_count = 0
    
    for article in articles:
        try:
            article_id = article['article_id']
            title = article['title']
            content = format_article_content(article)
            
            metadata = {
                'vendor': 'Extreme Networks',
                'platform': article.get('platform', 'EXOS'),
                'category': article.get('category', 'general'),
                'subcategory': article.get('subcategory', ''),
                'version': article.get('version', 'All'),
                'source_url': article.get('source_url', ''),
                'extraction_method': article.get('extraction_method', 'unknown'),
                'confidence': article.get('confidence', 0.0)
            }
            
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
                print(f"  ✗ {article_id}: Failed to import")
                
        except Exception as e:
            print(f"  ✗ {article.get('article_id', 'unknown')}: {e}")
    
    print(f"\n{'='*70}")
    print(f"Successfully imported {success_count}/{len(articles)} articles")
    print(f"{'='*70}")
    
    # Print stats
    try:
        stats = vector_kb.get_stats()
        print(f"\nVector DB Statistics:")
        print(f"  - Incidents: {stats.get('incidents', 0)}")
        print(f"  - KB Articles: {stats.get('kb_articles', 0)}")
        print(f"  - Commands: {stats.get('commands', 0)}")
        print(f"  - Vendor Docs: {stats.get('vendor_docs', 0)}")
    except Exception as e:
        print(f"Could not retrieve stats: {e}")
    
    return success_count > 0


def main():
    """Main entry point"""
    print("="*70)
    print("KB JSON Article Importer for Smart NOC")
    print("="*70)
    
    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser(description='Import JSON KB articles to ChromaDB')
    parser.add_argument('--input', default='kb_sources/validated_articles',
                        help='Directory containing JSON KB articles')
    parser.add_argument('--host', default='localhost',
                        help='ChromaDB host (default: localhost)')
    parser.add_argument('--port', type=int, default=8000,
                        help='ChromaDB port (default: 8000)')
    
    args = parser.parse_args()
    
    # Load articles
    print(f"\nLoading articles from: {args.input}")
    articles = load_json_articles(args.input)
    
    if not articles:
        print("✗ No articles found to import")
        return 1
    
    print(f"✓ Loaded {len(articles)} articles")
    
    # Import to ChromaDB
    success = import_to_chromadb(articles, args.host, args.port)
    
    if success:
        print("\n✓ Import completed successfully!")
        return 0
    else:
        print("\n✗ Import failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
