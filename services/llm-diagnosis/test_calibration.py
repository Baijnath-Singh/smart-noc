"""
Test script for confidence calibration system

This script:
1. Adds sample feedback data to test calibration
2. Tests calibration with various confidence levels
3. Displays calibration metrics

Date: 2026-06-09
"""

import sys
import os
from uuid import uuid4
from datetime import datetime, timedelta
import random

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from confidence_calibrator import ConfidenceCalibrator
from sqlalchemy import create_engine

# Database connection
DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://noc_admin:noc_password@postgres:5432/smart_noc"
)

def add_sample_feedback():
    """Add sample feedback data for testing calibration"""
    calibrator = ConfidenceCalibrator()
    
    print("=" * 80)
    print("Adding sample feedback data for calibration testing...")
    print("=" * 80)
    
    # Simulate various scenarios:
    # Scenario 1: LLM overconfident at 0.9 (actually only 70% correct)
    print("\n📊 Scenario 1: LLM overconfident at 0.9 confidence")
    for i in range(10):
        was_correct = random.random() < 0.70  # 70% accuracy
        incident_number = 1000 + i
        calibrator.add_feedback(
            incident_number=incident_number,
            diagnosis_id=str(uuid4()),
            llm_confidence=0.9,
            predicted_root_cause="BGP peering failure",
            was_correct=was_correct,
            incident_type="BGP_DOWN",
            engineer_id="test_engineer"
        )
        print(f"  ✓ Incident {incident_number}: confidence=0.90, correct={was_correct}")
    
    # Scenario 2: LLM underconfident at 0.6 (actually 85% correct)
    print("\n📊 Scenario 2: LLM underconfident at 0.6 confidence")
    for i in range(10):
        was_correct = random.random() < 0.85  # 85% accuracy
        incident_number = 2000 + i
        calibrator.add_feedback(
            incident_number=incident_number,
            diagnosis_id=str(uuid4()),
            llm_confidence=0.6,
            predicted_root_cause="Interface flapping",
            was_correct=was_correct,
            incident_type="INTERFACE_FLAP",
            engineer_id="test_engineer"
        )
        print(f"  ✓ Incident {incident_number}: confidence=0.60, correct={was_correct}")
    
    # Scenario 3: LLM well-calibrated at 0.8 (actually 80% correct)
    print("\n📊 Scenario 3: LLM well-calibrated at 0.8 confidence")
    for i in range(10):
        was_correct = random.random() < 0.80  # 80% accuracy
        incident_number = 3000 + i
        calibrator.add_feedback(
            incident_number=incident_number,
            diagnosis_id=str(uuid4()),
            llm_confidence=0.8,
            predicted_root_cause="VLAN misconfiguration",
            was_correct=was_correct,
            incident_type="VLAN_TRUNK_FAIL",
            engineer_id="test_engineer"
        )
        print(f"  ✓ Incident {incident_number}: confidence=0.80, correct={was_correct}")
    
    # Scenario 4: Low confidence cases (0.5) - actually 50% correct
    print("\n📊 Scenario 4: Low confidence at 0.5")
    for i in range(10):
        was_correct = random.random() < 0.50  # 50% accuracy
        incident_number = 4000 + i
        calibrator.add_feedback(
            incident_number=incident_number,
            diagnosis_id=str(uuid4()),
            llm_confidence=0.5,
            predicted_root_cause="Unknown root cause",
            was_correct=was_correct,
            incident_type="UNKNOWN",
            engineer_id="test_engineer"
        )
        print(f"  ✓ Incident {incident_number}: confidence=0.50, correct={was_correct}")
    
    # Scenario 5: High confidence cases (0.95) - actually 95% correct (well-calibrated)
    print("\n📊 Scenario 5: High confidence at 0.95 (well-calibrated)")
    for i in range(10):
        was_correct = random.random() < 0.95  # 95% accuracy
        incident_number = 5000 + i
        calibrator.add_feedback(
            incident_number=incident_number,
            diagnosis_id=str(uuid4()),
            llm_confidence=0.95,
            predicted_root_cause="Link down - cable unplugged",
            was_correct=was_correct,
            incident_type="LINK_DOWN",
            engineer_id="test_engineer"
        )
        print(f"  ✓ Incident {incident_number}: confidence=0.95, correct={was_correct}")
    
    print("\n✅ Sample feedback data added successfully!")
    print(f"Total records: 50")
    
    return calibrator


def test_calibration():
    """Test calibration with various confidence levels"""
    calibrator = ConfidenceCalibrator()
    
    # Refresh calibration with new data
    print("\n" + "=" * 80)
    print("Refreshing calibration maps...")
    print("=" * 80)
    calibrator.refresh_calibration()
    
    print("\n" + "=" * 80)
    print("Testing calibration with various confidence levels...")
    print("=" * 80)
    
    test_cases = [
        (0.5, "UNKNOWN"),
        (0.6, "INTERFACE_FLAP"),
        (0.8, "VLAN_TRUNK_FAIL"),
        (0.9, "BGP_DOWN"),
        (0.95, "LINK_DOWN"),
        (0.7, None),  # No incident type (global calibration)
        (0.85, None),
    ]
    
    print(f"\n{'Confidence':<12} {'Type':<20} {'Calibrated':<12} {'Method':<20} {'Change':<10}")
    print("-" * 80)
    
    for confidence, incident_type in test_cases:
        calibrated, method = calibrator.calibrate(confidence, incident_type)
        change = calibrated - confidence
        change_str = f"{change:+.3f}"
        
        type_str = incident_type or "global"
        print(f"{confidence:<12.2f} {type_str:<20} {calibrated:<12.3f} {method:<20} {change_str:<10}")
    
    # Display calibration metrics
    print("\n" + "=" * 80)
    print("Calibration Metrics")
    print("=" * 80)
    
    metrics = calibrator.get_calibration_metrics()
    if metrics.get('status') == 'active':
        print(f"\n📊 Overall Statistics:")
        print(f"  Total Feedback Records: {metrics['total_feedback']}")
        print(f"  Total Correct Diagnoses: {metrics['total_correct']}")
        print(f"  Overall Accuracy: {metrics['overall_accuracy']:.1%}")
        print(f"  Average LLM Confidence: {metrics['avg_confidence']:.3f}")
        print(f"  Mean Absolute Error: {metrics['mean_absolute_error']:.3f}")
        print(f"  Incident Types Covered: {metrics['incident_types_covered']}")
        print(f"  Calibration Maps Loaded: {metrics['calibration_maps']}")
        print(f"  Last Update: {metrics['last_update']}")
    else:
        print(f"\n⚠️  Status: {metrics.get('message', 'Unknown')}")
    
    # Display detailed calibration data by bucket
    print("\n" + "=" * 80)
    print("Detailed Calibration Data by Confidence Bucket")
    print("=" * 80)
    
    calibration_data = calibrator.get_calibration_data_by_bucket()
    
    if calibration_data:
        print(f"\n{'Bucket':<10} {'Samples':<10} {'Correct':<10} {'Accuracy':<12} {'Avg Conf':<12} {'Error':<10}")
        print("-" * 80)
        
        for data in calibration_data:
            print(
                f"{data.confidence_bucket:<10.1f} "
                f"{data.total_samples:<10} "
                f"{data.correct_samples:<10} "
                f"{data.actual_accuracy:<12.1%} "
                f"{data.avg_reported_confidence:<12.3f} "
                f"{data.calibration_error:+.3f}"
            )
    else:
        print("\nNo calibration data available yet.")
    
    print("\n✅ Calibration test complete!")


def main():
    """Main test function"""
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 78 + "║")
    print("║" + "     Confidence Calibration System - Test Script".center(78) + "║")
    print("║" + " " * 78 + "║")
    print("╚" + "=" * 78 + "╝")
    
    try:
        # Add sample feedback
        calibrator = add_sample_feedback()
        
        # Test calibration
        test_calibration()
        
        print("\n" + "=" * 80)
        print("✅ All tests completed successfully!")
        print("=" * 80)
        
        print("\n💡 Next Steps:")
        print("  1. Check Grafana dashboards for calibration metrics")
        print("  2. Monitor calibration_status view in database")
        print("  3. Restart llm-diagnosis service to use calibration")
        print("  4. Add real engineer feedback as incidents are diagnosed")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
