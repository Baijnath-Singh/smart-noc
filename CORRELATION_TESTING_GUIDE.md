# 🧪 Smart NOC - Correlation Engine Testing Guide

## 📋 Overview

This guide provides comprehensive testing scenarios for Phase 3: Incident Correlation Engine. Test various correlation patterns to validate time-based and pattern-based incident detection.

---

## 🎯 Testing Objectives

- ✅ Validate **Pattern-Based Correlation** (4 patterns: DEVICE_FAILURE, NETWORK_PERFORMANCE, SECURITY_BREACH, CONNECTIVITY_ISSUE)
- ✅ Validate **Time-Based Correlation** (5-minute sliding window)
- ✅ Verify **Incident Severity Calculation** (CRITICAL/HIGH/MEDIUM/LOW)
- ✅ Verify **Impact Scoring** (device count + anomaly count + severity)
- ✅ Test **Database Persistence** (PostgreSQL incident storage)
- ✅ Test **Elasticsearch Indexing** (searchable incidents)

---

## 🔧 Quick Start Commands

### Check System Status
```bash
# From project root: C:\Users\baisingh\ng-iam\smart-noc
cd /mnt/c/Users/baisingh/ng-iam/smart-noc

# Check all services
docker compose ps

# Check correlation engine logs
docker compose logs -f correlation-engine

# Check incidents in PostgreSQL
docker compose exec postgres psql -U noc_admin -d smart_noc -c "SELECT incident_number, incident_type, severity, anomaly_count, affected_device_count FROM incidents ORDER BY created_at DESC LIMIT 10;"

# Check incidents in Elasticsearch
curl -s 'http://localhost:9200/incidents-*/_count' | jq

# View recent incidents
curl -s 'http://localhost:9200/incidents-*/_search?size=5&sort=created_at:desc' | jq '.hits.hits[]._source | {incident_number, incident_type, severity, affected_devices, correlation_method}'
```

---

## 📝 Test Scenarios

### **🔴 Scenario 1: DEVICE_FAILURE Pattern**

**Pattern:** Same device with 3+ anomalies of different types within 5 minutes

**Command:**
```bash
cd services/log-generator
source ../../venv/bin/activate

# Generate device failure scenario (same device, multiple anomaly types)
python generate_scenarios.py --scenario device-failure --device dist-switch-02 --count 5
```

**Expected Behavior:**
- ✅ Correlation engine detects 5 anomalies from same device (dist-switch-02)
- ✅ Creates **DEVICE_FAILURE** incident (severity: HIGH or CRITICAL)
- ✅ Incident groups all 5 anomalies
- ✅ `affected_device_count: 1`, `anomaly_count: 5`

**Verification:**
```bash
# Check correlation engine logs (should show "DEVICE_FAILURE pattern detected")
docker compose logs correlation-engine | grep -i "device_failure"

# Query PostgreSQL for incident
docker compose exec postgres psql -U noc_admin -d smart_noc -c "SELECT incident_number, incident_type, severity, primary_device, anomaly_count FROM incidents WHERE incident_type='DEVICE_FAILURE' ORDER BY created_at DESC LIMIT 1;"

# Check Elasticsearch
curl -s 'http://localhost:9200/incidents-*/_search?q=incident_type:DEVICE_FAILURE&size=1&sort=created_at:desc' | jq '.hits.hits[0]._source | {incident_number, severity, primary_device, anomaly_count}'
```

**Sample Output:**
```
Incident #105: DEVICE_FAILURE
- Severity: HIGH
- Primary Device: dist-switch-02
- Anomaly Count: 5
- Correlation Method: PATTERN_BASED
```

---

### **🔴 Scenario 2: NETWORK_PERFORMANCE Pattern**

**Pattern:** HIGH_CPU/HIGH_MEMORY/PACKET_LOSS on 2+ devices within 5 minutes

**Command:**
```bash
cd services/log-generator
source ../../venv/bin/activate

# Generate high CPU on multiple devices
python generate_scenarios.py --scenario high-cpu --count 8

# Wait 2 seconds, then add high memory
sleep 2
python generate_scenarios.py --scenario high-memory --count 6
```

**Expected Behavior:**
- ✅ Correlation engine detects HIGH_CPU + HIGH_MEMORY anomalies on multiple devices
- ✅ Creates **NETWORK_PERFORMANCE** incident (severity based on anomaly severities)
- ✅ Groups performance anomalies across devices
- ✅ `affected_device_count: ≥2`, `anomaly_count: 14`

**Verification:**
```bash
# Check logs
docker compose logs correlation-engine | grep -i "network_performance"

# Query incident
docker compose exec postgres psql -U noc_admin -d smart_noc -c "SELECT incident_number, incident_type, severity, affected_device_count, anomaly_count FROM incidents WHERE incident_type='NETWORK_PERFORMANCE' ORDER BY created_at DESC LIMIT 1;"
```

**Sample Output:**
```
Incident #106: NETWORK_PERFORMANCE
- Severity: HIGH
- Affected Devices: 4
- Anomaly Count: 14
- Correlation Method: PATTERN_BASED
```

---

### **🔴 Scenario 3: SECURITY_BREACH Pattern**

**Pattern:** AUTH_FAILURE/AUTH_BRUTE_FORCE with 2+ occurrences within 5 minutes

**Command:**
```bash
cd services/log-generator
source ../../venv/bin/activate

# Generate brute force attack scenario
python generate_scenarios.py --scenario brute-force --count 15
```

**Expected Behavior:**
- ✅ Correlation engine detects 15 AUTH_FAILURE anomalies
- ✅ Creates **SECURITY_BREACH** incident (severity: HIGH)
- ✅ Groups authentication failure anomalies
- ✅ Device: dist-switch-02 (typical target in scenarios)

**Verification:**
```bash
# Check logs
docker compose logs correlation-engine | grep -i "security_breach"

# Query incident
docker compose exec postgres psql -U noc_admin -d smart_noc -c "SELECT incident_number, incident_type, severity, primary_device, anomaly_count FROM incidents WHERE incident_type='SECURITY_BREACH' ORDER BY created_at DESC LIMIT 1;"
```

**Sample Output:**
```
Incident #107: SECURITY_BREACH
- Severity: HIGH
- Primary Device: dist-switch-02
- Anomaly Count: 15
- Correlation Method: PATTERN_BASED
```

---

### **🔴 Scenario 4: CONNECTIVITY_ISSUE Pattern**

**Pattern:** INTERFACE_DOWN/INTERFACE_FLAPPING/BGP_DOWN on 2+ devices within 5 minutes

**Command:**
```bash
cd services/log-generator
source ../../venv/bin/activate

# Generate interface flapping scenario
python generate_scenarios.py --scenario flapping --count 10

# Wait 1 second, add BGP instability
sleep 1
python generate_scenarios.py --scenario bgp-instability --count 8
```

**Expected Behavior:**
- ✅ Correlation engine detects INTERFACE_FLAPPING + BGP_DOWN anomalies
- ✅ Creates **CONNECTIVITY_ISSUE** incident (severity: CRITICAL or HIGH)
- ✅ Groups connectivity anomalies across devices
- ✅ `affected_device_count: ≥2`, `anomaly_count: 18`

**Verification:**
```bash
# Check logs
docker compose logs correlation-engine | grep -i "connectivity_issue"

# Query incident
docker compose exec postgres psql -U noc_admin -d smart_noc -c "SELECT incident_number, incident_type, severity, affected_device_count, anomaly_count FROM incidents WHERE incident_type='CONNECTIVITY_ISSUE' ORDER BY created_at DESC LIMIT 1;"
```

**Sample Output:**
```
Incident #108: CONNECTIVITY_ISSUE
- Severity: HIGH
- Affected Devices: 6
- Anomaly Count: 18
- Correlation Method: PATTERN_BASED
```

---

### **🔵 Scenario 5: Time-Based Correlation (Multi-Pattern)**

**Pattern:** Multiple anomaly types within 5-minute window (tests time-based grouping)

**Command:**
```bash
cd services/log-generator
source ../../venv/bin/activate

# Generate rapid sequence of different anomalies
python generate_logs.py --rate 50 --duration 10 &
sleep 2
python generate_scenarios.py --scenario high-cpu --count 5 &
sleep 2
python generate_scenarios.py --scenario brute-force --count 8 &
sleep 2
python generate_scenarios.py --scenario flapping --count 6 &
wait
```

**Expected Behavior:**
- ✅ Correlation engine buffers all anomalies in 5-minute window
- ✅ Creates **multiple incidents** based on pattern matching
- ✅ Some anomalies grouped by time proximity
- ✅ Statistics show buffer size and processing rate

**Verification:**
```bash
# Check correlation stats
docker compose logs correlation-engine | tail -50

# Count incidents created in last 5 minutes
docker compose exec postgres psql -U noc_admin -d smart_noc -c "SELECT COUNT(*) FROM incidents WHERE created_at > NOW() - INTERVAL '5 minutes';"

# View incident distribution
docker compose exec postgres psql -U noc_admin -d smart_noc -c "SELECT incident_type, COUNT(*) as count FROM incidents WHERE created_at > NOW() - INTERVAL '5 minutes' GROUP BY incident_type;"
```

**Sample Output:**
```
Incidents created in last 5 minutes: 4

Distribution:
- DEVICE_FAILURE: 2
- SECURITY_BREACH: 1
- NETWORK_PERFORMANCE: 1
```

---

### **🔵 Scenario 6: Complex Multi-Device Network Outage**

**Pattern:** Large-scale network event affecting 5+ devices with multiple anomaly types

**Command:**
```bash
cd services/log-generator
source ../../venv/bin/activate

# Simulate network-wide outage
echo "🌐 Simulating network outage across multiple devices..."

# Stage 1: Interface failures (0-30s)
python generate_scenarios.py --scenario flapping --count 12 &

# Stage 2: BGP instability (5s delay)
sleep 5
python generate_scenarios.py --scenario bgp-instability --count 10 &

# Stage 3: High CPU due to reconvergence (10s delay)
sleep 5
python generate_scenarios.py --scenario high-cpu --count 8 &

# Stage 4: Authentication failures during chaos (15s delay)
sleep 5
python generate_scenarios.py --scenario brute-force --count 6 &

wait
echo "✅ Network outage simulation complete"
```

**Expected Behavior:**
- ✅ Correlation engine creates **multiple incidents** (CONNECTIVITY_ISSUE, DEVICE_FAILURE, NETWORK_PERFORMANCE, SECURITY_BREACH)
- ✅ Severity levels vary (CRITICAL for connectivity, HIGH for others)
- ✅ Large `affected_device_count` (5-10 devices)
- ✅ High `impact_score` (50-80) due to widespread impact

**Verification:**
```bash
# View all incidents created
docker compose exec postgres psql -U noc_admin -d smart_noc -c "SELECT incident_number, incident_type, severity, affected_device_count, anomaly_count, impact_score FROM incidents WHERE created_at > NOW() - INTERVAL '2 minutes' ORDER BY impact_score DESC;"

# Check Grafana dashboard
echo "Open Grafana: http://localhost:3000/d/smart-noc-incidents (admin/admin)"
```

**Sample Output:**
```
Incident #109: CONNECTIVITY_ISSUE - CRITICAL - 8 devices - 22 anomalies - Impact: 78.5
Incident #110: DEVICE_FAILURE - HIGH - 3 devices - 5 anomalies - Impact: 52.3
Incident #111: NETWORK_PERFORMANCE - HIGH - 4 devices - 8 anomalies - Impact: 48.7
Incident #112: SECURITY_BREACH - MEDIUM - 1 device - 6 anomalies - Impact: 35.2
```

---

### **🔵 Scenario 7: Scattered Anomalies (No Correlation)**

**Pattern:** Random anomalies without correlation pattern (tests negative case)

**Command:**
```bash
cd services/log-generator
source ../../venv/bin/activate

# Generate single isolated anomalies (won't correlate)
echo "🔍 Testing non-correlated anomalies..."

python generate_logs.py --rate 20 --duration 15
```

**Expected Behavior:**
- ✅ Correlation engine processes anomalies
- ✅ **No incidents created** (anomalies don't match patterns)
- ✅ Buffer fills and cleans old entries
- ✅ Statistics show processed anomalies but zero incidents

**Verification:**
```bash
# Check correlation logs (should show "No correlations found")
docker compose logs correlation-engine | tail -20

# Verify incident count didn't increase
docker compose exec postgres psql -U noc_admin -d smart_noc -c "SELECT COUNT(*) FROM incidents WHERE created_at > NOW() - INTERVAL '2 minutes';"
```

**Sample Output:**
```
Anomalies processed: 25
Incidents created: 0
Buffer size: 12 anomalies
```

---

### **🔵 Scenario 8: Severity Escalation Test**

**Pattern:** Test incident severity calculation based on anomaly severities

**Command:**
```bash
cd services/log-generator
source ../../venv/bin/activate

# Generate critical-severity anomalies (should create CRITICAL incident)
echo "🚨 Testing CRITICAL severity escalation..."

# Method: Generate device failure with high-severity anomalies
for i in {1..5}; do
  # Send critical-level events to same device
  python -c "
import sys
sys.path.append('.')
from generate_logs import send_to_kafka
import json
from datetime import datetime

log = {
    'timestamp': datetime.utcnow().isoformat() + 'Z',
    'device_id': 'core-router-01',
    'device_type': 'router',
    'event_type': 'INTERFACE_DOWN',
    'severity': 'CRITICAL',
    'message': 'Critical interface failure - Redundancy lost',
    'interface': f'GigabitEthernet0/{i}'
}
send_to_kafka(log)
print(f'Sent CRITICAL anomaly {i}/5')
" &
  sleep 0.5
done
wait

echo "✅ Critical anomaly sequence sent"
```

**Expected Behavior:**
- ✅ All 5 anomalies have CRITICAL severity
- ✅ Correlation creates **DEVICE_FAILURE** incident with **CRITICAL** severity
- ✅ Severity calculation averages to ≥90 (CRITICAL threshold)
- ✅ High `impact_score` due to critical severity

**Verification:**
```bash
# Query most recent incident
docker compose exec postgres psql -U noc_admin -d smart_noc -c "SELECT incident_number, incident_type, severity, anomaly_count, primary_device FROM incidents ORDER BY created_at DESC LIMIT 1;"

# Verify severity is CRITICAL
curl -s 'http://localhost:9200/incidents-*/_search?size=1&sort=created_at:desc' | jq '.hits.hits[0]._source.severity'
```

**Sample Output:**
```
Incident #113: DEVICE_FAILURE
- Severity: CRITICAL ✅
- Primary Device: core-router-01
- Anomaly Count: 5
- Impact Score: 85.0
```

---

## 📊 Grafana Dashboard Verification

### Import Dashboard
1. Open Grafana: `http://localhost:3000` (admin/admin)
2. Navigate to **Dashboards** → **Import**
3. Upload: `dashboards/smart-noc-incidents-dashboard.json`
4. Select Elasticsearch datasource: `elasticsearch`
5. Click **Import**

### Dashboard Panels to Verify
- **Total Incidents** - Shows cumulative incident count
- **Active Incidents** - Shows incidents with status ACTIVE/INVESTIGATING
- **Critical Incidents** - Shows CRITICAL severity count
- **Total Devices Affected** - Sum of affected devices
- **Incident Timeline by Type** - Bar chart over time
- **Incidents by Type** - Pie chart (DEVICE_FAILURE, NETWORK_PERFORMANCE, SECURITY_BREACH, CONNECTIVITY_ISSUE)
- **Incidents by Severity** - Donut chart (CRITICAL, HIGH, MEDIUM, LOW)
- **Top 10 Devices by Incident Count** - Horizontal bar chart
- **Incident Status Distribution** - Pie chart (ACTIVE, INVESTIGATING, RESOLVED, CLOSED)
- **Correlation Method Distribution** - Donut chart (PATTERN_BASED, TIME_BASED, MULTI_METHOD)
- **Recent Incidents (Last 20)** - Table with full details

---

## 🧪 Advanced Testing

### Test 1: Correlation Accuracy (Precision/Recall)
```bash
# Expected: 4 incidents from specific patterns
cd services/log-generator
source ../../venv/bin/activate

# Generate known patterns
python generate_scenarios.py --scenario device-failure --device test-device-01 --count 5
sleep 10
python generate_scenarios.py --scenario brute-force --count 12
sleep 10
python generate_scenarios.py --scenario flapping --count 8
sleep 10
python generate_scenarios.py --scenario high-cpu --count 10

# Count incidents (should be 3-4)
docker compose exec postgres psql -U noc_admin -d smart_noc -c "SELECT COUNT(*) FROM incidents WHERE created_at > NOW() - INTERVAL '2 minutes';"
```

**Expected:** 3-4 incidents (DEVICE_FAILURE, SECURITY_BREACH, CONNECTIVITY_ISSUE, NETWORK_PERFORMANCE)

---

### Test 2: Time Window Boundary Test
```bash
# Test 5-minute correlation window boundary
cd services/log-generator
source ../../venv/bin/activate

# Generate anomalies at T=0
echo "⏱️  T=0min - Sending 3 anomalies for dist-switch-02..."
python generate_scenarios.py --scenario device-failure --device dist-switch-02 --count 3

# Wait 4 minutes (within window)
echo "⏱️  Waiting 4 minutes (within window)..."
sleep 240

# Send 2 more anomalies (should correlate with first 3)
echo "⏱️  T=4min - Sending 2 more anomalies (should correlate)..."
python generate_scenarios.py --scenario device-failure --device dist-switch-02 --count 2

# Wait 2 minutes (outside window for first batch)
echo "⏱️  Waiting 2 minutes..."
sleep 120

# Send 2 more anomalies (should NOT correlate with first 3, window expired)
echo "⏱️  T=6min - Sending 2 anomalies (window expired for first batch)..."
python generate_scenarios.py --scenario device-failure --device dist-switch-02 --count 2
```

**Expected:**
- First 3 anomalies: Buffered
- T=4min (2 more): Correlated into incident (5 anomalies total) ✅
- T=6min (2 more): May create new incident or wait for 3rd anomaly

---

### Test 3: Multi-Method Correlation
```bash
# Test both TIME_BASED and PATTERN_BASED correlation
cd services/log-generator
source ../../venv/bin/activate

# Send diverse anomalies within short window
echo "🔗 Testing multi-method correlation..."
python generate_logs.py --rate 100 --duration 10
```

**Expected:**
- Some incidents: `correlation_method: TIME_BASED` (grouped by time)
- Some incidents: `correlation_method: PATTERN_BASED` (grouped by pattern)
- Check distribution:
```bash
docker compose exec postgres psql -U noc_admin -d smart_noc -c "SELECT correlation_method, COUNT(*) FROM incidents WHERE created_at > NOW() - INTERVAL '2 minutes' GROUP BY correlation_method;"
```

---

### Test 4: Impact Score Validation
```bash
# Test impact scoring formula
cd services/log-generator
source ../../venv/bin/activate

# Scenario A: Few devices, many anomalies
echo "📈 Scenario A: 1 device, 10 anomalies..."
python generate_scenarios.py --scenario device-failure --device test-a --count 10
sleep 15

# Scenario B: Many devices, few anomalies each
echo "📈 Scenario B: 5 devices, 2 anomalies each..."
python generate_scenarios.py --scenario high-cpu --count 10  # Spreads across devices
sleep 15

# Compare impact scores
docker compose exec postgres psql -U noc_admin -d smart_noc -c "SELECT incident_number, incident_type, affected_device_count, anomaly_count, impact_score FROM incidents WHERE created_at > NOW() - INTERVAL '1 minute' ORDER BY created_at;"
```

**Expected:**
- Scenario A: Lower `affected_device_count` (1), higher `anomaly_count` (10) → Impact ~40-50
- Scenario B: Higher `affected_device_count` (5), lower `anomaly_count` (10) → Impact ~50-60

---

## 🔍 Troubleshooting

### Issue: No incidents created
**Check:**
```bash
# 1. Is correlation engine running?
docker compose ps correlation-engine

# 2. Are anomalies being detected?
curl 'http://localhost:9200/anomalies-*/_count'

# 3. Check correlation logs for errors
docker compose logs correlation-engine | grep -i error

# 4. Verify Kafka topics
docker compose exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list

# 5. Check anomaly consumption
docker compose logs correlation-engine | grep "Consumed anomaly"
```

### Issue: Incidents not appearing in Elasticsearch
**Check:**
```bash
# 1. Check Logstash incidents pipeline
docker compose logs logstash | grep incidents

# 2. Verify incidents Kafka topic
docker compose exec kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic incidents \
  --from-beginning --max-messages 5

# 3. Check Elasticsearch index
curl 'http://localhost:9200/_cat/indices/incidents-*?v'

# 4. Restart Logstash
docker compose restart logstash
```

### Issue: Incidents created but wrong pattern
**Check:**
```bash
# View correlation logic debugging
docker compose logs correlation-engine | grep "pattern\|correlation"

# Check anomaly types in recent incident
docker compose exec postgres psql -U noc_admin -d smart_noc -c "SELECT ia.anomaly_type, COUNT(*) FROM incident_anomalies ia JOIN incidents i ON ia.incident_id = i.id WHERE i.created_at > NOW() - INTERVAL '5 minutes' GROUP BY ia.anomaly_type;"
```

---

## 📈 Performance Testing

### Load Test: High-Volume Anomalies
```bash
cd services/log-generator
source ../../venv/bin/activate

# Generate 2000 logs over 30 seconds (sustained load)
python generate_logs.py --rate 100 --duration 20 &
python generate_scenarios.py --scenario flapping --count 20 &
python generate_scenarios.py --scenario brute-force --count 20 &
python generate_scenarios.py --scenario high-cpu --count 20 &
wait

# Check correlation engine performance
docker compose logs correlation-engine | grep "Statistics"
```

**Expected:**
- Processing time: <100ms per anomaly
- Buffer management: Old anomalies cleaned
- No memory leaks: `docker stats correlation-engine`

---

## 📝 Success Criteria

### ✅ Phase 3 Validation Checklist

- [ ] **Pattern Correlation**
  - [ ] DEVICE_FAILURE pattern creates incidents (3+ anomalies, same device)
  - [ ] NETWORK_PERFORMANCE pattern creates incidents (HIGH_CPU/MEMORY, 2+ devices)
  - [ ] SECURITY_BREACH pattern creates incidents (AUTH_FAILURE, 2+ occurrences)
  - [ ] CONNECTIVITY_ISSUE pattern creates incidents (INTERFACE_DOWN, 2+ devices)

- [ ] **Time-Based Correlation**
  - [ ] 5-minute sliding window groups related anomalies
  - [ ] Buffer cleans old entries (older than 10 minutes)
  - [ ] Anomalies outside window don't correlate

- [ ] **Incident Attributes**
  - [ ] `incident_number` increments sequentially (SERIAL)
  - [ ] `severity` calculated correctly (CRITICAL/HIGH/MEDIUM/LOW)
  - [ ] `impact_score` reflects device count + anomaly count + severity
  - [ ] `affected_devices` JSONB array populated
  - [ ] `correlation_method` indicates TIME_BASED or PATTERN_BASED

- [ ] **Data Pipeline**
  - [ ] Incidents stored in PostgreSQL (query successful)
  - [ ] Incidents indexed to Elasticsearch (search successful)
  - [ ] Logstash incidents pipeline operational
  - [ ] Kafka incidents topic receives messages

- [ ] **Grafana Dashboard**
  - [ ] All 11 panels render correctly
  - [ ] Data refreshes every 5 seconds
  - [ ] Severity colors correct (RED=CRITICAL, ORANGE=HIGH, YELLOW=MEDIUM, GREEN=LOW)
  - [ ] Recent incidents table shows actionable details

---

## 🎓 Next Steps

After validating Phase 3:

1. **Phase 4: LLM Diagnosis**
   - Build GPT-4/Claude integration for root cause analysis
   - Enrich incidents with AI-generated explanations
   - Generate remediation recommendations

2. **Phase 5: Remediation**
   - Ansible playbook execution
   - Automated fixes for common incidents
   - Human approval workflow for critical changes

3. **Phase 6: Validation + Memory**
   - Store remediation outcomes
   - Learn from successful resolutions
   - Improve correlation patterns over time

---

## 📚 Reference

### Correlation Patterns Configuration
Patterns defined in: `services/correlation-engine/config.yaml`

```yaml
patterns:
  NETWORK_PERFORMANCE:
    types: ["HIGH_CPU", "HIGH_MEMORY", "PACKET_LOSS"]
    min_devices: 2
  SECURITY_BREACH:
    types: ["AUTH_FAILURE", "UNAUTHORIZED_ACCESS", "AUTH_BRUTE_FORCE"]
    min_count: 2
  CONNECTIVITY_ISSUE:
    types: ["INTERFACE_DOWN", "BGP_DOWN", "LINK_DOWN", "INTERFACE_FLAPPING"]
    min_devices: 2
  DEVICE_FAILURE:
    min_count: 3  # Same device, different types
```

### Severity Thresholds
- **CRITICAL**: avg_severity ≥ 90 (weighted: CRITICAL=100, HIGH=75, MEDIUM=50, LOW=25)
- **HIGH**: avg_severity ≥ 70
- **MEDIUM**: avg_severity ≥ 40
- **LOW**: avg_severity < 40

### Impact Score Formula
```python
impact_score = (device_count * 10) * 0.4 +    # Device impact (40%)
               (anomaly_count * 3) * 0.3 +    # Anomaly volume (30%)
               avg_severity * 0.3              # Severity weight (30%)
```

---

**🚀 Happy Testing! Let's validate Smart NOC Phase 3 Correlation Engine! 🚀**
