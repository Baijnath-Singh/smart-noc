"""
Approval Workflow - Manages human approval for medium/high risk remediations
Handles notifications, timeouts, and approval decisions
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from loguru import logger


class ApprovalWorkflow:
    """Manage approval requests for autonomous remediation"""
    
    # Approval timeout settings (in minutes)
    APPROVAL_TIMEOUTS = {
        'LOW': 2,      # Low risk: 2 minutes
        'MEDIUM': 5,    # Medium risk: 5 minutes
        'HIGH': 10,     # High risk: 10 minutes
        'CRITICAL': 30  # Critical: 30 minutes (or never auto-approve)
    }
    
    def __init__(self, engine):
        self.engine = engine
        self.Session = sessionmaker(bind=engine)
    
    def request_approval(
        self,
        incident_number: int,
        request_type: str,
        risk_level: str,
        calibrated_confidence: float,
        auto_approve_off_hours: bool = True
    ) -> int:
        """
        Create approval request
        
        Args:
            incident_number: Incident number
            request_type: 'auto_remediation', 'rollback', 'escalation'
            risk_level: 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
            calibrated_confidence: Confidence score (0.0-1.0)
            auto_approve_off_hours: Auto-approve after timeout during off-hours
        
        Returns:
            approval_id
        """
        try:
            # Calculate expiry time
            timeout_minutes = self.APPROVAL_TIMEOUTS.get(risk_level, 5)
            expires_at = datetime.now() + timedelta(minutes=timeout_minutes)
            
            # Set auto-approve window for off-hours
            auto_approve_after = timedelta(minutes=timeout_minutes) if auto_approve_off_hours else None
            
            with self.Session() as session:
                result = session.execute(
                    text("""
                        INSERT INTO remediation_approvals (
                            incident_number,
                            request_type,
                            risk_level,
                            calibrated_confidence,
                            expires_at,
                            auto_approve_after
                        ) VALUES (
                            :incident_number,
                            :request_type,
                            :risk_level,
                            :calibrated_confidence,
                            :expires_at,
                            :auto_approve_after
                        )
                        RETURNING id
                    """),
                    {
                        'incident_number': incident_number,
                        'request_type': request_type,
                        'risk_level': risk_level,
                        'calibrated_confidence': calibrated_confidence,
                        'expires_at': expires_at,
                        'auto_approve_after': auto_approve_after
                    }
                )
                approval_id = result.scalar()
                session.commit()
                
                logger.info(
                    f"📝 Approval request created (ID: {approval_id}) for incident #{incident_number} "
                    f"(risk: {risk_level}, expires: {expires_at.strftime('%H:%M:%S')})"
                )
                
                # Send notification (simulated)
                self._send_notification(approval_id, incident_number, risk_level, expires_at)
                
                return approval_id
                
        except Exception as e:
            logger.error(f"Failed to create approval request: {e}")
            raise
    
    def _send_notification(
        self,
        approval_id: int,
        incident_number: int,
        risk_level: str,
        expires_at: datetime
    ):
        """
        Send approval notification to NOC engineers
        
        In production, this would:
        - Send Slack message
        - Send email
        - Trigger PagerDuty alert for CRITICAL
        - Include incident details and approval link
        
        For now, we'll just log it
        """
        notification_message = (
            f"🚨 APPROVAL REQUIRED\n"
            f"   Incident: #{incident_number}\n"
            f"   Risk: {risk_level}\n"
            f"   Expires: {expires_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"   Approval ID: {approval_id}"
        )
        
        logger.warning(notification_message)
        
        # Update notification status in database
        try:
            with self.Session() as session:
                session.execute(
                    text("""
                        UPDATE remediation_approvals
                        SET notification_sent = true,
                            notification_channel = 'log',
                            notification_id = :notification_id
                        WHERE id = :approval_id
                    """),
                    {
                        'approval_id': approval_id,
                        'notification_id': f"log_{approval_id}"
                    }
                )
                session.commit()
        except Exception as e:
            logger.error(f"Failed to update notification status: {e}")
    
    def approve_request(
        self,
        approval_id: int,
        approved_by: str,
        decision_reason: Optional[str] = None
    ) -> bool:
        """
        Approve a remediation request
        
        Returns:
            True if approval successful
        """
        try:
            with self.Session() as session:
                result = session.execute(
                    text("""
                        UPDATE remediation_approvals
                        SET status = 'approved',
                            approved_by = :approved_by,
                            approved_at = NOW(),
                            decision_reason = :decision_reason
                        WHERE id = :approval_id
                          AND status = 'pending'
                        RETURNING incident_number
                    """),
                    {
                        'approval_id': approval_id,
                        'approved_by': approved_by,
                        'decision_reason': decision_reason or 'Approved by NOC engineer'
                    }
                )
                incident_number = result.scalar()
                session.commit()
                
                if incident_number:
                    logger.success(
                        f"✅ Approval {approval_id} APPROVED by {approved_by} "
                        f"for incident #{incident_number}"
                    )
                    return True
                else:
                    logger.warning(f"Approval {approval_id} not found or already processed")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to approve request: {e}")
            return False
    
    def reject_request(
        self,
        approval_id: int,
        rejected_by: str,
        decision_reason: str
    ) -> bool:
        """
        Reject a remediation request
        
        Returns:
            True if rejection successful
        """
        try:
            with self.Session() as session:
                result = session.execute(
                    text("""
                        UPDATE remediation_approvals
                        SET status = 'rejected',
                            approved_by = :rejected_by,
                            approved_at = NOW(),
                            decision_reason = :decision_reason
                        WHERE id = :approval_id
                          AND status = 'pending'
                        RETURNING incident_number
                    """),
                    {
                        'approval_id': approval_id,
                        'rejected_by': rejected_by,
                        'decision_reason': decision_reason
                    }
                )
                incident_number = result.scalar()
                session.commit()
                
                if incident_number:
                    logger.warning(
                        f"❌ Approval {approval_id} REJECTED by {rejected_by} "
                        f"for incident #{incident_number}: {decision_reason}"
                    )
                    return True
                else:
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to reject request: {e}")
            return False
    
    def check_pending_approvals(self) -> list:
        """
        Check for pending approvals and handle timeouts
        
        Returns:
            List of pending approval IDs
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT id, incident_number, risk_level, expires_at, auto_approve_after
                        FROM remediation_approvals
                        WHERE status = 'pending'
                          AND expires_at > NOW()
                        ORDER BY requested_at
                    """)
                ).fetchall()
                
                pending_approvals = []
                for row in result:
                    approval_info = {
                        'id': row[0],
                        'incident_number': row[1],
                        'risk_level': row[2],
                        'expires_at': row[3],
                        'auto_approve_after': row[4]
                    }
                    pending_approvals.append(approval_info)
                
                return pending_approvals
                
        except Exception as e:
            logger.error(f"Failed to check pending approvals: {e}")
            return []
    
    def get_approval_status(self, approval_id: int) -> Optional[Dict[str, Any]]:
        """Get status of an approval request"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT 
                            id, incident_number, request_type, risk_level,
                            calibrated_confidence, status, approved_by,
                            approved_at, decision_reason, expires_at
                        FROM remediation_approvals
                        WHERE id = :approval_id
                    """),
                    {'approval_id': approval_id}
                ).fetchone()
                
                if not result:
                    return None
                
                return {
                    'id': result[0],
                    'incident_number': result[1],
                    'request_type': result[2],
                    'risk_level': result[3],
                    'calibrated_confidence': float(result[4]) if result[4] else None,
                    'status': result[5],
                    'approved_by': result[6],
                    'approved_at': result[7],
                    'decision_reason': result[8],
                    'expires_at': result[9]
                }
        except Exception as e:
            logger.error(f"Failed to get approval status: {e}")
            return None


if __name__ == '__main__':
    # Test approval workflow
    from sqlalchemy import create_engine
    
    DATABASE_URL = "postgresql://noc_admin:noc_admin_password@localhost:5432/smart_noc"
    engine = create_engine(DATABASE_URL)
    
    workflow = ApprovalWorkflow(engine)
    
    print("\n✅ Testing Approval Workflow:")
    
    # Test approval request
    approval_id = workflow.request_approval(
        incident_number=999,
        request_type='auto_remediation',
        risk_level='MEDIUM',
        calibrated_confidence=0.82,
        auto_approve_off_hours=True
    )
    print(f"   Created approval request ID: {approval_id}")
    
    # Check status
    status = workflow.get_approval_status(approval_id)
    print(f"   Status: {status['status']}")
    print(f"   Expires: {status['expires_at']}")
    
    # Test approval
    approved = workflow.approve_request(
        approval_id=approval_id,
        approved_by='test_engineer@example.com',
        decision_reason='Approved for testing'
    )
    print(f"   Approval result: {'✓ SUCCESS' if approved else '✗ FAILED'}")
    
    # Check pending
    pending = workflow.check_pending_approvals()
    print(f"   Pending approvals: {len(pending)}")
