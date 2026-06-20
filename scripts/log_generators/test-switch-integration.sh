#!/bin/bash
# Quick Test: Verify Switch Log Integration with Smart NOC

set -e

SMART_NOC_IP="10.37.12.33"  # Change this to your Smart NOC server IP
LOGSTASH_PORT="5000"
SWITCH_IP="10.139.38.4"

echo "================================================================================"
echo "SMART NOC - EXTREME SWITCH INTEGRATION TEST"
echo "================================================================================"
echo ""

echo "Step 1: Checking if Logstash is listening on port $LOGSTASH_PORT..."
if netstat -tuln | grep -q ":$LOGSTASH_PORT"; then
    echo "   ✅ Logstash is listening on port $LOGSTASH_PORT"
else
    echo "   ⚠️  Logstash may not be listening. Checking Docker..."
    docker ps | grep logstash
fi
echo ""

echo "Step 2: Testing connectivity from Smart NOC to switch..."
if ping -c 2 $SWITCH_IP > /dev/null 2>&1; then
    echo "   ✅ Can ping switch at $SWITCH_IP"
else
    echo "   ⚠️  Cannot ping switch at $SWITCH_IP"
fi
echo ""

echo "Step 3: Sending test syslog message to Logstash..."
echo "<134>$(date '+%b %d %H:%M:%S') test-switch TEST: Smart NOC integration test message" | nc -w 1 localhost $LOGSTASH_PORT
sleep 2
echo "   ✅ Test message sent"
echo ""

echo "Step 4: Checking Logstash logs for test message..."
docker logs smart-noc-logstash --tail=20 | grep -i "test" && echo "   ✅ Test message received" || echo "   ⚠️  Test message not found"
echo ""

echo "Step 5: Checking Kafka for raw-logs..."
timeout 5 docker exec smart-noc-kafka kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic raw-logs \
  --from-beginning \
  --max-messages 1 2>/dev/null && echo "   ✅ Kafka receiving logs" || echo "   ⚠️  No messages in Kafka"
echo ""

echo "================================================================================"
echo "NEXT STEPS TO CONFIGURE YOUR SWITCH"
echo "================================================================================"
echo ""
echo "1. Telnet to your switch:"
echo "   telnet $SWITCH_IP 5019"
echo ""
echo "2. Login (username: admin, password: press Enter)"
echo ""
echo "3. Configure syslog (copy-paste these commands):"
echo ""
cat << 'EOF'
configure
configure syslog add 10.37.12.33:5000 local7
configure syslog add 10.37.12.33:5000 local7 debug-data info warning error critical
enable log target syslog 10.37.12.33:5000
save configuration
exit
EOF
echo ""
echo "4. Verify configuration:"
echo "   show log configuration"
echo "   show log target syslog"
echo ""
echo "5. Generate test log:"
echo "   log message \"TEST: Smart NOC integration successful\""
echo ""
echo "6. Monitor logs on Smart NOC:"
echo "   docker logs -f smart-noc-logstash | grep \"$SWITCH_IP\""
echo ""
echo "================================================================================"
echo "TROUBLESHOOTING"
echo "================================================================================"
echo ""
echo "If logs don't appear:"
echo ""
echo "• Check firewall: sudo iptables -L -n | grep $LOGSTASH_PORT"
echo "• Monitor port: sudo tcpdump -i any -n port $LOGSTASH_PORT"
echo "• Check Logstash: docker logs smart-noc-logstash --tail=50"
echo "• Test directly: echo 'TEST' | nc localhost $LOGSTASH_PORT"
echo ""
echo "================================================================================"
