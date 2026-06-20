#!/usr/bin/env python3
"""
KB Bulk Importer for ChromaDB

Imports validated KB articles (JSON format) into ChromaDB in batch.

Usage:
    python scripts/kb_bulk_import.py --input kb_sources/validated_articles/
    python scripts/kb_bulk_import.py --input kb_sources/validated_articles/ --batch-size 50
    python scripts/kb_bulk_import.py --input kb_sources/validated_articles/ --collection kb_articles
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict
import time

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    ENDC = '\033[0m'

def print_success(text: str):
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")

def print_error(text: str):
    print(f"{Colors.RED}✗ {text}{Colors.ENDC}")

def print_info(text: str):
    print(f"{Colors.CYAN}ℹ {text}{Colors.ENDC}")

def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.ENDC}")

def load_article_files(input_dir: str) -> List[Dict]:
    """Load all JSON article files from directory."""
    input_path = Path(input_dir)
    
    if not input_path.exists():
        print_error(f"Directory not found: {input_dir}")
        return []
    
    json_files = list(input_path.glob("*.json"))
    
    if not json_files:
        print_warning(f"No JSON files found in: {input_dir}")
        return []
    
    articles = []
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                article = json.load(f)
                articles.append(article)
        except json.JSONDecodeError as e:
            print_error(f"Invalid JSON in {json_file.name}: {e}")
        except Exception as e:
            print_error(f"Error reading {json_file.name}: {e}")
    
    return articles

def create_document_text(article: Dict) -> str:
    """Create document text for ChromaDB embedding."""
    doc_text = f"""
{article.get('title', 'Untitled')}

Vendor: {article.get('vendor', 'Unknown')}
Platform: {article.get('platform', 'Unknown')}
Category: {article.get('category', 'General')} - {article.get('subcategory', 'N/A')}

Symptoms: {', '.join(article.get('symptoms', []))}
Root Causes: {', '.join(article.get('root_causes', []))}

Diagnostic Commands: {', '.join(article.get('diagnostic_commands', []))}

Remediation:
{chr(10).join([f"Step {s.get('step', 0)}: {s.get('description', '')}" for s in article.get('remediation_steps', [])])}

Additional Notes: {article.get('additional_notes', '')}

Keywords: {', '.join(article.get('keywords', []))}
"""
    return doc_text.strip()

def import_batch_to_chromadb(
    articles: List[Dict],
    collection_name: str,
    chromadb_host: str,
    chromadb_port: int,
    batch_size: int = 20
) -> Dict:
    """Import articles to ChromaDB in batches."""
    try:
        import chromadb
        from chromadb.config import Settings
        
        print_info(f"Connecting to ChromaDB at {chromadb_host}:{chromadb_port}")
        
        # Connect to ChromaDB
        client = chromadb.HttpClient(host=chromadb_host, port=chromadb_port)
        
        # Get or create collection
        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Network troubleshooting knowledge base"}
        )
        
        initial_count = collection.count()
        print_info(f"Collection '{collection_name}' currently has {initial_count} articles")
        
        # Prepare batches
        total_articles = len(articles)
        imported = 0
        skipped = 0
        errors = 0
        
        print_info(f"Processing {total_articles} articles in batches of {batch_size}...")
        
        for i in range(0, total_articles, batch_size):
            batch = articles[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_articles + batch_size - 1) // batch_size
            
            print_info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} articles)...")
            
            documents = []
            metadatas = []
            ids = []
            
            for article in batch:
                article_id = article.get('article_id')
                
                if not article_id:
                    print_warning(f"Article missing article_id, skipping")
                    skipped += 1
                    continue
                
                # Check if article already exists
                try:
                    existing = collection.get(ids=[article_id])
                    if existing['ids']:
                        print_warning(f"Article {article_id} already exists, skipping")
                        skipped += 1
                        continue
                except Exception:
                    pass  # Article doesn't exist, proceed
                
                # Prepare document
                doc_text = create_document_text(article)
                
                documents.append(doc_text)
                metadatas.append({
                    "article_id": article_id,
                    "title": article.get('title', 'Untitled')[:500],  # Limit length
                    "vendor": article.get('vendor', 'Unknown'),
                    "platform": article.get('platform', 'Unknown'),
                    "category": article.get('category', 'General'),
                    "subcategory": article.get('subcategory', 'N/A'),
                    "source_url": article.get('source_url', '')
                })
                ids.append(article_id)
            
            # Import batch
            if documents:
                try:
                    collection.add(
                        documents=documents,
                        metadatas=metadatas,
                        ids=ids
                    )
                    imported += len(documents)
                    print_success(f"Batch {batch_num} imported: {len(documents)} articles")
                except Exception as e:
                    print_error(f"Batch {batch_num} failed: {e}")
                    errors += len(documents)
            
            # Brief pause between batches to avoid overwhelming ChromaDB
            time.sleep(0.5)
        
        final_count = collection.count()
        
        return {
            'initial_count': initial_count,
            'final_count': final_count,
            'imported': imported,
            'skipped': skipped,
            'errors': errors,
            'total_processed': total_articles
        }
        
    except ImportError:
        print_error("ChromaDB library not found. Install with: pip install chromadb")
        sys.exit(1)
    except Exception as e:
        print_error(f"Failed to connect to ChromaDB: {e}")
        sys.exit(1)

def display_summary(results: Dict):
    """Display import summary."""
    print("\n" + "="*70)
    print(f"{Colors.BOLD}Import Summary{Colors.ENDC}".center(70))
    print("="*70 + "\n")
    
    print(f"{Colors.BOLD}Initial article count:{Colors.ENDC} {results['initial_count']}")
    print(f"{Colors.BOLD}Final article count:{Colors.ENDC}   {results['final_count']}")
    print(f"{Colors.BOLD}Articles processed:{Colors.ENDC}    {results['total_processed']}")
    print()
    print(f"{Colors.GREEN}✓ Successfully imported: {results['imported']}{Colors.ENDC}")
    print(f"{Colors.YELLOW}⚠ Skipped (duplicates):  {results['skipped']}{Colors.ENDC}")
    print(f"{Colors.RED}✗ Errors:                {results['errors']}{Colors.ENDC}")
    print()
    print(f"{Colors.BOLD}Net change:{Colors.ENDC} +{results['final_count'] - results['initial_count']} articles")
    print("="*70 + "\n")

def main():
    parser = argparse.ArgumentParser(
        description="Import KB articles to ChromaDB in batch",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Import all articles from directory
  python scripts/kb_bulk_import.py --input kb_sources/validated_articles/
  
  # Use custom batch size
  python scripts/kb_bulk_import.py --input kb_sources/validated_articles/ --batch-size 50
  
  # Use custom collection name
  python scripts/kb_bulk_import.py --input kb_sources/validated_articles/ --collection my_kb
  
  # Connect to remote ChromaDB
  python scripts/kb_bulk_import.py --input kb_sources/validated_articles/ --host 192.168.1.100
        """
    )
    
    parser.add_argument(
        '--input',
        type=str,
        required=True,
        help='Input directory containing JSON article files'
    )
    
    parser.add_argument(
        '--collection',
        type=str,
        default='kb_articles',
        help='ChromaDB collection name (default: kb_articles)'
    )
    
    parser.add_argument(
        '--host',
        type=str,
        default='localhost',
        help='ChromaDB host (default: localhost)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='ChromaDB port (default: 8000)'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        default=20,
        help='Number of articles to import per batch (default: 20)'
    )
    
    args = parser.parse_args()
    
    # Load articles
    print_info(f"Loading articles from: {args.input}")
    articles = load_article_files(args.input)
    
    if not articles:
        print_error("No articles to import")
        sys.exit(1)
    
    print_success(f"Loaded {len(articles)} articles")
    
    # Import to ChromaDB
    results = import_batch_to_chromadb(
        articles=articles,
        collection_name=args.collection,
        chromadb_host=args.host,
        chromadb_port=args.port,
        batch_size=args.batch_size
    )
    
    # Display summary
    display_summary(results)
    
    if results['errors'] > 0:
        print_warning("Some articles failed to import. Check logs above for details.")
        sys.exit(1)
    else:
        print_success("All articles processed successfully!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Operation cancelled by user.{Colors.ENDC}")
        sys.exit(0)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
