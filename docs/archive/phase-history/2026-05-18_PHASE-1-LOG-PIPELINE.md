# Phase 1: Log Pipeline

**Duration**: 2-3 days  
**Difficulty**: Medium  
**Goal**: Build a working log ingestion pipeline from mock devices to dashboard

---

## 🎯 What You'll Build

```
┌─────────────┐      ┌─────────┐      ┌──────────┐      ┌──────────┐
│   Mock      │ ───▶ │  Kafka  │ ───▶ │ Logstash │ ───▶ │ Dashboard│
│ Log Generator│      │ (Broker)│      │ (Parser) │      │ (Grafana)│
└─────────────┘      └─────────┘      └──────────┘      └──────────┘
     Python            Messages         Structured         Visualize
   Simulates           Queue             JSON               Logs
   Network
   Devices
```

**By the end**: You'll see network logs flowing in real-time through your system!

---

## 📋 Components Overview

| Component | Purpose | Port |
|-----------|---------|------|
| **Mock Log Generator** | Simulates router/switch logs | - |
| **Kafka** | Message broker (buffer logs) | 9092 |
| **Kafka UI** | View Kafka messages | 8080 |
| **Logstash** | Parse logs into JSON | 5000 |
| **Elasticsearch** | Store logs | 9200 |
| **Grafana** | Dashboard | 3000 |

---

## 🏗️ Step-by-Step Implementation

### Step 1: Create Docker Infrastructure

Create `docker-compose.yml`:

```bash
cd ~/ng-iam/smart-noc
mkdir -p infrastructure/docker
cd infrastructure/docker
```

Create the compose file (I'll provide this separately).

---

### Step 2: Create Mock Log Generator

This simulates network devices sending logs:

```bash
cd ~/ng-iam/smart-noc
mkdir -p services/log-generator
cd services/log-generator
```

The generator will produce realistic logs like:
- Interface up/down events
- BGP session changes
- CPU/memory alerts
- Authentication failures
- Routing updates

---

### Step 3: Configure Logstash Pipeline

Logstash will parse raw logs into structured JSON:

**Input**: 
```
%LINK-3-UPDOWN: Interface GigabitEthernet0/1, changed state to down
```

**Output**:
```json
{
  "timestamp": "2026-04-23T10:30:45Z",
  "device": "router-01",
  "severity": "ERROR",
  "event_type": "INTERFACE_DOWN",
  "interface": "GigabitEthernet0/1",
  "message": "Interface changed state to down"
}
```

---

### Step 4: Start the Pipeline

```bash
# Start all services
docker compose up -d

# Check all containers are running
docker compose ps

# Expected output: All containers "Up"

# View logs
docker compose logs -f
```

---

### Step 5: Generate Sample Logs

```bash
# Activate Python environment
cd ~/ng-iam/smart-noc
source venv/bin/activate

# Run log generator
python services/log-generator/generate_logs.py

# You should see: "Sending log: ..."
```

---

### Step 6: Verify Log Flow

**Check Kafka**:
```bash
# Access Kafka UI
# Open browser: http://localhost:8080

# You should see:
# - Topic: "network-logs"
# - Messages flowing in
```

**Check Elasticsearch**:
```bash
# Query logs
curl http://localhost:9200/network-logs/_search?pretty

# Should return log entries
```

**Check Grafana**:
```bash
# Open browser: http://localhost:3000
# Login: admin / admin (change password)

# Add Elasticsearch data source:
# - URL: http://elasticsearch:9200
# - Index: network-logs

# Create a dashboard showing:
# - Log rate (logs/sec)
# - Events by severity
# - Events by device
# - Recent logs table
```

---

## 📊 Log Schema

All parsed logs follow this schema:

```json
{
  "timestamp": "ISO8601 datetime",
  "device_id": "string (e.g., router-01)",
  "device_type": "router|switch|firewall",
  "severity": "INFO|WARNING|ERROR|CRITICAL",
  "event_type": "string (e.g., INTERFACE_DOWN)",
  "interface": "string|null",
  "message": "string",
  "raw_log": "original syslog message",
  "tags": ["array", "of", "tags"]
}
```

---

## 🔬 Testing Scenarios

### Scenario 1: Interface Flapping
Generate rapid interface up/down events:

```bash
python services/log-generator/generate_logs.py --scenario interface_flap
```

**Expected**: Grafana shows spike in INTERFACE_DOWN/UP events

---

### Scenario 2: BGP Session Failure
Simulate BGP neighbor down:

```bash
python services/log-generator/generate_logs.py --scenario bgp_failure
```

**Expected**: See BGP_DOWN events correlated with routing changes

---

### Scenario 3: High CPU Alert
Generate CPU threshold alerts:

```bash
python services/log-generator/generate_logs.py --scenario high_cpu
```

**Expected**: CRITICAL severity logs appear

---

## 📈 Success Metrics

### Phase 1 is complete when you can:

- ✅ Generate 100+ logs/second without lag
- ✅ See logs in Kafka UI within 1 second
- ✅ Elasticsearch contains parsed logs
- ✅ Grafana dashboard shows real-time updates
- ✅ No errors in Docker logs (`docker compose logs`)

### Performance targets:
- Log ingestion latency: <100ms
- Parsing rate: 1000+ logs/sec
- Storage overhead: <1MB per 1000 logs

---

## 🛠️ Configuration Files

### Kafka Topics (auto-created):
```
network-logs          (raw logs)
network-logs-parsed   (after Logstash)
network-logs-dead-letter (failed parsing)
```

### Logstash Pipeline:
- Input: Kafka consumer
- Filter: Grok patterns + mutate
- Output: Elasticsearch + stdout (debug)

---

## 🐛 Troubleshooting

### Kafka not receiving logs

```bash
# Check Kafka broker health
docker compose exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092

# Manually produce a test message
docker compose exec kafka kafka-console-producer --bootstrap-server localhost:9092 --topic network-logs
# Type a message and press Enter
```

---

### Logstash not parsing

```bash
# Check Logstash logs
docker compose logs logstash

# Common issues:
# - Grok pattern mismatch
# - Kafka connection failure

# Test grok pattern
docker compose exec logstash bin/logstash -e '
input { stdin { } }
filter { 
  grok { 
    match => { "message" => "%{SYSLOG5424PRI}%{SYSLOGTIMESTAMP:syslog_timestamp}" }
  }
}
output { stdout { codec => rubydebug } }'
```

---

### High memory usage

```bash
# Check container resource usage
docker stats

# Reduce Kafka heap (in docker-compose.yml):
KAFKA_HEAP_OPTS: "-Xmx512M -Xms512M"

# Reduce Logstash workers:
LS_JAVA_OPTS: "-Xmx512m -Xms512m"
```

---

### Elasticsearch storage full

```bash
# Check indices
curl http://localhost:9200/_cat/indices?v

# Delete old indices
curl -X DELETE http://localhost:9200/network-logs-2026.04.01
```

---

## 📁 Project Files Created

After Phase 1, you should have:

```
smart-noc/
├── docker-compose.yml
├── services/
│   └── log-generator/
│       ├── generate_logs.py
│       ├── log_templates.py
│       └── requirements.txt
├── infrastructure/
│   └── logstash/
│       ├── pipeline/
│       │   └── network-logs.conf
│       └── config/
│           └── logstash.yml
└── configs/
    └── grafana/
        └── provisioning/
            └── dashboards/
                └── network-overview.json
```

---

## 🎓 Key Learnings

By completing Phase 1, you'll understand:

1. **Kafka basics**:
   - Topics, producers, consumers
   - Retention policies
   - Fault tolerance

2. **Log parsing**:
   - Grok patterns
   - Field extraction
   - Data enrichment

3. **Pipeline design**:
   - Decoupling with message queues
   - Backpressure handling
   - Dead letter queues

4. **Observability**:
   - Monitoring data flow
   - Identifying bottlenecks
   - Debugging pipelines

---

## 🚀 Next Step

**→ [Phase 2: Anomaly Detection](PHASE-2-ANOMALY-DETECTION.md)**

Now that logs are flowing, let's detect problems!

---

## 📝 Optional Enhancements

Before moving to Phase 2, you can:

1. **Add more log types**:
   - Firewall deny logs
   - DNS query logs
   - DHCP lease logs

2. **Improve parsing**:
   - Add GeoIP enrichment
   - Parse timestamps correctly
   - Add custom fields

3. **Better dashboards**:
   - Heatmaps
   - Alert annotations
   - Device topology view

4. **Performance tuning**:
   - Kafka partitioning
   - Logstash multi-pipeline
   - Elasticsearch sharding
