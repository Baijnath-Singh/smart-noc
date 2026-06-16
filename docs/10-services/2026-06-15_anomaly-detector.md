# Anomaly Detector Service

**Service Name:** `smart-noc-anomaly-detector`  
**Image:** `smart-noc_anomaly-detector` (custom)  
**Technology:** Python 3.9  
**Status:** Core Service  
**Uptime Target:** 99.5%

---

## Overview

The Anomaly Detector Service is a **real-time stream processor** that consumes enriched network logs from Kafka, applies both **rule-based** and **ML-based** detection algorithms, and publishes anomalies to Kafka for correlation and diagnosis.

**Key Capabilities:**
- **Dual Detection:** Rule-based patterns + Isolation Forest ML
- **Enrichment Propagation:** Preserves device metadata through pipeline
- **Real-time Processing:** Sub-second detection latency
- **Stateful Tracking:** Maintains time-window state for pattern detection

---

## Service Configuration

### Resources
- **Memory:** 1GB-2GB (ML models + state tracking)
- **CPU:** 1-2 cores
- **Storage:** Minimal (checkpoints only)

### Environment Variables
```
KAFKA_BOOTSTRAP_SERVERS: kafka:9092
KAFKA_GROUP_ID: anomaly-detector-group
LOG_LEVEL: INFO
DETECTION_WINDOW: 300  # 5 minutes
ML_MODEL_PATH: /app/models/isolation_forest.pkl
POSTGRES_HOST: postgres
POSTGRES_PORT: 5432
POSTGRES_DB: smart_noc
POSTGRES_USER: noc_admin
POSTGRES_PASSWORD: noc_password
```

---

## Architecture Components

### 1. **Kafka Consumer**

**Input Topic:** `network-logs`  
**Consumer Group:** `anomaly-detector-group`  
**Offset Management:** Auto-commit (interval: 5s)

**Message Format (Input):**
```json
{
  "@timestamp": "2026-06-13T22:51:55.123Z",
  "device_id": "10.139.38.188",
  "event_type": "INTERFACE_DOWN",
  "interface": "1:55",
  "device_vendor": "Extreme Networks",
  "device_family": "EXOS",
  "device_cli_syntax": "EXOS",
  "syslog_message": "Port 1:55 link DOWN"
}
```

**Processing:**
- Deserialize JSON
- Validate required fields
- Extract timestamp, device_id, event_type
- Pass to detection engines

---

### 2. **Rule-Based Detection Engine**

**Purpose:** Pattern-based anomaly detection using predefined rules

#### **Detection Rules**

**A. Interface Flapping Detection**

**Pattern:** Multiple UP/DOWN transitions on same interface within time window

**Logic:**
```
IF interface has 3+ state changes in 5 minutes:
    THEN create INTERFACE_FLAPPING anomaly
```

**Parameters:**
- **Window:** 300 seconds (5 minutes)
- **Threshold:** 3 transitions minimum
- **State Tracking:** Per-device, per-interface

**Example:**
```
22:50:00 | Port 1:55 DOWN
22:50:30 | Port 1:55 UP
22:51:00 | Port 1:55 DOWN
22:51:30 | Port 1:55 UP
         ↓
    FLAPPING DETECTED
```

**Output Anomaly:**
```json
{
  "anomaly_id": "anom-20240613-001",
  "anomaly_type": "INTERFACE_FLAPPING",
  "device_id": "10.139.38.188",
  "interface": "1:55",
  "event_count": 4,
  "time_window_seconds": 90,
  "first_seen": "2026-06-13T22:50:00Z",
  "last_seen": "2026-06-13T22:51:30Z",
  "severity": "HIGH",
  "device_vendor": "Extreme Networks",
  "device_cli_syntax": "EXOS"
}
```

---

**B. Authentication Brute Force Detection**

**Pattern:** Multiple failed authentication attempts from same source

**Logic:**
```
IF device has 5+ auth failures in 10 minutes:
    THEN create AUTH_BRUTE_FORCE anomaly
```

**Parameters:**
- **Window:** 600 seconds (10 minutes)
- **Threshold:** 5 failures
- **State Tracking:** Per-device

---

**C. BGP Session Instability**

**Pattern:** BGP session flapping (established → down → established)

**Logic:**
```
IF BGP peer transitions 2+ times in 15 minutes:
    THEN create BGP_INSTABILITY anomaly
```

**Parameters:**
- **Window:** 900 seconds (15 minutes)
- **Threshold:** 2 transitions
- **State Tracking:** Per-device, per-peer

---

**D. High Error Rate**

**Pattern:** Spike in error messages

**Logic:**
```
IF error_messages > 50 in 5 minutes:
    THEN create HIGH_ERROR_RATE anomaly
```

**Parameters:**
- **Window:** 300 seconds
- **Threshold:** 50 errors
- **State Tracking:** Per-device

---

### 3. **ML-Based Detection Engine**

**Algorithm:** Isolation Forest  
**Purpose:** Detect novel/unknown anomalies not covered by rules

#### **Feature Engineering**

**Input Features (per log):**
1. **event_type_encoded:** One-hot encoding of event types
2. **hour_of_day:** Temporal feature (0-23)
3. **day_of_week:** Temporal feature (0-6)
4. **device_role_encoded:** One-hot encoding of device roles
5. **message_length:** Length of syslog message
6. **frequency_last_hour:** Event count from this device in last hour

**Feature Vector Example:**
```python
[
    event_type_INTERFACE_DOWN: 1,
    event_type_INTERFACE_UP: 0,
    event_type_BGP_SESSION: 0,
    hour: 22,
    day_of_week: 4,  # Friday
    device_role_core: 1,
    message_length: 28,
    frequency_last_hour: 5
]
```

#### **Isolation Forest Model**

**Parameters:**
```python
IsolationForest(
    n_estimators=100,
    contamination=0.05,  # 5% anomaly rate expected
    max_samples='auto',
    random_state=42
)
```

**Training:**
- **Dataset:** Historical logs (30 days)
- **Size:** 100K+ samples
- **Retraining:** Weekly (automated)
- **Validation:** Precision/Recall metrics

**Inference:**
```python
anomaly_score = model.decision_function([feature_vector])
is_anomaly = anomaly_score < threshold  # Typically -0.5
```

**Output:**
```json
{
  "anomaly_id": "anom-ml-20240613-042",
  "anomaly_type": "ML_DETECTED",
  "device_id": "10.139.38.188",
  "anomaly_score": -0.73,
  "confidence": 0.85,
  "features": {
    "event_type": "INTERFACE_DOWN",
    "hour": 22,
    "frequency_spike": true
  },
  "device_vendor": "Extreme Networks"
}
```

---

### 4. **Enrichment Propagation**

**Purpose:** Ensure device metadata flows through entire pipeline

**Implementation:**
```python
def _enrich_with_device_fields(anomaly, log):
    """Copy device metadata from source log to anomaly"""
    enrichment_fields = [
        'device_vendor',
        'device_family',
        'device_model',
        'device_os_version',
        'device_cli_syntax',
        'device_role'
    ]
    
    for field in enrichment_fields:
        if field in log:
            anomaly[field] = log[field]
    
    return anomaly
```

**Logging:**
```
✓ Enriched anomaly with 6 device fields (vendor=Extreme Networks, cli=EXOS)
```

**Validation:**
```python
if not anomaly.get('device_vendor'):
    logger.warning("⚠ No enrichment fields found in log for device {device_id}")
```

---

### 5. **Kafka Producer**

**Output Topic:** `anomalies`  
**Message Format:**
```json
{
  "anomaly_id": "anom-20240613-001",
  "anomaly_type": "INTERFACE_FLAPPING",
  "device_id": "10.139.38.188",
  "interface": "1:55",
  "severity": "HIGH",
  "confidence": 0.95,
  "event_count": 4,
  "time_window_seconds": 90,
  "first_seen": "2026-06-13T22:50:00Z",
  "last_seen": "2026-06-13T22:51:30Z",
  "device_vendor": "Extreme Networks",
  "device_family": "EXOS",
  "device_model": "X690-48x",
  "device_cli_syntax": "EXOS",
  "device_role": "core",
  "source_logs": [
    {"timestamp": "2026-06-13T22:50:00Z", "message": "Port 1:55 DOWN"},
    {"timestamp": "2026-06-13T22:50:30Z", "message": "Port 1:55 UP"},
    {"timestamp": "2026-06-13T22:51:00Z", "message": "Port 1:55 DOWN"},
    {"timestamp": "2026-06-13T22:51:30Z", "message": "Port 1:55 UP"}
  ],
  "detection_method": "rule_based",
  "created_at": "2026-06-13T22:51:35Z"
}
```

---

### 6. **PostgreSQL Logging**

**Table:** `anomalies`

**Schema:**
```sql
CREATE TABLE anomalies (
    anomaly_id VARCHAR(100) PRIMARY KEY,
    anomaly_type VARCHAR(50),
    device_id VARCHAR(100),
    interface VARCHAR(50),
    severity VARCHAR(20),
    confidence FLOAT,
    event_count INTEGER,
    time_window_seconds INTEGER,
    first_seen TIMESTAMP,
    last_seen TIMESTAMP,
    detection_method VARCHAR(50),
    anomaly_data JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Purpose:**
- Historical anomaly tracking
- Trend analysis
- ML model training data
- Audit trail

**Insert Example:**
```sql
INSERT INTO anomalies (anomaly_id, anomaly_type, device_id, severity, anomaly_data)
VALUES ('anom-20240613-001', 'INTERFACE_FLAPPING', '10.139.38.188', 'HIGH', '{"interface":"1:55",...}');
```

---

## Dependencies

### Upstream
- **Kafka (network-logs topic):** Enriched logs from Logstash
- **Redis:** Caching for frequency calculations (optional)

### Downstream
- **Kafka (anomalies topic):** Publishes detected anomalies
- **Correlation Engine:** Consumes anomalies
- **PostgreSQL:** Logs anomalies to database

---

## Data Flow

```
Kafka (network-logs) → Consumer
                          ↓
                    Rule-Based Engine
                          ↓
                    ML-Based Engine
                          ↓
                    Enrichment Propagation
                          ↓
                    Kafka (anomalies) → Correlation Engine
                          ↓
                    PostgreSQL (anomalies table)
```

---

## Performance Characteristics

### Throughput
- **Tested:** 5,000 logs/second
- **Capacity:** 10,000 logs/second (optimized)
- **Detection Rate:** ~3-5% of logs trigger anomalies

### Latency
- **Rule-Based:** <5ms per log
- **ML-Based:** 10-20ms per log (model inference)
- **Total:** 15-25ms average

### Resource Usage
- **Memory:** 1.2GB (ML model + state)
- **CPU:** 30-50% on 2 cores at 2K logs/sec
- **Storage:** <1GB (model + checkpoints)

---

## Monitoring & Health

### Logs
```bash
docker logs smart-noc-anomaly-detector --tail 100
```

**Normal Output:**
```
[INFO] Kafka consumer started: network-logs
[INFO] Loaded Isolation Forest model: 100 estimators
[INFO] Detected INTERFACE_FLAPPING: device=10.139.38.188, interface=1:55
[INFO] ✓ Enriched anomaly with 6 device fields (vendor=Extreme Networks, cli=EXOS)
[INFO] Published anomaly to Kafka: anom-20240613-001
```

**Error Indicators:**
```
[ERROR] Kafka connection failed: Connection refused
[ERROR] PostgreSQL insert failed: Connection timeout
[WARNING] ⚠ No enrichment fields found in log for device 10.139.38.188
```

### Metrics
- **Anomalies Detected:** Counter (by type)
- **Detection Latency:** Histogram
- **Kafka Lag:** Consumer offset lag
- **False Positive Rate:** Manual validation

---

## Troubleshooting

### Issue: No Anomalies Detected

**Symptoms:**
- Logs flowing but no anomalies published
- `anomalies` topic empty

**Diagnosis:**
```bash
# Check if logs are being consumed
docker logs smart-noc-anomaly-detector | grep "Consumed log"

# Check detection thresholds
docker logs smart-noc-anomaly-detector | grep "threshold"
```

**Resolution:**
1. Verify logs have enrichment fields (device_vendor, etc.)
2. Lower detection thresholds temporarily
3. Check rule logic for event_type matching

---

### Issue: High False Positive Rate

**Symptoms:**
- Too many anomalies generated
- Most are not real issues

**Diagnosis:**
- Review anomaly severity distribution
- Check ML model contamination parameter

**Resolution:**
1. Increase detection thresholds (e.g., 3 → 5 events)
2. Retrain ML model with labeled data
3. Add exclusion rules for known false positives

---

### Issue: Enrichment Fields Missing

**Symptoms:**
- Warning: "No enrichment fields found"
- LLM diagnosis receives generic anomalies

**Diagnosis:**
```bash
# Check source logs in Kafka
docker exec smart-noc-kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic network-logs --from-beginning | head -5
```

**Resolution:**
1. Verify Logstash enrichment is working
2. Check device-enrichment service health
3. Ensure devices exist in PostgreSQL

---

## Scaling Considerations

### Horizontal Scaling
- Deploy multiple instances with same consumer group
- Kafka partitions enable parallelism (3-6 partitions recommended)
- State synchronization via Redis (for frequency counters)

### Vertical Scaling
- Increase memory for larger ML models
- Add CPU for faster inference

### Optimization
- Batch processing: Process 10-50 logs before committing
- Async PostgreSQL writes (non-blocking)
- Redis caching for frequency lookups

---

## ML Model Management

### Training Pipeline
```bash
# Extract training data from PostgreSQL
python scripts/extract_training_data.py --days 30 --output train.csv

# Train Isolation Forest model
python scripts/train_model.py --input train.csv --output models/isolation_forest.pkl

# Validate model
python scripts/validate_model.py --model models/isolation_forest.pkl --test test.csv
```

### Model Deployment
```bash
# Copy model to service container
docker cp models/isolation_forest.pkl smart-noc-anomaly-detector:/app/models/

# Restart service to load new model
docker restart smart-noc-anomaly-detector
```

### Model Monitoring
- **Drift Detection:** Compare feature distributions monthly
- **Performance Tracking:** Precision/Recall on labeled data
- **Retraining Schedule:** Weekly or on significant drift

---

## Configuration Files

### Main Service
**Location:** `/services/anomaly-detector/anomaly_service.py`

### Detection Rules
**Location:** `/services/anomaly-detector/detectors/rule_based.py`

**Configurable Parameters:**
```python
FLAPPING_THRESHOLD = 3  # events
FLAPPING_WINDOW = 300   # seconds
AUTH_THRESHOLD = 5      # attempts
AUTH_WINDOW = 600       # seconds
```

### ML Model Config
**Location:** `/services/anomaly-detector/detectors/ml_based.py`

**Parameters:**
```python
CONTAMINATION = 0.05  # Expected anomaly rate
THRESHOLD = -0.5      # Decision threshold
```

---

## Related Documentation

- [Logstash Service](01-logstash.md)
- [Correlation Engine](04-correlation-engine.md)
- [Kafka Topics](11-kafka-topics.md)
- [PostgreSQL Schema](08-postgres.md)
- [Complete Architecture](../02-architecture/COMPLETE_ARCHITECTURE.md)
