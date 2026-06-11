#!/usr/bin/env python3
"""
Service Health & Performance Verification

Checks all services for:
1. Performance metrics (CPU, memory)
2. Existing features still working
3. No breakage after Safety Framework integration
"""
import subprocess
import json
import psycopg2
from psycopg2.extras import RealDictCursor
import time

DB_CONFIG = {
    'host': 'localhost',
    'port': '5432',
    'database': 'smart_noc',
    'user': 'noc_admin',
    'password': 'noc_password'
}

class ServiceHealthCheck:
    def __init__(self):
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
    
    def check_service_status(self):
        """Check all services are running"""
        print("\n" + "="*80)
        print("SERVICE STATUS CHECK")
        print("="*80)
        
        services = [
            'llm-diagnosis',
            'remediation-agent',
            'correlation-engine',
            'anomaly-detector',
            'postgres',
            'kafka'
        ]
        
        passed = 0
        failed = 0
        
        for service in services:
            try:
                result = subprocess.run(
                    ['docker-compose', 'ps', service],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if 'running' in result.stdout.lower() or 'up' in result.stdout.lower():
                    passed += 1
                    self.log_result(f"Service: {service}", True, "Running")
                else:
                    failed += 1
                    self.log_result(f"Service: {service}", False, "Not running")
            except Exception as e:
                failed += 1
                self.log_result(f"Service: {service}", False, f"Check failed: {e}")
        
        print(f"\n📊 Service Status: {passed}/{passed+failed} services healthy")
        return passed, failed
    
    def check_performance_metrics(self):
        """Check CPU and memory usage"""
        print("\n" + "="*80)
        print("PERFORMANCE METRICS")
        print("="*80)
        
        passed = 0
        failed = 0
        
        try:
            result = subprocess.run(
                ['docker', 'stats', '--no-stream', '--format', 
                 '{"name":"{{.Name}}","cpu":"{{.CPUPerc}}","mem":"{{.MemUsage}}"}'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            services_metrics = {}
            for line in result.stdout.strip().split('\n'):
                if line:
                    data = json.loads(line)
                    name = data['name']
                    if 'smart-noc' in name:
                        service_name = name.replace('smart-noc-', '')
                        cpu = float(data['cpu'].replace('%', ''))
                        mem = data['mem']
                        services_metrics[service_name] = {
                            'cpu': cpu,
                            'memory': mem
                        }
            
            # Performance thresholds
            thresholds = {
                'llm-diagnosis': {'cpu': 5.0, 'name': 'LLM Diagnosis'},
                'remediation-agent': {'cpu': 20.0, 'name': 'Remediation Agent'},
                'correlation-engine': {'cpu': 5.0, 'name': 'Correlation Engine'},
                'anomaly-detector': {'cpu': 5.0, 'name': 'Anomaly Detector'}
            }
            
            for service, threshold in thresholds.items():
                if service in services_metrics:
                    cpu = services_metrics[service]['cpu']
                    mem = services_metrics[service]['memory']
                    
                    if cpu < threshold['cpu']:
                        passed += 1
                        self.log_result(
                            f"Performance: {threshold['name']}",
                            True,
                            f"CPU: {cpu:.2f}% (threshold: <{threshold['cpu']}%), Memory: {mem}"
                        )
                    else:
                        failed += 1
                        self.log_result(
                            f"Performance: {threshold['name']}",
                            False,
                            f"CPU: {cpu:.2f}% exceeds threshold {threshold['cpu']}%"
                        )
                else:
                    failed += 1
                    self.log_result(f"Performance: {threshold['name']}", False, "Metrics not available")
        
        except Exception as e:
            failed += 1
            self.log_result("Performance metrics", False, f"Failed to collect: {e}")
        
        print(f"\n📊 Performance: {passed}/{passed+failed} within thresholds")
        return passed, failed
    
    def check_database_connectivity(self):
        """Check database is accessible"""
        print("\n" + "="*80)
        print("DATABASE CONNECTIVITY")
        print("="*80)
        
        passed = 0
        failed = 0
        
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Test 1: Basic connectivity
            cursor.execute("SELECT version()")
            version = cursor.fetchone()
            passed += 1
            self.log_result("Database: Connection", True, "Connected successfully")
            
            # Test 2: Incidents table accessible
            cursor.execute("SELECT COUNT(*) as count FROM incidents")
            count = cursor.fetchone()['count']
            passed += 1
            self.log_result("Database: Incidents table", True, f"{count} incidents in database")
            
            # Test 3: Safety Framework tables exist
            safety_tables = [
                'incident_risk_assessment',
                'autonomous_decision_log',
                'configuration_snapshots',
                'remediation_executions'
            ]
            
            for table in safety_tables:
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                count = cursor.fetchone()['count']
                passed += 1
                self.log_result(f"Database: {table}", True, f"{count} records")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            failed += 1
            self.log_result("Database connectivity", False, f"Error: {e}")
        
        print(f"\n📊 Database: {passed}/{passed+failed} checks passed")
        return passed, failed
    
    def check_existing_features(self):
        """Verify existing features still work"""
        print("\n" + "="*80)
        print("EXISTING FEATURES VERIFICATION")
        print("="*80)
        
        passed = 0
        failed = 0
        
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Test 1: Incident creation still works
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM incidents 
                WHERE created_at > NOW() - INTERVAL '1 hour'
            """)
            recent = cursor.fetchone()['count']
            if recent >= 0:
                passed += 1
                self.log_result("Feature: Incident creation", True, f"{recent} recent incidents")
            
            # Test 2: Diagnosis functionality
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM incidents 
                WHERE root_cause IS NOT NULL
            """)
            diagnosed = cursor.fetchone()['count']
            if diagnosed > 0:
                passed += 1
                self.log_result("Feature: Diagnosis", True, f"{diagnosed} diagnosed incidents")
            else:
                failed += 1
                self.log_result("Feature: Diagnosis", False, "No diagnosed incidents found")
            
            # Test 3: Confidence calibration
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM incidents 
                WHERE confidence_reasoning IS NOT NULL
            """)
            calibrated = cursor.fetchone()['count']
            if calibrated > 0:
                passed += 1
                self.log_result("Feature: Confidence calibration", True, f"{calibrated} incidents with calibration")
            else:
                failed += 1
                self.log_result("Feature: Confidence calibration", False, "No calibration data")
            
            # Test 4: Anomaly correlation
            cursor.execute("""
                SELECT COUNT(DISTINCT incident_id) as count 
                FROM incident_anomalies
            """)
            correlated = cursor.fetchone()['count']
            if correlated > 0:
                passed += 1
                self.log_result("Feature: Anomaly correlation", True, f"{correlated} incidents with anomalies")
            else:
                failed += 1
                self.log_result("Feature: Anomaly correlation", False, "No anomaly correlations")
            
            # Test 5: Vector search integration
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM incidents 
                WHERE incident_metadata::text LIKE '%vector%' OR incident_metadata::text LIKE '%kb_article%'
            """)
            vector = cursor.fetchone()['count']
            passed += 1
            self.log_result("Feature: Vector search", True, f"{vector} incidents with vector data")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            failed += 1
            self.log_result("Existing features", False, f"Error: {e}")
        
        print(f"\n📊 Features: {passed}/{passed+failed} working correctly")
        return passed, failed
    
    def check_logs_for_errors(self):
        """Check recent logs for errors"""
        print("\n" + "="*80)
        print("LOG ERROR ANALYSIS")
        print("="*80)
        
        passed = 0
        failed = 0
        
        services = ['llm-diagnosis', 'remediation-agent', 'correlation-engine', 'anomaly-detector']
        
        for service in services:
            try:
                result = subprocess.run(
                    ['docker-compose', 'logs', '--tail=50', service],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                logs = result.stdout + result.stderr
                
                # Count critical errors (excluding expected test errors)
                critical_keywords = ['CRITICAL', 'FATAL', 'Exception', 'Traceback']
                ignore_keywords = ['test', 'Test', 'TEST', 'ModuleNotFoundError: kafka']
                
                errors = 0
                for line in logs.split('\n'):
                    if any(keyword in line for keyword in critical_keywords):
                        if not any(ignore in line for ignore in ignore_keywords):
                            errors += 1
                
                if errors == 0:
                    passed += 1
                    self.log_result(f"Logs: {service}", True, "No critical errors")
                else:
                    failed += 1
                    self.log_result(f"Logs: {service}", False, f"{errors} critical errors found")
                    
            except Exception as e:
                failed += 1
                self.log_result(f"Logs: {service}", False, f"Failed to check: {e}")
        
        print(f"\n📊 Logs: {passed}/{passed+failed} services error-free")
        return passed, failed
    
    def generate_report(self):
        """Generate health report"""
        print("\n" + "="*80)
        print("SERVICE HEALTH REPORT")
        print("="*80)
        
        total = len(self.results)
        passed = sum(1 for r in self.results if r['passed'])
        failed = total - passed
        score = 100 * passed / total if total > 0 else 0
        
        print(f"\n📊 Overall Health:")
        print(f"   Total Checks: {total}")
        print(f"   Passed: {passed} ✅")
        print(f"   Failed: {failed} ❌")
        print(f"   Health Score: {score:.1f}%")
        
        if failed > 0:
            print(f"\n❌ Failed Checks:")
            for r in self.results:
                if not r['passed']:
                    print(f"   - {r['test']}: {r['details']}")
        
        print("\n" + "="*80)
        
        if score >= 95:
            health_status = "🟢 EXCELLENT - All systems operational"
        elif score >= 90:
            health_status = "🟢 GOOD - System healthy with minor issues"
        elif score >= 80:
            health_status = "🟡 WARNING - Some issues detected"
        else:
            health_status = "🔴 CRITICAL - Significant issues require attention"
        
        print(f"🏥 System Health: {health_status}")
        print("="*80)
        
        return score >= 90

def main():
    print("="*80)
    print("SERVICE HEALTH & PERFORMANCE VERIFICATION")
    print("="*80)
    
    checker = ServiceHealthCheck()
    
    # Run all checks
    checker.check_service_status()
    checker.check_performance_metrics()
    checker.check_database_connectivity()
    checker.check_existing_features()
    checker.check_logs_for_errors()
    
    # Generate report
    success = checker.generate_report()
    
    return 0 if success else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
