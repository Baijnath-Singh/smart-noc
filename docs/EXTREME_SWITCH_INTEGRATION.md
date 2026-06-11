# Extreme Networks Switch Integration Guide

## Overview
This guide shows how to configure an Extreme Networks switch to send logs to Smart NOC's Logstash service.

## Prerequisites
- Extreme Networks switch accessible via telnet/ssh
- Smart NOC Logstash running on port 5000 (TCP)
- Network connectivity between switch and Smart NOC server

## Switch Configuration

### 1. Connect to Switch
```bash
telnet 10.139.38.4 5019
# Login: admin
# Password: (press Enter - no password)
```

### 2. Configure Syslog Server

```bash
# Add Smart NOC as syslog target (replace <SMART_NOC_IP> with your server IP)
# Option A: INFO and above (recommended - moderate volume)
configure syslog add <SMART_NOC_IP>:5000 local7 info

# Option B: DEBUG-DATA and above (verbose - all messages)
# configure syslog add <SMART_NOC_IP>:5000 local7 debug-data

# Save configuration to persist across reboots
save configuration
```

**Note:** Based on actual switch testing (June 11, 2026):
- No need for `enable log target syslog` command
- Single `configure syslog add` command is sufficient
- Syslog automatically starts sending once configured
- No `configure` or `exit` mode commands needed (commands run directly)
save configuration

# Exit configuration mode
exit
```

### 3. Configure Syslog on Switch

#### ✅ Current State (Backed up - June 11, 2026)
- **No existing syslog configured** - Clean slate
- Backup saved to: `backups/switch-config-backup-20260611.md`
- Current logging: memory-buffer (63%), nvram, primary-node, backup-node

#### Commands to Execute:

```bash
# Option A: Send INFO and above (recommended - moderate volume)
configure syslog add 10.37.12.33:5000 local7 info

# Option B: Send DEBUG-DATA and above (verbose - all logs)
# configure syslog add 10.37.12.33:5000 local7 debug-data

# Save configuration to persist across reboots
save configuration
```

**What this does:**
- Adds Smart NOC (10.37.12.33:5000) as syslog receiver
- Uses facility `local7` for categorization
- Severity `info` = info, warning, error, critical messages
- **Does NOT disable** existing logging (memory-buffer, nvram remain active)

#### Rollback Commands (if needed):
```bash
configure syslog delete 10.37.12.33:5000
save configuration
```

### 4. Verify Configuration

```bash
# Show full log configuration (confirms syslog added)
show log configuration

# Show recent log messages from memory buffer
show log messages memory-buffer

# Test: Generate a log message
log message "TEST: Smart NOC integration verification"
```

### 5. Test Log Generation

Generate test log messages to verify connectivity:

```bash
# Generate a test log message
log message "TEST: Smart NOC integration verification"

# View recent logs in memory buffer
show log messages memory-buffer | include TEST

# Show configuration to confirm syslog target added
show log configuration | include syslog
```

## Verification in Smart NOC

### 1. Check Logstash is Receiving Logs

```bash
# On Smart NOC server, check Logstash logs
docker logs smart-noc-logstash --tail=50 | grep "10.139.38.4"

# Check Elasticsearch for switch logs
curl -X GET "localhost:9200/logs-*/_search?pretty" -H 'Content-Type: application/json' -d'
{
  "size": 5,
  "query": {
    "match": {
      "host": "10.139.38.4"
    }
  },
  "sort": [
    { "@timestamp": { "order": "desc" } }
  ]
}'
```

### 2. Check Kafka Topics

```bash
# Check if logs are flowing through Kafka
docker exec -it smart-noc-kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic raw-logs \
  --from-beginning \
  --max-messages 10
```

### 3. Monitor in Real-Time

```bash
# Tail Logstash output
docker logs -f smart-noc-logstash

# Watch Kafka messages
docker exec -it smart-noc-kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic raw-logs
```

## Logstash Configuration

The Logstash service is already configured to receive logs on port 5000. Current configuration:

```ruby
input {
  tcp {
    port => 5000
    codec => json_lines
  }
}
```

### If You Need to Add Syslog-Specific Parsing

If logs aren't parsed correctly, you may need to add syslog codec:

```ruby
input {
  tcp {
    port => 5000
    codec => plain
    type => "syslog"
  }
}

filter {
  if [type] == "syslog" {
    grok {
      match => { "message" => "%{SYSLOGTIMESTAMP:syslog_timestamp} %{SYSLOGHOST:syslog_hostname} %{DATA:syslog_program}(?:\[%{POSINT:syslog_pid}\])?: %{GREEDYDATA:syslog_message}" }
    }
    date {
      match => [ "syslog_timestamp", "MMM  d HH:mm:ss", "MMM dd HH:mm:ss" ]
    }
  }
}
```

## Troubleshooting

### Issue: Logs Not Appearing

**1. Check Network Connectivity**
```bash
# From switch
ping 10.37.12.33

# From Smart NOC server, check if switch can reach Logstash
sudo tcpdump -i any -n port 5000
```

**2. Verify Firewall Rules**
```bash
# On Smart NOC server
sudo iptables -L -n | grep 5000

# If blocked, allow:
sudo iptables -A INPUT -p tcp --dport 5000 -j ACCEPT
```

**3. Check Switch Syslog Status**
```bash
# On switch
show log configuration
show log target syslog
```

**4. Test Logstash Directly**
```bash
# From another machine, send test syslog
echo "TEST MESSAGE FROM SWITCH" | nc 10.37.12.33 5000

# Check if it appears in Logstash
docker logs smart-noc-logstash --tail=20
```

### Issue: Logs Received but Not Parsed

Check Logstash pipeline configuration:
```bash
docker exec -it smart-noc-logstash cat /usr/share/logstash/pipeline/logstash.conf
```

## Common Extreme Switch Log Messages

Once configured, you'll receive logs like:

```
<134>Jun 11 16:30:45 Stack.1 Vlan: Port 1:1 link UP at speed 1 Gbps full-duplex
<131>Jun 11 16:30:50 Stack.1 BGP: Peer 10.1.1.1 state changed to Established
<133>Jun 11 16:31:00 Stack.1 LLDP: Neighbor detected on port 1:5
<139>Jun 11 16:31:15 Stack.1 PoE: Power consumption on port 1:10 exceeded threshold
```

## Best Practices

1. **Log Level**: Start with `info` and above, add `debug-data` only if needed
2. **Save Configuration**: Always save after making changes
3. **Monitor**: Watch logs for first 24 hours to ensure proper flow
4. **Filtering**: Configure Smart NOC to focus on critical events (BGP, link down, errors)
5. **Alerts**: Set up alerts for critical switch events in Grafana

## Integration with Smart NOC Pipeline

Once logs are flowing:

1. **Logstash** receives → parses → enriches logs
2. **Kafka** `raw-logs` topic receives parsed logs
3. **Anomaly Detector** analyzes for unusual patterns
4. **Correlation Engine** groups related events
5. **LLM Diagnosis** determines root cause
6. **Remediation Agent** (with Safety Framework) takes action

## Example: BGP Flapping Detection

When BGP session flaps on your switch:
```
1. Switch sends: "BGP: Peer 192.168.1.1 state changed to Idle"
2. Logstash parses and publishes to Kafka
3. Anomaly Detector flags unusual BGP state changes
4. Correlation Engine groups related BGP events
5. LLM Diagnosis identifies "BGP session flapping" 
6. Safety Framework assesses risk
7. Remediation Agent executes fix (if LOW risk + high confidence)
```

## Next Steps

1. Configure syslog on switch (see commands above)
2. Verify logs appear in Logstash
3. Check Smart NOC pipeline processes logs
4. Set up Grafana alerts for switch events
5. Test end-to-end: Generate switch event → See Smart NOC response

## Support Commands

```bash
# Switch side
show log configuration
show log target syslog
show log messages | include "10.37.12.33"

# Smart NOC side
docker logs smart-noc-logstash --tail=100
docker exec -it smart-noc-kafka kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic raw-logs --max-messages 10
curl localhost:9200/logs-*/_search?pretty&size=5
```
