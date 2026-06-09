# Smart NOC End-to-End Flow Analysis

**Example Scenario**: BGP Failure Detection
**Test Command**: `./scripts/generate-logs.sh --rate 10 --duration 1 --scenario bgp_failure`

---

## 📊 Flow Overview

```
┌─────────────┐    ┌──────────┐    ┌─────────────┐    ┌─────────────┐    ┌──────────┐
│ Log         │───▶│ Logstash │───▶│  Anomaly    │───▶│ Correlation │───▶│   LLM    │
│ Generator   │    │ Enricher │    │  Detector   │    │   Engine    │    │ Diagnosis│
└─────────────┘    └──────────┘    └─────────────┘    └─────────────┘    └──────────┘
      │                  │                  │                  │                  │
      ▼                  ▼                  ▼                  ▼                  ▼
   Kafka:           Kafka:           Kafka:           Kafka:            PostgreSQL
network-logs  network-logs-     anomalies        incidents         incidents table
               enriched                                           (with root_cause)
```

---

## Step 1: Log Generation 📝

### Command Executed
```bash
./scripts/generate-logs.sh --rate 10 --duration 1 --scenario bgp_failure
```

### Logs Generated (10 total)
1. **dist-switch-01**: STP_STATE_CHANGE
2. **dist-switch-03**: STP_STATE_CHANGE  
3. **dist-switch-04**: STP_STATE_CHANGE
4. **dist-switch-05**: HIGH_CPU (85-99%)
5. **edge-firewall-02**: HIGH_CPU (85-99%)
6. **core-router-03**: HIGH_CPU (85-99%)
7. **core-router-01**: BGP_IDLE (neighbor went idle)
8. **dist-switch-02**: STP_STATE_CHANGE
9. **core-router-02**: BGP_DOWN (neighbor went down) ⚠️ **Critical**
10. **dist-switch-04**: INTERFACE_DOWN

### Example Raw Log (JSON)
```json
{
  "timestamp": "May 16 03:14:04",
  "device_id": "core-router-02",
  "device_type": "router",
  "severity": "CRITICAL",
  "event_type": "BGP_DOWN",
  "neighbor": "10.167.166.70",
  "message": "%BGP-5-ADJCHANGE: neighbor 10.167.166.70 down"
}
```

**Published to**: Kafka topic `network-logs`

---

## Step 2: Logstash Enrichment 🔧

### Enrichment Process

**Input**: Raw JSON from `network-logs` topic

**Enrichment Applied**:
1. ✅ **device_role** extraction (core/edge/distribution)
2. ✅ **criticality** assignment (high/medium/low)
3. ✅ **bgp_neighbor** extraction (for BGP events)
4. ✅ **cpu_utilization** extraction (for CPU events)
5. ✅ **event_fingerprint** (SHA256 hash for deduplication)
6. ✅ **tags** categorization (bgp, routing, performance, etc.)

### Example Enriched Log
```json
{
  "severity": "CRITICAL",
  "timestamp": "May 16 03:14:04",
  "event_type": "BGP_DOWN",
  "device_id": "core-router-02",
  "device_role": "core",          // ← Added by Logstash
  "criticality": "high",           // ← Added by Logstash
  "bgp_neighbor": "10.167.166.70", // ← Extracted by Logstash
  "bgp_state": "down",             // ← Extracted by Logstash
  "tags": ["bgp", "routing"],      // ← Added by Logstash
  "event_fingerprint": "68ec540e3860b1047771f56843fed748e1a0950bda89152765a2dc82714b17bf",
  "@timestamp": "2026-05-16T03:14:04.000Z",
  "message": "%BGP-5-ADJCHANGE: neighbor 10.167.166.70 down"
}
```

**Published to**: 
- Kafka topic `network-logs-enriched`
- Elasticsearch index `network-logs-2026.05.16`

### ⚠️ Issues Observed

**Problem 1: Date Parsing Failures**
```
"tags": ["_dateparsefailure", "_grokparsefailure"]
```
- Logstash cannot parse "May 16 03:14:04" format
- Missing year in timestamp
- Results in using current time instead

**Problem 2: Ruby Exception**
```
Ruby exception occurred: can't convert LogStash::Timestamp into an exact number
```
- Occurs when processing incident objects (not raw logs)
- Logstash is re-ingesting incidents from Kafka (creating a loop)

---

## Step 3: Anomaly Detection 🔍

### ML Model Status
```
ML Model: IsolationForest
├─ Trained: True ✅
├─ Training samples: 97
└─ Last training: 2026-05-16T03:02:15.608735
```

### Detection Process

**For each enriched log**:

1. **Feature Extraction**:
   ```python
   features = {
       "severity": "CRITICAL",
       "event_type": "BGP_DOWN",
       "criticality": "high",
       "time_context": "3:00 on day 5"  # Hour and day of week
   }
   ```

2. **ML Model Prediction**:
   ```python
   anomaly_score = isolation_forest.score_samples([features])
   # anomaly_score = -0.702 (negative = anomaly)
   
   if anomaly_score < threshold:
       is_anomaly = True
       confidence = 1.0  # 100%
   ```

3. **Anomaly Object Created**:
   ```json
   {
     "anomaly_type": "ML_DETECTED_ANOMALY",
     "severity": "MEDIUM",
     "device_id": "core-router-02",
     "event_type": "BGP_DOWN",
     "detection_method": "ml",
     "model": "isolation_forest",
     "confidence": 1.0,
     "anomaly_score": -0.702,
     "details": "ML model detected unusual pattern (confidence: 100.00%)",
     "features": {...},
     "timestamp": "2026-05-16T03:14:04.541775",
     "source_log": {...},  // Full enriched log
     "detected_at": "2026-05-16T03:14:04.541788",
     "detector_version": "1.0.0"
   }
   ```

### Anomalies Detected (9 out of 10 logs)

| Device | Event Type | Anomaly Score | Detected? |
|--------|-----------|---------------|-----------|
| dist-switch-01 | STP_STATE_CHANGE | -0.xxx | ✅ YES |
| dist-switch-03 | STP_STATE_CHANGE | -0.xxx | ✅ YES |
| dist-switch-04 | STP_STATE_CHANGE | -0.xxx | ✅ YES |
| dist-switch-05 | HIGH_CPU | -0.xxx | ❌ NO |
| edge-firewall-02 | HIGH_CPU | -0.684 | ✅ YES |
| core-router-03 | HIGH_CPU | -0.73 | ✅ YES |
| core-router-01 | BGP_IDLE | -0.74 | ✅ YES |
| dist-switch-02 | STP_STATE_CHANGE | -0.705 | ✅ YES |
| core-router-02 | BGP_DOWN | -0.702 | ✅ YES |
| dist-switch-04 | INTERFACE_DOWN | -0.xxx | ❌ NO |

**Published to**: Kafka topic `anomalies`

### 📊 Detection Statistics
```
Logs processed: 104 total
Total anomalies: 16
  ├─ Rule-based: 7
  └─ ML-based: 9 (from this batch)
```

### ⚠️ Issue: Over-Sensitive ML Model

The ML model is detecting **90% of logs as anomalies**. This happens because:
1. **Small training set** (97 samples)
2. **High diversity** in log types (IsolationForest treats rare patterns as anomalies)
3. **No tuning** of contamination parameter (default: 0.1 = 10% expected anomalies)

**Result**: Many false positives, "UNKNOWN" incidents created

---

## Step 4: Correlation Engine 🔗

### Time-Based Grouping (5-minute window)

**Correlation Logic**:
```python
# 1. Buffer anomalies within 5-minute window
time_window = 5 * 60  # 300 seconds

# 2. Group by time proximity
for anomaly in anomalies:
    if (current_time - anomaly.timestamp) < time_window:
        buffer.append(anomaly)

# 3. When buffer has 2+ anomalies, attempt correlation
if len(buffer) >= 2:
    incidents = correlate_patterns(buffer)
```

### Pattern Detection

**Pattern Matcher Checks**:

1. **CONNECTIVITY_ISSUE**:
   ```python
   # Need: 2+ devices with interface/link problems
   if count_devices_with_connectivity_issues >= 2:
       return "CONNECTIVITY_ISSUE"
   ```

2. **DEVICE_FAILURE**:
   ```python
   # Need: 3+ anomalies on single device
   if max_anomalies_per_device >= 3:
       return "DEVICE_FAILURE"
   ```

3. **BGP_INSTABILITY**:
   ```python
   # Need: 2+ BGP events
   if count_bgp_events >= 2:
       return "BGP_INSTABILITY"
   ```

4. **UNKNOWN** (default):
   ```python
   # Fallback: 2+ anomalies that don't match patterns
   return "UNKNOWN"
   ```

### Incidents Created

Your test created **5 new incidents** (Incidents #10-14):

#### Incident #10: UNKNOWN
```json
{
  "incident_number": 10,
  "incident_type": "UNKNOWN",
  "severity": "MEDIUM",
  "affected_devices": ["dist-switch-01", "core-router-01"],
  "primary_device": "core-router-01",
  "anomaly_count": 2,
  "correlation_method": "PATTERN_BASED",
  "correlation_confidence": 85.0,
  "impact_score": 41.0
}
```
**Why UNKNOWN?**: STP_STATE_CHANGE + BGP_IDLE don't match known patterns

#### Incident #11: UNKNOWN
```json
{
  "incident_number": 11,
  "affected_devices": ["unknown", "dist-switch-03"],
  "primary_device": "dist-switch-03",
  "anomaly_count": 2
}
```
**Note**: One device is "unknown" (from incident loop issue)

#### Incident #12: UNKNOWN
```json
{
  "incident_number": 12,
  "affected_devices": ["edge-firewall-02", "dist-switch-04"],
  "primary_device": "edge-firewall-02",
  "anomaly_count": 2
}
```
**Pattern**: HIGH_CPU + STP_STATE_CHANGE (unrelated events)

#### Incident #13: UNKNOWN
```json
{
  "incident_number": 13,
  "affected_devices": ["core-router-02", "dist-switch-02"],
  "primary_device": "core-router-02",
  "anomaly_count": 2
}
```
**Pattern**: BGP_DOWN + STP_STATE_CHANGE (should be BGP_INSTABILITY?)

#### Incident #14: UNKNOWN
```json
{
  "incident_number": 14,
  "affected_devices": ["core-router-03", "core-router-01"],
  "primary_device": "core-router-03",
  "anomaly_count": 2
}
```
**Pattern**: HIGH_CPU + BGP_IDLE (performance + routing)

**Published to**: 
- Kafka topic `incidents`
- PostgreSQL `incidents` table

### 📊 Correlation Statistics
```
Anomalies processed: 20
Incidents created: 10 (5 from this batch)
Correlations found: 10
Buffer size: 0 anomalies (all processed)
```

### ⚠️ Issue: Pattern Matching Not Working

**Expected**: BGP_INSTABILITY incident for BGP_DOWN + BGP_IDLE events

**Actual**: Multiple UNKNOWN incidents

**Why?**:
1. Anomalies are on different devices (core-router-01 vs core-router-02)
2. Pattern matcher groups by device first, then checks event types
3. BGP events split across devices → no BGP_INSTABILITY pattern matched

---

## Step 5: LLM Diagnosis 🤖

### Diagnosis Process

**For each incident**:

1. **Context Building**:
   ```python
   context = {
       "incident": incident_details,
       "anomalies": fetch_related_anomalies(incident_id),
       "device_history": fetch_device_logs(devices, last_hour),
       "similar_incidents": find_similar_past_incidents(incident_type)
   }
   ```

2. **LLM Prompt Construction**:
   ```
   SYSTEM: You are a network operations expert...
   
   USER: Analyze this incident:
   - Type: UNKNOWN
   - Devices: core-router-02, dist-switch-02
   - Anomalies:
     * ML_DETECTED_ANOMALY: BGP_DOWN on core-router-02
     * ML_DETECTED_ANOMALY: STP_STATE_CHANGE on dist-switch-02
   - Timeline: Both occurred at 2026-05-16 03:14:04
   
   Provide root cause and remediation plan.
   ```

3. **Groq API Call**:
   ```python
   response = openai.chat.completions.create(
       model="llama-3.3-70b-versatile",
       messages=[system_prompt, user_prompt],
       temperature=0.3,
       max_tokens=2000
   )
   # Duration: ~1.5-2 seconds ⚡
   ```

4. **Database Update**:
   ```sql
   UPDATE incidents
   SET root_cause = 'Simultaneous ML anomalies...',
       remediation_plan = '[{step 1}, {step 2}, ...]',
       updated_at = NOW()
   WHERE incident_number = 13;
   ```

### Diagnosis Results

#### Incident #10
```
Root Cause:
  "Unidentified machine learning detected anomalies on core-router-01 
   and dist-switch-01, potentially indicating correlated network issues."

Confidence: 0.60 (LOW)
Duration: 1821ms
Tokens: 1497
```

#### Incident #11
```
Root Cause:
  "Unidentified anomaly detected by machine learning algorithm on 
   dist-switch-03 and an unknown device, suggesting potential network 
   configuration issues."

Confidence: 0.60 (LOW)
Duration: 1545ms
Tokens: 1419
```

#### Incident #12
```
Root Cause:
  "Sudden and simultaneous machine learning detected anomalies on 
   edge-firewall-02 and dist-switch-04 indicate a potential cascading 
   failure or coordinated attack."

Confidence: 0.80 (MEDIUM-HIGH)
Duration: 1928ms
Tokens: 1507
```

#### Incident #13
```
Root Cause:
  "Simultaneous machine learning detected anomalies on core-router-02 
   and dist-switch-02 indicate a potential Layer 2/3 connectivity issue 
   affecting both routing and switching."

Confidence: 0.75 (MEDIUM-HIGH)
Duration: 2127ms
Tokens: 1561
```

#### Incident #14
```
Root Cause:
  "Simultaneous machine learning detected anomalies on core-router-03 
   and core-router-01, indicating a potential BGP routing issue or 
   resource exhaustion in the core network."

Confidence: 0.60 (LOW)
Duration: 2029ms
Tokens: 1464
```

### 📊 Diagnosis Statistics
```
Processed: 60 incidents
Diagnosed: 6 (including 5 new ones)
Failed: 0
Skipped: 54 (already diagnosed or delay not met)
Rate: 4.80/min
Total Tokens: 9,236
Estimated Cost: $0.0000 ✅ (Free Groq tier)
```

### Performance Comparison

| Metric | Ollama (phi3) | Groq (llama-3.3) |
|--------|---------------|------------------|
| **Diagnosis Time** | 120-180s | **1.5-2s** ⚡ |
| **Quality** | Lower | **Higher** 🎯 |
| **CPU Usage** | High | **None** ☁️ |
| **Cost** | Free (local) | **Free** tier ✅ |

---

## 🔍 Key Observations

### ✅ What's Working Well

1. **Enrichment Pipeline**: Device roles and criticality correctly assigned
2. **Groq Performance**: 48-72x faster than Ollama
3. **End-to-End Flow**: All services communicating properly
4. **Database Updates**: Root causes saved successfully

### ⚠️ Issues Identified

#### 1. ML Model Over-Detection
**Problem**: 90% of logs flagged as anomalies
**Impact**: Many false positives, "UNKNOWN" incidents
**Solution**:
```yaml
# services/anomaly-detector/config.yaml
detection:
  isolation_forest:
    contamination: 0.05  # Lower from 0.1 to 0.05 (5% anomalies)
    min_samples: 100      # Increase from 50 to 100 (better training)
```

#### 2. Pattern Matching Too Strict
**Problem**: BGP events split across devices don't match BGP_INSTABILITY pattern
**Expected**: core-router-01 (BGP_IDLE) + core-router-02 (BGP_DOWN) → BGP_INSTABILITY
**Actual**: Two separate UNKNOWN incidents

**Solution**: Modify pattern matcher to check BGP events across devices:
```python
# services/correlation-engine/correlators/pattern_based.py
def detect_bgp_instability(anomalies):
    bgp_events = [a for a in anomalies if 'BGP' in a.event_type]
    if len(bgp_events) >= 2:  # Don't require same device
        return "BGP_INSTABILITY"
```

#### 3. Logstash Processing Incidents
**Problem**: Incidents published to Kafka are consumed by Logstash, creating errors
**Evidence**: `"document_type": "incident"` in Logstash output

**Solution**: Configure Logstash to skip incident messages:
```ruby
# infrastructure/logstash/pipeline/network-logs.conf
filter {
  if [document_type] == "incident" {
    drop {}  # Skip incidents, only process logs
  }
}
```

#### 4. Timestamp Parsing Failures
**Problem**: Logstash can't parse "May 16 03:14:03" (missing year)
**Impact**: `_dateparsefailure` tags, uses current time

**Solution**: Update log generator to use ISO8601 format:
```python
# services/log-generator/generate_logs.py
def _generate_syslog_timestamp(self):
    return datetime.utcnow().isoformat()  # "2026-05-16T03:14:03Z"
```

#### 5. Low Diagnosis Confidence
**Problem**: Incidents #10, #11, #14 have only 60% confidence
**Reason**: LLM uncertain about "ML_DETECTED_ANOMALY" without specific event details

**Solution**: Improve prompt to include more context from source logs

---

## 📈 Summary Statistics

| Metric | Value |
|--------|-------|
| **Logs Generated** | 10 |
| **Logs Enriched** | 10 (100%) |
| **Anomalies Detected** | 9 (90%) |
| **Incidents Created** | 5 |
| **Incidents Diagnosed** | 5 (100%) |
| **Total Time** | ~15 seconds |
| **Average Diagnosis Time** | 1.9 seconds |

---

## 🎯 Recommendations

### Immediate Fixes

1. **Tune ML Model**: Reduce contamination to 5%
2. **Fix BGP Pattern**: Match BGP events across devices
3. **Filter Incidents**: Prevent Logstash from processing incidents
4. **Fix Timestamps**: Use ISO8601 format in log generator

### Long-Term Improvements

1. **Rule-Based Detection**: Add specific rules for BGP_DOWN (don't rely only on ML)
2. **Multi-Device Patterns**: Enhance correlation to detect network-wide issues
3. **Confidence Calibration**: Improve LLM prompts with more context
4. **Alert Thresholds**: Configure severity-based alerting

---

## 📚 Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [TESTING_GUIDE.md](TESTING_GUIDE.md) - Testing scenarios
- [GROQ_SETUP.md](GROQ_SETUP.md) - LLM configuration
- [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) - Common issues
