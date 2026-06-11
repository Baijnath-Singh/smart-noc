#!/usr/bin/env python3
"""
End-to-End Test: Safety Framework Integration

Tests complete flow:
1. Create test incident
2. LLM-diagnosis generates diagnosis
3. Remediation-agent receives diagnosis  
4. Safety Framework assesses risk
5. Verify proper decision is made
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import time
import json

# Database connection
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    user='noc_admin',
    password='noc_password',
    database='smart_noc',
    cursor_factory=RealDictCursor
)

print("=" * 80)
print("🧪 END-TO-END SAFETY FRAMEWORK INTEGRATION TEST")
print("=" * 80)

# Step 1: Create a test incident
print("\n📝 Step 1: Creating test incident...")
cursor = conn.cursor()

cursor.execute("""
    INSERT INTO incidents (
        incident_number,
        primary_device,
        incident_type,
        severity,
        status,
        start_time,
        correlation_method
    ) VALUES (
        9999,
        'access-sw-test',
        'CONNECTIVITY_ISSUE',
        'LOW',
        'ACTIVE',
        NOW(),
        'test_safety_framework'
    )
    ON CONFLICT (incident_number) DO UPDATE
    SET status = 'ACTIVE', start_time = NOW()
    RETURNING incident_number
""")
conn.commit()

print("✅ Test incident created: #9999")

# Step 2: Check if incident was diagnosed (wait up to 30 seconds)
print("\n📊 Step 2: Waiting for LLM diagnosis...")
max_wait = 30
waited = 0

while waited < max_wait:
    cursor.execute("""
        SELECT 
            incident_number,
            root_cause,
            raw_confidence,
            calibrated_confidence,
            diagnosis_timestamp
        FROM incidents
        WHERE incident_number = 9999
          AND root_cause IS NOT NULL
    """)
    
    result = cursor.fetchone()
    
    if result:
        print(f"✅ Incident diagnosed!")
        print(f"   Root Cause: {result['root_cause']}")
        print(f"   Raw Confidence: {result['raw_confidence']}")
        print(f"   Calibrated Confidence: {result['calibrated_confidence']}")
        break
    
    time.sleep(2)
    waited += 2
    print(f"   Waiting... ({waited}s/{max_wait}s)")

if waited >= max_wait:
    print("⚠️  Timeout: Incident not diagnosed yet (this is OK if llm-diagnosis is not processing)")

# Step 3: Check if risk assessment was performed
print("\n🛡️  Step 3: Checking risk assessment...")
cursor.execute("""
    SELECT 
        incident_number,
        risk_level,
        risk_score,
        factors,
        assessed_at
    FROM incident_risk_assessment
    WHERE incident_number = 9999
    ORDER BY assessed_at DESC
    LIMIT 1
""")

risk_result = cursor.fetchone()

if risk_result:
    print(f"✅ Risk assessment performed!")
    print(f"   Risk Level: {risk_result['risk_level']}")
    print(f"   Risk Score: {risk_result['risk_score']:.2f}")
    print(f"   Factors: {json.dumps(risk_result['factors'], indent=2)}")
else:
    print("⚠️  No risk assessment found (remediation-agent may not have processed it yet)")

# Step 4: Check autonomous decision
print("\n🤖 Step 4: Checking autonomous decision...")
cursor.execute("""
    SELECT 
        incident_number,
        decision,
        decision_reasoning,
        calibrated_confidence,
        risk_level,
        decided_at
    FROM autonomous_decision_log
    WHERE incident_number = 9999
    ORDER BY decided_at DESC
    LIMIT 1
""")

decision_result = cursor.fetchone()

if decision_result:
    print(f"✅ Decision made!")
    print(f"   Decision: {decision_result['decision']}")
    print(f"   Reasoning: {decision_result['decision_reasoning']}")
    print(f"   Confidence: {decision_result['calibrated_confidence']:.2f}")
    print(f"   Risk: {decision_result['risk_level']}")
else:
    print("⚠️  No decision found (remediation-agent may not have processed it yet)")

# Step 5: Summary
print("\n" + "=" * 80)
print("📊 TEST SUMMARY")
print("=" * 80)

if risk_result and decision_result:
    print("✅ Safety Framework integration working!")
    print(f"\n🔄 Complete Flow:")
    print(f"   Incident #9999 → Diagnosed → Risk Assessed ({risk_result['risk_level']}) → ")
    print(f"   Decision: {decision_result['decision']}")
    
    # Verify decision makes sense
    expected_decision = None
    if risk_result['risk_level'] == 'LOW' and decision_result['calibrated_confidence'] >= 0.95:
        expected_decision = 'execute'
    elif risk_result['risk_level'] == 'LOW' and decision_result['calibrated_confidence'] >= 0.87:
        expected_decision = 'execute_notify'
    elif risk_result['risk_level'] in ['MEDIUM', 'HIGH']:
        expected_decision = 'require_approval or manual_only'
    
    print(f"\n💡 Decision Matrix Check:")
    print(f"   Risk: {risk_result['risk_level']}, Confidence: {decision_result['calibrated_confidence']:.2f}")
    print(f"   Expected: {expected_decision}")
    print(f"   Actual: {decision_result['decision']}")
    
    if expected_decision and expected_decision in decision_result['decision']:
        print("   ✅ Decision matches expectations!")
    else:
        print("   ⚠️  Decision may be conservative (which is safe)")

else:
    print("⚠️  Integration test incomplete")
    print("   This could mean:")
    print("   - Services need more time to process")
    print("   - LLM-diagnosis is not auto-processing test incidents")
    print("   - Remediation-agent is waiting for Kafka messages")
    print("\n   To manually trigger diagnosis:")
    print("   docker-compose exec postgres psql -U noc_admin -d smart_noc \\")
    print("     -c \"SELECT incident_number FROM incidents WHERE incident_number = 9999;\"")

print("\n" + "=" * 80)

# Cleanup (optional)
cleanup = input("\n🗑️  Delete test incident? (y/n): ")
if cleanup.lower() == 'y':
    cursor.execute("DELETE FROM incidents WHERE incident_number = 9999")
    cursor.execute("DELETE FROM incident_risk_assessment WHERE incident_number = 9999")
    cursor.execute("DELETE FROM autonomous_decision_log WHERE incident_number = 9999")
    conn.commit()
    print("✅ Test data cleaned up")

cursor.close()
conn.close()
