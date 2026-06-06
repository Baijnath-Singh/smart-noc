#!/usr/bin/env python3
"""
ChromaDB Query Tool (REST API - Python 3.8 compatible)
Inspect collections and data in the Smart NOC vector database
"""

import json
import urllib.request
import urllib.error

CHROMADB_URL = "http://localhost:8000"

def make_request(endpoint, method="GET", data=None):
    """Make HTTP request to ChromaDB API"""
    url = f"{CHROMADB_URL}{endpoint}"
    
    if data:
        data = json.dumps(data).encode('utf-8')
        
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('Content-Type', 'application/json')
    
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        raise Exception(f"HTTP {e.code}: {error_body}")

def list_collections():
    """List all collections"""
    return make_request("/api/v1/collections")

def get_collection_by_name(name):
    """Get collection ID by name"""
    collections = list_collections()
    for col in collections:
        if col.get('name') == name:
            return col
    return None

def count_collection(collection_id):
    """Count documents in collection"""
    result = make_request(f"/api/v1/collections/{collection_id}/count", method="GET")
    return result

def get_documents(collection_id, limit=5):
    """Get documents from collection"""
    data = {
        "limit": limit,
        "include": ["documents", "metadatas"]
    }
    return make_request(f"/api/v1/collections/{collection_id}/get", method="POST", data=data)

def main():
    print("=" * 70)
    print("ChromaDB Inspector - Smart NOC Vector Database")
    print("=" * 70)
    
    # Test connection
    try:
        make_request("/api/v1/heartbeat")
        print("✓ Connected to ChromaDB at localhost:8000\n")
    except Exception as e:
        print(f"✗ Failed to connect to ChromaDB: {e}")
        return

    # List all collections
    print("=" * 70)
    print("COLLECTIONS")
    print("=" * 70)
    try:
        collections = list_collections()
        if not collections:
            print("No collections found.")
        else:
            for col in collections:
                name = col.get('name', 'unknown')
                col_id = col.get('id', '')
                try:
                    count_result = count_collection(col_id)
                    count = count_result if isinstance(count_result, int) else 0
                    print(f"  📚 {name}: {count} documents")
                except Exception as e:
                    print(f"  📚 {name}: (count error: {e})")
        print()
    except Exception as e:
        print(f"Error listing collections: {e}\n")

    # Query incidents collection
    print("=" * 70)
    print("INCIDENTS COLLECTION")
    print("=" * 70)
    try:
        # Get collection by name
        col = get_collection_by_name("incidents")
        if not col:
            print("Incidents collection not found.")
        else:
            col_id = col.get('id')
            count_result = count_collection(col_id)
            total = count_result if isinstance(count_result, int) else 0
            print(f"Total incidents stored: {total}\n")
            
            if total > 0:
                # Get first 5 incidents
                results = get_documents(col_id, limit=5)
                
                ids = results.get('ids', [])
                docs = results.get('documents', [])
                metas = results.get('metadatas', [])
                
                for i, (doc_id, doc, meta) in enumerate(zip(ids, docs, metas), 1):
                    print(f"\n{i}. Incident ID: {doc_id}")
                    print(f"   Incident Number: {meta.get('incident_number', 'N/A')}")
                    print(f"   Type: {meta.get('incident_type', 'N/A')}")
                    print(f"   Severity: {meta.get('severity', 'N/A')}")
                    print(f"   Device Count: {meta.get('device_count', 'N/A')}")
                    print(f"   Timestamp: {meta.get('timestamp', 'N/A')}")
                    print(f"   Document Preview: {doc[:200]}...")
                    
                if total > 5:
                    print(f"\n... and {total - 5} more incidents")
            else:
                print("No incidents found in the collection.")
            
    except Exception as e:
        print(f"Incidents collection error: {e}")

    # Query knowledge base collection
    print("\n" + "=" * 70)
    print("KNOWLEDGE BASE COLLECTION")
    print("=" * 70)
    try:
        col = get_collection_by_name("knowledge_base")
        if not col:
            print("Knowledge base collection not found.")
        else:
            col_id = col.get('id')
            count_result = count_collection(col_id)
            total = count_result if isinstance(count_result, int) else 0
            print(f"Total KB articles stored: {total}\n")
            
            if total > 0:
                results = get_documents(col_id, limit=10)
                
                ids = results.get('ids', [])
                docs = results.get('documents', [])
                metas = results.get('metadatas', [])
                
                for i, (doc_id, doc, meta) in enumerate(zip(ids, docs, metas), 1):
                    print(f"\n{i}. Article ID: {doc_id}")
                    print(f"   Category: {meta.get('category', 'N/A')}")
                    print(f"   Title: {meta.get('title', 'N/A')}")
                    print(f"   Document Preview: {doc[:150]}...")
                    
                if total > 10:
                    print(f"\n... and {total - 10} more articles")
            else:
                print("No knowledge base articles found.")
            
    except Exception as e:
        print(f"Knowledge base collection error: {e}")

    # Query vendor documentation collection
    print("\n" + "=" * 70)
    print("VENDOR DOCUMENTATION COLLECTION")
    print("=" * 70)
    try:
        col = get_collection_by_name("vendor_documentation")
        if not col:
            print("Vendor documentation collection not found.")
        else:
            col_id = col.get('id')
            count_result = count_collection(col_id)
            total = count_result if isinstance(count_result, int) else 0
            print(f"Total vendor docs stored: {total}\n")
            
            if total > 0:
                results = get_documents(col_id, limit=5)
                
                ids = results.get('ids', [])
                docs = results.get('documents', [])
                metas = results.get('metadatas', [])
                
                for i, (doc_id, doc, meta) in enumerate(zip(ids, docs, metas), 1):
                    print(f"\n{i}. Doc ID: {doc_id}")
                    print(f"   Vendor: {meta.get('vendor', 'N/A')}")
                    print(f"   Title: {meta.get('title', 'N/A')}")
                    print(f"   Document Preview: {doc[:150]}...")
                    
                if total > 5:
                    print(f"\n... and {total - 5} more docs")
            else:
                print("No vendor documentation found.")
            
    except Exception as e:
        print(f"Vendor documentation collection error: {e}")

    # Query remediation commands collection
    print("\n" + "=" * 70)
    print("REMEDIATION COMMANDS COLLECTION")
    print("=" * 70)
    try:
        col = get_collection_by_name("remediation_commands")
        if not col:
            print("Remediation commands collection not found.")
        else:
            col_id = col.get('id')
            count_result = count_collection(col_id)
            total = count_result if isinstance(count_result, int) else 0
            print(f"Total remediation commands stored: {total}\n")
            
            if total > 0:
                results = get_documents(col_id, limit=5)
                
                ids = results.get('ids', [])
                docs = results.get('documents', [])
                metas = results.get('metadatas', [])
                
                for i, (doc_id, doc, meta) in enumerate(zip(ids, docs, metas), 1):
                    print(f"\n{i}. Command ID: {doc_id}")
                    print(f"   Type: {meta.get('type', 'N/A')}")
                    print(f"   Severity: {meta.get('severity', 'N/A')}")
                    print(f"   Document Preview: {doc[:150]}...")
                    
                if total > 5:
                    print(f"\n... and {total - 5} more commands")
            else:
                print("No remediation commands found.")
            
    except Exception as e:
        print(f"Remediation commands collection error: {e}")

    print("\n" + "=" * 70)
    print("Note: Semantic search requires embeddings and is not available via simple REST API")
    print("      Use the vector-service or Python client for similarity search")
    print("=" * 70)

    print("\n" + "=" * 70)
    print("Inspection complete!")
    print("=" * 70)

if __name__ == "__main__":
    main()
