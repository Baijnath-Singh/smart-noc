-- Phase 4: Add LLM diagnosis columns to incidents table
-- Migration: 002_add_diagnosis_columns.sql

-- Add diagnosis columns to incidents table
ALTER TABLE incidents 
ADD COLUMN IF NOT EXISTS root_cause TEXT,
ADD COLUMN IF NOT EXISTS root_cause_confidence NUMERIC(5,2) CHECK (root_cause_confidence >= 0 AND root_cause_confidence <= 1),
ADD COLUMN IF NOT EXISTS remediation_plan JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS diagnosis_timestamp TIMESTAMP,
ADD COLUMN IF NOT EXISTS llm_model VARCHAR(50),
ADD COLUMN IF NOT EXISTS diagnosis_metadata JSONB DEFAULT '{}'::jsonb;

-- Add index for diagnosis queries
CREATE INDEX IF NOT EXISTS idx_incidents_diagnosis_timestamp ON incidents(diagnosis_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_incidents_root_cause_confidence ON incidents(root_cause_confidence DESC);

-- Create diagnosis history table for audit trail
CREATE TABLE IF NOT EXISTS incident_diagnosis_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    diagnosis_version INTEGER NOT NULL DEFAULT 1,
    root_cause TEXT NOT NULL,
    root_cause_confidence NUMERIC(5,2) NOT NULL,
    remediation_plan JSONB NOT NULL,
    llm_model VARCHAR(50) NOT NULL,
    llm_prompt TEXT,
    llm_response TEXT,
    tokens_used INTEGER,
    diagnosis_duration_ms INTEGER,
    diagnosis_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(incident_id, diagnosis_version)
);

-- Add indexes for diagnosis history
CREATE INDEX IF NOT EXISTS idx_diagnosis_history_incident ON incident_diagnosis_history(incident_id);
CREATE INDEX IF NOT EXISTS idx_diagnosis_history_created ON incident_diagnosis_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_diagnosis_history_model ON incident_diagnosis_history(llm_model);

-- Create view for incidents with diagnosis
CREATE OR REPLACE VIEW incidents_with_diagnosis AS
SELECT 
    i.id,
    i.incident_number,
    i.incident_type,
    i.severity,
    i.status,
    i.affected_device_count,
    i.affected_devices,
    i.primary_device,
    i.anomaly_count,
    i.correlation_method,
    i.impact_score,
    i.root_cause,
    i.root_cause_confidence,
    i.remediation_plan,
    i.diagnosis_timestamp,
    i.llm_model,
    i.created_at,
    i.updated_at,
    CASE 
        WHEN i.root_cause IS NOT NULL THEN 'DIAGNOSED'
        WHEN i.diagnosis_timestamp IS NOT NULL AND i.root_cause IS NULL THEN 'DIAGNOSIS_FAILED'
        ELSE 'PENDING_DIAGNOSIS'
    END as diagnosis_status,
    CASE 
        WHEN i.diagnosis_timestamp IS NOT NULL THEN 
            EXTRACT(EPOCH FROM (i.diagnosis_timestamp - i.created_at)) 
        ELSE NULL 
    END as diagnosis_delay_seconds
FROM incidents i;

-- Create view for diagnosis statistics
CREATE OR REPLACE VIEW diagnosis_statistics AS
SELECT 
    COUNT(*) as total_incidents,
    COUNT(root_cause) as diagnosed_incidents,
    COUNT(*) FILTER (WHERE root_cause IS NULL) as pending_diagnosis,
    COUNT(*) FILTER (WHERE root_cause_confidence >= 0.8) as high_confidence_diagnosis,
    COUNT(*) FILTER (WHERE root_cause_confidence BETWEEN 0.5 AND 0.8) as medium_confidence_diagnosis,
    COUNT(*) FILTER (WHERE root_cause_confidence < 0.5) as low_confidence_diagnosis,
    AVG(root_cause_confidence) as avg_confidence,
    AVG(EXTRACT(EPOCH FROM (diagnosis_timestamp - created_at))) as avg_diagnosis_delay_seconds,
    COUNT(DISTINCT llm_model) as models_used
FROM incidents
WHERE created_at >= NOW() - INTERVAL '24 hours';

-- Grant permissions
GRANT SELECT ON incident_diagnosis_history TO noc_admin;
GRANT SELECT ON incidents_with_diagnosis TO noc_admin;
GRANT SELECT ON diagnosis_statistics TO noc_admin;

-- Add comments
COMMENT ON COLUMN incidents.root_cause IS 'LLM-generated root cause analysis';
COMMENT ON COLUMN incidents.root_cause_confidence IS 'Confidence score 0.0-1.0 for diagnosis accuracy';
COMMENT ON COLUMN incidents.remediation_plan IS 'Array of remediation steps with priorities';
COMMENT ON COLUMN incidents.diagnosis_timestamp IS 'Timestamp when diagnosis was completed';
COMMENT ON COLUMN incidents.llm_model IS 'LLM model used (e.g., gpt-4, claude-3)';
COMMENT ON COLUMN incidents.diagnosis_metadata IS 'Additional diagnosis metadata (tokens, duration, etc)';

COMMENT ON TABLE incident_diagnosis_history IS 'Audit trail for all diagnosis attempts including failed ones';
COMMENT ON VIEW incidents_with_diagnosis IS 'Incidents enriched with diagnosis status';
COMMENT ON VIEW diagnosis_statistics IS 'Real-time diagnosis performance metrics (24h rolling window)';
