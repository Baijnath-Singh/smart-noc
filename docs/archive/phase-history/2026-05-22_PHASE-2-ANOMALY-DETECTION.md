# Phase 2: Anomaly Detection

**Duration**: 2-3 days  
**Difficulty**: Medium  
**Goal**: Automatically detect unusual patterns in network logs

---

## 🎯 What You'll Build

An anomaly detection agent that identifies:
- Interface flapping (rapid up/down cycles)
- Unusual log frequency spikes
- Known error patterns
- Statistical outliers

**Architecture:**
```
Kafka → Anomaly Detector → Alerts Topic
         (Python Service)
```

---

## 📋 Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| **Detector Service** | Main detection logic | Python + scikit-learn |
| **Rule Engine** | Pattern-based detection | Python |
| **ML Model** | Statistical anomalies | Isolation Forest |
| **Alert Publisher** | Send alerts to Kafka | kafka-python |

---

## 🏗️ Implementation Steps

### Step 1: Create Anomaly Detection Service

```bash
cd ~/ng-iam/smart-noc
mkdir -p services/agents/anomaly
cd services/agents/anomaly
```

Create the detector (code provided separately).

---

### Step 2: Detection Strategies

#### Strategy 1: Rule-Based Detection (Simple & Fast)

**Use cases:**
- Known patterns
- Threshold-based
- Business logic

**Examples:**
```python
# Interface flapping: same interface up/down 5+ times in 60 seconds
# High CPU: CPU > 90% for 5+ consecutive logs
# Auth failures: 10+ failures from same IP in 60 seconds
```

#### Strategy 2: Frequency Analysis (Medium)

**Use cases:**
- Detect unusual spikes
- Baseline comparison

**Examples:**
```python
# Normal: 10 logs/min from device
# Anomaly: 100 logs/min from device (10x spike)
```

#### Strategy 3: ML-Based Detection (Advanced)

**Use cases:**
- Unknown patterns
- Multi-dimensional anomalies

**Algorithm**: Isolation Forest
- Unsupervised learning
- Good for high-dimensional data
- Fast training and prediction

---

### Step 3: Anomaly Schema

All detected anomalies follow this format:

```json
{
  "anomaly_id": "uuid",
  "timestamp": "ISO8601",
  "anomaly_type": "INTERFACE_FLAPPING|HIGH_FREQUENCY|THRESHOLD_BREACH|STATISTICAL",
  "severity": "LOW|MEDIUM|HIGH|CRITICAL",
  "confidence": 0.85,
  "device_id": "core-router-01",
  "event_type": "INTERFACE_DOWN",
  "evidence": [
    {
      "timestamp": "...",
      "log_id": "...",
      "message": "..."
    }
  ],
  "metrics": {
    "frequency": 10,
    "baseline": 2,
    "anomaly_score": 0.92
  },
  "recommendation": "Investigate interface cable"
}
```

---

### Step 4: Configure Kafka Topics

```bash
# Connect to Kafka container
docker compose exec kafka bash

# Create anomaly topic
kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic network-anomalies \
  --partitions 3 \
  --replication-factor 1

# Create alerts topic
kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic network-alerts \
  --partitions 3 \
  --replication-factor 1

# Verify
kafka-topics.sh --list --bootstrap-server localhost:9092
```

---

### Step 5: Run Anomaly Detector

```bash
# Install dependencies
cd ~/ng-iam/smart-noc/services/agents/anomaly
pip install -r requirements.txt

# Start detector
python anomaly_detector.py

# Expected output:
# ✅ Connected to Kafka
# 📊 Loaded baseline models
# 🔍 Monitoring: network-logs-parsed
```

---

### Step 6: Test Anomaly Detection

#### Test 1: Interface Flapping

```bash
# Terminal 1: Run detector
python services/agents/anomaly/anomaly_detector.py

# Terminal 2: Generate flapping scenario
python services/log-generator/generate_logs.py --scenario flap

# Expected: Detector logs "🚨 ANOMALY DETECTED: INTERFACE_FLAPPING"
```

#### Test 2: High Frequency

```bash
# Generate logs at high rate
python services/log-generator/generate_logs.py --rate 100

# Expected: Detector flags unusual spike
```

#### Test 3: View Anomalies

```bash
# Check Kafka UI
# http://localhost:8080
# Topic: network-anomalies

# Or use CLI
docker compose exec kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic network-anomalies \
  --from-beginning
```

---

## 📊 Detection Algorithms

### Algorithm 1: Sliding Window Counter

**Use case**: Frequency-based detection

```python
class SlidingWindow:
    def __init__(self, window_size=60, threshold=5):
        self.window_size = window_size  # seconds
        self.threshold = threshold
        self.events = []
    
    def add_event(self, event):
        now = time.time()
        # Remove old events
        self.events = [e for e in self.events 
                      if now - e['timestamp'] < self.window_size]
        self.events.append(event)
        
        # Check threshold
        if len(self.events) >= self.threshold:
            return True  # Anomaly!
        return False
```

---

### Algorithm 2: Z-Score (Statistical)

**Use case**: Deviation from baseline

```python
def detect_zscore_anomaly(value, baseline_mean, baseline_std, threshold=3):
    """
    Z-score > 3 = 99.7% confidence it's an outlier
    """
    if baseline_std == 0:
        return False
    
    z_score = abs((value - baseline_mean) / baseline_std)
    return z_score > threshold
```

---

### Algorithm 3: Isolation Forest (ML)

**Use case**: Multi-dimensional anomalies

```python
from sklearn.ensemble import IsolationForest

# Train on normal data
clf = IsolationForest(contamination=0.1, random_state=42)
clf.fit(normal_data)

# Predict
prediction = clf.predict([new_data])  # -1 = anomaly, 1 = normal
anomaly_score = clf.score_samples([new_data])
```

---

## 🎯 Detection Rules

### Rule 1: Interface Flapping

```yaml
name: Interface Flapping
condition: |
  Same interface has 5+ state changes in 60 seconds
severity: HIGH
action: Create incident
```

### Rule 2: BGP Instability

```yaml
name: BGP Instability
condition: |
  Same BGP neighbor up/down 3+ times in 300 seconds
severity: CRITICAL
action: Page on-call engineer
```

### Rule 3: Brute Force Attack

```yaml
name: Brute Force Attack
condition: |
  10+ auth failures from same source IP in 60 seconds
severity: HIGH
action: Automatically block IP (Phase 5)
```

### Rule 4: CPU Sustained High

```yaml
name: Sustained High CPU
condition: |
  CPU > 90% for 5+ consecutive reports
severity: MEDIUM
action: Investigate process
```

---

## 📈 Performance Tuning

### Baseline Collection

The detector needs a baseline of "normal" behavior:

```python
# Collect baseline for 24 hours
python anomaly_detector.py --mode baseline --duration 86400

# Saves baseline to: data/baseline.json
```

**Baseline includes:**
- Average log frequency per device
- Typical event type distribution
- Normal CPU/memory ranges
- Expected interface states

---

### Adjust Sensitivity

```yaml
# config/anomaly_detector.yaml

detection:
  sensitivity: medium  # low|medium|high
  
  thresholds:
    interface_flap_count: 5
    interface_flap_window: 60
    
    frequency_multiplier: 3  # 3x baseline = anomaly
    
    zscore_threshold: 3
    
    ml_contamination: 0.1  # 10% outlier rate
```

---

## 🐛 Troubleshooting

### Too many false positives

```yaml
# Increase thresholds
interface_flap_count: 10  # was 5
frequency_multiplier: 5   # was 3

# Or collect more baseline data
python anomaly_detector.py --mode baseline --duration 172800  # 48 hours
```

### Missing anomalies

```yaml
# Decrease thresholds
interface_flap_count: 3
frequency_multiplier: 2

# Check detector is running
ps aux | grep anomaly_detector
```

### High memory usage

```python
# Limit event history
MAX_HISTORY_SIZE = 10000  # keep last 10k events

# Use sliding window instead of storing all
```

---

## ✅ Success Metrics

Phase 2 is complete when:

- ✅ Detector consumes logs from Kafka
- ✅ Interface flapping detected correctly
- ✅ Anomalies published to Kafka topic
- ✅ False positive rate < 10%
- ✅ Detection latency < 5 seconds
- ✅ Baseline collected for all devices

---

## 📁 Files Created

```
services/agents/anomaly/
├── anomaly_detector.py      # Main detector
├── rules.py                 # Rule definitions
├── ml_model.py             # ML-based detection
├── baseline.py             # Baseline collection
├── requirements.txt
└── config.yaml

data/
└── baseline.json           # Collected baseline
```

---

## 🎓 Key Learnings

After Phase 2, you'll understand:

1. **Anomaly detection approaches**:
   - Rule-based (deterministic)
   - Statistical (probabilistic)
   - ML-based (learned)

2. **Stream processing**:
   - Sliding windows
   - Stateful processing
   - Event time vs processing time

3. **Tuning trade-offs**:
   - Sensitivity vs false positives
   - Latency vs accuracy
   - Memory vs history depth

---

## 🚀 Next Step

**→ [Phase 3: Correlation Engine](PHASE-3-CORRELATION.md)**

Now that we detect anomalies, let's connect related ones!

---

## 📝 Optional Enhancements

Before Phase 3:

1. **Add more rules**:
   - OSPF neighbor down
   - DHCP pool exhaustion
   - Duplicate IP detection

2. **Improve ML model**:
   - Feature engineering
   - Different algorithms (LOF, DBSCAN)
   - Online learning

3. **Better visualization**:
   - Real-time anomaly dashboard
   - Anomaly timeline
   - Device heatmap

4. **Alerting**:
   - Email notifications
   - Slack/Teams webhooks
   - PagerDuty integration
