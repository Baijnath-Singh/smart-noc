"""
Safety Framework - Autonomous Remediation Safety System

Components:
- RiskAssessor: Evaluates remediation risk (device criticality, blast radius, time sensitivity, change complexity)
- RollbackManager: Configuration snapshots and rollback capability
- ApprovalWorkflow: Human approval for medium/high risk remediations
- AutonomousExecutor: Core decision engine and remediation execution

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
"""

from .risk_assessor import RiskAssessor
from .rollback_manager import RollbackManager
from .approval_workflow import ApprovalWorkflow
from .autonomous_executor import AutonomousExecutor

__all__ = [
    'RiskAssessor',
    'RollbackManager',
    'ApprovalWorkflow',
    'AutonomousExecutor'
]

__version__ = '1.0.0'
