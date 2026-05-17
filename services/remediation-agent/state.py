"""
State definitions for the autonomous remediation workflow
"""
from typing import Dict, List, Any, TypedDict, Literal


class RemediationState(TypedDict):
    """
    State that flows through the remediation workflow
    
    This tracks the entire troubleshooting and remediation process,
    similar to how a network engineer would document their work.
    """
    
    # Input from diagnosis service
    incident_id: str
    incident_number: int
    incident_type: str
    diagnosis: Dict[str, Any]  # Root cause, confidence, etc.
    
    # Workflow state
    current_phase: Literal[
        "planning",
        "investigation", 
        "remediation",
        "verification",
        "rollback",
        "completed",
        "escalated"
    ]
    
    # Investigation findings
    investigation_steps: List[Dict[str, Any]]  # What we checked
    evidence: List[Dict[str, Any]]  # What we found
    hypothesis: str  # Current theory about the problem
    confidence: float  # How confident are we?
    
    # Remediation tracking
    remediation_plan: List[Dict[str, Any]]  # Steps to fix
    actions_taken: List[Dict[str, Any]]  # What we've done
    current_action: int  # Which step we're on
    
    # Results
    verification_results: List[Dict[str, Any]]  # Did fixes work?
    success: bool
    resolution_time_seconds: float
    
    # Error handling
    errors: List[str]
    retry_count: int
    rollback_performed: bool
    
    # Learning
    lessons_learned: str  # What did we learn?
    should_update_kb: bool  # Should we add this to knowledge base?


class ActionResult(TypedDict):
    """Result of executing a single action"""
    action_type: str
    device: str
    command: str
    success: bool
    output: str
    execution_time: float
    error: str | None
