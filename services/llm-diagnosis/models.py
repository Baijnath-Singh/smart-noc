"""
Pydantic Models for LLM Diagnosis
Ensures structured, validated responses from LLM
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum


class RemediationPriority(str, Enum):
    """Priority levels for remediation steps"""
    IMMEDIATE = "IMMEDIATE"  # 0-5 minutes
    SHORT_TERM = "SHORT_TERM"  # 5-30 minutes
    LONG_TERM = "LONG_TERM"  # Post-incident
    MONITORING = "MONITORING"  # Continuous monitoring


class RemediationStep(BaseModel):
    """Single remediation step with validation"""
    priority: RemediationPriority = Field(
        description="Urgency level (IMMEDIATE, SHORT_TERM, LONG_TERM, MONITORING)"
    )
    step: int = Field(
        ge=1,
        description="Step number (sequential, starting from 1)"
    )
    action: str = Field(
        min_length=10,
        max_length=500,
        description="Detailed action to take"
    )
    command: Optional[str] = Field(
        default=None,
        max_length=200,
        description="CLI command to execute (optional)"
    )
    expected_outcome: str = Field(
        min_length=5,
        max_length=300,
        description="What should happen after this step"
    )
    duration_minutes: int = Field(
        ge=1,
        le=120,
        description="Estimated time to complete (1-120 minutes)"
    )
    rollback_command: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Command to revert this change if needed"
    )
    
    @field_validator('command', 'rollback_command')
    @classmethod
    def validate_command(cls, v: Optional[str]) -> Optional[str]:
        """Validate CLI commands don't contain dangerous operations"""
        if v is None:
            return v
        
        # Check for dangerous commands (for autonomous execution safety)
        dangerous_keywords = ['rm ', 'delete', 'format', 'erase', 'write erase']
        v_lower = v.lower()
        for keyword in dangerous_keywords:
            if keyword in v_lower:
                raise ValueError(f"Dangerous command detected: '{keyword}' not allowed")
        
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "priority": "IMMEDIATE",
                "step": 1,
                "action": "Verify BGP neighbor status on primary device",
                "command": "show ip bgp summary",
                "expected_outcome": "BGP neighbor in Established state",
                "duration_minutes": 2,
                "rollback_command": None
            }
        }


class IncidentSeverity(str, Enum):
    """Incident severity levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DiagnosisResponse(BaseModel):
    """
    Complete LLM diagnosis response with validation
    
    This enforces:
    - All required fields are present
    - Types are correct (float confidence, not "high")
    - Value ranges are valid (confidence 0.0-1.0)
    - Remediation steps follow structure
    - No missing or malformed data
    """
    root_cause: str = Field(
        min_length=20,
        max_length=1000,
        description="Detailed technical root cause explanation"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0-1.0)"
    )
    reasoning: str = Field(
        min_length=50,
        max_length=2000,
        description="Step-by-step analysis explaining the diagnosis"
    )
    remediation_plan: List[RemediationStep] = Field(
        min_length=1,
        max_length=15,
        description="Ordered list of remediation steps (1-15 steps)"
    )
    affected_components: Optional[List[str]] = Field(
        default=None,
        description="List of affected network components (interfaces, protocols, etc.)"
    )
    escalation_needed: bool = Field(
        default=False,
        description="Whether this incident requires vendor/senior engineer escalation"
    )
    estimated_resolution_minutes: Optional[int] = Field(
        default=None,
        ge=1,
        le=480,
        description="Total estimated time to resolve (1-480 minutes)"
    )
    
    @field_validator('root_cause', 'reasoning')
    @classmethod
    def validate_technical_content(cls, v: str, info) -> str:
        """Ensure root_cause and reasoning are meaningful"""
        # Check for generic/placeholder responses
        generic_phrases = [
            'unknown issue',
            'not sure',
            'cannot determine',
            'insufficient data',
            'needs more information'
        ]
        v_lower = v.lower()
        
        # For low confidence (<0.5), generic phrases are acceptable
        # But for high confidence, we expect detailed technical analysis
        for phrase in generic_phrases:
            if phrase in v_lower and len(v) < 100:
                raise ValueError(
                    f"Response too generic: '{phrase}' found with insufficient detail"
                )
        
        return v
    
    @model_validator(mode='after')
    def validate_consistency(self) -> 'DiagnosisResponse':
        """Cross-field validation"""
        # High confidence should have detailed reasoning
        if self.confidence >= 0.8 and len(self.reasoning) < 100:
            raise ValueError(
                f"High confidence ({self.confidence}) requires detailed reasoning (>100 chars)"
            )
        
        # Validate step numbering is sequential
        steps = [step.step for step in self.remediation_plan]
        if steps != list(range(1, len(steps) + 1)):
            raise ValueError(
                f"Remediation steps must be sequential starting from 1. Got: {steps}"
            )
        
        # At least one IMMEDIATE action for CRITICAL/HIGH severity
        # (Note: We don't have severity in response, so skip this check)
        
        # Calculate total duration if not provided
        if self.estimated_resolution_minutes is None:
            total_duration = sum(step.duration_minutes for step in self.remediation_plan)
            self.estimated_resolution_minutes = min(total_duration, 480)  # Cap at 8 hours
        
        return self
    
    class Config:
        json_schema_extra = {
            "example": {
                "root_cause": "BGP neighbor session down due to MTU mismatch on WAN interface",
                "confidence": 0.85,
                "reasoning": "Analysis shows: 1) BGP session dropped after interface flap, 2) Large packets being fragmented, 3) MTU mismatch detected between peers",
                "remediation_plan": [
                    {
                        "priority": "IMMEDIATE",
                        "step": 1,
                        "action": "Verify current MTU settings on WAN interface",
                        "command": "show interfaces GigabitEthernet0/0/0",
                        "expected_outcome": "MTU should match peer device (1500 bytes)",
                        "duration_minutes": 2
                    },
                    {
                        "priority": "SHORT_TERM",
                        "step": 2,
                        "action": "Adjust MTU to match peer device",
                        "command": "interface GigabitEthernet0/0/0; mtu 1500",
                        "expected_outcome": "MTU configured successfully, no packet loss",
                        "duration_minutes": 5,
                        "rollback_command": "interface GigabitEthernet0/0/0; mtu 9000"
                    }
                ],
                "affected_components": ["GigabitEthernet0/0/0", "BGP neighbor 10.1.1.1"],
                "escalation_needed": False,
                "estimated_resolution_minutes": 7
            }
        }


class DiagnosisValidationError(Exception):
    """Custom exception for diagnosis validation failures"""
    
    def __init__(self, message: str, errors: List[dict]):
        self.message = message
        self.errors = errors
        super().__init__(self.message)
    
    def __str__(self):
        error_details = "\n".join([
            f"  - {err.get('loc', 'unknown')}: {err.get('msg', 'validation error')}"
            for err in self.errors
        ])
        return f"{self.message}\n{error_details}"


def validate_diagnosis(raw_response: dict) -> DiagnosisResponse:
    """
    Validate raw LLM response against Pydantic schema
    
    Args:
        raw_response: Unvalidated dict from LLM
    
    Returns:
        DiagnosisResponse: Validated, typed response
    
    Raises:
        DiagnosisValidationError: If validation fails
    """
    try:
        return DiagnosisResponse(**raw_response)
    except Exception as e:
        # Convert Pydantic ValidationError to custom error
        if hasattr(e, 'errors'):
            errors = e.errors()
        else:
            errors = [{"msg": str(e)}]
        
        raise DiagnosisValidationError(
            message=f"LLM response validation failed: {len(errors)} error(s)",
            errors=errors
        )


def get_json_schema() -> dict:
    """
    Get JSON Schema for OpenAI structured output
    
    OpenAI supports forcing LLM to follow JSON schema via response_format
    """
    return DiagnosisResponse.model_json_schema()
