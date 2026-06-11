-- Migration 008: Safety Framework for Autonomous Remediation
-- Date: 2026-06-10
-- Purpose: Add tables for risk assessment, approvals, rollback, and autonomous execution

-- ============================================================================
-- 1. DEVICE CRITICALITY TABLE
-- ============================================================================
-- Defines risk level for each device in the network

CREATE TABLE IF NOT EXISTS device_criticality (
    device_name VARCHAR(255) PRIMARY KEY,
    criticality VARCHAR(20) NOT NULL CHECK (criticality IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    device_role VARCHAR(50), -- 'core', 'distribution', 'access', 'edge'
    business_impact VARCHAR(20) CHECK (business_impact IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    maintenance_window VARCHAR(100), -- e.g., "Mon-Fri 22:00-06:00"
    requires_approval BOOLEAN DEFAULT false,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

COMMENT ON TABLE device_criticality IS 'Device risk classification for autonomous remediation decisions';

CREATE INDEX idx_device_criticality_role ON device_criticality(device_role);
CREATE INDEX idx_device_criticality_level ON device_criticality(criticality);

-- ============================================================================
-- 2. RISK ASSESSMENT TABLE
-- ============================================================================
-- Stores risk assessment for each incident

CREATE TABLE IF NOT EXISTS incident_risk_assessment (
    id SERIAL PRIMARY KEY,
    incident_number INTEGER NOT NULL REFERENCES incidents(incident_number) ON DELETE CASCADE,
    risk_level VARCHAR(20) NOT NULL CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    device_criticality VARCHAR(20),
    blast_radius_score NUMERIC(3,2), -- 0.0-1.0
    time_sensitivity_score NUMERIC(3,2), -- 0.0-1.0
    change_complexity_score NUMERIC(3,2), -- 0.0-1.0
    overall_risk_score NUMERIC(3,2), -- 0.0-1.0
    factors JSONB, -- Detailed risk factors
    assessed_at TIMESTAMP DEFAULT NOW(),
    assessed_by VARCHAR(50) DEFAULT 'risk_assessor_v1'
);

COMMENT ON TABLE incident_risk_assessment IS 'Risk assessment for autonomous remediation decisions';

CREATE INDEX idx_risk_assessment_incident ON incident_risk_assessment(incident_number);
CREATE INDEX idx_risk_assessment_level ON incident_risk_assessment(risk_level);

-- ============================================================================
-- 3. CONFIGURATION SNAPSHOTS TABLE
-- ============================================================================
-- Stores device configurations before remediation for rollback

CREATE TABLE IF NOT EXISTS configuration_snapshots (
    id SERIAL PRIMARY KEY,
    incident_number INTEGER NOT NULL REFERENCES incidents(incident_number) ON DELETE CASCADE,
    device_name VARCHAR(255) NOT NULL,
    snapshot_type VARCHAR(50) DEFAULT 'pre_remediation', -- 'pre_remediation', 'post_remediation', 'scheduled'
    configuration TEXT NOT NULL, -- Full device config
    running_config TEXT,
    startup_config TEXT,
    config_hash VARCHAR(64), -- SHA-256 hash for integrity
    metadata JSONB, -- Version info, backup method, etc.
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(50) DEFAULT 'rollback_manager_v1'
);

COMMENT ON TABLE configuration_snapshots IS 'Device configuration backups for rollback capability';

CREATE INDEX idx_snapshots_incident ON configuration_snapshots(incident_number);
CREATE INDEX idx_snapshots_device ON configuration_snapshots(device_name);
CREATE INDEX idx_snapshots_created ON configuration_snapshots(created_at DESC);

-- ============================================================================
-- 4. APPROVAL REQUESTS TABLE
-- ============================================================================
-- Tracks approval requests for medium/high risk remediations

CREATE TABLE IF NOT EXISTS remediation_approvals (
    id SERIAL PRIMARY KEY,
    incident_number INTEGER NOT NULL REFERENCES incidents(incident_number) ON DELETE CASCADE,
    request_type VARCHAR(50) NOT NULL, -- 'auto_remediation', 'rollback', 'escalation'
    risk_level VARCHAR(20) NOT NULL,
    calibrated_confidence NUMERIC(3,2),
    requested_by VARCHAR(50) DEFAULT 'autonomous_system',
    requested_at TIMESTAMP DEFAULT NOW(),
    
    -- Approval status
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'expired', 'auto_approved')),
    approved_by VARCHAR(100), -- NOC engineer username/email
    approved_at TIMESTAMP,
    decision_reason TEXT,
    
    -- Timeout handling
    expires_at TIMESTAMP,
    auto_approve_after INTERVAL, -- e.g., '5 minutes' for off-hours
    
    -- Notification tracking
    notification_sent BOOLEAN DEFAULT false,
    notification_channel VARCHAR(50), -- 'slack', 'email', 'pagerduty'
    notification_id VARCHAR(255),
    
    metadata JSONB
);

COMMENT ON TABLE remediation_approvals IS 'Approval workflow for autonomous remediation';

CREATE INDEX idx_approvals_incident ON remediation_approvals(incident_number);
CREATE INDEX idx_approvals_status ON remediation_approvals(status);
CREATE INDEX idx_approvals_pending ON remediation_approvals(status, expires_at) WHERE status = 'pending';

-- ============================================================================
-- 5. REMEDIATION EXECUTIONS TABLE (Enhanced)
-- ============================================================================
-- Already exists, but let's add safety framework fields

ALTER TABLE remediation_executions
ADD COLUMN IF NOT EXISTS risk_level VARCHAR(20),
ADD COLUMN IF NOT EXISTS approval_id INTEGER REFERENCES remediation_approvals(id),
ADD COLUMN IF NOT EXISTS snapshot_id INTEGER REFERENCES configuration_snapshots(id),
ADD COLUMN IF NOT EXISTS rollback_available BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS autonomous_execution BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS safety_checks_passed BOOLEAN DEFAULT true,
ADD COLUMN IF NOT EXISTS pre_execution_snapshot JSONB,
ADD COLUMN IF NOT EXISTS post_execution_snapshot JSONB;

-- ============================================================================
-- 6. ROLLBACK HISTORY TABLE
-- ============================================================================
-- Tracks rollback operations

CREATE TABLE IF NOT EXISTS rollback_history (
    id SERIAL PRIMARY KEY,
    incident_number INTEGER NOT NULL REFERENCES incidents(incident_number) ON DELETE CASCADE,
    remediation_execution_id INTEGER REFERENCES remediation_executions(id),
    snapshot_id INTEGER NOT NULL REFERENCES configuration_snapshots(id),
    rollback_reason VARCHAR(50) NOT NULL, -- 'execution_failed', 'verification_failed', 'manual_request', 'auto_rollback'
    
    -- Rollback status
    status VARCHAR(20) DEFAULT 'initiated' CHECK (status IN ('initiated', 'in_progress', 'completed', 'failed')),
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    
    -- Results
    success BOOLEAN,
    error_message TEXT,
    commands_executed JSONB,
    verification_results JSONB,
    
    -- Who triggered
    triggered_by VARCHAR(50) DEFAULT 'autonomous_system',
    triggered_reason TEXT,
    
    metadata JSONB
);

COMMENT ON TABLE rollback_history IS 'History of configuration rollback operations';

CREATE INDEX idx_rollback_incident ON rollback_history(incident_number);
CREATE INDEX idx_rollback_execution ON rollback_history(remediation_execution_id);
CREATE INDEX idx_rollback_status ON rollback_history(status);

-- ============================================================================
-- 7. AUTONOMOUS DECISION LOG TABLE
-- ============================================================================
-- Audit trail for all autonomous decisions

CREATE TABLE IF NOT EXISTS autonomous_decision_log (
    id SERIAL PRIMARY KEY,
    incident_number INTEGER NOT NULL REFERENCES incidents(incident_number) ON DELETE CASCADE,
    decision_type VARCHAR(50) NOT NULL, -- 'auto_execute', 'require_approval', 'reject', 'rollback'
    
    -- Decision inputs
    calibrated_confidence NUMERIC(3,2),
    risk_level VARCHAR(20),
    device_criticality VARCHAR(20),
    time_of_day TIME,
    is_business_hours BOOLEAN,
    
    -- Decision logic
    decision VARCHAR(20) NOT NULL, -- 'execute', 'approve', 'reject', 'escalate'
    decision_reasoning TEXT NOT NULL,
    rule_matched VARCHAR(100), -- Which decision rule was applied
    
    -- Metadata
    decided_at TIMESTAMP DEFAULT NOW(),
    decided_by VARCHAR(50) DEFAULT 'autonomous_executor_v1',
    metadata JSONB
);

COMMENT ON TABLE autonomous_decision_log IS 'Audit trail for autonomous remediation decisions';

CREATE INDEX idx_decision_log_incident ON autonomous_decision_log(incident_number);
CREATE INDEX idx_decision_log_decision ON autonomous_decision_log(decision);
CREATE INDEX idx_decision_log_time ON autonomous_decision_log(decided_at DESC);

-- ============================================================================
-- 8. VIEWS FOR MONITORING
-- ============================================================================

-- View: Pending approvals
CREATE OR REPLACE VIEW pending_approvals AS
SELECT 
    ra.id as approval_id,
    ra.incident_number,
    i.incident_type,
    i.severity,
    i.primary_device,
    ra.risk_level,
    ra.calibrated_confidence,
    ra.requested_at,
    ra.expires_at,
    EXTRACT(EPOCH FROM (ra.expires_at - NOW())) / 60 as minutes_until_expiry,
    ra.notification_sent,
    ra.notification_channel
FROM remediation_approvals ra
JOIN incidents i ON ra.incident_number = i.incident_number
WHERE ra.status = 'pending'
  AND ra.expires_at > NOW()
ORDER BY ra.requested_at;

COMMENT ON VIEW pending_approvals IS 'Active approval requests awaiting NOC engineer decision';

-- View: Autonomous execution stats
CREATE OR REPLACE VIEW autonomous_execution_stats AS
SELECT 
    DATE(decided_at) as date,
    decision,
    risk_level,
    COUNT(*) as count,
    AVG(calibrated_confidence) as avg_confidence,
    COUNT(CASE WHEN decision = 'execute' THEN 1 END) as auto_executed,
    COUNT(CASE WHEN decision = 'approve' THEN 1 END) as required_approval
FROM autonomous_decision_log
GROUP BY DATE(decided_at), decision, risk_level
ORDER BY date DESC, decision;

COMMENT ON VIEW autonomous_execution_stats IS 'Daily statistics for autonomous remediation decisions';

-- View: Rollback success rate
CREATE OR REPLACE VIEW rollback_success_rate AS
SELECT 
    DATE(started_at) as date,
    rollback_reason,
    COUNT(*) as total_rollbacks,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful,
    ROUND(AVG(CASE WHEN success THEN 1.0 ELSE 0.0 END) * 100, 2) as success_rate_pct,
    AVG(duration_seconds) as avg_duration_seconds
FROM rollback_history
GROUP BY DATE(started_at), rollback_reason
ORDER BY date DESC;

COMMENT ON VIEW rollback_success_rate IS 'Rollback operation success metrics';

-- View: Safety framework dashboard
CREATE OR REPLACE VIEW safety_framework_dashboard AS
SELECT 
    (SELECT COUNT(*) FROM remediation_approvals WHERE status = 'pending') as pending_approvals,
    (SELECT COUNT(*) FROM autonomous_decision_log WHERE decided_at >= NOW() - INTERVAL '24 hours') as decisions_24h,
    (SELECT COUNT(*) FROM autonomous_decision_log WHERE decision = 'execute' AND decided_at >= NOW() - INTERVAL '24 hours') as auto_executed_24h,
    (SELECT COUNT(*) FROM rollback_history WHERE started_at >= NOW() - INTERVAL '24 hours') as rollbacks_24h,
    (SELECT COUNT(*) FROM rollback_history WHERE success = true AND started_at >= NOW() - INTERVAL '24 hours') as successful_rollbacks_24h,
    (SELECT COUNT(*) FROM configuration_snapshots WHERE created_at >= NOW() - INTERVAL '24 hours') as snapshots_24h;

COMMENT ON VIEW safety_framework_dashboard IS 'Real-time safety framework metrics';

-- ============================================================================
-- 9. INSERT DEFAULT DEVICE CRITICALITY DATA
-- ============================================================================

-- Core routers (CRITICAL)
INSERT INTO device_criticality (device_name, criticality, device_role, business_impact, requires_approval, notes)
VALUES 
    ('core-router-01', 'CRITICAL', 'core', 'CRITICAL', true, 'Primary core router - always requires approval'),
    ('core-router-02', 'CRITICAL', 'core', 'CRITICAL', true, 'Secondary core router - always requires approval'),
    ('core-switch-01', 'CRITICAL', 'core', 'CRITICAL', true, 'Core distribution switch')
ON CONFLICT (device_name) DO NOTHING;

-- Distribution switches (HIGH)
INSERT INTO device_criticality (device_name, criticality, device_role, business_impact, requires_approval, notes)
VALUES 
    ('voss-dist-switch-01', 'HIGH', 'distribution', 'HIGH', true, 'Distribution layer - requires approval'),
    ('edge-switch-05', 'MEDIUM', 'edge', 'MEDIUM', false, 'Edge switch - autonomous allowed for low risk')
ON CONFLICT (device_name) DO NOTHING;

-- Access switches (MEDIUM/LOW)
INSERT INTO device_criticality (device_name, criticality, device_role, business_impact, requires_approval, notes)
VALUES 
    ('access-switch-12', 'MEDIUM', 'access', 'LOW', false, 'Access layer - autonomous allowed'),
    ('lab-switch-01', 'LOW', 'access', 'LOW', false, 'Lab environment - fully autonomous')
ON CONFLICT (device_name) DO NOTHING;

-- ============================================================================
-- 10. TRIGGERS FOR AUTOMATIC EXPIRY HANDLING
-- ============================================================================

-- Function to auto-approve expired requests (off-hours only)
CREATE OR REPLACE FUNCTION handle_expired_approvals()
RETURNS TRIGGER AS $$
BEGIN
    -- Check if auto-approve window has passed
    IF NEW.status = 'pending' AND NEW.expires_at <= NOW() AND NEW.auto_approve_after IS NOT NULL THEN
        -- Only auto-approve during off-hours (defined as 22:00-06:00)
        IF EXTRACT(HOUR FROM NOW()) >= 22 OR EXTRACT(HOUR FROM NOW()) < 6 THEN
            NEW.status = 'auto_approved';
            NEW.approved_at = NOW();
            NEW.approved_by = 'system_auto_approval';
            NEW.decision_reason = 'Auto-approved after timeout during off-hours';
        ELSE
            NEW.status = 'expired';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to check for expiry on update
CREATE TRIGGER check_approval_expiry
BEFORE UPDATE ON remediation_approvals
FOR EACH ROW
EXECUTE FUNCTION handle_expired_approvals();

-- ============================================================================
-- SUCCESS MESSAGE
-- ============================================================================

DO $$ 
BEGIN 
    RAISE NOTICE 'Migration 008 completed: Safety Framework tables created';
    RAISE NOTICE '  - device_criticality: Device risk classification';
    RAISE NOTICE '  - incident_risk_assessment: Incident risk scoring';
    RAISE NOTICE '  - configuration_snapshots: Config backups for rollback';
    RAISE NOTICE '  - remediation_approvals: Approval workflow';
    RAISE NOTICE '  - rollback_history: Rollback tracking';
    RAISE NOTICE '  - autonomous_decision_log: Decision audit trail';
    RAISE NOTICE '  - Views: pending_approvals, autonomous_execution_stats, safety_framework_dashboard';
END $$;
