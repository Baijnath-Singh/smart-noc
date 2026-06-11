# Safety Framework Grafana Dashboard - Setup Guide

**Dashboard:** Smart NOC - Safety Framework Dashboard  
**Purpose:** Real-time observability for autonomous remediation decision-making  
**Date:** June 11, 2026

---

## 📊 Dashboard Overview

The Safety Framework Dashboard provides comprehensive visibility into:
- **Decision Distribution** - Execute vs Approval vs Manual breakdown
- **Risk Assessment** - Risk level distribution and trends
- **Confidence Metrics** - Diagnosis confidence over time
- **Remediation Performance** - Success rates and execution statistics
- **Decision Matrix** - Risk × Decision heatmap
- **Risk Factors** - Device criticality, blast radius, time sensitivity, change complexity

---

## 🚀 Quick Start (Automated)

### Option A: Automated Setup Script

```bash
cd /home/user/ng-iam/smart-noc
chmod +x scripts/setup-grafana-dashboard.sh
./scripts/setup-grafana-dashboard.sh
```

The script will:
1. Configure PostgreSQL data source in Grafana
2. Import Safety Framework dashboard
3. Verify dashboard is accessible

---

## 🔧 Manual Setup (Step-by-Step)

### Step 1: Access Grafana

```bash
# Grafana is already running on port 3000
# Access at: http://localhost:3000 or http://<your-server-ip>:3000
```

**Default Credentials:**
- Username: `admin`
- Password: `admin` (you'll be prompted to change on first login)

### Step 2: Add PostgreSQL Data Source

1. **Navigate to Data Sources:**
   - Click **☰** (hamburger menu) → **Connections** → **Data sources**
   - Click **Add data source**

2. **Select PostgreSQL:**
   - Search for "PostgreSQL"
   - Click **PostgreSQL**

3. **Configure Connection:**
   ```
   Name: smart_noc_postgres (or any name you prefer)
   Host: smart-noc-postgres:5432
   Database: smart_noc
   User: noc_admin
   Password: noc_password
   TLS/SSL Mode: disable
   Version: 16+
   ```

4. **Additional Settings:**
   - **Enable:** ✅ PostgreSQL details
   - **Max open connections:** 100
   - **Max idle connections:** 2
   - **Max connection lifetime:** 14400

5. **Click "Save & test"**
   - You should see: ✅ "Database Connection OK"

### Step 3: Import Dashboard

1. **Navigate to Dashboards:**
   - Click **☰** → **Dashboards**
   - Click **New** → **Import**

2. **Import Options:**
   
   **Option A: Direct File Upload**
   ```bash
   # Upload file: /home/user/ng-iam/smart-noc/dashboards/safety-framework-dashboard.json
   ```
   - Click **Upload dashboard JSON file**
   - Select `safety-framework-dashboard.json`
   - Click **Load**

   **Option B: Copy-Paste JSON**
   - Open `/home/user/ng-iam/smart-noc/dashboards/safety-framework-dashboard.json`
   - Copy entire contents
   - Paste into **Import via panel json** text area
   - Click **Load**

3. **Configure Import:**
   - **Name:** Smart NOC - Safety Framework Dashboard
   - **Folder:** General (or create new folder: "Smart NOC")
   - **Unique ID (UID):** safety-framework
   - **Data Source:** Select `smart_noc_postgres` (the data source you just created)

4. **Click "Import"**

### Step 4: Verify Dashboard

1. **Dashboard should load with 13 panels:**
   - ✅ Total Decisions (stat)
   - ✅ Autonomous Executions (stat)
   - ✅ Approvals Required (stat)
   - ✅ Manual Interventions (stat)
   - ✅ Decision Distribution (pie chart)
   - ✅ Risk Level Distribution (pie chart)
   - ✅ Decisions Over Time (time series)
   - ✅ Average Risk Score Over Time (time series)
   - ✅ Average Confidence Over Time (time series)
   - ✅ Decision Matrix Heatmap (chart)
   - ✅ Remediation Execution Statistics (table)
   - ✅ Risk Factor Trends (time series)
   - ✅ Recent Safety Framework Decisions (table)

2. **Set Time Range:**
   - Top right: Select "Last 24 hours" or "Last 7 days"
   - Dashboard auto-refreshes every 30 seconds

3. **Test Queries:**
   - All panels should show data (if you have test incidents from decision matrix testing)
   - If no data: Run decision matrix tests to populate dashboard

---

## 📈 Dashboard Panels Explained

### Top Row: Key Metrics (Stats)

**Total Decisions**
- Count of all Safety Framework decisions in time range
- Tracks overall system activity

**Autonomous Executions**
- Count of `execute` decisions
- Shows how many incidents were autonomously remediated

**Approvals Required**
- Count of `require_approval` decisions
- Incidents waiting for human approval

**Manual Interventions**
- Count of `manual_only` decisions
- Incidents escalated to human operators

### Row 2: Distribution Charts

**Decision Distribution (Pie Chart)**
- Breakdown of execute / require_approval / manual_only
- Shows decision patterns at a glance
- Color coded: Green (execute), Orange (approval), Red (manual)

**Risk Level Distribution (Pie Chart)**
- Breakdown of LOW / MEDIUM / HIGH / CRITICAL risks
- Shows risk profile of incidents
- Color coded: Green (LOW) → Red (CRITICAL)

### Row 3: Decisions Over Time

**Decisions Over Time (Time Series)**
- Line chart showing decision trends by hour
- Separate lines for each decision type
- Helps identify patterns (e.g., more manual decisions during business hours)

### Row 4: Score Trends

**Average Risk Score Over Time**
- Shows risk score trends (0.0 - 1.0 scale)
- Green (LOW) → Red (CRITICAL)
- Helps identify if risk is increasing

**Average Confidence Over Time**
- Shows diagnosis confidence trends (0.0 - 1.0 scale)
- Red (<0.75) → Yellow (0.75-0.92) → Green (≥0.92)
- Tracks diagnosis quality improvement

### Row 5: Decision Matrix & Execution Stats

**Decision Matrix Heatmap**
- Shows Risk Level × Decision combinations
- Validates decision matrix is working correctly
- Should match expected patterns (e.g., CRITICAL → manual_only)

**Remediation Execution Statistics (Table)**
- Total executions, successful, failed
- Success rate (should be >90%)
- Average duration of remediations

### Row 6: Risk Factor Trends

**Risk Factor Trends (Time Series)**
- Shows all 4 risk components over time:
  - Device Criticality (40% weight) - Red
  - Blast Radius (30% weight) - Orange
  - Time Sensitivity (20% weight) - Yellow
  - Change Complexity (10% weight) - Blue
- Helps understand what's driving risk scores

### Row 7: Recent Decisions Table

**Recent Safety Framework Decisions**
- Last 100 decisions with full details
- Color-coded risk levels and decisions
- Confidence displayed as gauges
- Searchable and sortable
- Click incident_number to drill down

---

## 🔍 Using the Dashboard

### Analyzing Decision Patterns

**Expected Patterns (Healthy System):**
- **LOW risk + high confidence → execute** (autonomous)
- **MEDIUM/HIGH risk + high confidence → require_approval**
- **Any risk + low confidence → manual_only**
- **CRITICAL risk → always manual_only**

**Red Flags:**
- Too many manual interventions (>80%) → Need to improve confidence
- Low success rate (<85%) → Review remediation actions
- Increasing risk scores → Infrastructure issues
- Declining confidence → Knowledge base needs expansion

### Time Range Selection

**Common Ranges:**
- **Last 1 hour:** Real-time monitoring
- **Last 24 hours:** Daily operations review
- **Last 7 days:** Weekly trend analysis
- **Last 30 days:** Monthly performance review

**Custom Range:**
- Click time picker (top right)
- Select "Custom range"
- Set specific start/end dates

### Auto-Refresh

- Default: 30 seconds
- Change: Click ⟳ dropdown (top right)
- Options: 5s, 10s, 30s, 1m, 5m, 15m, 30m, 1h, 2h, 1d
- Disable: Select "Off"

### Filtering

**Variables (when implemented):**
- Risk Level filter
- Decision Type filter
- Device filter
- Time range

---

## 📊 Sample Queries

### Decision Distribution Query
```sql
SELECT 
  decision,
  COUNT(*) as count
FROM autonomous_decision_log
WHERE decided_at >= NOW() - INTERVAL '24 hours'
GROUP BY decision
ORDER BY count DESC;
```

### Average Risk Score by Hour
```sql
SELECT 
  date_trunc('hour', assessed_at) as time,
  AVG(overall_risk_score) as avg_risk
FROM incident_risk_assessment
WHERE assessed_at >= NOW() - INTERVAL '24 hours'
GROUP BY date_trunc('hour', assessed_at)
ORDER BY time;
```

### Remediation Success Rate
```sql
SELECT 
  COUNT(*) as total,
  SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful,
  ROUND(SUM(CASE WHEN success THEN 1 ELSE 0 END)::numeric / COUNT(*)::numeric, 3) as success_rate
FROM remediation_executions
WHERE executed_at >= NOW() - INTERVAL '24 hours';
```

### Decision Matrix Validation
```sql
SELECT 
  r.risk_level,
  d.decision,
  COUNT(*) as count
FROM incident_risk_assessment r
JOIN autonomous_decision_log d ON r.incident_number = d.incident_number
WHERE r.assessed_at >= NOW() - INTERVAL '24 hours'
GROUP BY r.risk_level, d.decision
ORDER BY r.risk_level, d.decision;
```

---

## 🐛 Troubleshooting

### Dashboard shows "No data"

**Check 1: Data Source Connection**
```bash
# Test PostgreSQL connection
docker-compose exec postgres psql -U noc_admin -d smart_noc -c "SELECT COUNT(*) FROM autonomous_decision_log;"
```

**Check 2: Test Data Exists**
```bash
# Check if there are recent decisions
docker-compose exec postgres psql -U noc_admin -d smart_noc -c "
SELECT COUNT(*) FROM autonomous_decision_log 
WHERE decided_at >= NOW() - INTERVAL '24 hours';"
```

**Check 3: Time Range**
- Ensure time range includes data
- Try "Last 7 days" or "Last 30 days"

**Check 4: Run Test Suite**
```bash
# Generate test data
cd /home/user/ng-iam/smart-noc
./test_decision_matrix_all_scenarios.sh
```

### Panel shows "Error executing query"

**Check Query:**
1. Edit panel (click panel title → Edit)
2. Check SQL query syntax
3. Verify table/column names
4. Test query in PostgreSQL directly

**Common Issues:**
- Table not found → Check database migration ran
- Column not found → Check schema matches query
- Timeout → Reduce time range or add indexes

### Data Source connection fails

**Check PostgreSQL container:**
```bash
docker-compose ps postgres
docker-compose logs postgres --tail=50
```

**Check credentials:**
```bash
# Verify in .env file
cat .env | grep POSTGRES

# Should show:
# POSTGRES_USER=noc_admin
# POSTGRES_PASSWORD=noc_password
# POSTGRES_DB=smart_noc
```

**Restart Grafana:**
```bash
docker-compose restart grafana
```

### Dashboard not refreshing

**Check auto-refresh:**
- Top right: Ensure refresh interval is set (not "Off")
- Click ⟳ dropdown → Select "30s" or "1m"

**Check browser:**
- Hard refresh: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)
- Clear cache and reload

---

## 🎨 Customization

### Add Variables (Filters)

1. **Dashboard Settings:**
   - Click ⚙️ (top right) → **Variables**
   - Click **Add variable**

2. **Risk Level Filter:**
   ```
   Name: risk_level
   Type: Query
   Data source: smart_noc_postgres
   Query: SELECT DISTINCT risk_level FROM incident_risk_assessment ORDER BY risk_level
   Multi-value: Yes
   Include All option: Yes
   ```

3. **Update Panel Queries:**
   Add to WHERE clause: `AND risk_level = '$risk_level'`

### Modify Panels

**Edit Panel:**
1. Click panel title
2. Select **Edit**
3. Modify query, visualization, or options
4. Click **Apply**

**Add Panel:**
1. Click **Add panel** (top right)
2. Select visualization type
3. Configure query
4. Style and save

### Export Dashboard

```bash
# In Grafana UI:
# Dashboard → Share → Export → Save to file

# Or use API:
curl -X GET http://admin:admin@localhost:3000/api/dashboards/uid/safety-framework \
  | jq '.dashboard' > safety-framework-dashboard-export.json
```

---

## 📱 Alerting (Future Enhancement)

### Recommended Alerts

**Low Success Rate:**
```sql
-- Alert if remediation success rate < 85%
SELECT 
  ROUND(SUM(CASE WHEN success THEN 1 ELSE 0 END)::numeric / COUNT(*)::numeric, 3) as success_rate
FROM remediation_executions
WHERE executed_at >= NOW() - INTERVAL '1 hour'
HAVING ROUND(SUM(CASE WHEN success THEN 1 ELSE 0 END)::numeric / COUNT(*)::numeric, 3) < 0.85;
```

**High Risk Trend:**
```sql
-- Alert if average risk score > 0.70 for past hour
SELECT AVG(overall_risk_score) as avg_risk
FROM incident_risk_assessment
WHERE assessed_at >= NOW() - INTERVAL '1 hour'
HAVING AVG(overall_risk_score) > 0.70;
```

**Too Many Manual Interventions:**
```sql
-- Alert if >80% of decisions are manual_only
SELECT 
  COUNT(*) FILTER (WHERE decision = 'manual_only') * 100.0 / COUNT(*) as manual_pct
FROM autonomous_decision_log
WHERE decided_at >= NOW() - INTERVAL '1 hour'
HAVING COUNT(*) FILTER (WHERE decision = 'manual_only') * 100.0 / COUNT(*) > 80;
```

---

## 📚 Related Documentation

- **Safety Framework Complete:** [docs/03-features/safety-framework/2026-06-11_SAFETY_FRAMEWORK_COMPLETE.md](../docs/03-features/safety-framework/2026-06-11_SAFETY_FRAMEWORK_COMPLETE.md)
- **Decision Matrix Test Results:** [docs/03-features/safety-framework/2026-06-11_DECISION_MATRIX_TEST_RESULTS.md](../docs/03-features/safety-framework/2026-06-11_DECISION_MATRIX_TEST_RESULTS.md)
- **E2E Flow:** [docs/03-features/safety-framework/2026-06-11_E2E_FLOW_WITH_REMEDIATION.md](../docs/03-features/safety-framework/2026-06-11_E2E_FLOW_WITH_REMEDIATION.md)

---

## 🆘 Support

### Useful Commands

```bash
# Check Grafana logs
docker-compose logs grafana --tail=100 -f

# Check PostgreSQL connectivity
docker-compose exec postgres psql -U noc_admin -d smart_noc -c "\dt"

# Verify Safety Framework tables
docker-compose exec postgres psql -U noc_admin -d smart_noc -c "
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name LIKE '%risk%' OR table_name LIKE '%decision%';"

# Check recent decisions
docker-compose exec postgres psql -U noc_admin -d smart_noc -c "
SELECT incident_number, risk_level, decision, decided_at 
FROM autonomous_decision_log 
ORDER BY decided_at DESC LIMIT 10;"
```

---

**Setup Date:** June 11, 2026  
**Dashboard Version:** 1.0  
**Grafana Version:** 10.3.3  
**Status:** ✅ Production Ready
