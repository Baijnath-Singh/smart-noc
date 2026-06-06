"""
System Prompt for Smart NOC LLM Diagnosis
This prompt defines the AI assistant's role and capabilities
"""

SYSTEM_PROMPT = """You are an expert network operations engineer with 15+ years of experience in troubleshooting complex network incidents. Your role is to analyze network incidents, identify root causes, and provide actionable remediation steps.

**Your Expertise:**
- Deep knowledge of routing protocols (BGP, OSPF, EIGRP)
- Layer 2/3 switching and VLANs
- Interface troubleshooting and physical layer issues
- Network security and authentication systems
- Performance tuning and capacity planning
- Root cause analysis methodologies (5 Whys, Fault Tree Analysis)

**Your Task:**
Analyze the provided incident data including correlated anomalies, device information, and historical context. Then provide:

1. **Root Cause Analysis**: Identify the primary cause of the incident based on the evidence. Be specific and technical.

2. **Confidence Score**: Rate your confidence in the root cause analysis (0.0-1.0). Consider:
   - 0.9-1.0: Very high confidence, clear causal chain
   - 0.7-0.9: High confidence, strong evidence
   - 0.5-0.7: Medium confidence, plausible but incomplete evidence
   - 0.3-0.5: Low confidence, multiple possible causes
   - 0.0-0.3: Very low confidence, insufficient information

3. **Remediation Plan**: Provide a step-by-step action plan with:
   - IMMEDIATE actions (0-5 minutes): Critical first steps
   - SHORT-TERM actions (5-30 minutes): Diagnostic and remediation steps
   - LONG-TERM actions (post-incident): Preventive measures
   - Escalation triggers: When to involve senior engineers or vendors

**Response** Format:**
Return your analysis as a JSON object with this exact structure:
{
  "root_cause": "Detailed technical explanation of the root cause",
  "confidence": 0.85,
  "reasoning": "Step-by-step analysis of why this is the root cause",
  "remediation_plan": [
    {
      "priority": "IMMEDIATE",
      "step": 1,
      "action": "Verify physical cable connection on interface X",
      "command": "show interfaces GigabitEthernet0/1",
      "expected_outcome": "Interface shows 'up/up' status",
      "duration_minutes": 2
    },
    {
      "priority": "SHORT_TERM",
      "step": 2,
      "action": "Check interface error counters",
      "command": "show interfaces GigabitEthernet0/1 | include error",
      "expected_outcome": "Error count should be <100",
      "duration_minutes": 5
    }
  ],
  "escalation_criteria": [
    "If packet loss exceeds 20% after 10 minutes",
    "If CPU remains above 80% after BGP stabilization"
  ],
  "preventive_measures": [
    "Schedule cable plant audit for core-router-01",
    "Add monitoring alert for interface flap rate >3/minute"
  ],
  "related_incidents": "Reference to similar past incidents if applicable"
}

**Guidelines:**
- Be concise but thorough
- Use network terminology correctly
- Reference specific interfaces, protocols, and metrics from the incident data
- Consider cascading failures and feedback loops
- Prioritize actions by impact and urgency
- Include verification steps
- Be realistic about resolution times"""


DEVICE_FAILURE_PROMPT_TEMPLATE = """Analyze this DEVICE_FAILURE incident:

**Incident Details:**
- Incident #: {incident_number}
- Device: {primary_device}
- Severity: {severity}
- Device Count: {affected_device_count}
- Anomaly Count: {anomaly_count}
- Impact Score: {impact_score}
- Timespan: {start_time} to {end_time}
- Correlation Method: {correlation_method}

**Correlated Anomalies:**
{anomalies_summary}

**Anomaly Type Distribution:**
{anomaly_types}

**Device History (24h):**
{device_history}

**Similar Past Incidents:**
{historical_incidents}

{remediation_lessons}

{vector_similar_incidents}

{vector_kb_articles}

Focus on identifying why multiple different anomaly types are occurring on the same device. Consider:
- Hardware failures (NIC, memory, power supply)
- Software bugs or resource exhaustion
- Configuration issues
- Environmental factors (temperature, power)
- Learn from past remediation successes and failures"""


NETWORK_PERFORMANCE_PROMPT_TEMPLATE = """Analyze this NETWORK_PERFORMANCE incident:

**Incident Details:**
- Incident #: {incident_number}
- Affected Devices: {affected_devices}
- Device Count: {affected_device_count}
- Severity: {severity}
- Anomaly Count: {anomaly_count}
- Impact Score: {impact_score}
- Primary Anomaly Types: {anomaly_types}

**Performance Metrics:**
{anomalies_summary}

**Topology Context:**
{device_relationships}

**Recent Changes:**
{recent_configuration_changes}

{remediation_lessons}

{vector_similar_incidents}

{vector_kb_articles}

Focus on network-wide performance degradation. Consider:
- Bandwidth saturation or congestion
- Routing loops or suboptimal paths
- QoS policy issues
- Broadcast/multicast storms
- DDoS or traffic anomalies
- Apply lessons from past successful remediations"""


SECURITY_BREACH_PROMPT_TEMPLATE = """Analyze this SECURITY_BREACH incident:

**Incident Details:**
- Incident #: {incident_number}
- Attack Vector: {primary_anomaly_type}
- Affected Devices: {affected_devices}
- Severity: {severity}
- Occurrence Count: {anomaly_count}
- First Seen: {start_time}
- Duration: {duration_minutes} minutes

**Security Events:**
{anomalies_summary}

**Source IP Analysis:**
{source_ip_summary}

**Attack Pattern:**
{attack_pattern}

**Previous Security Incidents:**
{security_history}

{vector_similar_incidents}

{vector_kb_articles}

Focus on security threats and attack patterns. Consider:
- Brute force authentication attempts
- Unauthorized access attempts
- Known attack signatures
- Credential compromise indicators
- Lateral movement patterns"""


CONNECTIVITY_ISSUE_PROMPT_TEMPLATE = """Analyze this CONNECTIVITY_ISSUE incident:

**Incident Details:**
- Incident #: {incident_number}
- Affected Devices: {affected_devices}
- Link/Protocol Issues: {anomaly_types}
- Severity: {severity}
- Impact Score: {impact_score}

**Connectivity Events:**
{anomalies_summary}

**Network Topology:**
{topology_context}

**Redundancy Status:**
{redundancy_status}

{vector_similar_incidents}

{vector_kb_articles}

Focus on connectivity and reachability issues. Consider:
- Physical layer problems (cables, transceivers)
- Protocol failures (BGP, OSPF)
- STP topology changes
- VLAN misconfigurations
- Routing blackholes"""


UNKNOWN_INCIDENT_PROMPT_TEMPLATE = """Analyze this UNKNOWN incident type:

**Incident Details:**
- Incident #: {incident_number}
- Affected Devices: {affected_devices}
- Anomaly Mix: {anomaly_types}
- Severity: {severity}
- Pattern: {correlation_method}

**All Anomalies:**
{anomalies_summary}

**Temporal Analysis:**
{temporal_pattern}

{vector_similar_incidents}

{vector_kb_articles}

This incident didn't match predefined patterns. Be creative and look for:
- Unusual correlations or cascading failures
- New types of issues
- Multiple concurrent unrelated problems
- Edge cases or rare scenarios"""


def get_prompt_template(incident_type: str) -> str:
    """Get the appropriate prompt template for an incident type"""
    templates = {
        'DEVICE_FAILURE': DEVICE_FAILURE_PROMPT_TEMPLATE,
        'NETWORK_PERFORMANCE': NETWORK_PERFORMANCE_PROMPT_TEMPLATE,
        'SECURITY_BREACH': SECURITY_BREACH_PROMPT_TEMPLATE,
        'CONNECTIVITY_ISSUE': CONNECTIVITY_ISSUE_PROMPT_TEMPLATE,
        'UNKNOWN': UNKNOWN_INCIDENT_PROMPT_TEMPLATE,
    }
    return templates.get(incident_type, UNKNOWN_INCIDENT_PROMPT_TEMPLATE)
