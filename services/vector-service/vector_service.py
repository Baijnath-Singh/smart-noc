"""
Smart NOC Vector Service
Manages vector database for knowledge base, incident similarity search, and remediation commands
"""

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VectorKnowledgeBase:
    """
    Vector database manager for Smart NOC
    Handles embeddings, similarity search, and knowledge retrieval
    """
    
    def __init__(
        self,
        chromadb_host: str = "chromadb",
        chromadb_port: int = 8000,
        embedding_model: str = "all-MiniLM-L6-v2"
    ):
        """
        Initialize Vector Knowledge Base
        
        Args:
            chromadb_host: ChromaDB server hostname
            chromadb_port: ChromaDB server port
            embedding_model: Sentence transformer model name
        """
        logger.info(f"Initializing Vector Knowledge Base")
        logger.info(f"ChromaDB: {chromadb_host}:{chromadb_port}")
        logger.info(f"Embedding model: {embedding_model}")
        
        # Connect to ChromaDB
        self.client = chromadb.HttpClient(
            host=chromadb_host,
            port=chromadb_port,
            settings=Settings(
                allow_reset=True,
                anonymized_telemetry=False
            )
        )
        
        # Load embedding model (384-dimensional vectors, fast inference)
        logger.info("Loading embedding model...")
        self.model = SentenceTransformer(embedding_model)
        logger.info(f"Model loaded: {embedding_model} ({self.model.get_sentence_embedding_dimension()} dimensions)")
        
        # Initialize collections
        self._init_collections()
        
        logger.info("Vector Knowledge Base initialized successfully")
    
    def _init_collections(self):
        """Initialize ChromaDB collections"""
        
        # Collection 1: Resolved Incidents (for similarity search)
        self.incidents = self.client.get_or_create_collection(
            name="incidents",
            metadata={
                "description": "Historical resolved incidents for similarity search",
                "hnsw:space": "cosine"  # Use cosine similarity
            }
        )
        logger.info(f"Incidents collection: {self.incidents.count()} documents")
        
        # Collection 2: Knowledge Base Articles
        self.kb_articles = self.client.get_or_create_collection(
            name="knowledge_base",
            metadata={
                "description": "Network troubleshooting knowledge base",
                "hnsw:space": "cosine"
            }
        )
        logger.info(f"Knowledge Base collection: {self.kb_articles.count()} documents")
        
        # Collection 3: Remediation Commands
        self.commands = self.client.get_or_create_collection(
            name="remediation_commands",
            metadata={
                "description": "Safe remediation commands by vendor and event type",
                "hnsw:space": "cosine"
            }
        )
        logger.info(f"Remediation Commands collection: {self.commands.count()} documents")
        
        # Collection 4: Vendor Documentation (future)
        self.vendor_docs = self.client.get_or_create_collection(
            name="vendor_documentation",
            metadata={
                "description": "Vendor-specific documentation and best practices",
                "hnsw:space": "cosine"
            }
        )
        logger.info(f"Vendor Documentation collection: {self.vendor_docs.count()} documents")
    
    # =========================================================================
    # INCIDENT MANAGEMENT
    # =========================================================================
    
    def add_incident(
        self,
        incident_id: str,
        incident_type: str,
        description: str,
        root_cause: str,
        remediation: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Store a resolved incident for future similarity search
        
        Args:
            incident_id: Unique incident identifier
            incident_type: Type of incident (BGP_SESSION_DOWN, etc.)
            description: Human-readable description
            root_cause: Identified root cause
            remediation: Steps taken to resolve
            metadata: Additional context (devices, severity, etc.)
        
        Returns:
            True if successful
        """
        try:
            # Build searchable text
            text = f"""
            Incident Type: {incident_type}
            Description: {description}
            Root Cause: {root_cause}
            Remediation: {remediation}
            Devices: {', '.join(metadata.get('devices', []))}
            """.strip()
            
            # Generate embedding
            embedding = self.model.encode(text).tolist()
            
            # Store in ChromaDB
            self.incidents.add(
                ids=[incident_id],
                embeddings=[embedding],
                metadatas=[{
                    "incident_type": incident_type,
                    "success": metadata.get('success', True),
                    "resolution_time_minutes": metadata.get('resolution_time_minutes', 0),
                    "severity": metadata.get('severity', 'UNKNOWN'),
                    "devices": ','.join(metadata.get('devices', [])),
                    "vendor": metadata.get('vendor', 'unknown'),
                    "created_at": metadata.get('created_at', datetime.utcnow().isoformat())
                }],
                documents=[text]
            )
            
            logger.info(f"Stored incident: {incident_id} ({incident_type})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store incident {incident_id}: {e}")
            return False
    
    def find_similar_incidents(
        self,
        query_text: str,
        top_k: int = 5,
        min_similarity: float = 0.60,  # Lowered from 0.75 for better recall
        incident_type: Optional[str] = None,
        vendor: Optional[str] = None
    ) -> List[Dict]:
        """
        Find similar past incidents using semantic search
        
        Args:
            query_text: Current incident description
            top_k: Number of results to return
            min_similarity: Minimum similarity threshold (0-1)
            incident_type: Filter by incident type
            vendor: Filter by vendor
        
        Returns:
            List of similar incidents with similarity scores
        """
        try:
            # Generate query embedding
            query_embedding = self.model.encode(query_text).tolist()
            
            # Build filter (ChromaDB requires $and for multiple conditions)
            where_filter = None
            if incident_type and vendor:
                where_filter = {
                    "$and": [
                        {"incident_type": incident_type},
                        {"vendor": vendor}
                    ]
                }
            elif incident_type:
                where_filter = {"incident_type": incident_type}
            elif vendor:
                where_filter = {"vendor": vendor}
            
            # Search
            results = self.incidents.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_filter
            )
            
            # Format results
            similar = []
            if results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    similarity = 1 - results['distances'][0][i]  # Convert distance to similarity
                    
                    if similarity >= min_similarity:
                        similar.append({
                            "incident_id": results['ids'][0][i],
                            "text": results['documents'][0][i],
                            "metadata": results['metadatas'][0][i],
                            "similarity": round(similarity, 3)
                        })
            
            logger.info(f"Found {len(similar)} similar incidents (threshold: {min_similarity})")
            return similar
            
        except Exception as e:
            logger.error(f"Error finding similar incidents: {e}")
            return []
    
    # =========================================================================
    # KNOWLEDGE BASE MANAGEMENT
    # =========================================================================
    
    def add_kb_article(
        self,
        article_id: str,
        title: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Add knowledge base article
        
        Args:
            article_id: Unique KB article ID
            title: Article title
            content: Article content
            metadata: Event types, vendors, success rate, etc.
        
        Returns:
            True if successful
        """
        try:
            # Build searchable text
            text = f"{title}\n\n{content}"
            
            # Generate embedding
            embedding = self.model.encode(text).tolist()
            
            # Store
            self.kb_articles.add(
                ids=[article_id],
                embeddings=[embedding],
                metadatas=[{
                    "title": title,
                    "event_type": metadata.get('event_type', 'GENERAL'),
                    "vendor": metadata.get('vendor', 'generic'),
                    "success_rate": metadata.get('success_rate', 0.0),
                    "category": metadata.get('category', 'troubleshooting')
                }],
                documents=[text]
            )
            
            logger.info(f"Stored KB article: {article_id} ({title})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store KB article {article_id}: {e}")
            return False
    
    def find_relevant_kb(
        self,
        query_text: str,
        top_k: int = 3,
        event_type: Optional[str] = None,
        vendor: Optional[str] = None
    ) -> List[Dict]:
        """
        Find relevant knowledge base articles
        
        Args:
            query_text: Incident or question description
            top_k: Number of results
            event_type: Filter by event type
            vendor: Filter by vendor
        
        Returns:
            List of relevant KB articles
        """
        try:
            query_embedding = self.model.encode(query_text).tolist()
            
            # Build filter (ChromaDB requires $and for multiple conditions)
            where_filter = None
            if event_type and vendor:
                where_filter = {
                    "$and": [
                        {"event_type": event_type},
                        {"vendor": vendor}
                    ]
                }
            elif event_type:
                where_filter = {"event_type": event_type}
            elif vendor:
                where_filter = {"vendor": vendor}
            
            results = self.kb_articles.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_filter
            )
            
            articles = []
            if results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    articles.append({
                        "article_id": results['ids'][0][i],
                        "text": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i],
                        "relevance": round(1 - results['distances'][0][i], 3)
                    })
            
            logger.info(f"Found {len(articles)} relevant KB articles")
            return articles
            
        except Exception as e:
            logger.error(f"Error finding KB articles: {e}")
            return []
    
    # =========================================================================
    # REMEDIATION COMMANDS
    # =========================================================================
    
    def add_remediation_command(
        self,
        command_id: str,
        command: str,
        description: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Add safe remediation command
        
        Args:
            command_id: Unique command ID
            command: The actual command
            description: What the command does
            metadata: vendor, risk_level, event_types, etc.
        
        Returns:
            True if successful
        """
        try:
            text = f"{command} - {description}"
            embedding = self.model.encode(text).tolist()
            
            self.commands.add(
                ids=[command_id],
                embeddings=[embedding],
                metadatas=[{
                    "command": command,
                    "vendor": metadata.get('vendor', 'generic'),
                    "risk_level": metadata.get('risk_level', 'safe'),
                    "event_types": ','.join(metadata.get('event_types', [])),
                    "requires_approval": metadata.get('requires_approval', False)
                }],
                documents=[text]
            )
            
            logger.info(f"Stored remediation command: {command_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store command {command_id}: {e}")
            return False
    
    def find_remediation_commands(
        self,
        incident_description: str,
        vendor: str,
        risk_level: str = "safe",
        top_k: int = 5
    ) -> List[Dict]:
        """
        Find safe remediation commands for incident
        
        Args:
            incident_description: Description of the issue
            vendor: Device vendor (cisco, juniper, etc.)
            risk_level: Maximum risk level (safe, low, medium)
            top_k: Number of commands to return
        
        Returns:
            List of applicable commands
        """
        try:
            query_embedding = self.model.encode(incident_description).tolist()
            
            # Risk hierarchy
            allowed_risks = {
                "safe": ["safe"],
                "low": ["safe", "low"],
                "medium": ["safe", "low", "medium"]
            }
            
            results = self.commands.query(
                query_embeddings=[query_embedding],
                n_results=top_k * 2,  # Get more, then filter
                where={"vendor": vendor}
            )
            
            commands = []
            if results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    cmd_risk = results['metadatas'][0][i].get('risk_level', 'safe')
                    if cmd_risk in allowed_risks.get(risk_level, ['safe']):
                        commands.append({
                            "command_id": results['ids'][0][i],
                            "command": results['metadatas'][0][i].get('command'),
                            "description": results['documents'][0][i],
                            "metadata": results['metadatas'][0][i],
                            "relevance": round(1 - results['distances'][0][i], 3)
                        })
                        
                        if len(commands) >= top_k:
                            break
            
            logger.info(f"Found {len(commands)} remediation commands (risk: {risk_level})")
            return commands
            
        except Exception as e:
            logger.error(f"Error finding commands: {e}")
            return []
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def get_stats(self) -> Dict[str, int]:
        """Get collection statistics"""
        return {
            "incidents": self.incidents.count(),
            "kb_articles": self.kb_articles.count(),
            "commands": self.commands.count(),
            "vendor_docs": self.vendor_docs.count()
        }
    
    def reset_collection(self, collection_name: str) -> bool:
        """Reset a collection (delete all data) - USE WITH CAUTION"""
        try:
            self.client.delete_collection(name=collection_name)
            self._init_collections()
            logger.warning(f"Reset collection: {collection_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to reset collection {collection_name}: {e}")
            return False


def main():
    """Initialize and run vector service"""
    logger.info("Starting Vector Service...")
    
    # Get configuration from environment
    chromadb_host = os.getenv("CHROMADB_HOST", "chromadb")
    chromadb_port = int(os.getenv("CHROMADB_PORT", "8000"))
    
    # Initialize vector KB
    vector_kb = VectorKnowledgeBase(
        chromadb_host=chromadb_host,
        chromadb_port=chromadb_port
    )
    
    # Print stats
    stats = vector_kb.get_stats()
    logger.info(f"Vector DB Stats: {stats}")
    
    # Keep service running (will add API server later)
    logger.info("Vector Service ready")
    logger.info("Waiting for requests...")
    
    try:
        import time
        while True:
            time.sleep(60)
            # Periodic stats logging
            if datetime.now().minute == 0:
                logger.info(f"Hourly stats: {vector_kb.get_stats()}")
    except KeyboardInterrupt:
        logger.info("Vector Service shutting down...")


if __name__ == "__main__":
    main()
