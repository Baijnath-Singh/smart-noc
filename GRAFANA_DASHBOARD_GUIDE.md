# 📊 Smart NOC - Grafana Incident Dashboard Guide

## 🚀 Quick Start

### Step 1: Import Dashboard to Grafana

**Manual Import (Recommended):**

1. Open Grafana: **http://localhost:3000**
2. Login with credentials: `admin` / `admin` (or your custom password)
3. Navigate to **Dashboards** → **Import** (+ icon → Import)
4. Click **Upload JSON file**
5. Select file: `dashboards/smart-noc-incidents-dashboard.json`
6. Configure datasource:
   - **Elasticsearch datasource:** Select `elasticsearch` from dropdown
7. Click **Import**
8. Dashboard URL: **http://localhost:3000/d/smart-noc-incidents**

---

## 🎨 Dashboard Overview

### **11 Visualization Panels**

#### **Top Row - Key Metrics (4 Stat Panels)**
1. **Total Incidents** - Cumulative count of all incidents
   - Color thresholds: Green (<10), Yellow (10-50), Orange (50-100), Red (>100)

2. **Active Incidents** - Count of ACTIVE or INVESTIGATING status
   - Filter: `status:ACTIVE OR status:INVESTIGATING`
   - Color thresholds: Green (<5), Yellow (5-20), Red (>20)

3. **Critical Incidents** - Count of CRITICAL severity
   - Filter: `severity:CRITICAL`
   - Color: Red when >0

4. **Total Devices Affected** - Sum of `affected_device_count`
   - Shows infrastructure impact scope

#### **Middle Row - Trends & Distributions**
5. **Incident Timeline by Type** (Time Series Bar Chart)
   - X-axis: Time (auto-interval based on range)
   - Y-axis: Incident count
   - Stacked by: `incident_type`
   - Shows incident creation rate over time

6. **Incidents by Type** (Pie Chart)
   - DEVICE_FAILURE
   - NETWORK_PERFORMANCE
   - SECURITY_BREACH
   - CONNECTIVITY_ISSUE
   - UNKNOWN
   - Legend: Shows count and percentage

7. **Incidents by Severity** (Donut Chart)
   - CRITICAL (Dark Red)
   - HIGH (Dark Orange)
   - MEDIUM (Dark Yellow)
   - LOW (Dark Green)
   - Legend: Shows count and percentage

#### **Lower Row - Device & Correlation Analysis**
8. **Top 10 Devices by Incident Count** (Horizontal Bar Chart)
   - Aggregation: `primary_device.keyword`
   - Sorted by incident count (descending)
   - Identifies problematic devices

9. **Incident Status Distribution** (Pie Chart)
   - ACTIVE (Red text)
   - INVESTIGATING (Orange text)
   - RESOLVED (Blue text)
   - CLOSED (Green text)
   - Shows incident lifecycle state

10. **Correlation Method Distribution** (Donut Chart)
    - PATTERN_BASED
    - TIME_BASED
    - MULTI_METHOD
    - Shows correlation engine effectiveness

#### **Bottom Row - Detailed Table**
11. **Recent Incidents (Last 20)** (Table)
    - Columns:
      - `incident_number` (clickable ID)
      - `incident_type`
      - `severity` (color-coded background)
      - `status` (color-coded text)
      - `affected_device_count`
      - `anomaly_count`
      - `primary_device`
      - `correlation_method`
      - `impact_score`
      - `created_at` (timestamp)
    - Sorted by: `created_at DESC`
    - Auto-refresh: Every 5 seconds

---

## ⚙️ Dashboard Settings

### Refresh Rate
- **Auto-refresh:** Every 5 seconds (configurable in top-right dropdown)
- **Time range:** Last 1 hour (default)
- **Adjustable:** 5m, 15m, 30m, 1h, 3h, 6h, 12h, 24h, 7d, 30d

### Elasticsearch Configuration
- **Index pattern:** `incidents-*`
- **Time field:** `@timestamp`
- **Document ID:** `incident_id` (UUID)

---

## 🧪 Testing Dashboard with Scenarios

### Test 1: Generate DEVICE_FAILURE Incidents

```bash
cd /mnt/c/Users/baisingh/ng-iam/smart-noc/services/log-generator
source ../../venv/bin/activate

# Generate 5 device failures
python generate_scenarios.py --scenario chaos --count 10

# Wait 10 seconds
sleep 10
```

**Expected Dashboard Changes:**
- ✅ **Total Incidents** increases by 5-10
- ✅ **Incidents by Type** - DEVICE_FAILURE segment grows
- ✅ **Incident Timeline** - spike at current time
- ✅ **Recent Incidents Table** - new rows appear with DEVICE_FAILURE type

---

### Test 2: Generate SECURITY_BREACH Incidents

```bash
# Generate brute force attacks
python generate_scenarios.py --scenario brute-force --count 15

# Wait 10 seconds
sleep 10
```

**Expected Dashboard Changes:**
- ✅ **Active Incidents** increases (new incidents start as ACTIVE)
- ✅ **Incidents by Type** - SECURITY_BREACH segment appears/grows
- ✅ **Incidents by Severity** - HIGH severity increases (brute force = HIGH)
- ✅ **Top 10 Devices** - dist-switch-02 count increases

---

### Test 3: Generate HIGH SEVERITY Burst

```bash
# Generate multiple scenario types simultaneously
python generate_scenarios.py --scenario flapping --count 8 &
python generate_scenarios.py --scenario brute-force --count 12 &
python generate_scenarios.py --scenario high-cpu --count 6 &
wait

# Wait 15 seconds for correlation
sleep 15
```

**Expected Dashboard Changes:**
- ✅ **Total Incidents** increases by 10-15
- ✅ **Critical Incidents** may increase (depending on severity calculation)
- ✅ **Incidents by Type** - Multiple segments grow (DEVICE_FAILURE, SECURITY_BREACH, NETWORK_PERFORMANCE)
- ✅ **Incident Timeline** - large spike at current time
- ✅ **Correlation Method** - PATTERN_BASED dominates

---

### Test 4: Watch Real-Time Correlation

```bash
# Start continuous log generation (1 log/second for 5 minutes)
python generate_logs.py --rate 60 --duration 300 &

# Monitor dashboard in browser - watch metrics update every 5 seconds
# Open: http://localhost:3000/d/smart-noc-incidents
```

**Expected Dashboard Behavior:**
- ✅ **Auto-refresh** every 5 seconds
- ✅ **Incident Timeline** shows gradual increase over 5 minutes
- ✅ **Recent Incidents Table** continuously updates with new incidents
- ✅ **Total Devices Affected** increases as anomalies spread across infrastructure

---

## 🔍 Dashboard Verification Checklist

### ✅ Data Flow Validation

```bash
cd /mnt/c/Users/baisingh/ng-iam/smart-noc

# 1. Check Elasticsearch indices
curl -s 'http://localhost:9200/_cat/indices/incidents-*?v'

# 2. Verify incident count
curl -s 'http://localhost:9200/incidents-*/_count' | jq

# 3. Sample incident document
curl -s 'http://localhost:9200/incidents-*/_search?size=1' | jq '.hits.hits[0]._source'

# 4. Check Grafana can query Elasticsearch
curl -s 'http://localhost:3000/api/datasources' | jq '.[] | select(.type=="elasticsearch") | {name, url, access}'
```

**Expected Results:**
- Elasticsearch: `incidents-2026.04.25` index exists with documents
- Incident count: Matches PostgreSQL count (±1-2 due to indexing delay)
- Sample document: Contains all fields (incident_number, type, severity, etc.)
- Grafana datasource: `elasticsearch` datasource configured with URL `http://elasticsearch:9200`

---

## 🎨 Panel Customization

### Change Color Thresholds

**Example: Make Critical Incidents threshold more sensitive**

1. Edit dashboard (top-right ⚙️ icon → Edit)
2. Select **Critical Incidents** panel
3. Click panel menu (3 dots) → **Edit**
4. Go to **Field** tab → **Thresholds**
5. Modify steps:
   - Green: `null` → Change to `0`
   - Yellow: `5` → Change to `3`
   - Red: `20` → Change to `10`
6. **Apply** → **Save dashboard**

---

### Add Custom Panel: Average Impact Score

1. **Add panel** (top-right + icon)
2. Select **Visualization:** Stat
3. **Query:**
   ```
   Metric: Average (field: impact_score)
   Bucket aggregation: Date Histogram (@timestamp, auto)
   ```
4. **Panel title:** "Average Incident Impact"
5. **Thresholds:**
   - Green: 0-30 (Low impact)
   - Yellow: 30-50 (Medium impact)
   - Orange: 50-70 (High impact)
   - Red: 70+ (Critical impact)
6. **Apply** → **Save**

---

## 📈 Useful Elasticsearch Queries

### Query 1: Find High-Impact Incidents

```bash
curl -s 'http://localhost:9200/incidents-*/_search' \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "range": {
        "impact_score": {
          "gte": 60
        }
      }
    },
    "sort": [{"impact_score": "desc"}],
    "size": 10
  }' | jq '.hits.hits[]._source | {incident_number, incident_type, impact_score, affected_devices}'
```

---

### Query 2: Incidents by Device

```bash
curl -s 'http://localhost:9200/incidents-*/_search' \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "term": {
        "primary_device.keyword": "dist-switch-02"
      }
    },
    "size": 5
  }' | jq '.hits.hits[]._source | {incident_number, incident_type, severity, anomaly_count}'
```

---

### Query 3: Incidents Created Today

```bash
curl -s 'http://localhost:9200/incidents-*/_search' \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "range": {
        "created_at": {
          "gte": "now/d"
        }
      }
    },
    "aggs": {
      "types": {
        "terms": {
          "field": "incident_type.keyword"
        }
      }
    },
    "size": 0
  }' | jq '{total: .hits.total.value, by_type: .aggregations.types.buckets}'
```

---

## 🐛 Troubleshooting

### Issue: Dashboard shows "No data"

**Check:**
```bash
# 1. Verify Logstash incidents pipeline is running
docker compose logs logstash | grep incidents

# 2. Check Elasticsearch incidents index
curl 'http://localhost:9200/_cat/indices/incidents-*?v'

# 3. Verify incidents are being indexed
curl -s 'http://localhost:9200/incidents-*/_count' | jq

# 4. Check Grafana datasource connectivity
docker compose logs grafana | grep -i error
```

**Fix:**
```bash
# Restart Logstash to reload pipelines
docker compose restart logstash

# Wait 30 seconds for re-initialization
sleep 30

# Generate test incident
cd services/log-generator
source ../../venv/bin/activate
python generate_scenarios.py --scenario chaos --count 5
```

---

### Issue: Dashboard shows old data only

**Check time range:**
1. Dashboard top-right corner → Time range selector
2. Change to "Last 5 minutes" or "Last 1 hour"
3. Enable auto-refresh (5s interval)

**Force refresh:**
- Click 🔄 refresh icon (top-right)
- Or press `Ctrl+R` / `Cmd+R`

---

### Issue: Panels show "Error" or empty visualizations

**Check Elasticsearch field mappings:**
```bash
curl -s 'http://localhost:9200/incidents-*/_mapping' | jq '.."properties"'
```

**Verify field names in panel queries:**
- Field names are case-sensitive
- Use `.keyword` suffix for exact matching (e.g., `incident_type.keyword`)
- Numeric fields don't need `.keyword` (e.g., `anomaly_count`, `impact_score`)

---

## 🎓 Dashboard Best Practices

### 1. Set Appropriate Time Ranges
- **Development/Testing:** Last 15 minutes or 1 hour
- **Operations:** Last 24 hours
- **Historical Analysis:** Last 7 days or 30 days

### 2. Use Filters for Focus
- Click on pie chart segments to filter by type
- Click on bar chart devices to filter by device
- Use Grafana variables for dynamic filtering

### 3. Monitor Auto-Refresh Impact
- 5-second refresh for active monitoring
- 30-second refresh for normal operations
- Disable auto-refresh for historical analysis (reduces load)

### 4. Export for Reporting
- **Snapshot:** Share → Snapshot → Create public snapshot
- **PDF:** Panel menu → Inspect → Download CSV (data)
- **Image:** Panel menu → Share → Render image

---

## 📊 Dashboard Metrics Summary

| Metric | Description | Good Threshold | Warning Threshold | Critical Threshold |
|--------|-------------|----------------|-------------------|-------------------|
| **Total Incidents** | Cumulative count | < 100/day | 100-500/day | > 500/day |
| **Active Incidents** | Needs attention | < 5 | 5-20 | > 20 |
| **Critical Incidents** | Severe issues | 0 | 1-3 | > 3 |
| **Affected Devices** | Infrastructure impact | < 10 devices | 10-30 devices | > 30 devices |
| **Impact Score** | Incident severity composite | < 40 (LOW) | 40-70 (MEDIUM-HIGH) | > 70 (HIGH-CRITICAL) |

---

## 🔗 Related Resources

- **Testing Guide:** [CORRELATION_TESTING_GUIDE.md](./CORRELATION_TESTING_GUIDE.md)
- **Anomaly Detection Dashboard:** http://localhost:3000/d/smart-noc-anomalies
- **Kafka UI:** http://localhost:8080
- **Elasticsearch:** http://localhost:9200
- **Kibana (if enabled):** http://localhost:5601

---

## 🚀 Next Steps After Dashboard Setup

1. **Baseline Establishment**
   - Run system for 24-48 hours
   - Observe normal incident patterns
   - Note typical incident types and frequencies

2. **Alert Configuration** (Future Phase)
   - Configure Grafana alerts for:
     - Active incidents > 20
     - Critical incidents > 0
     - Impact score > 80
   - Set up notification channels (Slack, email, PagerDuty)

3. **Dashboard Evolution**
   - Add panels for:
     - Mean Time to Resolution (MTTR)
     - Incident resolution rate
     - Top recurring incident patterns
     - Correlation accuracy metrics

4. **Integration with Phase 4** (LLM Diagnosis)
   - Add panel showing incidents with AI-generated root cause
   - Display LLM diagnosis confidence scores
   - Show remediation recommendation status

---

**🎉 Congratulations! Your Incident Correlation Dashboard is ready for operations! 🎉**

**Dashboard URL:** http://localhost:3000/d/smart-noc-incidents

---

## 📸 Expected Dashboard Appearance

### Initial State (Clean System)
- Total Incidents: 0-10
- Active Incidents: 0
- Critical Incidents: 0
- All charts: Minimal or empty data

### After Running Test Scenarios (100+ incidents)
- Total Incidents: 100-500
- Active Incidents: 10-30
- Critical Incidents: 1-5
- Incident Timeline: Clear spikes during test periods
- By Type: DEVICE_FAILURE dominant (due to test patterns)
- By Severity: Mix of HIGH (60%), MEDIUM (30%), CRITICAL (10%)
- Top Devices: Dist-switch-02, core-router-01, access-switch-01
- Correlation Method: PATTERN_BASED (80%), TIME_BASED (20%)

---

**✨ Happy Monitoring! Your Smart NOC is now visualizing actionable incidents! ✨**
