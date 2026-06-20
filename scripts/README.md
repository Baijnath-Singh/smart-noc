# Smart NOC Scripts

**Organization Date:** June 9, 2026  
**Purpose:** Organized collection of setup, testing, and utility scripts

---

## 📂 Directory Structure

```
scripts/
├── kb_tools/          # KB article creation & management
├── log_generators/    # Test log generation & sending
├── setup/             # System setup and initialization
├── teardown/          # Cleanup and teardown scripts  
├── testing/           # Test execution scripts
└── utilities/         # Helper tools and utilities
```

### 📚 KB Tools (`kb_tools/`)
Scripts for creating and managing knowledge base articles:
- **`kb_article_creator.py`** - Interactive KB article creator with LLM extraction
- **`import_kb_to_vector.sh`** - Import KB articles to ChromaDB
- **`llm_extractor.py`** - LLM-based article extraction from vendor docs
- **`article_validator.py`** - Validate KB article quality
- See [kb_tools/README_KB_TOOLS.md](kb_tools/README_KB_TOOLS.md) for details

### 📝 Log Generators (`log_generators/`)
Scripts for generating and sending test logs:
- **`send_test_logs.sh`** - Send syslog messages to Logstash (main test tool)
- **`generate-logs.sh`** - Generate synthetic network logs
- See [log_generators/README.md](log_generators/README.md) for usage

---

## 🚀 Setup Scripts (`scripts/setup/`)

### **Primary Setup**
- **`setup-noc.sh`** - Main Smart NOC setup (Linux/Mac)
  ```bash
  ./scripts/setup/setup-noc.sh
  ```
  - Sets up Docker Compose environment
  - Creates Kafka topics
  - Initializes PostgreSQL database
  - Seeds knowledge base with Extreme Networks articles
  - Verifies all services are running

- **`setup-noc.ps1`** - Main Smart NOC setup (Windows PowerShell)
  ```powershell
  .\scripts\setup\setup-noc.ps1
  ```

### **Component Setup**
- **`setup-vector-service.sh`** - Initialize ChromaDB vector database (Linux/Mac)
- **`setup-vector-service.ps1`** - Initialize ChromaDB vector database (Windows)
- **`create-kafka-topics.sh`** - Create required Kafka topics
  - `network-logs` - Raw network log ingestion
  - `anomalies` - Detected anomalies
  - `incidents` - Correlated incidents
  - `incidents-diagnosed` - Diagnosed incidents with remediation plans

### **Verification**
- **`verify-status.sh`** - Check system health and service status
  ```bash
  ./scripts/setup/verify-status.sh
  ```
  - Verifies all Docker containers running
  - Checks Kafka topics exist
  - Validates PostgreSQL connectivity
  - Tests vector database connection

---

## 🧹 Teardown Scripts (`scripts/teardown/`)

- **`teardown-noc.sh`** - Complete system teardown (Linux/Mac)
  ```bash
  ./scripts/teardown/teardown-noc.sh
  ```
  - Stops all Docker containers
  - Removes Docker volumes (optional)
  - Cleans up temporary files

- **`teardown-noc.ps1`** - Complete system teardown (Windows)

- **`cleanup-and-test.sh`** - Clean environment and run tests
  ```bash
  ./scripts/teardown/cleanup-and-test.sh
  ```
  - Performs full cleanup
  - Restarts services
  - Runs validation tests

---

## 🧪 Testing Scripts (`scripts/testing/`)

### **Phase-Based Tests**
- **`test-phase1.sh`** - Phase 1: Log Pipeline & Anomaly Detection
  ```bash
  ./scripts/testing/test-phase1.sh
  ```
  - Tests Logstash → Kafka → Anomaly Detector pipeline
  - Validates anomaly detection accuracy
  - Checks database insertions

- **`test-phase2-e2e.sh`** - Phase 2: Full E2E test (Correlation + LLM Diagnosis)
  ```bash
  ./scripts/testing/test-phase2-e2e.sh
  ```
  - End-to-end test of entire pipeline
  - Tests vector search integration
  - Validates LLM diagnosis generation
  - Checks remediation plan quality

- **`test-phase2-simple.sh`** - Phase 2: Simplified correlation test
- **`test-phases.sh`** - Run all phase tests sequentially

### **Feature-Specific Tests**
- **`run_vlan_trunk_e2e_test.sh`** - VLAN trunk misconfiguration E2E test
  ```bash
  ./scripts/testing/run_vlan_trunk_e2e_test.sh
  ```
  - Tests VLAN trunk failure detection
  - Validates Extreme Networks KB article retrieval
  - Checks diagnosis accuracy for VLAN issues

- **`test_vlan_trunk_mismatch_e2e.py`** - Python-based VLAN trunk test
  ```bash
  python scripts/testing/test_vlan_trunk_mismatch_e2e.py
  ```
  - Programmatic E2E test
  - Validates entire pipeline with VLAN scenarios
  - Generates detailed test report

---

## 🔧 Utility Scripts (`scripts/utilities/`)

### **Knowledge Base Management**
- **`add_kb_article.py`** - Add new knowledge base article
  ```bash
  python scripts/utilities/add_kb_article.py \
    --id "EXT-030" \
    --title "EXOS Interface Flapping Issues" \
    --content "..." \
    --vendor "extreme" \
    --platform "exos"
  ```

- **`update_kb_article.py`** - Update existing KB article
  ```bash
  python scripts/utilities/update_kb_article.py \
    --id "EXT-019" \
    --content "Updated troubleshooting steps..."
  ```

- **`query_chromadb.py`** - Query vector database
  ```bash
  python scripts/utilities/query_chromadb.py \
    --query "VLAN trunk misconfiguration" \
    --collection "knowledge_base"
  ```

### **Testing & Validation**
- **`test_e2e_extreme_kb.py`** - E2E test with Extreme Networks KB
- **`test_enhanced_search.py`** - Test multi-query vector search
- **`test_exos_enhanced_search.py`** - Test EXOS-specific search
- **`test_exos_kb.py`** - Test EXOS knowledge base retrieval
- **`test_search_in_container.py`** - Container-based search test
- **`test-semantic-search.py`** - Semantic similarity search test

### **Data Management**
- **`populate-test-lessons.py`** - Populate test remediation lessons
  ```bash
  python scripts/utilities/populate-test-lessons.py
  ```
  - Adds sample remediation history
  - Seeds past incident lessons
  - Used for testing learning features

### **Operations**
- **`check_incidents.py`** - Check incident status in database
  ```bash
  python scripts/utilities/check_incidents.py --last 10
  ```

- **`fix_dashboard_datasource.py`** - Fix Grafana datasource configuration
  ```bash
  python scripts/utilities/fix_dashboard_datasource.py
  ```

---

## 📊 Test Data (`../test-data/`)

### **Incidents** (`test-data/incidents/`)
- **`test-bgp-incident.sql`** - Sample BGP peering failure incident
- **`test_feedback_data.sql`** - Confidence calibration feedback samples

### **Logs** (`test-data/logs/`)
- **`test-bgp-log.json`** - BGP log sample for testing
- **`test-log.json`** - Generic network log sample
- **`test-flapping.json`** - Interface flapping log data
- **`test-flapping-incident.json`** - Flapping incident data

**Usage:**
```bash
# Load test incident
docker-compose exec -T postgres psql -U noc_admin -d smart_noc < test-data/incidents/test-bgp-incident.sql

# Send test log to Logstash
curl -X POST http://localhost:5000 -H "Content-Type: application/json" -d @test-data/logs/test-bgp-log.json
```

---

## 🗄️ Archive (`../archive/`)

Historical or obsolete files no longer in active use:
- **`log_pipeline_exercise.txt`** - Old log pipeline exercise documentation

---

## 🎯 Common Workflows

### **1. Initial Setup**
```bash
# Clone repository
git clone <repo-url>
cd smart-noc

# Run setup
./scripts/setup/setup-noc.sh

# Verify everything works
./scripts/setup/verify-status.sh

# Run tests
./scripts/testing/test-phases.sh
```

### **2. Add Knowledge Base Article**
```bash
# Add new Extreme Networks article
python scripts/utilities/add_kb_article.py \
  --id "EXT-050" \
  --title "VOSS BGP Configuration Best Practices" \
  --content "$(cat my-article.md)" \
  --vendor "extreme" \
  --platform "voss"

# Test retrieval
python scripts/utilities/query_chromadb.py \
  --query "BGP configuration VOSS"
```

### **3. Run E2E Test**
```bash
# Full end-to-end test
./scripts/testing/test-phase2-e2e.sh

# Check results
python scripts/utilities/check_incidents.py --last 5
```

### **4. Clean Restart**
```bash
# Full cleanup
./scripts/teardown/teardown-noc.sh

# Fresh setup
./scripts/setup/setup-noc.sh

# Verify
./scripts/setup/verify-status.sh
```

---

## 🔍 Troubleshooting

### **Permission Denied**
```bash
# Make scripts executable
chmod +x scripts/setup/*.sh
chmod +x scripts/testing/*.sh
chmod +x scripts/teardown/*.sh
```

### **Docker Not Running**
```bash
# Start Docker
sudo systemctl start docker

# Verify
docker ps
```

### **Services Not Starting**
```bash
# Check logs
docker-compose logs <service-name>

# Restart specific service
docker-compose restart <service-name>

# Full restart
./scripts/teardown/teardown-noc.sh
./scripts/setup/setup-noc.sh
```

### **Kafka Topics Missing**
```bash
# Recreate topics
./scripts/setup/create-kafka-topics.sh

# Verify topics
docker-compose exec kafka kafka-topics.sh --bootstrap-server localhost:9092 --list
```

### **Vector Database Empty**
```bash
# Reinitialize vector service
./scripts/setup/setup-vector-service.sh

# Verify articles loaded
python scripts/utilities/query_chromadb.py --query "test" --collection "knowledge_base"
```

---

## 📝 Script Development Guidelines

### **Adding New Scripts**

**Setup/Teardown Scripts** → `scripts/setup/` or `scripts/teardown/`
- Use `.sh` for Linux/Mac, `.ps1` for Windows
- Include error handling (`set -e` for bash)
- Add verification steps
- Document in this README

**Test Scripts** → `scripts/testing/`
- Prefix with `test-` for shell scripts
- Prefix with `test_` for Python scripts
- Include clear success/failure messages
- Return appropriate exit codes

**Utility Scripts** → `scripts/utilities/`
- Use descriptive names
- Include `--help` flag
- Add to this README with usage examples

### **Best Practices**
1. ✅ Always use absolute paths or `cd $(dirname $0)/..` to handle relative paths
2. ✅ Add error handling and validation
3. ✅ Include usage examples in comments
4. ✅ Make scripts idempotent (can run multiple times safely)
5. ✅ Log important actions
6. ✅ Return meaningful exit codes

---

## 📚 Related Documentation

- **Main README**: [../README.md](../README.md)
- **Setup Guide**: [../docs/01-getting-started/2026-05-01_NOC_SETUP_GUIDE.md](../docs/01-getting-started/2026-05-01_NOC_SETUP_GUIDE.md)
- **Testing Guide**: [../docs/04-testing/2026-05-25_TESTING_GUIDE.md](../docs/04-testing/2026-05-25_TESTING_GUIDE.md)
- **Troubleshooting**: [../docs/05-operations/2026-06-01_TROUBLESHOOTING.md](../docs/05-operations/2026-06-01_TROUBLESHOOTING.md)

---

**Organization Date**: June 9, 2026  
**Maintained By**: Smart NOC Team (Extreme Networks)  
**Last Updated**: June 9, 2026
