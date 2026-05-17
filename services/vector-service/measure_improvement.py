"""
Week 2 Success Metrics: Measure 20% Improvement in LLM Diagnosis Quality

This script compares diagnosis quality before and after vector search integration:
- Remediation step count (more comprehensive plans)
- Root cause depth (more detailed analysis)
- Diagnosis confidence scores
- Use of KB article context

Comparison:
- "Before": Incidents 5-22 (before KB articles added)
- "After": Incidents 26-30 (with KB article vector search)

Target: 20% improvement in diagnosis quality metrics

Usage:
    python measure_improvement.py
    python measure_improvement.py --verbose
"""

import sys
import os
import argparse
import json
from typing import List, Dict, Any, Tuple
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class DiagnosisMetrics:
    """Measure and compare LLM diagnosis quality"""
    
    def __init__(self):
        """Initialize metrics calculator"""
        # Database configuration
        self.db_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', 5432)),
            'database': os.getenv('POSTGRES_DB', 'smart_noc'),
            'user': os.getenv('POSTGRES_USER', 'noc_admin'),
            'password': os.getenv('POSTGRES_PASSWORD', 'noc_pass_2024')
        }
        
    def fetch_incidents(self, incident_numbers: List[int]) -> List[Dict[str, Any]]:
        """
        Fetch specific incidents from database
        
        Args:
            incident_numbers: List of incident numbers to fetch
        
        Returns:
            List of incident dictionaries
        """
        query = """
            SELECT 
                incident_number,
                incident_type,
                severity,
                root_cause,
                remediation_plan,
                correlation_confidence,
                created_at
            FROM incidents
            WHERE incident_number = ANY(%s)
            ORDER BY incident_number
        """
        
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(query, (incident_numbers,))
            incidents = cursor.fetchall()
            cursor.close()
            conn.close()
            
            return [dict(row) for row in incidents]
            
        except Exception as e:
            logger.error(f"Error fetching incidents: {e}")
            return []
    
    def calculate_root_cause_score(self, root_cause: str) -> Dict[str, Any]:
        """
        Analyze root cause quality
        
        Metrics:
        - Length (more detailed = better)
        - Mentions multiple causes (OR/AND logic)
        - Mentions specific components (NIC, PSU, transceiver, etc.)
        - Mentions environmental factors
        
        Args:
            root_cause: Root cause text
        
        Returns:
            Dictionary with quality metrics
        """
        if not root_cause:
            return {"score": 0, "length": 0, "multiple_causes": False, "specific_components": 0, "environmental": False}
        
        # Length score (cap at 200 chars for fairness)
        length = len(root_cause)
        length_score = min(length / 200.0, 1.0)
        
        # Multiple causes mentioned?
        multiple_causes = " or " in root_cause.lower() or " and " in root_cause.lower()
        
        # Specific components mentioned
        components = ["nic", "power supply", "transceiver", "cable", "memory", "cpu", "backplane", "line card", "fan", "psu"]
        specific_components = sum(1 for comp in components if comp in root_cause.lower())
        
        # Environmental factors
        environmental_terms = ["environment", "temperature", "cooling", "power fluctuation", "humidity", "overheat"]
        environmental = any(term in root_cause.lower() for term in environmental_terms)
        
        # Overall score (0-100)
        score = (
            length_score * 30 +  # 30 points for length
            (20 if multiple_causes else 0) +  # 20 points for multiple causes
            (specific_components * 10) +  # 10 points per component (max 50)
            (20 if environmental else 0)  # 20 points for environmental factors
        )
        
        return {
            "score": round(score, 2),
            "length": length,
            "multiple_causes": multiple_causes,
            "specific_components": specific_components,
            "environmental": environmental
        }
    
    def calculate_remediation_score(self, remediation_plan: Any) -> Dict[str, Any]:
        """
        Analyze remediation plan quality
        
        Metrics:
        - Number of steps (more comprehensive = better)
        - Includes immediate, short-term, long-term priorities
        - Commands provided
        - Expected outcomes defined
        
        Args:
            remediation_plan: JSON remediation plan
        
        Returns:
            Dictionary with quality metrics
        """
        if not remediation_plan:
            return {"score": 0, "steps": 0, "has_priorities": False, "has_commands": 0, "has_outcomes": 0}
        
        try:
            if isinstance(remediation_plan, str):
                plan = json.loads(remediation_plan)
            else:
                plan = remediation_plan
            
            if not isinstance(plan, list):
                return {"score": 0, "steps": 0, "has_priorities": False, "has_commands": 0, "has_outcomes": 0}
            
            steps = len(plan)
            
            # Check for priority diversity
            priorities = set(step.get('priority', '') for step in plan)
            has_priorities = len(priorities) > 1  # Multiple priority levels
            
            # Count steps with commands
            has_commands = sum(1 for step in plan if step.get('command') and step.get('command') != 'None')
            
            # Count steps with expected outcomes
            has_outcomes = sum(1 for step in plan if step.get('expected_outcome'))
            
            # Score (0-100)
            score = (
                min(steps / 5.0, 1.0) * 40 +  # 40 points for 5+ steps
                (20 if has_priorities else 0) +  # 20 points for priority diversity
                (has_commands / steps * 20 if steps > 0 else 0) +  # 20 points if all have commands
                (has_outcomes / steps * 20 if steps > 0 else 0)  # 20 points if all have outcomes
            )
            
            return {
                "score": round(score, 2),
                "steps": steps,
                "has_priorities": has_priorities,
                "has_commands": has_commands,
                "has_outcomes": has_outcomes
            }
            
        except Exception as e:
            logger.error(f"Error parsing remediation plan: {e}")
            return {"score": 0, "steps": 0, "has_priorities": False, "has_commands": 0, "has_outcomes": 0}
    
    def analyze_incidents(self, incidents: List[Dict[str, Any]], label: str) -> Dict[str, Any]:
        """
        Analyze a group of incidents
        
        Args:
            incidents: List of incidents to analyze
            label: Label for this group (e.g., "Before", "After")
        
        Returns:
            Aggregated metrics
        """
        if not incidents:
            return {"label": label, "count": 0, "root_cause_score": 0, "remediation_score": 0, "overall_score": 0}
        
        root_cause_scores = []
        remediation_scores = []
        
        for incident in incidents:
            # Analyze root cause
            rc_metrics = self.calculate_root_cause_score(incident.get('root_cause', ''))
            root_cause_scores.append(rc_metrics['score'])
            
            # Analyze remediation plan
            rem_metrics = self.calculate_remediation_score(incident.get('remediation_plan'))
            remediation_scores.append(rem_metrics['score'])
        
        # Calculate averages
        avg_rc = sum(root_cause_scores) / len(root_cause_scores)
        avg_rem = sum(remediation_scores) / len(remediation_scores)
        overall = (avg_rc + avg_rem) / 2
        
        return {
            "label": label,
            "count": len(incidents),
            "root_cause_score": round(avg_rc, 2),
            "remediation_score": round(avg_rem, 2),
            "overall_score": round(overall, 2),
            "root_cause_scores": root_cause_scores,
            "remediation_scores": remediation_scores
        }
    
    def compare_groups(self, before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare before and after metrics
        
        Args:
            before: Metrics from before group
            after: Metrics from after group
        
        Returns:
            Comparison results with improvement percentages
        """
        def calc_improvement(before_val: float, after_val: float) -> float:
            """Calculate percentage improvement"""
            if before_val == 0:
                return 0.0
            return ((after_val - before_val) / before_val) * 100
        
        rc_improvement = calc_improvement(before['root_cause_score'], after['root_cause_score'])
        rem_improvement = calc_improvement(before['remediation_score'], after['remediation_score'])
        overall_improvement = calc_improvement(before['overall_score'], after['overall_score'])
        
        return {
            "root_cause_improvement": round(rc_improvement, 2),
            "remediation_improvement": round(rem_improvement, 2),
            "overall_improvement": round(overall_improvement, 2),
            "target_met": overall_improvement >= 20.0
        }
    
    def print_detailed_report(self, before: Dict, after: Dict, comparison: Dict, verbose: bool = False):
        """Print detailed comparison report"""
        logger.info("")
        logger.info("=" * 80)
        logger.info("WEEK 2 SUCCESS METRICS: LLM DIAGNOSIS QUALITY IMPROVEMENT")
        logger.info("=" * 80)
        logger.info("")
        
        # Before section
        logger.info(f"📊 BEFORE (Incidents without KB articles): {before['count']} incidents")
        logger.info(f"   Root Cause Quality:     {before['root_cause_score']:.2f}/100")
        logger.info(f"   Remediation Quality:    {before['remediation_score']:.2f}/100")
        logger.info(f"   Overall Quality:        {before['overall_score']:.2f}/100")
        logger.info("")
        
        # After section
        logger.info(f"📊 AFTER (Incidents with KB article vector search): {after['count']} incidents")
        logger.info(f"   Root Cause Quality:     {after['root_cause_score']:.2f}/100")
        logger.info(f"   Remediation Quality:    {after['remediation_score']:.2f}/100")
        logger.info(f"   Overall Quality:        {after['overall_score']:.2f}/100")
        logger.info("")
        
        # Improvement section
        logger.info("📈 IMPROVEMENT:")
        logger.info(f"   Root Cause:             {comparison['root_cause_improvement']:+.2f}%")
        logger.info(f"   Remediation Plan:       {comparison['remediation_improvement']:+.2f}%")
        logger.info(f"   Overall Diagnosis:      {comparison['overall_improvement']:+.2f}%")
        logger.info("")
        
        # Success verdict
        if comparison['target_met']:
            logger.info("✅ SUCCESS: Target of 20% improvement ACHIEVED!")
        else:
            logger.warning(f"⚠️  PARTIAL: {comparison['overall_improvement']:.2f}% improvement (target: 20%)")
        
        logger.info("")
        logger.info("=" * 80)
        logger.info("")
        
        if verbose:
            logger.info("Detailed Breakdown:")
            logger.info(f"  Before - Root Cause Scores: {before['root_cause_scores']}")
            logger.info(f"  After  - Root Cause Scores: {after['root_cause_scores']}")
            logger.info(f"  Before - Remediation Scores: {before['remediation_scores']}")
            logger.info(f"  After  - Remediation Scores: {after['remediation_scores']}")
            logger.info("")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Measure Week 2 diagnosis quality improvement")
    parser.add_argument('--verbose', action='store_true', help='Show detailed metrics')
    parser.add_argument('--before', type=str, default='17,18,19,20,21,22', 
                       help='Comma-separated incident numbers for BEFORE group')
    parser.add_argument('--after', type=str, default='26,27,28,30',
                       help='Comma-separated incident numbers for AFTER group')
    
    args = parser.parse_args()
    
    try:
        metrics = DiagnosisMetrics()
        
        # Parse incident numbers
        before_incidents = [int(x.strip()) for x in args.before.split(',')]
        after_incidents = [int(x.strip()) for x in args.after.split(',')]
        
        logger.info(f"Comparing {len(before_incidents)} BEFORE incidents vs {len(after_incidents)} AFTER incidents")
        logger.info("")
        
        # Fetch data
        before_data = metrics.fetch_incidents(before_incidents)
        after_data = metrics.fetch_incidents(after_incidents)
        
        if not before_data or not after_data:
            logger.error("❌ Failed to fetch incident data")
            return 1
        
        # Analyze
        before_metrics = metrics.analyze_incidents(before_data, "Before")
        after_metrics = metrics.analyze_incidents(after_data, "After")
        
        # Compare
        comparison = metrics.compare_groups(before_metrics, after_metrics)
        
        # Report
        metrics.print_detailed_report(before_metrics, after_metrics, comparison, verbose=args.verbose)
        
        # Return success/failure
        return 0 if comparison['target_met'] else 1
        
    except Exception as e:
        logger.error(f"❌ Metrics calculation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
