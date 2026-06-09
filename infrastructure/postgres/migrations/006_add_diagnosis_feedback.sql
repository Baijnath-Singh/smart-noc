-- Migration: Add diagnosis feedback table for confidence calibration
-- Date: 2026-06-09
-- Purpose: Track LLM confidence vs actual diagnosis correctness for calibration

-- Create diagnosis feedback table
CREATE TABLE IF NOT EXISTS diagnosis_feedback (
    id SERIAL PRIMARY KEY,
    diagnosis_id UUID NOT NULL,
    incident_number INTEGER NOT NULL,  -- Changed from VARCHAR(50) to INTEGER
    
    -- LLM output
    llm_confidence FLOAT NOT NULL CHECK (llm_confidence >= 0 AND llm_confidence <= 1),
    predicted_root_cause TEXT NOT NULL,
    incident_type VARCHAR(100),
    
    -- Engineer feedback
    was_correct BOOLEAN NOT NULL,
    actual_root_cause TEXT,
    engineer_notes TEXT,
    engineer_id VARCHAR(100),
    
    -- Remediation outcome
    remediation_success BOOLEAN,
    remediation_notes TEXT,
    
    -- Metadata
    feedback_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    incident_timestamp TIMESTAMP,
    
    -- Indexes for fast lookup
    CONSTRAINT fk_incident 
        FOREIGN KEY (incident_number) 
        REFERENCES incidents(incident_number)
        ON DELETE CASCADE
);

-- Create indexes for performance
CREATE INDEX idx_diagnosis_feedback_confidence ON diagnosis_feedback(llm_confidence);
CREATE INDEX idx_diagnosis_feedback_incident_type ON diagnosis_feedback(incident_type);
CREATE INDEX idx_diagnosis_feedback_timestamp ON diagnosis_feedback(feedback_timestamp DESC);
CREATE INDEX idx_diagnosis_feedback_correct ON diagnosis_feedback(was_correct);
CREATE INDEX idx_diagnosis_feedback_incident_number ON diagnosis_feedback(incident_number);

-- Create view for calibration metrics
CREATE OR REPLACE VIEW confidence_calibration_metrics AS
SELECT 
    FLOOR(llm_confidence * 10) / 10 AS confidence_bucket,
    incident_type,
    COUNT(*) as total_diagnoses,
    SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) as correct_diagnoses,
    ROUND(AVG(CASE WHEN was_correct THEN 1.0 ELSE 0.0 END)::numeric, 3) as actual_accuracy,
    ROUND(AVG(llm_confidence)::numeric, 3) as avg_reported_confidence,
    ROUND(AVG(llm_confidence)::numeric - AVG(CASE WHEN was_correct THEN 1.0 ELSE 0.0 END)::numeric, 3) as calibration_error
FROM diagnosis_feedback
WHERE feedback_timestamp > NOW() - INTERVAL '30 days'
GROUP BY FLOOR(llm_confidence * 10) / 10, incident_type
HAVING COUNT(*) >= 5
ORDER BY confidence_bucket DESC, incident_type;

-- Create view for overall calibration status
CREATE OR REPLACE VIEW calibration_status AS
SELECT 
    COUNT(*) as total_feedback_records,
    SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) as total_correct,
    ROUND(AVG(CASE WHEN was_correct THEN 1.0 ELSE 0.0 END)::numeric, 3) as overall_accuracy,
    ROUND(AVG(llm_confidence)::numeric, 3) as avg_confidence,
    ROUND(AVG(ABS(llm_confidence - CASE WHEN was_correct THEN 1.0 ELSE 0.0 END))::numeric, 3) as mean_absolute_error,
    COUNT(DISTINCT incident_type) as incident_types_covered,
    MIN(feedback_timestamp) as earliest_feedback,
    MAX(feedback_timestamp) as latest_feedback
FROM diagnosis_feedback;

-- Add comment for documentation
COMMENT ON TABLE diagnosis_feedback IS 'Stores engineer feedback on diagnosis accuracy for confidence calibration';
COMMENT ON VIEW confidence_calibration_metrics IS 'Aggregated calibration metrics by confidence bucket and incident type';
COMMENT ON VIEW calibration_status IS 'Overall system calibration status and metrics';

-- Grant permissions
GRANT SELECT, INSERT, UPDATE ON diagnosis_feedback TO noc_admin;
GRANT SELECT ON confidence_calibration_metrics TO noc_admin;
GRANT SELECT ON calibration_status TO noc_admin;
GRANT USAGE, SELECT ON SEQUENCE diagnosis_feedback_id_seq TO noc_admin;
