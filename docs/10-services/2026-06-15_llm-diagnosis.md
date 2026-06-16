# LLM Diagnosis Service

**Service Name:** `smart-noc-llm-diagnosis`  
**Image:** `smart-noc_llm-diagnosis` (custom)  
**Technology:** Python 3.9, Groq API, ChromaDB  
**Status:** Core Service  
**Uptime Target:** 99.9%

---

## Overview

The LLM Diagnosis Service is the **AI brain** of Smart NOC. It consumes incidents from Kafka, retrieves relevant knowledge base articles using vector similarity search, generates vendor-specific remediation plans using LLM reasoning, and publishes diagnosed incidents for execution.

**Key Capabilities:**
- **Vendor-Aware Diagnosis:** Generates commands specific to EXOS, VOSS, Cisco IOS, etc.
- **Knowledge Base Integration:** Retrieves similar historical incidents via ChromaDB
- **Explainable AI:** Provides root cause analysis with reasoning
- **Safety Validation:** Command validation prevents dangerous operations

---

## Service Configuration

### Ports
- **None** (internal service, Kafka consumer only)

### Resources
- **Memory:** 1GB-2GB (LLM context + KB cache)
- **CPU:** 2 cores (LLM inference can be CPU-intensive)
- **Storage:** Minimal (logs only)

### Environment Variables
```
KAFKA_BOOTSTRAP_SERVERS: kafka:9092
KAFKA_GROUP_ID: llm-diagnosis-group
POSTGRES_HOST: postgres
POSTGRES_PORT: 5432
POSTGRES_DB: smart_noc
POSTGRES_USER: noc_admin
POSTGRES_PASSWORD: noc_password
GROQ_API_KEY: gsk_***  # Groq Cloud API key
GROQ_MODEL: mixtral-8x7b-32768
CHROMA_HOST: chromadb
CHROMA_PORT: 8000
CHROMA_COLLECTION: kb_articles
LOG_LEVEL: INFO
SIMULATION_MODE: true  # Safety: no actual device commands
```

---

## Architecture Components

### 1. **Kafka Consumer**

**Input Topic:** `incidents`  
**Consumer Group:** `llm-diagnosis-group`  
**Processing Mode:** Sequential (one incident at a time for quality)

**Input Message Format:**
```json
{
  "incident_number": 20024,
  "incident_type": "CONNECTIVITY_ISSUE",
  "device_id": "10.139.38.188",
  "severity": "HIGH",
  "status": "PENDING_DIAGNOSIS",
  "anomaly_count": 2,
  "correlated_anomalies": [
    {
      "anomaly_id": "anom-20240613-001",
      "anomaly_type": "INTERFACE_FLAPPING",
      "interface": "1:55",
      "event_count": 4
    }
  ],
  "device_vendor": "Extreme Networks",
  "device_family": "EXOS",
  "device_cli_syntax": "EXOS",
  "created_at": "2026-06-13T22:51:35Z"
}
```

---

### 2. **Context Builder**

**Purpose:** Gather all relevant context for LLM analysis

#### **Context Sources**

**A. Incident Data (from Kafka)**
- Incident number, type, severity
- Device ID, vendor, family, CLI syntax
- Correlated anomalies with details

**B. Anomaly Details (from PostgreSQL)**
```sql
SELECT ia.anomaly_id, ia.anomaly_type, ia.anomaly_data
FROM incident_anomalies ia
WHERE ia.incident_number = $1
ORDER BY ia.created_at;
```

**C. Device Enrichment (from anomaly_data)**
- Device vendor: "Extreme Networks"
- Device platform: "EXOS"
- Device model: "X690-48x (2-slot stack)"
- Device OS version: "32.6.1.2"
- CLI syntax: "EXOS"
- Device role: "core"

**D. Knowledge Base Articles (from ChromaDB)**
- Vector similarity search for relevant historical incidents
- Top 5 similar KB articles retrieved

**Extraction Logic:**
```python
def extract_device_info(incident, anomalies):
    """Extract from 3 possible locations"""
    # Location 1: Top-level anomaly_data
    if 'device_vendor' in incident.get('anomaly_data', {}):
        return incident['anomaly_data']
    
    # Location 2: anomaly_data['source_log']
    if 'source_log' in incident.get('anomaly_data', {}):
        return incident['anomaly_data']['source_log']
    
    # Location 3: Direct anomaly fields
    for anomaly in anomalies:
        if 'device_vendor' in anomaly:
            return anomaly
    
    return {}
```

**Built Context:**
```python
context = {
    "incident_number": 20024,
    "incident_type": "CONNECTIVITY_ISSUE",
    "device_id": "10.139.38.188",
    "device_vendor": "extreme",  # Normalized
    "device_platform": "exos",
    "device_cli_syntax": "EXOS",
    "device_model": "X690-48x (2-slot stack)",
    "device_os": "32.6.1.2",
    "anomalies": [
        {"type": "INTERFACE_FLAPPING", "interface": "1:55", "count": 4},
        {"type": "INTERFACE_FLAPPING", "interface": "2:22", "count": 3}
    ],
    "kb_articles": [...]  # Retrieved from ChromaDB
}
```

---

### 3. **ChromaDB Vector Search**

**Purpose:** Retrieve similar historical incidents using semantic search

#### **Collection Structure**

**Collection Name:** `kb_articles`  
**Embedding Model:** `all-MiniLM-L6-v2` (sentence-transformers)  
**Vector Dimensions:** 384

**Document Format:**
```json
{
  "id": "EXT-EXOS-001",
  "title": "EXOS Interface Flapping Due to Cable Issues",
  "vendor": "extreme",
  "platform": "exos",
  "event_type": "interface_down",
  "symptoms": [
    "Port repeatedly transitions between UP and DOWN states",
    "Syslog shows frequent link state changes"
  ],
  "root_causes": [
    "Faulty cable or connector",
    "Incompatible SFP module",
    "Port configuration mismatch"
  ],
  "diagnosis_commands": [
    "show port {interface} information detail",
    "show port {interface} statistics",
    "show edp ports {interface} detail"
  ],
  "fix_commands": [
    "disable port {interface}",
    "enable port {interface}",
    "configure port {interface} auto on"
  ],
  "validation": [
    "show port {interface} information detail | include \"Port Status\"",
    "Verify status shows \"Active\""
  ]
}
```

#### **Query Process**

**Step 1: Build Query**
```python
query_text = f"""
Incident Type: {incident_type}
Device: {device_vendor} {device_platform}
Symptoms: {', '.join(anomaly_types)}
Interface: {interface}
"""
```

**Example Query:**
```
Incident Type: CONNECTIVITY_ISSUE
Device: extreme exos
Symptoms: INTERFACE_FLAPPING, INTERFACE_FLAPPING
Interface: 1:55
```

**Step 2: Vector Search**
```python
results = chroma_collection.query(
    query_texts=[query_text],
    n_results=5,
    where={"vendor": "extreme", "platform": "exos"}
)
```

**Step 3: Ranked Results**
```json
[
  {
    "id": "EXT-EXOS-001",
    "distance": 0.23,  # Lower = more similar
    "title": "EXOS Interface Flapping Due to Cable Issues"
  },
  {
    "id": "EXT-EXOS-012",
    "distance": 0.35,
    "title": "EXOS Port Auto-Negotiation Failure"
  }
]
```

---

### 4. **LLM Reasoning (Groq API)**

**Model:** `mixtral-8x7b-32768` (Mixtral 8x7B with 32K context window)  
**Provider:** Groq Cloud (ultra-fast inference)

#### **Prompt Engineering**

**System Prompt:**
```
You are a senior network operations engineer specializing in AI-driven network troubleshooting.

CRITICAL: Vendor-Specific CLI Commands

You MUST use vendor-specific commands based on the CLI Syntax provided:

EXOS (Extreme Networks):
- show port <X:Y> information detail
- enable port <X:Y>
- disable port <X:Y>
- show edp ports <X:Y> detail
- show vlan

Cisco IOS:
- show interface GigabitEthernet1/0/1
- no shutdown
- show cdp neighbors detail

Juniper JunOS:
- show interfaces ge-0/0/0 detail
- delete interfaces ge-0/0/0 disable

IMPORTANT: Use vendor-specific commands in your remediation plan based on the CLI Syntax in the incident data.
```

**User Prompt Template:**
```
INCIDENT: #{incident_number} - {incident_type}

DEVICE INFORMATION:
- Vendor: {device_vendor}
- Platform: {device_platform}
- CLI Syntax: {device_cli_syntax}
- Model: {device_model}
- OS Version: {device_os}

SYMPTOMS:
{anomaly_details}

SIMILAR HISTORICAL INCIDENTS:
{kb_articles}

Please provide:
1. Root Cause Analysis
2. Confidence Score (0-1)
3. Recommended Actions (step-by-step)
4. Vendor-Specific Commands
5. Validation Steps

IMPORTANT: Use vendor-specific CLI commands based on the CLI Syntax above (e.g., "show port X:Y information detail" for EXOS, not generic commands).
```

**Example User Message:**
```
INCIDENT: #20024 - CONNECTIVITY_ISSUE

DEVICE INFORMATION:
- Vendor: Extreme Networks
- Platform: EXOS
- CLI Syntax: EXOS
- Model: X690-48x (2-slot stack)
- OS Version: 32.6.1.2

SYMPTOMS:
1. Interface 1:55 flapping (4 state changes in 90 seconds)
2. Interface 2:22 flapping (3 state changes in 120 seconds)

SIMILAR HISTORICAL INCIDENTS:
- EXT-EXOS-001: Interface flapping due to cable issues (90% confidence)
- EXT-EXOS-012: Port auto-negotiation failure (75% confidence)

Please provide root cause analysis and remediation plan...
```

---

#### **LLM Response Parsing**

**Expected Response Format:**
```json
{
  "root_cause": "Multiple interfaces showing flapping behavior indicates potential upstream issue (cable, power, or environmental factor affecting multiple ports).",
  "confidence_score": 0.85,
  "recommended_actions": [
    "Check physical connections for both interfaces",
    "Verify SFP modules are properly seated",
    "Review port configuration for auto-negotiation settings",
    "Check for power supply issues affecting multiple ports"
  ],
  "commands": [
    "show port 1:55 information detail",
    "show port 2:22 information detail",
    "show edp ports 1:55 detail",
    "show edp ports 2:22 detail",
    "show vlan"
  ],
  "validation_steps": [
    "Verify port status shows 'Active' for both interfaces",
    "Check EDP neighbors are detected",
    "Confirm no further link state changes in 10 minutes"
  ]
}
```

---

### 5. **Command Validation**

**Purpose:** Prevent dangerous commands from being executed

**Validation Rules:**

**A. Safe Command Prefixes (Allow List)**
```python
SAFE_PREFIXES = [
    'show ', 'display ', 'get ', 'list ', 'view ',
    'ping ', 'traceroute ', 'dig '
]
```

**B. Dangerous Commands (Block List)**
```python
DANGEROUS_COMMANDS = [
    'reload', 'reboot', 'write erase', 'format',
    'delete', 'clear config', 'factory-reset',
    'shutdown', 'erase', 'rm '
]
```

**C. Special Handling: "format" in Read-Only Context**
```python
def validate_command(command):
    """Allow 'format' in show commands, block standalone format"""
    if command.startswith(tuple(SAFE_PREFIXES)):
        return True  # Allow "show port X:Y information detail"
    
    if any(danger in command.lower() for danger in DANGEROUS_COMMANDS):
        return False  # Block "format device"
    
    return True
```

**Example Validation:**
- ✅ `show port 1:55 information detail` → ALLOWED (read-only)
- ✅ `enable port 1:55` → ALLOWED (non-destructive config)
- ❌ `reload` → BLOCKED (device reboot)
- ❌ `write erase` → BLOCKED (destructive)

---

### 6. **PostgreSQL Integration**

#### **Table 1: incidents (UPDATE)**

**Update Query:**
```sql
UPDATE incidents
SET 
    root_cause = %s,
    remediation_plan = %s,
    confidence_score = %s,
    status = 'DIAGNOSED',
    updated_at = NOW()
WHERE incident_number = %s;
```

**Example:**
```sql
UPDATE incidents
SET 
    root_cause = 'Multiple interfaces showing flapping behavior...',
    remediation_plan = '{"commands": ["show port 1:55...",...]}',
    confidence_score = 0.85,
    status = 'DIAGNOSED'
WHERE incident_number = 20024;
```

---

#### **Table 2: incident_diagnosis_history**

**Purpose:** Audit trail of all LLM diagnoses

**Schema:**
```sql
CREATE TABLE incident_diagnosis_history (
    id SERIAL PRIMARY KEY,
    incident_number INTEGER REFERENCES incidents(incident_number),
    llm_model VARCHAR(100),
    prompt_text TEXT,
    llm_response TEXT,
    root_cause TEXT,
    remediation_plan JSONB,
    confidence_score FLOAT,
    processing_time_ms INTEGER,
    kb_articles_used JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Insert Example:**
```sql
INSERT INTO incident_diagnosis_history (
    incident_number, llm_model, root_cause, remediation_plan, 
    confidence_score, processing_time_ms, kb_articles_used
)
VALUES (
    20024, 
    'mixtral-8x7b-32768',
    'Multiple interfaces showing flapping behavior...',
    '{"commands": ["show port 1:55...",...]}',
    0.85,
    1247,
    '["EXT-EXOS-001", "EXT-EXOS-012"]'
);
```

---

### 7. **Kafka Producer**

**Output Topic:** `incidents-diagnosed`

**Message Format:**
```json
{
  "incident_number": 20024,
  "device_id": "10.139.38.188",
  "device_vendor": "Extreme Networks",
  "device_cli_syntax": "EXOS",
  "root_cause": "Multiple interfaces showing flapping behavior indicates potential upstream issue affecting multiple ports.",
  "confidence_score": 0.85,
  "remediation_plan": {
    "recommended_actions": [
      "Check physical connections for both interfaces",
      "Verify SFP modules are properly seated",
      "Review port configuration for auto-negotiation settings"
    ],
    "commands": [
      "show port 1:55 information detail",
      "show port 2:22 information detail",
      "show edp ports 1:55 detail",
      "show edp ports 2:22 detail",
      "show vlan"
    ],
    "validation_steps": [
      "Verify port status shows 'Active' for both interfaces",
      "Check EDP neighbors are detected"
    ]
  },
  "kb_articles_used": ["EXT-EXOS-001", "EXT-EXOS-012"],
  "diagnosed_at": "2026-06-13T22:52:15Z",
  "processing_time_ms": 1247
}
```

---

## Dependencies

### Upstream
- **Kafka (incidents topic):** Incidents from Correlation Engine
- **PostgreSQL (incidents table):** Read incident details
- **PostgreSQL (incident_anomalies table):** Read related anomalies

### Downstream
- **Groq API:** LLM inference (external API)
- **ChromaDB:** Vector knowledge base (HTTP API)
- **Kafka (incidents-diagnosed topic):** Publishes diagnosed incidents
- **PostgreSQL (incidents table):** Updates incident with diagnosis
- **PostgreSQL (incident_diagnosis_history table):** Audit trail
- **Remediation Agent:** Consumes diagnosed incidents

---

## Data Flow

```
Kafka (incidents) → Consumer
                      ↓
                Context Builder
                      ↓
          ┌─────────┴─────────┐
          ↓                   ↓
    PostgreSQL (anomalies)  ChromaDB (KB search)
          ↓                   ↓
          └─────────┬─────────┘
                    ↓
              LLM Prompt (Groq)
                    ↓
             LLM Response
                    ↓
          Command Validation
                    ↓
         ┌──────────┴──────────┐
         ↓                     ↓
  PostgreSQL (update)   Kafka (incidents-diagnosed)
                               ↓
                        Remediation Agent
```

---

## Performance Characteristics

### Throughput
- **Tested:** 10-20 incidents/minute
- **Capacity:** 50 incidents/minute (with caching)
- **Bottleneck:** LLM API latency (500-2000ms per call)

### Latency
- **Context Building:** 100-200ms (DB queries + vector search)
- **LLM Inference:** 800-1500ms (Groq is fast!)
- **Total:** 1-2 seconds per incident

### Resource Usage
- **Memory:** 800MB (LLM client + context cache)
- **CPU:** 20-40% (mostly I/O wait)
- **Network:** API calls to Groq + ChromaDB

---

## Monitoring & Health

### Health Check
```yaml
healthcheck:
  test: ["CMD-SHELL", "python -c 'import requests; requests.get(\"http://chromadb:8000/api/v1/heartbeat\", timeout=3)' || exit 1"]
  interval: 60s
  timeout: 10s
  retries: 3
```

### Logs
```bash
docker logs smart-noc-llm-diagnosis --tail 100
```

**Normal Output:**
```
[INFO] Kafka consumer started: incidents
[INFO] Processing incident 20024 (CONNECTIVITY_ISSUE)
[INFO] Using device inventory data (top-level) - Vendor: extreme, Platform: exos, CLI: EXOS
[INFO] Retrieved 5 KB articles from ChromaDB
[INFO] Sending prompt to Groq API (model: mixtral-8x7b-32768)
[INFO] LLM response received (1247ms)
[INFO] Validated 5 commands (all safe)
[INFO] Updated incident 20024 in PostgreSQL
[INFO] Published diagnosed incident to Kafka: 20024
```

**Error Indicators:**
```
[ERROR] Groq API error: Rate limit exceeded
[ERROR] ChromaDB connection failed: Connection refused
[ERROR] Dangerous command detected: 'reload' not allowed
[WARNING] Low confidence diagnosis: 0.45 < 0.60 threshold
```

---

## Troubleshooting

### Issue: LLM Generating Generic Commands

**Symptoms:**
- Commands are not vendor-specific
- EXOS device getting Cisco commands

**Diagnosis:**
```bash
# Check device enrichment in context
docker logs smart-noc-llm-diagnosis | grep "device inventory data"
```

**Resolution:**
1. Verify device enrichment fields (device_vendor, device_cli_syntax) present in incident
2. Check system prompt includes vendor-specific command examples
3. Review LLM response for correct CLI syntax

---

### Issue: Groq API Rate Limit

**Symptoms:**
- Error: "Rate limit exceeded"
- Processing stops

**Diagnosis:**
```bash
# Check Groq API quota
curl -H "Authorization: Bearer $GROQ_API_KEY" https://api.groq.com/openai/v1/models
```

**Resolution:**
1. Implement exponential backoff retry
2. Add request queuing/throttling
3. Upgrade Groq plan for higher limits

---

### Issue: Low Confidence Diagnoses

**Symptoms:**
- Confidence scores <0.60
- Vague or generic remediation plans

**Diagnosis:**
- Review KB article quality
- Check if similar incidents exist in ChromaDB

**Resolution:**
1. Expand knowledge base (100+ articles)
2. Improve KB article quality (more specific symptoms, commands)
3. Fine-tune similarity search thresholds

---

## Configuration Files

### Main Service
**Location:** `/services/llm-diagnosis/diagnosis_service.py`

### Prompts
**Location:** `/services/llm-diagnosis/prompts/`
- `system_prompts.py`: System prompt with vendor CLI examples
- `improved_system_prompt.py`: Enhanced vendor-specific guidance

### Context Builder
**Location:** `/services/llm-diagnosis/context_builder.py`

---

## Related Documentation

- [Correlation Engine](04-correlation-engine.md)
- [Remediation Agent](06-remediation-agent.md)
- [ChromaDB](10-chromadb.md)
- [PostgreSQL Schema](08-postgres.md)
- [Complete Architecture](../02-architecture/COMPLETE_ARCHITECTURE.md)
