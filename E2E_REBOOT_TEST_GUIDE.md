# End-to-End Reboot Loop Test Guide

## Overview
This guide walks you through testing the complete Smart NOC pipeline for EXOS reboot loop incidents, verifying that KB-EXOS-CONFIGURATION-003 is used correctly.

---

## Prerequisites

### 1. Verify All Services Running
```bash
docker ps --format "table {{.Names}}\t{{.Status}}" | grep smart-noc
```

**Expected:** All services should show "Up" status:
- smart-noc-logstash
- smart-noc-device-enrichment
- smart-noc-anomaly-detector
- smart-noc-correlation-engine
- smart-noc-llm-diagnosis
- smart-noc-chromadb
- smart-noc-postgres
- smart-noc-kafka

### 2. Verify KB Article Exists
```bash
docker exec smart-noc-chromadb curl -s "http://localhost:8000/api/v1/collections/59bf82e6-59a4-4926-abc2-5cf5013278cb/get" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"ids": ["KB-EXOS-CONFIGURATION-003"], "include": ["metadatas"]}' | python3 -m json.tool
```

**Expected Output:**
```json
{
    "metadatas": [{
        "category": "system",
        "event_type": "SYSTEM_REBOOT",
        "platform": "exos",
        "title": "Fixing EXOS/Switch Engine Reboot Loop",
        "vendor": "extreme"
    }]
}
```

### 3. Check Device Exists
```bash
docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -c \
  "SELECT device_id, hostname, management_ip, vendor FROM devices WHERE device_id = '10.139.38.188';"
```

**Expected:** Device should exist with vendor "Extreme Networks"

---

## Step-by-Step Test

### Step 1: Create Test Log File

Create realistic reboot loop logs in proper syslog format:

```bash
cat > /tmp/e2e-reboot-test.log << 'EOF'
Jun 20 11:30:00 10.139.38.188 EXOS: Emergency: System boot failure - configuration file corrupted
Jun 20 11:30:15 10.139.38.188 EXOS: System reboot initiated - attempting recovery
Jun 20 11:30:30 10.139.38.188 EXOS: Boot process failed - cannot load configuration
Jun 20 11:30:45 10.139.38.188 EXOS: System reboot initiated - retry attempt 2
Jun 20 11:31:00 10.139.38.188 EXOS: Boot failure - configuration corruption detected
Jun 20 11:31:15 10.139.38.188 EXOS: Critical: System in reboot loop - 5 failures in 90 seconds
Jun 20 11:31:30 10.139.38.188 EXOS: System reboot initiated - attempting alternate image
Jun 20 11:31:45 10.139.38.188 EXOS: Boot process failed - primary image error
Jun 20 11:32:00 10.139.38.188 EXOS: Emergency: Continuous reboot cycle detected
Jun 20 11:32:15 10.139.38.188 EXOS: System reboot initiated - rescue mode attempt
Jun 20 11:32:30 10.139.38.188 EXOS: Boot failure - switch unresponsive
Jun 20 11:32:45 10.139.38.188 EXOS: Critical: Reboot loop - manual intervention needed
Jun 20 11:33:00 10.139.38.188 EXOS: Emergency: System boot loader failure
Jun 20 11:33:15 10.139.38.188 EXOS: Critical: Reboot loop - corrupted boot configuration
Jun 20 11:33:30 10.139.38.188 EXOS: System reboot initiated - emergency recovery mode
EOF
```

**What this does:** Creates 15 reboot log messages spanning 3.5 minutes

---

### Step 2: Send Logs to Logstash

```bash
bash scripts/send_test_logs.sh /tmp/e2e-reboot-test.log
```

**Expected Output:**
```
Sending test logs to localhost:5000
============================================================
  Sent line 1: <134>Jun 20 11:30:00 10.139.38.188 EXOS: Emergency: System boot failure...
  ...
  Sent line 15: <134>Jun 20 11:33:30 10.139.38.188 EXOS: System reboot initiated...
============================================================
✓ Sent 15 log message(s)
```

**What happens:** Script adds syslog priority `<134>` and sends each line via UDP to port 5000

---

### Step 3: Monitor Logstash Processing

Wait 5 seconds, then check:

```bash
docker logs --tail 30 smart-noc-logstash 2>&1 | grep -E "event_type|SYSTEM_REBOOT|reboot_loop" | head -10
```

**Expected Output (sample):**
```
"event_type" => "SYSTEM_REBOOT"
"tags" => ["syslog_parsed", "system", "reboot", "critical", "reboot_loop", "alert"]
```

**What to verify:**
- ✅ `event_type` is `SYSTEM_REBOOT`
- ✅ Tags include `reboot`, `reboot_loop`, `boot_failure`

---

### Step 4: Verify Device Enrichment

Wait 10 seconds, then check:

```bash
docker logs --tail 50 smart-noc-device-enrichment 2>&1 | grep "10.139.38.188"
```

**Expected Output (sample):**
```
2026-06-20 XX:XX:XX | INFO     | → Request: GET /device/10.139.38.188
2026-06-20 XX:XX:XX | INFO     | ✓ Device found in Redis cache: 10.139.38.188
2026-06-20 XX:XX:XX | INFO     | 192.168.32.7 - - [20/Jun/2026 XX:XX:XX] "GET /device/10.139.38.188 HTTP/1.1" 200 -
```

**What to verify:**
- ✅ Status code 200 (device found)
- ✅ No 404 errors

---

### Step 5: Monitor Anomaly Detection

Wait 15-20 seconds:

```bash
docker logs --tail 100 smart-noc-anomaly-detector 2>&1 | grep -E "Processing.*10.139.38.188.*SYSTEM_REBOOT|ML anomaly detected.*SYSTEM_REBOOT|Anomaly published"
```

**Expected Output (sample):**
```
2026-06-20 XX:XX:XX | DEBUG    | Processing: 10.139.38.188 - SYSTEM_REBOOT
2026-06-20 XX:XX:XX | WARNING  | ML anomaly detected: 10.139.38.188 - SYSTEM_REBOOT (confidence: 1.00)
2026-06-20 XX:XX:XX | INFO     | Anomaly published: ML_DETECTED_ANOMALY - 10.139.38.188
```

**What to verify:**
- ✅ Event type is `SYSTEM_REBOOT` (not AUTH_EVENT or unknown)
- ✅ At least 1-2 anomalies published

---

### Step 6: Check Incident Creation

Wait 25-30 seconds total, then check:

```bash
docker logs --tail 50 smart-noc-correlation-engine 2>&1 | grep -E "Created incident|Incident published" | tail -3
```

**Expected Output (sample):**
```
2026-06-20 XX:XX:XX | SUCCESS  | Created incident #20029: UNKNOWN (severity: MEDIUM, devices: 1)
2026-06-20 XX:XX:XX | INFO     | Incident published to Kafka: incidents
```

**Note the incident number** (e.g., #20029) - you'll need it for next steps

**What to verify:**
- ✅ New incident created (number will be higher than previous)
- ✅ Published to Kafka

---

### Step 7: Monitor LLM Diagnosis

Wait 35-40 seconds total:

```bash
# Replace 20029 with your actual incident number
INCIDENT_NUM=20029
docker logs --tail 200 smart-noc-llm-diagnosis 2>&1 | grep -E "incident #${INCIDENT_NUM}|KB.*Reboot|DIAGNOSIS COMPLETE" | head -15
```

**Expected Output (sample):**
```
2026-06-20 XX:XX:XX | INFO     | Processing incident #20029
2026-06-20 XX:XX:XX | INFO     | Building context for incident #20029
2026-06-20 XX:XX:XX | INFO     |   → KB Article 1: KB-EXOS-CONFIGURATION-003 - Fixing EXOS/Switch Engine Reboot Loop (relevance: 0.679, queries: 5)
2026-06-20 XX:XX:XX | INFO     | Vector search completed for incident #20029
2026-06-20 XX:XX:XX | SUCCESS  | ✅ INCIDENT #20029 DIAGNOSIS COMPLETE
```

**What to verify:**
- ✅ KB-EXOS-CONFIGURATION-003 is mentioned
- ✅ Relevance score > 0.60
- ✅ Diagnosis completed successfully

---

### Step 8: Verify Diagnosis Results

Check the database:

```bash
# Replace 20029 with your incident number
INCIDENT_NUM=20029

# Check root cause
docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -c \
  "SELECT incident_number, incident_type, root_cause FROM incidents WHERE incident_number = ${INCIDENT_NUM};"
```

**Expected Output (sample):**
```
 incident_number | incident_type | root_cause
-----------------+---------------+----------------------------------------------
           20029 | UNKNOWN       | Intermittent device failure due to a potential 
                                   configuration or software issue, such as a 
                                   corrupted configuration file or failed software update
```

**What to verify:**
- ✅ Root cause mentions "configuration file" or "software update"
- ✅ Related to reboot/boot issues

---

### Step 9: Check Remediation Plan

```bash
# Replace 20029 with your incident number
INCIDENT_NUM=20029

docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -t -c \
  "SELECT remediation_plan FROM incidents WHERE incident_number = ${INCIDENT_NUM};" \
  | python3 -m json.tool
```

**Expected Output (sample):**
```json
[
    {
        "priority": "IMMEDIATE",
        "step": 1,
        "action": "Verify device configuration and software version",
        "command": "show configuration",
        "expected_outcome": "Configuration and software version are verified",
        "duration_minutes": 5
    },
    {
        "priority": "SHORT_TERM",
        "step": 2,
        "action": "Check for software updates and apply if necessary",
        "command": "show bootvar",
        "expected_outcome": "Software is up-to-date",
        "duration_minutes": 10
    },
    {
        "priority": "LONG_TERM",
        "step": 3,
        "action": "Schedule maintenance to inspect and update configuration files",
        "command": "schedule maintenance",
        "expected_outcome": "Configuration files are updated and device is stable",
        "duration_minutes": 60
    }
]
```

**What to verify:**
- ✅ Commands are EXOS-specific (`show configuration`, `show bootvar`)
- ✅ NOT Cisco commands (NO "show running-config", NO "configure terminal")
- ✅ 3 steps with priorities: IMMEDIATE, SHORT_TERM, LONG_TERM

---

### Step 10: Verify Full Diagnosis Output

```bash
# Replace 20029 with your incident number
INCIDENT_NUM=20029

docker logs --tail 300 smart-noc-llm-diagnosis 2>&1 | \
  grep -A 60 "incident #${INCIDENT_NUM}" | \
  grep -A 40 "ROOT CAUSE\|REMEDIATION\|KB Article"
```

**Expected to see:**
- KB article title mentioned
- Chain-of-thought reasoning referencing reboot loop
- Root cause explaining configuration/software issues
- 3-step remediation plan

---

### Step 11: Verify Anomaly Data

```bash
# Replace 20029 with your incident number
INCIDENT_NUM=20029

docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -t -c \
  "SELECT ia.anomaly_data->'source_log'->>'message', 
          ia.anomaly_data->>'event_type' 
   FROM incident_anomalies ia 
   JOIN incidents i ON ia.incident_id = i.id 
   WHERE i.incident_number = ${INCIDENT_NUM};"
```

**Expected Output (sample):**
```
 System reboot initiated - attempting recovery    | SYSTEM_REBOOT
 Critical: System in reboot loop - 5 failures     | SYSTEM_REBOOT
```

**What to verify:**
- ✅ Messages contain "reboot", "boot failure", "configuration"
- ✅ Event type is `SYSTEM_REBOOT`

---

## Success Criteria Checklist

Use this to verify your test passed:

- [ ] **Step 2:** All 15 logs sent successfully
- [ ] **Step 3:** Logstash classified logs as `SYSTEM_REBOOT`
- [ ] **Step 4:** Device enrichment returned 200 (found device)
- [ ] **Step 5:** Anomaly detector published 1-2 ML anomalies with `SYSTEM_REBOOT` type
- [ ] **Step 6:** Correlation engine created new incident
- [ ] **Step 7:** LLM diagnosis found KB-EXOS-CONFIGURATION-003 with relevance > 0.6
- [ ] **Step 8:** Root cause mentions configuration/software/reboot issues
- [ ] **Step 9:** Remediation uses EXOS commands (`show configuration`, `show bootvar`)
- [ ] **Step 10:** Full diagnosis output shows KB article usage
- [ ] **Step 11:** Anomaly messages contain reboot keywords

---

## Troubleshooting

### Issue: No incident created (Step 6)

**Possible causes:**
- Not enough anomalies detected (need at least 2)
- Correlation threshold not met

**Solution:**
```bash
# Send more logs
cat > /tmp/additional-reboot-logs.log << 'EOF'
Jun 20 11:35:00 10.139.38.188 EXOS: Emergency: Boot loader failure
Jun 20 11:35:20 10.139.38.188 EXOS: Critical: Reboot loop continues
Jun 20 11:35:40 10.139.38.188 EXOS: System reboot initiated - attempt 10
Jun 20 11:36:00 10.139.38.188 EXOS: Boot failure - system offline
Jun 20 11:36:20 10.139.38.188 EXOS: Emergency: Manual intervention required
EOF

bash scripts/send_test_logs.sh /tmp/additional-reboot-logs.log
```

Wait 30 seconds and check Step 6 again.

---

### Issue: KB article not found (Step 7)

**Check if article exists:**
```bash
docker exec smart-noc-chromadb curl -s "http://localhost:8000/api/v1/collections/59bf82e6-59a4-4926-abc2-5cf5013278cb/count"
```

Expected: 64

**Verify metadata:**
```bash
docker exec smart-noc-chromadb curl -s \
  "http://localhost:8000/api/v1/collections/59bf82e6-59a4-4926-abc2-5cf5013278cb/get" \
  -X POST -H "Content-Type: application/json" \
  -d '{"ids": ["KB-EXOS-CONFIGURATION-003"], "include": ["metadatas"]}' \
  | python3 -m json.tool | grep -E "event_type|vendor|platform"
```

Expected:
- `"event_type": "SYSTEM_REBOOT"` (not "CONFIGURATION")
- `"vendor": "extreme"` (lowercase)
- `"platform": "exos"` (lowercase)

**If incorrect, reimport:**
```bash
# Delete old article
docker exec smart-noc-chromadb curl -s \
  "http://localhost:8000/api/v1/collections/59bf82e6-59a4-4926-abc2-5cf5013278cb/delete" \
  -X POST -H "Content-Type: application/json" \
  -d '{"ids": ["KB-EXOS-CONFIGURATION-003"]}'

# Reimport with correct metadata
bash scripts/import_kb_to_vector.sh kb_sources/validated_articles/KB-EXOS-CONFIGURATION-001.json
```

---

### Issue: Wrong event type (AUTH_EVENT instead of SYSTEM_REBOOT)

**Check Logstash configuration:**
```bash
grep -A 10 "reboot" infrastructure/logstash/pipeline/syslog-input.conf
```

Should contain SYSTEM_REBOOT detection patterns.

**If missing, restart Logstash:**
```bash
docker restart smart-noc-logstash
sleep 15
```

Then retry from Step 2.

---

### Issue: Device not found (404 in Step 4)

**Check device exists:**
```bash
docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -c \
  "SELECT * FROM devices WHERE management_ip = '10.139.38.188';"
```

**If empty, use the correct device IP from your database:**
```bash
docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -c \
  "SELECT device_id, hostname, management_ip FROM devices LIMIT 5;"
```

Update your test log file with the correct IP.

---

## Quick Verification Commands

Run these anytime to check system state:

```bash
# 1. Check latest incidents
docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -c \
  "SELECT incident_number, incident_type, status, anomaly_count, created_at 
   FROM incidents ORDER BY incident_number DESC LIMIT 5;"

# 2. Check ChromaDB article count
docker exec smart-noc-chromadb curl -s \
  "http://localhost:8000/api/v1/collections/59bf82e6-59a4-4926-abc2-5cf5013278cb/count"

# 3. Check service health
docker ps --filter name=smart-noc --format "table {{.Names}}\t{{.Status}}"

# 4. Check recent anomalies
docker logs --tail 50 smart-noc-anomaly-detector 2>&1 | \
  grep -E "ML anomaly detected|Anomaly published" | tail -5
```

---

## Expected Timeline

| Time | Step | Action |
|------|------|--------|
| 0s | 1 | Create test logs |
| 2s | 2 | Send to Logstash |
| 7s | 3-4 | Logstash parses, enrichment adds device data |
| 15s | 5 | Anomaly detection (1-2 anomalies) |
| 30s | 6 | Correlation creates incident |
| 40s | 7-9 | LLM diagnosis completes |
| 45s | 10-11 | Verify results |

**Total time:** ~45-60 seconds from log submission to complete diagnosis

---

## Notes

- **Incident numbers increment:** Each test creates a new incident (20025, 20026, 20027...)
- **Timestamps don't matter:** Using old dates (Jun 20) is fine; system uses `@timestamp` from ingestion
- **Multiple tests:** Can run test multiple times; each creates a new incident
- **Cleanup:** No cleanup needed; incidents stay in database for historical analysis

---

## Success Example

When everything works correctly, you'll see:

1. **Logstash:** Event classified as `SYSTEM_REBOOT` with tags `reboot_loop`, `boot_failure`
2. **Anomaly Detector:** Published ML anomalies with `SYSTEM_REBOOT` type
3. **Correlation:** Created incident from 2 correlated anomalies
4. **LLM Diagnosis:** Found and used KB-EXOS-CONFIGURATION-003 (relevance 0.67-0.75)
5. **Root Cause:** Mentions "configuration corruption", "software update failure", or "boot issues"
6. **Remediation:** EXOS-specific commands (`show configuration`, `show bootvar`, not Cisco syntax)

**This proves the KB article is correctly integrated into the diagnosis pipeline!** 🎉
