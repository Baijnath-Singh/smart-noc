# Network Connectivity Issue - Evidence Package
**Date:** June 11, 2026 19:30 UTC  
**Issue:** Switch syslog not reaching Smart NOC monitoring platform  
**Severity:** Medium - Monitoring functionality blocked

---

## 🎯 Executive Summary

Extreme Networks switch (10.139.38.188) is **confirmed generating syslog** but packets are **not reaching** Smart NOC server (10.37.12.33:5000) due to network-level blocking between 10.139.38.0/24 and 10.37.12.0/20 networks.

**Impact:** Network monitoring system cannot receive real-time logs from production switch.

---

## ✅ What's Working (Verified)

### Switch Side
- ✅ **Logs being generated:** 150+ events in memory buffer (authentication, ports, hardware)
- ✅ **Syslog configured:** Target `10.37.12.33:5000 local7` 
- ✅ **Syslog enabled:** Status confirmed via `show log configuration`
- ✅ **Recent activity:** Latest log entry `06/11/2026 18:35:51` (today)

### Smart NOC Side
- ✅ **UDP listener active:** Port 5000 listening on 0.0.0.0
- ✅ **Pipeline tested:** Local UDP test successful (Logstash → Kafka working)
- ✅ **No firewall blocks:** iptables policy ACCEPT for INPUT chain
- ✅ **Can reach switch:** Ping to 10.139.38.4 successful (211ms RTT)

---

## ❌ What's NOT Working (The Problem)

### Network Connectivity Test Results

#### Test 1: Switch → Smart NOC (FAILED)
```
* Slot-2 Stack.12 # ping 10.37.12.33 count 3
Ping(ICMP) 10.37.12.33: 4 packets, 8 data bytes
Packet transmit error; Destination unreachable
Packet transmit error; Destination unreachable
Packet transmit error; Destination unreachable

Result: 0 packets transmitted, 0 received, 0% loss
Status: ❌ FAILED - Cannot reach Smart NOC
```

#### Test 2: Smart NOC → Switch (SUCCESS)
```
user@colo-dev-vm-12-33:~$ ping -c 3 10.139.38.4
64 bytes from 10.139.38.4: icmp_seq=1 ttl=56 time=211 ms
64 bytes from 10.139.38.4: icmp_seq=2 ttl=56 time=211 ms
64 bytes from 10.139.38.4: icmp_seq=3 ttl=56 time=211 ms

Result: 3 packets transmitted, 3 received, 0% packet loss
Status: ✅ SUCCESS - Can reach switch
```

**Finding:** Asymmetric routing - one direction works, other doesn't.

#### Test 3: Packet Capture on Smart NOC (30 seconds)
```
sudo tcpdump -i any -nn 'src host 10.139.38.188 and udp port 5000' -c 3 -v
Result: 0 packets captured
Status: ❌ NO TRAFFIC - Switch packets not arriving
```

---

## 🔍 Switch Configuration Details

### Network Configuration
```
Switch IP:     10.139.38.188/24
Management VLAN: Mgmt (VID 4095)
Virtual Router: VR-Mgmt
Default Gateway: 10.139.38.1
```

### Routing Table (VR-Mgmt)
```
Destination        Gateway         Flags
Default Route      10.139.38.1     UG-D---um--f-  (BOOTP)
10.139.38.0/24     10.139.38.188   U------um--f-  (Direct)
```

**Analysis:** Switch has default route via 10.139.38.1, but gateway appears to be blocking or not routing to 10.37.12.0/20 network.

### Syslog Configuration
```
Log Target: syslog; 10.37.12.33:5000 (vr VR-Mgmt), local7
    Enabled:     yes  ✅
    Filter Name: DefaultFilter
    Match regex: Any
    Severity:    Debug-Data (through Critical)
    Format:      PRI Mmm DD HH:MM:SS HOSTNAME TAG: Slot:
    Port Type:   UDP
```

### Sample Log Entries (Latest 5)
```
06/11/2026 18:35:51.84 <Info:AAA.authPass> Login passed for user admin
06/11/2026 18:09:17.77 <Info:AAA.logout> Administrative account logout
06/11/2026 17:49:15.18 <Info:AAA.authPass> Login passed for user admin
06/11/2026 17:48:01.80 <Warn:AAA.authFail> Login failed - invalid password
06/11/2026 17:46:49.81 <Warn:AAA.authFail> Previous message repeated 4 times
```

**These logs SHOULD be going to Smart NOC but are not arriving.**

---

## 📊 Smart NOC Configuration Details

### Network Configuration
```
Server IP:   10.37.12.33/20
Interface:   ens160
Gateway:     10.37.12.1 (assumed)
Docker Network: 192.168.32.1/20 (bridge br-5d79e7b69514)
```

### UDP Listener Status
```
$ ss -uln | grep 5000
UNCONN  0  0  0.0.0.0:5000  0.0.0.0:*  ✅ LISTENING
UNCONN  0  0     [::]:5000     [::]:*  ✅ LISTENING
```

### Docker Port Mapping
```
Container: smart-noc-logstash
Ports: 
  0.0.0.0:5000->5000/tcp  ✅
  0.0.0.0:5000->5000/udp  ✅
  :::5000->5000/tcp       ✅
  :::5000->5000/udp       ✅
```

### Pipeline Verification (Local Test)
```
$ echo "<134>Jun 11 19:15:00 10.139.38.188 ExtremeSwitch: TEST" | nc -u localhost 5000
Result: Message successfully received and processed through Kafka ✅
```

---

## 🎯 Root Cause Analysis

### Problem Location
Traffic is being **blocked between switch gateway (10.139.38.1) and Smart NOC (10.37.12.33)**.

### Evidence Chain
1. ✅ Switch generates logs (150+ entries confirmed)
2. ✅ Switch syslog configured and enabled
3. ✅ Smart NOC UDP listener ready and tested
4. ❌ **Switch cannot ping Smart NOC** (Destination unreachable)
5. ❌ **Packet capture shows zero arrivals** (30 seconds, 0 packets)
6. ✅ Smart NOC CAN reach switch (ping successful)

### Likely Causes (Priority Order)
1. **Firewall blocking** UDP 5000 from 10.139.38.188 → 10.37.12.33
2. **Gateway routing** - Gateway 10.139.38.1 lacks route to 10.37.12.0/20
3. **ACL/Policy** - Access control list blocking inter-network traffic
4. **VLAN isolation** - VR-Mgmt restricted from reaching certain networks

---

## 🔧 Required Solution

### Option 1: Firewall Rule (Recommended - Fastest)
**Add firewall exception:**
```
Source:      10.139.38.188/32
Destination: 10.37.12.33/32
Protocol:    UDP
Port:        5000
Direction:   Permit
Purpose:     Syslog monitoring
```

### Option 2: Gateway Routing
**Add route on gateway 10.139.38.1:**
```
ip route add 10.37.12.0/20 via <next-hop-gateway>
```

### Option 3: Static Route on Switch
**Add static route (requires change approval):**
```
configure iproute add 10.37.12.0/20 <gateway-ip> vr VR-Mgmt
save configuration
```

---

## ✅ Verification Steps (After Fix)

### Step 1: Test ICMP
```bash
# On Switch:
ping 10.37.12.33 count 3
# Expected: 3 packets transmitted, 3 received, 0% loss
```

### Step 2: Verify Syslog Arrival
```bash
# On Smart NOC:
sudo tcpdump -i any -nn 'src host 10.139.38.188 and udp port 5000' -c 5 -v
# Expected: See UDP packets with syslog data within 30 seconds
```

### Step 3: Confirm End-to-End
```bash
# On Smart NOC:
docker logs -f smart-noc-logstash | grep "10.139.38"
# Expected: See parsed syslog messages from switch

# Check Kafka:
docker exec smart-noc-kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 --topic network-logs \
  --from-beginning | grep "10.139.38"
# Expected: JSON messages with device_id containing switch IP
```

---

## 📈 Expected Traffic Volume

**Normal Operations:**
- **Message Rate:** 50-200 messages/hour
- **Bandwidth:** ~10-50 KB/hour (~100 bytes/message)
- **Protocol:** UDP (stateless, fire-and-forget)
- **Impact:** Negligible - less than 0.01% network utilization

**Peak Activity:**
- **During incidents:** Up to 1000 messages/hour
- **During configuration changes:** Up to 500 messages/hour
- **Maximum bandwidth:** <200 KB/hour

---

## 🔒 Security Considerations

### Traffic Characteristics
- **Direction:** Unidirectional (Switch → Smart NOC only)
- **Return traffic:** None required (UDP syslog is fire-and-forget)
- **Protocol:** UDP port 5000 (standard syslog)
- **Encryption:** None (internal network, plaintext syslog)

### Risk Assessment
- **Security Risk:** Low - read-only monitoring data
- **Availability Risk:** None - no return path needed
- **Compliance:** Standard syslog protocol (RFC 3164/5424)

---

## 📋 Approval Checklist

- [ ] Network team review
- [ ] Firewall change approved
- [ ] Routing verification completed
- [ ] Change window scheduled (if needed)
- [ ] Firewall rule implemented
- [ ] Connectivity verified (ping test)
- [ ] Syslog flow confirmed (tcpdump)
- [ ] Smart NOC monitoring active
- [ ] Documentation updated

---

## 📞 Contact Information

**Smart NOC Team:**
- Server: 10.37.12.33 (colo-dev-vm-12-33)
- Service: Logstash UDP Syslog Receiver (Port 5000)

**Switch Information:**
- Device: Extreme Networks Switch Stack
- Management IP: 10.139.38.188
- Data Plane: 10.139.38.4
- Console: Port 5019 (telnet)

---

## 📎 Attachments

1. Switch log dump (150+ entries showing active logging)
2. Smart NOC packet capture (0 packets received - proof of blocking)
3. Ping test results (asymmetric connectivity)
4. Routing table export (VR-Mgmt)
5. Syslog configuration export

---

**Next Action:** Please review and approve firewall rule to enable UDP 5000 from 10.139.38.188 → 10.37.12.33.

**Timeline:** Waiting on network team action.
