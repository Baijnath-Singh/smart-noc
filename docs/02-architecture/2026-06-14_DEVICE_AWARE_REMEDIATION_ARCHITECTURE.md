# Device-Aware Remediation Architecture

## 🎯 **Problem Statement**

**Challenge:** How can the LLM provide accurate, device-specific CLI commands when only an IP address is in the syslog message?

**Example Scenario:**
```
Syslog: <134>Jun 11 18:35:51 10.139.38.188 Slot-2: Port 1:58 link down
```

**Questions:**
- Is this Extreme Networks EXOS, VOSS, or Fabric Engine?
- Is it Cisco IOS, IOS-XR, or NXOS?
- Is it Juniper JunOS?
- What's the correct CLI syntax for this device?

---

## ✅ **Solution Architecture**

### **Component 1: Device Inventory Database**

**Table: `devices`**
```sql
CREATE TABLE devices (
    device_id VARCHAR(255) PRIMARY KEY,      -- IP or hostname
    management_ip INET,                      -- 10.139.38.188
    vendor VARCHAR(50),                      -- 'Extreme Networks'
    device_family VARCHAR(50),               -- 'EXOS' (OS/Platform)
    model VARCHAR(100),                      -- 'X690-48x'
    os_version VARCHAR(50),                  -- '32.6.1.2'
    cli_syntax VARCHAR(50),                  -- 'EXOS' (command syntax)
    device_role VARCHAR(50),                 -- 'core', 'edge', 'access'
    ...
);
```

**Sample Data:**
```sql
INSERT INTO devices VALUES (
    '10.139.38.188',
    '10.139.38.188'::inet,
    'Extreme Networks',
    'EXOS',
    'X690-48x (2-slot stack)',
    '32.6.1.2',
    'EXOS',
    'core'
);
```

---

### **Component 2: Logstash Device Enrichment**

**Location:** `infrastructure/logstash/pipeline/syslog-input.conf`

**Process:**
1. Syslog arrives with IP: `10.139.38.188`
2. Logstash queries device inventory database
3. Adds device metadata to log message

**Logstash Filter (JDBC Lookup):**
```ruby
filter {
  # ... existing syslog parsing ...
  
  # Device Inventory Enrichment
  if [syslog_hostname] {
    jdbc_streaming {
      jdbc_connection_string => "jdbc:postgresql://postgres:5432/smart_noc"
      jdbc_user => "noc_admin"
      jdbc_password => "noc_password"
      statement => "SELECT vendor, device_family, model, os_version, cli_syntax, device_role 
                    FROM devices 
                    WHERE device_id = :device_id OR management_ip = CAST(:device_id AS inet)"
      parameters => { "device_id" => "[syslog_hostname]" }
      target => "device_info"
    }
    
    # Add fields to message
    if [device_info][0] {
      mutate {
        add_field => {
          "device_vendor" => "%{[device_info][0][vendor]}"
          "device_family" => "%{[device_info][0][device_family]}"
          "device_model" => "%{[device_info][0][model]}"
          "device_os_version" => "%{[device_info][0][os_version]}"
          "device_cli_syntax" => "%{[device_info][0][cli_syntax]}"
        }
      }
    }
  }
}
```

**Enriched Output to Kafka:**
```json
{
  "timestamp": "2026-06-11T18:35:51Z",
  "syslog_hostname": "10.139.38.188",
  "message": "Slot-2: Port 1:58 link down",
  "event_type": "INTERFACE_DOWN",
  "interface": "1:58",
  "severity": "WARNING",
  "device_vendor": "Extreme Networks",
  "device_family": "EXOS",
  "device_model": "X690-48x (2-slot stack)",
  "device_os_version": "32.6.1.2",
  "device_cli_syntax": "EXOS"
}
```

---

### **Component 3: LLM Diagnosis with Device Context**

**Location:** `services/llm-diagnosis/context_builder.py`

**Process:**
```python
# Priority 1: Use device info from enriched Kafka message
if anomalies:
    first_anomaly = anomalies[0]
    if 'device_vendor' in first_anomaly:
        vendor = first_anomaly.get('device_vendor', '').lower().split()[0]  # "extreme"
        platform = first_anomaly.get('device_family', '').lower()           # "exos"
        device_model = first_anomaly.get('device_model')                    # "X690-48x"
        device_os = first_anomaly.get('device_os_version')                  # "32.6.1.2"
        cli_syntax = first_anomaly.get('device_cli_syntax')                 # "EXOS"
        
        logger.info(f"Device: {vendor} {platform}, Model: {device_model}, OS: {device_os}")

# Priority 2: Fallback to heuristic detection if no inventory data
if vendor == "generic":
    # Use hostname patterns: "exos-sw", "vsp-8600", etc.
    if "exos" in device_id.lower():
        vendor = "extreme"
        platform = "exos"
```

**Vector KB Search with Device Filters:**
```python
# Search knowledge base with device-specific filters
results = self.vector_kb.find_relevant_kb(
    query_text="Interface 1:58 link down troubleshooting",
    event_type="INTERFACE_DOWN",
    vendor="extreme",        # Filter to Extreme Networks articles
    platform="exos",         # Filter to EXOS-specific commands
    top_k=5,
    min_relevance=0.50
)
```

---

### **Component 4: LLM Prompt with Device Details**

**System Prompt Enhancement:**
```
You are an expert network operations engineer analyzing an incident.

DEVICE CONTEXT:
- Vendor: Extreme Networks
- Platform: EXOS
- Model: X690-48x (2-slot stack)
- OS Version: 32.6.1.2
- CLI Syntax: EXOS

When providing remediation commands, use EXOS CLI syntax:
✓ show port 1:58 information detail
✓ show port 1:58 statistics
✓ enable port 1:58
✗ show interface GigabitEthernet1/0/58  (Wrong - This is Cisco IOS syntax!)
```

**Knowledge Base Articles (Device-Specific):**
```
KB Article #42: Interface Down Troubleshooting - Extreme EXOS

Platform: EXOS
Device Family: X-series (X460, X670, X690)

Diagnostic Commands:
1. show port <port> information detail
2. show port <port> statistics
3. show port <port> transceiver information detail

Common Causes:
- SFP transceiver failure
- Cable issues
- Admin disabled
- ELRP (Extreme Loop Recovery Protocol) shutdown

Remediation:
1. Check admin status: show port <port> configuration
2. Check transceiver: show port <port> transceiver information
3. Enable port: enable port <port>
4. Clear counters: clear counters port <port>
```

---

### **Component 5: LLM Response with Correct CLI**

**LLM Diagnosis Output:**
```json
{
  "root_cause": "Interface 1:58 on X690 core switch down due to transceiver power alarm",
  "confidence_score": 0.85,
  "reasoning": "Sensor alarm logs show TX Power low alarm immediately before link down...",
  "remediation_steps": [
    {
      "step": 1,
      "description": "Check interface status and transceiver health",
      "commands": [
        "show port 1:58 information detail",
        "show port 1:58 transceiver information detail"
      ],
      "expected_output": "Check for 'low alarm' in TX/RX power sensors",
      "cli_syntax": "EXOS"
    },
    {
      "step": 2,
      "description": "Reseat or replace transceiver",
      "commands": [
        "disable port 1:58",
        "# Physically reseat SFP module",
        "enable port 1:58"
      ],
      "expected_output": "Port should come up if transceiver connection was loose",
      "cli_syntax": "EXOS"
    },
    {
      "step": 3,
      "description": "Verify link restoration",
      "commands": [
        "show port 1:58 information | include Status",
        "show port 1:58 statistics | include Error"
      ],
      "expected_output": "Status: Active, Speed: 10Gbps, Errors: 0",
      "cli_syntax": "EXOS"
    }
  ],
  "priority": "SHORT_TERM",
  "estimated_resolution_time": "15 minutes"
}
```

---

## 🔄 **Complete Data Flow**

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. SWITCH GENERATES SYSLOG                                          │
│    <134>Jun 11 18:35:51 10.139.38.188 Slot-2: Port 1:58 link down  │
└────────────────────────┬────────────────────────────────────────────┘
                         │ UDP port 5000
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 2. LOGSTASH RECEIVES & ENRICHES                                     │
│    • Parses syslog (RFC3164)                                        │
│    • Extracts: IP=10.139.38.188, Interface=1:58                     │
│    • Queries device inventory: SELECT * FROM devices WHERE ip=...   │
│    • Adds: vendor=Extreme, family=EXOS, model=X690, cli=EXOS        │
└────────────────────────┬────────────────────────────────────────────┘
                         │ Kafka: network-logs
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 3. ANOMALY DETECTOR ANALYZES                                        │
│    • Detects: INTERFACE_DOWN on device 10.139.38.188                │
│    • Preserves device metadata from enriched log                    │
└────────────────────────┬────────────────────────────────────────────┘
                         │ Kafka: anomalies
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 4. CORRELATION ENGINE CREATES INCIDENT                              │
│    • Groups: Single HIGH severity INTERFACE_DOWN                    │
│    • Creates: Incident #20017                                       │
│    • Preserves: All device metadata                                 │
└────────────────────────┬────────────────────────────────────────────┘
                         │ Kafka: incidents + PostgreSQL
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 5. LLM DIAGNOSIS SERVICE                                            │
│    • Reads incident + anomalies (with device metadata)              │
│    • Extracts: vendor=extreme, platform=exos, model=X690            │
│    • Searches Vector KB with filters: vendor=extreme, platform=exos │
│    • Finds: "EXOS Interface Down Troubleshooting" KB article        │
│    • Builds prompt with device context                              │
└────────────────────────┬────────────────────────────────────────────┘
                         │ Groq LLM API
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 6. GROQ LLM ANALYZES                                                │
│    System Prompt: "Device is Extreme EXOS X690, use EXOS commands" │
│    KB Articles: EXOS-specific troubleshooting guides                │
│    Generates: Root cause + EXOS CLI commands (not Cisco/Juniper!)  │
└────────────────────────┬────────────────────────────────────────────┘
                         │ Kafka: incidents-diagnosed
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 7. REMEDIATION AGENT                                                │
│    • Validates commands match cli_syntax=EXOS                       │
│    • Checks device_role=core → requires_approval=true               │
│    • Decision: MANUAL_ONLY (core switch, needs human approval)      │
│    • If auto-remediation approved:                                  │
│      - Uses Netmiko with device_type='extreme_exos'                 │
│      - Executes: show port 1:58 information detail                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📊 **Device Inventory Population Methods**

### **Method 1: Manual Entry (Small Networks)**
```bash
# Add devices manually
docker exec -i smart-noc-postgres psql -U noc_admin -d smart_noc <<EOF
INSERT INTO devices VALUES 
('10.10.1.1', '10.10.1.1', 'Extreme Networks', 'EXOS', 'X460-G2', '32.6.1.2', 'EXOS', 'core'),
('10.10.1.2', '10.10.1.2', 'Cisco', 'IOS', 'Catalyst9300', '16.12.5', 'IOS', 'distribution'),
('10.10.1.3', '10.10.1.3', 'Juniper', 'JUNOS', 'EX4300', '22.3R1', 'JUNOS', 'access');
EOF
```

### **Method 2: SNMP Discovery (Recommended)**
```python
# Auto-discover devices via SNMP
from pysnmp.hlapi import *

def discover_device(ip):
    # Get sysObjectID
    oid = ObjectIdentity('SNMPv2-MIB', 'sysObjectID', 0)
    result = getCmd(SnmpEngine(), CommunityData('public'),
                    UdpTransportTarget((ip, 161)), ContextData(), oid)
    
    # Parse vendor/model from OID
    # Extreme: 1.3.6.1.4.1.1916.2.xxx
    # Cisco: 1.3.6.1.4.1.9.xxx
    # Juniper: 1.3.6.1.4.1.2636.xxx
    
    # Get sysDescr for OS version
    # Insert into database
```

### **Method 3: Network Management System Integration**
```python
# Import from ExtremeCloud IQ, Cisco Prime, etc.
import requests

# ExtremeCloud IQ API
devices = requests.get('https://api.extremecloudiq.com/devices',
                       headers={'Authorization': f'Bearer {token}'}).json()

for device in devices:
    db.execute("""
        INSERT INTO devices (device_id, management_ip, vendor, device_family, model, os_version)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (device['ip'], device['ip'], 'Extreme Networks', 
          device['platform'], device['model'], device['softwareVersion']))
```

### **Method 4: CSV Import (Bulk)**
```csv
device_id,management_ip,vendor,device_family,model,os_version,cli_syntax,device_role
10.10.1.1,10.10.1.1,Extreme Networks,EXOS,X460-G2,32.6.1.2,EXOS,core
10.10.1.2,10.10.1.2,Extreme Networks,VOSS,VSP8600,8.2.5,VOSS,core
10.10.1.3,10.10.1.3,Cisco,IOS,Cat9300,16.12.5,IOS,distribution
```

```bash
# Import CSV
docker exec -i smart-noc-postgres psql -U noc_admin -d smart_noc <<EOF
COPY devices(device_id, management_ip, vendor, device_family, model, os_version, cli_syntax, device_role)
FROM '/tmp/devices.csv' CSV HEADER;
EOF
```

---

## 🎯 **Benefits of Device Inventory Integration**

### **1. Accurate CLI Commands**
- **Before:** Generic "show interface" command (wrong for many vendors)
- **After:** Correct "show port 1:58 information detail" for EXOS

### **2. Vendor-Specific Knowledge**
- **Before:** Generic KB articles for all vendors
- **After:** EXOS-specific articles with exact CLI syntax and common issues

### **3. Automated Remediation**
- **Before:** Can't execute commands (don't know CLI syntax)
- **After:** Can use Netmiko/Netconf with correct device_type

### **4. Context-Aware Analysis**
- **Before:** "Interface down" (could be any vendor)
- **After:** "Interface down on Extreme X690 core switch - check transceiver"

### **5. Compliance & Safety**
- **Before:** Can't check criticality rules
- **After:** "Core switch - requires approval before changes"

---

## 🚀 **Next Steps**

### **Phase 1: Basic Implementation (Current)**
✅ Device inventory table created  
✅ Logstash enrichment filter added  
✅ LLM diagnosis updated to use device metadata  
⏳ Need to: Install PostgreSQL JDBC driver in Logstash  
⏳ Need to: Populate device inventory  

### **Phase 2: Discovery & Automation**
- [ ] SNMP-based auto-discovery
- [ ] NetMiko integration for command execution
- [ ] Device capability matrix (supports NETCONF/RESTCONF?)

### **Phase 3: Advanced Features**
- [ ] Device configuration backup/versioning
- [ ] Change management workflow
- [ ] Compliance validation (approved commands per device type)

---

## 📝 **Testing the Complete Flow**

```bash
# 1. Populate device inventory
docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -c \
  "SELECT device_id, vendor, device_family, model FROM devices;"

# 2. Send test syslog
echo "<134>Jun 13 12:00:00 10.139.38.188 Slot-2: Port 1:58 link down" | \
  nc -u localhost 5000

# 3. Check enriched message in Kafka
docker exec smart-noc-kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 --topic network-logs \
  --from-beginning --max-messages 1 | jq '.'

# Should see:
{
  "device_vendor": "Extreme Networks",
  "device_family": "EXOS",
  "device_model": "X690-48x (2-slot stack)",
  ...
}

# 4. Check LLM diagnosis used device context
docker logs smart-noc-llm-diagnosis | grep "Device context"
# Should see: "Device context - Vendor: extreme, Platform: exos"

# 5. Verify CLI commands are EXOS-specific
docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -c \
  "SELECT root_cause, remediation_steps FROM incident_diagnosis_history 
   ORDER BY diagnosed_at DESC LIMIT 1;" | grep "show port"
# Should see: "show port 1:58" (EXOS), NOT "show interface Gi1/0/58" (Cisco)
```

---

## 🏆 **Summary**

**Question:** How does LLM know device details from just an IP address?

**Answer:** 
1. **Device Inventory** stores IP → Vendor/Model/OS/CLI mappings
2. **Logstash enriches** syslog with database lookup
3. **LLM receives** full device context in anomaly data
4. **Vector KB filters** to vendor-specific knowledge articles  
5. **LLM generates** device-specific commands (EXOS, not Cisco!)
6. **Remediation agent** validates CLI syntax matches device type

**Result:** Accurate, device-specific remediation commands! 🎯
