# Correlation Engine Service

**Service Name:** `smart-noc-correlation-engine`  
**Image:** `smart-noc_correlation-engine` (custom)  
**Technology:** Python 3.9  
**Status:** Core Service  
**Uptime Target:** 99.5%

---

## Overview

The Correlation Engine is the **intelligence layer** that transforms individual anomalies into actionable incidents. It groups related anomalies using temporal and spatial correlation algorithms, determines incident severity, and triggers the LLM diagnosis workflow.

**Key Capabilities:**
- **Multi-Anomaly Correlation:** Groups related anomalies by device, time window, and pattern
- **Incident Creation:** Creates structured incidents for AI diagnosis
- **Severity Calculation:** Determines incident priority based on impact
- **Deduplication:** Prevents duplicate incidents for same root cause

---

## Service Configuration

### Resources
- **Memory:** 512MB-1GB
- **CPU:** 1 core
- **Storage:** Minimal (state tracking only)

### Environment Variables
```
KAFKA_BOOTSTRAP_SERVERS: kafka:9092
KAFKA_GROUP_ID: correlation-engine-group
POSTGRES_HOST: postgres
POSTGRES_PORT: 5432
POSTGRES_DB: smart_noc
POSTGRES_USER: noc_admin
POSTGRES_PASSWORD: noc_password
CORRELATION_WINDOW: 300  # 5 minutes
MIN_ANOMALIES: 2         # Minimum anomalies to create incident
LOG_LEVEL: INFO
```

---

## Architecture Components

### 1. **Kafka Consumer**

**Input Topic:** `anomalies`  
**Consumer Group:** `correlation-engine-group`  
**Processing Mode:** Real-time streaming

**Input Message Format:**
```json
{
  "anomaly_id": "anom-20240613-001",
  "anomaly_type": "INTERFACE_FLAPPING",
  "device_id": "10.139.38.188",
  "interface": "1:55",
  "severity": "HIGH",
  "confidence": 0.95,
  "event_count": 4,
  "first_seen": "2026-06-13T22:50:00Z",
  "last_seen": "2026-06-13T22:51:30Z",
  "device_vendor": "Extreme Networks",
  "device_family": "EXOS",
  "device_cli_syntax": "EXOS",
  "source_logs": [...]
}
```

---

### 2. **Correlation Algorithms**

#### **Algorithm 1: Temporal-Spatial Correlation**

**Purpose:** Group anomalies that occur on the same device within a time window

**Logic:**
```python
IF anomalies share same device_id
   AND occurred within CORRELATION_WINDOW (5 minutes)
   AND anomaly_count >= MIN_ANOMALIES (2):
    THEN create incident
```

**Example:**
```
22:50:00 | Device 10.139.38.188 | Port 1:55 FLAPPING
22:51:00 | Device 10.139.38.188 | Port 2:22 FLAPPING
         ↓
    INCIDENT CREATED: Multiple interface issues on same device
```

**State Tracking:**
- **Pending Anomalies:** Per-device buffer of recent anomalies
- **Window Management:** Sliding 5-minute window
- **Cleanup:** Expired anomalies removed from buffer

---

#### **Algorithm 2: Pattern-Based Correlation**

**Purpose:** Group anomalies by similar patterns (e.g., multiple flapping interfaces)

**Patterns Detected:**
1. **Multi-Interface Flapping:** 2+ interfaces flapping on same device
2. **BGP + Interface Down:** BGP session loss correlated with interface down
3. **Authentication Spike:** Multiple auth failures across devices
4. **Cascading Failures:** Downstream devices failing after upstream

**Example:**
```
Pattern: MULTI_INTERFACE_FLAPPING
├─ Port 1:55 flapping (4 events)
├─ Port 2:22 flapping (3 events)
└─ Device: 10.139.38.188 (EXOS core switch)
    ↓
Incident Type: CONNECTIVITY_ISSUE
Severity: HIGH
```

---

#### **Algorithm 3: Device Role Weighting**

**Purpose:** Prioritize incidents based on device criticality

**Role Weights:**
- **Core:** Weight = 3 (highest priority)
- **Distribution:** Weight = 2
- **Access:** Weight = 1
- **Unknown:** Weight = 1

**Severity Calculation:**
```python
base_severity = max(anomaly.severity for anomaly in group)
role_weight = device_role_weights.get(device_role, 1)

final_severity = min(base_severity * role_weight, "CRITICAL")
```

**Example:**
```
Anomaly Severity: MEDIUM
Device Role: core (weight=3)
Final Incident Severity: HIGH
```

---

### 3. **Incident Creation**

**Trigger Conditions:**
1. **Multiple Anomalies:** 2+ correlated anomalies within window
2. **High Severity:** Single CRITICAL anomaly (immediate incident)
3. **Pattern Match:** Recognized failure pattern detected

**Incident Generation:**
```python
def create_incident(correlated_anomalies):
    incident = {
        "incident_number": generate_incident_number(),  # e.g., INC-20024
        "incident_type": determine_type(anomalies),     # CONNECTIVITY_ISSUE
        "device_id": anomalies[0]["device_id"],
        "severity": calculate_severity(anomalies),
        "status": "PENDING_DIAGNOSIS",
        "anomaly_count": len(anomalies),
        "first_anomaly_time": min(a["first_seen"] for a in anomalies),
        "last_anomaly_time": max(a["last_seen"] for a in anomalies),
        "created_at": datetime.now(),
        "device_vendor": anomalies[0].get("device_vendor"),
        "device_cli_syntax": anomalies[0].get("device_cli_syntax")
    }
    return incident
```

---

### 4. **PostgreSQL Integration**

#### **Table 1: incidents**

**Schema:**
```sql
CREATE TABLE incidents (
    incident_number SERIAL PRIMARY KEY,
    incident_type VARCHAR(100),
    device_id VARCHAR(100),
    severity VARCHAR(20),
    status VARCHAR(50),
    anomaly_count INTEGER,
    first_anomaly_time TIMESTAMP,
    last_anomaly_time TIMESTAMP,
    root_cause TEXT,
    remediation_plan TEXT,
    confidence_score FLOAT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Insert Example:**
```sql
INSERT INTO incidents (incident_number, incident_type, device_id, severity, status, anomaly_count)
VALUES (20024, 'CONNECTIVITY_ISSUE', '10.139.38.188', 'HIGH', 'PENDING_DIAGNOSIS', 2)
RETURNING incident_number;
```

---

#### **Table 2: incident_anomalies**

**Purpose:** Link anomalies to incidents (many-to-one relationship)

**Schema:**
```sql
CREATE TABLE incident_anomalies (
    id SERIAL PRIMARY KEY,
    incident_number INTEGER REFERENCES incidents(incident_number),
    anomaly_id VARCHAR(100),
    anomaly_type VARCHAR(50),
    anomaly_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Insert Example:**
```sql
INSERT INTO incident_anomalies (incident_number, anomaly_id, anomaly_type, anomaly_data)
VALUES (20024, 'anom-20240613-001', 'INTERFACE_FLAPPING', '{"interface":"1:55",...}');
```

**Query (for LLM context):**
```sql
SELECT ia.anomaly_id, ia.anomaly_type, ia.anomaly_data
FROM incident_anomalies ia
WHERE ia.incident_number = 20024
ORDER BY ia.created_at;
```

---

### 5. **Kafka Producer**

**Output Topic:** `incidents`  
**Message Format:**
```json
{
  "incident_number": 20024,
  "incident_type": "CONNECTIVITY_ISSUE",
  "device_id": "10.139.38.188",
  "severity": "HIGH",
  "status": "PENDING_DIAGNOSIS",
  "anomaly_count": 2,
  "first_anomaly_time": "2026-06-13T22:50:00Z",
  "last_anomaly_time": "2026-06-13T22:51:30Z",
  "correlated_anomalies": [
    {
      "anomaly_id": "anom-20240613-001",
      "anomaly_type": "INTERFACE_FLAPPING",
      "interface": "1:55",
      "event_count": 4
    },
    {
      "anomaly_id": "anom-20240613-002",
      "anomaly_type": "INTERFACE_FLAPPING",
      "interface": "2:22",
      "event_count": 3
    }
  ],
  "device_vendor": "Extreme Networks",
  "device_family": "EXOS",
  "device_cli_syntax": "EXOS",
  "device_role": "core",
  "created_at": "2026-06-13T22:51:35Z"
}
```

**Routing:**
- **incidents topic** → LLM Diagnosis Service (for AI analysis)
- **PostgreSQL** → Historical incident database

---

## Incident Types & Classification

### Classification Logic

**Type 1: CONNECTIVITY_ISSUE**
- **Patterns:** Interface down, interface flapping, link failures
- **Examples:** Cable issues, port configuration errors, hardware failure
- **Severity:** HIGH to CRITICAL

**Type 2: ROUTING_ISSUE**
- **Patterns:** BGP session down, OSPF neighbor loss, route flapping
- **Examples:** Routing protocol misconfiguration, network partition
- **Severity:** CRITICAL

**Type 3: AUTHENTICATION_ISSUE**
- **Patterns:** Repeated auth failures, RADIUS timeout
- **Examples:** Wrong credentials, AAA server down
- **Severity:** MEDIUM to HIGH

**Type 4: PERFORMANCE_ISSUE**
- **Patterns:** High CPU, memory exhaustion, packet drops
- **Examples:** Resource exhaustion, traffic spike
- **Severity:** MEDIUM to HIGH

**Type 5: SECURITY_ISSUE**
- **Patterns:** Unauthorized access attempts, DDoS indicators
- **Examples:** Brute force attacks, port scanning
- **Severity:** HIGH to CRITICAL

---

## Deduplication Logic

**Problem:** Same root cause generates multiple anomalies → multiple incidents

**Solution:** Deduplicate within time window

**Algorithm:**
```python
def is_duplicate_incident(new_incident, existing_incidents):
    """Check if incident is duplicate"""
    for existing in existing_incidents:
        if (existing.device_id == new_incident.device_id and
            existing.incident_type == new_incident.incident_type and
            existing.status in ['PENDING_DIAGNOSIS', 'IN_PROGRESS'] and
            time_diff(existing.created_at, new_incident.created_at) < 3600):
            return True
    return False
```

**Behavior:**
- **Duplicate Detected:** Update existing incident (add new anomalies)
- **Not Duplicate:** Create new incident

**Example:**
```
10:00 | Incident 20024: Port 1:55 flapping → Created
10:05 | Port 1:55 still flapping → Update 20024 (not new incident)
11:05 | Port 1:55 flapping again → New incident 20025 (>1 hour gap)
```

---

## Dependencies

### Upstream
- **Kafka (anomalies topic):** Anomalies from Anomaly Detector
- **PostgreSQL:** Read existing incidents for deduplication

### Downstream
- **Kafka (incidents topic):** Publishes incidents to LLM Diagnosis
- **PostgreSQL (incidents table):** Stores incident records
- **PostgreSQL (incident_anomalies table):** Links anomalies to incidents

---

## Data Flow

```
Kafka (anomalies) → Consumer
                      ↓
                Correlation Algorithms
                      ↓
                  ┌─────────────┐
                  │ Buffer      │
                  │ (5 min)     │
                  └─────────────┘
                      ↓
          [2+ Anomalies Correlated?]
                      ↓ YES
                Create Incident
                      ↓
           ┌──────────┴──────────┐
           ↓                     ↓
    Kafka (incidents)    PostgreSQL (incidents)
           ↓                     ↓
     LLM Diagnosis          Historical DB
```

---

## Performance Characteristics

### Throughput
- **Tested:** 500 anomalies/second
- **Capacity:** 2,000 anomalies/second
- **Incident Rate:** ~5-10% of anomalies → incidents

### Latency
- **Correlation:** <10ms per anomaly
- **Incident Creation:** 50-100ms (database write)
- **Total:** <200ms from anomaly to incident

### Resource Usage
- **Memory:** 300MB (buffer + state)
- **CPU:** 10-20% on 1 core
- **Storage:** <100MB (ephemeral state)

---

## Monitoring & Health

### Logs
```bash
docker logs smart-noc-correlation-engine --tail 100
```

**Normal Output:**
```
[INFO] Kafka consumer started: anomalies
[INFO] Received anomaly: anom-20240613-001 (INTERFACE_FLAPPING)
[INFO] Buffering anomaly for device 10.139.38.188 (2/2 threshold)
[INFO] Correlation triggered: 2 anomalies within window
[INFO] Created incident 20024: CONNECTIVITY_ISSUE (severity=HIGH)
[INFO] Published incident to Kafka: 20024
```

**Error Indicators:**
```
[ERROR] PostgreSQL connection failed
[ERROR] Incident creation failed: Unique constraint violation
[WARNING] Anomaly buffer full for device 10.139.38.188
```

### Metrics
- **Incidents Created:** Counter (by type, severity)
- **Correlation Latency:** Histogram
- **Buffer Size:** Gauge (per device)
- **Duplicate Rate:** Ratio of deduplicated incidents

---

## Troubleshooting

### Issue: No Incidents Created

**Symptoms:**
- Anomalies flowing but no incidents
- `incidents` topic empty

**Diagnosis:**
```bash
# Check anomaly count per device
docker logs smart-noc-correlation-engine | grep "Buffering anomaly"

# Check correlation threshold
docker logs smart-noc-correlation-engine | grep "threshold"
```

**Resolution:**
1. Verify MIN_ANOMALIES setting (should be 2 or lower)
2. Check CORRELATION_WINDOW (may be too short)
3. Ensure multiple anomalies on same device

---

### Issue: Duplicate Incidents

**Symptoms:**
- Multiple incidents for same issue
- Incident numbers incrementing rapidly

**Diagnosis:**
```bash
# Query duplicate incidents
docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -c \
  "SELECT device_id, incident_type, COUNT(*) FROM incidents WHERE status='PENDING_DIAGNOSIS' GROUP BY device_id, incident_type HAVING COUNT(*) > 1;"
```

**Resolution:**
1. Verify deduplication logic is enabled
2. Increase deduplication window (3600 → 7200 seconds)
3. Add more deduplication criteria (interface, pattern)

---

### Issue: Incident Creation Fails

**Symptoms:**
- Error: "Incident creation failed"
- Database constraint violations

**Diagnosis:**
```bash
# Check PostgreSQL errors
docker logs smart-noc-postgres | grep ERROR

# Verify incidents table
docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -c "SELECT COUNT(*) FROM incidents;"
```

**Resolution:**
1. Check PostgreSQL schema is up to date
2. Verify database credentials
3. Check disk space on PostgreSQL volume

---

## Configuration Parameters

### Correlation Settings
```python
# Minimum anomalies required to create incident
MIN_ANOMALIES = 2

# Time window for correlation (seconds)
CORRELATION_WINDOW = 300

# Deduplication window (seconds)
DEDUPLICATION_WINDOW = 3600

# Device role weights (for severity calculation)
DEVICE_ROLE_WEIGHTS = {
    'core': 3,
    'distribution': 2,
    'access': 1,
    'unknown': 1
}
```

### Incident Type Patterns
```python
INCIDENT_PATTERNS = {
    'CONNECTIVITY_ISSUE': [
        'INTERFACE_DOWN',
        'INTERFACE_FLAPPING',
        'LINK_FAILURE'
    ],
    'ROUTING_ISSUE': [
        'BGP_SESSION_DOWN',
        'OSPF_NEIGHBOR_DOWN',
        'ROUTE_FLAPPING'
    ],
    'AUTHENTICATION_ISSUE': [
        'AUTH_FAILURE',
        'AUTH_TIMEOUT'
    ]
}
```

---

## Scaling Considerations

### Horizontal Scaling
- Deploy multiple instances with consumer group
- Kafka partitioning enables parallel processing
- Shared state via PostgreSQL (not Redis)

### Vertical Scaling
- Increase memory for larger anomaly buffers
- Not CPU-intensive

### Optimization
- Batch PostgreSQL writes (insert multiple incident_anomalies)
- Async Kafka publishing (non-blocking)
- Periodic buffer cleanup (remove stale entries)

---

## Related Documentation

- [Anomaly Detector](03-anomaly-detector.md)
- [LLM Diagnosis Service](05-llm-diagnosis.md)
- [Kafka Topics](11-kafka-topics.md)
- [PostgreSQL Schema](08-postgres.md)
- [Complete Architecture](../02-architecture/COMPLETE_ARCHITECTURE.md)
