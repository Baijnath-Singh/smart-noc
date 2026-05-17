-- ============================================================================
-- Smart NOC - PostgreSQL Initialization Schema
-- Purpose: Store correlated incidents from anomaly detection
-- ============================================================================

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- INCIDENTS TABLE
-- Stores correlated incidents (groups of related anomalies)
-- ============================================================================
CREATE TABLE IF NOT EXISTS incidents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_number SERIAL UNIQUE NOT NULL,
    incident_type VARCHAR(100) NOT NULL,
    -- Incident types: NETWORK_PERFORMANCE, SECURITY_BREACH, CONNECTIVITY_ISSUE, 
    --                 DEVICE_FAILURE, CASCADE_FAILURE, UNKNOWN
    
    severity VARCHAR(20) NOT NULL,
    -- Severity levels: LOW, MEDIUM, HIGH, CRITICAL
    
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    -- Status: ACTIVE, INVESTIGATING, RESOLVED, CLOSED
    
    affected_device_count INTEGER NOT NULL DEFAULT 0,
    affected_devices JSONB NOT NULL DEFAULT '[]'::JSONB,
    -- Array of device IDs affected by this incident
    
    primary_device VARCHAR(255),
    -- Main device responsible for the incident (if identified)
    
    anomaly_count INTEGER NOT NULL DEFAULT 0,
    
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    duration_seconds INTEGER,
    -- Calculated: end_time - start_time
    
    correlation_method VARCHAR(50) NOT NULL,
    -- Method used: TIME_BASED, PATTERN_BASED, TOPOLOGY_BASED
    
    correlation_confidence DECIMAL(5,2),
    -- Confidence score 0-100 for correlation accuracy
    
    impact_score DECIMAL(5,2),
    -- Business impact score 0-100
    
    root_cause TEXT,
    -- LLM-generated root cause (Phase 4)
    
    remediation_plan TEXT,
    -- Suggested remediation steps (Phase 5)
    
    incident_metadata JSONB DEFAULT '{}'::JSONB,
    -- Additional incident metadata
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMP,
    
    -- Indexes for fast queries
    CONSTRAINT incidents_severity_check CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    CONSTRAINT incidents_status_check CHECK (status IN ('ACTIVE', 'INVESTIGATING', 'RESOLVED', 'CLOSED'))
);

-- ============================================================================
-- INCIDENT_ANOMALIES TABLE
-- Many-to-many relationship: incidents ↔ anomalies
-- ============================================================================
CREATE TABLE IF NOT EXISTS incident_anomalies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    
    -- Anomaly details (denormalized for performance)
    anomaly_id VARCHAR(255) NOT NULL,
    -- Fingerprint from Elasticsearch
    
    device_id VARCHAR(255) NOT NULL,
    anomaly_type VARCHAR(100) NOT NULL,
    detection_method VARCHAR(50) NOT NULL,
    -- RULE_BASED or ML_BASED
    
    confidence DECIMAL(5,2),
    timestamp TIMESTAMP NOT NULL,
    
    anomaly_data JSONB NOT NULL DEFAULT '{}'::JSONB,
    -- Full anomaly payload from Kafka
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Composite index for fast lookups
    CONSTRAINT unique_incident_anomaly UNIQUE (incident_id, anomaly_id)
);

-- ============================================================================
-- INCIDENT_TIMELINE TABLE
-- Tracks incident state changes for audit trail
-- ============================================================================
CREATE TABLE IF NOT EXISTS incident_timeline (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_id UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    
    event_type VARCHAR(50) NOT NULL,
    -- Event types: CREATED, ANOMALY_ADDED, STATUS_CHANGED, RESOLVED, REOPENED
    
    description TEXT NOT NULL,
    
    previous_status VARCHAR(20),
    new_status VARCHAR(20),
    
    changed_by VARCHAR(100) DEFAULT 'SYSTEM',
    -- User or system that made the change
   event_metadata JSONB DEFAULT '{}'::JSONB,
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- INDEXES for Performance
-- ============================================================================

-- Incidents indexes
CREATE INDEX idx_incidents_status ON incidents(status);
CREATE INDEX idx_incidents_severity ON incidents(severity);
CREATE INDEX idx_incidents_type ON incidents(incident_type);
CREATE INDEX idx_incidents_start_time ON incidents(start_time DESC);
CREATE INDEX idx_incidents_affected_devices ON incidents USING GIN (affected_devices);
CREATE INDEX idx_incidents_created_at ON incidents(created_at DESC);

-- Incident anomalies indexes
CREATE INDEX idx_incident_anomalies_incident ON incident_anomalies(incident_id);
CREATE INDEX idx_incident_anomalies_device ON incident_anomalies(device_id);
CREATE INDEX idx_incident_anomalies_timestamp ON incident_anomalies(timestamp DESC);

-- Timeline indexes
CREATE INDEX idx_timeline_incident ON incident_timeline(incident_id);
CREATE INDEX idx_timeline_created ON incident_timeline(created_at DESC);

-- ============================================================================
-- FUNCTIONS & TRIGGERS
-- ============================================================================

-- Function: Update incidents.updated_at on any change
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: Auto-update updated_at
CREATE TRIGGER trigger_incidents_updated_at
    BEFORE UPDATE ON incidents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function: Calculate incident duration when resolved
CREATE OR REPLACE FUNCTION calculate_incident_duration()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.end_time IS NOT NULL AND OLD.end_time IS NULL THEN
        NEW.duration_seconds = EXTRACT(EPOCH FROM (NEW.end_time - NEW.start_time))::INTEGER;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: Auto-calculate duration
CREATE TRIGGER trigger_incident_duration
    BEFORE UPDATE ON incidents
    FOR EACH ROW
    EXECUTE FUNCTION calculate_incident_duration();

-- Function: Add timeline entry on incident status change
CREATE OR REPLACE FUNCTION log_incident_status_change()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status != OLD.status THEN
        INSERT INTO incident_timeline (incident_id, event_type, description, previous_status, new_status)
        VALUES (
            NEW.id,
            'STATUS_CHANGED',
            'Incident status changed from ' || OLD.status || ' to ' || NEW.status,
            OLD.status,
            NEW.status
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: Log status changes
CREATE TRIGGER trigger_log_status_change
    AFTER UPDATE ON incidents
    FOR EACH ROW
    WHEN (OLD.status IS DISTINCT FROM NEW.status)
    EXECUTE FUNCTION log_incident_status_change();

-- ============================================================================
-- VIEWS for Common Queries
-- ============================================================================

-- View: Active incidents summary
CREATE OR REPLACE VIEW active_incidents AS
SELECT 
    i.id,
    i.incident_number,
    i.incident_type,
    i.severity,
    i.status,
    i.affected_device_count,
    i.anomaly_count,
    i.start_time,
    EXTRACT(EPOCH FROM (NOW() - i.start_time))::INTEGER AS age_seconds,
    i.primary_device,
    i.correlation_method
FROM incidents i
WHERE i.status IN ('ACTIVE', 'INVESTIGATING')
ORDER BY i.severity DESC, i.start_time DESC;

-- View: Incident statistics
CREATE OR REPLACE VIEW incident_statistics AS
SELECT 
    incident_type,
    severity,
    status,
    COUNT(*) AS total_count,
    AVG(affected_device_count) AS avg_devices_affected,
    AVG(anomaly_count) AS avg_anomalies_per_incident,
    AVG(duration_seconds) AS avg_duration_seconds,
    MIN(start_time) AS first_occurrence,
    MAX(start_time) AS last_occurrence
FROM incidents
GROUP BY incident_type, severity, status;

-- ============================================================================
-- INITIAL DATA (Optional)
-- ============================================================================

-- Insert sample incident types for reference
CREATE TABLE IF NOT EXISTS incident_type_definitions (
    incident_type VARCHAR(100) PRIMARY KEY,
    description TEXT NOT NULL,
    typical_symptoms TEXT,
    recommended_actions TEXT
);

INSERT INTO incident_type_definitions (incident_type, description, typical_symptoms, recommended_actions) VALUES
('NETWORK_PERFORMANCE', 'Network-wide performance degradation', 'Multiple devices showing HIGH_CPU, HIGH_MEMORY, or packet loss', 'Check network utilization, investigate routing issues, verify QoS configuration'),
('SECURITY_BREACH', 'Security incident or attack attempt', 'Multiple AUTH_FAILURE, UNAUTHORIZED_ACCESS events', 'Block attacking IPs, review firewall rules, check for compromised credentials'),
('CONNECTIVITY_ISSUE', 'Network connectivity problems', 'Multiple INTERFACE_DOWN, BGP_DOWN, link failures', 'Check physical connections, verify routing protocols, inspect interface status'),
('DEVICE_FAILURE', 'Single device experiencing multiple issues', 'Single device with various anomaly types', 'Investigate device health, check logs, consider device replacement or reboot'),
('CASCADE_FAILURE', 'Upstream failure causing downstream impact', 'Upstream device failure affecting connected devices', 'Identify root cause device, restore upstream service first'),
('UNKNOWN', 'Unclassified incident requiring investigation', 'Pattern not matching known incident types', 'Manual investigation required, gather more data')
ON CONFLICT (incident_type) DO NOTHING;

-- ============================================================================
-- Grant Permissions
-- ============================================================================

-- Grant permissions to application user (if needed)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO noc_admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO noc_admin;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO noc_admin;

-- ============================================================================
-- Database Ready
-- ============================================================================

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'Smart NOC PostgreSQL database initialized successfully';
    RAISE NOTICE 'Tables created: incidents, incident_anomalies, incident_timeline';
    RAISE NOTICE 'Views created: active_incidents, incident_statistics';
    RAISE NOTICE 'Triggers enabled: auto-update timestamps, duration calculation, status logging';
END $$;
