"""
Standalone test script for the LangGraph remediation workflow

Run this to test the workflow without needing Kafka/Postgres running.
"""
import sys
import os
from typing import Dict, Any
from loguru import logger

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from workflow import RemediationAgent


def create_test_incident() -> Dict[str, Any]:
    """Create a simulated incident for testing"""
    return {
        "incident_id": "test-001",
        "incident_number": 999,
        "incident_type": "DEVICE_FAILURE",
        "severity": "MEDIUM",
        "primary_device": "core-router-01",
        "anomaly_count": 5,
        "correlation_confidence": 85.0
    }


def create_test_diagnosis() -> Dict[str, Any]:
    """Create a simulated diagnosis for testing"""
    return {
        "root_cause": "Interface GigabitEthernet0/1 experiencing high error rate (1250 errors) likely due to physical layer issues or NIC failure",
        "confidence": 0.85,
        "severity": "MEDIUM",
        "primary_device": "core-router-01",
        "remediation_plan": {
            "actions": [
                {
                    "type": "clear_interface_errors",
                    "device": "core-router-01",
                    "interface": "GigabitEthernet0/1",
                    "priority": 1
                },
                {
                    "type": "reload_interface",
                    "device": "core-router-01",
                    "interface": "GigabitEthernet0/1",
                    "priority": 2
                }
            ]
        }
    }


def test_simple_workflow():
    """Test 1: Simple interface issue (should succeed)"""
    logger.info("=" * 80)
    logger.info("TEST 1: Simple Interface Issue (Expected: SUCCESS)")
    logger.info("=" * 80)
    
    # Check API key
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        logger.error("GROQ_API_KEY not set. Set it in environment or .env file")
        return False
    
    # Create agent
    agent = RemediationAgent(
        groq_api_key=api_key,
        simulation_mode=True
    )
    
    # Create test data
    incident = create_test_incident()
    diagnosis = create_test_diagnosis()
    
    # Run remediation
    result = agent.remediate(incident, diagnosis)
    
    # Check result
    logger.info("=" * 80)
    logger.info("TEST RESULT:")
    logger.info(f"  Success: {result['success']}")
    logger.info(f"  Phase: {result['final_phase']}")
    logger.info(f"  Actions: {result['actions_taken']}")
    logger.info(f"  Time: {result['resolution_time']:.2f}s")
    logger.info(f"  Lessons: {result['lessons_learned']}")
    logger.info("=" * 80)
    
    return result['success']


def test_low_confidence_workflow():
    """Test 2: Low confidence diagnosis (should escalate)"""
    logger.info("\n\n")
    logger.info("=" * 80)
    logger.info("TEST 2: Low Confidence Diagnosis (Expected: ESCALATION)")
    logger.info("=" * 80)
    
    api_key = os.getenv('GROQ_API_KEY')
    agent = RemediationAgent(groq_api_key=api_key, simulation_mode=True)
    
    incident = create_test_incident()
    diagnosis = create_test_diagnosis()
    
    # Lower confidence to trigger escalation
    diagnosis['confidence'] = 0.3
    
    result = agent.remediate(incident, diagnosis)
    
    logger.info("=" * 80)
    logger.info("TEST RESULT:")
    logger.info(f"  Success: {result['success']}")
    logger.info(f"  Phase: {result['final_phase']}")
    logger.info(f"  Expected escalation: {'✅ YES' if result['final_phase'] == 'escalated' else '❌ NO'}")
    logger.info("=" * 80)
    
    return result['final_phase'] == 'escalated'


def test_bgp_workflow():
    """Test 3: BGP incident (different workflow)"""
    logger.info("\n\n")
    logger.info("=" * 80)
    logger.info("TEST 3: BGP Incident (Expected: SUCCESS with different actions)")
    logger.info("=" * 80)
    
    api_key = os.getenv('GROQ_API_KEY')
    agent = RemediationAgent(groq_api_key=api_key, simulation_mode=True)
    
    incident = {
        "incident_id": "test-003",
        "incident_number": 998,
        "incident_type": "BGP_ROUTE_FLAPPING",
        "severity": "HIGH",
        "primary_device": "core-router-01",
        "anomaly_count": 3,
        "correlation_confidence": 75.0
    }
    
    diagnosis = {
        "root_cause": "BGP session with peer 10.1.1.2 flapping due to timer mismatch",
        "confidence": 0.75,
        "severity": "HIGH",
        "primary_device": "core-router-01",
        "remediation_plan": {
            "actions": [
                {
                    "type": "restart_service",
                    "device": "core-router-01",
                    "service": "bgp",
                    "priority": 1
                }
            ]
        }
    }
    
    result = agent.remediate(incident, diagnosis)
    
    logger.info("=" * 80)
    logger.info("TEST RESULT:")
    logger.info(f"  Success: {result['success']}")
    logger.info(f"  Phase: {result['final_phase']}")
    logger.info(f"  Actions: {result['actions_taken']}")
    logger.info(f"  Time: {result['resolution_time']:.2f}s")
    logger.info("=" * 80)
    
    return result['success'] or result['final_phase'] == 'escalated'  # BGP is HIGH severity, might escalate


def main():
    """Run all tests"""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    logger.info("🧪 Testing LangGraph Remediation Workflow")
    logger.info("=" * 80)
    
    # Check API key first
    if not os.getenv('GROQ_API_KEY'):
        logger.error("❌ GROQ_API_KEY not set!")
        logger.info("Set it in your environment:")
        logger.info("  export GROQ_API_KEY='your-key-here'")
        logger.info("Or create a .env file with:")
        logger.info("  GROQ_API_KEY=your-key-here")
        sys.exit(1)
    
    # Run tests
    tests = [
        ("Simple Interface Issue", test_simple_workflow),
        ("Low Confidence Escalation", test_low_confidence_workflow),
        ("BGP Incident", test_bgp_workflow)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            logger.error(f"Test '{name}' failed with exception: {e}")
            results.append((name, False))
    
    # Summary
    logger.info("\n\n")
    logger.info("=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"  {status}: {name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    logger.info("=" * 80)
    logger.info(f"Result: {passed_count}/{total_count} tests passed")
    logger.info("=" * 80)
    
    if passed_count == total_count:
        logger.success("🎉 All tests passed!")
        sys.exit(0)
    else:
        logger.error("❌ Some tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
