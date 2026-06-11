"""
Autonomous Executor - Core decision engine for autonomous remediation
Implements safety-first decision matrix based on confidence + risk
"""

import json
from typing import Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from loguru import logger

from risk_assessor import RiskAssessor
from rollback_manager import RollbackManager
from approval_workflow import ApprovalWorkflow


class AutonomousExecutor:
    """
    Core autonomous execution engine
    
    Decision Matrix:
    ┌─────────────┬─────────┬──────────┬──────────┬──────────┐
    │ Confidence  │   LOW   │  MEDIUM  │   HIGH   │ CRITICAL │
    ├─────────────┼─────────┼──────────┼──────────┼──────────┤
    │ 0.95-1.00   │ Execute │ Approval │ Approval │  Manual  │
    │ 0.90-0.95   │ Execute │ Approval │ Approval │  Manual  │
    │ 0.85-0.90   │ Notify  │ Approval │ Approval │  Manual  │
    │ 0.75-0.85   │ Notify  │ Approval │  Manual  │  Manual  │
    │ <0.75       │ Manual  │  Manual  │  Manual  │  Manual  │
    └─────────────┴─────────┴──────────┴──────────┴──────────┘
    
    Actions:
    - Execute: Auto-execute immediately
    - Notify: Execute + send notification
    - Approval: Request approval (with timeout)
    - Manual: Requires manual intervention
    """
    
    def __init__(self, engine):
        self.engine = engine
        self.Session = sessionmaker(bind=engine)
        self.risk_assessor = RiskAssessor(engine)
        self.rollback_manager = RollbackManager(engine)
        self.approval_workflow = ApprovalWorkflow(engine)
    
    def decide_action(
        self,
        incident: Dict[str, Any],
        diagnosis: Dict[str, Any],
        risk_assessment: Dict[str, Any]
    ) -> Tuple[str, str, Dict[str, Any]]:
        """
        Decide what action to take based on confidence + risk
        
        Args:
            incident: Incident data
            diagnosis: Diagnosis data with calibrated_confidence
            risk_assessment: Risk assessment with risk_level, risk_score
        
        Returns:
            (decision, reasoning, metadata)
            decision: 'execute', 'execute_notify', 'require_approval', 'manual_only'
        """
        calibrated_confidence = diagnosis.get('calibrated_confidence', 0.0)
        risk_level = risk_assessment.get('risk_level', 'MEDIUM')
        incident_number = incident.get('incident_number')
        
        # Decision matrix implementation
        decision = None
        reasoning = None
        rule_matched = None
        
        # CRITICAL risk: Always manual (except extremely high confidence)
        if risk_level == 'CRITICAL':
            if calibrated_confidence >= 0.98:
                decision = 'require_approval'
                reasoning = "Critical risk requires approval even at very high confidence"
                rule_matched = 'critical_risk_approval'
            else:
                decision = 'manual_only'
                reasoning = "Critical risk requires manual intervention"
                rule_matched = 'critical_risk_manual'
        
        # HIGH risk: Approval required for most, manual for low confidence
        elif risk_level == 'HIGH':
            if calibrated_confidence >= 0.85:
                decision = 'require_approval'
                reasoning = "High risk requires approval despite good confidence"
                rule_matched = 'high_risk_approval'
            else:
                decision = 'manual_only'
                reasoning = "High risk + lower confidence requires manual intervention"
                rule_matched = 'high_risk_manual'
        
        # MEDIUM risk: Approval for most, execute for very high confidence
        elif risk_level == 'MEDIUM':
            if calibrated_confidence >= 0.90:
                decision = 'require_approval'
                reasoning = "Medium risk with high confidence - requesting approval"
                rule_matched = 'medium_risk_high_confidence'
            elif calibrated_confidence >= 0.75:
                decision = 'require_approval'
                reasoning = "Medium risk with moderate confidence - approval required"
                rule_matched = 'medium_risk_approval'
            else:
                decision = 'manual_only'
                reasoning = "Medium risk + low confidence requires manual intervention"
                rule_matched = 'medium_risk_manual'
        
        # LOW risk: Can auto-execute with good confidence
        elif risk_level == 'LOW':
            if calibrated_confidence >= 0.90:
                decision = 'execute'
                reasoning = "Low risk + high confidence - safe to auto-execute"
                rule_matched = 'low_risk_high_confidence'
            elif calibrated_confidence >= 0.85:
                decision = 'execute_notify'
                reasoning = "Low risk + good confidence - execute with notification"
                rule_matched = 'low_risk_notify'
            elif calibrated_confidence >= 0.75:
                decision = 'execute_notify'
                reasoning = "Low risk + moderate confidence - execute with close monitoring"
                rule_matched = 'low_risk_moderate'
            else:
                decision = 'manual_only'
                reasoning = "Even low risk requires manual review at low confidence"
                rule_matched = 'low_risk_manual'
        
        else:
            decision = 'manual_only'
            reasoning = f"Unknown risk level: {risk_level}"
            rule_matched = 'unknown_risk'
        
        # Log decision
        metadata = {
            'calibrated_confidence': calibrated_confidence,
            'risk_level': risk_level,
            'risk_score': risk_assessment.get('risk_score', 0.0),
            'rule_matched': rule_matched,
            'decision_time': datetime.now().isoformat()
        }
        
        logger.info(
            f"🤖 Autonomous Decision for incident #{incident_number}: {decision.upper()}\n"
            f"   Confidence: {calibrated_confidence:.2f} | Risk: {risk_level} ({risk_assessment.get('risk_score', 0):.2f})\n"
            f"   Reasoning: {reasoning}"
        )
        
        # Store decision in audit log
        self._log_decision(
            incident_number=incident_number,
            decision_type='remediation_decision',
            calibrated_confidence=calibrated_confidence,
            risk_level=risk_level,
            decision=decision,
            decision_reasoning=reasoning,
            rule_matched=rule_matched,
            metadata=metadata
        )
        
        return decision, reasoning, metadata
    
    def execute_remediation(
        self,
        incident: Dict[str, Any],
        diagnosis: Dict[str, Any],
        decision_metadata: Dict[str, Any],
        approval_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute autonomous remediation
        
        This is a SIMULATED execution for the prototype.
        In production, this would:
        1. Take configuration snapshot (pre-remediation)
        2. Execute each remediation step
        3. Verify execution success
        4. Take post-remediation snapshot
        5. Run validation tests
        6. Rollback if verification fails
        
        Returns:
            execution_result with status, success, duration, etc.
        """
        incident_number = incident.get('incident_number')
        device_name = incident.get('primary_device', 'unknown')
        remediation_plan = diagnosis.get('remediation_plan', [])
        
        logger.info(f"🚀 Starting autonomous remediation for incident #{incident_number}")
        
        execution_start = datetime.now()
        execution_result = {
            'incident_number': incident_number,
            'status': 'in_progress',
            'success': False,
            'started_at': execution_start,
            'steps_executed': 0,
            'steps_total': len(remediation_plan)
        }
        
        try:
            # Step 1: Take pre-remediation snapshot
            logger.info(f"📸 Taking pre-remediation snapshot for {device_name}")
            
            # Simulate getting device configuration
            simulated_config = self._get_device_config(device_name)
            
            snapshot_id = self.rollback_manager.create_snapshot(
                incident_number=incident_number,
                device_name=device_name,
                configuration=simulated_config,
                snapshot_type='pre_remediation',
                metadata={'autonomous_execution': True}
            )
            
            execution_result['pre_snapshot_id'] = snapshot_id
            execution_result['rollback_available'] = True
            
            # Step 2: Execute remediation steps (SIMULATED)
            logger.info(f"⚙️ Executing {len(remediation_plan)} remediation steps")
            
            executed_commands = []
            for i, step in enumerate(remediation_plan, 1):
                command = step.get('command', '')
                action = step.get('action', '')
                
                logger.debug(f"   Step {i}/{len(remediation_plan)}: {action}")
                
                # SIMULATED: In production, execute actual command
                # For now, we'll simulate successful execution
                import time
                time.sleep(0.1)  # Simulate command execution time
                
                executed_commands.append({
                    'step': i,
                    'command': command,
                    'action': action,
                    'status': 'success',
                    'output': f"Simulated: {command}"
                })
                
                execution_result['steps_executed'] = i
            
            # Step 3: Verify execution success (SIMULATED)
            logger.info(f"✓ Verifying remediation success")
            
            verification_passed = True  # Simulate successful verification
            verification_details = {
                'checks_performed': ['interface_status', 'connectivity', 'errors'],
                'checks_passed': 3,
                'checks_failed': 0
            }
            
            # Step 4: Take post-remediation snapshot
            logger.info(f"📸 Taking post-remediation snapshot")
            
            simulated_config_after = self._get_device_config(device_name, after=True)
            
            post_snapshot_id = self.rollback_manager.create_snapshot(
                incident_number=incident_number,
                device_name=device_name,
                configuration=simulated_config_after,
                snapshot_type='post_remediation',
                metadata={'autonomous_execution': True, 'verification_passed': verification_passed}
            )
            
            execution_result['post_snapshot_id'] = post_snapshot_id
            
            # Step 5: Finalize execution
            execution_end = datetime.now()
            duration = int((execution_end - execution_start).total_seconds())
            
            execution_result.update({
                'status': 'completed',
                'success': True,
                'completed_at': execution_end,
                'duration_seconds': duration,
                'verification_passed': verification_passed,
                'verification_details': verification_details,
                'executed_commands': executed_commands
            })
            
            logger.success(
                f"✅ Autonomous remediation COMPLETED for incident #{incident_number} "
                f"(took {duration}s, {len(executed_commands)} steps)"
            )
            
            # Update incident status
            self._update_incident_status(
                incident_number=incident_number,
                status='resolved',
                resolution_notes='Resolved by autonomous remediation',
                execution_result=execution_result
            )
            
            return execution_result
            
        except Exception as e:
            logger.error(f"❌ Autonomous remediation FAILED for incident #{incident_number}: {e}")
            
            execution_result.update({
                'status': 'failed',
                'success': False,
                'error_message': str(e),
                'completed_at': datetime.now()
            })
            
            # Attempt rollback if snapshot was taken
            if execution_result.get('pre_snapshot_id'):
                logger.warning(f"🔄 Attempting automatic rollback...")
                
                rollback_success = self.rollback_manager.execute_rollback(
                    incident_number=incident_number,
                    snapshot_id=execution_result['pre_snapshot_id'],
                    rollback_reason='autonomous_execution_failed',
                    triggered_by='autonomous_executor'
                )
                
                execution_result['rollback_attempted'] = True
                execution_result['rollback_success'] = rollback_success
            
            return execution_result
    
    def _get_device_config(self, device_name: str, after: bool = False) -> str:
        """
        Simulate getting device configuration
        In production, this would SSH/NETCONF to device
        """
        config = f"""!
! Configuration for {device_name}
! Generated: {datetime.now().isoformat()}
! Status: {'post-remediation' if after else 'pre-remediation'}
!
hostname {device_name}
!
interface GigabitEthernet0/1
 description Sample interface
 switchport mode {'trunk' if after else 'access'}
 switchport {'trunk allowed vlan all' if after else 'access vlan 100'}
!
end
"""
        return config
    
    def _log_decision(
        self,
        incident_number: int,
        decision_type: str,
        calibrated_confidence: float,
        risk_level: str,
        decision: str,
        decision_reasoning: str,
        rule_matched: str,
        metadata: Dict[str, Any]
    ):
        """Log decision to autonomous_decision_log"""
        try:
            with self.Session() as session:
                session.execute(
                    text("""
                        INSERT INTO autonomous_decision_log (
                            incident_number,
                            decision_type,
                            calibrated_confidence,
                            risk_level,
                            decision,
                            decision_reasoning,
                            rule_matched,
                            metadata
                        ) VALUES (
                            :incident_number,
                            :decision_type,
                            :calibrated_confidence,
                            :risk_level,
                            :decision,
                            :decision_reasoning,
                            :rule_matched,
                            :metadata
                        )
                    """),
                    {
                        'incident_number': incident_number,
                        'decision_type': decision_type,
                        'calibrated_confidence': calibrated_confidence,
                        'risk_level': risk_level,
                        'decision': decision,
                        'decision_reasoning': decision_reasoning,
                        'rule_matched': rule_matched,
                        'metadata': json.dumps(metadata)
                    }
                )
                session.commit()
        except Exception as e:
            logger.error(f"Failed to log decision: {e}")
    
    def _update_incident_status(
        self,
        incident_number: int,
        status: str,
        resolution_notes: str,
        execution_result: Dict[str, Any]
    ):
        """Update incident status after remediation"""
        try:
            with self.Session() as session:
                session.execute(
                    text("""
                        UPDATE incidents
                        SET status = :status,
                            resolution_notes = :resolution_notes,
                            resolved_at = NOW(),
                            autonomous_resolution = true
                        WHERE incident_number = :incident_number
                    """),
                    {
                        'incident_number': incident_number,
                        'status': status,
                        'resolution_notes': resolution_notes
                    }
                )
                session.commit()
                logger.info(f"✓ Incident #{incident_number} status updated to: {status}")
        except Exception as e:
            logger.error(f"Failed to update incident status: {e}")


if __name__ == '__main__':
    # Test autonomous executor
    from sqlalchemy import create_engine
    
    DATABASE_URL = "postgresql://noc_admin:noc_admin_password@localhost:5432/smart_noc"
    engine = create_engine(DATABASE_URL)
    
    executor = AutonomousExecutor(engine)
    
    print("\n✅ Testing Autonomous Executor:")
    
    # Test decision matrix with different scenarios
    test_scenarios = [
        {
            'name': 'Low risk + high confidence',
            'incident': {'incident_number': 1001, 'primary_device': 'test-switch-01'},
            'diagnosis': {'calibrated_confidence': 0.95, 'remediation_plan': []},
            'risk': {'risk_level': 'LOW', 'risk_score': 0.25}
        },
        {
            'name': 'Medium risk + high confidence',
            'incident': {'incident_number': 1002, 'primary_device': 'test-switch-02'},
            'diagnosis': {'calibrated_confidence': 0.90, 'remediation_plan': []},
            'risk': {'risk_level': 'MEDIUM', 'risk_score': 0.50}
        },
        {
            'name': 'High risk + high confidence',
            'incident': {'incident_number': 1003, 'primary_device': 'test-router-01'},
            'diagnosis': {'calibrated_confidence': 0.92, 'remediation_plan': []},
            'risk': {'risk_level': 'HIGH', 'risk_score': 0.75}
        },
        {
            'name': 'Critical risk',
            'incident': {'incident_number': 1004, 'primary_device': 'core-router-01'},
            'diagnosis': {'calibrated_confidence': 0.95, 'remediation_plan': []},
            'risk': {'risk_level': 'CRITICAL', 'risk_score': 0.95}
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\n📊 Scenario: {scenario['name']}")
        decision, reasoning, metadata = executor.decide_action(
            scenario['incident'],
            scenario['diagnosis'],
            scenario['risk']
        )
        print(f"   Decision: {decision}")
        print(f"   Rule: {metadata['rule_matched']}")
