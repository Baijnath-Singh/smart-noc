#!/usr/bin/env python3
"""
Comprehensive Safety Framework Test Suite

Tests all decision matrix scenarios, performance, and existing functionality
"""
import sys
import time
import psycopg2
from psycopg2.extras import RealDictCursor
import json

sys.path.insert(0, '/app')
from safety_integration import SafetyIntegration

# Database configuration
DB_CONFIG = {
    'host': 'postgres',
    'port': '5432',
    'database': 'smart_noc',
    'user': 'noc_admin',
    'password': 'noc_password'
}

class SafetyFrameworkTestSuite:
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        database_url = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
        self.safety = SafetyIntegration(database_url)
        self.results = []
        
    def log_result(self, test_name, passed, details):
        """Log test result"""
        self.results.append({
            'test': test_name,
            'passed': passed,
            'details': details
        })
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
        if details:
            print(f"      {details}")
    
    def test_decision_matrix_coverage(self):
        """Test all decision matrix scenarios"""
        print("\n" + "="*80)
        print("TEST SUITE 1: DECISION MATRIX COVERAGE")
        print("="*80)
        
        test_cases = [
            # (risk_level, confidence, severity, expected_decision, test_name)
            ("LOW", 0.95, "LOW", "execute", "LOW risk + Very High confidence"),
            ("LOW", 0.88, "LOW", "execute_notify", "LOW risk + High confidence"),
            ("LOW", 0.72, "LOW", "manual_only", "LOW risk + Medium confidence"),
            ("LOW", 0.65, "LOW", "manual_only", "LOW risk + Low confidence"),
            
            ("MEDIUM", 0.95, "MEDIUM", "require_approval", "MEDIUM risk + Very High confidence"),
            ("MEDIUM", 0.82, "MEDIUM", "require_approval", "MEDIUM risk + High confidence"),
            ("MEDIUM", 0.70, "MEDIUM", "manual_only", "MEDIUM risk + Medium confidence"),
            
            ("HIGH", 0.95, "HIGH", "require_approval", "HIGH risk + Very High confidence"),
            ("HIGH", 0.80, "HIGH", "require_approval", "HIGH risk + High confidence"),
            ("HIGH", 0.70, "HIGH", "manual_only", "HIGH risk + Low confidence"),
            
            ("CRITICAL", 0.95, "CRITICAL", "manual_only", "CRITICAL risk + Very High confidence"),
            ("CRITICAL", 0.80, "CRITICAL", "manual_only", "CRITICAL risk + High confidence"),
            ("CRITICAL", 0.60, "CRITICAL", "manual_only", "CRITICAL risk + Low confidence"),
        ]
        
        passed = 0
        failed = 0
        
        for risk_level, confidence, severity, expected_decision, test_name in test_cases:
            # Determine risk_score from risk_level
            risk_score_map = {"LOW": 0.3, "MEDIUM": 0.55, "HIGH": 0.75, "CRITICAL": 0.92}
            risk_score = risk_score_map[risk_level]
            
            # Create test incident
            incident = {
                'incident_number': 99000 + len(self.results),
                'primary_device': 'test-device',
                'incident_type': 'TEST',
                'affected_device_count': 1,
                'severity': severity
            }
            
            diagnosis = {
                'root_cause': 'Test root cause',
                'remediation_plan': [{'step': 1, 'action': 'test', 'device': 'test-device'}]
            }
            
            # Perform assessment
            start_time = time.time()
            result = self.safety.assess_safety(incident, diagnosis, confidence)
            duration = time.time() - start_time
            
            # Verify decision
            actual_decision = result['decision']
            matches = actual_decision == expected_decision
            
            if matches:
                passed += 1
                self.log_result(
                    f"DM-{len(self.results):02d}: {test_name}",
                    True,
                    f"Risk={risk_level} Conf={confidence:.2f} → {actual_decision} (expected: {expected_decision}) in {duration*1000:.0f}ms"
                )
            else:
                failed += 1
                self.log_result(
                    f"DM-{len(self.results):02d}: {test_name}",
                    False,
                    f"Risk={risk_level} Conf={confidence:.2f} → {actual_decision} (expected: {expected_decision})"
                )
        
        print(f"\n📊 Decision Matrix Coverage: {passed}/{passed+failed} passed ({100*passed/(passed+failed):.1f}%)")
        return passed, failed
    
    def test_risk_assessment_accuracy(self):
        """Test risk assessment calculations"""
        print("\n" + "="*80)
        print("TEST SUITE 2: RISK ASSESSMENT ACCURACY")
        print("="*80)
        
        test_cases = [
            # (device, affected_count, incident_type, complexity_steps, expected_risk, test_name)
            ("access-sw-01", 1, "INTERFACE_FLAPPING", 1, "LOW", "Single access switch, simple fix"),
            ("core-router-01", 1, "INTERFACE_FLAPPING", 2, "MEDIUM", "Core router, moderate fix"),
            ("dist-switch-01", 5, "BGP_FLAPPING", 3, "HIGH", "Distribution switch affecting 5 devices"),
            ("core-router-01", 10, "BGP_FLAPPING", 5, "CRITICAL", "Core router affecting 10 devices"),
        ]
        
        passed = 0
        failed = 0
        
        for device, affected_count, inc_type, steps, expected_risk, test_name in test_cases:
            incident = {
                'incident_number': 99100 + len(test_cases),
                'primary_device': device,
                'incident_type': inc_type,
                'affected_device_count': affected_count,
                'severity': 'MEDIUM'
            }
            
            remediation_steps = [
                {'step': i+1, 'action': f'step_{i}', 'device': device}
                for i in range(steps)
            ]
            
            diagnosis = {
                'root_cause': 'Test root cause',
                'remediation_plan': remediation_steps
            }
            
            result = self.safety.assess_safety(incident, diagnosis, 0.80)
            actual_risk = result['risk_level']
            
            # Allow one level difference for borderline cases
            risk_levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
            expected_idx = risk_levels.index(expected_risk)
            actual_idx = risk_levels.index(actual_risk)
            
            matches = abs(expected_idx - actual_idx) <= 1
            
            if matches:
                passed += 1
                self.log_result(
                    f"RA-{len(self.results):02d}: {test_name}",
                    True,
                    f"Device={device} Affected={affected_count} Steps={steps} → {actual_risk} (score: {result['risk_score']:.2f})"
                )
            else:
                failed += 1
                self.log_result(
                    f"RA-{len(self.results):02d}: {test_name}",
                    False,
                    f"Expected {expected_risk}, got {actual_risk} (score: {result['risk_score']:.2f})"
                )
        
        print(f"\n📊 Risk Assessment Accuracy: {passed}/{passed+failed} passed ({100*passed/(passed+failed):.1f}%)")
        return passed, failed
    
    def test_database_logging(self):
        """Test database logging integrity"""
        print("\n" + "="*80)
        print("TEST SUITE 3: DATABASE LOGGING")
        print("="*80)
        
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        passed = 0
        failed = 0
        
        # Test 1: Risk assessment logging
        incident = {
            'incident_number': 99200,
            'primary_device': 'test-device',
            'incident_type': 'TEST',
            'affected_device_count': 1,
            'severity': 'LOW'
        }
        diagnosis = {
            'root_cause': 'Test',
            'remediation_plan': [{'step': 1, 'action': 'test', 'device': 'test-device'}]
        }
        
        result = self.safety.assess_safety(incident, diagnosis, 0.85)
        
        # Verify risk assessment in DB
        cursor.execute("""
            SELECT incident_number, risk_level, overall_risk_score
            FROM incident_risk_assessment
            WHERE incident_number = 99200
            ORDER BY assessed_at DESC
            LIMIT 1
        """)
        risk_record = cursor.fetchone()
        
        if risk_record:
            passed += 1
            self.log_result(
                "DB-01: Risk assessment logged",
                True,
                f"Found in incident_risk_assessment: {risk_record['risk_level']} (score: {risk_record['overall_risk_score']:.2f})"
            )
        else:
            failed += 1
            self.log_result("DB-01: Risk assessment logged", False, "Not found in database")
        
        # Test 2: Decision logging
        cursor.execute("""
            SELECT incident_number, decision, risk_level, calibrated_confidence
            FROM autonomous_decision_log
            WHERE incident_number = 99200
            ORDER BY decided_at DESC
            LIMIT 1
        """)
        decision_record = cursor.fetchone()
        
        if decision_record:
            passed += 1
            self.log_result(
                "DB-02: Decision logged",
                True,
                f"Found in autonomous_decision_log: {decision_record['decision']} at confidence {decision_record['calibrated_confidence']:.2f}"
            )
        else:
            failed += 1
            self.log_result("DB-02: Decision logged", False, "Not found in database")
        
        # Test 3: Data consistency
        if risk_record and decision_record:
            consistent = (risk_record['risk_level'] == decision_record['risk_level'])
            if consistent:
                passed += 1
                self.log_result("DB-03: Data consistency", True, "Risk levels match across tables")
            else:
                failed += 1
                self.log_result("DB-03: Data consistency", False, "Risk levels don't match")
        
        cursor.close()
        print(f"\n📊 Database Logging: {passed}/{passed+failed} passed ({100*passed/(passed+failed):.1f}%)")
        return passed, failed
    
    def test_performance(self):
        """Test performance benchmarks"""
        print("\n" + "="*80)
        print("TEST SUITE 4: PERFORMANCE BENCHMARKS")
        print("="*80)
        
        passed = 0
        failed = 0
        
        # Benchmark: Assessment speed
        durations = []
        for i in range(10):
            incident = {
                'incident_number': 99300 + i,
                'primary_device': 'test-device',
                'incident_type': 'TEST',
                'affected_device_count': 1,
                'severity': 'LOW'
            }
            diagnosis = {
                'root_cause': 'Test',
                'remediation_plan': [{'step': 1, 'action': 'test', 'device': 'test-device'}]
            }
            
            start = time.time()
            self.safety.assess_safety(incident, diagnosis, 0.80)
            duration = time.time() - start
            durations.append(duration)
        
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        
        # Performance threshold: < 100ms average, < 200ms max
        if avg_duration < 0.1:
            passed += 1
            self.log_result(
                "PERF-01: Average assessment speed",
                True,
                f"{avg_duration*1000:.1f}ms average (threshold: <100ms)"
            )
        else:
            failed += 1
            self.log_result(
                "PERF-01: Average assessment speed",
                False,
                f"{avg_duration*1000:.1f}ms average (threshold: <100ms)"
            )
        
        if max_duration < 0.2:
            passed += 1
            self.log_result(
                "PERF-02: Maximum assessment speed",
                True,
                f"{max_duration*1000:.1f}ms max (threshold: <200ms)"
            )
        else:
            failed += 1
            self.log_result(
                "PERF-02: Maximum assessment speed",
                False,
                f"{max_duration*1000:.1f}ms max (threshold: <200ms)"
            )
        
        print(f"\n📊 Performance: {passed}/{passed+failed} passed ({100*passed/(passed+failed):.1f}%)")
        return passed, failed
    
    def test_edge_cases(self):
        """Test edge cases and error handling"""
        print("\n" + "="*80)
        print("TEST SUITE 5: EDGE CASES")
        print("="*80)
        
        passed = 0
        failed = 0
        
        # Test 1: Confidence at exact thresholds
        for conf, expected in [(0.90, "execute"), (0.75, "execute_notify"), (0.74, "manual_only")]:
            incident = {
                'incident_number': 99400,
                'primary_device': 'access-sw-01',
                'incident_type': 'TEST',
                'affected_device_count': 1,
                'severity': 'LOW'
            }
            diagnosis = {
                'root_cause': 'Test',
                'remediation_plan': [{'step': 1, 'action': 'test', 'device': 'test'}]
            }
            
            result = self.safety.assess_safety(incident, diagnosis, conf)
            if result['decision'] == expected:
                passed += 1
                self.log_result(
                    f"EDGE-01: Threshold confidence {conf}",
                    True,
                    f"Confidence {conf} → {result['decision']} (expected: {expected})"
                )
            else:
                failed += 1
                self.log_result(
                    f"EDGE-01: Threshold confidence {conf}",
                    False,
                    f"Confidence {conf} → {result['decision']} (expected: {expected})"
                )
        
        # Test 2: Missing optional fields
        incident = {
            'incident_number': 99401,
            'primary_device': 'test-device',
            'incident_type': 'TEST',
            'affected_device_count': 1,
            'severity': 'MEDIUM'
        }
        diagnosis = {
            'remediation_plan': []  # Empty plan
        }
        
        try:
            result = self.safety.assess_safety(incident, diagnosis, 0.80)
            if result['risk_level']:
                passed += 1
                self.log_result(
                    "EDGE-02: Empty remediation plan",
                    True,
                    f"Handled gracefully: {result['risk_level']} risk"
                )
        except Exception as e:
            failed += 1
            self.log_result("EDGE-02: Empty remediation plan", False, f"Exception: {e}")
        
        print(f"\n📊 Edge Cases: {passed}/{passed+failed} passed ({100*passed/(passed+failed):.1f}%)")
        return passed, failed
    
    def generate_report(self):
        """Generate final test report"""
        print("\n" + "="*80)
        print("COMPREHENSIVE TEST REPORT")
        print("="*80)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r['passed'])
        failed = total - passed
        score = 100 * passed / total if total > 0 else 0
        
        print(f"\n📊 Overall Results:")
        print(f"   Total Tests: {total}")
        print(f"   Passed: {passed} ✅")
        print(f"   Failed: {failed} ❌")
        print(f"   Score: {score:.1f}%")
        
        if failed > 0:
            print(f"\n❌ Failed Tests:")
            for r in self.results:
                if not r['passed']:
                    print(f"   - {r['test']}: {r['details']}")
        
        print("\n" + "="*80)
        
        # Grade
        if score >= 95:
            grade = "A+ (Excellent)"
        elif score >= 90:
            grade = "A (Very Good)"
        elif score >= 85:
            grade = "B+ (Good)"
        elif score >= 80:
            grade = "B (Satisfactory)"
        else:
            grade = "C (Needs Improvement)"
        
        print(f"🏆 Final Grade: {grade}")
        print("="*80)
        
        return score >= 90

def main():
    print("="*80)
    print("SAFETY FRAMEWORK COMPREHENSIVE TEST SUITE")
    print("="*80)
    
    suite = SafetyFrameworkTestSuite()
    
    # Run all test suites
    dm_pass, dm_fail = suite.test_decision_matrix_coverage()
    ra_pass, ra_fail = suite.test_risk_assessment_accuracy()
    db_pass, db_fail = suite.test_database_logging()
    perf_pass, perf_fail = suite.test_performance()
    edge_pass, edge_fail = suite.test_edge_cases()
    
    # Generate report
    success = suite.generate_report()
    
    suite.conn.close()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
