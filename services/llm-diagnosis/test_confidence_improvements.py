#!/usr/bin/env python3
"""
Test Confidence Improvements: Old vs New Prompts
Compares confidence scores between standard and improved prompts with historical feedback
"""

import sys
import os
import json
from datetime import datetime

# Add services directory to path
sys.path.insert(0, '/home/user/ng-iam/smart-noc/services/llm-diagnosis')

import config
from llm_client import LLMClient
from confidence_calibrator import ConfidenceCalibrator
from prompts.system_prompts import SYSTEM_PROMPT
from prompts.improved_system_prompt import get_improved_prompt_with_feedback
from sqlalchemy import create_engine

# Initialize components
engine = create_engine(config.DATABASE_URL)
calibrator = ConfidenceCalibrator(engine=engine)
llm_client = LLMClient()

def create_test_incident():
    """Create a realistic test incident"""
    return {
        'incident_number': 999,
        'incident_type': 'CONNECTIVITY_ISSUE',
        'severity': 'HIGH',
        'affected_device_count': 2,
        'anomaly_count': 3,
        'impact_score': 7.5,
        'start_time': '2026-06-10 10:30:00',
        'end_time': '2026-06-10 10:45:00',
        'primary_device': 'core-router-01',
        'affected_devices': ['core-router-01', 'edge-switch-05']
    }

def create_test_context():
    """Create test context with anomalies"""
    return """
**Anomaly Summary:**
- 10:30:15 - core-router-01: BGP neighbor 10.1.1.1 down (adjacency lost)
- 10:30:18 - core-router-01: High packet fragmentation (1,247 fragments)
- 10:32:00 - core-router-01: Interface GigE0/0 flapping

**Device History:**
- 10:15:00 - Configuration change: MTU adjusted from 1500 to 9000 on GigE0/0
- 10:20:00 - No errors reported
- 10:30:00 - BGP session instability begins

**Network Topology:**
- core-router-01 connects to remote site via GigE0/0
- BGP peer (10.1.1.1) has MTU: 1500 (standard)
- No recent MTU changes on remote peer
"""

def test_old_prompt(incident: dict, context: str) -> dict:
    """Test with OLD prompt (no historical feedback)"""
    print("\n" + "="*80)
    print("TEST 1: OLD PROMPT (No Historical Feedback)")
    print("="*80)
    
    user_message = f"""Analyze this {incident['incident_type']} incident:

**Incident Details:**
- Incident #: {incident['incident_number']}
- Device: {incident['primary_device']}
- Severity: {incident['severity']}
- Device Count: {incident['affected_device_count']}
- Anomaly Count: {incident['anomaly_count']}
- Impact Score: {incident['impact_score']}
- Timespan: {incident['start_time']} to {incident['end_time']}

{context}

Focus on identifying the root cause with clear evidence."""

    try:
        diagnosis, metadata = llm_client.generate_diagnosis(SYSTEM_PROMPT, user_message)
        
        print(f"\n📋 Root Cause: {diagnosis['root_cause'][:150]}...")
        print(f"\n🎯 Confidence: {diagnosis['confidence']:.2f}")
        
        if 'confidence_reasoning' in diagnosis:
            print(f"\n💭 Confidence Reasoning: {diagnosis['confidence_reasoning'][:200]}...")
        else:
            print("\n⚠️  No confidence reasoning provided (old prompt)")
        
        print(f"\n📊 Tokens Used: {metadata.get('total_tokens', 0)}")
        print(f"⏱️  Duration: {metadata.get('duration_ms', 0)}ms")
        
        return diagnosis
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_new_prompt(incident: dict, context: str, calibrator: ConfidenceCalibrator) -> dict:
    """Test with NEW prompt (with historical feedback)"""
    print("\n" + "="*80)
    print("TEST 2: NEW PROMPT (With Historical Feedback)")
    print("="*80)
    
    # Get improved prompt with historical feedback
    try:
        system_prompt = get_improved_prompt_with_feedback(
            calibrator=calibrator,
            incident_type=incident['incident_type']
        )
        print("✅ Loaded improved prompt with historical accuracy feedback")
        
        # Show a snippet of the feedback
        if 'Your Historical Accuracy' in system_prompt:
            feedback_start = system_prompt.find('Your Historical Accuracy')
            feedback_snippet = system_prompt[feedback_start:feedback_start+300]
            print(f"\n📊 Feedback Snippet:\n{feedback_snippet}...\n")
        
    except Exception as e:
        print(f"⚠️  Could not load improved prompt: {e}")
        system_prompt = SYSTEM_PROMPT
    
    user_message = f"""Analyze this {incident['incident_type']} incident:

**Incident Details:**
- Incident #: {incident['incident_number']}
- Device: {incident['primary_device']}
- Severity: {incident['severity']}
- Device Count: {incident['affected_device_count']}
- Anomaly Count: {incident['anomaly_count']}
- Impact Score: {incident['impact_score']}
- Timespan: {incident['start_time']} to {incident['end_time']}

{context}

Focus on identifying the root cause with clear evidence."""

    try:
        diagnosis, metadata = llm_client.generate_diagnosis(system_prompt, user_message)
        
        print(f"\n📋 Root Cause: {diagnosis['root_cause'][:150]}...")
        print(f"\n🎯 Raw Confidence: {diagnosis['confidence']:.2f}")
        
        if 'confidence_reasoning' in diagnosis:
            print(f"\n💭 Confidence Reasoning:")
            print(f"   {diagnosis['confidence_reasoning'][:400]}...")
        else:
            print("\n⚠️  No confidence reasoning provided")
        
        if 'evidence_quality' in diagnosis:
            eq = diagnosis['evidence_quality']
            print(f"\n📊 Evidence Quality:")
            print(f"   Direct Evidence: {eq.get('direct_evidence_count', 0)}")
            print(f"   Indirect Evidence: {eq.get('indirect_evidence_count', 0)}")
            print(f"   Missing Data: {eq.get('missing_critical_data', [])}")
            print(f"   Alternatives Considered: {len(eq.get('alternative_causes_considered', []))}")
        
        print(f"\n📊 Tokens Used: {metadata.get('total_tokens', 0)}")
        print(f"⏱️  Duration: {metadata.get('duration_ms', 0)}ms")
        
        return diagnosis
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

def compare_results(old_diagnosis: dict, new_diagnosis: dict):
    """Compare old vs new results"""
    print("\n" + "="*80)
    print("COMPARISON: Old vs New")
    print("="*80)
    
    if not old_diagnosis or not new_diagnosis:
        print("❌ Cannot compare - one or both diagnoses failed")
        return
    
    old_conf = old_diagnosis['confidence']
    new_conf = new_diagnosis['confidence']
    
    print(f"\n🎯 Confidence Scores:")
    print(f"   Old Prompt: {old_conf:.2f}")
    print(f"   New Prompt: {new_conf:.2f}")
    print(f"   Difference: {new_conf - old_conf:+.2f} ({((new_conf - old_conf) / old_conf * 100):+.1f}%)")
    
    # Check if confidence changed in the right direction
    if old_conf > 0.85:
        if new_conf < old_conf:
            print(f"   ✅ IMPROVEMENT: New prompt reduced overconfident score")
        else:
            print(f"   ⚠️  WARNING: High confidence maintained")
    
    # Check for confidence reasoning
    has_old_reasoning = 'confidence_reasoning' in old_diagnosis and old_diagnosis['confidence_reasoning']
    has_new_reasoning = 'confidence_reasoning' in new_diagnosis and new_diagnosis['confidence_reasoning']
    
    print(f"\n💭 Confidence Reasoning:")
    print(f"   Old Prompt: {'✅ Provided' if has_old_reasoning else '❌ Missing'}")
    print(f"   New Prompt: {'✅ Provided' if has_new_reasoning else '❌ Missing'}")
    
    # Check for evidence quality
    has_old_evidence = 'evidence_quality' in old_diagnosis
    has_new_evidence = 'evidence_quality' in new_diagnosis
    
    print(f"\n📊 Evidence Quality Tracking:")
    print(f"   Old Prompt: {'✅ Provided' if has_old_evidence else '❌ Missing'}")
    print(f"   New Prompt: {'✅ Provided' if has_new_evidence else '❌ Missing'}")
    
    if has_new_evidence:
        eq = new_diagnosis['evidence_quality']
        total_evidence = eq.get('direct_evidence_count', 0) + eq.get('indirect_evidence_count', 0)
        print(f"   Total Evidence Points: {total_evidence}")
        print(f"   Direct Evidence: {eq.get('direct_evidence_count', 0)}")
        
        # Validate confidence vs evidence
        if new_conf >= 0.85 and eq.get('direct_evidence_count', 0) < 2:
            print(f"   ⚠️  WARNING: High confidence with limited direct evidence")
        elif new_conf >= 0.85 and eq.get('direct_evidence_count', 0) >= 2:
            print(f"   ✅ GOOD: High confidence backed by strong evidence")

def test_calibration(diagnosis: dict, incident_type: str):
    """Test calibration on diagnosis"""
    print("\n" + "="*80)
    print("TEST 3: CALIBRATION (Historical Accuracy Mapping)")
    print("="*80)
    
    if not diagnosis:
        print("❌ No diagnosis to calibrate")
        return
    
    raw_confidence = diagnosis['confidence']
    
    # Apply calibration
    calibrated, method = calibrator.calibrate(raw_confidence, incident_type)
    
    print(f"\n📊 Calibration Results:")
    print(f"   Raw Confidence: {raw_confidence:.2f}")
    print(f"   Calibrated Confidence: {calibrated:.2f}")
    print(f"   Adjustment: {calibrated - raw_confidence:+.2f}")
    print(f"   Method: {method}")
    
    # Show what this means for autonomous mode
    print(f"\n🤖 Autonomous Mode Decision:")
    if calibrated >= 0.90:
        print(f"   ✅ AUTO-REMEDIATE: High calibrated confidence ({calibrated:.2f} ≥ 0.90)")
    elif calibrated >= 0.75:
        print(f"   ⚠️  NOTIFY + EXECUTE: Medium confidence ({calibrated:.2f})")
    elif calibrated >= 0.50:
        print(f"   👤 REQUIRE APPROVAL: Low confidence ({calibrated:.2f})")
    else:
        print(f"   🚫 MANUAL DIAGNOSIS: Very low confidence ({calibrated:.2f} < 0.50)")

def main():
    """Main test runner"""
    print("\n" + "="*80)
    print("CONFIDENCE IMPROVEMENT TEST SUITE")
    print("Testing: Old Prompt vs New Prompt with Historical Feedback")
    print("Date: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*80)
    
    # Show calibration data
    print("\n📊 Current Calibration Data:")
    print("   (Historical accuracy for confidence calibration)")
    
    try:
        stats = calibrator.get_calibration_stats('CONNECTIVITY_ISSUE')
        if stats and not stats.get('insufficient_data'):
            print(f"   Total Samples: {stats['total_samples']}")
            for bucket in stats['confidence_buckets']:
                print(f"     {bucket['confidence']:.0%} confidence → {bucket['accuracy']:.0%} accurate ({bucket['count']} cases)")
        else:
            print("   ⚠️  Insufficient data for type-specific calibration")
    except Exception as e:
        print(f"   ⚠️  Could not load calibration stats: {e}")
    
    # Create test data
    incident = create_test_incident()
    context = create_test_context()
    
    # Test old prompt
    old_diagnosis = test_old_prompt(incident, context)
    
    # Test new prompt
    new_diagnosis = test_new_prompt(incident, context, calibrator)
    
    # Compare results
    compare_results(old_diagnosis, new_diagnosis)
    
    # Test calibration on new diagnosis
    if new_diagnosis:
        test_calibration(new_diagnosis, incident['incident_type'])
    
    # Final summary
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)
    print("\n✅ Expected Improvements:")
    print("   1. New prompt should generate lower confidence (more conservative)")
    print("   2. New prompt should include detailed confidence reasoning")
    print("   3. New prompt should track evidence quality")
    print("   4. Calibration should further adjust confidence based on history")
    print("\n🎯 Goal: Raw confidence closer to actual accuracy")
    print("   Less aggressive calibration needed = better LLM generation!\n")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
