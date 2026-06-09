# Isolation Forest Anomaly Detection - Deep Dive

## 📚 Table of Contents
1. [How Isolation Forest Works](#how-isolation-forest-works)
2. [Feature Extraction](#feature-extraction)
3. [Training Process](#training-process)
4. [Detection Process](#detection-process)
5. [Real Example Walkthrough](#real-example-walkthrough)
6. [Understanding Scores](#understanding-scores)

---

## How Isolation Forest Works 🌲

### Core Concept

**Key Idea**: Anomalies are rare and different, so they're easier to "isolate" from normal data.

Think of it like finding a red ball in a bag of blue balls:
- **Normal case**: Blue ball is surrounded by other blue balls (hard to isolate)
- **Anomaly case**: Red ball stands alone (easy to isolate)

### Visual Example

Imagine we have network logs plotted by severity and time:

```
High Severity
    │
    │     ○                    ← Anomaly (BGP_DOWN at 3 AM)
    │                          (Easy to isolate: just 2 cuts)
    │
Mid │  ●●●●●●●●●●●●●●●        ← Normal logs
    │  ●●●●●●●●●●●●●●●        (Hard to isolate: need many cuts)
    │  ●●●●●●●●●●●●●●●
Low │
    └─────────────────────────► Time
      9AM        12PM       3AM
```

**Isolation Forest Algorithm**:
1. **Pick random feature** (e.g., severity or time)
2. **Pick random split value** (e.g., severity > 2)
3. **Divide data** into two groups
4. **Repeat** until each point is isolated
5. **Count splits** needed to isolate each point
   - **Few splits** = Anomaly (easy to isolate)
   - **Many splits** = Normal (hard to isolate)

---

## Feature Extraction 🔍

### 12 Features Extracted from Each Log

Your system converts raw logs into 12 numerical features:

```python
# Raw Log Input
{
  "timestamp": "May 16 03:14:04",
  "device_id": "core-router-02",
  "device_type": "router",
  "severity": "CRITICAL",
  "event_type": "BGP_DOWN",
  "neighbor": "10.167.166.70",
  "message": "%BGP-5-ADJCHANGE: neighbor 10.167.166.70 down",
  "criticality": "high",      # Added by Logstash
  "device_role": "core"       # Added by Logstash
}

# Extracted Features (12 numerical values)
features = {
    'severity': 3,              # CRITICAL=3, ERROR=2, WARNING=1, INFO=0
    'event_hash': 742,          # Hash of "BGP_DOWN" mod 1000
    'criticality': 2,           # high=2, medium=1, low=0
    'device_role': 2,           # core=2, distribution=1, edge=0
    'hour_of_day': 3,           # 3 AM
    'day_of_week': 4,           # Friday (0=Monday, 6=Sunday)
    'message_length': 53,       # Length of message string
    'has_error_keyword': 1,     # 1 if message contains "error"/"fail"/"down"
    'has_interface': 0,         # 1 if log mentions interface
    'has_cpu_data': 0,          # 1 if CPU metrics present
    'has_bgp_data': 1,          # 1 if BGP neighbor present
    'has_auth_data': 0          # 1 if auth username present
}
```

### Feature Mapping Tables

| Feature | Mapping | Example Values |
|---------|---------|----------------|
| **severity** | INFO=0, WARNING=1, ERROR=2, CRITICAL=3 | `"CRITICAL"` → `3` |
| **event_hash** | `hash(event_type) % 1000` | `"BGP_DOWN"` → `742` |
| **criticality** | low=0, medium=1, high=2 | `"high"` → `2` |
| **device_role** | edge=0, dist=1, core=2 | `"core"` → `2` |
| **hour_of_day** | 0-23 | `"3:14 AM"` → `3` |
| **day_of_week** | Monday=0, Sunday=6 | `Friday` → `4` |

---

## Training Process 🏋️

### Step 1: Collect Training Data

The model needs at least **50 samples** before it can train (configurable):

```python
# Buffer accumulates features from logs
feature_buffer = [
    [0, 123, 1, 1, 9, 0, 45, 0, 0, 0, 0, 0],  # Normal: INFO log at 9 AM
    [1, 456, 1, 1, 10, 0, 52, 0, 1, 0, 0, 0], # Normal: WARNING with interface
    [3, 742, 2, 2, 3, 4, 53, 1, 0, 0, 1, 0],  # Anomaly: CRITICAL BGP at 3 AM
    # ... 47 more samples ...
]

# When buffer reaches 50+ samples, training begins
if len(feature_buffer) >= 50:
    train_model()
```

### Step 2: Feature Scaling (Normalization)

Features have different scales (severity: 0-3, hour: 0-23), so we normalize:

```python
# Original features
X = [[3, 742, 2, 2, 3, 4, 53, 1, 0, 0, 1, 0]]

# Standardized (mean=0, std=1)
X_scaled = StandardScaler().fit_transform(X)
# Result: [[2.1, 0.8, 1.5, 1.5, -1.2, 0.3, 0.6, 0.9, -0.4, -0.4, 0.9, -0.4]]
```

**Why?** So large values (like `event_hash=742`) don't dominate small values (like `severity=3`).

### Step 3: Build 100 Isolation Trees

The model creates 100 random trees (configurable):

```
Tree 1:                  Tree 2:                  Tree 100:
─────────                ─────────                ─────────
Split 1: hour < 12?      Split 1: severity < 2?   Split 1: criticality < 1?
   ├─ Yes: ...              ├─ Yes: ...              ├─ Yes: ...
   └─ No:                   └─ No:                   └─ No:
      Split 2: bgp=1?          Split 2: role=2?         Split 2: hour < 8?
         ├─ Yes: ANOMALY!         ├─ Yes: ...             ├─ Yes: ANOMALY!
         └─ No: ...               └─ No: ...              └─ No: ...
```

Each tree learns different patterns!

### Step 4: Calculate Average Path Length

For each sample, we measure how many splits it took to isolate:

```
Sample #1 (Normal INFO log):
  Tree 1: 8 splits
  Tree 2: 7 splits
  ...
  Tree 100: 9 splits
  Average: 8.2 splits (hard to isolate = NORMAL)

Sample #2 (CRITICAL BGP at 3 AM):
  Tree 1: 2 splits ✓ (Found quickly!)
  Tree 2: 3 splits ✓
  ...
  Tree 100: 2 splits ✓
  Average: 2.5 splits (easy to isolate = ANOMALY!)
```

---

## Detection Process 🎯

### Step 1: New Log Arrives

```python
# New log from core-router-02
new_log = {
    "severity": "CRITICAL",
    "event_type": "BGP_DOWN",
    "device_id": "core-router-02",
    "criticality": "high",
    "device_role": "core",
    "timestamp": "May 16 03:14:04",
    # ... more fields ...
}
```

### Step 2: Extract Features

```python
features = extract_features(new_log)
# Result: [3, 742, 2, 2, 3, 4, 53, 1, 0, 0, 1, 0]
```

### Step 3: Scale Features

```python
X_scaled = scaler.transform([[3, 742, 2, 2, 3, 4, 53, 1, 0, 0, 1, 0]])
# Result: [[2.1, 0.8, 1.5, 1.5, -1.2, 0.3, 0.6, 0.9, -0.4, -0.4, 0.9, -0.4]]
```

### Step 4: Run Through All 100 Trees

```python
# Each tree tries to isolate the sample
path_lengths = []
for tree in isolation_forest.estimators_:
    depth = tree.predict_path_length(X_scaled)
    path_lengths.append(depth)

# Average path length
avg_path_length = mean(path_lengths)  # e.g., 2.8
```

### Step 5: Calculate Anomaly Score

```python
# Normalize path length to score (range: -1 to 0)
# Formula: score = 2^(-avg_path / expected_path)
# Then convert to log scale: score = -log2(normalized_score)

anomaly_score = model.score_samples(X_scaled)[0]
# Result: -0.702
```

**Score Interpretation**:
- **Close to 0** (e.g., -0.1): Normal (took many splits)
- **Negative** (e.g., -0.7): Anomaly (took few splits)
- **Very negative** (e.g., -1.0): Strong anomaly

### Step 6: Make Decision

```python
# Model prediction
prediction = model.predict(X_scaled)[0]  # -1 = anomaly, 1 = normal

if prediction == -1:
    # Calculate confidence (0 to 1)
    confidence = abs(anomaly_score) * 2  # -0.702 → 1.404 → capped at 1.0
    confidence = min(1.0, confidence)    # Result: 1.0 (100% confident)
    
    return {
        'anomaly_type': 'ML_DETECTED_ANOMALY',
        'severity': 'MEDIUM',  # High confidence → MEDIUM severity
        'confidence': 1.0,
        'anomaly_score': -0.702,
        'details': 'ML model detected unusual pattern (confidence: 100.00%)'
    }
```

---

## Real Example Walkthrough 🎬

### Scenario: BGP_DOWN at 3 AM on Critical Router

Let's trace **exactly** what happens when your BGP failure log arrives:

#### **Input Log**
```json
{
  "timestamp": "May 16 03:14:04",
  "device_id": "core-router-02",
  "device_type": "router",
  "severity": "CRITICAL",
  "event_type": "BGP_DOWN",
  "neighbor": "10.167.166.70",
  "message": "%BGP-5-ADJCHANGE: neighbor 10.167.166.70 down",
  "device_role": "core",
  "criticality": "high"
}
```

#### **Step 1: Feature Extraction**

```python
features = {
    'severity': 3,          # CRITICAL → highest value
    'event_hash': 742,      # hash("BGP_DOWN") % 1000
    'criticality': 2,       # high → highest value
    'device_role': 2,       # core → highest value
    'hour_of_day': 3,       # 3:14 AM → unusual time!
    'day_of_week': 4,       # Friday
    'message_length': 53,   # Length of message
    'has_error_keyword': 1, # "down" in message
    'has_interface': 0,     # No interface mentioned
    'has_cpu_data': 0,      # No CPU metrics
    'has_bgp_data': 1,      # BGP neighbor present
    'has_auth_data': 0      # No auth data
}

# Feature vector (what ML model sees)
X = [3, 742, 2, 2, 3, 4, 53, 1, 0, 0, 1, 0]
```

#### **Step 2: Feature Scaling**

```python
# Model was trained on logs that typically look like:
# - Severity: mostly 0-1 (INFO/WARNING)
# - Hour: mostly 9-17 (business hours)
# - Criticality: mostly 1 (medium)

# Our log after scaling (relative to training data)
X_scaled = scaler.transform([X])
# Result (approximate):
# [+2.1,  # Severity: 3 is 2.1 std devs above mean
#  +0.8,  # Event hash: slightly above average
#  +1.5,  # Criticality: 2 is 1.5 std devs above mean
#  +1.5,  # Device role: core is 1.5 std devs above mean
#  -1.2,  # Hour: 3 AM is 1.2 std devs BELOW mean (unusual!)
#  +0.3,  # Day of week: Friday is slightly above average
#  +0.6,  # Message length: slightly longer than average
#  +0.9,  # Has error keyword: present
#  -0.4,  # Has interface: not present
#  -0.4,  # Has CPU data: not present
#  +0.9,  # Has BGP data: present
#  -0.4]  # Has auth data: not present
```

**Key Observations**:
- ⚠️ **High severity** (+2.1) - unusual
- ⚠️ **3 AM timestamp** (-1.2) - very unusual!
- ⚠️ **High criticality** (+1.5) - unusual
- ⚠️ **Core router** (+1.5) - critical device
- ✅ **BGP data** (+0.9) - relevant for BGP event

#### **Step 3: Isolation Forest Scoring**

The model runs this log through 100 trees:

```
Tree 1:
├─ Split 1: hour_of_day < 8?  YES (3 < 8)
│  └─ Split 2: severity > 2?  YES (3 > 2)
│     └─ ISOLATED! (2 splits)

Tree 2:
├─ Split 1: criticality > 1?  YES (2 > 1)
│  └─ Split 2: has_bgp_data = 1?  YES
│     └─ ISOLATED! (2 splits)

Tree 3:
├─ Split 1: severity > 1?  YES (3 > 1)
│  └─ Split 2: hour_of_day < 6?  YES (3 < 6)
│     └─ Split 3: device_role = 2?  YES
│        └─ ISOLATED! (3 splits)

...

Tree 100:
├─ Split 1: hour_of_day < 10?  YES (3 < 10)
│  └─ Split 2: has_error_keyword = 1?  YES
│     └─ ISOLATED! (2 splits)

Average across 100 trees: 2.8 splits
```

**Compare to Normal Log** (INFO at 10 AM):
```
Average: 8.5 splits (much harder to isolate)
```

#### **Step 4: Anomaly Score Calculation**

```python
# Isolation Forest converts path length to score
# Short path → negative score

avg_path_length = 2.8
expected_path_length = 8.5  # Average for normal logs

# Simplified formula (actual uses c(n) normalization):
anomaly_score = -log2(avg_path_length / expected_path_length)
                = -log2(2.8 / 8.5)
                = -log2(0.329)
                = -1.60

# sklearn normalizes this to roughly -0.702
anomaly_score = -0.702  # NEGATIVE = ANOMALY!
```

#### **Step 5: Prediction**

```python
# Model classifies as anomaly
prediction = model.predict(X_scaled)  # Returns: -1

if prediction == -1:
    # Convert score to confidence
    confidence = abs(anomaly_score) * 2
    confidence = min(1.0, abs(-0.702) * 2)
    confidence = min(1.0, 1.404)
    confidence = 1.0  # 100% confident it's an anomaly!
    
    result = {
        'anomaly_type': 'ML_DETECTED_ANOMALY',
        'severity': 'MEDIUM',
        'device_id': 'core-router-02',
        'event_type': 'BGP_DOWN',
        'detection_method': 'ml',
        'model': 'isolation_forest',
        'confidence': 1.0,
        'anomaly_score': -0.702,
        'details': 'ML model detected unusual pattern (confidence: 100.00%)'
    }
```

#### **Output**

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
  "features": {
    "severity": "CRITICAL",
    "event_type": "BGP_DOWN",
    "criticality": "high",
    "time_context": "3:00 on day 4"
  },
  "timestamp": "2026-05-16T03:14:04.541775",
  "source_log": { ... }
}
```

---

## Understanding Scores 📊

### Score Ranges Explained

| Anomaly Score | Meaning | Example | Confidence |
|---------------|---------|---------|------------|
| **-0.1 to 0** | Normal | INFO log at 10 AM | 0% - 20% |
| **-0.3 to -0.1** | Suspicious | WARNING at 2 AM | 20% - 60% |
| **-0.5 to -0.3** | Likely Anomaly | ERROR at midnight | 60% - 100% |
| **< -0.5** | Strong Anomaly | CRITICAL BGP at 3 AM | 100% |

### Visual Representation

```
Score Scale:
                          
NORMAL    SUSPICIOUS    ANOMALY    STRONG
  │            │           │       ANOMALY
  │            │           │          │
  0          -0.3        -0.5      -0.702
  └────────────┴───────────┴──────────┘
     INFO        WARNING    ERROR    CRITICAL
   at 10AM       at 2AM    at 12AM   BGP 3AM
```

### Real Examples from Your System

| Log | Anomaly Score | Why? |
|-----|---------------|------|
| `INFO: STP_STATE_CHANGE at 10 AM` | **-0.15** | Common event, business hours |
| `WARNING: HIGH_CPU (85%) at 2 PM` | **-0.35** | Unusual but not rare |
| `ERROR: INTERFACE_DOWN at midnight` | **-0.52** | Rare time + severity |
| `CRITICAL: BGP_DOWN at 3 AM` | **-0.702** | Very rare combination! |

---

## Why Anomalies Were Detected 🔎

### Your BGP Test Results

From your test, **9 out of 10 logs** were flagged as anomalies. Here's why:

| Log | Score | Why Anomaly? |
|-----|-------|--------------|
| STP_STATE_CHANGE (3x) | -0.7x | **Rare event type** + multiple occurrences |
| HIGH_CPU (3x) | -0.68 to -0.73 | **High CPU + unusual time** (3 AM) |
| BGP_IDLE | -0.74 | **Rare event + core router** |
| BGP_DOWN | -0.702 | **Critical severity + 3 AM + core router** |

### Why 90% Detection Rate?

**Problem: Over-sensitive model**

1. **Small training set** (97 samples):
   - Model hasn't seen enough "normal" patterns
   - Treats most patterns as rare/unusual

2. **High diversity** in logs:
   - 10 different event types in one batch
   - Model trained on mostly routine logs (STP, CPU)

3. **Contamination parameter** set to 0.1 (10%):
   - Model expects 10% of logs to be anomalies
   - But seeing 90% unusual patterns → flags them all!

### Solution: Tune Model Parameters

```yaml
# services/anomaly-detector/config.yaml
detection:
  isolation_forest:
    contamination: 0.05      # Lower to 5% (from 10%)
    n_estimators: 100        # Keep at 100 trees
    min_samples: 100         # Increase from 50 → better training
    train_interval_minutes: 60
```

**Effect**: Model becomes less sensitive, requires more evidence before flagging anomaly.

---

## Key Takeaways 💡

### ✅ Isolation Forest Strengths

1. **No labeled data needed**: Learns from normal patterns automatically
2. **Fast detection**: ~10ms per log
3. **Handles high dimensions**: 12 features easily processed
4. **Adaptive**: Retrains every hour with new data

### ⚠️ Current Limitations

1. **Small training set**: 97 samples insufficient for diverse log types
2. **Over-detection**: 90% of logs flagged (should be 5-10%)
3. **No event-specific thresholds**: Treats all events equally
4. **Time sensitivity**: Flags legitimate off-hours maintenance

### 🎯 Best Practices

1. **Collect more training data**: Aim for 500-1000 samples minimum
2. **Tune contamination**: Start at 0.05 (5% anomaly expectation)
3. **Combine with rules**: Use rule-based detection for known patterns
4. **Monitor false positives**: Adjust thresholds based on feedback

---

## Code Reference 📝

**Full Implementation**: [`services/anomaly-detector/detectors/ml_based.py`](../services/anomaly-detector/detectors/ml_based.py)

**Key Functions**:
- `extract_features()`: Lines 48-109 - Feature extraction logic
- `train()`: Lines 123-156 - Model training process
- `predict()`: Lines 158-220 - Anomaly detection logic

**Configuration**: [`services/anomaly-detector/config.yaml`](../services/anomaly-detector/config.yaml)

---

## Further Reading 📚

- [Isolation Forest Paper](https://cs.nju.edu.cn/zhouzh/zhouzh.files/publication/icdm08b.pdf) - Original research paper
- [Scikit-learn IsolationForest](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html) - Official documentation
- [FLOW_ANALYSIS_EXAMPLE.md](FLOW_ANALYSIS_EXAMPLE.md) - End-to-end system flow

---

## Questions? 🤔

**Q: Why negative scores?**
**A**: Sklearn's implementation uses negative values for anomalies (based on path length formula). More negative = stronger anomaly.

**Q: Why 100% confidence but only MEDIUM severity?**
**A**: High confidence means "definitely unusual", but severity depends on impact. ML can't assess business impact - that's what correlation and LLM diagnosis do!

**Q: How to reduce false positives?**
**A**: 
1. Lower `contamination` parameter
2. Increase training data
3. Add event-specific rules
4. Filter routine maintenance logs
