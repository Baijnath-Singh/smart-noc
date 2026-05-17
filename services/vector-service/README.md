# Smart NOC Vector Service

Vector database service for Smart NOC, providing semantic search capabilities for:
- Historical incident similarity matching
- Knowledge base article retrieval
- Remediation command recommendations

## Components

### 1. Vector Service (`vector_service.py`)
Core vector database manager with CRUD operations for:
- **Incidents**: Resolved incidents for similarity search
- **Knowledge Base**: 20 troubleshooting articles
- **Remediation Commands**: Safe commands by vendor/event type
- **Vendor Documentation**: Vendor-specific docs (future)

### 2. Knowledge Base (`knowledge_base.yaml`)
20 curated articles covering:
- BGP issues (4 articles)
- Interface issues (4 articles)
- Routing issues (3 articles)
- Performance issues (3 articles)
- Spanning Tree issues (2 articles)
- Security issues (2 articles)
- DHCP/DNS issues (2 articles)

### 3. Population Script (`populate_kb.py`)
Loads KB articles into ChromaDB with semantic embeddings.

## Quick Start

### 1. Start Services
```bash
# Start ChromaDB and vector service
docker compose up chromadb vector-service -d

# Wait for services to be ready
docker compose logs -f vector-service
```

### 2. Populate Knowledge Base
```bash
# Run population script
docker compose exec vector-service python populate_kb.py
```

### 3. Verify
```bash
# Check stats
docker compose logs vector-service | grep "Vector DB Statistics"
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Smart NOC Services                       │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │   Anomaly    │  │ Correlation  │  │ LLM Diagnosis   │  │
│  │   Detector   │  │   Engine     │  │    Service      │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬────────┘  │
│         │                  │                    │           │
│         └──────────────────┴────────────────────┘           │
│                            │                                │
│                   ┌────────▼────────┐                       │
│                   │ Vector Service  │                       │
│                   │  (This Service) │                       │
│                   └────────┬────────┘                       │
│                            │                                │
│                   ┌────────▼────────┐                       │
│                   │    ChromaDB     │                       │
│                   │ (Vector Store)  │                       │
│                   └─────────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

## API Methods

### VectorKnowledgeBase Class

#### Incident Management
```python
# Store resolved incident
vector_kb.add_incident(
    incident_id="inc-123",
    incident_type="BGP_SESSION_DOWN",
    description="BGP neighbor down on core-router-01",
    root_cause="Faulty SFP module",
    remediation="Replaced SFP, session restored",
    metadata={
        'devices': ['core-router-01'],
        'severity': 'CRITICAL',
        'resolution_time_minutes': 15
    }
)

# Find similar incidents
similar = vector_kb.find_similar_incidents(
    query_text="BGP session keeps going down",
    top_k=5,
    min_similarity=0.75
)
```

#### Knowledge Base
```python
# Find relevant articles
articles = vector_kb.find_relevant_kb(
    query_text="Interface flapping constantly",
    top_k=3,
    event_type="INTERFACE_LINK_FLAP"
)
```

#### Remediation Commands
```python
# Find safe commands
commands = vector_kb.find_remediation_commands(
    incident_description="BGP neighbor down",
    vendor="cisco",
    risk_level="safe",
    top_k=5
)
```

## Embedding Model

**Model**: `all-MiniLM-L6-v2`
- **Dimensions**: 384
- **Speed**: ~14,000 sentences/sec on CPU
- **Quality**: High for semantic search
- **Size**: 80MB

## Configuration

Environment variables:
```bash
CHROMADB_HOST=chromadb       # ChromaDB hostname
CHROMADB_PORT=8000           # ChromaDB port
POSTGRES_HOST=postgres       # PostgreSQL for backfill
POSTGRES_PORT=5432
POSTGRES_DB=smart_noc
POSTGRES_USER=noc_admin
POSTGRES_PASSWORD=noc_password
LOG_LEVEL=INFO
```

## Integration Examples

### From LLM Diagnosis Service
```python
from vector_service import VectorKnowledgeBase

vector_kb = VectorKnowledgeBase()

# Build enhanced context
context = {
    "incident": incident_details,
    "similar_incidents": vector_kb.find_similar_incidents(
        query_text=incident_description,
        top_k=5
    ),
    "knowledge_base": vector_kb.find_relevant_kb(
        query_text=incident_description,
        event_type=incident_type
    )
}

# Send to LLM with rich context
diagnosis = llm.diagnose(context)
```

### From Correlation Engine
```python
# After creating incident, find similar past incidents
similar = vector_kb.find_similar_incidents(
    query_text=f"{incident_type} on {device_id}",
    vendor=device_vendor,
    top_k=3
)

# Use for confidence scoring
if similar and similar[0]['similarity'] > 0.90:
    confidence += 0.2  # Boost confidence if very similar incident found
```

## Performance

- **Embedding generation**: ~50ms per document (CPU)
- **Search query**: ~10-20ms for top-5 results
- **Scalability**: Handles 100K+ documents efficiently

## Future Enhancements

1. **API Server**: REST API for external access
2. **Auto-backfill**: Automatically index resolved incidents from PostgreSQL
3. **Vendor Docs**: Scrape and index Cisco/Juniper documentation
4. **Fine-tuning**: Train custom embedding model on network domain
5. **Multi-modal**: Support for topology diagrams, config snippets

## Troubleshooting

### ChromaDB connection fails
```bash
# Check if ChromaDB is running
docker compose ps chromadb

# Check ChromaDB health
curl http://localhost:8000/api/v1/heartbeat

# View ChromaDB logs
docker compose logs chromadb
```

### Slow embedding generation
- Model downloads on first run (~80MB)
- Subsequent runs use cached model
- Consider GPU acceleration for large-scale indexing

### Low similarity scores
- Ensure query text is descriptive (not just keywords)
- Try different phrasing
- Check if KB article exists for event type

## Maintenance

### Regular Tasks
```bash
# Check stats
docker compose exec vector-service python -c "
from vector_service import VectorKnowledgeBase
vkb = VectorKnowledgeBase()
print(vkb.get_stats())
"

# Re-populate KB (if articles updated)
docker compose exec vector-service python populate_kb.py

# Reset collection (CAUTION: deletes all data)
# docker compose exec vector-service python -c "
# from vector_service import VectorKnowledgeBase
# vkb = VectorKnowledgeBase()
# vkb.reset_collection('knowledge_base')
# "
```

## Contributing

To add new KB articles:
1. Edit `knowledge_base.yaml`
2. Follow existing format
3. Run `populate_kb.py` to index
4. Test with sample queries

## License

Part of Smart NOC project
