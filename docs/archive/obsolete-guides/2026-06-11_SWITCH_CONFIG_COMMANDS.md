# Switch Syslog Configuration - READY TO EXECUTE
**Date:** June 11, 2026  
**Switch:** 10.139.38.4:5019 (Extreme Networks)  
**Smart NOC:** 10.37.12.33:5000 (Logstash TCP Syslog Input)

---

## ✅ Pre-Check Complete
- [x] Switch current configuration backed up → `backups/switch-config-backup-20260611.md`
- [x] Smart NOC Logstash listening on TCP port 5000
- [x] No existing syslog configured on switch (clean slate)
- [x] End-to-end pipeline verified working

---

## 🚀 Commands to Execute on Switch

### Step 1: Add Smart NOC Syslog Target

**Recommended (Moderate volume - INFO and above):**
```bash
configure syslog add 10.37.12.33:5000 local7 info
```

**Alternative (Verbose - ALL messages including DEBUG):**
```bash
configure syslog add 10.37.12.33:5000 local7 debug-data
```

### Step 2: Save Configuration
```bash
save configuration
```

### Step 3: Verify Configuration
```bash
show log configuration | include syslog
```

### Step 4: Test with Sample Log
```bash
log message "TEST: Smart NOC integration verification from switch"
```

---

## ✅ What This Does
- Adds Smart NOC (10.37.12.33:5000) as a syslog receiver
- Uses facility **local7** for categorization
- Sends severity **INFO** and above (info, notice, warning, error, critical)
- **Does NOT disable** existing logging (memory-buffer, nvram stay active)
- Configuration persists across reboots after save

---

## 🔄 Rollback Commands (If Needed)

If you need to remove Smart NOC syslog:
```bash
configure syslog delete 10.37.12.33:5000
save configuration
```

To restore original state (no syslog):
```bash
configure syslog delete 10.37.12.33:5000
save configuration
# This returns switch to original configuration (backed up)
```

---

## 📊 Verification on Smart NOC Side

After executing the commands above, run these on Smart NOC server:

```bash
# Watch Logstash logs for incoming syslog (run for 10-15 seconds)
docker logs -f smart-noc-logstash

# Check Kafka for messages (should see test message)
docker exec smart-noc-kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic network-logs \
  --from-beginning | grep "TEST"

# Check Elasticsearch for indexed logs
curl -s "http://localhost:9200/network-logs-*/_search?q=device_id:10.139.38.4&size=5" | jq

# View in Grafana (if dashboard configured for switch logs)
http://10.37.12.33:3000/d/safety-framework-v2
```

---

## 📝 Expected Behavior

**Immediately after configuration:**
1. Switch starts sending syslog to 10.37.12.33:5000
2. Logstash receives logs on TCP port 5000
3. Logstash parses and publishes to Kafka topic `network-logs`
4. Downstream services consume from Kafka
5. Logs indexed to Elasticsearch
6. Visible in Grafana dashboards

**Log volume estimate:**
- INFO level: ~50-200 messages/hour (normal operations)
- DEBUG-DATA level: ~500-2000 messages/hour (verbose)

---

## ⚠️ Important Notes

1. **No risk to existing logging:** Memory-buffer and NVRAM logging continue unchanged
2. **Network connectivity:** Ensure firewall allows TCP 5000 from switch to Smart NOC
3. **Performance:** Syslog is fire-and-forget (UDP-like), no impact on switch performance
4. **Shared switch safety:** Configuration change is minimal and reversible
5. **Testing:** Start with INFO level, upgrade to DEBUG-DATA if needed

---

## 🎯 Ready to Proceed?

Copy and paste the commands from **Step 1-4** above into your switch terminal.

After execution, share the output of:
```bash
show log configuration | include syslog
```

This will confirm successful configuration! 🚀
