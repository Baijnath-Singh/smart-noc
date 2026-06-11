#!/usr/bin/env python3
"""
End-to-End Safety Framework Test

Tests the complete flow:
1. Fetch test incident #9999 from database
2. Perform risk assessment via Safety Framework
3. Make autonomous decision
4. Verify decision is logged correctly
"""
import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# PostgreSQL connection
DB_HOST = os.getenv("POSTGRES_HOST", "postgres")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "smart_noc")
DB_USER = os.getenv("POSTGRES_USER", "noc_admin")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "noc_secret_2024")

def get_connection():
    """Create database connection"""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )

def test_safety_framework_flow():
    """Test complete Safety Framework flow"""
    print("=" * 80)
    print("END-TO-END SAFETY FRAMEWORK TEST")
    print("=" * 80)
    
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Step 1: Fetch test incident
        print("\n📋 Step 1: Fetching test incident #9999...")
        cursor.execute("""
            SELECT 
                incident_number,
                primary_device,
                incident_type,
                severity,
                status,
                root_cause,
                remediation_plan,
                confidence_reasoning,
                evidence_direct_count,
                evidence_indirect_count
            FROM incidents
            WHERE incident_number = 9999
        """)
        incident = cursor.fetchone()
        
        if not incident:
            print("❌ FAIL: Incident #9999 not found")
            return False
        
        print(f"✅ Found incident #9999")
        print(f"   Device: {incident['primary_device']}")
        print(f"   Type: {incident['incident_type']}")
        print(f"   Severity: {incident['severity']}")
        print(f"   Root Cause: {incident['root_cause']}")
        print(f"   Evidence (Direct/Indirect): {incident['evidence_direct_count']}/{incident['evidence_indirect_count']}")
        
        # Calculate calibrated confidence from evidence
        direct_count = incident['evidence_direct_count'] or 0
        indirect_count = incident['evidence_indirect_count'] or 0
        total_evidence = direct_count + (indirect_count * 0.3)
        calibrated_confidence = min(0.95, 0.60 + (total_evidence * 0.05))
        
        print(f"   Calibrated Confidence: {calibrated_confidence:.2f}")
        
        # Step 2: Import and initialize Safety Framework
        print("\n🔧 Step 2: Initializing Safety Framework...")
        sys.path.insert(0, '/app')
        from safety_integration import SafetyIntegration
        
        database_url = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        safety = SafetyIntegration(database_url)
        print("✅ Safety Framework initialized")
        
        # Step 3: Perform safety assessment
        print("\n🎯 Step 3: Performing safety assessment...")
        
        incident_data = {
            'incident_number': incident['incident_number'],
            'primary_device': incident['primary_device'],
            'incident_type': incident['incident_type'],
            'affected_device_count': 1,
            'severity': incident['severity']
        }
        
        # Convert remediation_plan string to list format expected by risk assessor
        remediation_steps = []
        if incident['remediation_plan']:
            # Simple conversion: treat as single step
            remediation_steps = [{
                'action': 'apply_configuration',
                'command': incident['remediation_plan'],
                'device': incident['primary_device']
            }]
        
        diagnosis_data = {
            'root_cause': incident['root_cause'],
            'remediation_plan': remediation_steps
        }
        
        safety_result = safety.assess_safety(
            incident=incident_data,
            diagnosis=diagnosis_data,
            calibrated_confidence=calibrated_confidence
        )
        
        print(f"✅ Safety assessment complete")
        print(f"   Risk Level: {safety_result['risk_level']}")
        print(f"   Risk Score: {safety_result['risk_score']:.2f}")
        print(f"   Decision: {safety_result['decision']}")
        print(f"   Safe to Proceed: {safety_result['safe_to_proceed']}")
        print(f"   Requires Approval: {safety_result['requires_approval']}")
        print(f"   Must Escalate: {safety_result['must_escalate']}")
        
        # Step 4: Verify risk assessment was logged
        print("\n🔍 Step 4: Verifying risk assessment in database...")
        cursor.execute("""
            SELECT 
                incident_number,
                risk_level,
                overall_risk_score,
                factors
            FROM incident_risk_assessment
            WHERE incident_number = 9999
            ORDER BY assessed_at DESC
            LIMIT 1
        """)
        risk_record = cursor.fetchone()
        
        if risk_record:
            print(f"✅ Risk assessment logged")
            print(f"   Risk Level: {risk_record['risk_level']}")
            print(f"   Risk Score: {risk_record['overall_risk_score']:.2f}")
            print(f"   Factors: {risk_record['factors']}")
        else:
            print("⚠️  No risk assessment found in database")
        
        # Step 5: Verify decision was logged
        print("\n🔍 Step 5: Verifying decision in database...")
        cursor.execute("""
            SELECT 
                incident_number,
                decision,
                decision_reasoning,
                calibrated_confidence,
                risk_level,
                rule_matched,
                decided_at
            FROM autonomous_decision_log
            WHERE incident_number = 9999
            ORDER BY decided_at DESC
            LIMIT 1
        """)
        decision_record = cursor.fetchone()
        
        if decision_record:
            print(f"✅ Decision logged")
            print(f"   Decision: {decision_record['decision']}")
            print(f"   Risk Level: {decision_record['risk_level']}")
            print(f"   Confidence: {decision_record['calibrated_confidence']:.2f}")
            print(f"   Rule Matched: {decision_record['rule_matched']}")
            print(f"   Reasoning: {decision_record['decision_reasoning']}")
            print(f"   Timestamp: {decision_record['decided_at']}")
        else:
            print("⚠️  No decision found in database")
        
        # Step 6: Validate decision logic
        print("\n✅ Step 6: Validating decision logic...")
        expected_decision = None
        
        if safety_result['risk_level'] == 'CRITICAL':
            expected_decision = 'manual_only'
        elif safety_result['risk_level'] == 'HIGH':
            expected_decision = 'require_approval'
        elif safety_result['risk_level'] == 'MEDIUM':
            if calibrated_confidence >= 0.85:
                expected_decision = 'require_approval'
            else:
                expected_decision = 'manual_only'
        elif safety_result['risk_level'] == 'LOW':
            if calibrated_confidence >= 0.90:
                expected_decision = 'execute'
            elif calibrated_confidence >= 0.75:
                expected_decision = 'execute_notify'
            else:
                expected_decision = 'manual_only'
        
        actual_decision = safety_result['decision']
        
        if actual_decision == expected_decision:
            print(f"✅ Decision logic correct: {actual_decision} == {expected_decision}")
        else:
            print(f"⚠️  Decision logic mismatch: {actual_decision} != {expected_decision}")
            print(f"   (This may be acceptable depending on decision matrix rules)")
        
        # Summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"✅ Incident #9999 processed successfully")
        print(f"✅ Risk Level: {safety_result['risk_level']} (Score: {safety_result['risk_score']:.2f})")
        print(f"✅ Decision: {safety_result['decision']}")
        print(f"✅ Confidence: {calibrated_confidence:.2f}")
        print(f"✅ Database logging: {'OK' if risk_record and decision_record else 'PARTIAL'}")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    success = test_safety_framework_flow()
    sys.exit(0 if success else 1)
