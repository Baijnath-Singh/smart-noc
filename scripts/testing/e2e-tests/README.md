# End-to-End Test Scripts

This directory contains comprehensive end-to-end test scripts for validating the complete Smart NOC pipeline.

## Test Scripts

### test_full_e2e.sh
Comprehensive E2E test that validates the entire pipeline from syslog ingestion through incident diagnosis.

**What it tests:**
- Sends multiple interface down events to trigger correlation
- Waits for correlation engine to create incident
- Validates LLM diagnosis with EXOS enrichment
- Verifies EXOS-specific commands in remediation plan

**Usage:**
```bash
cd /home/user/ng-iam/smart-noc
./scripts/testing/e2e-tests/test_full_e2e.sh
```

### test_flapping_e2e.sh
Specialized E2E test for interface flapping scenarios.

**What it tests:**
- Generates 8 alternating UP/DOWN events (flapping pattern)
- Validates anomaly detection with enrichment
- Checks correlation engine creates HIGH severity incident
- Verifies LLM diagnosis completion
- Extracts and validates EXOS-specific commands

**Usage:**
```bash
cd /home/user/ng-iam/smart-noc
./scripts/testing/e2e-tests/test_flapping_e2e.sh
```

## Test Flow

```
Syslog Event (Port X:Y link DOWN)
    ↓
Logstash (parse + HTTP enrichment)
    ↓
Kafka network-logs (with device_cli_syntax)
    ↓
Anomaly Detector (detect + propagate enrichment)
    ↓
Kafka anomalies (enriched anomaly data)
    ↓
Correlation Engine (create incident)
    ↓
Kafka incidents
    ↓
LLM Diagnosis (vendor-specific commands)
    ↓
Database (remediation plan with EXOS commands)
```

## Expected Results

✅ Enrichment service responds in <100ms (with caching)
✅ Event type detected correctly (INTERFACE_UP/DOWN)
✅ Interface extracted in EXOS format (X:Y)
✅ Anomaly contains 6 enrichment fields
✅ Incident created from multiple anomalies
✅ LLM generates vendor-specific commands:
   - `show port X:Y information detail` (not "show interface")
   - `enable port X:Y` (not "no shutdown")
   - `show edp ports X:Y detail`

## Date Created
June 13, 2026
