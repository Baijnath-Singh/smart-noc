"""
Safety Framework Integration for Remediation Agent

This module integrates the Safety Framework into the remediation workflow,
providing risk assessment, decision-making, and safe execution capabilities.
"""
from typing import Dict, Tuple, Any
from sqlalchemy import create_engine
from loguru import logger

from risk_assessor import RiskAssessor
from autonomous_executor import AutonomousExecutor
from rollback_manager import RollbackManager
from approval_workflow import ApprovalWorkflow


class SafetyIntegration:
    """
    Integrates Safety Framework into remediation workflow
    
    This provides:
    - Risk assessment based on device, blast radius, time, complexity
    - Decision matrix evaluation (execute, require approval, manual only)
    - Pre-remediation snapshots
    - Safe execution with rollback capability
    """
    
    def __init__(self, database_url: str):
        """
        Initialize safety components with database connection
        
        Args:
            database_url: PostgreSQL connection string
        """
        self.engine = create_engine(database_url, pool_pre_ping=True)
        
        # Initialize safety components
        self.risk_assessor = RiskAssessor(self.engine)
        self.autonomous_executor = AutonomousExecutor(self.engine)
        self.rollback_manager = RollbackManager(self.engine)
        self.approval_workflow = ApprovalWorkflow(self.engine)
        
        logger.info("✅ Safety Framework integration initialized")
    
    def assess_safety(
        self,
        incident: Dict[str, Any],
        diagnosis: Dict[str, Any],
        calibrated_confidence: float
    ) -> Dict[str, Any]:
        """
        Perform complete safety assessment for a remediation
        
        Args:
            incident: Incident details (number, device, type, etc.)
            diagnosis: LLM diagnosis with remediation plan
            calibrated_confidence: Calibrated confidence from three-layer system
        
        Returns:
            Safety assessment with:
            - risk_level: LOW/MEDIUM/HIGH/CRITICAL
            - risk_score: 0.0-1.0
            - decision: execute/execute_notify/require_approval/manual_only
            - decision_reasoning: Why this decision was made
            - factors: Breakdown of risk factors
            - safe_to_proceed: Boolean
        """
        try:
            # Step 1: Assess risk
            risk_level, risk_score, factors = self.risk_assessor.assess_risk(
                incident, diagnosis
            )
            
            logger.info(
                f"📊 Risk Assessment: {risk_level} (score: {risk_score:.2f}) "
                f"for incident #{incident.get('incident_number', 'unknown')}"
            )
            
            # Save risk assessment to database
            self.risk_assessor.save_risk_assessment(
                incident['incident_number'],
                risk_level,
                risk_score,
                factors
            )
            
            # Step 2: Make decision based on risk + confidence
            # Add calibrated_confidence to diagnosis dict for decision making
            diagnosis_with_confidence = {**diagnosis, 'calibrated_confidence': calibrated_confidence}
            risk_assessment = {'risk_level': risk_level, 'risk_score': risk_score}
            
            decision, reasoning, metadata = self.autonomous_executor.decide_action(
                incident=incident,
                diagnosis=diagnosis_with_confidence,
                risk_assessment=risk_assessment
            )
            
            logger.info(
                f"🤖 Decision: {decision} - {reasoning}"
            )
            
            # Step 3: Determine if we can proceed
            safe_to_proceed = decision in ['execute', 'execute_notify']
            
            return {
                'risk_level': risk_level,
                'risk_score': risk_score,
                'decision': decision,
                'decision_reasoning': reasoning,
                'factors': factors,
                'safe_to_proceed': safe_to_proceed,
                'requires_approval': decision == 'require_approval',
                'must_escalate': decision == 'manual_only'
            }
            
        except Exception as e:
            logger.error(f"Safety assessment failed: {e}")
            # Conservative fallback: require manual intervention
            return {
                'risk_level': 'UNKNOWN',
                'risk_score': 1.0,
                'decision': 'manual_only',
                'decision_reasoning': f'Safety assessment failed: {e}',
                'factors': {},
                'safe_to_proceed': False,
                'requires_approval': False,
                'must_escalate': True
            }
    
    def create_pre_remediation_snapshot(
        self,
        incident_number: int,
        device_name: str,
        current_config: str
    ) -> int:
        """
        Create configuration snapshot before remediation
        
        Args:
            incident_number: Incident ID
            device_name: Device to snapshot
            current_config: Current device configuration
        
        Returns:
            snapshot_id: ID of created snapshot
        """
        try:
            snapshot_id = self.rollback_manager.create_snapshot(
                incident_number=incident_number,
                device_name=device_name,
                snapshot_type='pre_remediation',
                configuration=current_config,
                metadata={
                    'triggered_by': 'remediation_agent',
                    'purpose': 'pre_remediation_backup'
                }
            )
            
            logger.info(
                f"📸 Snapshot created: ID={snapshot_id} for {device_name} "
                f"(incident #{incident_number})"
            )
            
            return snapshot_id
            
        except Exception as e:
            logger.error(f"Failed to create snapshot: {e}")
            raise
    
    def execute_with_rollback(
        self,
        incident_number: int,
        snapshot_id: int,
        remediation_commands: list,
        device_name: str
    ) -> Dict[str, Any]:
        """
        Execute remediation with automatic rollback on failure
        
        Args:
            incident_number: Incident ID
            snapshot_id: Pre-remediation snapshot ID
            remediation_commands: List of commands to execute
            device_name: Device being remediated
        
        Returns:
            Execution result with success status and details
        """
        try:
            # Execute remediation (simulated in this version)
            logger.info(f"🔧 Executing remediation on {device_name}...")
            
            # In production, this would actually execute commands
            # For now, simulate success
            execution_result = {
                'success': True,
                'commands_executed': remediation_commands,
                'outputs': ['Command executed successfully'] * len(remediation_commands)
            }
            
            if execution_result['success']:
                logger.success(f"✅ Remediation successful on {device_name}")
                return {
                    'success': True,
                    'snapshot_id': snapshot_id,
                    'rollback_performed': False
                }
            else:
                # Remediation failed, trigger rollback
                logger.warning(f"⚠️ Remediation failed, initiating rollback...")
                
                rollback_success = self.rollback_manager.execute_rollback(
                    incident_number=incident_number,
                    snapshot_id=snapshot_id,
                    rollback_reason='remediation_failed',
                    triggered_by='remediation_agent_automatic'
                )
                
                if rollback_success:
                    logger.success("✅ Rollback successful, device restored")
                else:
                    logger.error("❌ Rollback failed! Manual intervention required")
                
                return {
                    'success': False,
                    'snapshot_id': snapshot_id,
                    'rollback_performed': True,
                    'rollback_success': rollback_success,
                    'error': 'Remediation failed, rolled back to previous state'
                }
                
        except Exception as e:
            logger.error(f"Execution with rollback failed: {e}")
            return {
                'success': False,
                'snapshot_id': snapshot_id,
                'rollback_performed': False,
                'error': str(e)
            }
    
    def request_approval(
        self,
        incident_number: int,
        risk_level: str,
        calibrated_confidence: float,
        timeout_minutes: int = 5
    ) -> int:
        """
        Request human approval for medium/high-risk remediation
        
        Args:
            incident_number: Incident ID
            risk_level: Risk level assessment
            calibrated_confidence: Confidence score
            timeout_minutes: Minutes before timeout
        
        Returns:
            approval_id: ID of approval request
        """
        try:
            approval_id = self.approval_workflow.request_approval(
                incident_number=incident_number,
                risk_level=risk_level,
                calibrated_confidence=calibrated_confidence,
                timeout_minutes=timeout_minutes
            )
            
            logger.info(
                f"📋 Approval requested: ID={approval_id} for incident #{incident_number} "
                f"(timeout: {timeout_minutes} min)"
            )
            
            return approval_id
            
        except Exception as e:
            logger.error(f"Failed to request approval: {e}")
            raise
    
    def check_approval_status(self, approval_id: int) -> Tuple[str, str]:
        """
        Check status of approval request
        
        Args:
            approval_id: Approval request ID
        
        Returns:
            (status, approved_by): Status and approver
        """
        return self.approval_workflow.check_approval_status(approval_id)
