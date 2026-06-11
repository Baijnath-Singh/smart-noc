-- Migration 007: Add Confidence Reasoning Fields
-- Date: 2026-06-10
-- Purpose: Support improved LLM confidence generation with reasoning and evidence tracking

-- Add new fields to incidents table for confidence reasoning
ALTER TABLE incidents
ADD COLUMN IF NOT EXISTS confidence_reasoning TEXT,
ADD COLUMN IF NOT EXISTS evidence_direct_count INTEGER,
ADD COLUMN IF NOT EXISTS evidence_indirect_count INTEGER,
ADD COLUMN IF NOT EXISTS evidence_missing JSONB,
ADD COLUMN IF NOT EXISTS alternatives_considered JSONB;

-- Add comments for documentation
COMMENT ON COLUMN incidents.confidence_reasoning IS 'LLM explanation of why specific confidence score was assigned';
COMMENT ON COLUMN incidents.evidence_direct_count IS 'Number of direct causal evidence pieces';
COMMENT ON COLUMN incidents.evidence_indirect_count IS 'Number of indirect/correlational evidence pieces';
COMMENT ON COLUMN incidents.evidence_missing IS 'JSON array of missing critical data that would improve confidence';
COMMENT ON COLUMN incidents.alternatives_considered IS 'JSON array of alternative root causes that were considered and ruled out';

-- Create view for confidence analysis (using JSONB fields)
CREATE OR REPLACE VIEW confidence_analysis AS
SELECT 
    incident_number,
    incident_type,
    (incident_metadata->'llm_diagnosis'->>'raw_confidence')::float as raw_confidence,
    (incident_metadata->'llm_diagnosis'->>'calibrated_confidence')::float as calibrated_confidence,
    incident_metadata->'llm_diagnosis'->>'calibration_method' as calibration_method,
    confidence_reasoning,
    evidence_direct_count,
    evidence_indirect_count,
    COALESCE(evidence_direct_count, 0) + COALESCE(evidence_indirect_count, 0) as total_evidence_count,
    CASE 
        WHEN evidence_direct_count >= 2 
             AND (incident_metadata->'llm_diagnosis'->>'calibrated_confidence')::float >= 0.85 
             THEN 'HIGH_QUALITY'
        WHEN evidence_direct_count >= 1 
             AND (incident_metadata->'llm_diagnosis'->>'calibrated_confidence')::float >= 0.70 
             THEN 'MEDIUM_QUALITY'
        WHEN COALESCE(evidence_direct_count, 0) = 0 
             AND (incident_metadata->'llm_diagnosis'->>'calibrated_confidence')::float >= 0.70 
             THEN 'OVERCONFIDENT_SUSPECT'
        ELSE 'LOW_CONFIDENCE'
    END as confidence_quality,
    evidence_missing,
    alternatives_considered,
    created_at as diagnosis_timestamp
FROM incidents
WHERE incident_metadata->'llm_diagnosis'->>'raw_confidence' IS NOT NULL
ORDER BY incident_number DESC;

COMMENT ON VIEW confidence_analysis IS 'Analysis view for confidence quality and reasoning validation';

-- Create index for evidence analysis
CREATE INDEX IF NOT EXISTS idx_incidents_evidence_counts 
ON incidents(evidence_direct_count, evidence_indirect_count) 
WHERE incident_metadata->'llm_diagnosis' IS NOT NULL;

-- Create index for confidence reasoning queries
CREATE INDEX IF NOT EXISTS idx_incidents_confidence_reasoning 
ON incidents(evidence_direct_count) 
WHERE confidence_reasoning IS NOT NULL;

-- Sample query to identify overconfident diagnoses
-- (High confidence with weak evidence)
CREATE OR REPLACE VIEW potentially_overconfident_diagnoses AS
SELECT 
    incident_number,
    incident_type,
    (incident_metadata->'llm_diagnosis'->>'raw_confidence')::float as raw_confidence,
    (incident_metadata->'llm_diagnosis'->>'calibrated_confidence')::float as calibrated_confidence,
    evidence_direct_count,
    evidence_indirect_count,
    confidence_reasoning,
    created_at as diagnosis_timestamp
FROM incidents
WHERE (incident_metadata->'llm_diagnosis'->>'raw_confidence')::float >= 0.80
  AND COALESCE(evidence_direct_count, 0) = 0
  AND created_at >= NOW() - INTERVAL '30 days'
ORDER BY (incident_metadata->'llm_diagnosis'->>'raw_confidence')::float DESC;

COMMENT ON VIEW potentially_overconfident_diagnoses IS 'Identifies diagnoses with high confidence but no direct evidence (potential overconfidence)';

-- Success message (using PostgreSQL RAISE NOTICE)
DO $$ 
BEGIN 
    RAISE NOTICE 'Migration 007 completed: Confidence reasoning fields added';
END $$;
