# Log Generators

Scripts for generating and sending test logs to the Smart NOC pipeline.

## Scripts

### Log Generation

- **`generate-logs.sh`** - Generate synthetic network logs (calls log-generator service)
- **`generate-dashboard-test-data.sh`** - Generate test data for Grafana dashboards
- **`populate-dashboard-data.sh`** - Populate dashboard with sample data

### Log Sending

- **`send_test_logs.sh`** - Send test syslog messages to Logstash
  - Adds syslog priority headers
  - Sends via UDP to port 5000
  - Usage: `bash send_test_logs.sh <log_file>`

- **`send-test-syslog.sh`** - Alternative syslog sender
  - Legacy test log sender

### Integration Tests

- **`convert-send-switch-logs.sh`** - Convert and send switch logs
- **`test-switch-integration.sh`** - Test switch integration with log pipeline

## Quick Start

### Send Test Reboot Logs

```bash
# Create test logs
cat > /tmp/test-reboot.log << 'EOF'
Jun 20 11:00:00 10.139.38.188 EXOS: System reboot initiated
Jun 20 11:00:15 10.139.38.188 EXOS: Boot process failed
Jun 20 11:00:30 10.139.38.188 EXOS: Critical: Reboot loop detected
EOF

# Send to pipeline
bash send_test_logs.sh /tmp/test-reboot.log
```

### Generate Sample Logs

```bash
# Generate 100 logs
bash generate-logs.sh --count 100

# Generate with specific pattern
bash generate-logs.sh --pattern bgp_flapping --count 50
```

## Notes

- All scripts expect services to be running
- Logstash must be listening on port 5000 (UDP/TCP)
- Test logs use device IP 10.139.38.188 by default
