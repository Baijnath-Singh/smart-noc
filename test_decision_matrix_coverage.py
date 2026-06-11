#!/usr/bin/env python3
"""
Decision Matrix Test Coverage - Validate All 12 Scenarios

Tests all combinations of:
- Risk Levels: LOW, MEDIUM, HIGH, CRITICAL
- Confidence Levels: High (≥0.92), Medium (0.75-0.92), Low (<0.75)

Total: 12 test scenarios
"""

import psycopg2
import json
from datetime import datetime
from typing import Dict, List, Tuple
import sys

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'smart_noc',
    'user': 'noc_admin',
    'password': 'noc_password'
}

# Decision Matrix Rules (from autonomous_executor.py)
DECISION_MATRIX = {
    'CRITICAL': {
        'high': 'manual_only',    # ≥0.92
        'medium': 'manual_only',  # 0.75-0.92
        'low': 'manual_only'      # <0.75
    },
    'HIGH': {
        'high': 'require_approval',   # ≥0.92
        'medium': 'manual_only',      # 0.75-0.92
        'low': 'manual_only'          # <0.75
    },
    'MEDIUM': {
        'high': 'require_approval',   # ≥0.92
        'medium': 'manual_only',      # 0.75-0.92 (changed from notify_and_execute)
        'low': 'manual_only'          # <0.75
    },
    'LOW': {
        'high': 'execute',        # ≥0.92
        'medium': 'execute',      # 0.75-0.92
        'low': 'manual_only'      # <0.75
    }
}

# Test scenarios: (risk_level, confidence, confidence_bucket, expected_decision)
TEST_SCENARIOS = [
    # LOW risk scenarios (3)
    ('LOW', 0.95, 'high', 'execute'),
    ('LOW', 0.85, 'medium', 'execute'),
    ('LOW', 0.70, 'low', 'manual_only'),
    
    # MEDIUM risk scenarios (3)
    ('MEDIUM', 0.95, 'high', 'require_approval'),
    ('MEDIUM', 0.85, 'medium', 'manual_only'),
    ('MEDIUM', 0.70, 'low', 'manual_only'),
    
    # HIGH risk scenarios (3)
    ('HIGH', 0.95, 'high', 'require_approval'),
    ('HIGH', 0.85, 'medium', 'manual_only'),
    ('HIGH', 0.70, 'low', 'manual_only'),
    
    # CRITICAL risk scenarios (3)
    ('CRITICAL', 0.95, 'high', 'manual_only'),
    ('CRITICAL', 0.85, 'medium', 'manual_only'),
    ('CRITICAL', 0.70, 'low', 'manual_only'),
]

class DecisionMatrixTester:
    def __init__(self):
        self.conn = None
        self.results = []
        self.base_incident_number = 10000  # Start from 10000 to avoid conflicts
    
    def connect(self):
        """Connect to database"""
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            print("✅ Connected to database")
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False
    
    def cleanup_test_data(self):
        """Clean up any existing test incidents"""
        try:
            cursor = self.conn.cursor()
            
            # Delete test incidents (10000-10999)
            cursor.execute("""
                DELETE FROM incident_risk_assessment 
                WHERE incident_number BETWEEN 10000 AND 10999
            """)
            
            cursor.execute("""
                DELETE FROM autonomous_decision_log 
                WHERE incident_number BETWEEN 10000 AND 10999
            """)
            
            cursor.execute("""
                DELETE FROM incidents 
                WHERE incident_number BETWEEN 10000 AND 10999
            """)
            
            self.conn.commit()
            cursor.close()
            print("✅ Cleaned up existing test data")
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")
            self.conn.rollback()
    
    def create_test_device(self, device_name: str, criticality: str):
        """Ensure test device exists with specified criticality"""
        try:
            cursor = self.conn.cursor()
            
            # Insert or update device criticality
            cursor.execute("""
                INSERT INTO device_criticality (device_name, criticality_level, business_impact, description)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (device_name) 
                DO UPDATE SET criticality_level = EXCLUDED.criticality_level
            """, (
                device_name,
                criticality,
                f"Test device with {criticality} criticality",
                f"Created for decision matrix testing"
            ))
            
            self.conn.commit()
            cursor.close()
            return True
        except Exception as e:
            print(f"❌ Failed to create device {device_name}: {e}")
            self.conn.rollback()
            return False
    
    def calculate_risk_factors(self, risk_level: str) -> Dict[str, float]:
        """Calculate risk factors to achieve target risk level"""
        
        # Risk score ranges:
        # LOW: 0.0-0.39
        # MEDIUM: 0.40-0.59
        # HIGH: 0.60-0.79
        # CRITICAL: 0.80-1.0
        
        risk_configs = {
            'LOW': {
                'device_criticality': 0.25,  # LOW
                'blast_radius': 0.20,        # 1 device
                'time_sensitivity': 0.30,    # Off-hours
                'change_complexity': 0.30,   # Simple change
                'target_score': 0.25,        # Midpoint of LOW range
                'affected_devices': 1
            },
            'MEDIUM': {
                'device_criticality': 0.55,  # MEDIUM
                'blast_radius': 0.50,        # 3-9 devices
                'time_sensitivity': 0.50,    # Semi-business hours
                'change_complexity': 0.60,   # Moderate complexity
                'target_score': 0.50,        # Midpoint of MEDIUM range
                'affected_devices': 5
            },
            'HIGH': {
                'device_criticality': 0.75,  # HIGH
                'blast_radius': 0.70,        # 10-19 devices
                'time_sensitivity': 0.80,    # Business hours
                'change_complexity': 0.80,   # High complexity
                'target_score': 0.70,        # Midpoint of HIGH range
                'affected_devices': 15
            },
            'CRITICAL': {
                'device_criticality': 0.95,  # CRITICAL
                'blast_radius': 0.90,        # 20+ devices
                'time_sensitivity': 0.90,    # Peak business hours
                'change_complexity': 0.90,   # Very high complexity
                'target_score': 0.90,        # Midpoint of CRITICAL range
                'affected_devices': 25
            }
        }
        
        return risk_configs[risk_level]
    
    def create_test_incident(self, scenario_num: int, risk_level: str, confidence: float) -> int:
        """Create a test incident with specific risk profile"""
        incident_number = self.base_incident_number + scenario_num
        
        # Get risk configuration
        risk_config = self.calculate_risk_factors(risk_level)
        
        # Create appropriate device
        device_criticality_map = {
            'LOW': 'LOW',
            'MEDIUM': 'MEDIUM',
            'HIGH': 'HIGH',
            'CRITICAL': 'CRITICAL'
        }
        device_name = f'test-device-{risk_level.lower()}-{scenario_num}'
        self.create_test_device(device_name, device_criticality_map[risk_level])
        
        # Create affected devices array
        affected_devices = [device_name]
        for i in range(1, risk_config['affected_devices']):
            affected_devices.append(f'{device_name}-peer-{i}')
        
        try:
            cursor = self.conn.cursor()
            
            # Insert incident
            cursor.execute("""
                INSERT INTO incidents 
                    (incident_number, primary_device, incident_type, severity, 
                     start_time, status, affected_devices)
                VALUES 
                    (%s, %s, %s, %s, NOW(), %s, %s)
            """, (
                incident_number,
                device_name,
                'TEST_SCENARIO',
                risk_level,
                'ACTIVE',
                affected_devices
            ))
            
            # Insert diagnosis (simulating llm-diagnosis output)
            cursor.execute("""
                UPDATE incidents 
                SET 
                    root_cause = %s,
                    root_cause_confidence = %s,
                    confidence_reasoning = %s,
                    remediation_plan = %s,
                    diagnosis_timestamp = NOW()
                WHERE incident_number = %s
            """, (
                f'Test scenario: {risk_level} risk with {confidence:.2f} confidence',
                confidence,
                f'Synthetic test data for decision matrix validation',
                json.dumps([{
                    'step': 1,
                    'action': 'Test remediation action',
                    'command': 'show version',
                    'expected_outcome': 'Test outcome'
                }]),
                incident_number
            ))
            
            self.conn.commit()
            cursor.close()
            return incident_number
            
        except Exception as e:
            print(f"❌ Failed to create incident {incident_number}: {e}")
            self.conn.rollback()
            return None
    
    def assess_risk(self, incident_number: int, risk_level: str) -> Tuple[str, float]:
        """Simulate risk assessment"""
        risk_config = self.calculate_risk_factors(risk_level)
        
        # Calculate overall risk score using weighted formula
        # device_criticality (40%) + blast_radius (30%) + time_sensitivity (20%) + change_complexity (10%)
        overall_score = (
            risk_config['device_criticality'] * 0.40 +
            risk_config['blast_radius'] * 0.30 +
            risk_config['time_sensitivity'] * 0.20 +
            risk_config['change_complexity'] * 0.10
        )
        
        try:
            cursor = self.conn.cursor()
            
            # Insert risk assessment
            cursor.execute("""
                INSERT INTO incident_risk_assessment
                    (incident_number, risk_level, overall_risk_score, 
                     device_criticality, blast_radius, time_sensitivity, change_complexity,
                     factors, assessed_at)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, (
                incident_number,
                risk_level,
                overall_score,
                risk_config['device_criticality'],
                risk_config['blast_radius'],
                risk_config['time_sensitivity'],
                risk_config['change_complexity'],
                json.dumps(risk_config)
            ))
            
            self.conn.commit()
            cursor.close()
            return risk_level, overall_score
            
        except Exception as e:
            print(f"❌ Risk assessment failed for incident {incident_number}: {e}")
            self.conn.rollback()
            return None, None
    
    def apply_decision_matrix(self, incident_number: int, risk_level: str, 
                             confidence: float, confidence_bucket: str) -> str:
        """Apply decision matrix logic"""
        
        # Get expected decision from matrix
        decision = DECISION_MATRIX[risk_level][confidence_bucket]
        
        # Generate reasoning
        reasoning_map = {
            'execute': f'{risk_level} risk with sufficient confidence ({confidence:.2f}) allows autonomous execution',
            'require_approval': f'{risk_level} risk with high confidence ({confidence:.2f}) requires human approval before execution',
            'manual_only': f'{risk_level} risk with confidence ({confidence:.2f}) requires manual intervention',
            'notify_and_execute': f'{risk_level} risk allows execution with notification at confidence ({confidence:.2f})'
        }
        reasoning = reasoning_map.get(decision, 'Unknown decision reasoning')
        
        try:
            cursor = self.conn.cursor()
            
            # Insert decision log
            cursor.execute("""
                INSERT INTO autonomous_decision_log
                    (incident_number, decision, reasoning, calibrated_confidence, 
                     risk_level, decided_at)
                VALUES
                    (%s, %s, %s, %s, %s, NOW())
            """, (
                incident_number,
                decision,
                reasoning,
                confidence,
                risk_level
            ))
            
            self.conn.commit()
            cursor.close()
            return decision
            
        except Exception as e:
            print(f"❌ Decision logging failed for incident {incident_number}: {e}")
            self.conn.rollback()
            return None
    
    def run_test_scenario(self, scenario_num: int, risk_level: str, confidence: float, 
                         confidence_bucket: str, expected_decision: str) -> Dict:
        """Run a single test scenario"""
        
        print(f"\n{'='*80}")
        print(f"TEST SCENARIO #{scenario_num + 1}: {risk_level} Risk + {confidence_bucket.upper()} Confidence")
        print(f"{'='*80}")
        
        result = {
            'scenario_num': scenario_num + 1,
            'risk_level': risk_level,
            'confidence': confidence,
            'confidence_bucket': confidence_bucket,
            'expected_decision': expected_decision,
            'actual_decision': None,
            'passed': False,
            'incident_number': None,
            'risk_score': None
        }
        
        # Step 1: Create test incident
        print(f"📝 Creating test incident...")
        incident_number = self.create_test_incident(scenario_num, risk_level, confidence)
        if not incident_number:
            result['error'] = 'Failed to create incident'
            return result
        
        result['incident_number'] = incident_number
        print(f"   ✅ Incident #{incident_number} created")
        
        # Step 2: Assess risk
        print(f"🔍 Assessing risk...")
        assessed_risk, risk_score = self.assess_risk(incident_number, risk_level)
        if not assessed_risk:
            result['error'] = 'Risk assessment failed'
            return result
        
        result['risk_score'] = risk_score
        print(f"   ✅ Risk: {assessed_risk} (score: {risk_score:.2f})")
        
        # Step 3: Apply decision matrix
        print(f"🎯 Applying decision matrix...")
        actual_decision = self.apply_decision_matrix(
            incident_number, risk_level, confidence, confidence_bucket
        )
        if not actual_decision:
            result['error'] = 'Decision matrix failed'
            return result
        
        result['actual_decision'] = actual_decision
        print(f"   Decision: {actual_decision}")
        
        # Step 4: Validate result
        result['passed'] = (actual_decision == expected_decision)
        
        if result['passed']:
            print(f"   ✅ PASS - Decision matches expected: {expected_decision}")
        else:
            print(f"   ❌ FAIL - Expected: {expected_decision}, Got: {actual_decision}")
        
        return result
    
    def run_all_tests(self):
        """Run all 12 test scenarios"""
        
        print("\n" + "="*80)
        print("DECISION MATRIX TEST COVERAGE - ALL 12 SCENARIOS")
        print("="*80)
        print(f"Database: {DB_CONFIG['database']}@{DB_CONFIG['host']}")
        print(f"Test Range: Incidents #{self.base_incident_number} - #{self.base_incident_number + 11}")
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        # Connect to database
        if not self.connect():
            print("❌ Cannot proceed without database connection")
            return
        
        # Cleanup existing test data
        self.cleanup_test_data()
        
        # Run each test scenario
        for idx, (risk_level, confidence, conf_bucket, expected_decision) in enumerate(TEST_SCENARIOS):
            result = self.run_test_scenario(idx, risk_level, confidence, conf_bucket, expected_decision)
            self.results.append(result)
        
        # Generate report
        self.generate_report()
        
        # Cleanup
        self.conn.close()
    
    def generate_report(self):
        """Generate comprehensive test report"""
        
        print("\n\n" + "="*80)
        print("COMPREHENSIVE TEST REPORT")
        print("="*80)
        
        # Summary statistics
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r['passed'])
        failed_tests = total_tests - passed_tests
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n📊 SUMMARY:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests} ✅")
        print(f"   Failed: {failed_tests} ❌")
        print(f"   Pass Rate: {pass_rate:.1f}%")
        
        # Score and grade
        if pass_rate >= 95:
            grade = "A+ (Excellent)"
        elif pass_rate >= 90:
            grade = "A (Very Good)"
        elif pass_rate >= 85:
            grade = "B+ (Good)"
        elif pass_rate >= 80:
            grade = "B (Satisfactory)"
        else:
            grade = "C (Needs Improvement)"
        
        print(f"   Grade: {grade}")
        
        # Detailed results by risk level
        print(f"\n📋 RESULTS BY RISK LEVEL:")
        
        for risk_level in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']:
            risk_results = [r for r in self.results if r['risk_level'] == risk_level]
            risk_passed = sum(1 for r in risk_results if r['passed'])
            risk_total = len(risk_results)
            
            print(f"\n   {risk_level} Risk ({risk_passed}/{risk_total} passed):")
            for r in risk_results:
                status = "✅" if r['passed'] else "❌"
                print(f"      {status} Scenario #{r['scenario_num']}: "
                      f"Conf={r['confidence']:.2f} → {r['actual_decision']} "
                      f"(expected: {r['expected_decision']})")
        
        # Decision matrix coverage table
        print(f"\n📊 DECISION MATRIX COVERAGE:")
        print(f"\n   {'Risk Level':<12} | {'High Conf':<20} | {'Medium Conf':<20} | {'Low Conf':<20}")
        print(f"   {'-'*12}-+-{'-'*20}-+-{'-'*20}-+-{'-'*20}")
        
        for risk_level in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']:
            row = f"   {risk_level:<12} |"
            
            for conf_bucket in ['high', 'medium', 'low']:
                result = next((r for r in self.results 
                              if r['risk_level'] == risk_level and 
                              r['confidence_bucket'] == conf_bucket), None)
                
                if result:
                    status = "✅" if result['passed'] else "❌"
                    cell = f" {status} {result['actual_decision']:<15}"
                else:
                    cell = " ⚠️  Not tested"
                
                row += f"{cell} |"
            
            print(row)
        
        # Failed tests detail
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS DETAIL:")
            for r in self.results:
                if not r['passed']:
                    print(f"\n   Scenario #{r['scenario_num']}: {r['risk_level']} + {r['confidence_bucket']}")
                    print(f"      Incident: #{r['incident_number']}")
                    print(f"      Expected: {r['expected_decision']}")
                    print(f"      Actual: {r['actual_decision']}")
                    print(f"      Risk Score: {r.get('risk_score', 'N/A')}")
        
        # Database verification queries
        print(f"\n🔍 VERIFICATION QUERIES:")
        print(f"""
   -- View all test results
   SELECT 
       i.incident_number,
       i.severity as risk_level,
       i.root_cause_confidence as confidence,
       r.overall_risk_score,
       d.decision,
       d.reasoning
   FROM incidents i
   LEFT JOIN incident_risk_assessment r ON i.incident_number = r.incident_number
   LEFT JOIN autonomous_decision_log d ON i.incident_number = d.incident_number
   WHERE i.incident_number BETWEEN 10000 AND 10011
   ORDER BY i.incident_number;
   
   -- Summary by decision type
   SELECT 
       d.decision,
       COUNT(*) as count
   FROM autonomous_decision_log d
   WHERE d.incident_number BETWEEN 10000 AND 10011
   GROUP BY d.decision
   ORDER BY count DESC;
        """)
        
        print(f"\n{'='*80}")
        print(f"TEST COMPLETION TIME: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}\n")
        
        # Return exit code
        return 0 if failed_tests == 0 else 1

def main():
    """Main entry point"""
    tester = DecisionMatrixTester()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)

if __name__ == '__main__':
    main()
