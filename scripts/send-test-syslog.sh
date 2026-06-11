#!/bin/bash
# ==============================================================================
# Send Test Syslog Messages to Smart NOC
# ==============================================================================
# This script converts Extreme Networks switch logs to syslog format
# and sends them to Logstash for testing the pipeline.
#
# Usage: ./send-test-syslog.sh

set -e

LOGSTASH_IP="localhost"  # Send from Smart NOC to itself
LOGSTASH_PORT="5000"
SWITCH_IP="10.139.38.188"
SWITCH_HOSTNAME="ExtremeSwitch"
FACILITY="local7"  # Same as configured on switch
PRIORITY="134"     # local7 (16) << 3 + info (6) = 134

echo "=================================================="
echo "  Smart NOC - Test Syslog Sender"
echo "=================================================="
echo "Target: ${LOGSTASH_IP}:${LOGSTASH_PORT}"
echo "Switch IP: ${SWITCH_IP}"
echo "Facility: ${FACILITY} (Priority: ${PRIORITY})"
echo ""

# Function to send a syslog message
send_syslog() {
    local message="$1"
    local timestamp=$(date '+%b %d %H:%M:%S')
    
    # RFC3164 syslog format: <PRI>TIMESTAMP HOSTNAME MESSAGE
    local syslog_msg="<${PRIORITY}>${timestamp} ${SWITCH_IP} ${message}"
    
    echo "Sending: ${message}"
    echo "${syslog_msg}" | nc -u -w1 ${LOGSTASH_IP} ${LOGSTASH_PORT}
    sleep 0.5
}

echo "Sending test messages..."
echo ""

# Example 1: Authentication success
send_syslog "AAA.authPass: Login passed for user admin through ssh (10.37.12.33)"

# Example 2: Authentication failure
send_syslog "AAA.authFail: Login failed due to invalid username/password for user testuser through ssh (192.168.1.100)"

# Example 3: Port link up
send_syslog "vlan.msgs.portLinkStateUp: Port 1:5 link UP at speed 1 Gbps and full-duplex"

# Example 4: Port link down
send_syslog "vlan.msgs.portLinkStateDown: Port 1:8 link down"

# Example 5: BGP neighbor down (critical event)
send_syslog "BGP.Notif: BGP neighbor 10.0.1.2 connection down"

# Example 6: System warning
send_syslog "DM.Warning: Slot-1 FAILED (1)"

# Example 7: Hardware sensor
send_syslog "DM.SensorAlarmDtect: Port 1:1 TX Power Sensor=low alarm Value=0.00 mW"

# Example 8: Configuration change
send_syslog "CM.Change: Configuration saved to primary.cfg by admin"

echo ""
echo "=================================================="
echo "  Sent 8 test syslog messages"
echo "=================================================="
echo ""
echo "Now verify they arrived in Smart NOC:"
echo ""
echo "1. Check Logstash logs:"
echo "   docker logs smart-noc-logstash --tail 30"
echo ""
echo "2. Check Kafka:"
echo "   docker exec smart-noc-kafka /opt/kafka/bin/kafka-console-consumer.sh \\"
echo "     --bootstrap-server localhost:9092 --topic network-logs \\"
echo "     --from-beginning --max-messages 10 | grep '${SWITCH_IP}'"
echo ""
echo "3. Check Elasticsearch:"
echo "   curl -s 'http://localhost:9200/network-logs-*/_search?q=device_id:${SWITCH_IP}&size=10' | jq '.hits.hits[]._source.message'"
echo ""
