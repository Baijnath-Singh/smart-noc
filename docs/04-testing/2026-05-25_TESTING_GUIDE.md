# Smart NOC - Anomaly Detection Testing & Demo Guide

## 🎯 Overview

This guide shows you how to send logs, trigger anomaly detection, and verify everything works end-to-end.

---

## 📊 Architecture Reminder

```
Log Generator → Kafka → Logstash → Elasticsearch
                  ↓
           Anomaly Detector (AI Agent)
                  ↓
           Kafka (anomalies topic) → Logstash → Elasticsearch
                                                      ↓
                                                  Grafana Dashboard
```

---

## 🧪 Test Scenarios

### **Scenario 1: Normal Logs (No Anomalies)**

Generate regular network events that should NOT trigger anomalies.

```bash
cd services/log-generator
source ../../venv/bin/activate

# Generate 50 normal logs over 10 seconds (5 logs/sec)
python generate_logs.py --rate 5 --duration 10
```

**What happens:**
- ✅ Logs go to Elasticsearch (network-logs index)
- ✅ Anomaly detector processes them
- ✅ ML model learns from them (training data)
- ❌ No anomalies detected (normal patterns)

**Verification:**
```bash
# Check network logs
curl -s 'http://localhost:9200/network-logs-*/_count' | jq

# Check anomaly detector logs
docker compose logs --tail=20 anomaly-detector | grep "processed"
```

---

### **Scenario 2: Interface Flapping (Rule-Based Detection)**

**What is it:** Network interface goes UP/DOWN rapidly (hardware/cable issue)

**Detection:** Rule-based detector triggers after 5 flaps in 5 minutes

```bash
# Generate 6 interface flaps (triggers rule-based detector)
python generate_scenarios.py --scenario flapping --count 6
```

**What you'll see:**

1. **In Terminal** (after 12 seconds):
   ```
   ✅ Scenario complete: 6 interface flaps sent
   ```

2. **In Anomaly Detector Logs**:
   ```bash
   docker compose logs --tail=20 anomaly-detector | grep "flapping"
   ```
   
   Expected output:
   ```
   WARNING | Interface flapping detected: core-router-01 GigabitEthernet0/1 (5 events)
   INFO    | Anomaly published: INTERFACE_FLAPPING - core-router-01
   ```

3. **In Grafana Dashboard** (refresh after 5-10 seconds):
   - Total Anomalies: +1
   - Rule-Based Detections: +1
   - Anomaly Type pie chart shows "INTERFACE_FLAPPING"
   - Recent Anomalies table shows new entry

**Verification Commands:**
```bash
# Check if anomaly was published to Kafka
docker compose exec -T kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic anomalies \
  --from-beginning \
  --max-messages 1 \
  --timeout-ms 5000 | jq '.anomaly_type'

# Check Elasticsearch anomalies count
curl -s 'http://localhost:9200/anomalies-*/_count' | jq '.count'
```

---

### **Scenario 3: Authentication Brute Force (Rule-Based Detection)**

**What is it:** Multiple failed login attempts from same IP (security attack)

**Detection:** Rule-based detector triggers after 10 failures in 2 minutes

```bash
# Generate 12 failed login attempts (triggers rule-based detector)
python generate_scenarios.py --scenario brute-force --count 12
```

**What you'll see:**

1. **In Terminal** (after 12 seconds):
   ```
   ✅ Scenario complete: 12 brute force attempts sent
   ```

2. **In Anomaly Detector Logs**:
   ```bash
   docker compose logs --tail=20 anomaly-detector | grep "brute"
   ```
   
   Expected output:
   ```
   WARNING | Auth brute force detected: 192.168.100.50 → dist-switch-02 (10 attempts)
   INFO    | Anomaly published: AUTH_BRUTE_FORCE - dist-switch-02
   ```

3. **In Grafana Dashboard**:
   - Total Anomalies: +1
   - Rule-Based Detections: +1
   - Anomaly Type shows "AUTH_BRUTE_FORCE"
   - Top Devices shows "dist-switch-02"

---

### **Scenario 4: ML Detection (AI-Based Pattern Recognition)**

**What is it:** Unusual patterns that don't match rule-based detectors (AI finds them!)

**Detection:** Isolation Forest ML model detects unusual combinations of:
- Event type at unusual time
- Multiple devices with same issue simultaneously
- Unusual severity + event type combinations

```bash
# First, ensure ML model is trained (needs 50+ samples)
# Check current training status
docker compose logs --tail=50 anomaly-detector | grep -i "trained"

# If "Trained: False", generate training data
python generate_logs.py --rate 50 --duration 5
# Wait 20 seconds for training...

# Now generate mixed events to trigger ML anomalies
python generate_logs.py --rate 30 --duration 10
```

**What you'll see:**

1. **ML Training** (if not already trained):
   ```bash
   docker compose logs --tail=100 anomaly-detector | grep -E "Training|trained"
   ```
   
   Expected output:
   ```
   SUCCESS | Isolation Forest trained on 50 samples
   ```

2. **ML Detections**:
   ```bash
   docker compose logs --tail=30 anomaly-detector | grep "ML anomaly"
   ```
   
   Expected output:
   ```
   WARNING | ML anomaly detected: core-router-03 - BGP_IDLE (confidence: 0.00)
   WARNING | ML anomaly detected: dist-switch-01 - HIGH_CPU (confidence: 0.00)
   WARNING | ML anomaly detected: edge-firewall-02 - INTERFACE_DOWN (confidence: 0.00)
   ```

3. **In Grafana Dashboard**:
   - Total Anomalies: increases significantly
   - ML-Based Detections: increases
   - Anomaly Type shows "ML_DETECTED_ANOMALY"
   - Detection Method pie chart shows ML vs Rule split

**Why ML detects these:**
- BGP_IDLE at unusual hour (middle of night)
- Multiple HIGH_CPU simultaneously across devices
- Unusual combinations of events that don't match rule patterns

---

### **Scenario 5: High CPU Sustained (Rule-Based Detection)**

**What is it:** CPU usage >80% for extended period (10+ minutes)

**Detection:** Rule-based detector tracks sustained high CPU

```bash
# Generate sustained high CPU events
python generate_scenarios.py --scenario high-cpu --count 15
```

**Note:** This scenario requires CPU to stay high for 10 minutes continuously, so it takes time to trigger. For a quick demo, use flapping or brute-force instead!

---

## 📈 Full Demo Flow (Team Demonstration)

### **Part 1: Show the Working System** (5 minutes)

1. **Open monitoring tools in browser tabs:**
   - Tab 1: Grafana Dashboard → http://localhost:3000
   - Tab 2: Kafka UI → http://localhost:8080 (show topics: network-logs, anomalies)
   - Tab 3: Kibana (optional) → Check Elasticsearch data

2. **Show current state:**
   ```bash
   # Show all services running
   docker compose ps
   
   # Show anomaly detector agent is alive
   docker compose logs --tail=10 anomaly-detector
   ```

3. **Explain the architecture:**
   - Point to each service in `docker compose ps` output
   - Explain: "Logs go to Kafka → Logstash enriches → Elasticsearch stores"
   - Show: "AI Agent watches Kafka, detects anomalies, publishes back to Kafka"

---

### **Part 2: Trigger Interface Flapping** (2 minutes)

1. **In terminal:**
   ```bash
   cd services/log-generator
   source ../../venv/bin/activate
   python generate_scenarios.py --scenario flapping --count 6
   ```

2. **Show detection in real-time:**
   ```bash
   # In another terminal (split screen)
   docker compose logs -f anomaly-detector
   ```
   
   Point out:
   - "Watch for: WARNING | Interface flapping detected"
   - "The rule detected 5 UP/DOWN events within 5 minutes"

3. **Show in Grafana:**
   - Refresh dashboard (auto-refreshes every 5 seconds)
   - Point to: "Total Anomalies increased by 1"
   - Point to: "Rule-Based Detections increased"
   - Show in table: "Recent Anomalies - INTERFACE_FLAPPING"

---

### **Part 3: Trigger Brute Force Attack** (2 minutes)

1. **Generate attack:**
   ```bash
   python generate_scenarios.py --scenario brute-force --count 12
   ```

2. **Show detection:**
   ```bash
   docker compose logs --tail=20 anomaly-detector | grep "brute"
   ```

3. **Show in Grafana:**
   - Point to: "AUTH_BRUTE_FORCE in pie chart"
   - Show: "dist-switch-02 now appears in Top Devices"
   - Explain: "Rule detected 10+ failed logins from same IP in 2 minutes"

---

### **Part 4: AI Detection (The Magic!)** (5 minutes)

1. **Check if ML model is trained:**
   ```bash
   docker compose logs anomaly-detector | grep -i "trained on"
   ```
   
   If not trained:
   ```bash
   python generate_logs.py --rate 50 --duration 5
   # Wait 20 seconds
   ```

2. **Generate mixed events:**
   ```bash
   python generate_logs.py --rate 30 --duration 10
   ```

3. **Show AI detections:**
   ```bash
   docker compose logs --tail=50 anomaly-detector | grep "ML anomaly detected"
   ```

4. **Explain to team:**
   - "These anomalies have NO rules defined!"
   - "The AI (Isolation Forest) learned what 'normal' looks like"
   - "It detected unusual patterns automatically"
   - Examples:
     - "BGP_IDLE at 3 AM is weird (usually happens during business hours)"
     - "7 devices with HIGH_CPU simultaneously is unusual"

5. **Show in Grafana:**
   - Point to ML-Based Detections count
   - Show Detection Method pie chart split
   - Explain: "Blue = Rules we wrote, Purple = AI discovered"

---

### **Part 5: End-to-End Verification** (3 minutes)

Show the full data flow:

```bash
# 1. Count logs in Kafka
curl -s http://localhost:8080/api/clusters/smart-noc-cluster/topics/network-logs | jq

# 2. Count logs in Elasticsearch
curl -s 'http://localhost:9200/network-logs-*/_count' | jq

# 3. Count detected anomalies in Elasticsearch
curl -s 'http://localhost:9200/anomalies-*/_count' | jq

# 4. Show anomaly detector statistics
docker compose logs --tail=100 anomaly-detector | grep "STATISTICS" -A 10
```

Sample output explanation:
```
Logs processed: 500
Total anomalies: 15
  ├─ Rule-based: 3 (flapping, brute force)
  └─ ML-based: 12 (AI discovered)

ML Model: IsolationForest
  ├─ Trained: True
  ├─ Training samples: 250
  └─ Last training: 2026-04-24 17:45:00
```

---

## 🔍 Troubleshooting Commands

### Check if services are running:
```bash
docker compose ps
```

Expected: All services show "Up (healthy)" or "Up"

### Check anomaly detector logs:
```bash
docker compose logs --tail=50 anomaly-detector
```

Look for: "SUCCESS | Anomaly Detection Service running!"

### Check if logs are flowing:
```bash
# Count logs in Kafka
docker compose exec -T kafka kafka-run-class kafka.tools.GetOffsetShell \
  --broker-list localhost:9092 \
  --topic network-logs

# Count in Elasticsearch
curl -s 'http://localhost:9200/network-logs-*/_count' | jq
```

### Check ML model status:
```bash
docker compose logs anomaly-detector | grep -E "Trained|Training samples"
```

### View recent anomalies:
```bash
curl -s 'http://localhost:9200/anomalies-*/_search?size=5&sort=@timestamp:desc' | jq '.hits.hits[]._source | {time: .timestamp, device: .device_id, type: .anomaly_type, method: .detection_method}'
```

### Restart anomaly detector if needed:
```bash
docker compose restart anomaly-detector
# Wait 10 seconds
docker compose logs --tail=20 anomaly-detector
```

---

## 💡 Key Talking Points for Demo

### **1. Rule-Based Detection (Traditional Approach)**
- ✅ "We defined rules based on known patterns"
- ✅ "Interface flapping: >5 state changes in 5 minutes"
- ✅ "Brute force: >10 auth failures in 2 minutes"
- ✅ "100% confidence when detected (deterministic)"
- ❌ "Only catches what we thought of in advance"

### **2. ML-Based Detection (AI Approach)**
- ✅ "Isolation Forest learns from normal behavior"
- ✅ "Detects NEW patterns we never thought of"
- ✅ "Finds 'odd one out' - rare combinations"
- ✅ "Auto-trains after 50 samples, retrains every hour"
- ✅ "Complements rule-based (hybrid approach)"

### **3. Why This Matters**
- **Reduced Alert Fatigue**: Two-stage detection (rules + AI)
- **Early Detection**: Catches issues before they become critical
- **Unknown Unknowns**: ML finds anomalies we didn't anticipate
- **Scalable**: Works across 100s of devices
- **Real-time**: Processes logs as they arrive

### **4. What's Next (Pipeline)**
- ✅ Phase 1: Log ingestion + enrichment (DONE)
- ✅ Phase 2: AI-powered anomaly detection (DONE)
- 🚧 Phase 3: Correlation engine (group related anomalies)
- 🚧 Phase 4: LLM diagnosis (GPT explains root cause)
- 🚧 Phase 5: Automated remediation (Ansible playbooks)
- 🚧 Phase 6: Learning + memory (store solutions)

---

## 📊 Demo Checklist

Before presenting to team:

- [ ] All Docker services running (`docker compose ps`)
- [ ] Grafana dashboard loads (http://localhost:3000)
- [ ] Anomaly detector shows "running" status
- [ ] ML model is trained (50+ samples)
- [ ] Test scenarios work:
  - [ ] Interface flapping detection
  - [ ] Brute force detection
  - [ ] ML detections visible
- [ ] Grafana shows real-time updates
- [ ] Know how to check logs (`docker compose logs`)
- [ ] Can explain rule vs ML detection
- [ ] Can run all commands above confidently

---

## 🎯 Quick Test Script

Run this complete test sequence (takes ~2 minutes):

```bash
#!/bin/bash
cd services/log-generator
source ../../venv/bin/activate

echo "🔥 Test 1: Interface Flapping"
python generate_scenarios.py --scenario flapping --count 6
sleep 5

echo "🔥 Test 2: Auth Brute Force"
python generate_scenarios.py --scenario brute-force --count 12
sleep 5

echo "🔥 Test 3: Mixed Events (ML Detection)"
python generate_logs.py --rate 30 --duration 10
sleep 5

echo "✅ All scenarios complete!"
echo "📊 Check Grafana dashboard: http://localhost:3000"
echo "🔍 View detections: docker compose logs --tail=50 anomaly-detector"
```

Save this as `test_all.sh` and run: `bash test_all.sh`

---

## 📝 Summary

You now have:
- ✅ **4 test scenarios** to demonstrate different detections
- ✅ **Verification commands** to prove it's working
- ✅ **Full demo flow** for team presentation
- ✅ **Troubleshooting commands** if something goes wrong
- ✅ **Key talking points** to explain the value

**Next Phase**: After you're comfortable with testing, we'll build Phase 3: Correlation Engine to group related anomalies into incidents! 🚀
