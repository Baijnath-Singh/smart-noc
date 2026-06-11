# Safety Framework: End-to-End Flow with Remediation Agent

**Date:** June 11, 2026  
**Architecture:** Safety Framework integrated in remediation-agent (CORRECT)  
**Purpose:** Complete walkthrough showing how Safety Framework gates autonomous remediation

---

## 🎯 Complete End-to-End Flow

### Scenario: BGP Flapping on Distribution Switch

**Initial Alert**: Distribution switch `dist-sw-01` has BGP session flapping with peer 10.1.1.1

```
🔴 ALERT: BGP session down on dist-sw-01
Time: 2:30 AM (June 11, 2026)
Logs: 15 BGP log entries in 5 minutes
Affected devices: dist-sw-01, access-sw-05, access-sw-06, access-sw-07 (4 total)
```

---

## Step-by-Step Flow

### 1️⃣ **Incident Detection & Correlation** (Existing Pipeline)

**Anomaly Detector** identifies BGP flapping pattern:
```python
# services/anomaly-detector/detector.py
anomalies = [
    {'device': 'dist-sw-01', 'type': 'BGP_FLAPPING', 'severity': 0.85},
    {'device': 'dist-sw-01', 'type': 'HIGH_CPU', 'severity': 0.45}
]
```

**Correlation Engine** creates incident:
```python
# services/correlation-engine/correlator.py
incident = {
    'incident_number': 125,
    'primary_device': 'dist-sw-01',
    'incident_type': 'BGP_FLAPPING',
    'severity': 'MEDIUM',
    'affected_devices': ['dist-sw-01', 'access-sw-05', 'access-sw-06', 'access-sw-07'],
    'start_time': '2026-06-11 02:30:00',
    'status': 'ACTIVE'
}

# Save to database
INSERT INTO incidents (incident_number, primary_device, incident_type, severity, ...)
VALUES (125, 'dist-sw-01', 'BGP_FLAPPING', 'MEDIUM', ...);
```

---

### 2️⃣ **LLM Diagnosis Service** (ONLY DIAGNOSIS - Clean)

**Kafka Message**: `incidents` topic → llm-diagnosis service

**llm-diagnosis processes incident**:
```python
# services/llm-diagnosis/diagnosis_service.py
# ✅ NO SAFETY FRAMEWORK CODE HERE - CLEAN SERVICE

class DiagnosisService:
    def __init__(self):
        self.llm = LLMClient(...)
        self.context = ContextBuilder(...)
        self.calibrator = ConfidenceCalibrator(...)
        # ❌ NO: self.risk_assessor, self.executor, self.rollback, etc.
    
    async def process_incident(self, incident: dict):
        # 1. Build context (vector search + anomalies + history)
        context = self.context.build_context(incident)
        
        # 2. Call LLM for diagnosis
        diagnosis = await self.llm.diagnose(incident, context)
        '''
        diagnosis = {
            'root_cause': 'BGP session instability due to hold timer mismatch',
            'confidence': 0.75,  # Raw LLM confidence
            'confidence_reasoning': '''
                ✓ Direct evidence: BGP hold timer mismatch in logs (30s vs 180s)
                ✓ Pattern match: Similar to incident #87 (resolved with timer adjustment)
                ✗ Missing: No interface errors (unusual for link issues)
                
                Confidence: 0.75 - Strong evidence but not 100% certain about peer config
            ''',
            'evidence_quality': {
                'direct_evidence_count': 2,
                'indirect_evidence_count': 1,
                'missing_critical_data': ['peer device configuration']
            },
            'remediation_plan': [
                {
                    'step': 1,
                    'action': 'Set BGP hold timer to 180s on dist-sw-01',
                    'command': 'router bgp 65000\n neighbor 10.1.1.1 timers 60 180',
                    'expected_outcome': 'BGP timers synchronized',
                    'duration_minutes': 2
                },
                {
                    'step': 2,
                    'action': 'Clear BGP session with peer 10.1.1.1',
                    'command': 'clear bgp neighbor 10.1.1.1 soft',
                    'expected_outcome': 'Session re-establishes cleanly',
                    'duration_minutes': 1
                }
            ],
            'requires_reboot': False
        }
        '''
        
        # 3. Three-layer confidence calibration
        calibrated = self.calibrator.calibrate(
            raw_confidence=diagnosis['confidence'],
            incident_type=incident['incident_type'],
            evidence_quality=diagnosis['evidence_quality']
        )
        '''
        calibrated = {
            'raw_confidence': 0.75,
            'calibrated_confidence': 0.67,  # Adjusted down based on history
            'confidence_reasoning': '...',
            'calibration_factors': {
                'historical_adjustment': -0.05,  # BGP diagnoses tend to be overconfident
                'evidence_quality_adjustment': -0.03  # Missing peer config data
            }
        }
        '''
        
        # 4. Save diagnosis to database
        await self.db.save_diagnosis(incident['incident_number'], diagnosis, calibrated)
        
        # 5. Publish to Kafka for remediation-agent
        await self.kafka.publish('incidents-diagnosed', {
            'incident_number': 125,
            'incident': incident,
            'diagnosis': diagnosis,
            'calibrated_confidence': 0.67,
            'timestamp': '2026-06-11 02:31:30'
        })
        
        # ✅ END OF llm-diagnosis RESPONSIBILITY
        # ❌ NO risk assessment, NO decision making, NO remediation here!
```

**Database Update**:
```sql
-- llm-diagnosis only updates diagnosis columns
UPDATE incidents 
SET 
    root_cause = 'BGP session instability due to hold timer mismatch',
    root_cause_confidence = 0.67,  -- Calibrated confidence
    confidence_reasoning = '✓ Direct evidence: BGP hold timer mismatch...',
    remediation_plan = '[{"step": 1, "action": "Set BGP hold timer..."}]',
    diagnosis_timestamp = '2026-06-11 02:31:30',
    llm_model = 'gpt-4'
WHERE incident_number = 125;
```

**Kafka Message Published**: Topic `incidents-diagnosed`
```json
{
  "incident_number": 125,
  "incident": {
    "incident_number": 125,
    "primary_device": "dist-sw-01",
    "incident_type": "BGP_FLAPPING",
    "severity": "MEDIUM",
    "affected_devices": ["dist-sw-01", "access-sw-05", "access-sw-06", "access-sw-07"]
  },
  "diagnosis": {
    "root_cause": "BGP session instability due to hold timer mismatch",
    "confidence": 0.75,
    "remediation_plan": [...]
  },
  "calibrated_confidence": 0.67
}
```

---

### 3️⃣ **Remediation Agent Receives Message** (Entry Point)

**Kafka Consumer**: remediation-agent subscribes to `incidents-diagnosed`

```python
# services/remediation-agent/main.py

class RemediationService:
    def __init__(self):
        # LangGraph workflow for remediation execution
        self.agent = RemediationAgent(...)
        
        # ✅ Safety Framework integrated HERE (correct location)
        database_url = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
        self.safety = SafetyIntegration(database_url)
        
        logger.info("✅ Safety Framework integrated")
        logger.info("✅ Remediation agent initialized with LangGraph workflow")
    
    async def process_diagnosis(self, message: dict) -> bool:
        """Process diagnosed incident with Safety Framework gatekeeper"""
        
        incident = message['incident']
        diagnosis = message['diagnosis']
        calibrated_confidence = message['calibrated_confidence']
        
        logger.info(f"📥 Received diagnosed incident #{incident['incident_number']}")
        logger.info(f"   Root cause: {diagnosis['root_cause']}")
        logger.info(f"   Confidence: {calibrated_confidence}")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 🛡️ SAFETY FRAMEWORK GATEKEEPER (CORRECT LOCATION)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        logger.info("🛡️ Running Safety Framework assessment...")
        safety_result = self._assess_safety(incident, diagnosis, calibrated_confidence)
        
        # Handle different decision outcomes
        if safety_result['must_escalate']:
            logger.warning(f"🚫 ESCALATE: {safety_result['reasoning']}")
            await self._escalate_to_human(incident, safety_result)
            return True
        
        elif safety_result['requires_approval']:
            logger.warning(f"⏸️ APPROVAL REQUIRED: {safety_result['reasoning']}")
            approval_id = await self._request_approval(incident, diagnosis, safety_result)
            logger.info(f"   Approval request #{approval_id} created")
            return True
        
        elif safety_result['safe_to_proceed']:
            logger.success(f"✅ SAFE TO PROCEED: {safety_result['reasoning']}")
            logger.info(f"   Risk: {safety_result['risk_level']} ({safety_result['risk_score']:.2f})")
            logger.info(f"   Decision: {safety_result['decision']}")
            
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            # 🚀 PASS TO LANGGRAPH WORKFLOW (Only if safe)
            # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
            
            logger.info("🤖 Initiating LangGraph autonomous remediation...")
            result = await self.agent.remediate(incident, diagnosis)
            
            if result['success']:
                logger.success(f"✅ Remediation completed successfully")
            else:
                logger.error(f"❌ Remediation failed: {result['error']}")
            
            return result['success']
        
        else:
            logger.error(f"❌ BLOCKED: {safety_result['reasoning']}")
            return False
```

---

### 4️⃣ **Safety Framework Assessment** (Risk + Decision)

**Safety Integration wrapper orchestrates all components**:

```python
# services/remediation-agent/safety_integration.py

class SafetyIntegration:
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)
        self.risk_assessor = RiskAssessor(self.engine)
        self.executor = AutonomousExecutor(self.engine)
        self.rollback_manager = RollbackManager(self.engine)
        self.approval_workflow = ApprovalWorkflow(self.engine)
    
    def assess_safety(self, incident: dict, diagnosis: dict, calibrated_confidence: float) -> dict:
        """Complete safety assessment - risk + decision"""
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STEP 1: RISK ASSESSMENT
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        risk_level, risk_score, factors = self.risk_assessor.assess_risk(
            incident=incident,
            diagnosis=diagnosis
        )
        
        '''
        Risk Calculation for our example:
        
        1. Device Criticality: dist-sw-01 = HIGH (0.75)
           - Distribution switch in device_criticality table
        
        2. Blast Radius: 4 devices affected (0.50)
           - 3-9 devices = MEDIUM impact
        
        3. Time Sensitivity: 2:30 AM = off-hours (0.30)
           - Not business hours (9 AM - 5 PM) = LOW urgency
        
        4. Change Complexity: BGP config change (0.60)
           - 2 remediation steps
           - Routing protocol change = MEDIUM complexity
        
        Weighted Score:
        overall_risk_score = (0.75 * 0.40) + (0.50 * 0.30) + (0.30 * 0.20) + (0.60 * 0.10)
                           = 0.30 + 0.15 + 0.06 + 0.06
                           = 0.57
        
        Risk Level: 0.57 → MEDIUM (0.40-0.59)
        '''
        
        logger.info(f"📊 Risk Assessment:")
        logger.info(f"   Overall Risk: {risk_level} (score: {risk_score:.2f})")
        logger.info(f"   Device Criticality: {factors['device_criticality']:.2f}")
        logger.info(f"   Blast Radius: {factors['blast_radius']:.2f}")
        logger.info(f"   Time Sensitivity: {factors['time_sensitivity']:.2f}")
        logger.info(f"   Change Complexity: {factors['change_complexity']:.2f}")
        
        # Save to database
        self.risk_assessor.save_risk_assessment(
            incident_number=incident['incident_number'],
            risk_level=risk_level,
            overall_risk_score=risk_score,
            factors=factors
        )
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STEP 2: DECISION MATRIX EVALUATION
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        decision, reasoning = self.executor.decide_action(
            incident={'incident_number': incident['incident_number'], 'incident_type': incident['incident_type']},
            diagnosis_with_confidence={'calibrated_confidence': calibrated_confidence},
            risk_assessment={'risk_level': risk_level, 'overall_risk_score': risk_score}
        )
        
        '''
        Decision Matrix Logic:
        
        Input:
          - Risk: MEDIUM
          - Confidence: 0.67
        
        Matrix Rules (from autonomous_executor.py):
        
        Rule 1: CRITICAL risk → always manual_only ❌ (not CRITICAL)
        Rule 2: HIGH risk + confidence < 0.92 → manual_only ❌ (not HIGH)
        Rule 3: HIGH risk + confidence ≥ 0.92 → require_approval ❌ (not HIGH)
        Rule 4: MEDIUM risk + confidence < 0.92 → manual_only ✅ MATCH!
                (0.67 < 0.92 → requires manual intervention)
        Rule 5: MEDIUM risk + confidence ≥ 0.92 → require_approval ❌ (0.67 < 0.92)
        Rule 6: LOW risk + confidence ≥ 0.75 → execute ❌ (not LOW)
        
        Decision: manual_only
        Reasoning: MEDIUM risk with moderate confidence (0.67) requires manual review
        '''
        
        logger.info(f"🎯 Decision Matrix:")
        logger.info(f"   Decision: {decision}")
        logger.info(f"   Reasoning: {reasoning}")
        
        # Save decision to database
        self.executor.save_decision(
            incident_number=incident['incident_number'],
            decision=decision,
            reasoning=reasoning,
            calibrated_confidence=calibrated_confidence,
            risk_level=risk_level
        )
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # STEP 3: TRANSLATE DECISION TO ACTION FLAGS
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        return {
            'risk_level': risk_level,
            'risk_score': risk_score,
            'risk_factors': factors,
            'decision': decision,
            'reasoning': reasoning,
            'calibrated_confidence': calibrated_confidence,
            
            # Action flags for remediation service
            'safe_to_proceed': False,           # decision == 'execute'
            'requires_approval': False,         # decision == 'require_approval'
            'must_escalate': True,              # decision == 'manual_only'
            'should_create_snapshot': True      # Any non-execute decision
        }
```

**Database Updates**:

```sql
-- 1. Risk assessment saved
INSERT INTO incident_risk_assessment 
    (incident_number, risk_level, overall_risk_score, device_criticality, 
     blast_radius, time_sensitivity, change_complexity, factors, assessed_at)
VALUES 
    (125, 'MEDIUM', 0.57, 0.75, 0.50, 0.30, 0.60,
     '{"device_criticality": 0.75, "blast_radius": 0.50, "time_sensitivity": 0.30, "change_complexity": 0.60}',
     '2026-06-11 02:31:35');

-- 2. Decision saved
INSERT INTO autonomous_decision_log
    (incident_number, decision, reasoning, calibrated_confidence, risk_level, decided_at)
VALUES
    (125, 'manual_only', 
     'MEDIUM risk with moderate confidence (0.67) requires manual review',
     0.67, 'MEDIUM', '2026-06-11 02:31:35');
```

---

### 5️⃣ **Decision Path: Manual Escalation** (Our Example)

Since decision is `manual_only`, the system escalates to human operator:

```python
# services/remediation-agent/main.py

async def _escalate_to_human(self, incident: dict, safety_result: dict):
    """Escalate to human operator with full context"""
    
    # Update incident status
    await self.db.execute("""
        UPDATE incidents 
        SET 
            status = 'REQUIRES_MANUAL_INTERVENTION',
            escalated_at = NOW(),
            escalation_reason = $1
        WHERE incident_number = $2
    """, safety_result['reasoning'], incident['incident_number'])
    
    # Create notification (email, Slack, PagerDuty, etc.)
    await self.notify(
        channel='NOC_ENGINEERS',
        priority='HIGH',
        message=f"""
        🚨 Incident #{incident['incident_number']} Requires Manual Intervention
        
        Device: {incident['primary_device']}
        Type: {incident['incident_type']}
        Severity: {incident['severity']}
        
        Diagnosis: {incident.get('root_cause', 'N/A')}
        Confidence: {safety_result['calibrated_confidence']:.2%}
        
        Risk Assessment:
          - Risk Level: {safety_result['risk_level']}
          - Risk Score: {safety_result['risk_score']:.2f}
          - Affected Devices: {len(incident.get('affected_devices', []))}
        
        Decision: MANUAL INTERVENTION REQUIRED
        Reason: {safety_result['reasoning']}
        
        Action Required: Review and approve/modify remediation plan in dashboard
        Dashboard: https://noc.example.com/incidents/{incident['incident_number']}
        """
    )
    
    logger.warning(f"🚨 Incident #{incident['incident_number']} escalated to human operators")
```

**Final Database State**:
```sql
UPDATE incidents 
SET 
    status = 'REQUIRES_MANUAL_INTERVENTION',
    escalated_at = '2026-06-11 02:31:40',
    escalation_reason = 'MEDIUM risk with moderate confidence (0.67) requires manual review'
WHERE incident_number = 125;
```

---

## Alternative Decision Paths

### Path A: LOW Risk + High Confidence → Execute

**Different Scenario**: Simple interface flap on access switch

```python
# Same flow until Step 4, but different inputs:
incident = {
    'incident_number': 126,
    'primary_device': 'access-sw-10',  # Access switch (LOW criticality)
    'incident_type': 'INTERFACE_FLAPPING',
    'affected_devices': ['access-sw-10'],  # Only 1 device
    'severity': 'LOW'
}

diagnosis = {
    'root_cause': 'Interface Gi0/1 flapping due to duplex mismatch',
    'confidence': 0.95  # High confidence
}

calibrated_confidence = 0.92  # After three-layer calibration

# Risk Assessment:
risk_factors = {
    'device_criticality': 0.25,  # Access switch = LOW
    'blast_radius': 0.20,        # 1 device = LOW
    'time_sensitivity': 0.30,    # Off-hours = LOW
    'change_complexity': 0.30    # Simple interface command = LOW
}
overall_risk_score = (0.25 * 0.40) + (0.20 * 0.30) + (0.30 * 0.20) + (0.30 * 0.10)
                   = 0.10 + 0.06 + 0.06 + 0.03
                   = 0.25
risk_level = 'LOW'  # 0.25 < 0.40

# Decision Matrix:
# Rule 6: LOW risk + confidence ≥ 0.75 → execute
# 0.92 ≥ 0.75 ✅
decision = 'execute'

# Safety result:
safety_result = {
    'safe_to_proceed': True,  # ✅ GREEN LIGHT
    'requires_approval': False,
    'must_escalate': False
}
```

**Autonomous Execution**:
```python
# services/remediation-agent/main.py

if safety_result['safe_to_proceed']:
    logger.success("✅ Safety checks passed, proceeding with autonomous remediation")
    
    # 1. Create pre-remediation snapshot
    snapshot_id = self.safety.create_pre_remediation_snapshot(
        incident_number=126,
        device_name='access-sw-10',
        config=await self.get_device_config('access-sw-10')
    )
    
    # 2. Execute with LangGraph workflow
    result = await self.agent.remediate(incident, diagnosis)
    
    # 3. If execution fails, automatic rollback
    if not result['success']:
        logger.warning("⚠️ Remediation failed, initiating rollback...")
        rollback_result = self.safety.execute_with_rollback(
            incident_number=126,
            snapshot_id=snapshot_id,
            commands=diagnosis['remediation_plan'],
            device='access-sw-10'
        )
```

---

### Path B: MEDIUM Risk + High Confidence → Require Approval

**Different Scenario**: Core router with high confidence diagnosis

```python
incident = {
    'incident_number': 127,
    'primary_device': 'core-router-01',  # Core = CRITICAL
    'incident_type': 'HIGH_CPU',
    'affected_devices': ['core-router-01'],
    'severity': 'HIGH'
}

calibrated_confidence = 0.94  # Very high confidence

# Risk Assessment:
risk_factors = {
    'device_criticality': 0.95,  # Core router = CRITICAL
    'blast_radius': 0.20,        # 1 device but critical
    'time_sensitivity': 0.90,    # Business hours = HIGH
    'change_complexity': 0.50    # MODERATE
}
overall_risk_score = (0.95 * 0.40) + (0.20 * 0.30) + (0.90 * 0.20) + (0.50 * 0.10)
                   = 0.38 + 0.06 + 0.18 + 0.05
                   = 0.67
risk_level = 'HIGH'  # 0.60 ≤ 0.67 < 0.80

# Decision Matrix:
# Rule 3: HIGH risk + confidence ≥ 0.92 → require_approval
# 0.94 ≥ 0.92 ✅
decision = 'require_approval'

safety_result = {
    'safe_to_proceed': False,
    'requires_approval': True,  # ✅ APPROVAL WORKFLOW
    'must_escalate': False
}
```

**Approval Workflow**:
```python
# services/remediation-agent/main.py

elif safety_result['requires_approval']:
    logger.warning("⏸️ High risk incident requires approval before execution")
    
    # Create approval request
    approval_id = self.safety.request_approval(
        incident_number=127,
        risk_level='HIGH',
        risk_score=0.67,
        confidence=0.94,
        proposed_actions=diagnosis['remediation_plan'],
        timeout_minutes=30  # Auto-reject if no response
    )
    
    # Notify senior engineers
    await self.notify(
        channel='SENIOR_NOC_ENGINEERS',
        priority='URGENT',
        message=f"""
        ⚠️ Approval Required: Incident #{127}
        
        Device: core-router-01 (CRITICAL)
        Risk: HIGH (0.67)
        Confidence: 94%
        
        Proposed Actions:
        1. Restart stuck BGP process
        2. Clear ARP cache
        
        Approve/Reject in dashboard or reply:
        - APPROVE: /approve {approval_id}
        - REJECT: /reject {approval_id}
        
        Auto-reject in 30 minutes if no response
        """
    )
    
    # Wait for approval (async, doesn't block)
    logger.info(f"⏳ Waiting for approval #{approval_id}...")
```

**Database**:
```sql
INSERT INTO remediation_approvals
    (incident_number, risk_level, risk_score, calibrated_confidence,
     proposed_actions, status, timeout_at)
VALUES
    (127, 'HIGH', 0.67, 0.94,
     '[{"step": 1, "action": "Restart stuck BGP process..."}]',
     'PENDING', '2026-06-11 03:01:35');
```

**When approved by human**:
```python
# Human clicks "Approve" in dashboard or types /approve command

async def handle_approval(approval_id: int, approved_by: str):
    # Update approval record
    await self.db.execute("""
        UPDATE remediation_approvals
        SET status = 'APPROVED', approved_by = $1, approved_at = NOW()
        WHERE id = $2
    """, approved_by, approval_id)
    
    # Fetch incident and diagnosis
    approval = await self.db.fetch_approval(approval_id)
    
    # Create snapshot
    snapshot_id = self.safety.create_pre_remediation_snapshot(...)
    
    # Execute remediation
    logger.success(f"✅ Approval granted by {approved_by}, executing remediation...")
    result = await self.agent.remediate(approval.incident, approval.diagnosis)
```

---

## 6️⃣ **LangGraph Workflow Execution** (If Approved)

When Safety Framework gives green light (`safe_to_proceed=True`), LangGraph executes:

```python
# services/remediation-agent/workflow.py

class RemediationAgent:
    """LangGraph state machine for autonomous remediation"""
    
    async def remediate(self, incident: dict, diagnosis: dict) -> dict:
        """Execute 7-phase remediation workflow"""
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PHASE 1: ASSESS COMPLEXITY
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        complexity = self._assess_complexity(diagnosis['remediation_plan'])
        logger.info(f"📊 Complexity: {complexity['level']} ({complexity['score']:.2f})")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PHASE 2: INVESTIGATE (gather additional context)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        device_state = await self._investigate(incident['primary_device'])
        logger.info(f"🔍 Current device state: {device_state['status']}")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PHASE 3: CREATE PLAN (convert diagnosis to executable steps)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        execution_plan = self._create_plan(diagnosis['remediation_plan'], device_state)
        logger.info(f"📝 Execution plan: {len(execution_plan)} steps")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PHASE 4: EXECUTE ACTIONS
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        for step in execution_plan:
            logger.info(f"⚡ Executing: {step['action']}")
            result = await self._execute_step(step, incident['primary_device'])
            
            if not result['success']:
                logger.error(f"❌ Step failed: {result['error']}")
                # Trigger rollback (handled by Safety Framework)
                return {'success': False, 'error': result['error'], 'failed_step': step}
            
            logger.success(f"✅ Step completed: {step['action']}")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PHASE 5: VERIFY FIX
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        logger.info("🔍 Verifying fix...")
        verification = await self._verify_fix(incident, device_state)
        
        if not verification['fixed']:
            logger.warning(f"⚠️ Verification failed: {verification['reason']}")
            # May trigger rollback or escalation
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PHASE 6: ROLLBACK (if needed - handled by Safety Framework)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        # Safety Framework's RollbackManager handles this
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # PHASE 7: DOCUMENT
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        await self._document_remediation(incident, execution_plan, verification)
        
        return {
            'success': verification['fixed'],
            'steps_executed': len(execution_plan),
            'duration_seconds': (datetime.now() - start_time).total_seconds(),
            'verification': verification
        }
```

**Database Logging**:
```sql
-- Remediation execution tracked
INSERT INTO remediation_executions
    (incident_number, snapshot_id, steps_executed, success, 
     executed_at, completed_at, execution_metadata)
VALUES
    (126, 15, 2, true,
     '2026-06-11 02:32:00', '2026-06-11 02:32:45',
     '{"duration_seconds": 45, "steps": [...], "verification": {...}}');
```

---

## Complete Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SMART NOC SYSTEM                            │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────┐
│ Network Logs │
└──────┬───────┘
       │
       ▼
┌──────────────────┐
│ Anomaly Detector │  (Isolation Forest, statistical analysis)
└──────┬───────────┘
       │
       ▼
┌────────────────────┐
│ Correlation Engine │  (Group anomalies → incidents)
└──────┬─────────────┘
       │
       ▼  Create incident in DB
┌─────────────────────────────────────────────────────────────────────┐
│                        POSTGRES DATABASE                            │
│  incidents table: incident_number=125, status=ACTIVE                │
└─────────────────────────────────────────────────────────────────────┘
       │
       ▼  Kafka: "incidents" topic
┌─────────────────────────────────────────────────────────────────────┐
│                      LLM DIAGNOSIS SERVICE                          │
│  ✅ CLEAN - NO SAFETY FRAMEWORK CODE                               │
│                                                                     │
│  1. Build context (vector search KB + anomalies)                   │
│  2. Call LLM (GPT-4/Claude)                                        │
│  3. Three-layer confidence calibration                             │
│  4. Save diagnosis to DB                                           │
│  5. Publish to Kafka: "incidents-diagnosed"                        │
└─────────────────────────────────────────────────────────────────────┘
       │
       ▼  Kafka: "incidents-diagnosed" topic
┌─────────────────────────────────────────────────────────────────────┐
│                    REMEDIATION AGENT SERVICE                        │
│  🛡️ SAFETY FRAMEWORK INTEGRATED HERE (CORRECT)                     │
│                                                                     │
│  ┌────────────────────────────────────────┐                        │
│  │   Safety Framework (Gatekeeper)        │                        │
│  │                                        │                        │
│  │  1. Risk Assessment                    │                        │
│  │     - Device criticality               │                        │
│  │     - Blast radius                     │                        │
│  │     - Time sensitivity                 │                        │
│  │     - Change complexity                │                        │
│  │     → Overall risk score & level       │                        │
│  │                                        │                        │
│  │  2. Decision Matrix                    │                        │
│  │     - Input: risk + confidence         │                        │
│  │     - Output: execute / approval /     │                        │
│  │               manual                   │                        │
│  │                                        │                        │
│  │  3. Translate to action flags          │                        │
│  │     - safe_to_proceed?                 │                        │
│  │     - requires_approval?               │                        │
│  │     - must_escalate?                   │                        │
│  └────────────┬───────────────────────────┘                        │
│               │                                                     │
│               ▼                                                     │
│  ┌─────────────────────────────┐                                   │
│  │ IF safe_to_proceed:         │                                   │
│  │                             │                                   │
│  │  ┌───────────────────────┐  │                                   │
│  │  │  LangGraph Workflow   │  │                                   │
│  │  │                       │  │                                   │
│  │  │  1. Assess complexity │  │                                   │
│  │  │  2. Investigate       │  │                                   │
│  │  │  3. Create plan       │  │                                   │
│  │  │  4. Execute actions   │  │                                   │
│  │  │  5. Verify fix        │  │                                   │
│  │  │  6. Rollback          │  │                                   │
│  │  │  7. Document          │  │                                   │
│  │  └───────────────────────┘  │                                   │
│  └─────────────────────────────┘                                   │
│                                                                     │
│  ┌─────────────────────────────┐                                   │
│  │ IF requires_approval:       │                                   │
│  │  → Create approval request  │                                   │
│  │  → Notify senior engineers  │                                   │
│  │  → Wait for human decision  │                                   │
│  └─────────────────────────────┘                                   │
│                                                                     │
│  ┌─────────────────────────────┐                                   │
│  │ IF must_escalate:           │                                   │
│  │  → Update incident status   │                                   │
│  │  → Notify NOC engineers     │                                   │
│  │  → Human takes over         │                                   │
│  └─────────────────────────────┘                                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Key Architecture Principles

### ✅ Correct Separation of Concerns

1. **llm-diagnosis service:**
   - ONLY diagnoses incidents
   - NO risk assessment
   - NO decision making
   - NO remediation execution
   - ONLY: context → LLM → diagnosis → publish

2. **remediation-agent service:**
   - Receives diagnosed incidents
   - Safety Framework as GATEKEEPER
   - Risk assessment + decision matrix
   - Controls access to LangGraph workflow
   - Handles approvals and escalations

3. **Safety Framework:**
   - Lives in remediation-agent (correct location)
   - Evaluates before ANY remediation attempt
   - Multiple decision paths (execute/approve/manual)
   - Database logging for audit trail

---

## Summary: Why This Architecture is Correct

| Aspect | llm-diagnosis | remediation-agent |
|--------|---------------|-------------------|
| **Purpose** | Diagnose what's wrong | Decide if/how to fix |
| **LLM Usage** | Yes (for diagnosis) | Yes (for execution) |
| **Safety Framework** | ❌ NO | ✅ YES |
| **Risk Assessment** | ❌ NO | ✅ YES |
| **Decision Making** | ❌ NO | ✅ YES |
| **Remediation** | ❌ NO | ✅ YES |
| **Database Writes** | Diagnosis columns | Risk + decision + execution tables |
| **Kafka Publishes** | incidents-diagnosed | incident-remediations |

**Key Principle**: **Diagnosis concerns are separate from remediation concerns**

- Diagnosis = "What is wrong + how to fix"
- Remediation = "Should we fix + is it safe + execute fix"

---

## Complete Database Schema Impact

```sql
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- llm-diagnosis writes to:
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

UPDATE incidents SET
    root_cause = '...',                  -- Diagnosis
    root_cause_confidence = 0.67,        -- Calibrated confidence
    confidence_reasoning = '...',        -- Why this confidence
    remediation_plan = '[...]',          -- How to fix
    diagnosis_timestamp = NOW(),
    llm_model = 'gpt-4'
WHERE incident_number = 125;

-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
-- remediation-agent (Safety Framework) writes to:
-- ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

-- 1. Risk assessment
INSERT INTO incident_risk_assessment (...) VALUES (...);

-- 2. Decision log
INSERT INTO autonomous_decision_log (...) VALUES (...);

-- 3. Configuration snapshot (before remediation)
INSERT INTO configuration_snapshots (...) VALUES (...);

-- 4. Remediation execution
INSERT INTO remediation_executions (...) VALUES (...);

-- 5. Rollback history (if needed)
INSERT INTO rollback_history (...) VALUES (...);

-- 6. Approval workflow (if needed)
INSERT INTO remediation_approvals (...) VALUES (...);

-- 7. Update incident status
UPDATE incidents SET
    status = 'REMEDIATED' | 'REQUIRES_APPROVAL' | 'REQUIRES_MANUAL_INTERVENTION',
    escalated_at = NOW(),
    escalation_reason = '...'
WHERE incident_number = 125;
```

---

## Testing the Complete Flow

```bash
# 1. Verify services running
docker-compose ps

# 2. Create test incident (simulates correlation engine)
docker-compose exec -T postgres psql -U noc_admin -d smart_noc <<EOF
INSERT INTO incidents 
    (incident_number, primary_device, incident_type, severity, affected_devices, status)
VALUES 
    (200, 'test-device-01', 'BGP_FLAPPING', 'MEDIUM', ARRAY['test-device-01'], 'ACTIVE');
EOF

# 3. Publish to Kafka (simulates diagnosis)
docker-compose exec -T remediation-agent python3 << 'EOF'
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers=['kafka:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

message = {
    'incident_number': 200,
    'incident': {
        'incident_number': 200,
        'primary_device': 'test-device-01',
        'incident_type': 'BGP_FLAPPING',
        'severity': 'MEDIUM',
        'affected_devices': ['test-device-01']
    },
    'diagnosis': {
        'root_cause': 'Test BGP flapping',
        'confidence': 0.85,
        'remediation_plan': [{'step': 1, 'action': 'Test action', 'command': 'show version'}]
    },
    'calibrated_confidence': 0.75
}

producer.send('incidents-diagnosed', message)
producer.flush()
print("✅ Test message published")
EOF

# 4. Check logs to see Safety Framework in action
docker-compose logs remediation-agent --tail=50 | grep -E "Safety|Risk|Decision"

# 5. Verify database writes
docker-compose exec -T postgres psql -U noc_admin -d smart_noc -c "
SELECT 
    i.incident_number,
    i.root_cause,
    r.risk_level,
    r.overall_risk_score,
    d.decision,
    d.reasoning
FROM incidents i
LEFT JOIN incident_risk_assessment r ON i.incident_number = r.incident_number
LEFT JOIN autonomous_decision_log d ON i.incident_number = d.incident_number
WHERE i.incident_number = 200;
"
```

---

## Conclusion

The Safety Framework is now correctly integrated in the **remediation-agent service** where it:

1. ✅ Acts as gatekeeper before ANY remediation attempt
2. ✅ Assesses risk using 4 weighted factors
3. ✅ Applies decision matrix based on risk + confidence
4. ✅ Controls access to LangGraph workflow
5. ✅ Logs all decisions for audit trail
6. ✅ Handles approvals and escalations
7. ✅ Manages rollbacks if remediation fails

The **llm-diagnosis service** is now clean and focused solely on diagnosis, maintaining proper separation of concerns.

**This is the correct architecture for autonomous remediation with safety guardrails.**
