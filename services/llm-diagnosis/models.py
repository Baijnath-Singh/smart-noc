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


class EvidenceQuality(BaseModel):
    """Quality assessment of evidence for diagnosis (helps LLM self-evaluate)"""
    direct_evidence_count: int = Field(
        ge=0,
        description="Number of direct causal evidence pieces"
    )
    indirect_evidence_count: int = Field(
        ge=0,
        description="Number of indirect/correlational evidence pieces"
    )
    missing_critical_data: List[str] = Field(
        default=[],
        description="List of critical missing data that would improve confidence"
    )
    alternative_causes_considered: List[str] = Field(
        default=[],
        description="Alternative root causes that were considered and ruled out"
    )


class DiagnosisResponse(BaseModel):
    """
    Complete LLM diagnosis response with validation
    
    This enforces:
    - All required fields are present
    - Types are correct (float confidence, not "high")
    - Value ranges are valid (confidence 0.0-1.0)
    - Remediation steps follow structure
    - No missing or malformed data
    - NEW: Confidence reasoning (explains why that confidence score)
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
    confidence_reasoning: Optional[str] = Field(
        default=None,
        min_length=50,
        max_length=1000,
        description="Explanation of why this confidence score was assigned (NEW: helps prevent overconfidence)"
    )
    evidence_quality: Optional[EvidenceQuality] = Field(
        default=None,
        description="Assessment of evidence strength (NEW: quantifies confidence basis)"
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
    
    @field_validator('root_cause', 'reasoning', 'confidence_reasoning')
    @classmethod
    def validate_technical_content(cls, v: str, info) -> str:
        """Ensure root_cause, reasoning, and confidence_reasoning are meaningful"""
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
        
        # High confidence should have detailed confidence_reasoning (if provided)
        if self.confidence >= 0.7 and self.confidence_reasoning and len(self.confidence_reasoning) < 80:
            raise ValueError(
                f"Confidence {self.confidence:.2f} requires detailed confidence reasoning (>80 chars)"
            )
        
        # Validate confidence reasoning contains key markers (if provided)
        if self.confidence_reasoning:
            conf_lower = self.confidence_reasoning.lower()
            if self.confidence >= 0.7:
                # Should mention evidence
                has_evidence_mention = any(word in conf_lower for word in ['evidence', 'support', 'confirm', 'indicate'])
                if not has_evidence_mention:
                    raise ValueError(
                        "High confidence reasoning must mention supporting evidence"
                    )
        
        # If evidence_quality provided, validate it matches confidence
        if self.evidence_quality:
            total_evidence = (
                self.evidence_quality.direct_evidence_count + 
                self.evidence_quality.indirect_evidence_count
            )
            
            # High confidence should have multiple evidence points
            if self.confidence >= 0.85 and total_evidence < 2:
                raise ValueError(
                    f"Confidence {self.confidence:.2f} too high with only {total_evidence} evidence points"
                )
            
            # High confidence should have direct evidence
            if self.confidence >= 0.85 and self.evidence_quality.direct_evidence_count == 0:
                raise ValueError(
                    f"Confidence {self.confidence:.2f} requires at least 1 direct evidence"
                )
        
        # Validate step numbering is sequential
        steps = [step.step for step in self.remediation_plan]
        if steps != list(range(1, len(steps) + 1)):
            raise ValueError(
                f"Remediation steps must be sequential starting from 1. Got: {steps}"
            )
        
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
                "confidence_reasoning": "Confidence: 0.85 because:\n✓ Direct evidence: MTU mismatch confirmed (9000 vs 1500)\n✓ Timeline correlation: fragmentation preceded BGP drop\n✓ Pattern match: identical to past incident #42\n✗ Missing: packet capture for absolute confirmation\nConclusion: High confidence but not 0.90+ due to missing packet capture",
                "evidence_quality": {
                    "direct_evidence_count": 2,
                    "indirect_evidence_count": 1,
                    "missing_critical_data": ["packet capture", "BGP debug logs"],
                    "alternative_causes_considered": ["Authentication failure", "Software bug", "Network congestion"]
                },
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
