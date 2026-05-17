# Autonomous Remediation Agent

LangGraph-based autonomous network remediation service that diagnoses and fixes network incidents without human intervention.

## 🎯 Features

- **Multi-Step Workflow**: Intelligent troubleshooting process (assess → investigate → plan → execute → verify)
- **Adaptive Decision Making**: Routes based on confidence, complexity, and results
- **Safety Guards**: Escalates high-severity or low-confidence incidents
- **Learning Loop**: Documents resolutions for future improvement
- **Vendor Agnostic**: Device connector abstraction (currently simulated, ready for real SSH/NETCONF)

## 🏗️ Architecture

```
Kafka (incident-diagnoses) 
    → Remediation Agent (LangGraph Workflow)
        → Network Tools (simulate device operations)
        → LLM (decision making)
    → Kafka (incident-remediations) + PostgreSQL (execution history)
```

### Workflow Phases

1. **Assessment**: Determine complexity (simple/complex/escalate)
2. **Investigation**: Gather diagnostic data if needed
3. **Planning**: Create remediation plan
4. **Execution**: Execute actions step-by-step
5. **Verification**: Check if fixes worked
6. **Rollback**: Undo changes if things got worse (optional)
7. **Documentation**: Record lessons learned

## 🚀 Quick Start

### Test Locally (Without Docker)

```bash
cd services/remediation-agent

# Install dependencies
pip install -r requirements.txt

# Set API key
export GROQ_API_KEY='your-groq-api-key'

# Run tests
python test_workflow.py
```

### Run in Docker

```bash
# From project root
docker compose up -d remediation-agent

# View logs
docker compose logs -f remediation-agent

# Check statistics
docker compose exec postgres psql -U noc_admin -d smart_noc -c "SELECT * FROM remediation_stats;"
```

## 📊 Database Schema

The service creates a `remediation_executions` table:

```sql
-- Apply schema
docker compose exec postgres psql -U noc_admin -d smart_noc < services/remediation-agent/schema.sql
```

## ⚙️ Configuration

Environment variables (set in `.env` or `docker-compose.yml`):

```bash
# LLM
GROQ_API_KEY=your-key-here
LLM_MODEL=llama-3.3-70b-versatile

# Execution
SIMULATION_MODE=true                    # Set false for real devices
ENABLE_AUTO_EXECUTION=true             # Set false to require approval
REQUIRE_APPROVAL_ABOVE_SEVERITY=HIGH   # HIGH, CRITICAL

# Kafka
KAFKA_CONSUME_TOPIC=incidents-diagnosed
KAFKA_PRODUCE_TOPIC=incident-remediations

# Safety
MAX_RETRY_ATTEMPTS=3
MAX_EXECUTIONS_PER_HOUR=100
```

## 🧪 Testing

The test suite validates three scenarios:

1. **Simple Interface Issue**: Should auto-remediate successfully
2. **Low Confidence**: Should escalate to human
3. **BGP Incident**: Should handle complex protocol issues

```bash
python test_workflow.py
```

Expected output:
```
✅ PASS: Simple Interface Issue
✅ PASS: Low Confidence Escalation  
✅ PASS: BGP Incident
Result: 3/3 tests passed
```

## 📈 Monitoring

### Check Remediation Statistics

```sql
-- Overall stats
SELECT * FROM remediation_stats ORDER BY date DESC LIMIT 7;

-- Success rate
SELECT 
    ROUND(100.0 * SUM(CASE WHEN success THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate_percent,
    AVG(resolution_time_seconds) as avg_resolution_time
FROM remediation_executions;

-- Recent executions
SELECT 
    incident_number,
    success,
    actions_taken,
    resolution_time_seconds,
    final_phase,
    executed_at
FROM remediation_executions
ORDER BY executed_at DESC
LIMIT 10;
```

### Kafka Topics

```bash
# Monitor diagnosed incidents (input)
docker compose exec kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic incidents-diagnosed

# Monitor remediation results (output)
docker compose exec kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic incident-remediations
```

## 🔧 Extending

### Add Real Device Connectors

Replace simulated tools in `tools.py` with real SSH/NETCONF:

```python
# tools.py
import netmiko

class NetworkTools:
    def __init__(self, simulation_mode: bool = False):
        self.simulation_mode = simulation_mode
        if not simulation_mode:
            self.connections = {}  # Device connection pool
    
    def show_interface_status(self, device: str, interface: str):
        if self.simulation_mode:
            # ... existing simulation code
        else:
            # Real SSH connection
            conn = self._get_connection(device)
            output = conn.send_command(f"show interface {interface}")
            return self._parse_interface_output(output)
```

### Add New Incident Types

Update `_create_remediation_plan()` in `workflow.py`:

```python
def _create_remediation_plan(self, state: RemediationState):
    if 'DNS' in state['incident_type']:
        # Add DNS-specific remediation
        state['remediation_plan'] = [...]
```

## 🐛 Troubleshooting

### Service Not Starting

```bash
# Check logs
docker compose logs remediation-agent

# Common issues:
# 1. GROQ_API_KEY not set
# 2. Kafka not ready (wait for health check)
# 3. Database connection failed
```

### Incidents Not Processing

```bash
# Check if messages are in topic
docker compose exec kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic incidents-diagnosed \
  --from-beginning

# Check consumer group lag
docker compose exec kafka /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --describe \
  --group remediation-agent-group
```

## 📝 Development

### Run in Development Mode

```python
# test_local.py
from workflow import RemediationAgent

agent = RemediationAgent(
    groq_api_key='your-key',
    simulation_mode=True
)

result = agent.remediate(incident, diagnosis)
print(result)
```

### Debug Workflow

Set log level to DEBUG:

```bash
export LOG_LEVEL=DEBUG
python test_workflow.py
```

## 🎓 Next Steps

1. **Week 3**: Test with simulated incidents
2. **Week 4**: Add real device connectors (SSH/NETCONF)
3. **Week 5**: Implement approval workflow for Tier 2
4. **Week 6**: Add proactive monitoring and prevention

## 📚 Resources

- [LangGraph Documentation](https://python.langchain.com/docs/langgraph)
- [Groq API](https://console.groq.com/)
- [Netmiko (SSH)](https://github.com/ktbyers/netmiko)
- [NAPALM (Multi-vendor)](https://napalm.readthedocs.io/)
