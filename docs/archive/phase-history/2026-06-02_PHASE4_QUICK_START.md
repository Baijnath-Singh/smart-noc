# Phase 4: LLM Diagnosis Service - Quick Start Guide

## Overview

Phase 4 adds AI-powered root cause analysis and remediation recommendations to Smart NOC. The LLM Diagnosis Service consumes correlated incidents from Kafka, analyzes them using GPT-4 or Claude, and generates:

- **Root Cause Analysis**: Technical explanation of what caused the incident
- **Confidence Score**: 0.0-1.0 rating of diagnosis accuracy
- **Remediation Plan**: Step-by-step actions (IMMEDIATE, SHORT_TERM, LONG_TERM)
- **Escalation Criteria**: When to involve senior engineers
- **Preventive Measures**: How to avoid future incidents

## Architecture

```
Kafka (incidents) → LLM Diagnosis Service → PostgreSQL
                         ↓
                    GPT-4/Claude API
                         ↓
                  Context Building
                  - Incident metadata
                  - Grouped anomalies
                  - Device history
                  - Similar past incidents
                         ↓
                  Prompt Engineering
                  - System prompt
                  - Incident-type templates
                  - Few-shot examples
                         ↓
                  Response Parsing
                  - JSON structured output
                  - Confidence validation
                  - Remediation formatting
```

## Prerequisites

1. **Phase 0-3 Complete**: Log pipeline, anomaly detection, and correlation engine operational
2. **LLM API Key**: OpenAI or Anthropic API access
3. **Sufficient API Credits**: Estimate $0.03-0.10 per incident diagnosis (GPT-4)

## Setup Instructions

### Step 1: Get LLM API Key

**Option A: OpenAI**
1. Create account at https://platform.openai.com/
2. Navigate to API Keys
3. Create new secret key
4. Copy the key (starts with `sk-...`)

**Option B: Anthropic Claude**
1. Create account at https://console.anthropic.com/
2. Navigate to API Keys
3. Create new key
4. Copy the key

### Step 2: Configure Environment

Create `.env` file in project root:

```bash
# Copy from example
cd /mnt/c/Users/baisingh/ng-iam/smart-noc/services/llm-diagnosis
cp .env.example ../../.env

# Edit .env file
nano ../../.env
```

Add your API key:

```env
# OpenAI Configuration
LLM_PROVIDER=openai
LLM_MODEL=gpt-4-turbo-preview
LLM_API_KEY=sk-your-actual-api-key-here

# OR Anthropic Configuration
# LLM_PROVIDER=anthropic
# LLM_MODEL=claude-3-sonnet-20240229
# LLM_API_KEY=sk-ant-your-api-key-here

# Diagnosis Settings
DIAGNOSIS_MIN_CONFIDENCE=0.3
DIAGNOSIS_DELAY_SECONDS=5
LLM_MAX_TOKENS=2000
LLM_TEMPERATURE=0.3

# Feature Flags
ENABLE_DIAGNOSIS=true
ENABLE_REMEDIATION=true
ENABLE_COST_TRACKING=true
```

**⚠️ IMPORTANT**: Never commit `.env` file to git! It's in `.gitignore`.

### Step 3: Build and Start Service

From WSL terminal:

```bash
cd /mnt/c/Users/baisingh/ng-iam/smart-noc

# Build the LLM diagnosis service
docker compose build llm-diagnosis

# Start the service
docker compose up -d llm-diagnosis

# Check logs
docker compose logs -f llm-diagnosis
```

Expected startup logs:
```
=== Smart NOC LLM Diagnosis Service ===
Provider: openai/gpt-4-turbo-preview
Min Confidence: 0.3
LLM Client initialized: openai/gpt-4-turbo-preview
Context Builder initialized
Kafka consumer created: incidents
Kafka producer created: incidents-diagnosed
Diagnosis service initialized successfully
Starting diagnosis service loop...
```

### Step 4: Verify Service Health

```bash
# Check service is running
docker compose ps llm-diagnosis

# Should show: Up (healthy)

# Check database schema
docker compose exec postgres psql -U noc_admin -d smart_noc \\
  -c "SELECT column_name FROM information_schema.columns WHERE table_name='incidents' AND column_name LIKE '%diagnosis%';"

# Should show: root_cause, root_cause_confidence, remediation_plan,
#              diagnosis_timestamp, llm_model, diagnosis_metadata
```

### Step 5: Test with Sample Incident

Generate a test incident:

```bash
cd /mnt/c/Users/baisingh/ng-iam/smart-noc/services/log-generator
source ../../venv/bin/activate

# Generate DEVICE_FAILURE incident
python generate_scenarios.py --scenario chaos --count 5
```

Wait 10-15 seconds, then check diagnosis:

```bash
# Query recent incidents with diagnosis
docker compose exec postgres psql -U noc_admin -d smart_noc -c "
SELECT 
    incident_number,
    incident_type,
    severity,
    root_cause_confidence,
    LEFT(root_cause, 100) as root_cause_preview,
    diagnosis_timestamp
FROM incidents
WHERE root_cause IS NOT NULL
ORDER BY created_at DESC
LIMIT 5;"
```

Expected output:
```
 incident_number | incident_type  | severity | root_cause_confidence |                  root_cause_preview                  
-----------------+----------------+----------+-----------------------+-----------------------------------------------------
           23401 | DEVICE_FAILURE | MEDIUM   |                  0.87 | Core-router-01 experiencing cascading failures...
```

### Step 6: View Full Diagnosis

```bash
docker compose exec postgres psql -U noc_admin -d smart_noc -c "
SELECT 
    incident_number,
    root_cause,
    remediation_plan::text,
    diagnosis_metadata::text
FROM incidents
WHERE incident_number = 23401;"
```

The remediation_plan is a JSON array of steps:
```json
[
  {
    "priority": "IMMEDIATE",
    "step": 1,
    "action": "Verify physical cable connection on GigE0/1",
    "command": "show interfaces GigE0/1",
    "expected_outcome": "Interface shows 'up/up' status",
    "duration_minutes": 2
  },
  ...
]
```

## Configuration Options

### LLM Models

**OpenAI Options:**
- `gpt-4-turbo-preview`: Best quality, higher cost ($0.01/1K input, $0.03/1K output)
- `gpt-4`: Stable, known performance
- `gpt-3.5-turbo`: Faster, cheaper, lower quality ($0.0005/1K input)

**Anthropic Options:**
- `claude-3-opus-20240229`: Best reasoning
- `claude-3-sonnet-20240229`: Balanced (recommended)
- `claude-3-haiku-20240307`: Fastest, cheapest

### Diagnosis Parameters

```env
# Minimum confidence to accept diagnosis (0.0-1.0)
DIAGNOSIS_MIN_CONFIDENCE=0.3

# Wait N seconds after incident creation before diagnosing
# (ensures correlation is complete)
DIAGNOSIS_DELAY_SECONDS=5

# Maximum tokens for LLM response
LLM_MAX_TOKENS=2000

# Temperature: 0.0=focused, 1.0=creative
LLM_TEMPERATURE=0.3

# Context limits
CONTEXT_MAX_ANOMALIES=50
CONTEXT_HISTORICAL_INCIDENTS=5
```

### Feature Flags

```env
# Enable/disable diagnosis generation
ENABLE_DIAGNOSIS=true

# Include remediation steps in output
ENABLE_REMEDIATION=true

# Track API costs in logs and metadata
ENABLE_COST_TRACKING=true

# Cache similar incidents (not implemented yet)
ENABLE_CACHE=false
```

## Cost Management

### Estimations

**Per Incident (GPT-4-turbo):**
- Input tokens: ~2000 (incident + context)
- Output tokens: ~1000 (diagnosis + remediation)
- Cost: ~$0.05/incident

**Daily at 500 incidents/day:**
- Total: ~$25/day
- Monthly: ~$750/month

**Optimization Strategies:**
1. Use `gpt-3.5-turbo` for LOW/MEDIUM severity incidents
2. Increase `DIAGNOSIS_MIN_CONFIDENCE` to reduce retries
3. Set `DIAGNOSIS_DELAY_SECONDS` higher to batch similar incidents
4. Use Claude Haiku for faster, cheaper diagnosis ($0.00025/1K input)

### Cost Tracking

View costs in database:

```bash
docker compose exec postgres psql -U noc_admin -d smart_noc -c "
SELECT 
    COUNT(*) as total_diagnoses,
    SUM((diagnosis_metadata->>'total_tokens')::int) as total_tokens,
    SUM((diagnosis_metadata->>'estimated_cost_usd')::numeric) as total_cost_usd,
    AVG((diagnosis_metadata->>'estimated_cost_usd')::numeric) as avg_cost_per_diagnosis
FROM incidents
WHERE diagnosis_timestamp >= NOW() - INTERVAL '24 hours';"
```

Check service logs:
```bash
docker compose logs llm-diagnosis | grep "Stats:"
```

Example output:
```
Stats: Processed=20, Diagnosed=18, Failed=1, Skipped=1, Rate=3.6/min, Tokens=35420, Cost=$1.78
```

## Troubleshooting

### Issue: Service won't start

**Check API key:**
```bash
# View environment variables
docker compose exec llm-diagnosis env | grep LLM
```

**Check logs:**
```bash
docker compose logs llm-diagnosis | tail -50
```

Common errors:
- `Configuration error: LLM_API_KEY is required` → Set API key in `.env`
- `Invalid LLM_PROVIDER` → Must be `openai`, `anthropic`, or `azure`
- `OpenAI API error: 401` → API key invalid or expired

### Issue: No diagnoses generated

**Check if incidents are being created:**
```bash
# Count recent incidents
docker compose exec postgres psql -U noc_admin -d smart_noc -c "
SELECT COUNT(*) FROM incidents WHERE created_at >= NOW() - INTERVAL '1 hour';"
```

**Check diagnosis delay:**
```bash
# Incidents waiting for diagnosis
docker compose exec postgres psql -U noc_admin -d smart_noc -c "
SELECT 
    COUNT(*) as pending_diagnosis,
    MIN(AGE(NOW(), created_at)) as oldest_incident_age
FROM incidents
WHERE root_cause IS NULL;"
```

If incidents are >5 minutes old without diagnosis, check service logs.

### Issue: Low confidence diagnoses

**View confidence distribution:**
```bash
docker compose exec postgres psql -U noc_admin -d smart_noc -c "
SELECT 
    CASE 
        WHEN root_cause_confidence >= 0.8 THEN 'HIGH (0.8-1.0)'
        WHEN root_cause_confidence >= 0.5 THEN 'MEDIUM (0.5-0.8)'
        ELSE 'LOW (<0.5)'
    END as confidence_range,
    COUNT(*) as count
FROM incidents
WHERE root_cause IS NOT NULL
GROUP BY 1
ORDER BY 1;"
```

**Improve confidence:**
1. Increase `CONTEXT_MAX_ANOMALIES` to provide more data
2. Use `gpt-4` instead of `gpt-3.5-turbo`
3. Review prompt templates in `prompts/system_prompts.py`
4. Ensure device history and similar incidents are available

### Issue: API rate limits

OpenAI rate limits (Tier 1):
- GPT-4-turbo: 10,000 requests/day, 300 requests/minute
- GPT-3.5-turbo: 10,000 requests/day, 3,500 requests/minute

**Solutions:**
1. Add retry logic (already implemented via `tenacity`)
2. Reduce diagnosis rate by increasing delay
3. Upgrade OpenAI tier
4. Switch to Anthropic (higher limits)

Error in logs:
```
Error 429: Rate limit exceeded. Retrying in X seconds...
```

## Monitoring

### View Diagnosis Statistics

```bash
# Daily stats
docker compose exec postgres psql -U noc_admin -d smart_noc -c "
SELECT * FROM diagnosis_statistics;"
```

Output:
```
 total_incidents | diagnosed_incidents | pending_diagnosis | high_confidence | avg_confidence | avg_diagnosis_delay_seconds 
-----------------+---------------------+-------------------+-----------------+----------------+-----------------------------
             142 |                 138 |                 4 |              95 |          0.812 |                        8.32
```

### View Diagnosis History

All diagnosis attempts (including failures):
```bash
docker compose exec postgres psql -U noc_admin -d smart_noc -c "
SELECT 
    incident_id,
    diagnosis_version,
    root_cause_confidence,
    llm_model,
    tokens_used,
    diagnosisduration_ms,
    created_at
FROM incident_diagnosis_history
ORDER BY created_at DESC
LIMIT 10;"
```

### Grafana Integration (Coming Soon)

Phase 4 will add diagnosis panels to the incidents dashboard:
- Root Cause Analysis panel
- Confidence gauge
- Remediation steps table
- Cost tracking stats

## Next Steps

With Phase 4 operational:

1. **Review diagnoses for quality**: Check first 10-20 diagnoses manually
2. **Tune prompts**: Edit `services/llm-diagnosis/prompts/system_prompts.py` if needed
3. **Monitor costs**: Set budget alerts in OpenAI dashboard
4. **Optimize model selection**: Test gpt-3.5 vs gpt-4 trade-offs
5. **Prepare for Phase 5**: Automated remediation with Ansible integration

## Support

**View service status:**
```bash
docker compose ps llm-diagnosis
docker compose logs -f llm-diagnosis
```

**Restart service:**
```bash
docker compose restart llm-diagnosis
```

**Stop service (to save API costs):**
```bash
docker compose stop llm-diagnosis
```

**Full rebuild after code changes:**
```bash
docker compose down llm-diagnosis
docker compose build llm-diagnosis
docker compose up -d llm-diagnosis
```

## References

- OpenAI API Docs: https://platform.openai.com/docs
- Anthropic Claude Docs: https://docs.anthropic.com/claude/reference
- Phase 4 Architecture: See `PHASE4_ARCHITECTURE.md` (coming soon)
- Prompt Engineering: `services/llm-diagnosis/prompts/system_prompts.py`
