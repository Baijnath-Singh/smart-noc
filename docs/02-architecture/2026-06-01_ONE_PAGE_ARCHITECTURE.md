# Smart NOC - One-Page Architecture & Flow

**Version:** 1.0  
**Date:** May 5, 2026  
**Purpose:** End-to-end architecture and service communication overview

---

## System Overview

Smart NOC is an AI-powered Network Operations Center that automatically detects anomalies, correlates incidents, and provides AI-driven root cause analysis from network device logs.

---

## Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          SMART NOC ARCHITECTURE                            │
│                    (Production-Grade Log Processing Pipeline)              │
└────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────┐
    │ Network Devices │  (Simulated)
    │ Log Generator   │  Generates syslog: flapping, high-cpu, BGP, attacks
    └────────┬────────┘
             │ TCP (Port 5000)
             │ Format: RFC 5424 Syslog
             │ Rate: 100-500 logs/min
             ▼
    ┌─────────────────┐
    │   LOGSTASH      │  ◄─── COLLECTOR
    │  (Log Parser)   │  Parses, enriches, normalizes logs
    └────────┬────────┘
             │ 
             │ • Grok parsing (syslog, custom patterns)
             │ • Multi-line handling (stack traces)
             │ • UTC timestamp normalization
             │ • Field enrichment (source, severity)
             │ • Disk-based persistent queue (durability)
             │ • Batching: 125 events, flush every 1s
             │
             │ HTTP POST
             ▼
    ┌─────────────────┐
    │ ELASTICSEARCH   │  ◄─── PRIMARY STORAGE
    │  (Log Store)    │  Fast full-text search, time-series indexing
    └────────┬────────┘
             │
             │ • Index: logs-* (dynamic mapping)
             │ • Retention: 7 days (configurable)
             │ • Query: REST API (port 9200)
             │ • Indexed: @timestamp, device, severity, message
             │
             │ Elasticsearch Query (every 30s)
             ▼
    ┌─────────────────┐
    │ ANOMALY         │  ◄─── DETECTOR
    │ DETECTOR        │  Hybrid rule-based + ML detection
    └────────┬────────┘
             │
             │ Detection Types:
             │ • INTERFACE_FLAPPING (rule: >2 flaps/5min)
             │ • HIGH_CPU (rule: >80% for 1min)
             │ • BGP_INSTABILITY (rule: >2 flaps/5min)
             │ • AUTHENTICATION_FAILURES (rule: >3/min)
             │ • HIGH_MEMORY (rule: >85% for 2min)
             │ • ML_DETECTED_ANOMALY (Isolation Forest)
             │
             │ State: Redis (tracks detection windows)
             │ Publish: Kafka (manual commit after success)
             │
             │ Kafka Topic: "anomalies"
             ▼
    ┌─────────────────┐
    │     KAFKA       │  ◄─── MESSAGE BROKER (Transport Layer)
    │ (Message Bus)   │  Event-driven decoupling
    └────────┬────────┘
             │
             │ Topics:
             │ • anomalies (3 partitions, device-keyed, 7d retention)
             │ • incidents (3 partitions, incident-keyed, 30d retention)
             │ • incidents-diagnosed (enriched with AI diagnosis)
             │
             │ Features:
             │ • At-least-once delivery (manual commit)
             │ • Backpressure handling (blocks on slow consumer)
             │ • Gzip compression
             │ • Graceful shutdown (drains in-flight batches)
             │
             │ Consume from "anomalies"
             ▼
    ┌─────────────────┐
    │ CORRELATION     │  ◄─── INCIDENT BUILDER
    │ ENGINE          │  Groups related anomalies into incidents
    └────────┬────────┘
             │
             │ Correlation Logic:
             │ • Time-based: Anomalies within 5-60s window
             │ • Pattern-based: Same device/type/severity
             │ • Creates incident with:
             │   - Incident number (auto-increment)
             │   - Type (DEVICE_FAILURE, NETWORK_PERFORMANCE, etc.)
             │   - Affected devices list
             │   - Anomaly count
             │
             │ Publish: Kafka "incidents" topic
             ▼
    ┌─────────────────┐
    │     KAFKA       │
    │ (incidents)     │
    └────────┬────────┘
             │
             │ Consume from "incidents"
             ▼
    ┌─────────────────┐
    │ LLM DIAGNOSIS   │  ◄─── AI ANALYZER
    │  (AI Service)   │  Root cause analysis & remediation planning
    └────────┬────────┘
             │
             │ LLM Features:
             │ • Multi-provider: OpenAI GPT-4, Anthropic Claude, Ollama phi3
             │ • Context building:
             │   - Current incident anomalies
             │   - Historical incidents (similar patterns)
             │   - Device history (last 24h)
             │ • Output:
             │   - Root cause (75-95% confidence)
             │   - Reasoning chain
             │   - Remediation plan (step-by-step with CLI commands)
             │   - Estimated duration per step
             │ • Timeout: 180s with exponential backoff retry
             │
             │ Write diagnosis
             ▼
    ┌─────────────────┐
    │  POSTGRESQL     │  ◄─── INCIDENT DATABASE (Secondary Storage)
    │  (smart_noc)    │  Persistent incident and diagnosis storage
    └────────┬────────┘
             │
             │ Tables:
             │ • incidents (id, incident_number, type, status, severity,
             │              root_cause, root_cause_confidence,
             │              remediation_plan JSONB, diagnosis_timestamp)
             │ • anomalies (id, anomaly_type, device, severity, timestamp)
             │ • incident_diagnosis_history (audit trail)
             │
             │ Views:
             │ • incidents_with_diagnosis (enriched data)
             │ • diagnosis_statistics (24h metrics)
             │
             │ Query by Grafana
             ▼
    ┌─────────────────┐
    │    GRAFANA      │  ◄─── VISUALIZATION
    │  (Dashboard)    │  Real-time monitoring and historical analysis
    └─────────────────┘
             
             Dashboards:
             • Anomalies Dashboard:
               - Time-series charts (anomalies over time)
               - Device heatmap (anomaly frequency)
               - Severity breakdown (pie chart)
               - Recent anomalies table
             
             • Incidents Dashboard:
               - Incident timeline
               - Diagnosis status (DIAGNOSED vs PENDING)
               - Confidence scores (bar chart)
               - Remediation plan viewer
             
             Datasources:
             • Elasticsearch (log search, time-range filtering)
             • PostgreSQL (incident queries, aggregations)

┌────────────────────────────────────────────────────────────────────────────┐
│                        SUPPORTING SERVICES                                 │
└────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────┐
    │     REDIS       │  State management (anomaly detection windows)
    └─────────────────┘

    ┌─────────────────┐
    │   KAFKA UI      │  Web interface for Kafka monitoring (port 8080)
    └─────────────────┘  Topic inspection, consumer lag, message browser

---

## Service Communication Matrix

| Source Service | Target Service | Protocol | Port | Purpose | Data Format |
|----------------|----------------|----------|------|---------|-------------|
| Log Generator | Logstash | TCP | 5000 | Log ingestion | RFC 5424 Syslog |
| Logstash | Elasticsearch | HTTP | 9200 | Store parsed logs | JSON |
| Anomaly Detector | Elasticsearch | HTTP | 9200 | Query logs | JSON Query DSL |
| Anomaly Detector | Redis | TCP | 6379 | State management | Redis Protocol |
| Anomaly Detector | Kafka | TCP | 19092 | Publish anomalies | JSON (gzip) |
| Correlation Engine | Kafka | TCP | 19092 | Consume anomalies | JSON (gzip) |
| Correlation Engine | PostgreSQL | TCP | 5432 | Store incidents | SQL |
| Correlation Engine | Kafka | TCP | 19092 | Publish incidents | JSON (gzip) |
| LLM Diagnosis | Kafka | TCP | 19092 | Consume incidents | JSON (gzip) |
| LLM Diagnosis | OpenAI/Claude | HTTPS | 443 | LLM inference | REST API |
| LLM Diagnosis | PostgreSQL | TCP | 5432 | Update diagnosis | SQL |
| LLM Diagnosis | Kafka | TCP | 19092 | Publish diagnosed | JSON (gzip) |
| Grafana | Elasticsearch | HTTP | 9200 | Query logs | JSON |
| Grafana | PostgreSQL | TCP | 5432 | Query incidents | SQL |
| Kafka UI | Kafka | TCP | 19092 | Monitor topics | Kafka Protocol |

---

## Data Flow Timeline (End-to-End)

```
Time     Stage                    Latency   Details
─────────────────────────────────────────────────────────────────────────
T+0ms    Log Generated            -         Network device emits syslog event
         └─> TCP send
T+50ms   Logstash Receives        50ms      TCP buffer, immediate
         └─> Parse (grok)
T+100ms  Logstash Parses          50ms      Syslog → structured JSON
         └─> Enrich fields
T+200ms  Logstash Enriches        100ms     Add UUID, normalize timestamp
         └─> Batch (125 events or 1s)
T+1.2s   Elasticsearch Index      1s        HTTP POST, bulk API
         └─> Refresh interval
T+3s     Elasticsearch Visible    1.8s      Near real-time search
         └─> Wait for next poll
T+30s    Anomaly Detector Polls   27s       Scheduled every 30s
         └─> Query last 2min logs
T+30.5s  Query Results            500ms     ES aggregation query
         └─> Run detectors
T+31s    Detection Complete       500ms     Rule-based + ML inference
         └─> Publish to Kafka
T+31.1s  Kafka Publish            100ms     Async, compressed
         └─> Consumer lag
T+31.5s  Correlation Consumes     400ms     Kafka poll (max 100 records)
         └─> Buffering logic
T+60s    Correlation Triggers     28.5s     Wait for related anomalies (5-60s)
         └─> Create incident
T+60.5s  PostgreSQL Insert        500ms     INSERT INTO incidents
         └─> Publish to Kafka
T+61s    Kafka Publish            500ms     Incidents topic
         └─> LLM Consumer lag
T+61.5s  LLM Diagnosis Consumes   500ms     Kafka poll
         └─> Build context
T+65s    Context Built            3.5s      Query PG for history, enrich
         └─> LLM API call
T+180s   LLM Response             115s      GPT-4 inference (avg 120s)
         └─> Parse & validate
T+181s   Response Parsed          1s        JSON validation, confidence check
         └─> Update database
T+181.5s PostgreSQL Update        500ms     UPDATE incidents SET root_cause...
         └─> Publish diagnosed
T+182s   Kafka Publish            500ms     Incidents-diagnosed topic
─────────────────────────────────────────────────────────────────────────
TOTAL    END-TO-END              ~3 min     Log → Diagnosed Incident

Note: Total time varies based on:
- Anomaly detection window (30s fixed)
- Correlation buffer (5-60s variable)
- LLM inference time (60-180s variable)
Typical range: 2-10 minutes
```

---

## Key Design Decisions

### 1. **Why Kafka?**
- **Decoupling**: Services can restart without data loss
- **Scalability**: Partitioned topics (3 partitions) enable horizontal scaling
- **Replay**: Can reprocess events from any offset (debugging/recovery)
- **Backpressure**: Manual commit ensures no data loss on slow consumers

### 2. **Why Dual Storage (Elasticsearch + PostgreSQL)?**
- **Elasticsearch**: Optimized for log search (full-text, time-series)
- **PostgreSQL**: Optimized for incident management (ACID, JOINs, analytics)
- **Separation of Concerns**: Logs are ephemeral (7d), incidents are persistent

### 3. **Why Hybrid Anomaly Detection (Rules + ML)?**
- **Rules**: Fast, explainable, low false positives (known patterns)
- **ML (Isolation Forest)**: Discovers unknown patterns, adapts to baselines
- **Hybrid**: Combines speed + explainability + discovery

### 4. **Why LLM Integration?**
- **Context Understanding**: Correlates across multiple anomaly types
- **Natural Language**: Generates human-readable root cause explanations
- **Remediation**: Provides actionable step-by-step fix plans
- **Learning**: Can reference historical incident patterns

### 5. **Why Manual Kafka Commits?**
- **Reliability**: Only commit after successful downstream write (PostgreSQL)
- **At-least-once**: Ensures no data loss on service crash
- **Idempotency**: Use UUIDs for deduplication

---

## Failure Handling & Recovery

| Failure Scenario | Handling Strategy | Recovery Time |
|------------------|-------------------|---------------|
| **Logstash crash** | Disk-based persistent queue preserves unsent events | < 30s (restart) |
| **Elasticsearch down** | Logstash retries with exponential backoff, queues locally | < 5min (manual intervention) |
| **Kafka broker down** | Producer retries (3 attempts), fails fast if all down | < 10s (automatic failover) |
| **Anomaly Detector crash** | Kafka retains messages, consumer resumes from last commit | < 30s (restart) |
| **Correlation Engine crash** | Kafka retains messages, resume from last offset | < 30s (restart) |
| **LLM API timeout** | Retry with exponential backoff (max 3 attempts) | < 5min (fallback to manual) |
| **PostgreSQL down** | Service logs error, Kafka messages remain uncommitted | < 2min (auto-restart) |
| **Redis down** | Anomaly Detector degrades (loses state history) | < 30s (restart, warm-up) |

---

## Observability & Monitoring

### Health Checks (Docker)
- **Kafka**: Broker API version check (every 10s)
- **Elasticsearch**: Cluster health endpoint (every 10s)
- **PostgreSQL**: `pg_isready` (every 5s)
- **Redis**: PING command (every 5s)
- **Logstash**: Monitoring API (port 9600)

### Metrics Exposed
- **Kafka**: Topic lag, consumer offset, partition count (Kafka UI)
- **Elasticsearch**: Index size, query latency, indexing rate (REST API)
- **Anomaly Detector**: Logs processed, anomalies detected (structured logs)
- **Correlation Engine**: Incidents created, correlation time (structured logs)
- **LLM Diagnosis**: API calls, tokens used, cost, latency (structured logs + PG)

### Logging Strategy
- **Structured JSON logs** (all Python services use `loguru`)
- **Log levels**: DEBUG (dev), INFO (prod), ERROR (always)
- **Correlation IDs**: anomaly_id, incident_number (traces full flow)

---

## Deployment

### One-Command Startup
```bash
# Linux/Mac
./setup-noc.sh

# Windows
./setup-noc.ps1
```

This script:
1. Validates Docker is running
2. Starts 10 services via docker-compose
3. Waits for health checks (max 3min)
4. Creates Kafka topics (anomalies, incidents, incidents-diagnosed)
5. Displays access URLs

### One-Command Teardown
```bash
# Linux/Mac
./teardown-noc.sh

# Windows
./teardown-noc.ps1
```

This script:
1. Gracefully stops all services (SIGTERM)
2. Optionally preserves volumes (data persistence)
3. Removes containers and networks

---

## Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| Grafana | http://localhost:3000 | Dashboards (admin/admin) |
| Elasticsearch | http://localhost:9200 | Log queries |
| PostgreSQL | localhost:5432 | Incident queries (noc_admin/noc_password) |
| Kafka UI | http://localhost:8080 | Topic monitoring |
| Logstash API | http://localhost:9600 | Pipeline stats |
| Kafka | localhost:9092 | External producer/consumer |
| Redis | localhost:6379 | State queries |

---

## Technology Stack

| Layer | Technology | Version | License |
|-------|-----------|---------|---------|
| Collector | Logstash | 8.12.0 | Elastic License 2.0 |
| Transport | Apache Kafka | 3.7.0 | Apache 2.0 |
| Storage (Logs) | Elasticsearch | 8.12.0 | Elastic License 2.0 |
| Storage (Incidents) | PostgreSQL | 16 | PostgreSQL License |
| Cache | Redis | 7 | BSD 3-Clause |
| Processing | Python | 3.11 | PSF License |
| ML | scikit-learn | 1.4.0 | BSD 3-Clause |
| LLM | OpenAI/Claude/Ollama | API/Local | Proprietary/Open |
| Visualization | Grafana | 10.3.3 | AGPL 3.0 |
| Monitoring | Kafka UI | Latest | Apache 2.0 |

---

## Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| **Throughput** | 5-10K events/sec | Logstash batching + Kafka compression |
| **End-to-End Latency** | 2-10 minutes | Depends on LLM inference time |
| **Anomaly Detection** | < 30s | Polling interval |
| **Memory (Total)** | ~3GB | All services combined |
| **CPU (Idle)** | 10-15% | Background polling |
| **CPU (Peak)** | 60-80% | During LLM inference |
| **Storage (Logs)** | ~500MB/day | 7-day retention = 3.5GB |
| **Storage (Incidents)** | ~10MB/month | PostgreSQL |

---

## Summary

**Smart NOC** is a production-ready, event-driven architecture that demonstrates:
- ✅ Clean separation of concerns (collector → transport → processor → storage)
- ✅ Fault tolerance (at-least-once delivery, graceful degradation)
- ✅ Scalability (Kafka partitioning, stateless services)
- ✅ Advanced AI integration (ML + LLM for intelligent analysis)
- ✅ Comprehensive observability (health checks, metrics, structured logging)
- ✅ Developer-friendly (one-command deployment, extensive documentation)

**Key Innovation**: Hybrid anomaly detection (rule-based + ML) + LLM-powered diagnosis provides both speed and intelligence, going beyond traditional NOC systems.
