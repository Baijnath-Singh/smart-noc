#!/bin/bash
# ==============================================================================
# Convert Switch Logs to Syslog and Send to Smart NOC
# ==============================================================================
# This script reads actual switch log entries (from switch memory buffer)
# and converts them to proper syslog format for Smart NOC testing.
#
# Usage: 
#   1. Copy switch logs to a file: switch-logs.txt
#   2. Run: ./convert-switch-logs.sh switch-logs.txt

set -e

if [ $# -eq 0 ]; then
    echo "Usage: $0 <switch-log-file>"
    echo ""
    echo "Example:"
    echo "  1. On switch: show log messages memory-buffer > logs.txt"
    echo "  2. Copy logs.txt to Smart NOC server"
    echo "  3. Run: $0 logs.txt"
    exit 1
fi

LOG_FILE="$1"
LOGSTASH_IP="localhost"
LOGSTASH_PORT="5000"
SWITCH_IP="10.139.38.188"
FACILITY_PRIORITY="134"  # local7.info

if [ ! -f "$LOG_FILE" ]; then
    echo "Error: File $LOG_FILE not found"
    exit 1
fi

echo "=================================================="
echo "  Converting Switch Logs to Syslog Format"
echo "=================================================="
echo "Input file: ${LOG_FILE}"
echo "Target: ${LOGSTASH_IP}:${LOGSTASH_PORT}"
echo "Switch IP: ${SWITCH_IP}"
echo ""

COUNT=0

# Read switch logs and convert to syslog format
while IFS= read -r line; do
    # Skip empty lines
    if [ -z "$line" ]; then
        continue
    fi
    
    # Skip lines that don't look like logs (e.g., switch prompt)
    if [[ "$line" =~ ^[[:space:]]*\*.*Stack\.[0-9]+ ]]; then
        continue
    fi
    
    # Extract date/time and message from switch log format:
    # 06/11/2026 18:35:51.84 <Info:AAA.authPass> Slot-2: Login passed...
    if [[ "$line" =~ ^([0-9]{2}/[0-9]{2}/[0-9]{4}[[:space:]]+[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]+)[[:space:]]+\<([^>]+)\>[[:space:]]+(.+)$ ]]; then
        switch_timestamp="${BASH_REMATCH[1]}"
        severity="${BASH_REMATCH[2]}"
        message="${BASH_REMATCH[3]}"
        
        # Convert switch timestamp to syslog timestamp (Mmm DD HH:MM:SS)
        # For simplicity, use current timestamp
        syslog_timestamp=$(date '+%b %d %H:%M:%S')
        
        # Create syslog message in RFC3164 format
        syslog_msg="<${FACILITY_PRIORITY}>${syslog_timestamp} ${SWITCH_IP} ${message}"
        
        # Send to Logstash
        echo "${syslog_msg}" | nc -u -w1 ${LOGSTASH_IP} ${LOGSTASH_PORT}
        
        COUNT=$((COUNT + 1))
        echo "[${COUNT}] Sent: ${message:0:80}..."
        
        # Small delay to avoid overwhelming
        sleep 0.1
    fi
done < "$LOG_FILE"

echo ""
echo "=================================================="
echo "  Sent ${COUNT} log entries to Smart NOC"
echo "=================================================="
echo ""
echo "Verification commands:"
echo ""
echo "# Check Kafka for messages:"
echo "docker exec smart-noc-kafka /opt/kafka/bin/kafka-console-consumer.sh \\"
echo "  --bootstrap-server localhost:9092 --topic network-logs \\"
echo "  --from-beginning --max-messages 20 | grep '${SWITCH_IP}'"
echo ""
echo "# Watch Logstash processing:"
echo "docker logs -f smart-noc-logstash"
echo ""
