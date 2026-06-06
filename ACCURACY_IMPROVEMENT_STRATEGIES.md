# Smart NOC - Accuracy Improvement Strategies

**Version:** 1.0  
**Date:** May 22, 2026  
**Focus:** Improving detection, diagnosis, and remediation accuracy

---

## Overview

This document provides actionable strategies to improve accuracy across the Smart NOC pipeline:
1. **Anomaly Detection** (currently 6 detectors: 5 rule-based + 1 ML)
2. **LLM Diagnosis** (Groq API with context from ChromaDB)
3. **Remediation** (LangChain/LangGraph workflow)

---

## 1. Anomaly Detection Accuracy

### Current Implementation
- **Rule-based:** 5 detectors (INTERFACE_DOWN, INTERFACE_FLAPPING, BGP_FLAP, HIGH_CPU, MEMORY_LEAK)
- **ML-based:** Isolation Forest for UNKNOWN_PATTERN detection
- **State:** Redis for sliding window counters
- **Location:** `services/anomaly-detector/anomaly_service.py`

### 🎯 Quick Wins (High Impact, Low Effort)

#### A. Tune Flapping Threshold
**Current:** 3 state changes in 5 minutes triggers INTERFACE_FLAPPING
**Problem:** Too sensitive for edge devices, not sensitive enough for core routers
**Solution:**
```yaml
# services/anomaly-detector/config.yaml
detection:
  flap_threshold:
    core: 2        # Critical devices: Lower threshold
    distribution: 3 # Default
    edge: 5        # Edge devices: Higher threshold
  time_window: 300
```

**Implementation:**
```python
# detectors/rule_based.py
def _detect_interface_flapping(self, log: Dict) -> Optional[Dict]:
    device_type = self._get_device_criticality(log['device'])
    threshold = self.config['detection']['flap_threshold'].get(device_type, 3)
    # ... rest of logic
```

**Expected Impact:** 30% reduction in false positives

#### B. Add Context-Aware Thresholds
**Current:** Fixed CPU threshold (80%)
**Problem:** Different device types have different normal operating ranges
**Solution:**
```yaml
detection:
  cpu_threshold:
    router: 80      # Routers typically run cooler
    switch: 85      # Switches can run hotter
    firewall: 90    # Firewalls under load
  baseline_learning: true  # Learn device-specific baselines
```

**Implementation:**
```python
# Add to RuleBasedDetector
def _detect_high_cpu(self, log: Dict) -> Optional[Dict]:
    cpu_value = self._extract_cpu_value(log)
    device_type = self._get_device_type(log['device'])
    
    # Dynamic baseline (24-hour moving average + 2 std deviations)
    baseline = self.state.get_baseline(f"cpu:{log['device']}", window=86400)
    if baseline:
        threshold = min(baseline['mean'] + 2 * baseline['std'], 95)
    else:
        threshold = self.config['detection']['cpu_threshold'].get(device_type, 80)
    
    if cpu_value > threshold:
        return self._create_anomaly('HIGH_CPU', log, confidence=0.88)
```

**Expected Impact:** 25% improvement in CPU anomaly accuracy

#### C. Enrich Logs Before Detection
**Current:** Raw logs consumed directly
**Problem:** Missing business context (device role, criticality, location)
**Solution:** Re-enable Logstash enrichment
```ruby
# config/logstash/logstash.conf
filter {
  # Add device metadata from lookup table
  translate {
    field => "device"
    destination => "device_metadata"
    dictionary_path => "/etc/logstash/device_inventory.yaml"
  }
  
  mutate {
    add_field => {
      "device_role" => "%{[device_metadata][role]}"
      "criticality" => "%{[device_metadata][criticality]}"
      "location" => "%{[device_metadata][location]}"
    }
  }
}
```

**Update anomaly detector:**
```python
# Use enriched topic instead of raw
kafka:
  input_topic: network-logs-enriched  # Was: network-logs
```

**Expected Impact:** 40% better prioritization, 15% accuracy improvement

### 🚀 Advanced Improvements (High Impact, Medium Effort)

#### D. Multi-Model ML Ensemble
**Current:** Single Isolation Forest model
**Problem:** One model can't capture all anomaly types
**Solution:** Ensemble of specialized models
```python
# detectors/ml_based.py
class MLBasedDetector:
    def __init__(self, state, config):
        self.models = {
            'isolation_forest': IsolationForest(contamination=0.1),
            'autoencoder': AutoencoderAnomalyDetector(),  # For temporal patterns
            'lof': LocalOutlierFactor(novelty=True),      # For density-based
        }
        self.voting_threshold = 2  # 2/3 models must agree
    
    def detect(self, log: Dict) -> List[Dict]:
        votes = []
        for name, model in self.models.items():
            if model.predict(features) == -1:  # Anomaly
                votes.append(name)
        
        if len(votes) >= self.voting_threshold:
            confidence = len(votes) / len(self.models)
            return [self._create_anomaly('UNKNOWN_PATTERN', log, confidence)]
        return []
```

**Expected Impact:** 50% improvement in ML detection accuracy

#### E. Time-Series Analysis for Patterns
**Current:** Single log evaluated in isolation
**Problem:** Miss temporal patterns (slow memory leaks, gradual performance degradation)
**Solution:** Sliding window feature extraction
```python
# detectors/temporal_detector.py
class TemporalPatternDetector:
    def detect_trend(self, device: str, metric: str, window_minutes: int = 60):
        """Detect gradual increase/decrease trends"""
        values = self.state.get_time_series(f"{device}:{metric}", window_minutes * 60)
        
        if len(values) < 10:
            return None
        
        # Linear regression to detect trend
        slope, r_squared = self._calculate_trend(values)
        
        # Detect memory leak: Steady upward trend
        if metric == 'memory' and slope > 0.1 and r_squared > 0.8:
            return {
                'anomaly_type': 'MEMORY_LEAK',
                'confidence': r_squared,
                'trend_slope': slope,
                'prediction': values[-1] + slope * 60  # 1 hour ahead
            }
```

**Expected Impact:** Detect issues 30-60 minutes earlier

#### F. Add Feedback Loop for Model Retraining
**Current:** Static models, no learning from diagnosis results
**Problem:** False positives don't improve over time
**Solution:** Supervised learning from labeled incidents
```python
# Add to anomaly detector
def update_from_feedback(self, anomaly_id: str, is_true_positive: bool):
    """Update model based on LLM diagnosis results"""
    # Get original features
    features = self.state.get_anomaly_features(anomaly_id)
    
    # Add to training dataset
    label = 1 if is_true_positive else 0  # 1=anomaly, 0=normal
    self.training_data.append((features, label))
    
    # Retrain periodically (every 100 samples)
    if len(self.training_data) % 100 == 0:
        self._retrain_models()
```

**Expected Impact:** 10-15% accuracy improvement per month

---

## 2. LLM Diagnosis Accuracy

### Current Implementation
- **Provider:** Groq API (llama-3.3-70b-versatile)
- **Context:** ChromaDB vector search (23 KB articles) + PostgreSQL history
- **Prompt:** Structured system prompt with incident-specific templates
- **Location:** `services/llm-diagnosis/diagnosis_service.py`

### 🎯 Quick Wins (High Impact, Low Effort)

#### A. Expand Knowledge Base
**Current:** 23 KB articles in ChromaDB
**Problem:** Limited coverage of incident types
**Solution:** Add more structured knowledge
```python
# Add to knowledge_base collection
kb_articles = [
    # Vendor-specific troubleshooting
    "Cisco IOS-XE memory leak in version 16.9.x: Known issue...",
    "Juniper BGP flapping due to keepalive timer mismatch...",
    
    # Protocol-specific
    "OSPF adjacency failure troubleshooting flowchart...",
    "BGP route dampening best practices...",
    
    # Physical layer
    "SFP transceiver compatibility matrix...",
    "Fiber cable testing procedures...",
    
    # Performance tuning
    "QoS policy templates for VoIP traffic...",
    "Buffer tuning for high-throughput links...",
]

# Organize by categories
for article in kb_articles:
    vector_service.add_document(
        collection='knowledge_base',
        document=article,
        metadata={'category': 'troubleshooting', 'verified': True}
    )
```

**Expected Impact:** 35% increase in diagnosis confidence

#### B. Improve Vector Search Quality
**Current:** Simple semantic search on entire incident description
**Problem:** Generic queries return irrelevant results
**Solution:** Multi-query search with ranking
```python
# context_builder.py
def _build_vector_search_query(self, incident: Dict) -> str:
    """Build optimized search query"""
    anomaly_types = set(a['anomaly_type'] for a in incident['anomalies'])
    device_type = incident.get('primary_device_type', 'router')
    
    # Structured query with specificity
    queries = [
        # Primary query (high weight)
        f"{' '.join(anomaly_types)} on {device_type}",
        
        # Secondary queries (medium weight)
        f"troubleshoot {incident['title']}",
        f"root cause {incident['incident_type']}",
        
        # Fallback (low weight)
        incident.get('description', '')
    ]
    
    # Search with each query, combine results
    all_results = []
    for weight, query in enumerate(queries, start=1):
        results = self.vector_kb.search(query, top_k=3)
        for r in results:
            r['relevance_score'] = r['score'] * weight
            all_results.append(r)
    
    # Deduplicate and re-rank
    unique_results = self._deduplicate_by_content(all_results)
    return sorted(unique_results, key=lambda x: x['relevance_score'], reverse=True)[:5]
```

**Expected Impact:** 30% better context relevance

#### C. Add Few-Shot Examples to Prompts
**Current:** Zero-shot prompts (no examples)
**Problem:** LLM doesn't know expected output quality
**Solution:** Include 2-3 exemplar diagnoses
```python
# prompts/system_prompts.py
FEW_SHOT_EXAMPLES = """
**Example 1: High-confidence diagnosis**
Incident: Interface flapping on core-router-01, GigabitEthernet0/1
Analysis: Physical layer issue confirmed by:
- CRC errors increasing (10K/hour)
- Light levels below threshold (-18 dBm, should be -3 dBm)
- No configuration changes in 30 days
Root Cause: Failed SFP transceiver
Confidence: 0.92
Remediation: Replace SFP, verify light levels return to normal (-3 to -5 dBm)

**Example 2: Medium-confidence diagnosis**
Incident: BGP session flapping on edge-router-02
Analysis: Session drops every 45 minutes, correlates with:
- No interface errors
- Keepalive timers: Local=60s, Peer=30s (mismatch)
- No route limit exceeded
Root Cause: BGP keepalive timer mismatch causing session timeout
Confidence: 0.75 (need to verify peer config)
Remediation: Align keepalive timers on both sides (recommend 60s/180s)

**Example 3: Low-confidence diagnosis**
Incident: Intermittent packet loss on multiple devices
Analysis: Pattern unclear:
- Affects 5 devices across 2 locations
- No correlated interface errors
- Occurs during business hours only
Root Cause: Possible bandwidth saturation OR upstream ISP issue
Confidence: 0.45 (insufficient data)
Remediation: ESCALATE - Requires packet capture analysis and ISP coordination
"""

# Add to system prompt
SYSTEM_PROMPT += f"\n\n**Examples of Good Diagnoses:**\n{FEW_SHOT_EXAMPLES}"
```

**Expected Impact:** 25% improvement in diagnosis quality

### 🚀 Advanced Improvements (High Impact, Medium Effort)

#### D. Chain-of-Thought Reasoning
**Current:** Single LLM call for diagnosis
**Problem:** Complex incidents need multi-step reasoning
**Solution:** Decompose into reasoning steps
```python
# llm_client.py
def diagnose_with_reasoning(self, context: Dict) -> Dict:
    """Multi-step reasoning process"""
    
    # Step 1: Observation - What do we know?
    observations = self._ask_llm(
        "List 5 key observations from the incident data (facts only, no interpretation):",
        context
    )
    
    # Step 2: Hypotheses - What could explain this?
    hypotheses = self._ask_llm(
        f"Given these observations:\n{observations}\n\nList 3 possible root causes (ranked by likelihood):",
        context
    )
    
    # Step 3: Evidence - Which hypothesis is strongest?
    analysis = self._ask_llm(
        f"Observations:\n{observations}\n\nHypotheses:\n{hypotheses}\n\nWhich hypothesis best explains ALL observations? Provide evidence:",
        context
    )
    
    # Step 4: Final diagnosis with confidence
    diagnosis = self._ask_llm(
        f"Based on this analysis:\n{analysis}\n\nProvide final diagnosis in JSON format:",
        context
    )
    
    return {
        'diagnosis': diagnosis,
        'reasoning_chain': {
            'observations': observations,
            'hypotheses': hypotheses,
            'analysis': analysis
        }
    }
```

**Expected Impact:** 40% improvement for complex incidents

#### E. Use Structured Output (JSON Mode)
**Current:** Free-form text parsed into JSON (error-prone)
**Problem:** ~15% of responses fail JSON parsing
**Solution:** Force JSON output with schema
```python
# llm_client.py
from pydantic import BaseModel, Field

class DiagnosisResponse(BaseModel):
    root_cause: str = Field(..., min_length=20, max_length=500)
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str
    remediation_plan: List[Dict]
    escalation_criteria: List[str]

def call_llm(self, prompt: str) -> DiagnosisResponse:
    response = self.client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        response_format={"type": "json_object"},  # Force JSON
        temperature=0.3
    )
    
    # Validate against schema
    return DiagnosisResponse.parse_raw(response.choices[0].message.content)
```

**Expected Impact:** 100% valid JSON responses, 20% faster parsing

#### F. Add Confidence Calibration
**Current:** LLM self-reports confidence (often overconfident)
**Problem:** 0.85 confidence doesn't always mean 85% accuracy
**Solution:** Calibrate based on historical accuracy
```python
# Add confidence calibration layer
class ConfidenceCalibrator:
    def __init__(self):
        self.history = []  # [(llm_confidence, actual_correct)]
    
    def calibrate(self, llm_confidence: float, incident_type: str) -> float:
        """Adjust LLM confidence based on historical accuracy"""
        # Get accuracy for similar confidence ranges
        similar = [
            actual for llm_conf, actual in self.history
            if abs(llm_conf - llm_confidence) < 0.1
        ]
        
        if len(similar) < 10:
            return llm_confidence  # Not enough data
        
        actual_accuracy = sum(similar) / len(similar)
        
        # Adjust: If LLM says 0.8 but historically 70% accurate, return 0.7
        return actual_accuracy
    
    def add_feedback(self, diagnosis_id: str, llm_confidence: float, was_correct: bool):
        """Learn from remediation outcomes"""
        self.history.append((llm_confidence, 1.0 if was_correct else 0.0))
```

**Expected Impact:** 30% better confidence accuracy

#### G. Add Multi-Model Voting
**Current:** Single LLM provider (Groq)
**Problem:** One model can miss nuances
**Solution:** Query multiple models, combine results
```python
# llm_client.py
class EnsembleLLMClient:
    def __init__(self):
        self.clients = {
            'groq': ChatGroq(model="llama-3.3-70b-versatile"),
            'openai': ChatOpenAI(model="gpt-4-turbo"),
            'anthropic': ChatAnthropic(model="claude-3-sonnet"),
        }
    
    def diagnose_with_ensemble(self, context: Dict) -> Dict:
        """Get diagnosis from multiple models, combine intelligently"""
        results = {}
        
        for name, client in self.clients.items():
            try:
                results[name] = self._get_diagnosis(client, context)
            except Exception as e:
                logger.warning(f"{name} failed: {e}")
        
        if len(results) < 2:
            return results[list(results.keys())[0]]  # Fallback to single result
        
        # Voting: If 2/3 agree on root cause, high confidence
        root_causes = [r['root_cause'] for r in results.values()]
        if len(set(root_causes)) == 1:
            # All agree
            return {
                **results['groq'],
                'confidence': min(results['groq']['confidence'] + 0.1, 1.0),
                'ensemble_agreement': 'unanimous'
            }
        else:
            # Disagreement - flag for review
            return {
                **results['groq'],  # Use primary model
                'confidence': results['groq']['confidence'] * 0.8,  # Reduce confidence
                'ensemble_agreement': 'split',
                'alternative_diagnoses': [r['root_cause'] for r in results.values()]
            }
```

**Expected Impact:** 50% improvement for ambiguous incidents

---

## 3. Remediation Accuracy

### Current Implementation
- **Framework:** LangChain + LangGraph state machine
- **Phases:** Assess → Plan → Execute → Verify → Rollback → Document
- **Tools:** 10+ network tools (show commands, config changes)
- **Location:** `services/remediation-agent/workflow.py`

### 🎯 Quick Wins (High Impact, Low Effort)

#### A. Add Pre-Execution Validation
**Current:** Actions executed immediately
**Problem:** Unsafe commands can make things worse
**Solution:** Dry-run validation
```python
# workflow.py - Before _execute_remediation_action
def _validate_action(self, state: RemediationState) -> RemediationState:
    """Validate action safety before execution"""
    action = state['remediation_plan'][state['current_action']]
    
    # Safety checks
    if action['tool'] == 'reload_interface':
        # Check if this is the only path
        redundancy = self.tools.check_redundancy(action['device'], action['interface'])
        if not redundancy['has_backup']:
            logger.warning("No redundant path available!")
            state['errors'].append("Cannot reload single path interface")
            return state  # Skip to escalate
    
    elif action['tool'] == 'restart_service':
        # Check if service is in use
        connections = self.tools.show_connections(action['device'], action['service'])
        if connections['active'] > 100:
            logger.warning(f"Service has {connections['active']} active connections")
            # Still proceed but add warning
            state['warnings'].append(f"Restarting service with {connections['active']} connections")
    
    state['action_validated'] = True
    return state
```

**Expected Impact:** 70% reduction in escalations due to unsafe actions

#### B. Improve Verification Logic
**Current:** Simple pass/fail checks
**Problem:** Doesn't detect partial success or degraded state
**Solution:** Detailed health scoring
```python
# workflow.py - Enhance _verify_remediation
def _verify_remediation(self, state: RemediationState) -> RemediationState:
    """Enhanced verification with health scoring"""
    device = state['diagnosis']['primary_device']
    interface = "GigabitEthernet0/1"  # From state
    
    # Multi-metric health check
    health = {
        'interface_status': self.tools.check_interface_status(device, interface),
        'error_rate': self.tools.get_error_rate(device, interface),
        'packet_loss': self.tools.measure_packet_loss(device),
        'latency': self.tools.measure_latency(device),
    }
    
    # Calculate health score (0-100)
    score = 0
    if health['interface_status'] == 'up':
        score += 40
    if health['error_rate'] < 0.01:  # <1% error rate
        score += 30
    if health['packet_loss'] < 0.001:  # <0.1% loss
        score += 20
    if health['latency'] < 50:  # <50ms
        score += 10
    
    logger.info(f"Health score: {score}/100")
    
    if score >= 90:
        state['verification_result'] = 'success'
    elif score >= 70:
        state['verification_result'] = 'partial'  # Improved but not perfect
        state['warnings'].append(f"Partial success (score: {score}/100)")
    else:
        state['verification_result'] = 'failed'
        state['errors'].append(f"Remediation failed (score: {score}/100)")
    
    state['health_metrics'] = health
    return state
```

**Expected Impact:** 40% better detection of partial failures

#### C. Add Learning from Outcomes
**Current:** No feedback loop to improve future actions
**Problem:** Same mistakes repeated
**Solution:** Document lessons learned
```python
# workflow.py - Add to _document_resolution
def _document_resolution(self, state: RemediationState) -> RemediationState:
    """Document what worked/didn't work for future reference"""
    
    lessons = {
        'incident_type': state['incident_type'],
        'actions_taken': len(state['action_results']),
        'successful_actions': [a for a in state['action_results'] if a['success']],
        'failed_actions': [a for a in state['action_results'] if not a['success']],
        'total_time_seconds': sum(a['duration'] for a in state['action_results']),
        'final_outcome': state['verification_result'],
    }
    
    # Generate lesson summary
    if state['verification_result'] == 'success':
        lesson = f"For {state['incident_type']}, this sequence worked: " + \
                 " → ".join([a['tool'] for a in lessons['successful_actions']])
    else:
        lesson = f"For {state['incident_type']}, these actions failed: " + \
                 ", ".join([a['tool'] for a in lessons['failed_actions']])
    
    # Save to database
    self._save_lesson_learned(state['incident_number'], lesson, lessons)
    
    # Add to vector DB for future context
    self.vector_kb.add_document(
        collection='remediation_commands',
        document=lesson,
        metadata={'incident_type': state['incident_type'], 'outcome': state['verification_result']}
    )
    
    state['lessons_learned'] = lesson
    return state
```

**Expected Impact:** 25% improvement in future remediation success

### 🚀 Advanced Improvements (High Impact, Medium Effort)

#### D. Add Simulation/Sandbox Mode
**Current:** Actions executed directly on production
**Problem:** Risky for critical infrastructure
**Solution:** Test in GNS3/EVE-NG sandbox first
```python
# tools.py
class NetworkTools:
    def __init__(self, simulation_mode: bool = True, sandbox_url: str = None):
        self.simulation_mode = simulation_mode
        self.sandbox = SandboxConnector(sandbox_url) if sandbox_url else None
    
    def reload_interface(self, device: str, interface: str):
        if self.sandbox:
            # Test in sandbox first
            result = self.sandbox.execute(device, [
                f"interface {interface}",
                "shutdown",
                "no shutdown"
            ])
            
            if not result['success']:
                logger.error(f"Sandbox test failed: {result['error']}")
                return {'success': False, 'message': 'Failed in sandbox'}
            
            logger.info("Sandbox test passed, proceeding to production")
        
        # Execute in production
        return self._execute_on_production(device, interface)
```

**Expected Impact:** 90% reduction in production incidents

#### E. Add Human-in-the-Loop for High-Risk Actions
**Current:** Fully autonomous
**Problem:** Some actions need approval
**Solution:** Pause for approval on critical actions
```python
# workflow.py
def _execute_remediation_action(self, state: RemediationState):
    action = state['remediation_plan'][state['current_action']]
    
    # Check if action requires approval
    if self._is_high_risk(action):
        logger.warning(f"High-risk action: {action['tool']} - Requesting approval")
        
        # Send approval request (webhook, Slack, PagerDuty)
        approval = self._request_approval(
            incident_number=state['incident_number'],
            action=action,
            timeout_seconds=300  # 5 minute timeout
        )
        
        if not approval['approved']:
            state['errors'].append(f"Action declined: {approval['reason']}")
            return state  # Skip to escalate
        
        logger.info(f"Action approved by {approval['approver']}")
    
    # Proceed with execution
    return self._execute_action_internal(state, action)

def _is_high_risk(self, action: Dict) -> bool:
    """Determine if action needs approval"""
    high_risk_tools = ['restart_service', 'apply_configuration', 'reload_device']
    return action['tool'] in high_risk_tools or \
           action.get('device_criticality') == 'core'
```

**Expected Impact:** 100% safety for critical actions

---

## Implementation Priority

### Week 1: Quick Wins
- [ ] Day 1: Tune anomaly detection thresholds (A, B)
- [ ] Day 2: Expand ChromaDB knowledge base (2.A)
- [ ] Day 3: Improve vector search queries (2.B)
- [ ] Day 4: Add pre-execution validation (3.A)
- [ ] Day 5: Add few-shot examples to prompts (2.C)

### Week 2: Medium Improvements
- [ ] Add time-series analysis (1.E)
- [ ] Implement chain-of-thought reasoning (2.D)
- [ ] Enhance verification logic (3.B)

### Week 3: Advanced Features
- [ ] Multi-model ML ensemble (1.D)
- [ ] Multi-model LLM voting (2.G)
- [ ] Sandbox testing mode (3.D)

### Week 4: Feedback Loops
- [ ] Model retraining from feedback (1.F)
- [ ] Confidence calibration (2.F)
- [ ] Document lessons learned (3.C)

---

## Measuring Improvement

Track these metrics in Grafana:

```yaml
Anomaly Detection:
  - False Positive Rate: <10% (currently ~20%)
  - False Negative Rate: <5% (currently ~10%)
  - Detection Latency: <100ms (currently 80ms)

LLM Diagnosis:
  - Diagnosis Confidence: >0.75 avg (currently 0.68)
  - JSON Parse Success: 100% (currently 85%)
  - Diagnosis Time: <5s (currently 3-7s)
  - Remediation Plan Quality: >80% executable (currently 65%)

Remediation:
  - Success Rate: >85% (currently 60%)
  - Escalation Rate: <20% (currently 35%)
  - Rollback Rate: <5% (currently 12%)
  - Mean Time to Repair: <15min (currently 25min)
```

---

**End of Document**
