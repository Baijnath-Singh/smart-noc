# Network Connectivity Request - Smart NOC Syslog Integration

**Date:** June 11, 2026  
**Requestor:** NOC Team  
**Priority:** Medium  
**Type:** Firewall/Routing Rule Addition

---

## 📋 Request Summary

Enable UDP syslog connectivity from **Extreme Networks switch** to **Smart NOC server** for network monitoring and incident management.

---

## 🎯 Required Connectivity

### Source (Switch)
- **Device:** Extreme Networks Switch (Stack)
- **IP Address:** 10.139.38.188/24
- **Management VLAN:** Mgmt (VID 4095)
- **Virtual Router:** VR-Mgmt
- **Gateway:** 10.139.38.1

### Destination (Smart NOC)
- **Server:** Smart NOC Monitoring Platform
- **IP Address:** 10.37.12.33/20
- **Interface:** ens160
- **Service:** Logstash Syslog Receiver

### Traffic Details
- **Protocol:** UDP
- **Port:** 5000
- **Direction:** Unidirectional (Switch → Smart NOC only)
- **Traffic Type:** Syslog (RFC 3164/5424)
- **Estimated Volume:** 50-200 messages/hour (~10-50 KB/hour)

---

## 🔍 Current Status

### Connectivity Test Results

```bash
# From Switch (10.139.38.188) to Smart NOC (10.37.12.33)
* Slot-2 Stack.12 # ping 10.37.12.33
Ping(ICMP) 10.37.12.33: 4 packets, 8 data bytes
Packet transmit error; Destination unreachable  ❌ FAILED
0 packets transmitted, 0 packets received, 0% loss

# From Smart NOC (10.37.12.33) to Switch (10.139.38.4)
user@colo-dev-vm-12-33:~$ ping -c 3 10.139.38.4
64 bytes from 10.139.38.4: icmp_seq=1 ttl=56 time=211 ms  ✅ SUCCESS
3 packets transmitted, 3 received, 0% packet loss
```

**Analysis:** Asymmetric connectivity - Smart NOC can reach switch, but switch cannot reach Smart NOC.

### Switch Routing Configuration

```
VR-Mgmt Routing Table:
Default Route: 10.139.38.1 (gateway)
Direct Route:  10.139.38.0/24 via 10.139.38.188

No specific route to 10.37.12.0/20 network
```

---

## ✅ What's Already Configured

### On Switch Side
- [x] Syslog target configured: `10.37.12.33:5000 local7`
- [x] Syslog target enabled
- [x] Management VLAN operational (VR-Mgmt)
- [x] Default gateway configured (10.139.38.1)

### On Smart NOC Side
- [x] Logstash UDP listener active on port 5000
- [x] Docker firewall rules configured
- [x] End-to-end pipeline tested and verified
- [x] Kafka integration working

---

## 🚀 Required Actions

### Option 1: Firewall Rule (Recommended)
Add firewall rule to allow UDP traffic:

```
Source:      10.139.38.188
Destination: 10.37.12.33
Port:        5000/UDP
Protocol:    UDP
Direction:   Allow (Ingress to 10.37.12.33)
Service:     Syslog
```

### Option 2: Routing Configuration
If gateway 10.139.38.1 lacks route to 10.37.12.0/20:

1. Add route on gateway 10.139.38.1:
   ```
   ip route add 10.37.12.0/20 via <next-hop-gateway>
   ```

2. Or add static route on switch (requires approval):
   ```
   configure iproute add 10.37.12.0/20 <gateway-ip> vr VR-Mgmt
   ```

---

## 🧪 Verification Steps

After firewall/routing changes, verify connectivity:

### Step 1: Test ICMP (Ping)
```bash
# On Switch:
ping 10.37.12.33 count 3
# Expected: 0% packet loss
```

### Step 2: Test UDP Syslog
```bash
# On Switch (generate test log):
show log configuration
# Logs should appear in Smart NOC within 5 seconds
```

### Step 3: Verify on Smart NOC
```bash
# Check Logstash received logs:
docker logs smart-noc-logstash --since 1m | grep "10.139.38"

# Check Kafka received logs:
docker exec smart-noc-kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 --topic network-logs \
  --from-beginning --max-messages 5 | grep "10.139.38"
```

---

## 📞 Contact Information

**Technical Owner:** NOC Operations Team  
**Smart NOC Server:** 10.37.12.33 (colo-dev-vm-12-33)  
**Switch Location:** 10.139.38.4:5019  

---

## 📎 Additional Context

### Why This is Needed
- Real-time network device monitoring
- Automated incident detection and correlation
- Safety framework for autonomous remediation
- Compliance and audit logging

### Business Impact
- **No Impact:** Read-only monitoring, no changes to switch operation
- **No Performance Impact:** Low-volume UDP syslog (~50 messages/hour)
- **No Availability Risk:** Fire-and-forget protocol, no switch dependency

### Security Considerations
- Unidirectional traffic (switch → monitoring only)
- Standard syslog protocol (RFC 3164/5424)
- No inbound connections to switch required
- UDP stateless protocol (low firewall state table impact)

---

## 🔄 Rollback Plan

If issues arise, disable syslog on switch:

```bash
# On Switch:
disable log target syslog 10.37.12.33:5000
configure syslog delete 10.37.12.33:5000
save configuration
```

**Rollback Time:** < 30 seconds  
**Risk:** None - removes monitoring only

---

## ✅ Approval

- [ ] Network Team Review
- [ ] Security Team Review (if required)
- [ ] Firewall Rule Implemented
- [ ] Connectivity Verified
- [ ] Monitoring Confirmed Active

---

**Next Steps:** Please review and approve this connectivity request. Once firewall/routing is configured, we can verify end-to-end syslog flow immediately.
