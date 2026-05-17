# End-to-End Validation Steps
## Smart NOC System Verification

> **Quick Reference**: Step-by-step commands to validate your Smart NOC setup from scratch

---

## 🚀 Phase 1: Clean Setup (5-10 minutes)

```bash
# Navigate to project directory
cd /mnt/c/Users/baisingh/ng-iam/smart-noc

# Stop everything
docker compose down

# Run setup script - THIS IS THE ONLY COMMAND YOUR TEAM NEEDS!
# It handles everything: builds images, starts services, creates Kafka topics, verifies health
./setup-noc.sh

# ✅ Expected: "✓ Setup Duration: Xm Ys" with resource verification summary
# The script automatically creates all 4 Kafka topics and verifies them
```

---

## ✅ Phase 2: Verify Infrastructure (2-3 minutes)

### 2.1 Check All Containers (10 services expected)

```bash
docker compose ps
```

**Expected Status:**
- ✓ `kafka` - healthy
- ✓ `postgres` - healthy
- ✓ `redis` - healthy
- ✓ `elasticsearch` - healthy
- ✓ `logstash` - running
- ✓ `grafana` - running
- ✓ `kafka-ui` - running
- ✓ `anomaly-detector` - running
- ✓ `correlation-engine` - running
- ✓ `llm-diagnosis` - running

---

### 2.2 Verify Kafka Topics (4 required)

```bash
docker compose exec kafka /opt/kafka/bin/kafka-topics.sh \
  --bootstrap-server localhost:9092 \
  --list
```

**Expected Output:**
```
anomalies
incidents
incidents-diagnosed
network-logs
```

**What Each Topic Does:**
- `network-logs`: log-generator → anomaly-detector
- `anomalies`: anomaly-detector → correlation-engine + logstash
- `incidents`: correlation-engine → llm-diagnosis
- `incidents-diagnosed`: llm-diagnosis → application output

---

### 2.3 Verify PostgreSQL Tables (4 required)

```bash
docker compose exec -T postgres psql -U noc_admin -d smart_noc -c "\dt"
```

**Expected Tables:**
- `incidents` - Main incident storage (22 columns)
- `incident_anomalies` - Many-to-many relationship
- `incident_timeline` - Audit trail
- `incident_type_definitions` - Reference data (6 incident types)

**Check Table Counts:**
```bash
docker compose exec -T postgres psql -U noc_admin -d smart_noc -c \
  "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;"
```

---

### 2.4 Verify LLM Configuration

```bash
docker compose logs llm-diagnosis --tail 20
```

**Expected Output:**
```
Starting LLM Diagnosis service...
Provider: openai/phi3
Setting timeout: 180 seconds
Successfully connected to LLM service
Waiting for incidents...
```

**If Errors Seen:**
- Check Ollama running: `ollama list` (from Windows PowerShell)
- Verify phi3 model: Should appear in list
- Check .env: `cat .env | grep LLM_`

---

## 🧪 Phase 3: Test Data Flow (5 minutes)

### 3.1 Check Baseline

```bash
docker compose exec -T postgres psql -U noc_admin -d smart_noc -c \
  "SELECT COUNT(*) as total_incidents FROM incidents;"
```

**Expected:** 0 or very low number

---

### 3.2 Generate Test Incident

```bash
cd services/log-generator
source ../../venv/bin/activate
python generate_scenarios.py --scenario chaos --count 1
```

**Expected Output:**
```
Generated X anomalies for device core-router-01
Sent to Kafka topic: network-logs
```

---

### 3.3 Wait for Processing

```bash
cd ../..
echo "⏳ Waiting 15 seconds for anomaly detection and correlation..."
sleep 15
```

---

### 3.4 Verify Anomaly Detection

```bash
docker compose exec kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic anomalies \
  --from-beginning \
  --max-messages 3 \
  --timeout-ms 5000
```

**Expected:** JSON messages with:
- `anomaly_type`
- `device_id`
- `severity`
- `timestamp`

---

### 3.5 Verify Incident Created

```bash
docker compose exec -T postgres psql -U noc_admin -d smart_noc -c \
  "SELECT incident_number, status, severity, incident_type, 
          LEFT(title, 50) as title_preview,
          created_at 
   FROM incidents 
   ORDER BY created_at DESC 
   LIMIT 1;"
```

**Expected:** 1 new incident with:
- `status` = 'open' or 'investigating'
- `incident_number` = INC-2026-XXX
- `severity` = critical/high/medium/low
- `incident_type` = DEVICE_FAILURE, NETWORK_PERFORMANCE, etc.

---

## 🤖 Phase 4: Validate AI Diagnosis (3-5 minutes)

### 4.1 Monitor LLM Service (Open in separate terminal)

```bash
docker compose logs -f llm-diagnosis
```

**Keep this running** to watch diagnosis progress in real-time.

---

### 4.2 Check Incident Before Diagnosis

```bash
docker compose exec -T postgres psql -U noc_admin -d smart_noc -c \
  "SELECT incident_number, status, root_cause 
   FROM incidents 
   WHERE root_cause IS NULL 
   ORDER BY created_at DESC 
   LIMIT 1;"
```

**Expected:** Incident exists with `root_cause` = NULL (not yet diagnosed)

---

### 4.3 Wait for AI Diagnosis

```bash
echo "⏳ Waiting 180 seconds for LLM diagnosis (phi3 typical time: 120-180s)..."
echo "📺 Watch the llm-diagnosis logs in other terminal for progress"
sleep 180
```

**Expected in Logs (other terminal):**
```
Processing incident: INC-2026-XXX
Generating diagnosis...
Making LLM API call with timeout 180s...
Response received in 155.32 seconds
✓ Updated incident INC-2026-XXX with diagnosis
```

---

### 4.4 Verify Diagnosis Saved

```bash
docker compose exec -T postgres psql -U noc_admin -d smart_noc -c \
  "SELECT incident_number, 
          status,
          LEFT(root_cause, 100) as root_cause_preview,
          LEFT(remediation_plan, 100) as remediation_preview,
          diagnosed_at
   FROM incidents 
   WHERE root_cause IS NOT NULL 
   ORDER BY created_at DESC 
   LIMIT 1;"
```

**Expected:**
- `status` = 'diagnosed'
- `root_cause` = Detailed analysis from phi3 AI
- `remediation_plan` = Step-by-step fix instructions
- `diagnosed_at` = Recent timestamp

---

## 📊 Phase 5: Verify Complete Workflow (2 minutes)

### 5.1 Check Incident Timeline (Audit Trail)

```bash
docker compose exec -T postgres psql -U noc_admin -d smart_noc -c \
  "SELECT i.incident_number, 
          t.event_type, 
          t.previous_status, 
          t.new_status, 
          t.event_timestamp
   FROM incident_timeline t
   JOIN incidents i ON i.id = t.incident_id
   ORDER BY t.event_timestamp DESC
   LIMIT 5;"
```

**Expected:** Status transitions like:
- open → investigating
- investigating → diagnosed

---

### 5.2 Check Incident-Anomaly Relationships

```bash
docker compose exec -T postgres psql -U noc_admin -d smart_noc -c \
  "SELECT i.incident_number, 
          ia.anomaly_id, 
          ia.confidence_score,
          ia.linked_at
   FROM incidents i
   JOIN incident_anomalies ia ON i.id = ia.incident_id
   ORDER BY i.created_at DESC
   LIMIT 5;"
```

**Expected:** Links between incidents and their associated anomalies

---

### 5.3 Verify Diagnosed Incidents Topic

```bash
docker compose exec kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic incidents-diagnosed \
  --from-beginning \
  --max-messages 1 \
  --timeout-ms 5000
```

**Expected:** JSON with:
- `incident_number`
- `root_cause`
- `remediation_plan`
- `diagnosed_at`

---

## 📈 Phase 6: Performance & Metrics (2 minutes)

### 6.1 Check Resource Usage

```bash
docker stats --no-stream
```

**Expected:** Total <12GB RAM, reasonable CPU usage

---

### 6.2 Verify Kafka Consumer Lag (Should be Low)

```bash
docker compose exec kafka /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --describe \
  --all-groups
```

**Expected:** LAG column = 0 or very small numbers (< 10)

---

### 6.3 Check Elasticsearch Indices

```bash
docker compose exec elasticsearch curl -s http://localhost:9200/_cat/indices
```

**Expected:** Some indices with anomaly data (may be empty initially - this is OK, will populate over time)

---

### 6.4 Final Incident Statistics

```bash
docker compose exec -T postgres psql -U noc_admin -d smart_noc -c \
  "SELECT 
     COUNT(*) as total_incidents,
     COUNT(CASE WHEN root_cause IS NOT NULL THEN 1 END) as diagnosed,
     COUNT(CASE WHEN status='open' THEN 1 END) as open,
     COUNT(CASE WHEN status='investigated' THEN 1 END) as investigated,
     COUNT(CASE WHEN status='diagnosed' THEN 1 END) as diagnosed_status
   FROM incidents;"
```

**Expected:**
- `total_incidents` ≥ 1
- `diagnosed` ≥ 1
- `diagnosed_status` ≥ 1

---

## 🔥 Phase 7: Stress Test (Optional, 5-10 minutes)

### 7.1 Generate Multiple Scenarios

```bash
cd services/log-generator
source ../../venv/bin/activate

echo "🔥 Generating multiple test scenarios..."

# Interface flapping (connectivity issues)
python generate_scenarios.py --scenario flapping --count 6
sleep 10

# Brute force attacks (security)
python generate_scenarios.py --scenario brute-force --count 10
sleep 10

# High CPU (performance)
python generate_scenarios.py --scenario high-cpu --count 8

echo "⏳ Waiting 30s for correlation..."
sleep 30
```

---

### 7.2 Check Incident Distribution

```bash
cd ../..
docker compose exec -T postgres psql -U noc_admin -d smart_noc -c \
  "SELECT incident_type, 
          severity,
          COUNT(*) as count
   FROM incidents 
   GROUP BY incident_type, severity 
   ORDER BY COUNT(*) DESC;"
```

**Expected:** Multiple incidents of different types:
- CONNECTIVITY_ISSUE (from flapping)
- SECURITY_BREACH (from brute-force)
- NETWORK_PERFORMANCE (from high-cpu)

---

### 7.3 Monitor AI Diagnosis Queue

```bash
docker compose exec -T postgres psql -U noc_admin -d smart_noc -c \
  "SELECT 
     COUNT(CASE WHEN status='open' THEN 1 END) as pending_diagnosis,
     COUNT(CASE WHEN status='diagnosed' THEN 1 END) as diagnosed,
     COUNT(*) as total
   FROM incidents;"
```

**Note:** AI diagnosis processes incidents sequentially (120-180s each), so `pending_diagnosis` may remain high for a while.

---

## ✅ Success Criteria Checklist

Mark each item as you validate:

- [ ] **Setup script completed** without errors
- [ ] **All 10 services** healthy/running
- [ ] **4 Kafka topics** created (network-logs, anomalies, incidents, incidents-diagnosed)
- [ ] **4 PostgreSQL tables** exist (incidents, incident_anomalies, incident_timeline, incident_type_definitions)
- [ ] **LLM connected** to Ollama phi3 (logs show "Provider: openai/phi3")
- [ ] **Anomalies detected** and sent to Kafka topic
- [ ] **Incident created** in database (INC-2026-XXX format)
- [ ] **AI diagnosis completed** within 180 seconds
- [ ] **Root cause** and **remediation plan** populated in database
- [ ] **Timeline tracked** status changes (open → investigating → diagnosed)
- [ ] **Kafka consumer lag** is low (<10)
- [ ] **System stable** under load (stress test optional)

---

## 🆘 Quick Troubleshooting

### Service Not Healthy

```bash
# Check logs
docker compose logs [service-name] --tail 50

# Restart service
docker compose restart [service-name]
sleep 30  # Wait for health check
docker compose ps
```

---

### Kafka Commands Not Found

All Kafka commands require full path for `apache/kafka:3.7.0` image:

```bash
# ✓ CORRECT:
docker compose exec kafka /opt/kafka/bin/kafka-topics.sh ...

# ✗ WRONG:
docker compose exec kafka kafka-topics.sh ...
```

---

### Ollama Connection Failed

From **Windows PowerShell**:

```powershell
# Check Ollama running
ollama list

# If not running, start Ollama service
# (It should auto-start, but you can restart it)

# Verify phi3 model exists
ollama pull phi3  # If missing
```

From **WSL/Linux**:

```bash
# Test Ollama API from Docker
curl http://host.docker.internal:11434/api/tags
```

---

### No Incidents Created

```bash
# Check anomaly-detector logs
docker compose logs anomaly-detector --tail 50

# Check correlation-engine logs
docker compose logs correlation-engine --tail 50

# Verify Kafka topics have data
docker compose exec kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic network-logs \
  --from-beginning \
  --max-messages 10 \
  --timeout-ms 5000
```

---

### AI Diagnosis Not Running

```bash
# Check llm-diagnosis logs for errors
docker compose logs llm-diagnosis --tail 50

# Verify configuration
docker compose exec -T llm-diagnosis printenv | grep LLM_

# Expected:
# LLM_PROVIDER=openai
# LLM_MODEL=phi3
# LLM_API_BASE=http://host.docker.internal:11434/v1
# LLM_TIMEOUT=180

# Restart service
docker compose restart llm-diagnosis
```

---

## 🛑 Clean Shutdown

```bash
# Interactive teardown (asks for confirmation)
./teardown-noc.sh

# Fast teardown (no confirmations)
./teardown-noc.sh --yes
```

---

## 📊 Expected Performance Metrics

### Timing
- **Setup**: 5-10 minutes (first run with image build)
- **Anomaly Detection**: <5 seconds per log batch
- **Incident Correlation**: 5-15 seconds
- **AI Diagnosis**: 120-180 seconds per incident (phi3 on typical hardware)
- **Total for 1 incident**: ~3-5 minutes end-to-end

### Resource Usage
- **CPU**: 2-4 cores (phi3 uses 1-2 cores during diagnosis)
- **RAM**: 8-12 GB total
- **Disk**: 15-20 GB (images ~5GB, volumes ~10GB, phi3 model ~2.3GB)

---

## 📚 Additional Documentation

- **Full Setup Guide**: [NOC_SETUP_GUIDE.md](NOC_SETUP_GUIDE.md)
- **Team Handover**: [TEAM_HANDOVER_CHECKLIST.md](TEAM_HANDOVER_CHECKLIST.md)
- **Quick Reference**: [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- **Automation Scripts**: [README_AUTOMATION.md](README_AUTOMATION.md)

---

## ✅ Validation Complete!

Once all phases pass and checklist items are marked:

1. **Your system is production-ready** ✓
2. **Safe to share with team** ✓
3. **Ready for demonstration** ✓

**Next Steps:**
- Generate test scenarios for demo
- Prepare presentation materials
- Document any environment-specific notes
- Train team members on setup script usage

---

**Questions or Issues?** Review [TEAM_HANDOVER_CHECKLIST.md](TEAM_HANDOVER_CHECKLIST.md) for detailed troubleshooting and common issues.
