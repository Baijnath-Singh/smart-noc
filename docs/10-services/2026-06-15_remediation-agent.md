# Remediation Agent Service

**Service Name:** `smart-noc-remediation-agent`  
**Image:** `smart-noc_remediation-agent` (custom)  
**Technology:** Python 3.9  
**Status:** Core Service  
**Mode:** Simulation (safety-first)

---

## Overview

The Remediation Agent is the **execution layer** that receives LLM-diagnosed incidents and optionally executes remediation commands on network devices. Currently operates in **SIMULATION MODE** for safety, logging all actions without making actual device changes.

**Key Capabilities:**
- **Simulation Mode:** Logs commands without execution (current implementation)
- **Safety Framework:** Multi-layer validation before any action
- **Audit Trail:** Complete logging of all attempted actions
- **Future:** SSH/NETCONF device connector for autonomous execution

---

## Service Configuration

### Resources
- **Memory:** 256MB
- **CPU:** 0.5 cores
- **Storage:** Minimal (logs only)

### Environment Variables
```
KAFKA_BOOTSTRAP_SERVERS: kafka:9092
KAFKA_GROUP_ID: remediation-agent-group
POSTGRES_HOST: postgres
POSTGRES_PORT: 5432
POSTGRES_DB: smart_noc
POSTGRES_USER: noc_admin
POSTGRES_PASSWORD: noc_password
EXECUTION_MODE: simulation  # simulation | assisted | autonomous
LOG_LEVEL: INFO
```

---

## Architecture Components

### 1. **Kafka Consumer**

**Input Topic:** `incidents-diagnosed`  
**Consumer Group:** `remediation-agent-group`

**Input Message Format:**
```json
{
  "incident_number": 20024,
  "device_id": "10.139.38.188",
  "device_vendor": "Extreme Networks",
  "device_cli_syntax": "EXOS",
  "root_cause": "Multiple interfaces showing flapping behavior...",
  "confidence_score": 0.85,
  "remediation_plan": {
    "commands": [
      "show port 1:55 information detail",
      "show port 2:22 information detail"
    ],
    "validation_steps": [...]
  }
}
```

---

### 2. **Execution Modes**

#### **Mode 1: Simulation (Current)**

**Behavior:**
- Logs all commands to console/database
- Does NOT connect to devices
- Does NOT execute commands
- Safe for testing and validation

**Output:**
```
[SIMULATION] Would execute on device 10.139.38.188:
  Command 1: show port 1:55 information detail
  Command 2: show port 2:22 information detail
Status: SIMULATED
```

---

#### **Mode 2: Assisted (Planned)**

**Behavior:**
- Low-risk commands auto-execute (show, display)
- High-risk commands require approval
- Human-in-loop for configuration changes

**Approval Workflow:**
- Slack notification with approve/reject buttons
- Email alert with remediation plan
- Web UI for review

---

#### **Mode 3: Autonomous (Future)**

**Behavior:**
- Auto-execute all validated commands
- Automatic rollback on failure
- Continuous learning from outcomes

**Safety Requirements:**
- Confidence score >0.85
- Command validation passed
- Rollback plan defined
- Not off-hours (configurable)

---

### 3. **Remediation Record Storage**

#### **PostgreSQL Table: remediation_actions**

**Schema:**
```sql
CREATE TABLE remediation_actions (
    action_id SERIAL PRIMARY KEY,
    incident_number INTEGER REFERENCES incidents(incident_number),
    device_id VARCHAR(100),
    command TEXT,
    execution_mode VARCHAR(50),
    status VARCHAR(50),
    output TEXT,
    error_message TEXT,
    executed_at TIMESTAMP,
    executed_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Example Record (Simulation):**
```sql
INSERT INTO remediation_actions (
    incident_number, device_id, command, execution_mode, status
)
VALUES (
    20024,
    '10.139.38.188',
    'show port 1:55 information detail',
    'simulation',
    'SIMULATED'
);
```

---

### 4. **Safety Framework (Future Implementation)**

**Layer 1: Pre-Execution Validation**
- Verify command in whitelist
- Check device accessibility (ping test)
- Validate current configuration snapshot exists

**Layer 2: Execution Controls**
- Time windows (business hours only)
- Device role checks (no core devices during peak)
- Concurrent execution limits (1 device at a time)

**Layer 3: Post-Execution Validation**
- Verify expected outcome (port status = UP)
- Check for unintended side effects
- Automatic rollback if validation fails

**Layer 4: Audit Trail**
- All actions logged to database
- Grafana dashboards show execution history
- Searchable audit logs for compliance

---

## Dependencies

### Upstream
- **Kafka (incidents-diagnosed topic):** Diagnosed incidents from LLM

### Downstream
- **PostgreSQL (remediation_actions table):** Action audit trail
- **Network Devices:** SSH/NETCONF (future implementation)
- **Notification Systems:** Slack, Email (future)

---

## Data Flow (Current - Simulation Mode)

```
Kafka (incidents-diagnosed) → Consumer
                                 ↓
                        Extract Commands
                                 ↓
                        Log to Console
                                 ↓
                PostgreSQL (remediation_actions)
                        [status=SIMULATED]
```

## Data Flow (Future - Autonomous Mode)

```
Kafka (incidents-diagnosed) → Consumer
                                 ↓
                        Safety Validation
                                 ↓
                   [Confidence >0.85?]
                        ↓ YES
              Device Connector (SSH/NETCONF)
                        ↓
                Execute Commands
                        ↓
              Validate Outcome
                        ↓
        PostgreSQL (remediation_actions)
              [status=EXECUTED/FAILED]
```

---

## Performance Characteristics

### Current (Simulation)
- **Throughput:** 100+ incidents/second (logging only)
- **Latency:** <50ms per incident
- **Resource Usage:** Minimal

### Future (Autonomous)
- **Throughput:** 5-10 devices/minute (SSH overhead)
- **Latency:** 5-30 seconds per device (SSH connection + command execution)
- **Resource Usage:** Higher (SSH sessions, state management)

---

## Monitoring & Health

### Logs
```bash
docker logs smart-noc-remediation-agent --tail 100
```

**Normal Output (Simulation):**
```
[INFO] Kafka consumer started: incidents-diagnosed
[INFO] Processing incident 20024 (device=10.139.38.188)
[SIMULATION] Would execute commands:
[SIMULATION]   1. show port 1:55 information detail
[SIMULATION]   2. show port 2:22 information detail
[INFO] Logged 2 remediation actions to database
```

---

## Future Enhancements

### Device Connector Service
- **Technology:** Netmiko (multi-vendor SSH library)
- **Vendors:** Extreme EXOS/VOSS, Cisco IOS, Juniper JunOS
- **Features:** Connection pooling, timeout handling, error recovery

### Approval Workflow
- **UI:** Web dashboard for command review
- **Notifications:** Slack, Email, PagerDuty
- **SLA:** Auto-approve after 15 minutes if no response

### Rollback Manager
- **Pre-Execution:** Snapshot current config
- **Post-Failure:** Automatic rollback to snapshot
- **Validation:** Verify config matches pre-change state

---

## Related Documentation

- [LLM Diagnosis Service](05-llm-diagnosis.md)
- [PostgreSQL Schema](08-postgres.md)
- [Complete Architecture](../02-architecture/COMPLETE_ARCHITECTURE.md)
- [NEXT_STEPS.md](../../NEXT_STEPS.md) - Roadmap for autonomous features
