# Smart NOC - Complete Architecture Documentation

**Version:** 2.0  
**Date:** May 7, 2026 (Updated with Option A - Enriched Pipeline Flow)  
**Author:** Smart NOC Team

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Service Inventory](#service-inventory)
4. [Data Flow & Communication](#data-flow--communication)
5. [Kafka Topics & Message Contracts](#kafka-topics--message-contracts)
6. [Service Details](#service-details)
7. [Algorithms & Machine Learning](#algorithms--machine-learning)
8. [LLM Integration](#llm-integration)
9. [Database Architecture](#database-architecture)
10. [Technology Stack](#technology-stack)
11. [Deployment Architecture](#deployment-architecture)
12. [Performance Characteristics](#performance-characteristics)
13. [Version History](#version-history)

---

## Executive Summary

**Smart NOC** is an AI-powered Network Operations Center platform that automatically detects network anomalies, correlates them into incidents, and provides AI-driven root cause analysis and remediation plans. The system processes network device logs in real-time, identifies patterns, and generates actionable insights using Large Language Models (LLMs).

> **🆕 Version 2.0 Update (May 7, 2026)**: Implemented **Option A - Enriched Pipeline Flow** architecture. Logstash now serves as a centralized enrichment layer, adding business context (device_role, criticality) before downstream processing. This enables **context-aware anomaly detection** with criticality-based thresholds. See [Version History](#version-history) for details.

### Key Capabilities

- **Hybrid Anomaly Detection**: Combines rule-based thresholds + ML (Isolation Forest) for comprehensive coverage
- **Context-Aware Detection** 🆕: Criticality-aware thresholds (high: 2 events, medium: 3, low: 4)
- **Real-time Detection**: Detects 6 anomaly types (5 rule-based + 1 ML-based) with configurable thresholds
- **Centralized Enrichment** 🆕: Single source of truth for business context (device_role, criticality)
- **Intelligent Correlation**: Groups related anomalies into incidents using time-based and pattern-based algorithms
- **AI-Powered Diagnosis**: Uses LLMs (phi3 via Ollama) to generate root cause analysis with 75-95% confidence
- **Automated Remediation**: Provides step-by-step remediation plans with priority ordering
- **Zero-Failure Deployment**: Fully automated setup and teardown scripts for team distribution

### Architecture Principles

1. **Event-Driven**: Kafka-based asynchronous communication between services
2. **Microservices**: Independent, scalable services with single responsibilities
3. **Pipeline Flow** 🆕: Raw → Enrich → Detect → Correlate → Diagnose (single enrichment point)
4. **Real-time Processing**: Sub-second anomaly detection, 5-10 minute end-to-end diagnosis
5. **Stateless Design**: Services can be scaled horizontally without coordination
6. **Graceful Degradation**: Manual commit and retry logic ensures no data loss

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                   SMART NOC ARCHITECTURE (v2.0)                         │
│                    Enriched Pipeline Flow (Option A)                    │
└─────────────────────────────────────────────────────────────────────────┘

┌────────────────┐
│ Log Generator  │ Sends raw JSON logs
└───────┬────────┘
        │ Kafka Producer
        │ localhost:9092
        │ Topic: network-logs (raw)
        ▼
┌────────────────┐
│     KAFKA      │ Message broker
│ (network-logs) │ Raw logs from devices
└───────┬────────┘
        │
        │ Consumer (logstash-consumer group)
        ▼
┌────────────────┐
│   LOGSTASH     │ Enrichment Layer
│                │ 
│ ADDS:          │
│ • device_role  │ (core/distribution/edge)
│ • criticality  │ (high/medium/low)
│ • link_state   │ (extracted from message)
│ • fingerprint  │ (SHA256 hash)
│ • tags         │ (categorization)
└───────┬────────┘
        │
        ├─────────────────────┬──────────────────────────┐
        │                     │                          │
        │ Kafka Producer      │ HTTP PUT                 │
        │ (enriched)          │                          │
        ▼                     ▼                          │
┌────────────────┐   ┌────────────────┐                │
│     KAFKA      │   │ ELASTICSEARCH  │                │
│(network-logs-  │   │                │                │
│   enriched)    │   │ Index:         │                │
│                │   │ network-logs   │                │
│ Enriched logs  │   │ -2026.05.07    │                │
│ with business  │   │                │                │
│ context        │   │ Purpose:       │                │
└───────┬────────┘   │ - Storage      │                │
        │            │ - Search       │                │
        │            │ - Dashboards   │                │
        │            └────────────────┘                │
        │                                              │
        │ Consumer (anomaly-detector group)           │
        ▼                                              │
┌────────────────┐                                    │
│ ANOMALY        │ Context-Aware Detection            │
│ DETECTOR       │                                    │
│                │ Uses enriched data:                │
│ • Criticality- │ - device_role                      │
│   aware        │ - criticality                      │
│   thresholds   │ - All parsed fields                │
│ • High: 2 flaps│                                    │
│ • Med:  3 flaps│                                    │
│ • Low:  4 flaps│                                    │
└───────┬────────┘                                    │
        │                                              │
        │ Kafka Producer                               │
        │ Topic: anomalies                             │
        ▼                                              │
┌────────────────┐                                    │
│     KAFKA      │                                    │
│  (anomalies)   │                                    │
└───────┬────────┘                                    │
        │                                              │
        │ Consumer (correlation-engine)                │
        ▼                                              │
┌────────────────┐                                    │
│ CORRELATION    │ Groups related anomalies           │
│ ENGINE         │ into incidents                     │
└───────┬────────┘                                    │
        │                                              │
        ├────────────────────┬─────────────────────┐   │
        │                    │                     │   │
        ▼                    ▼                     │   │
┌────────────────┐   ┌────────────────┐           │   │
│  POSTGRESQL    │   │     KAFKA      │           │   │
│                │   │  (incidents)   │           │   │
│ Tables:        │   └───────┬────────┘           │   │
│ • incidents    │           │                    │   │
│ • anomalies    │           │ Consumer           │   │
│ • devices      │           │ (llm-diagnosis)    │   │
│ • diagnosis    │           ▼                    │   │
└────────────────┘   ┌────────────────┐           │   │
                     │ LLM DIAGNOSIS  │           │   │
                     │  (phi3/Ollama) │           │   │
                     │                │           │   │
                     │ Generates:     │           │   │
                     │ • Root cause   │           │   │
                     │ • Remediation  │           │   │
                     └────────────────┘           │   │

KEY ARCHITECTURE CHANGES (v2.0):
✅ Pipeline Flow: Raw → Logstash → Enriched → Anomaly Detector
✅ Single Enrichment Point: Logstash adds business context once
✅ Context-Aware Detection: Uses criticality for smart thresholds
✅ Better Observability: Anomalies include device_role, criticality
```

---

## Service Inventory

| Service | Container | Port(s) | Language | Purpose | Critical Path |
|---------|-----------|---------|----------|---------|---------------|
| **Logstash** | smart-noc-logstash | 5000, 9600 | Ruby (JRuby) | **Enrichment layer** - Parses, enriches with business context, publishes to Kafka + Elasticsearch | ✅ Yes |
| **Elasticsearch** | smart-noc-elasticsearch | 9200, 9300 | Java | Log storage & search (parallel, not critical path) | ❌ No* |
| **Anomaly Detector** | smart-noc-anomaly-detector | - | Python 3.11 | Context-aware anomaly detection with criticality-based thresholds | ✅ Yes |
| **Correlation Engine** | smart-noc-correlation-engine | - | Python 3.11 | Incident correlation | ✅ Yes |
| **LLM Diagnosis** | smart-noc-llm-diagnosis | - | Python 3.11 | AI root cause analysis | ✅ Yes |
| **Kafka** | smart-noc-kafka | 9092, 9093 | Java (Scala) | Message broker (4 topics) | ✅ Yes |
| **PostgreSQL** | smart-noc-postgres | 5432 | C | Persistent storage | ✅ Yes |
| **Redis** | smart-noc-redis | 6379 | C | State management (anomaly detection window) | ✅ Yes |
| **Grafana** | smart-noc-grafana | 3000 | Go | Visualization | ❌ No |
| **Kafka UI** | smart-noc-kafka-ui | 8080 | Java | Management UI | ❌ No |

**Critical Path**: Services in the critical path must be operational for core functionality (log → diagnosis).  
*Elasticsearch is parallel path for storage/search - system works without it but loses historical query capability.

---

## Data Flow & Communication

### End-to-End Data Flow (v2.0 - Enriched Pipeline)

```
┌────────────┐     ┌──────────┐     ┌──────────────┐     ┌──────────────┐
│ Network    │────▶│   Kafka  │────▶│   Logstash   │────▶│    Kafka     │
│ Device Log │     │ (network │     │ (Enrichment) │     │ (network-logs│
└────────────┘     │  -logs)  │     │              │     │  -enriched)  │
                   └──────────┘     └──────┬───────┘     └──────┬───────┘
                    Raw JSON             │                     │
                                         │                     │
                                         ▼                     ▼
                                   ┌──────────┐        ┌──────────────┐
                                   │Elastic-  │        │   Anomaly    │
                                   │search    │        │   Detector   │
                                   └──────────┘        └──────┬───────┘
                                   (Storage/Search)   (Context-Aware)
                                                                │
                                                                ▼
                                                         [Kafka: anomalies]
                                                                │
                                    ┌──────────────────────────┘
                                    ▼
                              ┌──────────┐
                              │Correlation│
                              │ Engine   │
                              └────┬─────┘
                                   │
                                   ▼
                            [Kafka: incidents]
                                   │
                   ┌───────────────┴───────────────┐
                   ▼                               ▼
             ┌──────────┐                   ┌──────────┐
             │   LLM    │──────────────────▶│PostgreSQL│
             │Diagnosis │  (Update DB)      │          │
             └────┬─────┘                   └──────────┘
                  │
                  ▼
         [Kafka: incidents-diagnosed]
```

### Enrichment Details (NEW in v2.0)

**Logstash Enrichment Layer** adds:
1. **device_role** - Derived from device_id pattern (core-*/dist-*/edge-*)
2. **criticality** - Business importance (high/medium/low)
3. **link_state** - Extracted from syslog message via grok
4. **bgp_neighbor** - Extracted BGP peer IPs
5. **cpu_utilization** - Parsed from CPU alerts
6. **event_fingerprint** - SHA256 hash for deduplication
7. **tags** - Categorization (interface, security, performance, etc.)
8. **@timestamp** - Normalized ISO8601 timestamp

**Benefits**:
- Single enrichment point (DRY principle)
- Downstream services get consistent business context
- Criticality-aware thresholds in anomaly detection
- Better incident prioritization

### Timing Characteristics (Updated v2.0)

| Stage | Latency | Notes |
|-------|---------|-------|
| **Log Generation → Kafka** | < 50ms | Kafka producer, async |
| **Kafka → Logstash** | < 100ms | Consumer poll interval |
| **Logstash Processing** | 20-50ms | Parsing, enrichment, transforms |
| **Logstash → Kafka (enriched)** | < 50ms | Kafka producer, async, gzip |
| **Logstash → Elasticsearch** | < 1s | Batch size 125, flush 1s |
| **Elasticsearch Indexing** | < 2s | Near real-time refresh |
| **Kafka (enriched) → Anomaly Detector** | < 100ms | Consumer poll, processing |
| **Anomaly Detection** | < 100ms | In-memory analysis, Redis state |
| **Kafka Publish (anomalies)** | < 50ms | Compressed, async |
| **Correlation Buffer** | 5-60s | Waits for related anomalies |
| **Kafka Publish (incidents)** | < 50ms | Compressed, async |
| **LLM Diagnosis** | 120-180s | phi3 inference time |
| **Database Update** | < 500ms | PostgreSQL transaction |
| **End-to-End** | **~5-10 min** | Log to diagnosed incident |

**Enrichment Pipeline Adds**: ~50-100ms total latency (acceptable for better accuracy)

---

## Kafka Topics & Message Contracts

### Topic: `network-logs`

**Publisher**: Log Generator  
**Consumer**: Logstash  
**Partitions**: 3  
**Retention**: 1 day (transient data)  
**Compression**: gzip

#### Message Schema (Raw Logs)

```json
{
  "timestamp": "May 06 19:55:00",
  "device_id": "core-router-01",
  "device_type": "router",
  "severity": "ERROR",
  "event_type": "INTERFACE_DOWN",
  "interface": "GigabitEthernet0/1",
  "message": "%LINK-3-UPDOWN: Interface GigabitEthernet0/1, changed state to down"
}
```

**Purpose**: Raw network device logs before enrichment

---

### Topic: `network-logs-enriched` (NEW in v2.0)

**Publisher**: Logstash  
**Consumer**: Anomaly Detector  
**Partitions**: 3  
**Retention**: 1 day (transient data)  
**Compression**: gzip

#### Message Schema (Enriched Logs)

```json
{
  "@timestamp": "2026-05-06T19:55:00.000Z",
  "device_id": "core-router-01",
  "device_type": "router",
  "device_role": "core",
  "criticality": "high",
  "severity": "ERROR",
  "event_type": "INTERFACE_DOWN",
  "interface": "GigabitEthernet0/1",
  "link_state": "down",
  "tags": ["interface", "connectivity"],
  "event_fingerprint": "2f5657868ef6c5a3483d5dedae72cc1a4d05e5402236dcb708c50466ad2de49a",
  "message": "%LINK-3-UPDOWN: Interface GigabitEthernet0/1, changed state to down",
  "indexed_at": "2026-05-06T19:54:48.517720486Z"
}
```

**Fields Added by Logstash**:
- `device_role`: Derived from device_id pattern (core/distribution/edge)
- `criticality`: Business importance level (high/medium/low)
- `link_state`: Extracted from message with grok pattern
- `tags`: Categorization tags for filtering
- `event_fingerprint`: SHA256 hash for deduplication
- `@timestamp`: Normalized ISO8601 timestamp

**Purpose**: Enriched logs with business context for context-aware anomaly detection

---

### Topic: `anomalies`

**Publisher**: Anomaly Detector  
**Consumer**: Correlation Engine  
**Partitions**: 3 (device-keyed for ordering)  
**Retention**: 7 days  
**Compression**: gzip

#### Message Schema (Updated v2.0 - includes enriched context)

```json
{
  "anomaly_id": "550e8400-e29b-41d4-a716-446655440000",
  "anomaly_type": "INTERFACE_FLAPPING",
  "device_id": "core-router-01",
  "device_role": "core",
  "criticality": "high",
  "severity": "HIGH",
  "confidence": 1.0,
  "start_time": "2026-05-06T14:30:00.000Z",
  "end_time": "2026-05-06T14:30:15.000Z",
  "duration_seconds": 15,
  "event_count": 4,
  "window_minutes": 5,
  "detection_method": "rule",
  "interface": "GigabitEthernet0/1",
  "details": "Interface changed state 4 times in 5 minutes (criticality: high)",
  "detected_at": "2026-05-06T14:30:30.000Z",
  "detector_version": "1.0.0"
}
```

**Enriched Fields (NEW in v2.0)**:
- `device_role`: From Logstash enrichment (core/distribution/edge)
- `criticality`: From Logstash enrichment (high/medium/low)
- `details`: Now includes criticality context for better observability

**Anomaly Types** (with criticality-aware thresholds):
- `INTERFACE_FLAPPING`: Interface state changes
  - High criticality: 2 flaps/5min
  - Medium criticality: 3 flaps/5min  
  - Low criticality: 4 flaps/5min
- `HIGH_CPU`: CPU utilization > 80% (threshold: 1 min sustained)
- `BGP_INSTABILITY`: BGP neighbor flaps (threshold: 2 flaps/5min)
- `AUTH_BRUTE_FORCE`: Failed login attempts (threshold: 5/2min)
- `HIGH_MEMORY`: Memory utilization > 85% (threshold: 2 min sustained)
- `ML_DETECTED_ANOMALY`: Novel patterns detected by Isolation Forest (unsupervised)

---

### Topic: `incidents`

**Publisher**: Correlation Engine  
**Consumer**: LLM Diagnosis Service  
**Partitions**: 3 (incident-keyed)  
**Retention**: 30 days  
**Compression**: gzip

#### Message Schema

```json
{
  "id": "6dd1254c-2454-4ba0-893c-de73e4f34f76",
  "incident_number": 42,
  "incident_type": "DEVICE_FAILURE",
  "status": "ACTIVE",
  "severity": "HIGH",
  "primary_device": "core-router-01",
  "affected_devices": ["core-router-01", "access-switch-02"],
  "affected_device_count": 2,
  "anomaly_count": 3,
  "anomaly_ids": [
    "550e8400-e29b-41d4-a716-446655440001",
    "550e8400-e29b-41d4-a716-446655440002"
  ],
  "primary_anomaly_type": "INTERFACE_FLAPPING",
  "correlation_method": "TIME_BASED",
  "impact_score": 8.5,
  "start_time": "2026-04-25T14:30:00.000Z",
  "end_time": null,
  "duration_seconds": 45,
  "created_at": "2026-04-25T14:30:45.000Z",
  "updated_at": "2026-04-25T14:30:45.000Z",
  "correlation_metadata": {
    "correlation_window_seconds": 60,
    "primary_correlation_factor": "device_similarity"
  }
}
```

**Incident Types** (derived from patterns):
- `DEVICE_FAILURE`: Same device, 3+ anomaly types
- `NETWORK_PERFORMANCE`: Multiple devices, same type (HIGH_CPU)
- `SECURITY_INCIDENT`: Authentication failures pattern
- `CONNECTIVITY_ISSUE`: Interface/BGP related
- `UNKNOWN`: Default for unclassified patterns

---

### Topic: `incidents-diagnosed`

**Publisher**: LLM Diagnosis Service  
**Consumer**: (Future) Ticketing systems, alerting  
**Partitions**: 3  
**Retention**: 30 days  
**Compression**: gzip

#### Message Schema

```json
{
  "id": "6dd1254c-2454-4ba0-893c-de73e4f34f76",
  "incident_number": 42,
  "incident_type": "DEVICE_FAILURE",
  "status": "ACTIVE",
  "severity": "HIGH",
  "primary_device": "core-router-01",
  "affected_devices": ["core-router-01"],
  "anomaly_count": 3,
  
  "root_cause": "The primary cause appears to be a hardware fault in GigabitEthernet0/1, potentially due to a faulty SFP module or cable damage. The interface flapping, combined with environmental stress indicators (high CPU/memory), suggests a physical layer issue that is cascading into device instability.",
  
  "root_cause_confidence": 0.85,
  
  "remediation_plan": [
    {
      "step": 1,
      "priority": "IMMEDIATE",
      "action": "Inspect physical connections on GigabitEthernet0/1",
      "command": "",
      "expected_outcome": "Identify loose cables or damaged connectors",
      "estimated_time_minutes": 5
    },
    {
      "step": 2,
      "priority": "IMMEDIATE",
      "action": "Replace SFP module in GigabitEthernet0/1",
      "command": "hw-module slot 0/1 reload",
      "expected_outcome": "Interface stabilizes, no further flapping",
      "estimated_time_minutes": 10
    },
    {
      "step": 3,
      "priority": "HIGH",
      "action": "Monitor interface status for 30 minutes",
      "command": "show interface GigabitEthernet0/1 | include line protocol",
      "expected_outcome": "Interface remains UP/UP",
      "estimated_time_minutes": 30
    }
  ],
  
  "diagnosis_timestamp": "2026-04-25T14:35:30.000Z",
  "llm_model": "phi3",
  
  "diagnosis_metadata": {
    "total_tokens": 2391,
    "prompt_tokens": 1205,
    "completion_tokens": 1186,
    "duration_ms": 131526,
    "estimated_cost_usd": 0.0,
    "provider": "ollama",
    "model_version": "phi3:latest",
    "temperature": 0.3,
    "max_tokens": 2000
  }
}
```

---

## Service Details

### 1. Log Generator (Development Tool)

**Path**: `services/log-generator/`  
**Language**: Python 3.11  
**Type**: CLI tool (not a service)

#### Responsibility

Simulates network device logs in syslog format for testing and demonstration purposes. Not part of production deployment.

#### Algorithms

- **Event Generation**: Random device selection, timestamp generation
- **Scenario Templates**: Pre-defined patterns for realistic network events
- **Rate Control**: Configurable events/second with Poisson distribution

#### Usage

```bash
# Random logs
python generate_logs.py --rate 10 --duration 60

# Scenario-based (realistic incidents)
python generate_scenarios.py --scenario flapping --count 5
```

#### Scenarios

| Scenario | Events | Anomaly Type | Realistic Pattern |
|----------|--------|--------------|-------------------|
| `flapping` | 6-8 | INTERFACE_FLAPPING | Interface up/down cycles |
| `high-cpu` | 4-6 | HIGH_CPU | Sustained high utilization |
| `bgp-instability` | 4-6 | BGP_INSTABILITY | BGP neighbor state changes |
| `brute-force` | 8-12 | AUTH_FAILURES | Failed login attempts |
| `chaos` | 8-12 | Mixed | Multiple anomaly types, same device |

---

### 2. Logstash (Log Ingestion & Parsing)

**Container**: `smart-noc-logstash`  
**Image**: `docker.elastic.co/logstash/logstash:8.12.0`  
**Ports**: 5000 (TCP input), 9600 (monitoring API)

#### Responsibility

1. **Ingest** raw syslog messages from network devices (or log generator)
2. **Parse** unstructured logs into structured JSON using Grok patterns
3. **Enrich** logs with metadata (severity levels, device types, timestamps)
4. **Forward** to Elasticsearch for indexing and storage

#### Pipeline Configuration

```ruby
input {
  tcp {
    port => 5000
    codec => json_lines
  }
}

filter {
  # Parse syslog format
  grok {
    match => {
      "message" => "%{SYSLOGBASE} %{GREEDYDATA:log_message}"
    }
  }
  
  # Parse timestamp
  date {
    match => ["timestamp", "ISO8601"]
    target => "@timestamp"
  }
  
  # Enrich severity
  mutate {
    add_field => {
      "severity_level" => "%{severity}"
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "logs-%{+YYYY.MM.dd}"
  }
}
```

#### Performance

- **Throughput**: ~1000 events/second (single instance)
- **Batch Size**: 125 events
- **Flush Interval**: 1 second
- **Memory**: 1GB heap (-Xms1g -Xmx1g)

---

### 3. Elasticsearch (Log Storage & Search)

**Container**: `smart-noc-elasticsearch`  
**Image**: `docker.elastic.co/elasticsearch/elasticsearch:8.12.0`  
**Ports**: 9200 (HTTP API), 9300 (cluster communication)

#### Responsibility

1. **Index** structured logs from Logstash with full-text search capability
2. **Store** time-series log data with 7-day retention policy
3. **Query** logs for anomaly detection and historical analysis
4. **Aggregate** log statistics for dashboard visualization

#### Index Configuration

```json
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "refresh_interval": "1s",
    "index.lifecycle.name": "logs-policy",
    "index.lifecycle.rollover_alias": "logs"
  },
  "mappings": {
    "properties": {
      "@timestamp": { "type": "date" },
      "device": { "type": "keyword" },
      "severity": { "type": "keyword" },
      "log_type": { "type": "keyword" },
      "message": { "type": "text" },
      "interface": { "type": "keyword" },
      "cpu_usage": { "type": "float" },
      "memory_usage": { "type": "float" }
    }
  }
}
```

#### Query Pattern (Anomaly Detector)

```json
{
  "query": {
    "bool": {
      "must": [
        { "range": { "@timestamp": { "gte": "now-5m" } } },
        { "term": { "log_type": "interface" } }
      ]
    }
  },
  "aggs": {
    "by_device": {
      "terms": { "field": "device" },
      "aggs": {
        "by_interface": {
          "terms": { "field": "interface" },
          "aggs": {
            "state_changes": {
              "value_count": { "field": "interface_state" }
            }
          }
        }
      }
    }
  }
}
```

#### Performance

- **Write Rate**: ~5000 docs/second
- **Search Latency**: < 100ms (p95)
- **Storage**: ~1GB per day (10k events/day)
- **Retention**: 7 days (auto-delete via ILM)

---

### 4. Anomaly Detector

**Container**: `smart-noc-anomaly-detector`  
**Path**: `services/anomaly-detector/`  
**Language**: Python 3.11  
**Dependencies**: elasticsearch-py, loguru, pyyaml

#### Responsibility

1. **Poll** Elasticsearch every 30 seconds for recent logs
2. **Detect** anomalies using **dual detection approach**:
   - **Rule-Based**: 5 specific anomaly types with threshold-based algorithms
   - **ML-Based**: Isolation Forest for unsupervised anomaly detection
3. **Validate** anomaly confidence scores (0.0-1.0)
4. **Publish** detected anomalies to Kafka `anomalies` topic

#### Detection Algorithms

##### Algorithm 1: Interface Flapping Detection

**Type**: Time-series threshold  
**Threshold**: 2 state changes within 5 minutes (configurable)

```python
def detect_interface_flapping(self, time_window_minutes=5):
    """
    Query logs for interface state changes (up/down)
    Group by device + interface
    Count state transitions in time window
    Flag if count >= threshold
    """
    query = {
        "query": {
            "bool": {
                "must": [
                    {"range": {"@timestamp": {"gte": f"now-{time_window_minutes}m"}}},
                    {"term": {"log_type": "interface"}},
                    {"terms": {"interface_state": ["up", "down"]}}
                ]
            }
        },
        "aggs": {
            "by_device": {
                "terms": {"field": "device"},
                "aggs": {
                    "by_interface": {
                        "terms": {"field": "interface"},
                        "aggs": {
                            "state_changes": {
                                "cardinality": {"field": "interface_state"}
                            }
                        }
                    }
                }
            }
        }
    }
    
    # Threshold logic
    for device_bucket in aggregations:
        for interface_bucket in device_bucket['interfaces']:
            flap_count = interface_bucket['state_changes']['value']
            if flap_count >= self.config['interface_flapping']['threshold']:
                # Create anomaly
                confidence = min(1.0, flap_count / 10.0)  # 10 flaps = 100% confidence
                severity = self._calculate_severity(confidence)
                yield create_anomaly(
                    type="INTERFACE_FLAPPING",
                    device=device,
                    interface=interface,
                    confidence=confidence,
                    severity=severity,
                    metadata={"flap_count": flap_count}
                )
```

**Confidence Calculation**:
```
confidence = min(1.0, actual_flaps / 10.0)
Example: 2 flaps → 0.20, 5 flaps → 0.50, 10+ flaps → 1.00
```

---

##### Algorithm 2: High CPU Detection

**Type**: Time-series aggregation  
**Threshold**: CPU > 80% for 1 minute sustained (configurable)

```python
def detect_high_cpu(self, threshold=80, duration_minutes=1):
    """
    Query logs with cpu_usage field
    Calculate average CPU over time window
    Flag if sustained above threshold
    """
    query = {
        "query": {
            "bool": {
                "must": [
                    {"range": {"@timestamp": {"gte": f"now-{duration_minutes}m"}}},
                    {"exists": {"field": "cpu_usage"}},
                    {"range": {"cpu_usage": {"gte": threshold}}}
                ]
            }
        },
        "aggs": {
            "by_device": {
                "terms": {"field": "device"},
                "aggs": {
                    "avg_cpu": {"avg": {"field": "cpu_usage"}},
                    "max_cpu": {"max": {"field": "cpu_usage"}},
                    "sample_count": {"value_count": {"field": "cpu_usage"}}
                }
            }
        }
    }
    
    # Sustained check: require minimum 3 samples
    for device_bucket in aggregations:
        sample_count = device_bucket['sample_count']['value']
        if sample_count >= 3:
            avg_cpu = device_bucket['avg_cpu']['value']
            max_cpu = device_bucket['max_cpu']['value']
            
            if avg_cpu >= threshold:
                confidence = min(1.0, (avg_cpu - threshold) / 20.0)  # 100% CPU = full confidence
                severity = "CRITICAL" if avg_cpu > 95 else "HIGH"
                yield create_anomaly(
                    type="HIGH_CPU",
                    device=device,
                    confidence=confidence,
                    severity=severity,
                    metadata={
                        "avg_cpu": avg_cpu,
                        "max_cpu": max_cpu,
                        "duration_minutes": duration_minutes
                    }
                )
```

**Confidence Calculation**:
```
confidence = min(1.0, (actual_cpu - threshold) / 20.0)
Example: 85% CPU → 0.25, 90% CPU → 0.50, 100% CPU → 1.00
```

---

##### Algorithm 3: BGP Instability Detection

**Type**: State change counter  
**Threshold**: 2 BGP neighbor state changes in 5 minutes

```python
def detect_bgp_instability(self, time_window_minutes=5, threshold=2):
    """
    Query logs for BGP neighbor state changes (established/down)
    Count transitions per device + neighbor pair
    Flag if threshold exceeded
    """
    query = {
        "query": {
            "bool": {
                "must": [
                    {"range": {"@timestamp": {"gte": f"now-{time_window_minutes}m"}}},
                    {"term": {"log_type": "bgp"}},
                    {"terms": {"bgp_state": ["Established", "Down", "Idle"]}}
                ]
            }
        },
        "aggs": {
            "by_device": {
                "terms": {"field": "device"},
                "aggs": {
                    "by_neighbor": {
                        "terms": {"field": "bgp_neighbor"},
                        "aggs": {
                            "state_count": {"value_count": {"field": "bgp_state"}}
                        }
                    }
                }
            }
        }
    }
    
    for device_bucket in aggregations:
        for neighbor_bucket in device_bucket['neighbors']:
            state_changes = neighbor_bucket['state_count']['value']
            if state_changes >= threshold:
                confidence = min(1.0, state_changes / 5.0)  # 5+ changes = full confidence
                yield create_anomaly(
                    type="BGP_INSTABILITY",
                    device=device,
                    confidence=confidence,
                    severity="HIGH",
                    metadata={
                        "neighbor": neighbor_bucket['key'],
                        "state_changes": state_changes
                    }
                )
```

---

##### Algorithm 4: Authentication Failures Detection

**Type**: Rate-based threshold  
**Threshold**: 3+ failed login attempts per minute

```python
def detect_authentication_failures(self, time_window_minutes=1, threshold=3):
    """
    Query logs for authentication failure messages
    Count failures per device + source IP
    Flag if rate threshold exceeded
    """
    query = {
        "query": {
            "bool": {
                "must": [
                    {"range": {"@timestamp": {"gte": f"now-{time_window_minutes}m"}}},
                    {"term": {"log_type": "authentication"}},
                    {"term": {"auth_result": "failed"}}
                ]
            }
        },
        "aggs": {
            "by_device": {
                "terms": {"field": "device"},
                "aggs": {
                    "by_source_ip": {
                        "terms": {"field": "source_ip"},
                        "aggs": {
                            "failure_count": {"value_count": {"field": "@timestamp"}}
                        }
                    }
                }
            }
        }
    }
    
    for device_bucket in aggregations:
        for source_bucket in device_bucket['sources']:
            failure_count = source_bucket['failure_count']['value']
            if failure_count >= threshold:
                confidence = min(1.0, failure_count / 10.0)  # 10+ failures = full confidence
                severity = "CRITICAL" if failure_count >= 10 else "HIGH"
                yield create_anomaly(
                    type="AUTHENTICATION_FAILURES",
                    device=device,
                    confidence=confidence,
                    severity=severity,
                    metadata={
                        "source_ip": source_bucket['key'],
                        "failure_count": failure_count,
                        "rate_per_minute": failure_count / time_window_minutes
                    }
                )
```

---

##### Algorithm 5: High Memory Detection

**Type**: Time-series aggregation  
**Threshold**: Memory > 85% for 2 minutes sustained

```python
def detect_high_memory(self, threshold=85, duration_minutes=2):
    """
    Query logs with memory_usage field
    Calculate average memory over time window
    Flag if sustained above threshold
    """
    # Similar to High CPU, but with memory_usage field
    # Confidence calculation based on how far above threshold
    confidence = min(1.0, (actual_memory - threshold) / 15.0)
```

---

#### Configuration

**File**: `services/anomaly-detector/config.yaml`

```yaml
elasticsearch:
  host: "elasticsearch"
  port: 9200
  index_pattern: "logs-*"

kafka:
  bootstrap_servers: "kafka:9092"
  topic: "anomalies"
  compression: "gzip"

detection:
  poll_interval_seconds: 30
  lookback_window_minutes: 5
  
  interface_flapping:
    enabled: true
    threshold: 2  # Number of flaps
    time_window_minutes: 5
    confidence_multiplier: 0.1  # Per flap
  
  high_cpu:
    enabled: true
    threshold: 80  # Percentage
    duration_minutes: 1
    min_samples: 3
  
  bgp_instability:
    enabled: true
    threshold: 2  # State changes
    time_window_minutes: 5
  
  authentication_failures:
    enabled: true
    threshold: 3  # Failures per minute
    time_window_minutes: 1
  
  high_memory:
    enabled: true
    threshold: 85  # Percentage
    duration_minutes: 2
    min_samples: 3
```

#### Performance

- **Polling Frequency**: Every 30 seconds
- **Query Execution**: < 500ms per anomaly type
- **Detection Latency**: 30-60 seconds (next poll cycle)
- **Kafka Publish**: < 50ms per anomaly
- **Memory Usage**: ~200MB
- **CPU Usage**: < 5% (idle), ~20% (during detection)

---

### 5. Correlation Engine

**Container**: `smart-noc-correlation-engine`  
**Path**: `services/correlation-engine/`  
**Language**: Python 3.11  
**Dependencies**: confluent-kafka, loguru, psycopg2

#### Responsibility

1. **Consume** anomalies from Kafka `anomalies` topic
2. **Correlate** related anomalies into incidents using time-based and pattern-based algorithms
3. **Classify** incidents by type (DEVICE_FAILURE, NETWORK_PERFORMANCE, etc.)
4. **Persist** incidents to PostgreSQL database
5. **Publish** incidents to Kafka `incidents` topic

#### Correlation Algorithms

##### Algorithm 1: Time-Based Correlation

**Type**: Sliding window + Device grouping  
**Window**: 60 seconds (configurable)

```python
class TimeBasedCorrelator:
    """
    Correlates anomalies that occur within a time window on the same device
    """
    
    def __init__(self, time_window_seconds=60):
        self.time_window_seconds = time_window_seconds
        self.anomaly_buffer = []  # In-memory buffer of recent anomalies
        
    def add_anomaly(self, anomaly: Dict) -> Optional[Dict]:
        """
        Add anomaly to buffer, check for correlation
        Returns incident if correlation threshold met
        """
        self.anomaly_buffer.append(anomaly)
        
        # Remove old anomalies outside time window
        current_time = datetime.utcnow()
        self.anomaly_buffer = [
            a for a in self.anomaly_buffer
            if (current_time - parse_timestamp(a['detection_timestamp'])).total_seconds() 
               <= self.time_window_seconds
        ]
        
        # Group by device
        device_groups = self._group_by_device(self.anomaly_buffer)
        
        # Check each device for correlation
        for device, anomalies in device_groups.items():
            if self._should_create_incident(anomalies):
                incident = self._create_incident(anomalies)
                
                # Remove correlated anomalies from buffer
                self.remove_anomalies(anomalies)
                
                return incident
        
        return None
    
    def _should_create_incident(self, anomalies: List[Dict]) -> bool:
        """
        Correlation criteria:
        - 2+ anomalies of same type (indicates sustained issue)
        - OR 3+ anomalies of different types (indicates device failure)
        - OR 1 CRITICAL severity anomaly (immediate escalation)
        """
        if len(anomalies) < 2:
            return False
        
        # Check for critical severity
        if any(a['severity'] == 'CRITICAL' for a in anomalies):
            return True
        
        # Check for same-type clustering
        type_counts = {}
        for anomaly in anomalies:
            anom_type = anomaly['anomaly_type']
            type_counts[anom_type] = type_counts.get(anom_type, 0) + 1
        
        # 2+ of same type = incident
        if any(count >= 2 for count in type_counts.values()):
            return True
        
        # 3+ different types = device failure incident
        if len(type_counts) >= 3:
            return True
        
        return False
    
    def _create_incident(self, anomalies: List[Dict]) -> Dict:
        """
        Create incident from correlated anomalies
        """
        # Determine incident type based on pattern
        incident_type = self._classify_incident_type(anomalies)
        
        # Calculate impact score
        impact_score = self._calculate_impact_score(anomalies)
        
        # Determine severity
        severity = self._determine_severity(anomalies, impact_score)
        
        # Create incident
        incident = {
            'id': str(uuid.uuid4()),
            'incident_number': self._generate_incident_number(),
            'incident_type': incident_type,
            'status': 'ACTIVE',
            'severity': severity,
            'primary_device': anomalies[0]['device'],
            'affected_devices': list(set(a['device'] for a in anomalies)),
            'affected_device_count': len(set(a['device'] for a in anomalies)),
            'anomaly_count': len(anomalies),
            'anomaly_ids': [a['anomaly_id'] for a in anomalies],
            'primary_anomaly_type': anomalies[0]['anomaly_type'],
            'correlation_method': 'TIME_BASED',
            'impact_score': impact_score,
            'start_time': min(a['start_time'] for a in anomalies),
            'end_time': max(a['end_time'] for a in anomalies) if any(a.get('end_time') for a in anomalies) else None,
            'duration_seconds': self._calculate_duration(anomalies),
            'created_at': datetime.utcnow().isoformat() + 'Z',
            'updated_at': datetime.utcnow().isoformat() + 'Z',
            'correlation_metadata': {
                'correlation_window_seconds': self.time_window_seconds,
                'primary_correlation_factor': 'device_similarity'
            }
        }
        
        return incident
    
    def _classify_incident_type(self, anomalies: List[Dict]) -> str:
        """
        Classify incident type based on anomaly patterns
        """
        anomaly_types = [a['anomaly_type'] for a in anomalies]
        unique_types = set(anomaly_types)
        device_count = len(set(a['device'] for a in anomalies))
        
        # Pattern 1: Single device, multiple anomaly types = DEVICE_FAILURE
        if device_count == 1 and len(unique_types) >= 3:
            return 'DEVICE_FAILURE'
        
        # Pattern 2: Multiple devices, same anomaly type = NETWORK_PERFORMANCE
        if device_count > 1 and len(unique_types) == 1:
            if 'HIGH_CPU' in unique_types or 'HIGH_MEMORY' in unique_types:
                return 'NETWORK_PERFORMANCE'
            if 'INTERFACE_FLAPPING' in unique_types or 'BGP_INSTABILITY' in unique_types:
                return 'CONNECTIVITY_ISSUE'
        
        # Pattern 3: Authentication failures = SECURITY_INCIDENT
        if 'AUTHENTICATION_FAILURES' in unique_types:
            return 'SECURITY_INCIDENT'
        
        # Pattern 4: Default
        return 'UNKNOWN'
    
    def _calculate_impact_score(self, anomalies: List[Dict]) -> float:
        """
        Calculate impact score (0-10) based on multiple factors
        
        Factors:
        - Number of anomalies (more = higher impact)
        - Severity levels (CRITICAL > HIGH > MEDIUM)
        - Device count (more devices = higher impact)
        - Confidence scores (higher confidence = higher impact)
        """
        # Base score from anomaly count
        base_score = min(10.0, len(anomalies) * 1.5)
        
        # Severity multiplier
        severity_weights = {'CRITICAL': 3.0, 'HIGH': 2.0, 'MEDIUM': 1.0, 'LOW': 0.5}
        avg_severity_weight = sum(
            severity_weights.get(a['severity'], 1.0) for a in anomalies
        ) / len(anomalies)
        
        # Device count multiplier
        device_multiplier = min(2.0, 1.0 + (len(set(a['device'] for a in anomalies)) - 1) * 0.2)
        
        # Confidence multiplier
        avg_confidence = sum(a['confidence'] for a in anomalies) / len(anomalies)
        
        # Final score
        impact_score = (base_score * avg_severity_weight * device_multiplier * avg_confidence) / 3.0
        
        return min(10.0, impact_score)
    
    def _determine_severity(self, anomalies: List[Dict], impact_score: float) -> str:
        """
        Determine incident severity based on anomalies and impact
        """
        # If any anomaly is CRITICAL, incident is CRITICAL
        if any(a['severity'] == 'CRITICAL' for a in anomalies):
            return 'CRITICAL'
        
        # Use impact score
        if impact_score >= 8.0:
            return 'CRITICAL'
        elif impact_score >= 5.0:
            return 'HIGH'
        elif impact_score >= 3.0:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def remove_anomalies(self, anomalies: List[Dict]):
        """
        Remove anomalies from buffer after correlation
        Critical fix: Prevents infinite incident creation loop
        """
        anomaly_ids = set(a['anomaly_id'] for a in anomalies)
        self.anomaly_buffer = [
            a for a in self.anomaly_buffer 
            if a['anomaly_id'] not in anomaly_ids
        ]
```

**Key Insight**: The `remove_anomalies()` method is critical - without it, the same anomalies would be correlated repeatedly, creating infinite incidents.

---

##### Algorithm 2: Pattern-Based Correlation (Future Enhancement)

**Type**: Topology-aware + ML clustering  
**Status**: Planned for v2.0

```python
class PatternBasedCorrelator:
    """
    Uses network topology and ML clustering to correlate anomalies
    
    Features (planned):
    - Network topology graph (devices, links, bandwidth)
    - K-means clustering on anomaly features
    - DBSCAN for spatial-temporal clustering
    - Graph traversal for impact propagation
    """
    pass
```

---

#### Database Operations

```python
def persist_incident(self, incident: Dict):
    """
    Insert incident into PostgreSQL
    Also inserts anomaly associations
    """
    with self.db_engine.connect() as conn:
        # Insert incident
        conn.execute(
            text("""
                INSERT INTO incidents (
                    id, incident_number, incident_type, status, severity,
                    primary_device, affected_devices, affected_device_count,
                    anomaly_count, primary_anomaly_type, correlation_method,
                    impact_score, start_time, end_time, duration_seconds,
                    created_at, updated_at, correlation_metadata
                )
                VALUES (
                    CAST(:id AS uuid), :incident_number, :incident_type, :status, :severity,
                    :primary_device, :affected_devices, :affected_device_count,
                    :anomaly_count, :primary_anomaly_type, :correlation_method,
                    :impact_score, :start_time, :end_time, :duration_seconds,
                    :created_at, :updated_at, CAST(:correlation_metadata AS jsonb)
                )
            """),
            {
                'id': incident['id'],
                'incident_number': incident['incident_number'],
                # ... all fields
                'correlation_metadata': json.dumps(incident['correlation_metadata'])
            }
        )
        
        # Insert anomaly associations
        for anomaly_id in incident['anomaly_ids']:
            conn.execute(
                text("""
                    INSERT INTO incident_anomalies (incident_id, anomaly_id)
                    VALUES (CAST(:incident_id AS uuid), CAST(:anomaly_id AS uuid))
                    ON CONFLICT DO NOTHING
                """),
                {'incident_id': incident['id'], 'anomaly_id': anomaly_id}
            )
        
        conn.commit()
```

#### Configuration

**File**: `services/correlation-engine/config.py`

```python
# Correlation settings
CORRELATION_TIME_WINDOW_SECONDS = 60  # Group anomalies within 60s
CORRELATION_MIN_ANOMALIES = 2  # Minimum 2 anomalies for incident
CORRELATION_SAME_TYPE_THRESHOLD = 2  # 2+ of same type = incident
CORRELATION_DIFFERENT_TYPE_THRESHOLD = 3  # 3+ different types = device failure

# Impact scoring
IMPACT_SCORE_ANOMALY_WEIGHT = 1.5  # Each anomaly adds 1.5 points
IMPACT_SCORE_DEVICE_MULTIPLIER = 0.2  # Each additional device adds 20%
```

#### Performance

- **Kafka Poll Interval**: 1 second
- **Correlation Latency**: < 100ms (in-memory)
- **Database Insert**: < 500ms
- **Kafka Publish**: < 50ms
- **Memory Usage**: ~150MB (buffer holds max 1000 anomalies)
- **Throughput**: ~100 anomalies/second

---

### 6. LLM Diagnosis Service

**Container**: `smart-noc-llm-diagnosis`  
**Path**: `services/llm-diagnosis/`  
**Language**: Python 3.11  
**Dependencies**: confluent-kafka, openai, sqlalchemy, loguru

#### Responsibility

1. **Consume** incidents from Kafka `incidents` topic
2. **Build context** by fetching related anomalies, historical incidents, device info
3. **Generate diagnosis** using LLM (phi3 via Ollama) with structured prompt
4. **Validate** diagnosis quality (JSON schema, confidence threshold)
5. **Update** PostgreSQL with root cause and remediation plan
6. **Publish** diagnosed incident to Kafka `incidents-diagnosed` topic

#### LLM Integration

##### Model Selection: phi3 (Microsoft)

**Why phi3?**

| Criterion | Evaluation | Score |
|-----------|------------|-------|
| **Cost** | Free (local via Ollama) | ⭐⭐⭐⭐⭐ |
| **Latency** | 120-180s per inference (acceptable for async) | ⭐⭐⭐⭐ |
| **Quality** | Strong reasoning for technical analysis | ⭐⭐⭐⭐ |
| **Privacy** | Fully local, no data sent to external APIs | ⭐⭐⭐⭐⭐ |
| **Deployment** | Runs on Windows host, Docker accessible | ⭐⭐⭐⭐ |
| **Model Size** | 2.3GB (fits in 8GB RAM) | ⭐⭐⭐⭐⭐ |

**Alternatives Considered**:
- ❌ **GPT-4 (OpenAI)**: Too expensive ($0.03/1K tokens), rate limits
- ❌ **GPT-4o-mini (GitHub Models)**: Rate limited (15 RPM), not reliable
- ✅ **phi3 (Ollama)**: Winner - free, reliable, good quality

---

##### Prompt Engineering

**System Prompt** (sets context and constraints):

```python
SYSTEM_PROMPT = """You are an expert network operations engineer with 15+ years of experience in enterprise network troubleshooting and root cause analysis.

Your role is to analyze network incidents and provide:
1. Root cause analysis with high confidence
2. Step-by-step remediation plans
3. Preventive measures to avoid recurrence

Guidelines:
- Be specific and technical (use device names, interfaces, commands)
- Base analysis on provided anomaly data and patterns
- Consider temporal relationships between events
- Factor in device history and similar past incidents
- Provide actionable remediation steps with CLI commands
- Assign realistic confidence scores (0.0-1.0)
- If insufficient data, state assumptions clearly

Output Format: JSON with strict schema (root_cause, confidence, reasoning, remediation_plan, escalation_criteria, preventive_measures, related_incidents)
"""
```

**User Prompt Template** (incident-specific):

```python
USER_PROMPT_TEMPLATE = """
Analyze the following network incident:

INCIDENT SUMMARY:
- Incident Number: {incident_number}
- Incident Type: {incident_type}
- Severity: {severity}
- Primary Device: {primary_device}
- Affected Devices: {affected_devices} ({affected_device_count} total)
- Start Time: {start_time}
- Duration: {duration_minutes} minutes
- Impact Score: {impact_score}/10

ANOMALIES DETECTED:
{anomalies_summary}

Anomaly Type Distribution:
{anomaly_types}

DEVICE HISTORY (last 24 hours):
{device_history}

SIMILAR HISTORICAL INCIDENTS:
{historical_incidents}

TEMPORAL PATTERN:
{temporal_pattern}

TASK:
Provide a comprehensive root cause analysis and remediation plan in JSON format.

Output JSON Schema:
{{
  "root_cause": "string (detailed explanation, 100-300 words)",
  "confidence": float (0.0-1.0),
  "reasoning": [
    {{
      "step_description": "string",
      "analysis": "string",
      "supporting_evidence": ["string"]
    }}
  ],
  "remediation_plan": [
    {{
      "step": int,
      "priority": "IMMEDIATE|HIGH|MEDIUM|LOW",
      "action": "string",
      "command": "string (CLI command if applicable)",
      "expected_outcome": "string",
      "estimated_time_minutes": int
    }}
  ],
  "escalation_criteria": ["string"],
  "preventive_measures": ["string"],
  "related_incidents": ["string"]
}}
"""
```

---

##### Context Builder

**Purpose**: Enrich incident with historical and relational data

```python
class ContextBuilder:
    """
    Builds rich context for LLM diagnosis
    """
    
    def build_context(self, incident: Dict) -> Dict:
        """
        Fetch and structure contextual information
        
        Returns:
        {
            'anomaly_summary': str,
            'anomaly_types_distribution': str,
            'device_history': str,
            'similar_incidents': str,
            'temporal_pattern': str
        }
        """
        incident_id = incident['id']
        
        # 1. Fetch anomalies for this incident
        anomalies = self._fetch_anomalies(incident_id)
        
        # 2. Build anomaly summary
        anomaly_summary = self._build_anomaly_summary(anomalies)
        
        # 3. Analyze anomaly type distribution
        type_distribution = self._analyze_anomaly_types(anomalies)
        
        # 4. Fetch device history (last 24 hours)
        device_history = self._fetch_device_history(
            incident['primary_device'],
            hours=24
        )
        
        # 5. Find similar historical incidents
        similar_incidents = self._find_similar_incidents(
            incident_type=incident['incident_type'],
            device=incident['primary_device'],
            limit=5
        )
        
        # 6. Analyze temporal pattern
        temporal_pattern = self._analyze_temporal_pattern(anomalies)
        
        return {
            'anomaly_summary': anomaly_summary,
            'anomaly_types_distribution': type_distribution,
            'device_history': device_history,
            'similar_incidents': similar_incidents,
            'temporal_pattern': temporal_pattern
        }
    
    def _fetch_anomalies(self, incident_id: str) -> List[Dict]:
        """
        Query database for anomalies associated with incident
        """
        with self.db_engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT a.*
                    FROM anomalies a
                    JOIN incident_anomalies ia ON a.id = ia.anomaly_id
                    WHERE ia.incident_id = CAST(:incident_id AS uuid)
                    ORDER BY a.detection_timestamp ASC
                """),
                {'incident_id': incident_id}
            )
            return [dict(row) for row in result]
    
    def _build_anomaly_summary(self, anomalies: List[Dict]) -> str:
        """
        Create human-readable summary of anomalies
        
        Example output:
        1. [14:30:00] INTERFACE_FLAPPING on core-router-01 (GigabitEthernet0/1)
           - Confidence: 0.95, Severity: HIGH
           - 8 flaps detected over 15 seconds
        
        2. [14:30:12] HIGH_CPU on core-router-01
           - Confidence: 0.75, Severity: HIGH
           - Average CPU: 92%, Max: 98%
        """
        lines = []
        for i, anomaly in enumerate(anomalies, 1):
            timestamp = anomaly['start_time'].strftime('%H:%M:%S')
            anom_type = anomaly['anomaly_type']
            device = anomaly['device']
            confidence = anomaly['confidence']
            severity = anomaly['severity']
            
            lines.append(f"{i}. [{timestamp}] {anom_type} on {device}")
            lines.append(f"   - Confidence: {confidence:.2f}, Severity: {severity}")
            
            # Add type-specific details
            metadata = anomaly.get('metadata', {})
            if anom_type == 'INTERFACE_FLAPPING':
                lines.append(f"   - Interface: {metadata.get('interface')}, Flaps: {metadata.get('flap_count')}")
            elif anom_type == 'HIGH_CPU':
                lines.append(f"   - Avg CPU: {metadata.get('avg_cpu')}%, Max: {metadata.get('max_cpu')}%")
            elif anom_type == 'BGP_INSTABILITY':
                lines.append(f"   - Neighbor: {metadata.get('neighbor')}, Changes: {metadata.get('state_changes')}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _find_similar_incidents(self, incident_type: str, device: str, limit: int) -> str:
        """
        Find historical incidents with same type or device
        """
        with self.db_engine.connect() as conn:
            result = conn.execute(
                text("""
                    SELECT 
                        incident_number,
                        incident_type,
                        severity,
                        root_cause,
                        root_cause_confidence,
                        created_at
                    FROM incidents
                    WHERE 
                        root_cause IS NOT NULL
                        AND (
                            incident_type = :incident_type
                            OR primary_device = :device
                        )
                        AND created_at < NOW() - INTERVAL '1 hour'
                    ORDER BY created_at DESC
                    LIMIT :limit
                """),
                {
                    'incident_type': incident_type,
                    'device': device,
                    'limit': limit
                }
            )
            
            incidents = result.fetchall()
            if not incidents:
                return "No similar incidents found in history."
            
            lines = []
            for incident in incidents:
                lines.append(
                    f"- Incident #{incident[0]} ({incident[1]}): "
                    f"{incident[3][:100]}... (confidence: {incident[4]:.2f})"
                )
            
            return "\n".join(lines)
```

---

##### LLM Client

**Purpose**: Interface with Ollama API using OpenAI-compatible endpoint

```python
class LLMClient:
    """
    Client for generating diagnoses using LLM
    """
    
    def __init__(self):
        self.provider = config.LLM_PROVIDER  # "openai"
        self.model = config.LLM_MODEL  # "phi3"
        self.base_url = config.LLM_BASE_URL  # "http://host.docker.internal:11434/v1"
        
        # Initialize OpenAI client pointing to Ollama
        self.client = OpenAI(
            api_key="ollama",  # Dummy key (Ollama doesn't require auth)
            base_url=self.base_url,
            timeout=180.0  # 3 minutes (phi3 can take 120-180s)
        )
        
        logger.info(f"LLM Client initialized: {self.provider}/{self.model}")
    
    def generate_diagnosis(
        self,
        system_prompt: str,
        user_message: str
    ) -> Tuple[Dict, Dict]:
        """
        Generate diagnosis using LLM
        
        Returns:
            (diagnosis_dict, metadata_dict)
        """
        start_time = time.time()
        
        try:
            logger.debug("Making LLM API call...")
            
            # Call OpenAI-compatible API (points to Ollama)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.3,  # Low temperature for consistent technical analysis
                max_tokens=2000,  # Enough for detailed diagnosis
                response_format={"type": "json_object"}  # Force JSON output
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Extract response
            content = response.choices[0].message.content
            logger.debug(f"Raw LLM response: {content[:200]}...")
            
            # Parse JSON
            diagnosis = json.loads(content)
            logger.debug(f"Parsed diagnosis keys: {list(diagnosis.keys())}")
            
            # Build metadata
            metadata = {
                'total_tokens': response.usage.total_tokens,
                'prompt_tokens': response.usage.prompt_tokens,
                'completion_tokens': response.usage.completion_tokens,
                'duration_ms': duration_ms,
                'model': self.model,
                'provider': self.provider,
                'temperature': 0.3,
                'estimated_cost_usd': 0.0  # Free (Ollama)
            }
            
            logger.info(
                f"LLM diagnosis completed in {duration_ms}ms, "
                f"tokens: {metadata['total_tokens']}"
            )
            
            return (diagnosis, metadata)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise
        except Exception as e:
            logger.error(f"LLM API error: {e}")
            raise
    
    def validate_diagnosis(self, diagnosis: Dict) -> bool:
        """
        Validate diagnosis structure and quality
        
        Required fields:
        - root_cause (string, 50-500 words)
        - confidence (float, 0.0-1.0)
        - reasoning (array of objects)
        - remediation_plan (array of objects)
        """
        # Check required fields
        required_fields = ['root_cause', 'confidence', 'reasoning', 'remediation_plan']
        for field in required_fields:
            if field not in diagnosis:
                logger.warning(f"Missing required field: {field}")
                return False
        
        # Validate root_cause
        root_cause = diagnosis['root_cause']
        if not isinstance(root_cause, str) or len(root_cause) < 50:
            logger.warning(f"Root cause too short: {len(root_cause)} chars")
            return False
        
        # Validate confidence
        confidence = diagnosis['confidence']
        if not isinstance(confidence, (int, float)) or not (0.0 <= confidence <= 1.0):
            logger.warning(f"Invalid confidence: {confidence}")
            return False
        
        # Check minimum confidence threshold
        if confidence < config.DIAGNOSIS_MIN_CONFIDENCE:
            logger.warning(
                f"Confidence {confidence:.2f} below threshold "
                f"{config.DIAGNOSIS_MIN_CONFIDENCE}"
            )
            return False
        
        # Validate remediation_plan
        remediation = diagnosis['remediation_plan']
        if not isinstance(remediation, list) or len(remediation) < 1:
            logger.warning("Remediation plan empty or invalid")
            return False
        
        # Validate remediation steps
        for i, step in enumerate(remediation, 1):
            required_step_fields = ['step', 'priority', 'action']
            for field in required_step_fields:
                if field not in step:
                    logger.warning(f"Remediation step {i} missing field: {field}")
                    return False
        
        logger.debug("Diagnosis validation passed")
        return True
```

---

#### Kafka Consumer Configuration

**Critical Settings** (Fixed after extensive debugging):

```python
consumer_config = {
    'bootstrap.servers': 'kafka:9092',
    'group.id': 'llm-diagnosis-service',
    'auto.offset.reset': 'earliest',
    
    # CRITICAL: Manual commit to enable retry logic
    'enable.auto.commit': False,
    
    # CRITICAL: 10-minute timeout (phi3 takes 120-180s + overhead)
    'max.poll.interval.ms': 600000,  # 10 minutes
    
    'session.timeout.ms': 30000,  # 30 seconds
}
```

**Why These Settings?**

| Setting | Value | Reason |
|---------|-------|--------|
| `enable.auto.commit` | False | Allows manual retry for "too recent" incidents (< 5s old) |
| `max.poll.interval.ms` | 600000 (10 min) | phi3 takes 120-180s, exceeded 5-minute default → MAX_POLL_EXCEEDED errors |
| `auto.offset.reset` | earliest | Ensures no messages lost on consumer restart |

---

#### Manual Commit & Retry Logic

**Problem**: Incidents should wait 5 seconds after creation before diagnosis (to ensure all correlated anomalies are captured).

**Solution**: Manual commit with `seek()` to retry messages.

```python
def _process_incidents_from_kafka(self):
    """
    Poll Kafka, process incident, commit only if ready
    """
    msg = self.consumer.poll(timeout=0.1)  # 100ms poll
    
    if msg is None or msg.error():
        return
    
    incident = json.loads(msg.value().decode('utf-8'))
    
    # Process incident (returns True if ready, False if too recent)
    processed = self._process_incident(incident)
    
    if processed:
        # Commit offset - won't re-process this message
        self.consumer.commit(msg)
        logger.debug(f"Committed offset {msg.offset()}")
    else:
        # Don't commit - seek back to retry same message
        logger.debug(f"Skipped commit, seeking back to retry")
        tp = TopicPartition(msg.topic(), msg.partition(), msg.offset())
        self.consumer.seek(tp)  # CRITICAL: Rewind to same offset

def _process_incident(self, incident: Dict) -> bool:
    """
    Process incident, return True if should commit, False if should retry
    """
    incident_id = incident['id']
    
    # Check if already diagnosed (query database, NOT Kafka message)
    if self._is_already_diagnosed(incident_id):
        logger.debug(f"Already diagnosed, skipping")
        return True  # Commit offset
    
    # Check if too recent (< 5 seconds old)
    age_seconds = self._calculate_age(incident['created_at'])
    if age_seconds < config.DIAGNOSIS_DELAY_SECONDS:  # 5 seconds
        logger.debug(f"Too recent ({age_seconds}s), will retry")
        return False  # DON'T commit offset - retry on next poll
    
    # Ready for diagnosis
    self._diagnose_incident(incident)
    return True  # Commit offset after success

def _is_already_diagnosed(self, incident_id: str) -> bool:
    """
    CRITICAL: Check database, not Kafka message
    
    Kafka messages are immutable snapshots - even after updating the database,
    the Kafka message won't have the updated root_cause field.
    Must query PostgreSQL directly.
    """
    with self.engine.connect() as conn:
        result = conn.execute(
            text("SELECT root_cause FROM incidents WHERE id = :incident_id"),
            {"incident_id": incident_id}
        ).fetchone()
        return result is not None and result[0] is not None
```

**Key Insights**:

1. **seek() is critical**: Without it, `poll()` won't return the same message again (it's already consumed from internal buffer)
2. **Database check is critical**: Kafka messages are immutable, so checking `incident.get('root_cause')` always returns None even after DB update → infinite re-diagnosis loop
3. **Return value controls commit**: False = retry, True = commit and move on

---

#### Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| **Diagnosis Latency** | 120-180s | phi3 inference time |
| **Kafka Poll Rate** | 10 Hz (100ms) | Fast retries for "too recent" incidents |
| **Database Query** | < 100ms | Already-diagnosed check |
| **Database Update** | < 500ms | Two INSERTs (incidents + history) |
| **Kafka Publish** | < 50ms | Compressed, async |
| **Memory Usage** | ~300MB | Includes LLM client overhead |
| **Throughput** | ~0.5 incidents/min | Limited by LLM inference time |
| **Concurrent Diagnosis** | 1 | Sequential processing (could scale with multi-threading) |

---

## Algorithms & Machine Learning

### Anomaly Detection Algorithms

#### 1. Threshold-Based Detection

**Algorithm**: Statistical threshold with confidence scoring

**Pseudocode**:
```
FUNCTION detect_anomaly(metric_values, threshold, time_window):
    samples = fetch_recent_samples(time_window)
    
    IF COUNT(samples) < MIN_SAMPLES:
        RETURN None  // Insufficient data
    
    avg_value = AVERAGE(samples)
    max_value = MAX(samples)
    
    IF avg_value >= threshold:
        // Calculate confidence based on how far above threshold
        confidence = MIN(1.0, (avg_value - threshold) / (max_value - threshold))
        
        // Determine severity
        IF avg_value > threshold * 1.2:
            severity = "CRITICAL"
        ELSE IF avg_value > threshold * 1.1:
            severity = "HIGH"
        ELSE:
            severity = "MEDIUM"
        
        RETURN Anomaly(type, device, confidence, severity, metadata)
    
    RETURN None
END FUNCTION
```

**Advantages**:
- Simple, explainable
- No training required
- Low computational cost
- Real-time capable

**Limitations**:
- Requires manual threshold tuning
- No adaptation to baseline
- False positives during legitimate spikes

---

#### 2. Time-Series Analysis (Future)

**Algorithm**: ARIMA or Prophet for baseline + anomaly detection

**Approach**:
1. Build baseline model from historical data
2. Detect deviations from predicted values
3. Score confidence based on standard deviations

**Status**: Planned for v2.0

---

### Correlation Algorithms

#### 1. Time-Based Correlation

**Algorithm**: Sliding window with device grouping

**Complexity**: O(n) where n = buffer size

**Pseudocode**:
```
CLASS TimeBasedCorrelator:
    anomaly_buffer = []
    time_window_seconds = 60
    
    FUNCTION add_anomaly(anomaly):
        anomaly_buffer.APPEND(anomaly)
        
        // Remove old anomalies
        current_time = NOW()
        anomaly_buffer = FILTER(
            anomaly_buffer,
            WHERE (current_time - anomaly.timestamp) <= time_window_seconds
        )
        
        // Group by device
        device_groups = GROUP_BY(anomaly_buffer, 'device')
        
        // Check correlation criteria
        FOR device, anomalies IN device_groups:
            IF should_create_incident(anomalies):
                incident = create_incident(anomalies)
                remove_anomalies(anomalies)  // CRITICAL: Prevent duplicate incidents
                RETURN incident
        
        RETURN None
    
    FUNCTION should_create_incident(anomalies):
        // Criteria: 2+ same type OR 3+ different types OR 1 CRITICAL
        
        IF ANY(anomaly.severity == "CRITICAL" FOR anomaly IN anomalies):
            RETURN True
        
        type_counts = COUNT_BY_TYPE(anomalies)
        
        IF ANY(count >= 2 FOR count IN type_counts.VALUES()):
            RETURN True  // 2+ of same type
        
        IF LENGTH(type_counts) >= 3:
            RETURN True  // 3+ different types = device failure
        
        RETURN False
END CLASS
```

**Advantages**:
- Simple, predictable behavior
- Fast (in-memory)
- Works well for device-centric issues

**Limitations**:
- Misses distributed issues (multiple devices)
- No topology awareness
- Fixed time window (not adaptive)

---

#### 2. Pattern-Based Correlation (Planned)

**Algorithm**: Graph-based + ML clustering

**Approach**:
1. **Topology Graph**: Build network topology (devices, links)
2. **Feature Extraction**: Extract features from anomalies (device, type, severity, time)
3. **DBSCAN Clustering**: Cluster anomalies by spatial-temporal proximity
4. **Graph Traversal**: Detect impact propagation paths
5. **Incident Classification**: Classify by pattern (device failure vs network-wide)

**Status**: Planned for v2.0

---

### Machine Learning Components

#### Currently Implemented

**Isolation Forest** for unsupervised anomaly detection:

**Implementation Details**:
- **Algorithm**: Isolation Forest (scikit-learn)
- **Features**: 12-dimensional feature vector extracted from logs
  - Severity level (0-3: INFO, WARNING, ERROR, CRITICAL)
  - Event type hash (bounded 0-999)
  - Device criticality (0-2: low, medium, high)
  - Device role (0-2: edge, distribution, core)
  - Hour of day (0-23)
  - Day of week (0-6)
  - Message length
  - Has error keywords (binary)
  - Has interface data (binary)
  - Has CPU data (binary)
  - Has BGP data (binary)
  - Has auth data (binary)

**Training Strategy**:
- **Unsupervised**: No labeled data required
- **Initial Training**: After collecting 50 samples (configurable)
- **Retraining**: Every 60 minutes with recent samples
- **Feature Scaling**: StandardScaler for normalization
- **Contamination**: 0.1 (expects 10% anomalies)
- **Estimators**: 100 trees in the forest

**Detection Process**:
```python
# 1. Extract features from log entry
features = extract_features(log)

# 2. Scale features using fitted StandardScaler
X_scaled = scaler.transform(features)

# 3. Predict using Isolation Forest
prediction = model.predict(X_scaled)  # -1 = anomaly, 1 = normal

# 4. Get anomaly score (lower = more anomalous)
anomaly_score = model.score_samples(X_scaled)

# 5. Convert to confidence (0-1 range)
confidence = max(0, min(1, abs(anomaly_score) * 2))

# 6. Create ML_DETECTED_ANOMALY if prediction == -1
```

**Anomaly Type**: `ML_DETECTED_ANOMALY`
- **Severity**: MEDIUM (confidence > 0.7) or LOW
- **Cooldown**: 30 seconds per device (prevents spam)
- **Confidence Range**: 0.5-1.0 (higher = more anomalous)

**Advantages**:
- Detects unknown/novel anomaly patterns
- No manual threshold tuning needed
- Learns baseline behavior automatically
- Complements rule-based detection

**Limitations**:
- Requires 50+ samples before first training
- May have false positives during initial learning
- Black box (less explainable than rules)
- CPU intensive (100 trees per prediction)

**Current Performance**:
- Training Time: ~500ms (50-1000 samples)
- Prediction Time: ~50ms per log
- Memory: ~50MB model size
- Retraining: Every 60 minutes

---

#### Rule-Based Detection (Primary)

The system **also** uses explicit threshold-based detection for 5 known anomaly types, which provides:
- Immediate detection (no training needed)
- High explainability
- Domain-specific accuracy

**Rationale for Dual Approach**:
- **Rule-Based**: Fast, explainable, catches known patterns
- **ML-Based**: Catches novel/unknown patterns, adaptive
- **Together**: Comprehensive coverage

---

#### Planned Enhancements (v2.0)

1. **Anomaly Detection**: LSTM or Transformer for time-series prediction
   - Training data: Historical device metrics
   - Model: Predict next value, flag deviations
   - Benefit: Better temporal pattern recognition than Isolation Forest

2. **Correlation**: DBSCAN or HDBSCAN for spatial-temporal clustering
   - Training data: Historical anomalies + topology
   - Model: Learn patterns of co-occurring anomalies
   - Benefit: Detect distributed incidents

3. **Diagnosis Refinement**: Fine-tuned LLM on incident history
   - Training data: Historical incidents + engineer feedback
   - Model: phi3 fine-tuned on domain-specific data
   - Benefit: Higher quality diagnoses, domain vocabulary

4. **Feedback Loop**: Incorporate engineer corrections into ML models
   - Update Isolation Forest contamination parameter
   - Retrain with labeled false positives/negatives
   - Improve overall detection accuracy

---

## LLM Integration

### Model Architecture

**Model**: phi3 (Microsoft)  
**Size**: 2.3 GB  
**Parameters**: 3.8 billion  
**Context Length**: 128K tokens  
**Provider**: Ollama (local inference)

#### Why phi3?

phi3 is a Small Language Model (SLM) optimized for:
- **Technical reasoning**: Strong performance on STEM tasks
- **Efficient inference**: Runs on CPU (no GPU required)
- **Structured output**: Good at following JSON schemas
- **Privacy**: Fully local, no external API calls
- **Cost**: Free (no per-token charges)

**Benchmark Performance**:
- MMLU (reasoning): 68.1% (competitive with larger models)
- HumanEval (code): 58.5%
- TruthfulQA: 65.3%

**Comparison to Alternatives**:

| Model | Params | Latency | Quality | Cost | Privacy |
|-------|--------|---------|---------|------|---------|
| **phi3** | 3.8B | 120-180s | ⭐⭐⭐⭐ | Free | ✅ Local |
| GPT-4 | 1.7T | 5-10s | ⭐⭐⭐⭐⭐ | $0.03/1K | ❌ OpenAI |
| GPT-4o-mini | ~100B | 2-5s | ⭐⭐⭐⭐ | $0.15/1M | ❌ OpenAI |
| llama3.2 | 3B | 100-150s | ⭐⭐⭐ | Free | ✅ Local |

---

### Prompt Engineering

#### System Prompt Design

**Purpose**: Set role, constraints, and output format

**Key Elements**:
1. **Role Definition**: "Expert network operations engineer with 15+ years..."
2. **Task Specification**: "Analyze incidents, provide root cause + remediation"
3. **Guidelines**: Technical specificity, CLI commands, confidence scoring
4. **Output Format**: Strict JSON schema

**Why JSON Output?**
- Structured, parseable data
- Type safety (confidence is float, not string)
- Easy validation
- Integrates with database schema

---

#### User Prompt Design

**Purpose**: Provide incident-specific context

**Structure**:
1. **Incident Summary**: Numbers, devices, severity, timing
2. **Anomalies**: Detailed list with timestamps, types, metadata
3. **Device History**: Past issues on same device (24-hour window)
4. **Similar Incidents**: Historical patterns with same type/device
5. **Temporal Pattern**: Time-series analysis of anomaly sequence

**Context Size**: ~1200 tokens (well within phi3's 128K limit)

---

#### Temperature & Sampling

**Temperature**: 0.3 (low)

**Rationale**:
- Low temperature → deterministic, consistent output
- Technical analysis requires precision, not creativity
- Reduces hallucination risk

**Max Tokens**: 2000

**Rationale**:
- Enough for detailed root cause (200-300 words)
- Plus remediation plan (5-10 steps)
- Plus reasoning chain (3-5 steps)

---

### Output Validation

**Schema Validation**:
```json
{
  "root_cause": str,  # 50-500 words
  "confidence": float,  # 0.0-1.0
  "reasoning": [
    {
      "step_description": str,
      "analysis": str,
      "supporting_evidence": [str]
    }
  ],
  "remediation_plan": [
    {
      "step": int,
      "priority": enum["IMMEDIATE", "HIGH", "MEDIUM", "LOW"],
      "action": str,
      "command": str,
      "expected_outcome": str,
      "estimated_time_minutes": int
    }
  ],
  "escalation_criteria": [str],
  "preventive_measures": [str],
  "related_incidents": [str]
}
```

**Quality Checks**:
1. All required fields present
2. Root cause length >= 50 words (ensures detail)
3. Confidence within 0.0-1.0 range
4. Confidence >= 0.5 (minimum threshold)
5. Remediation plan has >= 1 step
6. Each remediation step has required fields

---

### Error Handling

**Retry Strategy**: No automatic retries (manual commit handles this)

**Failure Modes**:
1. **Timeout** (> 180s): Log error, commit offset, move on
2. **JSON Parse Error**: Log raw response, commit offset, move on
3. **Validation Error**: Log issues, commit offset, move on
4. **Kafka Error**: Seek back, retry on next poll

**Philosophy**: Fail fast, commit offset, don't block pipeline on single incident

---

## Database Architecture

### Schema Overview

**Database**: PostgreSQL 16  
**Total Tables**: 5  
**Total Indexes**: 12

#### Table: `incidents`

**Purpose**: Store active and historical incidents

```sql
CREATE TABLE incidents (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_number SERIAL UNIQUE NOT NULL,
    
    -- Classification
    incident_type VARCHAR(50) NOT NULL,  -- DEVICE_FAILURE, NETWORK_PERFORMANCE, etc.
    status VARCHAR(20) DEFAULT 'ACTIVE',  -- ACTIVE, RESOLVED, ACKNOWLEDGED
    severity VARCHAR(20) NOT NULL,  -- CRITICAL, HIGH, MEDIUM, LOW
    
    -- Affected Resources
    primary_device VARCHAR(255) NOT NULL,
    affected_devices TEXT[] NOT NULL,  -- PostgreSQL array
    affected_device_count INT DEFAULT 1,
    
    -- Anomaly Relationship
    anomaly_count INT DEFAULT 0,
    primary_anomaly_type VARCHAR(50),
    
    -- Correlation
    correlation_method VARCHAR(50),  -- TIME_BASED, PATTERN_BASED
    impact_score DECIMAL(4,2) DEFAULT 0.0,  -- 0.00-10.00
    
    -- Timing
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration_seconds INT,
    
    -- Diagnosis (filled by LLM service)
    root_cause TEXT,
    root_cause_confidence DECIMAL(4,2) NOT NULL,  -- 0.00-1.00
    remediation_plan TEXT,  -- JSON stored as TEXT
    diagnosis_timestamp TIMESTAMP,
    llm_model VARCHAR(50),
    diagnosis_metadata JSONB,  -- Tokens, cost, duration
    
    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    correlation_metadata JSONB,
    
    -- Indexes
    INDEX idx_incidents_created (created_at DESC),
    INDEX idx_incidents_device (primary_device),
    INDEX idx_incidents_type (incident_type),
    INDEX idx_incidents_severity (severity),
    INDEX idx_incidents_status (status),
    INDEX idx_incidents_diagnosis (diagnosis_timestamp)
);
```

**Row Count**: ~100-1000 per day (depends on anomaly rate)  
**Storage**: ~500 bytes per row  
**Retention**: Indefinite (for historical analysis)

---

#### Table: `anomalies`

**Purpose**: Store individual anomaly detections

```sql
CREATE TABLE anomalies (
    -- Identity
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    anomaly_type VARCHAR(50) NOT NULL,
    
    -- Device
    device VARCHAR(255) NOT NULL,
    
    -- Detection
    severity VARCHAR(20) NOT NULL,
    confidence DECIMAL(4,2) NOT NULL,  -- 0.00-1.00
    
    -- Timing
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration_seconds INT,
    
    -- Context
    event_count INT DEFAULT 1,
    metadata JSONB,  -- Type-specific data (interface, CPU%, etc.)
    raw_events JSONB,  -- Sample log events
    
    -- Detection Metadata
    detection_timestamp TIMESTAMP DEFAULT NOW(),
    detector_version VARCHAR(20),
    
    -- Indexes
    INDEX idx_anomalies_detection_time (detection_timestamp DESC),
    INDEX idx_anomalies_device (device),
    INDEX idx_anomalies_type (anomaly_type),
    INDEX idx_anomalies_device_type (device, anomaly_type)
);
```

**Row Count**: ~1000-10000 per day  
**Storage**: ~300 bytes per row (+ JSONB overhead)  
**Retention**: 30 days (purge old anomalies)

---

#### Table: `incident_anomalies`

**Purpose**: Many-to-many relationship between incidents and anomalies

```sql
CREATE TABLE incident_anomalies (
    incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    anomaly_id UUID NOT NULL REFERENCES anomalies(id) ON DELETE CASCADE,
    
    PRIMARY KEY (incident_id, anomaly_id),
    
    INDEX idx_incident_anomalies_incident (incident_id),
    INDEX idx_incident_anomalies_anomaly (anomaly_id)
);
```

**Row Count**: ~3-5x incidents (avg 3-5 anomalies per incident)

---

#### Table: `incident_diagnosis_history`

**Purpose**: Version history of diagnoses (for audit and re-diagnosis)

```sql
CREATE TABLE incident_diagnosis_history (
    id SERIAL PRIMARY KEY,
    incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    diagnosis_version INT NOT NULL,
    
    -- Diagnosis
    root_cause TEXT NOT NULL,
    root_cause_confidence DECIMAL(4,2) NOT NULL,
    remediation_plan JSONB NOT NULL,
    
    -- LLM Metadata
    llm_model VARCHAR(50) NOT NULL,
    tokens_used INT,
    diagnosis_duration_ms INT,
    diagnosis_metadata JSONB,
    
    -- Timing
    diagnosed_at TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_diagnosis_history_incident (incident_id),
    INDEX idx_diagnosis_history_time (diagnosed_at DESC)
);
```

**Purpose**: 
- Track diagnosis improvements over time
- A/B test different LLM models
- Audit trail for compliance

---

### Query Patterns

#### Common Queries

```sql
-- 1. Get recent incidents with diagnosis status
SELECT 
    incident_number,
    incident_type,
    severity,
    primary_device,
    CASE WHEN root_cause IS NOT NULL THEN 'DIAGNOSED' ELSE 'PENDING' END as diagnosis_status,
    root_cause_confidence,
    created_at
FROM incidents
WHERE created_at > NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;

-- 2. Get incident with all anomalies
SELECT 
    i.*,
    json_agg(a.*) as anomalies
FROM incidents i
JOIN incident_anomalies ia ON i.id = ia.incident_id
JOIN anomalies a ON ia.anomaly_id = a.id
WHERE i.id = :incident_id
GROUP BY i.id;

-- 3. Top devices by incident count
SELECT 
    primary_device,
    COUNT(*) as incident_count,
    AVG(impact_score) as avg_impact,
    MAX(created_at) as last_incident
FROM incidents
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY primary_device
ORDER BY incident_count DESC
LIMIT 10;

-- 4. Diagnosis performance metrics
SELECT 
    llm_model,
    COUNT(*) as diagnosis_count,
    AVG(root_cause_confidence) as avg_confidence,
    AVG(diagnosis_duration_ms) / 1000.0 as avg_duration_seconds,
    AVG(tokens_used) as avg_tokens
FROM incident_diagnosis_history
WHERE diagnosed_at > NOW() - INTERVAL '7 days'
GROUP BY llm_model;
```

---

### Performance Optimization

**Indexes**:
- Time-based queries: `created_at DESC`, `detection_timestamp DESC`
- Device lookups: `device`, `primary_device`
- Type filtering: `incident_type`, `anomaly_type`
- Composite: `(device, anomaly_type)` for join optimization

**Partitioning** (Planned):
- Partition incidents by month (time-series)
- Partition anomalies by day (high volume)

**Vacuum & Analyze**:
- Auto-vacuum enabled
- Daily ANALYZE for query planner

---

## Technology Stack

### Core Services

| Component | Technology | Version | License | Purpose |
|-----------|------------|---------|---------|---------|
| **Log Ingestion** | Logstash | 8.12.0 | Elastic 2.0 | Parse & forward logs |
| **Log Storage** | Elasticsearch | 8.12.0 | Elastic 2.0 | Time-series log storage |
| **Message Broker** | Apache Kafka | 3.7.0 | Apache 2.0 | Event streaming |
| **Database** | PostgreSQL | 16 | PostgreSQL | Persistent storage |
| **Cache** | Redis | 7 | BSD | Session cache (future) |
| **LLM Provider** | Ollama | 0.21.2 | MIT | Local LLM inference |
| **LLM Model** | phi3 | latest | MIT | AI diagnosis |

### Python Services

| Service | Python | Key Dependencies |
|---------|--------|------------------|
| Anomaly Detector | 3.11 | elasticsearch (8.12.0), scikit-learn (1.3.0), numpy, pandas, loguru (0.7.2) |
| Correlation Engine | 3.11 | confluent-kafka (2.3.0), psycopg2 (2.9.9) |
| LLM Diagnosis | 3.11 | openai (1.12.0), sqlalchemy (2.0.27) |

### Monitoring & UI

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Grafana** | 10.3.3 | Dashboards & visualization |
| **Kafka UI** | latest | Kafka management web UI |

### Development Tools

| Tool | Purpose |
|------|---------|
| **Docker Compose** | Orchestration |
| **Bash Scripts** | Deployment automation |
| **Python venv** | Dependency isolation |

---

## Deployment Architecture

### Containerization

**Platform**: Docker 24.0+  
**Orchestrator**: Docker Compose  
**Total Containers**: 10

#### Resource Requirements

| Container | CPU | Memory | Disk | Notes |
|-----------|-----|--------|------|-------|
| Elasticsearch | 2 cores | 2GB | 10GB | Heap: 1GB |
| Kafka | 1 core | 1GB | 5GB | KRaft mode |
| Logstash | 1 core | 1GB | 1GB | Heap: 1GB |
| PostgreSQL | 1 core | 512MB | 5GB | Shared buffers: 128MB |
| Anomaly Detector | 0.5 core | 256MB | 100MB | Python |
| Correlation Engine | 0.5 core | 256MB | 100MB | Python |
| LLM Diagnosis | 0.5 core | 512MB | 100MB | Python |
| Grafana | 0.5 core | 256MB | 1GB | Visualization |
| Kafka UI | 0.5 core | 256MB | 100MB | Management |
| Redis | 0.5 core | 128MB | 1GB | Cache |
| **TOTAL** | **8 cores** | **6.5GB** | **23GB** | Minimum |

**Recommended**: 16GB RAM, 50GB disk for development

---

### Network Architecture

**Docker Network**: `smart-noc-network` (bridge)

**Port Mappings**:
- 3000 → Grafana (dashboards)
- 5000 → Logstash (log ingestion)
- 5432 → PostgreSQL (database)
- 6379 → Redis (cache)
- 8080 → Kafka UI (management)
- 9092 → Kafka (broker)
- 9200 → Elasticsearch (HTTP API)
- 9600 → Logstash (monitoring)

**Service Discovery**: Docker DNS (service names as hostnames)

---

### Deployment Scripts

#### Setup Script: `setup-noc.sh`

**Purpose**: Zero-touch deployment for team members

**Steps**:
1. Validate prerequisites (Docker, WSL, disk space)
2. Create Python virtual environment
3. Install Python dependencies
4. Start Docker Compose services
5. Wait for health checks (Kafka, Elasticsearch, PostgreSQL)
6. Initialize database schema
7. Create Kafka topics
8. Validate service connectivity
9. Display access URLs

**Duration**: 5-10 minutes (first run), 2-3 minutes (subsequent)

#### Teardown Script: `teardown-noc.sh`

**Purpose**: Complete cleanup of all resources

**Steps**:
1. Stop services gracefully (apps → monitoring → pipeline → infrastructure)
2. Remove containers
3. Remove volumes (optional, --keep-data flag)
4. Remove networks
5. Remove Docker images (optional, --keep-images flag)
6. Remove Python venv (optional, prompt)
7. Validate cleanup (no hanging containers/volumes)

**Features**:
- Optional database backup before deletion
- Forced removal of lingering containers
- Comprehensive validation

---

## Performance Characteristics

### Throughput

| Stage | Throughput | Bottleneck |
|-------|------------|------------|
| **Log Ingestion** | 1000 events/sec | Logstash parsing |
| **Elasticsearch Indexing** | 5000 docs/sec | Disk I/O |
| **Anomaly Detection** | 100 anomalies/sec | Elasticsearch queries |
| **Correlation** | 100 anomalies/sec | In-memory processing |
| **LLM Diagnosis** | 0.5 incidents/min | phi3 inference time |

**System Bottleneck**: LLM diagnosis (120-180s per incident)

**Scaling Strategy**:
- Horizontal: Run multiple LLM diagnosis instances
- Vertical: Use GPU for faster inference
- Alternative: Use faster model (llama3.2 ~100s)

---

### Latency

| Path | P50 | P95 | P99 |
|------|-----|-----|-----|
| **Log → Elasticsearch** | 1s | 3s | 5s |
| **Anomaly Detection** | 30s | 60s | 90s |
| **Correlation** | 10s | 60s | 120s |
| **LLM Diagnosis** | 150s | 180s | 240s |
| **End-to-End** | 5min | 8min | 12min |

**End-to-End**: Log generation → Diagnosed incident in database

---

### Resource Usage

**Steady State** (no active diagnosis):
- CPU: ~10% total (mostly Elasticsearch)
- Memory: ~4GB total
- Disk I/O: ~10 MB/s (log writes)
- Network: ~1 Mbps (Kafka internal)

**Active Diagnosis** (1 concurrent):
- CPU: ~30% total (+20% for phi3)
- Memory: ~4.5GB total (+500MB for LLM)
- Disk I/O: ~50 MB/s (Elasticsearch reads)
- Network: ~5 Mbps (Kafka + Ollama)

---

### Scalability

**Current Limits**:
- **Single-node**: All services on one machine
- **Sequential diagnosis**: 1 incident at a time
- **No persistence**: Correlation buffer in-memory only

**Scaling Paths**:
1. **Horizontal**: Deploy multiple diagnosis workers (Kafka consumer group)
2. **Distributed**: Run services on separate machines
3. **Kubernetes**: Use K8s for auto-scaling and HA
4. **GPU**: Add GPU node for faster LLM inference
5. **Caching**: Use Redis for context caching

---

## Appendix

### Configuration Files

All configuration is managed via:
- `docker-compose.yml`: Container definitions
- `services/*/config.py` or `config.yaml`: Service-specific settings
- Environment variables (optional overrides)

### Monitoring & Observability

**Current**:
- Service logs (stdout, captured by Docker)
- Kafka UI (topic/consumer monitoring)
- Grafana (log dashboards)

**Planned**:
- Prometheus metrics export
- Distributed tracing (OpenTelemetry)
- Alerting rules (PagerDuty integration)

### Security Considerations

**Current State** (Development):
- No authentication on services
- Default passwords (postgres, elasticsearch)
- No TLS/SSL
- Services exposed to host network

**Production Hardening** (Planned):
- Enable authentication (SASL for Kafka, x-pack for Elasticsearch)
- Rotate default passwords
- Enable TLS for all inter-service communication
- Network segmentation (private subnets)
- Rate limiting on log ingestion
- Audit logging for database access

### Known Limitations

1. **Single-threaded diagnosis**: Can only process 1 incident at a time
2. **In-memory correlation**: Lost if service restarts
3. **No topology awareness**: Correlation doesn't use network topology
4. **Manual thresholds**: Anomaly detection requires manual tuning
5. **No feedback loop**: LLM doesn't learn from engineer corrections
6. **Limited history**: Elasticsearch only keeps 7 days of logs

### Future Roadmap

**v2.0 (Q3 2026)**:
- Pattern-based correlation with topology awareness
- ML-based anomaly detection (LSTM baseline)
- Multi-threaded LLM diagnosis
- Feedback mechanism for diagnosis quality
- Alert notification system (email, Slack)

**v3.0 (Q1 2027)**:
- Auto-remediation via Ansible playbooks
- Kubernetes deployment
- Fine-tuned LLM on incident history
- Predictive incident detection
- Integration with CMDB/ITSM systems

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-30 | Smart NOC Team | Initial comprehensive documentation |

---

**END OF ARCHITECTURE DOCUMENTATION**

---

## Version History

### Version 2.0 (May 7, 2026) - Option A: Enriched Pipeline Flow

**Major Architecture Change**: Transitioned from parallel processing to pipeline flow with centralized enrichment.

#### Changes:

1. **New Kafka Topic**: `network-logs-enriched`
   - Created new topic for enriched logs from Logstash
   - 3 partitions, 1-day retention, gzip compression

2. **Logstash Enhancement**:
   - Added Kafka output to publish enriched logs
   - Now serves as central enrichment layer
   - Adds: device_role, criticality, link_state, fingerprint, tags

3. **Anomaly Detector Upgrade**:
   - Changed input from `network-logs` to `network-logs-enriched`
   - Implemented criticality-aware thresholds
   - High criticality: 2 events (most sensitive)
   - Medium criticality: 3 events
   - Low criticality: 4 events

4. **Enriched Anomaly Output**:
   - Anomalies now include device_role and criticality fields
   - Better context for incident correlation and prioritization

#### Benefits:
- ? Single source of truth for enrichment logic
- ? Context-aware anomaly detection
- ? Better incident prioritization
- ? Improved observability and filtering
- ? Minimal latency impact (~50-100ms)

#### Rollback:
Change `config.yaml`: `input_topic: 'network-logs'` and restart anomaly-detector

---

### Version 1.0 (April 30, 2026) - Initial Release

**Initial Architecture**: Parallel processing with independent Logstash and Anomaly Detector consumers.

- Logstash ? Elasticsearch (storage)
- Anomaly Detector ? Kafka (real-time detection)
- Both consuming from `network-logs` topic independently

---
