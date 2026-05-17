# Smart NOC - Complete Architecture

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                      NETWORK DEVICES LAYER                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │ Routers  │  │ Switches │  │Firewalls │  │  Other   │           │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘           │
└───────┼─────────────┼─────────────┼─────────────┼───────────────────┘
        │ Syslog      │ SNMP        │             │
        └─────────────┴─────────────┴─────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    INGESTION LAYER (Phase 1)                         │
│                                                                       │
│  ┌────────────────┐         ┌──────────────────┐                   │
│  │  Fluent Bit    │────────▶│  Apache Kafka    │                   │
│  │  (Collector)   │         │  (Message Broker)│                   │
│  └────────────────┘         └─────────┬────────┘                   │
│                                        │                             │
│                              Topics:   │                             │
│                              • network-logs                          │
│                              • network-logs-parsed                   │
│                              • network-anomalies                     │
│                              • network-alerts                        │
└────────────────────────────────────────┼───────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PARSING LAYER (Phase 1)                           │
│                                                                       │
│  ┌─────────────────────────────────────────┐                        │
│  │         Logstash / Apache Flink         │                        │
│  │                                          │                        │
│  │  • Parse syslog format                  │                        │
│  │  • Extract fields (device, severity)    │                        │
│  │  • Enrich with metadata                 │                        │
│  │  • Structure into JSON                  │                        │
│  └───────────────────┬──────────────────────┘                        │
└────────────────────────┼────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   AGENT LAYER (Phase 2-5)                            │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────┐     │
│  │  AGENT 1: ANOMALY DETECTION (Phase 2)                      │     │
│  │  ┌──────────┐  ┌──────────┐  ┌────────────┐              │     │
│  │  │Rule-Based│  │Statistical│  │ ML (Isolation│             │     │
│  │  │ Engine   │  │ Detection │  │   Forest)  │              │     │
│  │  └──────────┘  └──────────┘  └────────────┘              │     │
│  │  Output: Anomaly events                                    │     │
│  └──────────────────────┬─────────────────────────────────────┘     │
│                         │                                            │
│                         ▼                                            │
│  ┌───────────────────────────────────────────────────────────┐     │
│  │  AGENT 2: CORRELATION ENGINE (Phase 3)                     │     │
│  │  ┌──────────┐  ┌──────────┐  ┌────────────┐              │     │
│  │  │  Time    │  │ Device   │  │  Event     │              │     │
│  │  │Correlation│  │ Topology │  │ Patterns   │              │     │
│  │  └──────────┘  └──────────┘  └────────────┘              │     │
│  │  • Group related anomalies                                 │     │
│  │  • Build incident timeline                                 │     │
│  │  • Identify root cause candidate                          │     │
│  │  Output: Incident with related events                      │     │
│  └──────────────────────┬─────────────────────────────────────┘     │
│                         │                                            │
│                         ▼                                            │
│  ┌───────────────────────────────────────────────────────────┐     │
│  │  AGENT 3: DIAGNOSIS (Phase 4)                              │     │
│  │  ┌──────────────────────────────────────┐                 │     │
│  │  │         LLM (Ollama/GPT-4)           │                 │     │
│  │  │                                       │                 │     │
│  │  │  Inputs:                             │                 │     │
│  │  │  • Incident details                  │                 │     │
│  │  │  • Device context                    │                 │     │
│  │  │  • Similar past incidents (from DB)  │                 │     │
│  │  │                                       │                 │     │
│  │  │  Process:                            │                 │     │
│  │  │  1. Retrieve similar incidents       │                 │     │
│  │  │  2. Build context prompt             │                 │     │
│  │  │  3. LLM reasoning                    │                 │     │
│  │  │  4. Generate diagnosis               │                 │     │
│  │  └──────────────────────────────────────┘                 │     │
│  │  Output: Root cause + confidence + fix suggestion         │     │
│  └──────────────────────┬─────────────────────────────────────┘     │
│                         │                                            │
│                         ▼                                            │
│  ┌───────────────────────────────────────────────────────────┐     │
│  │  AGENT 4: DECISION ENGINE (Phase 5)                        │     │
│  │  ┌────────────────────────────────┐                       │     │
│  │  │  Open Policy Agent (OPA)        │                       │     │
│  │  │                                 │                       │     │
│  │  │  Policies:                     │                       │     │
│  │  │  • Can we auto-fix?            │                       │     │
│  │  │  • Is device critical?         │                       │     │
│  │  │  • Is it business hours?       │                       │     │
│  │  │  • Requires approval?          │                       │     │
│  │  └────────────────────────────────┘                       │     │
│  │  Output: Decision (AUTO/MANUAL/BLOCKED)                    │     │
│  └──────────────────────┬─────────────────────────────────────┘     │
│                         │                                            │
│                         ▼                                            │
│  ┌───────────────────────────────────────────────────────────┐     │
│  │  AGENT 5: REMEDIATION (Phase 5)                            │     │
│  │  ┌────────────────────────────────┐                       │     │
│  │  │         Ansible Engine          │                       │     │
│  │  │                                 │                       │     │
│  │  │  Actions:                      │                       │     │
│  │  │  • Restart interface           │                       │     │
│  │  │  • Clear ARP cache             │                       │     │
│  │  │  • Rollback configuration      │                       │     │
│  │  │  • Restart BGP session         │                       │     │
│  │  │  • Adjust MTU                  │                       │     │
│  │  └────────────────────────────────┘                       │     │
│  │  Output: Remediation result                                │     │
│  └──────────────────────┬─────────────────────────────────────┘     │
│                         │                                            │
│                         ▼                                            │
│  ┌───────────────────────────────────────────────────────────┐     │
│  │  AGENT 6: VALIDATION (Phase 5)                             │     │
│  │  • Check logs for errors                                   │     │
│  │  • Verify metrics normalized                               │     │
│  │  • Confirm no new anomalies                                │     │
│  │  Output: Success/Failure + evidence                         │     │
│  └─────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│               ORCHESTRATION LAYER (Phase 6)                          │
│                                                                       │
│  ┌─────────────────────────────────────────┐                        │
│  │         Temporal Workflows               │                        │
│  │                                          │                        │
│  │  Workflow: Handle Network Incident      │                        │
│  │  1. Receive anomaly                     │                        │
│  │  2. Correlate events → create incident  │                        │
│  │  3. Diagnose with LLM                   │                        │
│  │  4. Check policy                        │                        │
│  │  5. Execute remediation                 │                        │
│  │  6. Validate fix                        │                        │
│  │  7. Store learning                      │                        │
│  │                                          │                        │
│  │  Features:                              │                        │
│  │  • Automatic retries                    │                        │
│  │  • State persistence                    │                        │
│  │  • Error handling                       │                        │
│  │  • Human-in-the-loop                   │                        │
│  └─────────────────────────────────────────┘                        │
└─────────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    STORAGE LAYER                                     │
│                                                                       │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐                │
│  │Elasticsearch│  │   Neo4j      │  │  ChromaDB  │                │
│  │(Logs)       │  │  (Topology)  │  │  (Vector)  │                │
│  └─────────────┘  └──────────────┘  └────────────┘                │
│                                                                       │
│  Stores:                                                             │
│  • All parsed logs (time-series)                                    │
│  • Device topology (graph)                                          │
│  • Past incidents + solutions (embeddings)                          │
│  • Metrics and KPIs                                                 │
└─────────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    VISUALIZATION LAYER                               │
│                                                                       │
│  ┌─────────────────────────────────────────┐                        │
│  │              Grafana                     │                        │
│  │                                          │                        │
│  │  Dashboards:                            │                        │
│  │  • Network Overview                     │                        │
│  │  • Anomaly Detection                    │                        │
│  │  • Incident Timeline                    │                        │
│  │  • Remediation Status                   │                        │
│  │  • System Health                        │                        │
│  └─────────────────────────────────────────┘                        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Data Flow Example

**Scenario: Interface Flapping on Core Router**

```
1. Device Event
   core-router-01: Interface Gi0/1 DOWN

2. Ingestion
   Fluent Bit → Kafka topic: network-logs

3. Parsing
   Logstash:
   {
     "device": "core-router-01",
     "event": "INTERFACE_DOWN",
     "interface": "Gi0/1",
     "timestamp": "2026-04-23T10:30:00Z"
   }

4. Anomaly Detection
   Detector: Same interface down 5 times in 60s
   → ANOMALY: INTERFACE_FLAPPING

5. Correlation
   Finds related:
   • BGP session down (same router)
   • Packet loss (connected devices)
   → Creates INCIDENT-12345

6. Diagnosis
   LLM checks:
   • Past similar incidents
   • Device configuration
   → Root cause: "Faulty cable (90% confidence)"

7. Decision
   OPA Policy:
   • Device: Critical ✗
   • Time: Business hours ✓
   • Auto-fix available: Yes ✓
   → Decision: MANUAL_APPROVAL_REQUIRED

8. Wait for approval...

9. Remediation (after approval)
   Ansible:
   • Shutdown interface
   • Check cable status
   • Bring up backup interface
   → Success

10. Validation
    Check logs for 5 minutes:
    • No more flapping ✓
    • BGP restored ✓
    → Incident RESOLVED

11. Learning
    Store in vector DB:
    "Interface flapping + cable issue → backup switchover"
```

---

## 🔑 Key Design Principles

### 1. **Decoupling**
- Each component independent
- Kafka as message backbone
- Can scale/replace components individually

### 2. **Reliability**
- Kafka durability (log retention)
- Temporal handles retries
- State persisted throughout

### 3. **Observability**
- Every step logged
- Metrics at each layer
- Grafana dashboards

### 4. **Safety**
- Policy engine prevents dangerous actions
- Human approval for critical changes
- Validation after every fix

### 5. **Learning**
- Store all incidents
- Vector similarity search
- Continuously improve

---

## 📈 Scalability

### Laptop (POC)
- 1,000 logs/sec
- 10 devices
- Single instance per component

### Small Production
- 10,000 logs/sec
- 100 devices
- 3 Kafka brokers
- Horizontal scaling

### Large Production
- 100,000+ logs/sec
- 1,000+ devices
- Kafka cluster
- Flink cluster
- Distributed agents

---

## 🔒 Security Considerations

1. **Network Access**
   - SSH key-based auth (Ansible)
   - No passwords in configs

2. **API Security**
   - JWT tokens
   - RBAC policies

3. **Data Privacy**
   - Local LLM (sensitive data stays local)
   - Encrypted at rest

4. **Audit Trail**
   - Every action logged
   - Immutable log store

---

## 💡 Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Kafka over RabbitMQ** | Higher throughput, log replay |
| **Temporal over Airflow** | Event-driven, not cron-based |
| **Ollama over OpenAI** | Privacy, no API costs |
| **OPA over custom code** | Industry standard, maintainable |
| **Elasticsearch over SQL** | Full-text search, time-series optimized |

---

## 🎯 Phase Dependencies

```
Phase 1 (Log Pipeline)
└─▶ Phase 2 (Anomaly Detection)
    └─▶ Phase 3 (Correlation)
        └─▶ Phase 4 (LLM Diagnosis)
            └─▶ Phase 5 (Remediation)
                └─▶ Phase 6 (Orchestration)
```

**Must complete in order** - each phase builds on the previous.

---

## 📚 Further Reading

- [Kafka Architecture](https://kafka.apache.org/documentation/)
- [Temporal Concepts](https://docs.temporal.io/concepts)
- [OPA Policy Language](https://www.openpolicyagent.org/docs/latest/policy-language/)
- [Network Automation with Ansible](https://docs.ansible.com/ansible/latest/network/index.html)
