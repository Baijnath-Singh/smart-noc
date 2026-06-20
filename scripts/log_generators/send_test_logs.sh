#!/bin/bash
# Send test syslog messages to Smart NOC
# Usage: bash send_test_logs.sh <log_file>

LOG_FILE="${1:-/tmp/test-reboot-loop.log}"
LOGSTASH_HOST="${2:-localhost}"
LOGSTASH_PORT="${3:-5000}"

if [ ! -f "$LOG_FILE" ]; then
    echo "Error: Log file not found: $LOG_FILE"
    exit 1
fi

echo "Sending test logs to $LOGSTASH_HOST:$LOGSTASH_PORT"
echo "============================================================"

# Read log file line by line and send each as separate UDP packet
line_count=0
while IFS= read -r line || [ -n "$line" ]; do
    # Skip empty lines
    [ -z "$line" ] && continue
    
    # Add syslog priority if not present
    # <134> = facility 16 (local0), severity 6 (informational)
    if [[ ! "$line" =~ ^\< ]]; then
        line="<134>$line"
    fi
    
    # Send via UDP using netcat (each line separately)
    echo "$line" | nc -u -w1 "$LOGSTASH_HOST" "$LOGSTASH_PORT"
    
    ((line_count++))
    echo "  Sent line $line_count: ${line:0:80}..."
    
    # Small delay between messages (100ms) to avoid overwhelming
    sleep 0.1
done < "$LOG_FILE"

echo "============================================================"
echo "✓ Sent $line_count log message(s)"
echo ""
echo "Monitor the logs with:"
echo "  docker logs -f smart-noc-logstash"
echo "  docker logs -f smart-noc-device-enrichment"
echo "  docker logs -f smart-noc-anomaly-detector"
