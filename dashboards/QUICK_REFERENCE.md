# Safety Framework Grafana Dashboard - Quick Reference

**Status:** ✅ **DEPLOYED AND OPERATIONAL**  
**Dashboard URL:** http://localhost:3000/d/safety-framework  
**Auto-Refresh:** Every 30 seconds  
**Default Credentials:** admin / admin

---

## 📊 At a Glance

### Key Metrics (Top Row)
```
┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│ Total Decisions │ Auto Executions │ Approvals Req'd │ Manual Required │
│                 │  (Green)        │  (Orange)       │  (Red)          │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┘
```

### Current Status
- **49 Decisions** in database
- **2 Risk Assessments** logged
- **All 13 Panels** operational
- **Real-time data** visible

---

## 🎯 Dashboard Panels (13 total)

### 1. **Top Stats Row** (4 panels)
- Total Decisions
- Autonomous Executions (`execute` decisions)
- Approvals Required (`require_approval` decisions)
- Manual Interventions (`manual_only` decisions)

### 2. **Distribution Charts** (2 panels)
- **Decision Distribution Pie Chart**
  - Green: execute (autonomous)
  - Orange: require_approval (needs human OK)
  - Red: manual_only (escalated)
  
- **Risk Level Distribution Pie Chart**
  - Green: LOW
  - Yellow: MEDIUM
  - Orange: HIGH
  - Red: CRITICAL

### 3. **Time Series - Decisions** (1 panel)
- Decisions over time (hourly buckets)
- Multi-line chart with all decision types
- Shows decision trends and patterns

### 4. **Time Series - Metrics** (2 panels)
- **Average Risk Score Over Time**
  - Scale: 0.0 (safe) to 1.0 (critical)
  - Color gradient: Green → Yellow → Red
  
- **Average Confidence Over Time**
  - Scale: 0.0 (low) to 1.0 (high)
  - Color gradient: Red → Yellow → Green

### 5. **Decision Matrix Analysis** (2 panels)
- **Decision Matrix Heatmap**
  - Shows Risk × Decision combinations
  - Validates decision logic
  
- **Remediation Execution Statistics Table**
  - Total executions
  - Success/failure counts
  - Success rate percentage
  - Average duration

### 6. **Risk Factor Trends** (1 panel)
- 4 weighted components over time:
  - Device Criticality (40%) - Red line
  - Blast Radius (30%) - Orange line
  - Time Sensitivity (20%) - Yellow line
  - Change Complexity (10%) - Blue line

### 7. **Recent Decisions Table** (1 panel)
- Last 100 decisions with full details
- Color-coded risk levels and decisions
- Confidence shown as gauges
- Sortable and searchable

---

## 🔍 Quick Insights

### What to Look For

**Healthy System:**
```
✅ Decision Distribution:
   - execute: 10-30% (LOW risk + good confidence)
   - require_approval: 10-20% (MEDIUM/HIGH risk + high confidence)
   - manual_only: 50-80% (conservative decisions)

✅ Success Rate: >90%
✅ Average Confidence: >0.75
✅ Risk Distribution: Mostly LOW/MEDIUM
```

**Red Flags:**
```
❌ Success rate <85% → Review remediation actions
❌ manual_only >90% → Need to improve diagnosis confidence
❌ Average risk score rising → Infrastructure issues
❌ Confidence declining → Knowledge base needs expansion
```

### Expected Decision Matrix Patterns

| Risk Level | High Conf (≥0.92) | Med Conf (0.75-0.92) | Low Conf (<0.75) |
|------------|-------------------|----------------------|------------------|
| LOW | execute | execute | manual_only |
| MEDIUM | require_approval | manual_only | manual_only |
| HIGH | require_approval | manual_only | manual_only |
| CRITICAL | manual_only | manual_only | manual_only |

---

## ⚡ Quick Actions

### Access Dashboard
```bash
# From browser
http://localhost:3000/d/safety-framework

# Or from server IP
http://<server-ip>:3000/d/safety-framework
```

### Generate Test Data
```bash
cd /home/user/ng-iam/smart-noc
./test_decision_matrix_all_scenarios.sh
# Creates 12 test incidents with all decision types
```

### View Recent Decisions
```bash
docker-compose exec -T postgres psql -U noc_admin -d smart_noc -c "
SELECT incident_number, risk_level, decision, calibrated_confidence, decided_at 
FROM autonomous_decision_log 
ORDER BY decided_at DESC 
LIMIT 10;"
```

### Check Success Rate
```bash
docker-compose exec -T postgres psql -U noc_admin -d smart_noc -c "
SELECT 
  COUNT(*) as total,
  SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful,
  ROUND(SUM(CASE WHEN success THEN 1 ELSE 0 END)::numeric / COUNT(*)::numeric * 100, 1) as success_rate_pct
FROM remediation_executions
WHERE executed_at >= NOW() - INTERVAL '24 hours';"
```

### Export Dashboard Data
```bash
# Export decision distribution
docker-compose exec -T postgres psql -U noc_admin -d smart_noc -c "
COPY (
  SELECT decision, COUNT(*) 
  FROM autonomous_decision_log 
  WHERE decided_at >= NOW() - INTERVAL '24 hours' 
  GROUP BY decision
) TO STDOUT CSV HEADER;" > decision_distribution.csv
```

---

## 🎨 Customization Tips

### Change Time Range
- Click time picker (top right)
- Select preset: 1h, 6h, 24h, 7d, 30d
- Or custom range

### Adjust Auto-Refresh
- Click ⟳ dropdown (top right)
- Options: 5s, 10s, 30s, 1m, 5m, 15m, 30m, 1h
- Current: 30s (recommended)

### Filter by Risk Level (manual)
- Edit any panel
- Add to WHERE clause: `AND risk_level = 'HIGH'`
- Save panel

### Share Dashboard
- Click 🔗 Share (top right)
- Options:
  - Link: Direct URL
  - Snapshot: Create shareable snapshot
  - Export: Download JSON

---

## 🐛 Troubleshooting

### Dashboard shows "No data"

**Quick Fix:**
```bash
# 1. Check time range (try "Last 7 days")
# 2. Generate test data:
cd /home/user/ng-iam/smart-noc
./test_decision_matrix_all_scenarios.sh

# 3. Refresh dashboard (Ctrl+R)
```

### Data Source Error

**Quick Fix:**
```bash
# Re-run setup script
cd /home/user/ng-iam/smart-noc
./scripts/setup-grafana-dashboard.sh
```

### Panel Query Error

**Check PostgreSQL:**
```bash
docker-compose logs postgres --tail=50
docker-compose exec postgres psql -U noc_admin -d smart_noc -c "\dt"
```

---

## 📊 Sample Queries for Custom Panels

### Decisions in Last Hour
```sql
SELECT decision, COUNT(*) 
FROM autonomous_decision_log 
WHERE decided_at >= NOW() - INTERVAL '1 hour'
GROUP BY decision;
```

### Top Risky Devices
```sql
SELECT 
  i.primary_device,
  COUNT(*) as incidents,
  AVG(r.overall_risk_score) as avg_risk
FROM incidents i
JOIN incident_risk_assessment r ON i.incident_number = r.incident_number
WHERE r.assessed_at >= NOW() - INTERVAL '7 days'
GROUP BY i.primary_device
ORDER BY avg_risk DESC
LIMIT 10;
```

### Decision Accuracy (Confidence vs Success)
```sql
SELECT 
  CASE 
    WHEN d.calibrated_confidence >= 0.92 THEN 'HIGH'
    WHEN d.calibrated_confidence >= 0.75 THEN 'MEDIUM'
    ELSE 'LOW'
  END as confidence_level,
  COUNT(*) as total,
  SUM(CASE WHEN r.success THEN 1 ELSE 0 END) as successful,
  ROUND(SUM(CASE WHEN r.success THEN 1 ELSE 0 END)::numeric / COUNT(*) * 100, 1) as success_rate
FROM autonomous_decision_log d
JOIN remediation_executions r ON d.incident_number = r.incident_number
WHERE d.decision = 'execute'
  AND d.decided_at >= NOW() - INTERVAL '7 days'
GROUP BY confidence_level;
```

---

## 📁 Files

- **Dashboard JSON:** `/home/user/ng-iam/smart-noc/dashboards/safety-framework-dashboard.json`
- **Setup Script:** `/home/user/ng-iam/smart-noc/scripts/setup-grafana-dashboard.sh`
- **Full Guide:** `/home/user/ng-iam/smart-noc/dashboards/GRAFANA_SETUP_GUIDE.md`
- **This File:** `/home/user/ng-iam/smart-noc/dashboards/QUICK_REFERENCE.md`

---

## 🔗 Related Links

- **Safety Framework Docs:** [docs/03-features/safety-framework/2026-06-11_SAFETY_FRAMEWORK_COMPLETE.md](../docs/03-features/safety-framework/2026-06-11_SAFETY_FRAMEWORK_COMPLETE.md)
- **Decision Matrix Tests:** [docs/03-features/safety-framework/2026-06-11_DECISION_MATRIX_TEST_RESULTS.md](../docs/03-features/safety-framework/2026-06-11_DECISION_MATRIX_TEST_RESULTS.md)
- **E2E Flow:** [docs/03-features/safety-framework/2026-06-11_E2E_FLOW_WITH_REMEDIATION.md](../docs/03-features/safety-framework/2026-06-11_E2E_FLOW_WITH_REMEDIATION.md)

---

**Created:** June 11, 2026  
**Status:** ✅ Production Ready  
**Dashboard URL:** http://localhost:3000/d/safety-framework  
**Data Source:** smart_noc_postgres (PostgreSQL)  
**Auto-Refresh:** 30 seconds
