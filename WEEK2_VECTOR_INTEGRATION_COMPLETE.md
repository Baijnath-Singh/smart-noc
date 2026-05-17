# Week 2: Vector Service Integration - COMPLETE ✅

**Objective:** Integrate vector service with LLM diagnosis for 20-30% accuracy improvement through semantic similarity search.

---

## Changes Made

### 1. Configuration (`services/llm-diagnosis/config.py`)
Added vector service configuration variables:
```python
# Vector Service Configuration (Week 2)
VECTOR_SERVICE_ENABLED = os.getenv('VECTOR_SERVICE_ENABLED', 'true').lower() == 'true'
VECTOR_CHROMADB_HOST = os.getenv('CHROMADB_HOST', 'chromadb')
VECTOR_CHROMADB_PORT = int(os.getenv('CHROMADB_PORT', '8000'))
VECTOR_SIMILAR_INCIDENTS_COUNT = int(os.getenv('VECTOR_SIMILAR_INCIDENTS_COUNT', '3'))
VECTOR_KB_ARTICLES_COUNT = int(os.getenv('VECTOR_KB_ARTICLES_COUNT', '2'))
VECTOR_MIN_SIMILARITY = float(os.getenv('VECTOR_MIN_SIMILARITY', '0.70'))
```

### 2. Dependencies (`services/llm-diagnosis/requirements.txt`)
Added vector service dependencies:
```
# Vector Service Dependencies (Week 2)
chromadb==0.5.0
sentence-transformers==2.3.1
numpy<2.0  # ChromaDB 0.5.0 incompatible with NumPy 2.0
```

### 3. Context Builder (`services/llm-diagnosis/context_builder.py`)
**Added:**
- Import: `from services.vector_service.vector_service import VectorKnowledgeBase`
- Initialize vector_kb in `__init__()` when enabled
- Call vector search in `build_context()` after traditional search
- New method: `_build_vector_search_query()` - Constructs semantic search query
- New method: `_get_vector_similar_incidents()` - Finds past resolved incidents
- New method: `_get_vector_relevant_kb()` - Retrieves relevant KB articles

**Vector Search Flow:**
```
build_context()
  ├─> _build_vector_search_query()  # Create query from incident details
  ├─> _get_vector_similar_incidents()  # Find top 3 similar incidents
  └─> _get_vector_relevant_kb()  # Find top 2 relevant KB articles
```

### 4. Prompt Templates (`services/llm-diagnosis/prompts/system_prompts.py`)
Added vector search result sections to all templates:
- DEVICE_FAILURE_PROMPT_TEMPLATE
- NETWORK_PERFORMANCE_PROMPT_TEMPLATE  
- SECURITY_BREACH_PROMPT_TEMPLATE
- CONNECTIVITY_ISSUE_PROMPT_TEMPLATE
- UNKNOWN_INCIDENT_PROMPT_TEMPLATE

Each template now includes:
```
{vector_similar_incidents}

{vector_kb_articles}
```

### 5. Diagnosis Service (`services/llm-diagnosis/diagnosis_service.py`)
Updated prompt formatting to pass vector results:
```python
vector_similar_incidents=context.get('vector_similar_incidents', ''),
vector_kb_articles=context.get('vector_kb_articles', ''),
```

### 6. Docker Compose (`docker-compose.yml`)
**llm-diagnosis service updates:**
- Added volume mount: `./services/vector-service:/app/services/vector_service:ro`
- Added 6 environment variables for vector configuration
- Added dependency: `chromadb` (service_started condition)

---

## How It Works

### Vector-Enhanced Context Flow

```
Incident Created
    ↓
Context Builder receives incident
    ↓
Traditional search: PostgreSQL similar incidents
    ↓
Vector search (NEW):
    ├─> Build query from incident type, description, device, severity
    ├─> ChromaDB similarity search for past incidents (top 3, >0.70 similarity)
    └─> ChromaDB similarity search for KB articles (top 2, >0.70 similarity)
    ↓
Context enriched with vector results
    ↓
LLM receives enhanced prompt with:
    - Traditional context (anomalies, device history)
    - Vector similar incidents (semantic matches)
    - Vector KB articles (expert knowledge)
    ↓
LLM generates diagnosis with better accuracy
```

### Vector Search Query Construction

From incident: `{type: "BGP_PEER_DOWN", description: "BGP session down", device: "router-01"}`

Builds query: `"BGP_PEER_DOWN incident: BGP session down (device: router-01, severity: CRITICAL)"`

### Sample Vector Results in Prompt

**Vector Similar Incidents (from past resolved cases):**
```
**Vector Search - Similar Past Incidents:**
Found 3 semantically similar resolved incidents:

1. [Relevance: 0.89] Incident #1042 (CONNECTIVITY_ISSUE)
   Device: core-router-02 | Severity: CRITICAL | Resolved: 2024-01-15
   Root Cause: BGP peer reset due to keepalive timeout (MTU mismatch on transit link)
   Resolution: Adjusted MTU to 1500 on both sides, BGP session restored in 2 minutes
   
2. [Relevance: 0.82] Incident #987 (BGP_PEER_DOWN)
   Device: edge-router-05 | Severity: HIGH | Resolved: 2024-01-10
   Root Cause: BGP authentication mismatch after password rotation
   Resolution: Corrected MD5 password on neighbor config, peer came up immediately
```

**Vector KB Articles (from knowledge base):**
```
**Vector Search - Relevant Knowledge Base Articles:**
Found 2 relevant KB articles:

1. [Relevance: 0.91] KB-001: BGP Session Flapping - Root Causes & Remediation
   Category: BGP | Success Rate: 95%
   Key Points:
   - Check keepalive/holdtime timers (default 60/180)
   - Verify MTU consistency across path
   - Review authentication config
   - Monitor CPU load on routing process
   Diagnostic Commands:
   - show ip bgp summary
   - show ip bgp neighbors <IP>
   - ping <peer-ip> df-bit size 1500
```

### Benefits

1. **Semantic Understanding:** Finds incidents with similar meaning, not just exact keyword matches
   - "BGP peer down" matches "BGP session flapping" (relevance 0.82)
   - "High CPU" matches "Router performance degraded" (relevance 0.76)

2. **Expert Knowledge Injection:** KB articles provide proven diagnostic/remediation patterns
   - 20 curated articles covering common network issues
   - Vendor-specific guidance
   - Success rates from past resolutions

3. **Better Context → Better Diagnosis:**
   - LLM sees what worked in similar situations
   - Reduces hallucination by grounding in real cases
   - Expected 20-30% improvement in diagnosis accuracy

---

## Testing Plan

### 1. Rebuild and Restart Service
```powershell
# Rebuild with new dependencies (will take 2-3 minutes)
docker compose build --no-cache llm-diagnosis

# Restart service
docker compose up -d llm-diagnosis

# Verify vector initialization in logs
docker compose logs llm-diagnosis --tail 50
```

**Expected log output:**
```
INFO | Vector Service enabled, initializing ChromaDB connection
INFO | Vector Knowledge Base initialized successfully
INFO | Loaded sentence-transformers model: all-MiniLM-L6-v2
```

### 2. Generate Test Incident
```bash
# Generate BGP flapping incident
bash -c "./scripts/generate-logs.sh --rate 2 --duration 2 --scenario bgp"
```

### 3. Monitor Diagnosis
```powershell
# Watch diagnosis logs in real-time
docker compose logs llm-diagnosis -f
```

**Look for:**
- Vector search execution: `"Performing vector similarity search..."`
- Similar incidents found: `"Found 2 vector similar incidents (relevance > 0.70)"`
- KB articles retrieved: `"Found 2 relevant KB articles"`
- Context inclusion: Check that diagnosis references similar past cases

### 4. Validate Improvement

**A/B Comparison:**
1. Disable vector search: Set `VECTOR_SERVICE_ENABLED=false` in docker-compose.yml
2. Generate identical incident, compare diagnosis
3. Re-enable vector search, generate again
4. Compare confidence scores and accuracy

**Metrics to track:**
- Diagnosis confidence score (target: increase by 0.10-0.15)
- Root cause accuracy (manual validation)
- Remediation plan completeness
- False positive reduction

---

## Configuration Options

### Environment Variables (docker-compose.yml)

| Variable | Default | Description |
|----------|---------|-------------|
| VECTOR_SERVICE_ENABLED | true | Enable/disable vector search integration |
| CHROMADB_HOST | chromadb | ChromaDB service hostname |
| CHROMADB_PORT | 8000 | ChromaDB API port |
| VECTOR_SIMILAR_INCIDENTS_COUNT | 3 | Max similar incidents to retrieve |
| VECTOR_KB_ARTICLES_COUNT | 2 | Max KB articles to retrieve |
| VECTOR_MIN_SIMILARITY | 0.70 | Minimum relevance threshold (0.0-1.0) |

### Tuning Similarity Threshold

**High threshold (0.80-0.95):** More precise, fewer results
- Use when: KB is large, want only highly relevant matches
- Trade-off: May miss useful similar cases

**Medium threshold (0.65-0.80):** Balanced, good default
- Use when: General purpose, balanced precision/recall
- Trade-off: Good coverage without noise

**Low threshold (0.50-0.65):** Broader matches, more results
- Use when: KB is small, want maximum context
- Trade-off: May include less relevant cases

---

## Expected Outcomes

### Success Criteria
✅ All 12 services running (including llm-diagnosis with vector integration)  
✅ Vector Knowledge Base initializes on startup  
✅ Semantic search finds relevant past incidents (>0.70 similarity)  
✅ KB articles retrieved and included in LLM prompt  
✅ Diagnosis confidence scores improve by 10-15%  
✅ Root cause accuracy improves (measured via manual validation)  

### Performance Impact
- **Build time:** +2-3 minutes first time (sentence-transformers download)
- **Startup time:** +2-5 seconds (model loading)
- **Per-diagnosis:** +50-100ms (vector search overhead)
- **Memory:** +200MB (sentence-transformers model)

### Troubleshooting

**Issue:** `ModuleNotFoundError: No module named 'chromadb'`  
**Fix:** Rebuild service: `docker compose build --no-cache llm-diagnosis`

**Issue:** `ConnectionRefusedError: chromadb:8000`  
**Fix:** Ensure ChromaDB service is running: `docker compose ps chromadb`

**Issue:** No vector results found  
**Fix:** Check similarity threshold, may be too high. Try 0.60-0.65.

**Issue:** Vector search disabled in logs  
**Fix:** Verify `VECTOR_SERVICE_ENABLED=true` in environment

---

## Next Steps (Week 3)

### Auto-Backfill Resolved Incidents
Once incidents are resolved, backfill them into vector DB for future reference:
```python
# scripts/backfill_incidents.py
# - Query PostgreSQL for resolved incidents (root_cause IS NOT NULL)
# - Extract: incident_type, description, device, root_cause, resolution
# - Add to vector DB: vector_kb.add_incident(...)
# - Run daily/weekly to keep KB current
```

### Incremental Update Mechanism
Add hook in llm-diagnosis to auto-add successful diagnoses:
```python
# After diagnosis is marked resolved
if diagnosis_confidence > 0.80:
    self.vector_kb.add_incident(
        incident_type=incident['incident_type'],
        device_id=incident['primary_device'],
        description=incident['description'],
        root_cause=diagnosis['root_cause'],
        resolution=diagnosis['remediation_plan']
    )
```

---

## Files Modified

1. `services/llm-diagnosis/config.py` - Added vector configuration
2. `services/llm-diagnosis/requirements.txt` - Added dependencies
3. `services/llm-diagnosis/context_builder.py` - Integrated vector search (~180 lines added)
4. `services/llm-diagnosis/prompts/system_prompts.py` - Updated all templates
5. `services/llm-diagnosis/diagnosis_service.py` - Pass vector results to prompts
6. `docker-compose.yml` - Added volume mount and environment variables

---

## Completion Status

- [x] Configuration setup
- [x] Dependencies added
- [x] Context builder integration
- [x] Prompt template updates
- [x] Diagnosis service updates
- [x] Docker compose configuration
- [ ] **Service rebuild (NEXT STEP)**
- [ ] **Testing and validation**
- [ ] **Performance metrics collection**

---

## Summary

Week 2 integration is **code complete** ✅. All changes successfully merged. The LLM diagnosis service now:

1. **Connects to vector DB** via mounted vector-service code
2. **Performs semantic search** for similar past incidents
3. **Retrieves relevant KB articles** based on incident characteristics
4. **Enriches LLM context** with vector search results
5. **Expected outcome:** 20-30% better diagnosis accuracy

**Immediate action required:** Rebuild llm-diagnosis service to install new dependencies.

```powershell
docker compose build --no-cache llm-diagnosis
docker compose up -d llm-diagnosis
docker compose logs llm-diagnosis --tail 50
```

Once rebuilt, the system will automatically use vector-enhanced context for all future diagnoses. 🚀
