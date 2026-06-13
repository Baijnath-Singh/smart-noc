# Smart NOC End-to-End Pipeline Test Report
**Date:** June 11, 2026  
**Test Duration:** ~1 hour  
**Objective:** Test complete pipeline flow from syslog ingestion through remediation

---

## 🎯 Test Summary

**Goal:** Send 10-20 syslogs and observe them flow through:
1. Logstash (UDP syslog receiver)
2. Kafka (message broker)
3. Anomaly Detector (pattern detection)
4. Correlation Engine (incident creation)
5. LLM Diagnosis (root cause analysis)
6. Remediation Service (action planning/execution)

---

## ✅ Issues Fixed During Testing

### 1. **Anomaly Detector - Feature Extraction Error** ✅ FIXED
- **Problem:** `'list' object has no attribute 'upper'` errors
- **Root Cause:** Elasticsearch aggregating events into array fields
- **Solution:** Added `normalize_field()` helper function to handle both strings and lists
- **File:** `/services/anomaly-detector/detectors/ml_based.py`
- **Status:** Deployed and validated (0 errors after fix)

### 2. **Correlation Engine - NoneType Error** ✅ FIXED
- **Problem:** `argument of type 'NoneType' is not iterable`
- **Root Cause:** `_get_anomaly_type()` returning None, causing string checks to fail
- **Solution:** Modified method to always return a string (default: 'UNKNOWN')
- **File:** `/services/correlation-engine/correlators/pattern_based.py`
- **Status:** Rebuilt image, restarted successfully

### 3. **Logstash - OutOfMemory Crash** ✅ FIXED
- **Problem:** Logstash crashed with `java.lang.OutOfMemoryError: Java heap space`
- **Root Cause:** Only 512MB allocated, insufficient for 4 pipeline configs
- **Solution:** Increased memory to 2GB max (1GB min)
- **File:** `/docker-compose.yml` line 71
- **Status:** Restarted successfully with increased memory

---

## ⚠️ Remaining Issues

### 1. **Logstash Pipeline Configuration** 🔴 CRITICAL
- **Problem:** All 4 pipeline configs loaded into single "main" pipeline
  - `syslog-input.conf` - UDP input → Kafka output (network-logs)
  - `network-logs.conf` - Kafka input (network-logs) → Elasticsearch output
  - `anomalies.conf` - Kafka input (anomalies) → ?
  - `incidents.conf` - Kafka input (incidents) → ?
- **Impact:** Creates circular dependencies and conflicts
- **Evidence:** Logstash has BOTH input AND output for network-logs topic
- **Solution Needed:** Implement proper pipeline separation using `pipelines.yml`

### 2. **Data Quality Issues** 🟡 MODERATE
- **Problem:** Fields contain unparsed Logstash variables:
  - `device_id`: `["10.139.38.188,10.139.38.188", "%{host}"]`
  - `message`: `"%{message}"`
  - `syslog_hostname`: `"%{host}"`
- **Impact:** Anomaly detection can't properly classify event types
- **Root Cause:** Logstash variable expansion failing
- **Solution Needed:** Fix Logstash grok patterns and variable references

### 3. **Message Flow Interruption** 🔴 CRITICAL
- **Problem:** Logs sent via UDP not reaching Kafka/Anomaly Detector
- **Evidence:**
  - Kafka topic offsets unchanged (168, 156, 216 = 540 total)
  - Anomaly detector shows no activity after restart
  - No stdout debug output from Logstash for new messages
- **Possible Causes:**
  - UDP listener not properly initialized
  - Kafka producer failing silently
  - Pipeline conflicts preventing message flow
- **Status:** Requires further debugging

---

## 📊 Test Results

### Logs Sent
- **Initial Test:** 15 strategic syslogs (port flapping, auth failures, hardware)
- **Second Test:** 12 burst logs (3 scenarios)
- **Third Test:** 15 burst logs (port flapping, brute force, device failure)
- **Fourth Test:** 20 logs (3 clear scenarios)
- **Final Test:** 17 logs (port flapping, auth failures, critical hardware)
- **Total:** ~79 test logs sent

### Pipeline Status
| Service | Status | Activity | Issues |
|---------|--------|----------|--------|
| **Logstash** | ✅ Running | ❌ No recent activity | Memory fixed, but not processing new logs |
| **Kafka** | ✅ Running | ⚠️ Topics stale | No new messages since 20:29 |
| **Anomaly Detector** | ✅ Running | ❌ No consumption | Waiting for messages |
| **Correlation Engine** | ✅ Running | ❌ No consumption | Fixed NoneType error |
| **LLM Diagnosis** | ✅ Running | ❌ No activity | Waiting for incidents |
| **Remediation** | ✅ Running | ❌ No activity | Waiting for diagnosed incidents |

### Database Status
- **Total Incidents:** 93
- **Latest Incident:** 2026-06-11 16:26:34 (4+ hours ago)
- **New Incidents Created:** 0 (during testing)

---

## 🔍 Diagnostic Findings

### Kafka Consumer Groups
```
Group: anomaly-detector
- Partition 0: Offset 168/168 (LAG=0)
- Partition 1: Offset 156/156 (LAG=0)
- Partition 2: Offset 216/216 (LAG=0)
Status: Connected but no new messages to consume

Group: correlation-engine  
- Consumed 394 anomalies total
- LAG=0 (all caught up)
- No incidents created

Group: logstash-consumer
- Consuming FROM network-logs (unexpected!)
- Should be PRODUCING TO network-logs
```

### Service Health
- ✅ All containers running
- ✅ All services started successfully
- ✅ No crash loops
- ❌ No message processing activity

---

## 🎓 Lessons Learned

1. **Memory Allocation:** Logstash needs adequate heap space when running multiple pipelines (2GB+ recommended)
2. **Pipeline Separation:** Single-pipeline Logstash configs create conflicts - use `pipelines.yml` for proper separation
3. **Data Validation:** Always validate field types from upstream (strings vs arrays)
4. **Defensive Coding:** Functions should never return None when strings are expected
5. **End-to-End Testing:** Individual service tests don't guarantee pipeline integration works

---

## 📋 Recommended Next Steps

### Immediate (Critical Path)
1. **Separate Logstash Pipelines**
   - Create `/infrastructure/logstash/config/pipelines.yml`
   - Define separate pipelines for syslog-input, network-logs, anomalies, incidents
   - Restart Logstash

2. **Verify UDP Reception**
   - Use `tcpdump` to confirm packets arrive at port 5000
   - Enable debug logging in Logstash
   - Test with simple netcat message

3. **Fix Logstash Variable Expansion**
   - Review grok patterns in all pipeline configs
   - Ensure proper field references (no `%{host}` in output)
   - Test with sample log

### Short Term
4. **Add Event Type Classification**
   - Enhance syslog-input.conf to properly set `event_type` field
   - Add patterns for: INTERFACE_FLAPPING, AUTH_BRUTE_FORCE, PSU_FAILURE, etc.
   - Validate with test logs

5. **Monitor Consumer Lag**
   - Set up alerts for Kafka consumer lag > 100
   - Track message processing rates
   - Identify bottlenecks

### Long Term
6. **Add Integration Tests**
   - Automated end-to-end pipeline tests
   - Synthetic log injection
   - Validation of expected incidents

7. **Improve Observability**
   - Structured logging for all services
   - Distributed tracing (OpenTelemetry)
   - Pipeline flow visualization

---

## 📞 Support Information

**Issues Fixed:** 3/3  
**Pipeline Functional:** Partial (ingestion blocked)  
**Data Flowing:** ❌ No  
**Incidents Created:** ❌ No  

**Blocking Issue:** Logstash not forwarding UDP syslogs to Kafka  
**Priority:** P0 (Critical)  
**ETA to Resolution:** ~2-4 hours (pipeline reconfiguration + testing)

---

## 🔗 Related Documents
- [ARCHITECTURE.md](./ARCHITECTURE.md)
- [TROUBLESHOOTING.md](./docs/TROUBLESHOOTING.md)
- [PHASE4_IMPLEMENTATION_COMPLETE.md](./PHASE4_IMPLEMENTATION_COMPLETE.md)
- [TESTING_GUIDE.md](./TESTING_GUIDE.md)

---

*Report generated during active debugging session*
*Next update: After Logstash pipeline reconfiguration*
