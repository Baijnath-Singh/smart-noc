# Smart NOC - Anomaly Dashboard Import Instructions

## Quick Import Steps

### Option 1: Via Grafana UI (Recommended)

1. **Open Grafana**: http://localhost:3000
   - Username: `admin`
   - Password: `admin` (default)

2. **Import Dashboard**:
   - Click the `+` icon in the left sidebar
   - Select "Import dashboard"
   - Click "Upload JSON file"
   - Select: `dashboards/smart-noc-anomalies-dashboard.json`

3. **Configure Data Source**:
   - In the import screen, select your **Elasticsearch** data source
   - Click "Import"

4. **View Dashboard**:
   - The dashboard will load with real-time anomaly data
   - Auto-refresh is set to 5 seconds

---

## Dashboard Panels Overview

✅ **Panel 1-4 (Top Row)**: Statistics Cards
- Total Anomalies Detected
- Rule-Based Detections
- ML-Based Detections  
- Critical Anomalies

✅ **Panel 5**: Anomaly Timeline
- Line chart showing anomaly rate over time
- Colored by detection method (rule vs ML)

✅ **Panel 6**: Detection Method Distribution
- Pie chart: Rule-based vs ML-based

✅ **Panel 7**: Anomaly Type Distribution
- Pie chart: INTERFACE_FLAPPING, AUTH_BRUTE_FORCE, ML_DETECTED_ANOMALY, etc.

✅ **Panel 8**: Severity Distribution
- Donut chart: CRITICAL, ERROR, WARNING, INFO

✅ **Panel 9**: Top 10 Anomalous Devices
- Horizontal bar chart showing which devices have most anomalies

✅ **Panel 10**: Confidence Score Over Time
- Line chart showing average confidence of detections

✅ **Panel 11**: Recent Anomalies Table
- Live feed of latest 20 anomalies
- Columns: Time, Device, Anomaly Type, Severity, Detection Method, Confidence

---

## Troubleshooting

### "No Data" in Dashboard?
```bash
# Check if anomalies are in Elasticsearch
curl -s 'http://localhost:9200/anomalies-*/_search?size=0' | jq '.hits.total.value'

# If 0, generate more anomalies
cd services/log-generator
source ../../venv/bin/activate
python generate_scenarios.py --scenario flapping --count 8
python generate_scenarios.py --scenario brute-force --count 12
python generate_logs.py --rate 30 --duration 10
```

### Data Source Not Found?
1. Go to Configuration → Data Sources
2. Verify Elasticsearch data source exists
3. Note the data source name
4. Re-import dashboard and select correct data source

### Time Range Issues?
- Dashboard default: Last 1 hour
- Change to "Last 12 hours" if you don't see recent data
- Or use "Last 5 minutes" for real-time testing

---

## Testing the Dashboard

Run these commands to see different anomaly types appear:

```bash
# Interface flapping (triggers rule-based detector)
python generate_scenarios.py --scenario flapping --count 7

# Wait 10 seconds, then check dashboard - you should see:
# - Total anomalies increase
# - Rule-based count increase
# - INTERFACE_FLAPPING in pie chart
# - core-router-01 in top devices

# Auth brute force (triggers rule-based detector)
python generate_scenarios.py --scenario brute-force --count 12

# Wait 10 seconds, then check dashboard - you should see:
# - AUTH_BRUTE_FORCE anomaly type
# - dist-switch-02 in top devices

# Mixed logs (triggers ML detector after 50 samples)
python generate_logs.py --rate 50 --duration 5

# Wait 20 seconds, then check dashboard - you should see:
# - ML-based count increase
# - ML_DETECTED_ANOMALY in pie chart
# - Confidence scores plotted on graph
```

---

## Dashboard Features

🔄 **Auto-Refresh**: Every 5 seconds (change in time picker)

📅 **Time Range**: Default last 1 hour (customizable)

🎨 **Dark Theme**: Modern dark theme enabled

🏷️ **Tags**: anomaly-detection, ai, machine-learning, smart-noc

🔗 **Drill-Down**: Click on any chart element to filter other panels

---

## Next Steps After Import

1. ✅ Verify all 11 panels load correctly
2. ✅ Check data source connection
3. ✅ Generate test anomalies
4. ✅ Watch real-time updates
5. ✅ Customize time range and refresh interval as needed

The dashboard is ready for Phase 3! 🚀
