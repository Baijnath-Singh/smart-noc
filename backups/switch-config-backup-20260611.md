# Switch Configuration Backup - June 11, 2026
**Switch IP:** 10.139.38.4:5019  
**Backup Date:** 2026-06-11 18:45:00  
**Purpose:** Pre-Smart NOC syslog integration

## Current Log Configuration State

### Overview
- **Debug-Mode:** Disabled
- **Show Message Privilege:** User (non-administrative)
- **Syslog Status:** NOT CONFIGURED (no syslog targets exist)

### Active Log Targets

#### 1. memory-buffer
```
Enabled     : yes
Filter Name : DefaultFilter
Match regex : Any
Severity    : Debug-Data (through Critical)
Format      : MM/DD/YYYY HH:MM:SS.hh <Severity:Component.SubComponent.Condition> Slot:
Buffer size : 1000 messages
Percent Full: 63%
Full Alert  : None
```

#### 2. nvram
```
Enabled     : yes
Filter Name : DefaultFilter
Match regex : Any
Severity    : Warning (through Critical)
Format      : MM/DD/YYYY HH:MM:SS.hh <Severity:Component.SubComponent.Condition> Slot:
```

#### 3. console
```
Enabled     : no
Filter Name : DefaultFilter
Match regex : Any
Severity    : Info (through Critical)
Format      : MM/DD/YYYY HH:MM:SS.hh <Severity:Component.SubComponent.Condition> Slot:
```

#### 4. primary-node
```
Enabled     : yes
Filter Name : DefaultFilter
Match regex : Any
Severity    : Warning (through Critical)
```

#### 5. backup-node
```
Enabled     : yes
Filter Name : DefaultFilter
Match regex : Any
Severity    : Warning (through Critical)
```

### TLS Configuration
```
Enabled TLS Ciphers:  aes128-sha, aes128-sha256, aes256-sha256, 
                      dhe-rsa-aes128-sha256, dhe-rsa-aes256-sha256, 
                      ecdhe-rsa-aes128-sha256, ecdhe-rsa-aes256-sha384
Disabled TLS Ciphers: None
Syslog TLS TCP User Timeout: Default
Syslog TLS OCSP: On
```

## Rollback Commands (if needed)

If Smart NOC syslog causes issues, run these commands to remove it:

```bash
configure syslog delete 10.37.12.33:5000
save configuration
```

## Notes
- No existing syslog configuration found
- All current logging goes to local targets only (memory-buffer, nvram, nodes)
- Clean state for adding Smart NOC syslog without conflicts
- Console logging is currently disabled
