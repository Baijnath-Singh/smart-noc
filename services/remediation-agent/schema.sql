-- Table to store remediation execution history
CREATE TABLE IF NOT EXISTS remediation_executions (
    id SERIAL PRIMARY KEY,
    incident_id UUID,
    incident_number INTEGER NOT NULL,
    success BOOLEAN NOT NULL,
    actions_taken INTEGER DEFAULT 0,
    resolution_time_seconds FLOAT DEFAULT 0.0,
    final_phase VARCHAR(50),
    lessons_learned TEXT,
    executed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Index for querying
    CONSTRAINT fk_incident FOREIGN KEY (incident_id) REFERENCES incidents(id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_remediation_incident_number ON remediation_executions(incident_number);
CREATE INDEX IF NOT EXISTS idx_remediation_executed_at ON remediation_executions(executed_at);
CREATE INDEX IF NOT EXISTS idx_remediation_success ON remediation_executions(success);

-- View for remediation statistics
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
