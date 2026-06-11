# Safety Framework Architecture - Correct Service Placement
**Date:** 2026-06-11  
**Status:** ✅ ARCHITECTURE CORRECTED

## Overview

This document explains the **correct architecture** for the Safety Framework integration, showing clean separation between diagnosis and remediation concerns.

## Architectural Violation (Fixed)

### ❌ BEFORE: Incorrect Architecture

```
┌─────────────────────┐
│  llm-diagnosis      │
├─────────────────────┤
│ ❌ Risk Assessment  │  ← WRONG: Diagnosis service making remediation decisions
│ ❌ Decision Matrix  │
│ ❌ Auto-Execution   │
│ ✅ Diagnosis        │
└──────────┬──────────┘
           │ Kafka
           ▼
┌─────────────────────┐
│  remediation-agent  │
├─────────────────────┤
│ ✅ LangGraph        │
│    Workflow         │
└─────────────────────┘
```

**Problems:**
- llm-diagnosis service contained Safety Framework code
- Diagnosis service was making remediation decisions
- Diagnosis service was even executing remediations
- Violated single responsibility principle
- Mixed diagnosis and remediation concerns

### ✅ AFTER: Correct Architecture

```
┌─────────────────────┐
│  llm-diagnosis      │
├─────────────────────┤
│ ✅ Context Building │
│ ✅ LLM Diagnosis    │
│ ✅ Confidence Cal.  │
│ ✅ Vector Search    │
└──────────┬──────────┘
           │ Kafka: incidents-diagnosed
           │ {incident, diagnosis, confidence}
           ▼
┌─────────────────────────────────────┐
│  remediation-agent                  │
├─────────────────────────────────────┤
│  ┌──────────────────────────────┐  │
│  │ 🛡️  SAFETY FRAMEWORK         │  │
│  ├──────────────────────────────┤  │
│  │ • Risk Assessment (4 factors)│  │
│  │ • Decision Matrix            │  │
│  │ • Rollback Manager           │  │
│  │ • Approval Workflow          │  │
│  └───────────┬──────────────────┘  │
│              │ safe_to_proceed?     │
│              ▼                      │
│  ┌──────────────────────────────┐  │
│  │ 🤖 LANGGRAPH WORKFLOW        │  │
│  ├──────────────────────────────┤  │
│  │ Phase 1: Assess Complexity   │  │
│  │ Phase 2: Investigate         │  │
│  │ Phase 3: Create Plan         │  │
│  │ Phase 4: Execute Actions     │  │
│  │ Phase 5: Verify Fix          │  │
│  │ Phase 6: Rollback (if needed)│  │
│  │ Phase 7: Document            │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

**Benefits:**
- Clean separation of concerns
- llm-diagnosis: ONLY diagnoses (what/why)
- remediation-agent: ONLY remediates (how/when)
- Safety Framework as gatekeeper before workflow
- Single service owns all remediation logic

## Complete Data Flow

### Step-by-Step Flow

```mermaid
sequenceDiagram
    participant DB as PostgreSQL
    participant LLM as llm-diagnosis
    participant Kafka
    participant RA as remediation-agent
    participant SF as Safety Framework
    participant LG as LangGraph Workflow
    
    Note over DB: Incident #10000 created
    LLM->>DB: Fetch incident + anomalies
    LLM->>LLM: Build context with vectors
    LLM->>LLM: Generate diagnosis
    LLM->>LLM: Calibrate confidence (3 layers)
    LLM->>DB: Save diagnosis to incidents table
    LLM->>Kafka: Publish to 'incidents-diagnosed'
    
    Note over Kafka: Message contains:<br/>incident + diagnosis + confidence
    
    RA->>Kafka: Consume message
    RA->>SF: assess_safety(incident, diagnosis, confidence)
    
    Note over SF: SAFETY FRAMEWORK EVALUATION
    
    SF->>SF: Risk Assessment<br/>• Device Criticality (40%)<br/>• Blast Radius (30%)<br/>• Time Sensitivity (20%)<br/>• Change Complexity (10%)
    SF->>DB: Save risk_assessment
    SF->>SF: Decision Matrix<br/>Risk + Confidence → Decision
    SF->>DB: Log decision to autonomous_decision_log
    SF-->>RA: {risk_level, decision, safe_to_proceed}
    
    alt decision = manual_only
        RA->>RA: Escalate to NOC
        Note over RA: STOP - Manual intervention required
    else decision = require_approval
        RA->>DB: Create approval request
        Note over RA: STOP - Awaiting approval
    else decision = execute / execute_notify
        Note over RA: ✅ Proceed with remediation
        
        RA->>LG: remediate(incident, diagnosis)
        
        Note over LG: LANGGRAPH WORKFLOW
        
        LG->>LG: Phase 1: Assess Complexity
        LG->>LG: Phase 2: Investigate (if needed)
        LG->>LG: Phase 3: Create Plan
        
        loop For each remediation step
            LG->>LG: Phase 4: Execute Action
        end
        
        LG->>LG: Phase 5: Verify Fix
        
        alt Verification Failed
            LG->>LG: Phase 6: Rollback Changes
            LG->>LG: Phase 8: Escalate
        else Verification Passed
            LG->>LG: Phase 7: Document Resolution
        end
        
        LG-->>RA: {success, resolution_time, actions_taken}
        
        RA->>DB: Save remediation_executions
        RA->>DB: Update incident status
        RA->>Kafka: Publish result to 'incident-remediations'
    end
```

## Code Integration Points

### 1. remediation-agent/main.py (Entry Point)

```python
def __init__(self):
    # Initialize LangGraph workflow
    self.agent = RemediationAgent(...)
    
    # Initialize Safety Framework
    database_url = f"postgresql://{user}:{pass}@{host}:{port}/{db}"
    self.safety = SafetyIntegration(database_url)  # ← Safety Framework wrapper
    logger.info("✅ Safety Framework integrated")

def process_diagnosis(self, message: dict) -> bool:
    """Process diagnosed incident from Kafka"""
    
    # 1. Extract incident and diagnosis
    incident = message.get('incident', {})
    diagnosis = message.get('diagnosis', {})
    
    # 2. ✅ SAFETY FRAMEWORK - Gatekeeper before remediation
    safety_result = self._assess_safety(incident, diagnosis)
    
    logger.info(
        f"🛡️  Safety Assessment: Risk={safety_result['risk_level']} "
        f"({safety_result['risk_score']:.2f}), "
        f"Decision={safety_result['decision']}"
    )
    
    # 3. Handle decision
    if safety_result['must_escalate']:
        logger.warning("🚫 Safety Framework: Manual intervention required")
        return True  # Don't proceed
    
    if safety_result['requires_approval']:
        logger.warning("⏸️  Safety Framework: Approval required")
        self.safety.request_approval(...)
        return True  # Wait for approval
    
    if not safety_result['safe_to_proceed']:
        logger.warning("⚠️  Safety check failed")
        return True  # Don't proceed
    
    # 4. ✅ SAFE TO PROCEED - Execute LangGraph workflow
    logger.success("✅ Safety checks passed, proceeding with remediation")
    result = self.agent.remediate(incident, diagnosis)  # ← LangGraph executes
    
    return True
```

### 2. remediation-agent/safety_integration.py (Wrapper)

```python
class SafetyIntegration:
    """Integrates all Safety Framework components"""
    
    def __init__(self, database_url: str):
        self.risk_assessor = RiskAssessor(engine)
        self.autonomous_executor = AutonomousExecutor(engine)
        self.rollback_manager = RollbackManager(engine)
        self.approval_workflow = ApprovalWorkflow(engine)
    
    def assess_safety(self, incident, diagnosis, calibrated_confidence) -> dict:
        """Complete safety assessment"""
        
        # Step 1: Risk assessment
        risk_level, risk_score, factors = self.risk_assessor.assess_risk(
            incident, diagnosis
        )
        self.risk_assessor.save_risk_assessment(...)
        
        # Step 2: Decision matrix
        decision, reasoning, metadata = self.autonomous_executor.decide_action(
            incident=incident,
            diagnosis=diagnosis_with_confidence,
            risk_assessment={'risk_level': risk_level, 'risk_score': risk_score}
        )
        
        # Step 3: Return gatekeeper result
        return {
            'risk_level': risk_level,
            'risk_score': risk_score,
            'decision': decision,
            'safe_to_proceed': decision in ['execute', 'execute_notify'],
            'requires_approval': decision == 'require_approval',
            'must_escalate': decision == 'manual_only'
        }
```

### 3. remediation-agent/workflow.py (LangGraph)

```python
class RemediationAgent:
    """LangGraph workflow for autonomous remediation"""
    
    def _build_workflow(self) -> StateGraph:
        graph = StateGraph(RemediationState)
        
        # Add workflow phases
        graph.add_node("assess_complexity", self._assess_complexity)
        graph.add_node("create_plan", self._create_remediation_plan)
        graph.add_node("execute_action", self._execute_remediation_action)
        graph.add_node("verify_fix", self._verify_remediation)
        graph.add_node("rollback", self._rollback_changes)
        graph.add_node("document", self._document_resolution)
        
        # Define flow
        graph.set_entry_point("assess_complexity")
        graph.add_edge("create_plan", "execute_action")
        graph.add_conditional_edges("execute_action", ...)
        
        return graph.compile()
    
    def remediate(self, incident, diagnosis):
        """Execute workflow - Only called if Safety Framework approved"""
        state = RemediationState(
            incident_number=incident['incident_number'],
            incident_type=incident['incident_type'],
            diagnosis=diagnosis,
            ...
        )
        
        # Run state machine
        result = self.workflow.invoke(state)
        return result
```

## Files Removed from llm-diagnosis

These files were **incorrectly** in llm-diagnosis and have been **removed**:

- ❌ `services/llm-diagnosis/risk_assessor.py`
- ❌ `services/llm-diagnosis/autonomous_executor.py`
- ❌ `services/llm-diagnosis/rollback_manager.py`
- ❌ `services/llm-diagnosis/approval_workflow.py`
- ❌ `services/llm-diagnosis/__init__.py` (Safety Framework init)

### Code Removed from llm-diagnosis/diagnosis_service.py

```python
# ❌ REMOVED: Safety Framework imports (lines 26-33)
# from risk_assessor import RiskAssessor
# from rollback_manager import RollbackManager
# from approval_workflow import ApprovalWorkflow
# from autonomous_executor import AutonomousExecutor

# ❌ REMOVED: Safety Framework initialization (lines 78-90)
# self.risk_assessor = RiskAssessor(engine=self.engine)
# self.rollback_manager = RollbackManager(engine=self.engine)
# self.approval_workflow = ApprovalWorkflow(engine=self.engine)
# self.autonomous_executor = AutonomousExecutor(engine=self.engine)

# ❌ REMOVED: Safety Framework integration code (lines 316-380)
# - Risk assessment
# - Decision making
# - Auto-execution
# - Approval requests
```

## Files in remediation-agent (Correct Location)

These files are **correctly** in remediation-agent:

- ✅ `services/remediation-agent/risk_assessor.py`
- ✅ `services/remediation-agent/autonomous_executor.py`
- ✅ `services/remediation-agent/rollback_manager.py`
- ✅ `services/remediation-agent/approval_workflow.py`
- ✅ `services/remediation-agent/safety_integration.py` (wrapper)
- ✅ `services/remediation-agent/workflow.py` (LangGraph)
- ✅ `services/remediation-agent/main.py` (orchestration)

## Verification Results

### ✅ 1. llm-diagnosis Clean

```bash
$ ls services/llm-diagnosis/*.py | grep -E "(risk|rollback|approval|autonomous)"
# No output - files removed ✅

$ docker-compose logs llm-diagnosis --tail=50 | grep "Safety"
# No output - no Safety Framework code running ✅
```

### ✅ 2. remediation-agent Has Safety Framework

```bash
$ ls services/remediation-agent/*.py | grep -E "(risk|rollback|approval|autonomous|safety)"
services/remediation-agent/approval_workflow.py
services/remediation-agent/autonomous_executor.py
services/remediation-agent/risk_assessor.py
services/remediation-agent/rollback_manager.py
services/remediation-agent/safety_integration.py
# All files present ✅

$ docker-compose logs remediation-agent | grep "Safety"
2026-06-11 02:08:32 | INFO | ✅ Safety Framework integration initialized
2026-06-11 02:08:32 | INFO | ✅ Safety Framework integrated
# Safety Framework running ✅
```

### ✅ 3. End-to-End Test Passed

```
Test Incident: #9999
Risk Level: LOW (score: 0.33)
Decision: manual_only (confidence 0.71 < 0.75 threshold)
Database Logging: ✅ incident_risk_assessment + autonomous_decision_log
Decision Logic: ✅ Correct per decision matrix
```

## Decision Matrix (Reference)

| Risk Level | Confidence ≥ 0.90 | Confidence 0.75-0.90 | Confidence < 0.75 |
|------------|------------------|---------------------|-------------------|
| **LOW**        | execute          | execute_notify      | manual_only       |
| **MEDIUM**     | require_approval | require_approval    | manual_only       |
| **HIGH**       | require_approval | require_approval    | manual_only       |
| **CRITICAL**   | manual_only      | manual_only         | manual_only       |

## Key Architectural Principles

### 1. Single Responsibility
- **llm-diagnosis**: Diagnoses incidents (what/why/confidence)
- **remediation-agent**: Remediates incidents (how/when/safely)

### 2. Separation of Concerns
- Diagnosis doesn't make remediation decisions
- Remediation service owns all remediation logic

### 3. Safety as Gatekeeper
- Safety Framework sits **before** LangGraph workflow
- Decides **IF** remediation should proceed
- LangGraph handles **HOW** remediation proceeds

### 4. Clean Data Flow
```
Incident → Diagnosis → Kafka → Safety Check → LangGraph → Resolution
```

## Performance Impact

### llm-diagnosis
- **Before removal:** 0.12% CPU, 30MB RAM
- **After removal:** 0.13% CPU, 30MB RAM
- **Impact:** None ✅

### remediation-agent  
- **With Safety Framework:** 12.21% CPU, 591MB RAM (normal)
- Includes: Safety Framework + LangGraph + Vector embeddings
- **Performance:** Normal operational range ✅

## Summary

✅ **Architecture Corrected**
- Removed all Safety Framework code from llm-diagnosis
- Safety Framework properly integrated in remediation-agent
- Clean separation between diagnosis and remediation
- Safety Framework acts as gatekeeper before LangGraph workflow

✅ **Tested and Verified**
- llm-diagnosis operates without Safety Framework
- remediation-agent Safety Framework fully functional
- E2E test passed with correct decision logic
- Database logging working correctly
- Zero performance impact

✅ **Production Ready**
- Correct architectural design
- Clean service boundaries
- Safety checks in correct location
- Autonomous remediation with proper guardrails

---

**Status:** ✅ COMPLETE  
**Last Updated:** 2026-06-11  
**Services Rebuilt:** llm-diagnosis ✅, remediation-agent ✅
