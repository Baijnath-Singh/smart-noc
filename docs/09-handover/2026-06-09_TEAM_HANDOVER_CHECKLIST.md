# Team Handover Checklist
## Smart NOC Setup Verification Guide

> **Purpose**: This checklist ensures Smart NOC is properly set up with all required resources before team demonstration or production use.

---

## ✅ Prerequisites Verification

Before running setup, ensure:

- [ ] **WSL2** installed and running
- [ ] **Docker Desktop** installed with WSL2 backend enabled
- [ ] **Python 3.8+** installed in WSL
- [ ] **Ollama 0.21.2+** installed on Windows with phi3 model pulled
- [ ] At least **20GB free disk space**

### Quick Commands:
```bash
# Check WSL version
wsl --version

# Check Docker
docker --version
docker compose version

# Check Python
python3 --version

# Check Ollama (from Windows PowerShell)
ollama --version
ollama list  # Should show phi3 model
```

---

## 🚀 Setup Execution

### Step 1: Run Setup Script
```bash
cd /mnt/c/Users/<your-username>/ng-iam/smart-noc
./setup-noc.sh
```

### Step 2: Monitor Output
Watch for these key checkpoints:

- [ ] ✓ All prerequisites verified
- [ ] ✓ Services built successfully
- [ ] ✓ Kafka container healthy (may require restart)
- [ ] ✓ PostgreSQL container healthy
- [ ] ✓ Elasticsearch container healthy
- [ ] ✓ Redis container healthy
- [ ] ✓ 4 Kafka topics created: network-logs, anomalies, incidents, incidents-diagnosed
- [ ] ✓ Application services started (anomaly-detector, correlation-engine, llm-diagnosis)
- [ ] ✓ Resource verification summary displayed

**Expected Duration**: 5-10 minutes (first run with image build)

---

## 📋 Resource Verification

### 1. Kafka Topics (4 Required)
```bash
docker compose exec kafka kafka-topics.sh --bootstrap-server kafka:19092 --list
```

**Expected Output**:
```
anomalies
incidents
incidents-diagnosed
network-logs
```

**Data Flow**:
- `network-logs`: log-generator → anomaly-detector
- `anomalies`: anomaly-detector → correlation-engine + logstash
- `incidents`: correlation-engine → llm-diagnosis
- `incidents-diagnosed`: llm-diagnosis → application output

---

### 2. PostgreSQL Tables (4 Required + Reference Data)
```bash
docker compose exec -T postgres psql -U noc_admin -d smart_noc -c "\dt"
```

**Expected Tables**:
- `incidents` - Main incident storage (22 columns)
- `incident_anomalies` - Many-to-many relationship with anomalies
- `incident_timeline` - Audit trail of incident status changes
- `incident_type_definitions` - Reference data (6 incident types)

**Verify Triggers**:
```bash
docker compose exec -T postgres psql -U noc_admin -d smart_noc -c "\df"
```

Expected functions:
- `update_updated_at_column()` - Auto-update timestamps
- `calculate_incident_duration()` - Auto-calculate incident duration
- `log_incident_status_change()` - Log status changes to timeline

---

### 3. Docker Containers (10 Required)
```bash
docker compose ps
```

**Expected Services** (all should show "healthy" or "running"):
1. `kafka` - Message broker (healthy)
2. `postgres` - Database (healthy)
3. `redis` - Cache (healthy)
4. `elasticsearch` - Search and analytics (healthy)
5. `logstash` - Data pipeline (running)
6. `grafana` - Visualization (running)
7. `kafka-ui` - Kafka management (running)
8. `anomaly-detector` - ML anomaly detection (running)
9. `correlation-engine` - Incident correlation (running)
10. `llm-diagnosis` - AI diagnosis (running)

**Note**: If kafka, postgres, or elasticsearch show "unhealthy", the setup script automatically restarts them.

---

### 4. Docker Volumes (3 Required)
```bash
docker volume ls --filter name=smart-noc
```

**Expected Volumes**:
- `smart-noc_postgres-data` - Database persistence
- `smart-noc_elasticsearch-data` - Search index persistence
- `smart-noc_kafka-data` - Message broker persistence

---

### 5. Elasticsearch Indices (Auto-Created)
```bash
docker compose exec elasticsearch curl -s http://localhost:9200/_cat/indices
```

**Note**: Indices are auto-created by Logstash when first data arrives. If empty initially, this is normal. Will populate after anomaly detection starts.

---

## 🧪 Functional Testing

### Test 1: Verify LLM Configuration
```bash
docker compose logs llm-diagnosis --tail 20
```

**Expected Output**:
```
Starting LLM Diagnosis service...
Provider: openai/phi3
Setting timeout: 180 seconds
Successfully connected to LLM service
```

**If you see errors**:
- Check Ollama is running on Windows: `ollama list` (from PowerShell)
- Verify phi3 model downloaded: Should show in list
- Check .env file: `LLM_API_BASE=http://host.docker.internal:11434/v1`

---

### Test 2: Generate Test Incidents (Optional)
```bash
cd services/log-generator
source ../../venv/bin/activate
python generate_scenarios.py --scenario chaos --count 5
```

**Expected Flow**:
1. Logs generated → `network-logs` topic
2. Anomaly detector processes → `anomalies` topic
3. Correlation engine creates incidents → `incidents` topic
4. LLM diagnosis service diagnoses → `incidents-diagnosed` topic

**Timeline**: 2-3 minutes per incident for phi3 diagnosis (timeout: 180s)

---

### Test 3: Check Database Incidents
```bash
docker compose exec -T postgres psql -U noc_admin -d smart_noc -c "SELECT incident_number, severity, status, incident_type FROM incidents ORDER BY created_at DESC LIMIT 5;"
```

**Expected Columns**:
- `incident_number` - Auto-generated (e.g., INC-2025-001)
- `severity` - critical, high, medium, low
- `status` - open, investigating, diagnosed, resolved, closed
- `incident_type` - NETWORK_PERFORMANCE, SECURITY_BREACH, etc.

---

### Test 4: Monitor AI Diagnosis
```bash
docker compose logs -f llm-diagnosis
```

**Expected Output** (per incident):
```
Processing incident: INC-2025-XXX
Making LLM API call with timeout 180s...
Response received in 155.32 seconds
✓ Updated incident INC-2025-XXX with diagnosis
```

**Troubleshooting**:
- If timeout errors occur: phi3 model may be too slow for hardware
- If connection errors: Check Ollama running in Windows
- If rate limit errors: Verify using local Ollama, not GitHub Models

---

## 🔍 Common Issues & Resolutions

### Issue 1: Kafka Container Unhealthy
**Symptoms**: `kafka` container shows "unhealthy" status

**Resolution**: Setup script auto-restarts unhealthy services. If persists:
```bash
docker compose restart kafka
sleep 30  # Wait for Kafka to be ready
```

---

### Issue 2: Missing Kafka Topics
**Symptoms**: Errors like "UNKNOWN_TOPIC_OR_PART" in logs

**Resolution**: Setup script creates all 4 topics automatically. To verify:
```bash
docker compose exec kafka kafka-topics.sh --bootstrap-server kafka:19092 --list
```

If missing, create manually:
```bash
docker compose exec kafka kafka-topics.sh --bootstrap-server kafka:19092 --create --topic network-logs --partitions 3 --replication-factor 1
# Repeat for: anomalies, incidents, incidents-diagnosed
```

---

### Issue 3: PostgreSQL Tables Not Created
**Symptoms**: Error "relation 'incidents' does not exist"

**Root Cause**: init.sql didn't run on first container start

**Resolution**:
```bash
docker compose down -v  # Remove volumes (WARNING: deletes data)
./setup-noc.sh  # Re-run setup
```

---

### Issue 4: Ollama Connection Failed
**Symptoms**: "Connection refused" or "Failed to connect to LLM service"

**Resolution**:
1. Check Ollama running on Windows:
   ```powershell
   # From Windows PowerShell
   ollama list
   ollama serve  # If not running
   ```

2. Verify phi3 model available:
   ```powershell
   ollama pull phi3  # If missing
   ```

3. Test Ollama API:
   ```bash
   curl http://host.docker.internal:11434/api/tags
   ```

---

### Issue 5: Slow LLM Response
**Symptoms**: Diagnosis takes 90+ seconds or timeout errors

**Current Setup**: phi3 with 180s timeout (working as expected)

**If too slow**: Consider increasing timeout in `.env`:
```bash
LLM_TIMEOUT=300  # Increase to 5 minutes
```

Then restart:
```bash
docker compose restart llm-diagnosis
```

---

## 🛑 Teardown Procedure

When finished with testing or development:

```bash
./teardown-noc.sh
```

**Interactive Mode**: Script asks for confirmation before each step
- Containers: yes/no
- Volumes: yes/no (WARNING: deletes all data)
- Networks: yes/no
- Orphan containers: yes/no

**Fast Mode**: Skip confirmations (use with caution)
```bash
./teardown-noc.sh --yes
```

---

## 📊 Expected Metrics

### Startup Times
- **First run** (with build): 5-10 minutes
- **Subsequent runs** (images cached): 2-3 minutes
- **Service health checks**: 30-60 seconds for infrastructure services

### Resource Usage
- **CPU**: 2-4 cores (phi3 uses 1-2 cores during diagnosis)
- **RAM**: 8-12 GB (phi3 requires ~2-4 GB)
- **Disk**: 15-20 GB (images ~5GB, volumes ~10GB, phi3 model ~2.3GB)

### Performance
- **Log generation**: ~100 logs/second
- **Anomaly detection**: Real-time (<1 second lag)
- **Incident correlation**: 1-5 seconds
- **AI diagnosis**: 120-180 seconds per incident (phi3 on typical hardware)

---

## 🎯 Success Criteria

Before handing over to team or demonstrating, verify:

- [ ] All 10 Docker containers running/healthy
- [ ] All 4 Kafka topics created and listed
- [ ] All 4 PostgreSQL tables exist with triggers
- [ ] 3 Docker volumes created for data persistence
- [ ] LLM service connected to Ollama phi3
- [ ] Test incident generated and diagnosed successfully
- [ ] Diagnosis completes within 180 seconds
- [ ] No error messages in service logs (anomaly-detector, correlation-engine, llm-diagnosis)
- [ ] Database can be queried successfully
- [ ] Teardown script can clean up environment

---

## 📚 Documentation Reference

- **Full Setup Guide**: [NOC_SETUP_GUIDE.md](NOC_SETUP_GUIDE.md)
- **Quick Reference**: [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- **Script Documentation**: [README_AUTOMATION.md](README_AUTOMATION.md)
- **Main README**: [README.md](README.md)

---

## 🆘 Getting Help

If issues persist after following this checklist:

1. **Check Service Logs**:
   ```bash
   docker compose logs [service-name] --tail 50
   ```

2. **Check System Resources**:
   ```bash
   docker system df  # Disk usage
   docker stats --no-stream  # CPU/RAM usage
   ```

3. **Complete Reset**:
   ```bash
   ./teardown-noc.sh --yes
   docker system prune -a  # WARNING: removes all Docker data
   ./setup-noc.sh
   ```

4. **Consult Documentation**: Check README files for detailed troubleshooting

---

## ✅ Team Handover Confirmation

Before sharing with team members, project lead should sign off:

- [ ] Tested complete setup from scratch
- [ ] Verified all resources created automatically
- [ ] Generated and diagnosed test incidents successfully
- [ ] Documented any environment-specific notes (hardware specs, timing expectations)
- [ ] Reviewed all scripts for security (credentials, exposed ports)
- [ ] Confirmed teardown works correctly

**Project Lead Signature**: _________________________

**Date**: _________________________

**Notes**:
