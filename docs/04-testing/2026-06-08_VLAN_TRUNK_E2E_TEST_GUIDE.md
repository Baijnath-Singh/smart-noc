# End-to-End Test Guide: VLAN Trunk Native VLAN Mismatch

## 📋 Test Scenario

**Issue:** VLAN trunk port native VLAN mismatch between two VOSS switches  
**Devices:** voss-dist-switch-01 (Native VLAN 1) ↔ voss-dist-switch-02 (Native VLAN 10)  
**Trunk Port:** 1/20 on both switches  
**Expected KB Article:** EXT-019 (VOSS VLAN Configuration and Trunking Issues)  
**Expected Event Type:** VLAN_MISMATCH → CONNECTIVITY_ISSUE incident  

---

## 🚀 Step 1: Run the Test

```bash
cd /home/user/ng-iam/smart-noc
source venv/bin/activate
python test_vlan_trunk_mismatch_e2e.py
```

**Expected Output:**
- 8 log events sent to Kafka `network-logs` topic
- Mix of VLAN_MISMATCH, MAC_LEARNING_ISSUE, STP_INCONSISTENCY events
- Events from voss-dist-switch-01 and voss-dist-switch-02

---

## ⏱️ Step 2: Wait for Processing

**Wait 30-40 seconds** for the pipeline to process:

1. **Anomaly Detector** (5-10s): Rule-based detection of VLAN mismatches
2. **Correlation Engine** (5s): Groups related anomalies into incident
3. **LLM Diagnosis** (10-15s): Enhanced multi-query KB search + LLM diagnosis

---

## 🔍 Step 3: Validation Queries

### **3.1 Check Raw Logs in Kafka (Optional)**

```bash
# Check network-logs topic for VLAN events
docker exec smart-noc-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic network-logs \
  --from-beginning \
  --max-messages 10 | grep -i vlan
```

**What to look for:**
- Log entries with `"event_type": "VLAN_MISMATCH"`
- Devices: voss-dist-switch-01, voss-dist-switch-02
- Native VLAN values: 1 vs 10

---

### **3.2 Check Anomaly Detection**

```bash
docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -c "
SELECT 
    id,
    anomaly_type,
    device_id,
    severity,
    TO_CHAR(timestamp, 'HH24:MI:SS') as time,
    details::json->>'local_native_vlan' as local_vlan,
    details::json->>'remote_native_vlan' as remote_vlan
FROM anomalies 
WHERE device_id LIKE 'voss-dist%'
ORDER BY timestamp DESC 
LIMIT 10;
"
```

**Expected Output:**
```
 id  | anomaly_type   | device_id              | severity | time     | local_vlan | remote_vlan
-----+----------------+------------------------+----------+----------+------------+-------------
 XX  | VLAN_MISMATCH  | voss-dist-switch-01    | medium   | 18:15:23 | 1          | 10
 XX  | VLAN_MISMATCH  | voss-dist-switch-02    | medium   | 18:15:28 | 10         | 1
```

**✅ Success Criteria:**
- At least 2-3 anomalies with `VLAN_MISMATCH` type
- Both devices (voss-dist-switch-01, voss-dist-switch-02) present
- Native VLAN values captured in details

---

### **3.3 Check Incident Correlation**

```bash
docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -c "
SELECT 
    incident_number,
    incident_type,
    severity,
    affected_devices,
    anomaly_count,
    TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') as created,
    CASE 
        WHEN root_cause IS NOT NULL THEN 'DIAGNOSED'
        ELSE 'PENDING'
    END as diagnosis_status
FROM incidents 
WHERE affected_devices::text LIKE '%voss-dist%'
ORDER BY incident_number DESC 
LIMIT 3;
"
```

**Expected Output:**
```
 incident_number | incident_type      | severity | affected_devices                                | anomaly_count | created             | diagnosis_status
-----------------+--------------------+----------+------------------------------------------------+---------------+---------------------+------------------
              15 | CONNECTIVITY_ISSUE | high     | ["voss-dist-switch-01","voss-dist-switch-02"]  |             8 | 2026-06-06 18:15:35 | DIAGNOSED
```

**✅ Success Criteria:**
- New incident created with incident_number (e.g., 15)
- `incident_type`: CONNECTIVITY_ISSUE (correlation engine classified it)
- `affected_devices`: Both VOSS switches
- `anomaly_count`: 6-8 (all related anomalies grouped)
- `diagnosis_status`: DIAGNOSED (LLM completed diagnosis)

---

### **3.4 Check Incident Details**

```bash
docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -c "
SELECT 
    incident_number,
    incident_type,
    LEFT(incident_metadata::text, 200) as metadata_preview
FROM incidents 
WHERE affected_devices::text LIKE '%voss-dist%'
ORDER BY incident_number DESC 
LIMIT 1;
"
```

**Expected Output:**
```
 incident_number | incident_type      | metadata_preview
-----------------+--------------------+---------------------------------------------------------------------------------
              15 | CONNECTIVITY_ISSUE | {"affected_vlans": [1, 10], "trunk_ports": ["1/20"], "mismatch_type": "native_vlan"}
```

**✅ Success Criteria:**
- Metadata includes affected VLANs (1 and 10)
- Trunk port identified (1/20)
- Mismatch type captured

---

### **3.5 Check Root Cause Analysis**

```bash
docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -c "
SELECT 
    incident_number,
    incident_type,
    root_cause
FROM incidents 
WHERE affected_devices::text LIKE '%voss-dist%'
ORDER BY incident_number DESC 
LIMIT 1;
"
```

**Expected Output (abbreviated):**
```
 incident_number | incident_type      | root_cause
-----------------+--------------------+--------------------------------------------------------------------
              15 | CONNECTIVITY_ISSUE | **Root Cause: Native VLAN Mismatch on Trunk Link**
                                        
                                        The connectivity issue is caused by a **native VLAN 
                                        mismatch** between two VOSS switches on their trunk link:
                                        
                                        - voss-dist-switch-01: Native VLAN 1 (port 1/20)
                                        - voss-dist-switch-02: Native VLAN 10 (port 1/20)
                                        
                                        This mismatch causes untagged traffic to be placed in 
                                        different VLANs on each switch, resulting in:
                                        - CDP/LLDP warnings about native VLAN inconsistency
                                        - MAC address learning issues
                                        - STP topology inconsistencies
                                        - 100% connectivity loss for untagged traffic
                                        
                                        **Contributing Factors:**
                                        1. Configuration inconsistency (likely manual config error)
                                        2. No automated VLAN audit in place
                                        3. Native VLAN 1 vs 10 mismatch
```

**✅ Success Criteria:**
- Root cause explicitly mentions "Native VLAN Mismatch"
- Identifies both devices and their native VLANs (1 vs 10)
- Mentions trunk port (1/20)
- Lists symptoms (CDP warnings, MAC issues, connectivity loss)
- References VOSS-specific context

---

### **3.6 Check Remediation Plan**

```bash
docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -c "
SELECT 
    incident_number,
    remediation_plan
FROM incidents 
WHERE affected_devices::text LIKE '%voss-dist%'
ORDER BY incident_number DESC 
LIMIT 1;
"
```

**Expected Output (abbreviated):**
```
 incident_number | remediation_plan
-----------------+--------------------------------------------------------------------
              15 | **Remediation Plan: Fix Native VLAN Mismatch**
                  
                  **Step 1: Verify Current Configuration**
                  
                  On voss-dist-switch-01:
                  # show interfaces gigabitEthernet 1/20
                  → Check "Default VLAN ID" (should show 1)
                  
                  On voss-dist-switch-02:
                  # show interfaces gigabitEthernet 1/20
                  → Check "Default VLAN ID" (should show 10)
                  
                  **Step 2: Standardize Native VLAN**
                  
                  Decision: Use VLAN 1 as standard (or choose VLAN 10)
                  
                  On voss-dist-switch-02 (change from 10 to 1):
                  (config)# interface gigabitEthernet 1/20
                  (config-if)# default-vlan-id 1
                  
                  **Step 3: Verify Configuration**
                  
                  # show interfaces gigabitEthernet 1/20 | include VLAN
                  → Both switches should show same native VLAN
                  
                  **Step 4: Test Connectivity**
                  
                  # ping <remote-switch-management-ip>
                  → Verify inter-switch connectivity restored
                  
                  # show mac-address-table vlan 1
                  → Verify MAC learning working correctly
                  
                  **Step 5: Clear CDP/LLDP Warnings**
                  
                  # clear lldp statistics
                  → Warnings should not reappear
                  
                  **Prevention:**
                  - Implement automated VLAN configuration audits
                  - Use consistent native VLAN across all trunks (standard: VLAN 1)
                  - Document trunk port configurations
                  - Enable CDP/LLDP monitoring alerts
```

**✅ Success Criteria:**
- Remediation includes VOSS-specific commands
- Step-by-step fix procedure provided
- Shows how to change native VLAN (`default-vlan-id`)
- Includes verification steps
- Provides prevention recommendations

---

### **3.7 Check KB Article Retrieval (Enhanced Search Metrics)**

```bash
docker-compose logs llm-diagnosis --tail 100 | grep -A 20 "multi-query\|KB Article\|Detected vendor"
```

**Expected Output:**
```
INFO - Detected vendor: extreme, platform: voss from device: voss-dist-switch-01
INFO - Found 3 relevant KB articles (multi-query, avg 3.7 queries per article)
INFO -   → KB Article 1: EXT-019 - VOSS VLAN Configuration and Trunking Issues (relevance: 0.752, queries: 4)
INFO -   → KB Article 2: KB-015 - Spanning Tree Loop/Broadcast Storm (relevance: 0.612, queries: 3)
INFO -   → KB Article 3: EXT-033 - VOSS MAC Address Table Issues (relevance: 0.598, queries: 3)
```

**✅ Success Criteria:**
- Vendor detection: `extreme, platform: voss`
- Multi-query search activated
- **EXT-019** retrieved as top article
- Relevance score: > 0.70 (enhanced search improvement)
- Multiple queries matched (3-5 queries)
- Query types: original, event-focused, vendor-focused, troubleshooting, root-cause

---

### **3.8 Check Diagnosis Confidence Score**

```bash
docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -c "
SELECT 
    incident_number,
    confidence_score,
    diagnosis_metadata::json->'kb_articles_used' as kb_articles,
    diagnosis_metadata::json->'vector_search_relevance' as search_relevance
FROM incidents 
WHERE affected_devices::text LIKE '%voss-dist%'
ORDER BY incident_number DESC 
LIMIT 1;
"
```

**Expected Output:**
```
 incident_number | confidence_score | kb_articles                     | search_relevance
-----------------+------------------+---------------------------------+------------------
              15 |             0.85 | ["EXT-019", "KB-015"]          | 0.752
```

**✅ Success Criteria:**
- Confidence score: > 0.80 (high confidence)
- KB articles include EXT-019 (VOSS VLAN trunking)
- Search relevance: > 0.70 (enhanced search working)

---

### **3.9 Check Diagnosis History (Timeline)**

```bash
docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -c "
SELECT 
    incident_number,
    TO_CHAR(diagnosed_at, 'HH24:MI:SS') as diagnosed_time,
    EXTRACT(EPOCH FROM (diagnosed_at - created_at)) as diagnosis_duration_seconds
FROM incidents 
WHERE affected_devices::text LIKE '%voss-dist%'
ORDER BY incident_number DESC 
LIMIT 1;
"
```

**Expected Output:**
```
 incident_number | diagnosed_time | diagnosis_duration_seconds
-----------------+----------------+----------------------------
              15 | 18:15:48       |                      13.5
```

**✅ Success Criteria:**
- Diagnosis completed within 10-20 seconds of incident creation
- Fast turnaround from detection to diagnosis

---

### **3.10 Full Incident Summary**

```bash
docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -c "
SELECT 
    'Incident #' || incident_number as incident,
    incident_type,
    severity,
    array_length(affected_devices, 1) as num_devices,
    anomaly_count,
    CASE 
        WHEN root_cause IS NOT NULL THEN '✅ YES' 
        ELSE '❌ NO' 
    END as has_root_cause,
    CASE 
        WHEN remediation_plan IS NOT NULL THEN '✅ YES' 
        ELSE '❌ NO' 
    END as has_remediation,
    confidence_score,
    TO_CHAR(created_at, 'HH24:MI:SS') as created,
    TO_CHAR(diagnosed_at, 'HH24:MI:SS') as diagnosed
FROM incidents 
WHERE affected_devices::text LIKE '%voss-dist%'
ORDER BY incident_number DESC 
LIMIT 1;
"
```

**Expected Output:**
```
   incident   |   incident_type    | severity | num_devices | anomaly_count | has_root_cause | has_remediation | confidence_score | created  | diagnosed
--------------+--------------------+----------+-------------+---------------+----------------+-----------------+------------------+----------+-----------
 Incident #15 | CONNECTIVITY_ISSUE | high     |           2 |             8 | ✅ YES         | ✅ YES          |             0.85 | 18:15:35 | 18:15:48
```

**✅ Success Criteria:**
- All fields populated
- Root cause: ✅ YES
- Remediation: ✅ YES
- Confidence: > 0.80
- Processing time: < 20 seconds

---

## 📊 Step 4: Verify Enhanced Search Impact

### **4.1 Check Query Variations Generated**

```bash
docker-compose logs llm-diagnosis --tail 200 | grep -B 2 -A 2 "query_text\|Query.*focused"
```

**Expected Output:**
```
Query 1 (original): "Native VLAN mismatch on trunk port causing connectivity issues"
Query 2 (event-focused): "VLAN_MISMATCH Native VLAN mismatch on trunk port causing connectivity issues"
Query 3 (vendor-focused): "extreme voss Native VLAN mismatch on trunk port causing connectivity issues"
Query 4 (troubleshooting): "troubleshooting Native VLAN mismatch on trunk port causing connectivity issues"
Query 5 (root-cause): "root cause Native VLAN mismatch on trunk port causing connectivity issues"
```

**✅ Success Criteria:**
- 5 query variations generated
- Includes vendor (extreme voss)
- Includes event type (VLAN_MISMATCH)
- Multiple semantic angles

---

### **4.2 Compare Single vs Multi-Query (Optional Deep Dive)**

```bash
# Check if both search methods were tried (for comparison)
docker-compose logs llm-diagnosis --tail 300 | grep -i "single-query\|multi-query"
```

---

## 🎯 Step 5: Expected Results Summary

### **Pipeline Flow Validation**

| Stage | Duration | Output | Status |
|-------|----------|--------|--------|
| **1. Log Generation** | Instant | 8 events to Kafka | ✅ |
| **2. Anomaly Detection** | 5-10s | 6-8 anomalies (VLAN_MISMATCH, etc.) | ✅ |
| **3. Correlation** | 5s | 1 CONNECTIVITY_ISSUE incident | ✅ |
| **4. Diagnosis** | 10-15s | Root cause + remediation | ✅ |
| **Total** | 20-30s | Complete incident lifecycle | ✅ |

---

### **KB Article Retrieval Validation**

| Metric | Expected | Actual | Status |
|--------|----------|--------|--------|
| **Primary KB Article** | EXT-019 | (check logs) | |
| **Relevance Score** | > 0.70 | (check logs) | |
| **Queries Matched** | 3-5 | (check logs) | |
| **Search Method** | Multi-query | (check logs) | |
| **Vendor Detection** | extreme/voss | (check logs) | |

---

### **Diagnosis Quality Validation**

| Component | Expected | Status |
|-----------|----------|--------|
| **Root Cause Identified** | Native VLAN mismatch (1 vs 10) | |
| **Devices Named** | voss-dist-switch-01, voss-dist-switch-02 | |
| **Port Identified** | 1/20 (trunk) | |
| **Symptoms Listed** | CDP warnings, MAC issues, connectivity loss | |
| **VOSS Commands** | `default-vlan-id`, `show interfaces` | |
| **Step-by-Step Fix** | Clear remediation procedure | |
| **Prevention Tips** | VLAN audits, standardization | |

---

## 🔬 Step 6: Advanced Analysis (Optional)

### **6.1 Check Vector Search Embeddings**

```bash
# Query ChromaDB directly (if needed)
docker exec smart-noc-chromadb curl -X POST "http://localhost:8000/api/v1/collections/kb_articles/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query_texts": ["Native VLAN mismatch trunk port"],
    "n_results": 3
  }'
```

---

### **6.2 Analyze Diagnosis Token Usage**

```bash
docker-compose logs llm-diagnosis | grep -i "token\|llm"
```

---

### **6.3 Check Kafka Message Flow**

```bash
# Check all Kafka topics for the incident
docker exec smart-noc-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic incidents-diagnosed \
  --from-beginning \
  --max-messages 1 | jq '.'
```

---

## ✅ Success Checklist

Use this checklist to validate the end-to-end test:

- [ ] **Test executed**: 8 VLAN mismatch events sent to Kafka
- [ ] **Anomalies detected**: 6-8 anomalies in anomalies table
- [ ] **Incident created**: New incident with CONNECTIVITY_ISSUE type
- [ ] **Both devices correlated**: voss-dist-switch-01 and voss-dist-switch-02
- [ ] **Vendor detected**: extreme/voss in logs
- [ ] **Multi-query search used**: 5 query variations generated
- [ ] **KB article retrieved**: EXT-019 as top match
- [ ] **Relevance score high**: > 0.70
- [ ] **Root cause accurate**: Native VLAN mismatch (1 vs 10) identified
- [ ] **Remediation complete**: VOSS-specific commands provided
- [ ] **Diagnosis fast**: < 20 seconds from detection to diagnosis
- [ ] **Confidence high**: > 0.80 confidence score

---

## 🐛 Troubleshooting

### **No anomalies detected**
- Check anomaly-detector logs: `docker-compose logs anomaly-detector --tail 50`
- Verify Kafka topic: `docker exec smart-noc-kafka kafka-topics --list --bootstrap-server localhost:9092`

### **No incident created**
- Check correlation-engine logs: `docker-compose logs correlation-engine --tail 50`
- Verify correlation patterns in `services/correlation-engine/config.yaml`

### **No diagnosis generated**
- Check llm-diagnosis logs: `docker-compose logs llm-diagnosis --tail 100`
- Verify Groq API key configured
- Check ChromaDB connectivity

### **KB article not retrieved**
- Verify ChromaDB has KB articles: `docker exec smart-noc-chromadb curl http://localhost:8000/api/v1/collections`
- Check vector-service logs: `docker-compose logs vector-service --tail 50`

---

## 📖 Related Documentation

- [LAYER2_LAYER3_CAPABILITIES.md](./LAYER2_LAYER3_CAPABILITIES.md) - Full L2/L3 coverage
- [ENHANCED_VECTOR_SEARCH.md](./ENHANCED_VECTOR_SEARCH.md) - Multi-query search details
- [ENHANCED_SEARCH_QUICK_GUIDE.md](./ENHANCED_SEARCH_QUICK_GUIDE.md) - Quick validation
- [E2E_FLOW_EXTREME_KB.md](./E2E_FLOW_EXTREME_KB.md) - Similar E2E test example

---

**Test Version:** 1.0  
**Last Updated:** June 6, 2026  
**Status:** ✅ Ready to run
