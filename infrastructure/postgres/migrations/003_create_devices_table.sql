-- ==============================================================================
-- Device Inventory Table
-- ==============================================================================
-- Stores comprehensive device information for accurate remediation and context
-- This table maps device IPs/hostnames to vendor, model, OS, and CLI syntax

CREATE TABLE IF NOT EXISTS devices (
    device_id VARCHAR(255) PRIMARY KEY,           -- Hostname or IP (primary identifier)
    hostname VARCHAR(255),                        -- DNS hostname
    management_ip INET,                           -- Management IP address
    vendor VARCHAR(50) NOT NULL,                  -- 'Extreme Networks', 'Cisco', 'Juniper', 'Aruba'
    device_family VARCHAR(50) NOT NULL,           -- 'EXOS', 'VOSS', 'IOS', 'IOS-XR', 'NXOS', 'JUNOS'
    model VARCHAR(100),                           -- 'X690-48x-2c-f', 'VSP8600', 'Catalyst9300', etc.
    os_version VARCHAR(50),                       -- '32.6.1.2', '16.9.5', '22.3R1', etc.
    cli_syntax VARCHAR(50),                       -- 'EXOS', 'IOS', 'JUNOS', 'NXOS'
    serial_number VARCHAR(100),                   -- Device serial number
    location VARCHAR(255),                        -- Physical location
    device_role VARCHAR(50),                      -- 'core', 'distribution', 'access', 'edge', 'border'
    site VARCHAR(100),                            -- Site/datacenter name
    snmp_community VARCHAR(100),                  -- SNMP read community (encrypted)
    ssh_username VARCHAR(50),                     -- SSH username for automation
    api_endpoint VARCHAR(255),                    -- REST API endpoint if available
    supports_netconf BOOLEAN DEFAULT false,       -- NETCONF support
    supports_restconf BOOLEAN DEFAULT false,      -- RESTCONF support
    last_seen TIMESTAMP,                          -- Last time device was reachable
    status VARCHAR(20) DEFAULT 'active',          -- 'active', 'maintenance', 'decommissioned'
    notes TEXT,                                   -- Additional notes
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_devices_management_ip ON devices(management_ip);
CREATE INDEX IF NOT EXISTS idx_devices_hostname ON devices(hostname);
CREATE INDEX IF NOT EXISTS idx_devices_vendor ON devices(vendor);
CREATE INDEX IF NOT EXISTS idx_devices_family ON devices(device_family);
CREATE INDEX IF NOT EXISTS idx_devices_role ON devices(device_role);
CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status);

-- Link to existing device_criticality table
ALTER TABLE device_criticality 
ADD COLUMN IF NOT EXISTS device_id VARCHAR(255) REFERENCES devices(device_id);

-- Sample data for your Extreme Networks switch
INSERT INTO devices (
    device_id, 
    hostname,
    management_ip, 
    vendor, 
    device_family, 
    model, 
    os_version,
    cli_syntax,
    device_role,
    location,
    status
) VALUES 
(
    '10.139.38.188',
    'core-switch-stack',
    '10.139.38.188'::inet,
    'Extreme Networks',
    'EXOS',
    'X690-48x (2-slot stack)',
    '32.6.1.2',
    'EXOS',
    'core',
    'Main Datacenter',
    'active'
)
ON CONFLICT (device_id) DO UPDATE SET
    vendor = EXCLUDED.vendor,
    device_family = EXCLUDED.device_family,
    model = EXCLUDED.model,
    os_version = EXCLUDED.os_version,
    updated_at = NOW();

-- Create a view for easy device context lookup
CREATE OR REPLACE VIEW v_device_context AS
SELECT 
    d.device_id,
    d.hostname,
    d.management_ip,
    d.vendor,
    d.device_family,
    d.model,
    d.os_version,
    d.cli_syntax,
    d.device_role,
    d.location,
    dc.criticality,
    dc.business_impact,
    dc.requires_approval
FROM devices d
LEFT JOIN device_criticality dc ON d.device_id = dc.device_name;

-- Add comments for documentation
COMMENT ON TABLE devices IS 'Comprehensive device inventory for Smart NOC';
COMMENT ON COLUMN devices.device_id IS 'Primary identifier - hostname or IP';
COMMENT ON COLUMN devices.cli_syntax IS 'CLI command syntax family for remediation scripts';
COMMENT ON COLUMN devices.device_family IS 'OS/Platform family for KB article matching';
