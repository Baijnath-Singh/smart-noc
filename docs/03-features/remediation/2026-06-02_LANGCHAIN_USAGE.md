# Smart NOC - LangChain & LangGraph Usage

**Version:** 1.0  
**Date:** May 22, 2026  
**Component:** Remediation Agent  
**Location:** `services/remediation-agent/`

---

## Overview

The **Remediation Agent** uses **LangChain** and **LangGraph** to implement an autonomous multi-phase network remediation workflow. Unlike the LLM Diagnosis service (which uses Groq API directly), the remediation agent uses LangChain for structured agent behavior.

**Why LangChain here?**
- **State Machine:** LangGraph provides graph-based workflow orchestration
- **Tool Integration:** LangChain standardizes network tool calling
- **Decision Routing:** Conditional edges based on LLM decisions
- **Retry Logic:** Built-in error handling and backtracking

---

## Architecture

### Component Stack

```
┌─────────────────────────────────────────────────────────┐
│               REMEDIATION AGENT                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐    ┌──────────────┐                 │
│  │   LangGraph  │───▶│ State Graph  │                 │
│  │   (Workflow) │    │  (7 nodes)   │                 │
│  └──────────────┘    └──────────────┘                 │
│         │                    │                         │
│         ▼                    ▼                         │
│  ┌──────────────────────────────────┐                 │
│  │  RemediationState (TypedDict)   │                 │
│  │  - incident_data                │                 │
│  │  - remediation_plan             │                 │
│  │  - action_results               │                 │
│  │  - current_phase                │                 │
│  └──────────────────────────────────┘                 │
│         │                    │                         │
│         ▼                    ▼                         │
│  ┌──────────────┐    ┌──────────────┐                 │
│  │  LangChain   │───▶│   ChatGroq   │                 │
│  │    (LLM)     │    │llama-3.3-70b │                 │
│  └──────────────┘    └──────────────┘                 │
│         │                                              │
│         ▼                                              │
│  ┌──────────────────────────────────┐                 │
│  │      NetworkTools                │                 │
│  │  - show_interface_status()      │                 │
│  │  - reload_interface()            │                 │
│  │  - restart_service()             │                 │
│  │  - clear_counters()              │                 │
│  │  (10+ tools)                     │                 │
│  └──────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────┘
```

---

## LangGraph State Machine

### Workflow Phases (7 Nodes)

```python
# workflow.py
graph = StateGraph(RemediationState)

# Node definitions
graph.add_node("assess_complexity", self._assess_complexity)
graph.add_node("create_plan", self._create_remediation_plan)
graph.add_node("investigate", self._investigate_further)
graph.add_node("execute_action", self._execute_remediation_action)
graph.add_node("verify_fix", self._verify_remediation)
graph.add_node("rollback", self._rollback_changes)
graph.add_node("document", self._document_resolution)
graph.add_node("escalate", self._escalate_to_human)

graph.set_entry_point("assess_complexity")
```

### Flow Diagram

```
START
  │
  ▼
┌─────────────────┐
│ assess_complexity│ → LLM decides: SIMPLE, COMPLEX, or ESCALATE
└────────┬─────────┘
         │
    ┌────┴─────┬──────────┐
    │          │          │
    ▼          ▼          ▼
SIMPLE     COMPLEX    ESCALATE → END
    │          │
    │    ┌─────┴──────┐
    │    │ investigate │ → Gather more data
    │    └─────┬───────┘
    │          │
    └──────────┴───────┐
                       ▼
              ┌─────────────────┐
              │   create_plan   │ → LLM creates remediation steps
              └────────┬─────────┘
                       │
                       ▼
              ┌─────────────────┐
              │ execute_action  │ → Run one tool
              └────────┬─────────┘
                       │
                  ┌────┴─────┬────────┐
                  │          │        │
                  ▼          ▼        ▼
              CONTINUE   VERIFY   FAILED → escalate → END
              (loop)        │
                            ▼
                   ┌─────────────────┐
                   │   verify_fix    │ → Check if it worked
                   └────────┬─────────┘
                            │
                   ┌────────┴────┬──────────┬──────────┐
                   │             │          │          │
                   ▼             ▼          ▼          ▼
               SUCCESS        RETRY    ROLLBACK   ESCALATE
                   │             │          │          │
                   │             └──────────┤          │
                   │                        │          │
                   ▼                        ▼          ▼
              ┌─────────────────┐   ┌─────────────────┐
              │    document     │   │    escalate     │
              └────────┬─────────┘   └────────┬────────┘
                       │                      │
                       └──────────┬───────────┘
                                  ▼
                                 END
```

---

## LangChain Components

### 1. ChatGroq (LLM Integration)

```python
# workflow.py
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

class RemediationAgent:
    def __init__(self, groq_api_key: str):
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=groq_api_key,
            temperature=0.1,  # Low temp for consistent decisions
            timeout=60.0
        )
```

**Why ChatGroq?**
- Structured interface to Groq API
- Automatic retry handling
- Message history management
- Streaming support (for future use)

### 2. Message Types

LangChain uses structured messages instead of raw strings:

```python
# Example from _assess_complexity
def _assess_complexity(self, state: RemediationState):
    prompt = f"""
    You are an autonomous network operations agent.
    
    Incident Type: {state['incident_type']}
    Diagnosis Confidence: {state['diagnosis']['confidence']}
    
    Can you handle this autonomously?
    Respond: SIMPLE, COMPLEX, or ESCALATE
    """
    
    response = self.llm.invoke([HumanMessage(content=prompt)])
    decision = response.content.strip().upper()
    
    return state  # Updated state
```

**Benefits:**
- Type safety (SystemMessage vs HumanMessage vs AIMessage)
- Conversation history tracking
- Token counting
- Role-based prompting

### 3. State Management (RemediationState)

```python
# state.py
from typing import TypedDict, List, Dict, Any

class RemediationState(TypedDict):
    """State that flows through the LangGraph workflow"""
    
    # Input
    incident_number: str
    incident_id: int
    incident_type: str
    diagnosis: Dict[str, Any]  # From LLM Diagnosis service
    
    # Workflow state
    current_phase: str  # planning, investigation, remediation, verification
    confidence: float
    
    # Planning
    remediation_plan: List[Dict[str, Any]]  # List of actions
    current_action: int  # Index of current action
    
    # Execution
    action_results: List[ActionResult]
    evidence: List[Dict[str, Any]]  # From investigation
    
    # Results
    success: bool
    resolution_time_seconds: int
    lessons_learned: str
    
    # Error handling
    errors: List[str]
    warnings: List[str]
```

**Why TypedDict?**
- Type hints for IDE autocomplete
- Validation at runtime
- Clear contract between nodes
- JSON serializable

---

## Tool Integration

### NetworkTools Class

```python
# tools.py
class NetworkTools:
    """Network operations tools for remediation actions"""
    
    def __init__(self, simulation_mode: bool = True):
        self.simulation_mode = simulation_mode
        logger.info(f"NetworkTools initialized (simulation: {simulation_mode})")
    
    def show_interface_status(self, device: str, interface: str) -> Dict:
        """Get interface status"""
        if self.simulation_mode:
            return {
                'device': device,
                'interface': interface,
                'status': 'up',
                'protocol': 'up',
                'errors': 42,
                'crc_errors': 12,
                'collisions': 0
            }
        else:
            # Real implementation using Netmiko/NAPALM
            return self._execute_on_device(device, f"show interface {interface}")
    
    def reload_interface(self, device: str, interface: str) -> Dict:
        """Reload interface (shut/no shut)"""
        commands = [
            f"interface {interface}",
            "shutdown",
            "no shutdown"
        ]
        return self._execute_commands(device, commands)
    
    def clear_interface_counters(self, device: str, interface: str) -> Dict:
        """Clear interface error counters"""
        return self._execute_commands(device, [f"clear counters {interface}"])
    
    def restart_service(self, device: str, service: str) -> Dict:
        """Restart a network service (BGP, OSPF, etc)"""
        commands = [
            f"clear ip {service} *" if service == 'bgp' else f"restart {service}"
        ]
        return self._execute_commands(device, commands)
```

### Tool Descriptions (For LLM)

```python
# tools.py
TOOL_DESCRIPTIONS = {
    'show_interface_status': {
        'description': 'Get detailed interface status including errors, state, and counters',
        'parameters': ['device', 'interface'],
        'safe': True,
        'execution_time': '2s'
    },
    'reload_interface': {
        'description': 'Reload interface (shutdown + no shutdown) to clear transient errors',
        'parameters': ['device', 'interface'],
        'safe': True,  # Safe if not single point of failure
        'execution_time': '10s',
        'caution': 'Will cause brief traffic interruption'
    },
    'clear_interface_counters': {
        'description': 'Clear interface error counters to reset baseline',
        'parameters': ['device', 'interface'],
        'safe': True,
        'execution_time': '1s'
    },
    'restart_service': {
        'description': 'Restart network service (BGP, OSPF, etc)',
        'parameters': ['device', 'service'],
        'safe': False,  # Can cause routing disruption
        'execution_time': '30s',
        'caution': 'May cause temporary routing instability'
    }
}
```

---

## Conditional Routing

### LangGraph Decision Points

```python
# workflow.py
def _route_after_assessment(self, state: RemediationState) -> str:
    """Route based on complexity assessment"""
    if 'ESCALATE' in state.get('errors', []):
        return "escalate"
    elif state.get('confidence', 0) > 0.7:
        return "simple"
    else:
        return "complex"

def _route_after_execution(self, state: RemediationState) -> str:
    """Route based on execution result"""
    if state['current_action'] < len(state['remediation_plan']) - 1:
        return "continue"  # More actions to execute
    elif state.get('action_failed', False):
        return "failed"
    else:
        return "verify"  # Done, verify it worked

def _route_after_verification(self, state: RemediationState) -> str:
    """Route based on verification result"""
    result = state.get('verification_result', 'unknown')
    
    if result == 'success':
        return "document"
    elif result == 'retry':
        return "create_plan"  # Try different approach
    elif result == 'rollback':
        return "rollback"
    else:
        return "escalate"
```

**Benefits of Conditional Edges:**
- Dynamic workflow based on results
- Automatic retry logic
- Graceful failure handling
- No complex if/else chains

---

## Example: Full Execution Flow

### Input (from Kafka)

```json
{
  "incident_id": 1,
  "incident_number": "INC-20260522-001",
  "incident_type": "INTERFACE_FLAPPING",
  "diagnosis": {
    "root_cause": "Physical layer issue (transient errors on fiber)",
    "confidence": 0.85,
    "primary_device": "core-router-01",
    "remediation_plan": [
      "Clear interface counters",
      "Reload interface",
      "Monitor for 5 minutes"
    ]
  }
}
```

### Execution Trace

```
[PHASE 1] Assessing complexity for incident #INC-20260522-001
  → LLM decision: SIMPLE (confidence 0.85, interface issue)
  → Route: assess_complexity → create_plan

[PHASE 2] Skipped investigation (simple incident)

[PHASE 3] Creating remediation plan
  → LLM generates 3-step plan:
    1. clear_interface_counters (GigabitEthernet0/1)
    2. reload_interface (GigabitEthernet0/1)
    3. verify_interface_health
  → Route: create_plan → execute_action

[PHASE 4] Executing step 1: clear_interface_counters
  → NetworkTool: clear_interface_counters(core-router-01, Gi0/1)
  → Result: SUCCESS (1.2s)
  → Route: execute_action → execute_action (continue)

[PHASE 4] Executing step 2: reload_interface
  → NetworkTool: reload_interface(core-router-01, Gi0/1)
  → Result: SUCCESS (8.5s)
  → Route: execute_action → verify_fix

[PHASE 5] Verifying remediation
  → Check: Interface status = up/up ✓
  → Check: Error rate = 0.02% ✓
  → Check: No flaps in 5 min ✓
  → Verification: SUCCESS
  → Route: verify_fix → document

[PHASE 6] Documenting resolution
  → Total time: 14.2s
  → Actions: 2 successful, 0 failed
  → Lesson: "For INTERFACE_FLAPPING, sequence worked: clear_counters → reload_interface"
  → Saved to database and ChromaDB
  → Route: document → END

Final result: SUCCESS ✓
```

---

## Key Advantages of LangChain/LangGraph

### 1. **Separation of Concerns**
```python
# Without LangChain (hard to maintain)
def remediate(incident):
    if assess(incident) == 'complex':
        if investigate(incident) == 'escalate':
            return escalate()
        plan = create_plan(incident)
    else:
        plan = create_plan(incident)
    
    for action in plan:
        result = execute(action)
        if result.failed:
            rollback()
            return escalate()
    
    if verify():
        document()
        return success()
    else:
        rollback()
        return escalate()

# With LangGraph (clear and testable)
graph.add_node("assess", assess_node)
graph.add_node("investigate", investigate_node)
graph.add_node("plan", plan_node)
graph.add_conditional_edges("assess", route_after_assessment)
# ... etc
```

### 2. **Testability**
```python
# Test individual nodes
def test_assess_complexity():
    state = {'incident_type': 'INTERFACE_DOWN', 'confidence': 0.9}
    result = agent._assess_complexity(state)
    assert result['current_phase'] == 'planning'

# Test routing
def test_routing_logic():
    state = {'confidence': 0.5, 'errors': []}
    route = agent._route_after_assessment(state)
    assert route == 'complex'
```

### 3. **Observability**
```python
# LangGraph provides execution trace
workflow.run(state)
# Outputs:
# assess_complexity → create_plan → execute_action → verify_fix → document

# Can export to visualization
graph.get_graph().draw_mermaid()
```

### 4. **Error Handling**
```python
# Automatic retry on LLM failure
self.llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    max_retries=3,  # Retry 3 times
    timeout=60.0
)

# Workflow continues even if one node fails
# (via error state tracking)
```

---

## Comparison: Why NOT Use LangChain for Diagnosis?

| Feature | LLM Diagnosis | Remediation Agent |
|---------|--------------|-------------------|
| **Workflow** | Single-shot (one LLM call) | Multi-phase state machine |
| **Decisions** | Human reviews diagnosis | Agent makes autonomous decisions |
| **Tools** | No tool calling needed | 10+ network tools |
| **Complexity** | Simple: prompt → response | Complex: branch, retry, rollback |
| **Best Approach** | Direct API call (simpler) | LangChain (better structure) |

**LLM Diagnosis Service** (no LangChain):
```python
# Direct approach works fine
def diagnose(incident):
    context = build_context(incident)
    prompt = create_prompt(context)
    response = groq_client.chat(prompt)  # One API call
    return parse_diagnosis(response)
```

**Remediation Agent** (needs LangChain):
```python
# Complex workflow needs orchestration
def remediate(incident):
    state = {'incident': incident}
    result = workflow.invoke(state)  # LangGraph handles branching
    return result
```

---

## Configuration

### Enabling/Disabling Features

```yaml
# services/remediation-agent/config.yaml
llm:
  provider: groq
  model: llama-3.3-70b-versatile
  temperature: 0.1
  max_retries: 3

workflow:
  simulation_mode: true  # True = don't execute real commands
  require_approval: false  # True = pause before execution
  max_actions_per_incident: 5
  verification_wait_seconds: 60

tools:
  timeout_seconds: 30
  retry_failed_tools: true
  allowed_tools:
    - show_interface_status
    - clear_interface_counters
    - reload_interface
  # Dangerous tools disabled in production
  # - reload_device
  # - apply_configuration
```

---

## Future Enhancements

### 1. **Add Tool Schemas** (LangChain Tool)
```python
from langchain.tools import tool

@tool
def show_interface_status(device: str, interface: str) -> dict:
    """
    Get interface status including errors and state.
    
    Args:
        device: Device hostname (e.g., 'core-router-01')
        interface: Interface name (e.g., 'GigabitEthernet0/1')
    
    Returns:
        Dictionary with status, errors, and counters
    """
    return network_tools.show_interface_status(device, interface)
```

### 2. **Agent with Tools** (Auto tool selection)
```python
from langchain.agents import create_tool_calling_agent

tools = [show_interface_status, reload_interface, clear_counters]
agent = create_tool_calling_agent(llm, tools, prompt)

# LLM automatically decides which tools to use
result = agent.invoke({"incident": incident_data})
```

### 3. **Memory** (Remember past incidents)
```python
from langchain.memory import ConversationBufferMemory

memory = ConversationBufferMemory()
# Agent remembers previous actions in conversation
```

---

## Troubleshooting

### Common Issues

**Problem:** LangGraph workflow stuck in loop
```python
# Check state updates
logger.debug(f"State after node: {state}")

# Add max iterations
graph.set_max_iterations(10)
```

**Problem:** Tool execution fails
```python
# Enable detailed logging
import logging
logging.getLogger("langchain").setLevel(logging.DEBUG)
```

**Problem:** LLM returns unexpected decision
```python
# Validate LLM outputs
response = self.llm.invoke([HumanMessage(content=prompt)])
decision = response.content.strip().upper()

if decision not in ['SIMPLE', 'COMPLEX', 'ESCALATE']:
    logger.error(f"Invalid decision: {decision}")
    decision = 'ESCALATE'  # Safe default
```

---

## Summary

| Aspect | Implementation |
|--------|----------------|
| **Framework** | LangChain + LangGraph |
| **LLM** | ChatGroq (llama-3.3-70b-versatile) |
| **Workflow** | 7-node state machine with conditional routing |
| **Tools** | 10+ network tools (show, clear, reload, restart) |
| **State** | TypedDict with 15+ fields |
| **Routing** | 3 conditional decision points |
| **Safety** | Simulation mode, validation, rollback |

**Key Takeaway:** LangChain/LangGraph provides structured agent behavior for complex multi-step workflows with tool calling and decision branching. Perfect for autonomous remediation, overkill for single-shot diagnosis.

---

**End of Document**
