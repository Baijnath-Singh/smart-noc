-- Phase 5: Add Remediation Agent tables
-- Migration: 003_add_remediation_tables.sql

-- ============================================================================
-- REMEDIATION_EXECUTIONS TABLE
-- Tracks autonomous remediation attempts and outcomes
-- ============================================================================
CREATE TABLE IF NOT EXISTS remediation_executions (
    id SERIAL PRIMARY KEY,
    incident_id UUID NOT NULL,
    incident_number INTEGER NOT NULL,
    success BOOLEAN NOT NULL,
    actions_taken INTEGER DEFAULT 0,
    resolution_time_seconds FLOAT,
    final_phase VARCHAR(50),
    lessons_learned TEXT,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key to incidents table
    CONSTRAINT fk_incident FOREIGN KEY (incident_id) 
        REFERENCES incidents(id) ON DELETE CASCADE
);

-- ============================================================================
-- INDEXES for better query performance
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_remediation_incident_number ON remediation_executions(incident_number);
CREATE INDEX IF NOT EXISTS idx_remediation_executed_at ON remediation_executions(executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_remediation_success ON remediation_executions(success);
CREATE INDEX IF NOT EXISTS idx_remediation_incident_id ON remediation_executions(incident_id);

-- ============================================================================
-- REMEDIATION_STATS VIEW
-- Daily aggregated statistics for remediation performance
-- ============================================================================
CREATE OR REPLACE VIEW remediation_stats AS
SELECT 
    DATE(executed_at) as date,
    COUNT(*) as total_executions,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful,
    SUM(CASE WHEN NOT success AND final_phase = 'escalated' THEN 1 ELSE 0 END) as escalated,
    SUM(CASE WHEN NOT success AND final_phase != 'escalated' THEN 1 ELSE 0 END) as failed,
    AVG(resolution_time_seconds) as avg_resolution_time,
    AVG(actions_taken) as avg_actions_per_incident
FROM remediation_executions
GROUP BY DATE(executed_at)
ORDER BY date DESC;

-- ============================================================================
-- COMMENTS for documentation
-- ============================================================================
COMMENT ON TABLE remediation_executions IS 'Tracks autonomous remediation attempts and outcomes from LangGraph workflow';
COMMENT ON COLUMN remediation_executions.incident_id IS 'UUID reference to incidents table';
COMMENT ON COLUMN remediation_executions.incident_number IS 'Human-readable incident number';
COMMENT ON COLUMN remediation_executions.success IS 'True if remediation succeeded, false if escalated/failed';
COMMENT ON COLUMN remediation_executions.actions_taken IS 'Number of remediation actions executed';
COMMENT ON COLUMN remediation_executions.resolution_time_seconds IS 'Total time taken for remediation workflow';
COMMENT ON COLUMN remediation_executions.final_phase IS 'Final workflow phase: completed, escalated, failed, rollback';
COMMENT ON COLUMN remediation_executions.lessons_learned IS 'Summary of what worked/failed for future learning';
COMMENT ON VIEW remediation_stats IS 'Daily aggregated statistics for remediation performance metrics';

-- Grant permissions
GRANT ALL ON remediation_executions TO noc_admin;
GRANT ALL ON remediation_executions_id_seq TO noc_admin;
GRANT SELECT ON remediation_stats TO noc_admin;
