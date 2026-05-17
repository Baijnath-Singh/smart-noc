"""
Backfill Script: Populate ChromaDB with Historical Resolved Incidents

This script:
1. Queries PostgreSQL for resolved incidents with diagnoses
2. Creates semantic embeddings for each incident
3. Stores them in ChromaDB 'incidents' collection for similarity search

Usage:
    python backfill_incidents.py
    python backfill_incidents.py --limit 100  # Backfill only 100 incidents
    python backfill_incidents.py --clear      # Clear existing and re-populate
"""

import sys
import os
import argparse
from typing import List, Dict, Any, Optional
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


class IncidentBackfiller:
    """Backfill historical incidents into ChromaDB"""
    
    def __init__(self, clear_existing: bool = False):
        """
        Initialize backfiller
        
        Args:
            clear_existing: If True, clear existing incidents collection before backfilling
        """
        # Database configuration
        self.db_config = {
            'host': os.getenv('POSTGRES_HOST', 'postgres'),
            'port': int(os.getenv('POSTGRES_PORT', 5432)),
            'database': os.getenv('POSTGRES_DB', 'smart_noc'),
            'user': os.getenv('POSTGRES_USER', 'noc_admin'),
            'password': os.getenv('POSTGRES_PASSWORD', 'noc_pass_2024')
        }
        
        # ChromaDB configuration
        chromadb_host = os.getenv('CHROMADB_HOST', 'chromadb')
        chromadb_port = int(os.getenv('CHROMADB_PORT', 8000))
        
        logger.info(f"Connecting to PostgreSQL: {self.db_config['host']}:{self.db_config['port']}")
        logger.info(f"Connecting to ChromaDB: {chromadb_host}:{chromadb_port}")
        
        # Connect to ChromaDB
        self.chroma_client = chromadb.HttpClient(
            host=chromadb_host,
            port=chromadb_port,
            settings=Settings(
                allow_reset=True,
                anonymized_telemetry=False
            )
        )
        
        # Get or create incidents collection
        if clear_existing:
            logger.warning("Clearing existing incidents collection...")
            try:
                self.chroma_client.delete_collection("incidents")
                logger.info("✓ Cleared existing collection")
            except Exception as e:
                logger.info(f"No existing collection to clear: {e}")
        
        self.collection = self.chroma_client.get_or_create_collection(
            name="incidents",
            metadata={
                "description": "Historical resolved incidents for similarity search",
                "hnsw:space": "cosine"
            }
        )
        
        # Load embedding model
        logger.info("Loading embedding model: all-MiniLM-L6-v2")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info(f"✓ Model loaded ({self.model.get_sentence_embedding_dimension()} dimensions)")
        
    def fetch_resolved_incidents(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch resolved incidents from PostgreSQL
        
        Args:
            limit: Maximum number of incidents to fetch (None = all)
        
        Returns:
            List of incident dictionaries
        """
        logger.info("Fetching resolved incidents from PostgreSQL...")
        
        query = """
            SELECT 
                incident_number,
                incident_type,
                severity,
                affected_devices,
                primary_device,
                anomaly_count,
                start_time,
                end_time,
                duration_seconds,
                root_cause,
                remediation_plan,
                correlation_confidence,
                impact_score,
                status,
                created_at,
                resolved_at
            FROM incidents
            WHERE root_cause IS NOT NULL
              AND root_cause != ''
            ORDER BY created_at DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query)
            incidents = cursor.fetchall()
            cursor.close()
            conn.close()
            
            logger.info(f"✓ Fetched {len(incidents)} resolved incidents")
            return [dict(row) for row in incidents]
            
        except Exception as e:
            logger.error(f"Error fetching incidents: {e}")
            return []
    
    def create_incident_text(self, incident: Dict[str, Any]) -> str:
        """
        Create searchable text representation of incident
        
        This text will be embedded for semantic search.
        
        Args:
            incident: Incident dictionary from database
        
        Returns:
            Formatted text for embedding
        """
        # Extract key information
        incident_type = incident.get('incident_type', 'UNKNOWN')
        severity = incident.get('severity', 'MEDIUM')
        primary_device = incident.get('primary_device', 'unknown')
        anomaly_count = incident.get('anomaly_count', 0)
        root_cause = incident.get('root_cause', 'Unknown cause')
        duration = incident.get('duration_seconds', 0) or 0
        
        # Format text for semantic search
        text = f"""
Incident Type: {incident_type}
Severity: {severity}
Device: {primary_device}
Anomalies: {anomaly_count}
Duration: {duration // 60} minutes
Root Cause: {root_cause}
        """.strip()
        
        return text
    
    def create_incident_metadata(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create metadata for ChromaDB storage
        
        Args:
            incident: Incident dictionary from database
        
        Returns:
            Metadata dictionary
        """
        # Extract affected devices
        affected_devices = incident.get('affected_devices', [])
        if isinstance(affected_devices, list) and affected_devices:
            vendor = "cisco"  # Default, would extract from device type in real scenario
        else:
            vendor = "generic"
        
        metadata = {
            "incident_number": incident.get('incident_number'),
            "incident_type": incident.get('incident_type', 'UNKNOWN'),
            "severity": incident.get('severity', 'MEDIUM'),
            "vendor": vendor,
            "primary_device": incident.get('primary_device', 'unknown'),
            "anomaly_count": incident.get('anomaly_count', 0) or 0,
            "duration_seconds": incident.get('duration_seconds', 0) or 0,
            "correlation_confidence": float(incident.get('correlation_confidence', 0.0) or 0.0),
            "impact_score": float(incident.get('impact_score', 0.0) or 0.0),
            "resolved_at": incident.get('resolved_at').isoformat() if incident.get('resolved_at') else None,
        }
        
        return metadata
    
    def backfill(self, limit: Optional[int] = None, batch_size: int = 50) -> int:
        """
        Main backfill process
        
        Args:
            limit: Maximum number of incidents to backfill
            batch_size: Number of incidents to process per batch
        
        Returns:
            Number of incidents backfilled
        """
        logger.info("=" * 60)
        logger.info("STARTING INCIDENT BACKFILL")
        logger.info("=" * 60)
        
        # Check current collection size
        current_count = self.collection.count()
        logger.info(f"Current incidents in ChromaDB: {current_count}")
        
        # Fetch incidents
        incidents = self.fetch_resolved_incidents(limit)
        
        if not incidents:
            logger.warning("No incidents to backfill!")
            return 0
        
        # Process in batches
        backfilled = 0
        total = len(incidents)
        
        for i in range(0, total, batch_size):
            batch = incidents[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total + batch_size - 1) // batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} incidents)...")
            
            # Prepare batch data
            ids = []
            documents = []
            metadatas = []
            embeddings = []
            
            for incident in batch:
                # Create searchable text
                text = self.create_incident_text(incident)
                
                # Create metadata
                metadata = self.create_incident_metadata(incident)
                
                # Generate embedding
                embedding = self.model.encode(text).tolist()
                
                # Add to batch
                incident_id = f"incident-{incident['incident_number']}"
                ids.append(incident_id)
                documents.append(text)
                metadatas.append(metadata)
                embeddings.append(embedding)
            
            # Store batch in ChromaDB
            try:
                self.collection.add(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas,
                    embeddings=embeddings
                )
                backfilled += len(batch)
                logger.info(f"✓ Batch {batch_num} stored ({backfilled}/{total} total)")
                
            except Exception as e:
                logger.error(f"Error storing batch {batch_num}: {e}")
                continue
        
        # Final summary
        logger.info("=" * 60)
        logger.info(f"BACKFILL COMPLETE: {backfilled}/{total} incidents added to ChromaDB")
        logger.info(f"Collection size: {self.collection.count()} incidents")
        logger.info("=" * 60)
        
        return backfilled


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Backfill resolved incidents into ChromaDB")
    parser.add_argument('--limit', type=int, help='Maximum number of incidents to backfill')
    parser.add_argument('--clear', action='store_true', help='Clear existing collection before backfilling')
    parser.add_argument('--batch-size', type=int, default=50, help='Batch size for processing')
    
    args = parser.parse_args()
    
    try:
        backfiller = IncidentBackfiller(clear_existing=args.clear)
        count = backfiller.backfill(limit=args.limit, batch_size=args.batch_size)
        
        if count > 0:
            logger.info(f"🎉 Successfully backfilled {count} incidents!")
            return 0
        else:
            logger.warning("⚠️  No incidents were backfilled")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Backfill failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
