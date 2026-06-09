# Smart NOC - System Architecture

**Version:** 3.0 (Production)  
**Date:** May 22, 2026  
**Status:** ✅ Fully Operational

---

## Overview

**Smart NOC** is an AI-powered autonomous Network Operations Center that detects network anomalies, correlates them into incidents, performs AI-driven root cause diagnosis using LLMs, and generates automated remediation plans.

**Processing Pipeline:**
```
Raw Logs → Anomaly Detection → Correlation → LLM Diagnosis → Remediation
```

**Key Metrics:**
- **13 Microservices** running in Docker containers
- **4 Kafka Topics** for event-driven communication
- **6 Anomaly Types** detected (rule-based + ML)
- **Real-time Processing:** Sub-second anomaly detection
- **AI Diagnosis:** 75-95% confidence using Groq LLM (llama-3.3-70b-versatile)

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          SMART NOC ARCHITECTURE                         │
│                     ═══ CRITICAL PATH ═══  ─── PARALLEL ───             │
└─────────────────────────────────────────────────────────────────────────┘

  Network Device Logs (JSON)
         │
         ▼
  ┌═════════════┐
  ║   KAFKA     ║ Port 9092 (external), 19092 (internal)
  ║ Topic:      ║ Partitions: 3, Retention: 7 days
  ║ network-    ║ Consumer Groups: anomaly-detector, logstash-consumer
  ║ logs (RAW)  ║
  └══════╦══════┘
         ║
         ╠════════════════════════════════════════════╗
         ║                                            ║
         ║ CRITICAL PATH (Real-time Detection)       ║ PARALLEL PATH (Storage)
         ║                                            ║
         ▼                                            ▼
  ┌═════════════┐                            ┌─────────────┐
  ║   ANOMALY   ║ Consumes RAW logs          │  LOGSTASH   │ Consumes same logs
  ║  DETECTOR   ║ (NO enrichment)            │             │ (Independent)
  ║             ║                             │ Port: 5000  │
  ║ Detection:  ║                             │             │
  ║ • 5 Rules   ║                             │ Actions:    │
  ║ • 1 ML      ║                             │ 1. Parse    │
  ║   (Isolation║                             │ 2. NO enrich│
  ║    Forest)  ║                             │ 3. Send →   │
  ║             ║                             └──────┬──────┘
  ║ Uses Redis  ║                                    │
  ║ for state   ║                                    ▼ HTTP PUT
  └══════╦══════┘                            ┌─────────────┐
         ║                                   │ELASTICSEARCH│
         ║ Publishes                         │ Port: 9200  │
         ▼                                   │             │
  ┌═════════════┐                            │ Purpose:    │
  ║   KAFKA     ║                            │ • Storage   │
  ║ Topic:      ║                            │ • Search    │
  ║ anomalies   ║                            │ • Dashboards│
  ║             ║                            │             │
  └══════╦══════┘                            │ NOT in      │
         ║                                   │ critical    │
         ║ Consumes                          │ detection   │
         ▼                                   │ path        │
  ┌═════════════┐                            └─────────────┘
  ║CORRELATION  ║
  ║  ENGINE     ║ Groups related anomalies
  ║             ║ Time window: 5 min
  ║ Rules:      ║ Min threshold: 2 anomalies
  ║ • Time      ║
  ║ • Device    ║
  ║ • Type      ║
  └══════╦══════┘
         ║
         ╠══════════════════════╗
         ║                      ║
         ▼                      ▼
  ┌─────────────┐        ┌═════════════┐
  │ POSTGRESQL  │        ║   KAFKA     ║
  │ Port: 5432  │        ║ Topic:      ║
  │             │        ║ incidents   ║
  │ Tables:     │        └══════╦══════┘
  │ • incidents │               ║
  │ • anomalies │               ║ Consumes
  │ • devices   │               ▼
  │ • diagnosis │        ┌═════════════┐
  │ • remedia-  │        ║LLM DIAGNOSIS║
  │   tions     │        ║             ║
  └─────┬───────┘        ║ Groq API    ║
        │                ║ llama-3.3-  ║──────┐
        │                ║ 70b         ║      │
        │                ║             ║      │ Queries KB
        │                ║ Steps:      ║      │
        │                ║ 1. Get      ║      │
        │                ║    incident ║      ▼
        │                ║ 2. Vector   ║  ┌─────────────┐
        │                ║    search   ║  │  CHROMADB   │
        │                ║ 3. Call LLM ║  │ Port: 8000  │
        │                ║ 4. Parse    ║  │             │
        │                ║ 5. Save     ║  │ Collections:│
        │                ║ 6. Publish  ║  │ • knowledge │
        │                └══════╦══════┘  │   _base: 23 │
        │                       ║         │ • incidents │
        │                       ║         │ • vendors   │
        │                       ▼         └─────────────┘
        │                ┌═════════════┐        ▲
        │                ║   KAFKA     ║        │
        │                ║ Topic:      ║        │
        │                ║ incidents-  ║  ┌─────┴───────┐
        │                ║ diagnosed   ║  │   VECTOR    │
        │                └══════╦══════┘  │  SERVICE    │
        │                       ║         │             │
        │                       ║         │ Manages     │
        │                       ▼         │ embeddings  │
        │                ┌═════════════┐  └─────────────┘
        │                ║REMEDIATION  ║
        │                ║   AGENT     ║
        │                ║             ║
        │                ║ Logic:      ║
        │                ║ • Auto-fix  ║
        │                ║ • Escalate  ║
        │                ║ • Rollback  ║
        │                └══════╦══════┘
        │                       ║
        │                       ║ Saves execution results
        └───────────────────────╨─────────────────────────┐
                                                           │
  ┌─────────────┐                                         │
  │    REDIS    │◄─── Used by Anomaly Detector           │
  │  Port: 6379 │     for state management               │
  │             │                                         │
  │ Keys:       │                                         │
  │ • flap_     │                                         │
  │   count     │                                         │
  │ • device_   │                                         │
  │   state     │                                         │
  └─────────────┘                                         │
                                                          │
  Monitoring & UI:                                        │
  ┌─────────────┐                                         │
  │  GRAFANA    │ Visualizes metrics                     │
  │ Port: 3000  │                                         │
  └─────────────┘                                         │
  ┌─────────────┐                                         │
  │  KAFKA UI   │ Manages topics                         │
  │ Port: 8080  │                                         │
  └─────────────┘                                         │
                                                          │
  Database: smart_noc (PostgreSQL) ◄────────────────────┘
  Credentials: noc_admin / noc_password

═══ Legend ═══
║ ═══ ║  Critical path services (real-time detection & diagnosis)
│ ─── │  Supporting/parallel services (storage, monitoring)
```

**Key Points:**
1. **Anomaly Detector** reads DIRECTLY from `network-logs` (raw, NOT enriched)
2. **Logstash** is PARALLEL - only stores logs in Elasticsearch (not critical)
3. **No enrichment** happens before anomaly detection (current working state)
4. **Elasticsearch** is for historical storage/search only

---

## Data Flow Explained

### Q: How does Anomaly Detector get logs?
**A:** The Anomaly Detector subscribes to the `network-logs` Kafka topic as a consumer.

```
Network Device → Kafka Topic (network-logs) → Anomaly Detector consumes
                                           → Logstash also consumes (parallel)
```

**Config Location:** `services/anomaly-detector/config.yaml`
```yaml
kafka:
  input_topic: network-logs  # Reads RAW logs directly
  consumer_group: anomaly-detector-group
```

### Q: Who is enriching the logs?
**A:** **Nobody is enriching logs** before anomaly detection in the current architecture.

- **Original Plan:** Logstash would enrich logs with business context (device_role, criticality)
- **Current Reality:** Anomaly detector bypasses enrichment due to Elasticsearch disk issues
- **Why it works:** Rule-based detection doesn't need enrichment to detect INTERFACE_DOWN, BGP_FLAP, etc.

### Q: What is the role of Elasticsearch?
**A:** Elasticsearch serves as a **passive storage layer** for historical log queries and dashboards.

**Responsibilities:**
- Store logs for historical search
- Power Grafana dashboards
- Enable troubleshooting via log search
- **NOT required** for real-time anomaly detection

**Think of it as:** A backup/archive system that runs in parallel.

### Q: How does Elasticsearch receive logs?
**A:** Logstash sends logs to Elasticsearch via HTTP PUT requests.

```
Flow:
1. Logstash consumes from Kafka (network-logs topic)
2. Logstash parses JSON logs
3. Logstash sends via HTTP PUT to Elasticsearch
4. Elasticsearch indexes logs in network-logs-* index
```

**Config Location:** `config/logstash/logstash.conf`
```ruby
input {
  kafka {
    bootstrap_servers => "kafka:19092"
    topics => ["network-logs"]
    consumer_group => "logstash-consumer"
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "network-logs-%{+YYYY.MM.dd}"
  }
}
```

### The Two Parallel Paths

```
                    ┌─── KAFKA (network-logs) ───┐
                    │                             │
        Path 1: CRITICAL (Real-time)    Path 2: STORAGE (Historical)
                    │                             │
                    ▼                             ▼
           Anomaly Detector                  Logstash
                    ↓                             ↓
           Kafka (anomalies)              Elasticsearch
                    ↓                        (Archive)
           Correlation Engine
                    ↓
              LLM Diagnosis
                    ↓
           Remediation Agent
```

**Key Insight:** If Elasticsearch goes down, anomaly detection continues working! It's decoupled.

---

## Services Inventory

### Core Processing Services (Critical Path)

| Service | Container | Port(s) | Purpose | Dependencies |
|---------|-----------|---------|---------|--------------|
| **Kafka** | smart-noc-kafka | 9092, 19092, 9093 | Event broker (KRaft mode) | None |
| **Anomaly Detector** | smart-noc-anomaly-detector | - | Detects 6 anomaly types using ML + rules | Kafka, Redis |
| **Correlation Engine** | smart-noc-correlation-engine | - | Groups anomalies into incidents | Kafka, PostgreSQL |
| **LLM Diagnosis** | smart-noc-llm-diagnosis | - | AI root cause analysis via Groq API | Kafka, PostgreSQL, ChromaDB |
| **Remediation Agent** | smart-noc-remediation-agent | - | Executes/escalates remediation plans | Kafka, PostgreSQL |

### Supporting Services

| Service | Container | Port(s) | Purpose |
|---------|-----------|---------|---------|
| **PostgreSQL** | smart-noc-postgres | 5432 | Persistent storage (incidents, anomalies, devices) |
| **Redis** | smart-noc-redis | 6379 | State management (sliding windows, counters) |
| **ChromaDB** | smart-noc-chromadb | 8000 | Vector database for semantic search |
| **Vector Service** | smart-noc-vector-service | - | Manages embeddings for ChromaDB |
| **Elasticsearch** | smart-noc-elasticsearch | 9200, 9300 | Log storage and search |
| **Logstash** | smart-noc-logstash | 5000, 9600 | Log parsing and enrichment |
| **Grafana** | smart-noc-grafana | 3000 | Monitoring dashboards |
| **Kafka UI** | smart-noc-kafka-ui | 8080 | Kafka management interface |

### Network Configuration
- **Docker Network:** `smart-noc-network` (bridge)
- **Internal Communication:** Services use container names
- **External Access:** Ports mapped to host (9092, 5432, 3000, 8080, 8000)

---

## Kafka Topics

| Topic | Partitions | Purpose | Producer | Consumer(s) |
|-------|------------|---------|----------|-------------|
| **network-logs** | 3 | Raw device logs | Log generator | Anomaly Detector |
| **anomalies** | 3 | Detected anomalies | Anomaly Detector | Correlation Engine |
| **incidents** | 3 | Correlated incidents | Correlation Engine | LLM Diagnosis |
| **incidents-diagnosed** | 3 | Diagnosed incidents with remediation | LLM Diagnosis | Remediation Agent |

**Configuration:**
- Retention: 7 days
- Replication Factor: 1 (single broker)
- Bootstrap Servers: `kafka:19092` (internal), `localhost:9092` (external)

---

## End-to-End Data Flow

### 1. Log Ingestion
```
Network Device → JSON Log → Kafka (network-logs topic)
```
**Log Schema:**
```json
{
  "timestamp": "2026-05-22T10:30:00Z",
  "device": "core-router-01",
  "interface": "GigabitEthernet0/1",
  "event_type": "INTERFACE_DOWN",
  "message": "Interface GigabitEthernet0/1 changed state to down"
}
```

### 2. Anomaly Detection
```
Kafka (network-logs) → Anomaly Detector → Kafka (anomalies)
```
**Detection Methods:**
- **Rule-based:** INTERFACE_DOWN, BGP_FLAP, HIGH_CPU, MEMORY_LEAK, AUTH_FAILURE
- **ML-based:** UNKNOWN_PATTERN (Isolation Forest algorithm)

**Anomaly Schema:**
```json
{
  "anomaly_id": "anom_20260522103001_abc123",
  "timestamp": "2026-05-22T10:30:01Z",
  "device": "core-router-01",
  "anomaly_type": "INTERFACE_FLAPPING",
  "severity": "high",
  "confidence": 0.92,
  "context": {
    "interface": "GigabitEthernet0/1",
    "flap_count": 5,
    "time_window": "300s"
  }
}
```

**State Management (Redis):**
- Sliding window counters for flapping detection
- Device state tracking
- LRU eviction policy

### 3. Correlation
```
Kafka (anomalies) → Correlation Engine → PostgreSQL + Kafka (incidents)
```
**Correlation Rules:**
- **Time-based:** Group anomalies within 5-minute window
- **Device-based:** Same device/interface
- **Type-based:** Similar anomaly types
- **Threshold:** Minimum 2 anomalies to create incident

**Incident Schema (PostgreSQL):**
```sql
incidents (
  id SERIAL PRIMARY KEY,
  incident_number TEXT UNIQUE,
  title TEXT,
  severity TEXT,
  status TEXT, -- open, investigating, resolved
  correlated_anomalies JSONB,
  created_at TIMESTAMP,
  updated_at TIMESTAMP
)
```

### 4. LLM Diagnosis
```
Kafka (incidents) → LLM Diagnosis → Vector Search (ChromaDB) → Groq API → Kafka (incidents-diagnosed)
```
**Process:**
1. Retrieve incident details from PostgreSQL
2. Semantic search in ChromaDB knowledge base (23 articles)
3. Construct prompt with incident context + KB articles
4. Call Groq API (llama-3.3-70b-versatile)
5. Parse LLM response → Extract root cause, remediation steps
6. Save to incident_diagnosis_history table
7. Publish to incidents-diagnosed topic

**Diagnosis Schema:**
```json
{
  "incident_id": 1,
  "incident_number": "INC-20260522-001",
  "root_cause": "Physical layer issue (faulty cable/connector)",
  "confidence": 0.85,
  "remediation_plan": [
    "Step 1: Inspect physical cable connection",
    "Step 2: Replace SFP transceiver if needed",
    "Step 3: Monitor interface for 30 minutes"
  ],
  "severity_assessment": "high",
  "estimated_time": "30 minutes"
}
```

**LLM API Configuration:**
- Provider: Groq Cloud
- Model: llama-3.3-70b-versatile
- Temperature: 0.3
- Max Tokens: 2048

### 5. Remediation
```
Kafka (incidents-diagnosed) → Remediation Agent → Execute/Escalate → PostgreSQL (remediation_executions)
```
**Decision Logic:**
- Auto-fix: Software configuration issues (safe commands)
- Escalate: Physical issues, high-risk changes, security breaches
- Rollback: If auto-fix fails

**Remediation Execution Schema:**
```sql
remediation_executions (
  id SERIAL PRIMARY KEY,
  incident_id INTEGER REFERENCES incidents(id),
  incident_number TEXT,
  success BOOLEAN,
  actions_taken INTEGER,
  resolution_time_seconds INTEGER,
  final_phase TEXT, -- completed, escalated, failed, rollback
  lessons_learned TEXT,
  executed_at TIMESTAMP DEFAULT NOW()
)
```

---

## Database Architecture

### PostgreSQL (smart_noc database)

**Credentials:**
- Host: `postgres:5432` (internal), `localhost:5432` (external)
- Database: `smart_noc`
- User: `noc_admin`
- Password: `noc_password`

**Schema:**
```sql
-- Core Tables
devices (id, device_name, device_type, location, criticality)
incidents (id, incident_number, title, severity, status, correlated_anomalies, root_cause)
anomalies (id, anomaly_id, device_id, anomaly_type, severity, detected_at)

-- Diagnosis & Remediation
incident_diagnosis_history (id, incident_id, diagnosis_text, confidence, llm_provider, tokens_used)
remediation_executions (id, incident_id, success, actions_taken, final_phase, executed_at)

-- Views
remediation_stats (aggregates daily remediation metrics)
```

**Indexes:**
- incident_number (unique)
- device_name (B-tree)
- detected_at (B-tree for time-based queries)
- remediation FK indexes

### ChromaDB Collections

**Host:** `chromadb:8000` (internal), `localhost:8000` (external)

| Collection | Documents | Purpose |
|------------|-----------|---------|
| **knowledge_base** | 23 | Network troubleshooting KB articles |
| **incidents** | 0 | Historical incident embeddings (future use) |
| **vendor_documentation** | 0 | Vendor docs (future use) |
| **remediation_commands** | 0 | Safe command database (future use) |

**Vector Search:**
- Embedding Model: sentence-transformers
- Distance Metric: Cosine similarity
- Top-K Results: 2-3 most relevant articles per query

### Redis Key-Value Store

**Host:** `redis:6379`

**Key Patterns:**
- `flap_count:{device}:{interface}` → Counter (sliding window)
- `device_state:{device}` → Hash (interface states)
- `anomaly_window:{device}` → Sorted set (time-based)

**Eviction Policy:** LRU (Least Recently Used)

---

## Anomaly Detection Details

### Detection Types

| Anomaly Type | Method | Threshold | Confidence |
|--------------|--------|-----------|------------|
| INTERFACE_DOWN | Rule | Keyword match | 0.95 |
| INTERFACE_FLAPPING | Rule | 3+ state changes in 5min | 0.90 |
| BGP_FLAP | Rule | BGP neighbor up/down | 0.92 |
| HIGH_CPU | Rule | CPU > 80% | 0.88 |
| MEMORY_LEAK | Rule | Memory increase trend | 0.85 |
| UNKNOWN_PATTERN | ML (Isolation Forest) | Anomaly score < -0.5 | 0.70-0.80 |

### Machine Learning Model

**Algorithm:** Isolation Forest (sklearn)
- **Features:** log_length, numeric_count, uppercase_ratio, special_char_ratio, etc.
- **Training:** Adaptive (retrains periodically on normal traffic)
- **Contamination:** 0.1 (10% expected anomalies)

---

## Configuration Files

### Critical Configurations

**Anomaly Detector:** `services/anomaly-detector/config.yaml`
```yaml
kafka:
  bootstrap_servers: kafka:19092
  input_topic: network-logs  # Direct consumption (no enrichment)
  output_topic: anomalies
  consumer_group: anomaly-detector-group

redis:
  host: redis
  port: 6379

detection:
  flap_threshold: 3
  time_window: 300
```

**Correlation Engine:** `services/correlation-engine/config.yaml`
```yaml
kafka:
  bootstrap_servers: kafka:19092
  input_topic: anomalies
  output_topic: incidents

postgres:
  host: postgres
  port: 5432
  database: smart_noc
  user: noc_admin

correlation:
  time_window: 300  # 5 minutes
  same_type_threshold: 2
```

**LLM Diagnosis:** `services/llm-diagnosis/config.yaml`
```yaml
kafka:
  input_topic: incidents
  output_topic: incidents-diagnosed

llm:
  provider: groq
  model: llama-3.3-70b-versatile
  api_key: ${LLM_API_KEY}
  temperature: 0.3
  max_tokens: 2048

chromadb:
  host: chromadb
  port: 8000
```

**Environment Variables:** `.env`
```bash
# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=smart_noc
POSTGRES_USER=noc_admin
POSTGRES_PASSWORD=noc_password

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:19092

# LLM
LLM_API_KEY=<groq_api_key>
LLM_MODEL=llama-3.3-70b-versatile
```

---

## Deployment & Operations

### Starting the System
```bash
cd /home/user/ng-iam/smart-noc
./setup-noc.sh
```
**What it does:**
1. Validates Docker environment
2. Starts 13 services via docker-compose
3. Creates Kafka topics
4. Initializes PostgreSQL schema
5. Validates all services are healthy
6. Displays access points

### Verification Commands
```bash
# Check all services
docker compose ps

# View service logs
docker compose logs -f anomaly-detector
docker compose logs -f correlation-engine
docker compose logs -f llm-diagnosis

# Check Kafka topics
docker compose exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list

# Query PostgreSQL
docker compose exec postgres psql -U noc_admin -d smart_noc -c "SELECT * FROM incidents ORDER BY created_at DESC LIMIT 5;"

# Check ChromaDB
python3 query_chromadb.py
```

### Access Points
- **Grafana Dashboard:** http://localhost:3000 (admin/admin)
- **Kafka UI:** http://localhost:8080
- **ChromaDB API:** http://localhost:8000
- **PostgreSQL:** `psql -h localhost -p 5432 -U noc_admin -d smart_noc`
- **Elasticsearch:** http://localhost:9200

### Health Checks
All services implement health checks:
- Kafka: Topic list
- PostgreSQL: SELECT 1
- Redis: PING
- ChromaDB: /api/v1/heartbeat
- Services: Kafka consumer group lag

---

## Performance & Scalability

### Current Metrics
- **Throughput:** ~1000 logs/second per anomaly detector instance
- **Latency:** 
  - Anomaly detection: <100ms
  - Correlation: <500ms
  - LLM diagnosis: 2-5 seconds
  - End-to-end: 5-10 seconds
- **Storage:** 
  - PostgreSQL: ~1MB per 1000 incidents
  - Elasticsearch: ~5MB per 10000 logs
  - ChromaDB: ~50KB per document

### Scaling Strategy
- **Horizontal:** Increase Kafka partitions + add consumer instances
- **Vertical:** Increase container CPU/memory limits
- **Database:** Read replicas for PostgreSQL, sharding for high volume

### Resource Requirements
```yaml
# Minimum (Development)
CPU: 4 cores
RAM: 8GB
Disk: 20GB

# Recommended (Production)
CPU: 8+ cores
RAM: 16GB
Disk: 100GB (with log retention)
```

---

## Security Considerations

- **Network Isolation:** All services in private Docker network
- **Credentials:** Stored in .env (not committed to git)
- **Database:** Password-protected PostgreSQL
- **API Keys:** LLM API key in environment variable
- **Least Privilege:** Service accounts with minimal permissions

---

## Monitoring & Observability

### Key Metrics to Monitor
1. **Kafka Lag:** Consumer group lag (alerts if >1000)
2. **Anomaly Rate:** Anomalies/minute (baseline ~5-10)
3. **Incident Rate:** Incidents/hour (baseline ~2-5)
4. **LLM Latency:** P95 response time (alert if >10s)
5. **Database Connections:** PostgreSQL active connections
6. **Disk Space:** Elasticsearch index size

### Grafana Dashboards
- Network Operations Dashboard (port 3000)
- Incident timeline
- Anomaly heatmap by device
- LLM diagnosis confidence distribution
- Remediation success rate

---

## Troubleshooting

### Common Issues

**Problem:** Anomaly detector not processing logs
- Check: `docker compose logs anomaly-detector`
- Verify: Kafka topic exists, Redis accessible
- Fix: Restart service with `docker compose restart anomaly-detector`

**Problem:** LLM diagnosis timing out
- Check: Groq API key validity
- Verify: ChromaDB accessible at port 8000
- Fix: Check .env file, restart llm-diagnosis

**Problem:** Elasticsearch flood stage watermark
- Symptom: Logstash errors, read-only index
- Fix: Free disk space, disable threshold temporarily
```bash
curl -X PUT "localhost:9200/_cluster/settings" -H 'Content-Type: application/json' -d'
{"persistent":{"cluster.routing.allocation.disk.threshold_enabled":false}}'
```

**Problem:** Database connection errors
- Check: PostgreSQL container running
- Verify: Credentials in .env match docker-compose.yml
- Fix: Apply migrations from `infrastructure/postgres/migrations/`

---

## Version History

**v3.0 (May 22, 2026)** - Current Production
- Fixed remediation_executions table schema
- Validated complete end-to-end AI pipeline
- Migrated to Groq API (llama-3.3-70b-versatile)
- Resolved Elasticsearch disk pressure issues
- All 13 services operational

**v2.0 (May 7, 2026)**
- Implemented enriched pipeline with Logstash
- Added context-aware anomaly detection
- Introduced criticality-based thresholds

**v1.0 (April 2026)**
- Initial architecture
- Basic anomaly detection and correlation
- Proof of concept LLM integration

---

## Quick Reference

**Restart All Services:**
```bash
docker compose restart
```

**Generate Test Incident:**
```bash
scripts/generate-logs.sh --scenario flapping
```

**Query Recent Incidents:**
```bash
docker compose exec postgres psql -U noc_admin -d smart_noc -c \
  "SELECT incident_number, severity, status, root_cause FROM incidents ORDER BY created_at DESC LIMIT 5;"
```

**Check Vector DB:**
```bash
python3 query_chromadb.py
```

**Teardown System:**
```bash
./teardown-noc.sh
```

---

**End of Architecture Document**
