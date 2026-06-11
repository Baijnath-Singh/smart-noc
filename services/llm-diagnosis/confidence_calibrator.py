"""
Confidence Calibration System for LLM Diagnosis

This module implements confidence calibration to ensure LLM-reported confidence
scores accurately reflect actual diagnosis correctness. Uses isotonic regression
for calibration based on historical feedback.

Date: 2026-06-09
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
import os

logger = logging.getLogger(__name__)


@dataclass
class CalibrationData:
    """Container for calibration statistics"""
    confidence_bucket: float
    total_samples: int
    correct_samples: int
    actual_accuracy: float
    avg_reported_confidence: float
    calibration_error: float


class ConfidenceCalibrator:
    """
    Calibrates LLM confidence scores based on historical accuracy.
    
    Uses isotonic regression approach:
    - Buckets confidence scores into ranges (0.0-0.1, 0.1-0.2, etc.)
    - Calculates actual accuracy for each bucket
    - Maps reported confidence to calibrated confidence
    
    Example:
        If LLM reports 0.85 confidence but historically only 70% accurate
        in that range, calibrated confidence will be 0.70.
    """
    
    def __init__(self, engine: Optional[Engine] = None, min_samples: int = 5):
        """
        Initialize confidence calibrator.
        
        Args:
            engine: SQLAlchemy engine (creates new if None)
            min_samples: Minimum samples required for calibration
        """
        if engine is None:
            db_url = os.getenv(
                "DATABASE_URL",
                "postgresql://noc_admin:noc_password@postgres:5432/smart_noc"
            )
            self.engine = create_engine(db_url)
        else:
            self.engine = engine
            
        self.min_samples = min_samples
        self.calibration_map: Dict[str, Dict[float, float]] = {}
        self.last_update: Optional[datetime] = None
        
        # Refresh calibration on init
        self.refresh_calibration()
    
    def add_feedback(
        self,
        incident_number: int,  # Changed from str to int
        diagnosis_id: str,
        llm_confidence: float,
        predicted_root_cause: str,
        was_correct: bool,
        actual_root_cause: Optional[str] = None,
        engineer_notes: Optional[str] = None,
        engineer_id: Optional[str] = None,
        incident_type: Optional[str] = None,
        remediation_success: Optional[bool] = None,
        remediation_notes: Optional[str] = None,
        incident_timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Add engineer feedback on diagnosis correctness.
        
        Args:
            incident_number: Incident identifier
            diagnosis_id: UUID of diagnosis
            llm_confidence: Original LLM confidence (0.0-1.0)
            predicted_root_cause: What LLM predicted
            was_correct: Whether diagnosis was correct
            actual_root_cause: Actual root cause if different
            engineer_notes: Optional notes from engineer
            engineer_id: Who provided feedback
            incident_type: Type of incident for typed calibration
            remediation_success: Whether remediation succeeded
            remediation_notes: Notes on remediation outcome
            incident_timestamp: When incident occurred
            
        Returns:
            True if feedback stored successfully
        """
        try:
            query = text("""
                INSERT INTO diagnosis_feedback (
                    diagnosis_id, incident_number, llm_confidence,
                    predicted_root_cause, incident_type, was_correct,
                    actual_root_cause, engineer_notes, engineer_id,
                    remediation_success, remediation_notes,
                    incident_timestamp, feedback_timestamp
                ) VALUES (
                    :diagnosis_id, :incident_number, :llm_confidence,
                    :predicted_root_cause, :incident_type, :was_correct,
                    :actual_root_cause, :engineer_notes, :engineer_id,
                    :remediation_success, :remediation_notes,
                    :incident_timestamp, NOW()
                )
            """)
            
            with self.engine.connect() as conn:
                conn.execute(query, {
                    "diagnosis_id": diagnosis_id,
                    "incident_number": incident_number,
                    "llm_confidence": llm_confidence,
                    "predicted_root_cause": predicted_root_cause,
                    "incident_type": incident_type,
                    "was_correct": was_correct,
                    "actual_root_cause": actual_root_cause,
                    "engineer_notes": engineer_notes,
                    "engineer_id": engineer_id,
                    "remediation_success": remediation_success,
                    "remediation_notes": remediation_notes,
                    "incident_timestamp": incident_timestamp
                })
                conn.commit()
            
            logger.info(
                f"✓ Feedback stored for incident {incident_number}: "
                f"confidence={llm_confidence:.2f}, correct={was_correct}"
            )
            
            # Refresh calibration if significant feedback added
            if self._should_refresh():
                self.refresh_calibration()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store feedback: {str(e)}", exc_info=True)
            return False
    
    def calibrate(
        self,
        llm_confidence: float,
        incident_type: Optional[str] = None
    ) -> Tuple[float, str]:
        """
        Calibrate LLM confidence based on historical accuracy.
        
        Args:
            llm_confidence: Raw confidence from LLM (0.0-1.0)
            incident_type: Optional incident type for typed calibration
            
        Returns:
            Tuple of (calibrated_confidence, calibration_method)
        """
        # Validate input
        if not 0.0 <= llm_confidence <= 1.0:
            logger.warning(f"Invalid confidence {llm_confidence}, clamping to [0,1]")
            llm_confidence = max(0.0, min(1.0, llm_confidence))
        
        # Try incident-type-specific calibration first
        if incident_type and incident_type in self.calibration_map:
            calibrated = self._lookup_calibration(
                llm_confidence,
                self.calibration_map[incident_type]
            )
            if calibrated is not None:
                return calibrated, "type-specific"
        
        # Fall back to global calibration
        if "global" in self.calibration_map:
            calibrated = self._lookup_calibration(
                llm_confidence,
                self.calibration_map["global"]
            )
            if calibrated is not None:
                return calibrated, "global"
        
        # No calibration data available yet
        logger.debug(
            f"No calibration data for confidence={llm_confidence:.2f}, "
            f"type={incident_type}, returning uncalibrated"
        )
        return llm_confidence, "uncalibrated"
    
    def _lookup_calibration(
        self,
        confidence: float,
        calibration_table: Dict[float, float]
    ) -> Optional[float]:
        """
        Look up calibrated confidence from calibration table.
        
        Uses linear interpolation between buckets.
        """
        if not calibration_table:
            return None
        
        # Find bucket (0.0-0.1, 0.1-0.2, etc.)
        bucket = round(confidence * 10) / 10
        
        # Exact match
        if bucket in calibration_table:
            return calibration_table[bucket]
        
        # Interpolate between nearest buckets
        buckets = sorted(calibration_table.keys())
        
        # Below lowest bucket
        if confidence < buckets[0]:
            return calibration_table[buckets[0]]
        
        # Above highest bucket
        if confidence > buckets[-1]:
            return calibration_table[buckets[-1]]
        
        # Linear interpolation
        for i in range(len(buckets) - 1):
            if buckets[i] <= confidence <= buckets[i + 1]:
                lower_bucket = buckets[i]
                upper_bucket = buckets[i + 1]
                lower_cal = calibration_table[lower_bucket]
                upper_cal = calibration_table[upper_bucket]
                
                # Linear interpolation
                ratio = (confidence - lower_bucket) / (upper_bucket - lower_bucket)
                return lower_cal + ratio * (upper_cal - lower_cal)
        
        return None
    
    def refresh_calibration(self, lookback_days: int = 30) -> None:
        """
        Refresh calibration maps from database.
        
        Args:
            lookback_days: Number of days of history to use
        """
        try:
            # Get global calibration
            global_cal = self._compute_calibration(
                incident_type=None,
                lookback_days=lookback_days
            )
            if global_cal:
                self.calibration_map["global"] = global_cal
                logger.info(f"✓ Global calibration updated with {len(global_cal)} buckets")
            
            # Get per-incident-type calibration
            incident_types = self._get_incident_types()
            for itype in incident_types:
                type_cal = self._compute_calibration(
                    incident_type=itype,
                    lookback_days=lookback_days
                )
                if type_cal:
                    self.calibration_map[itype] = type_cal
                    logger.info(
                        f"✓ Calibration for '{itype}' updated with {len(type_cal)} buckets"
                    )
            
            self.last_update = datetime.now()
            logger.info(f"✓ Calibration refresh complete: {len(self.calibration_map)} maps")
            
        except Exception as e:
            logger.error(f"Failed to refresh calibration: {str(e)}", exc_info=True)
    
    def _compute_calibration(
        self,
        incident_type: Optional[str],
        lookback_days: int
    ) -> Optional[Dict[float, float]]:
        """
        Compute calibration map for specific incident type (or global).
        
        Returns:
            Dict mapping confidence bucket -> actual accuracy
        """
        try:
            if incident_type:
                query = text("""
                    SELECT 
                        FLOOR(llm_confidence * 10) / 10 AS confidence_bucket,
                        COUNT(*) as total,
                        AVG(CASE WHEN was_correct THEN 1.0 ELSE 0.0 END) as accuracy
                    FROM diagnosis_feedback
                    WHERE incident_type = :incident_type
                      AND feedback_timestamp > NOW() - INTERVAL ':days days'
                    GROUP BY FLOOR(llm_confidence * 10) / 10
                    HAVING COUNT(*) >= :min_samples
                    ORDER BY confidence_bucket
                """)
                params = {
                    "incident_type": incident_type,
                    "days": lookback_days,
                    "min_samples": self.min_samples
                }
            else:
                query = text("""
                    SELECT 
                        FLOOR(llm_confidence * 10) / 10 AS confidence_bucket,
                        COUNT(*) as total,
                        AVG(CASE WHEN was_correct THEN 1.0 ELSE 0.0 END) as accuracy
                    FROM diagnosis_feedback
                    WHERE feedback_timestamp > NOW() - INTERVAL ':days days'
                    GROUP BY FLOOR(llm_confidence * 10) / 10
                    HAVING COUNT(*) >= :min_samples
                    ORDER BY confidence_bucket
                """)
                params = {"days": lookback_days, "min_samples": self.min_samples}
            
            with self.engine.connect() as conn:
                result = conn.execute(query, params)
                rows = result.fetchall()
            
            if not rows:
                return None
            
            # Build calibration map
            calibration = {}
            for row in rows:
                bucket = float(row[0])
                accuracy = float(row[2])
                calibration[bucket] = accuracy
            
            return calibration if calibration else None
            
        except Exception as e:
            logger.error(f"Failed to compute calibration: {str(e)}", exc_info=True)
            return None
    
    def _get_incident_types(self) -> List[str]:
        """Get list of incident types with sufficient feedback."""
        try:
            query = text("""
                SELECT DISTINCT incident_type
                FROM diagnosis_feedback
                WHERE incident_type IS NOT NULL
                GROUP BY incident_type
                HAVING COUNT(*) >= :min_samples
            """)
            
            with self.engine.connect() as conn:
                result = conn.execute(query, {"min_samples": self.min_samples})
                return [row[0] for row in result.fetchall()]
                
        except Exception as e:
            logger.error(f"Failed to get incident types: {str(e)}", exc_info=True)
            return []
    
    def _should_refresh(self) -> bool:
        """Check if calibration should be refreshed."""
        if self.last_update is None:
            return True
        
        # Refresh every 1 hour
        return (datetime.now() - self.last_update) > timedelta(hours=1)
    
    def get_calibration_metrics(self) -> Dict[str, any]:
        """
        Get current calibration metrics for monitoring.
        
        Returns:
            Dict with calibration statistics
        """
        try:
            query = text("SELECT * FROM calibration_status")
            
            with self.engine.connect() as conn:
                result = conn.execute(query)
                row = result.fetchone()
            
            if not row:
                return {
                    "status": "no_data",
                    "total_feedback": 0,
                    "message": "No feedback data available yet"
                }
            
            return {
                "status": "active",
                "total_feedback": row[0],
                "total_correct": row[1],
                "overall_accuracy": float(row[2]),
                "avg_confidence": float(row[3]),
                "mean_absolute_error": float(row[4]),
                "incident_types_covered": row[5],
                "earliest_feedback": row[6],
                "latest_feedback": row[7],
                "calibration_maps": len(self.calibration_map),
                "last_update": self.last_update
            }
            
        except Exception as e:
            logger.error(f"Failed to get metrics: {str(e)}", exc_info=True)
            return {"status": "error", "error": str(e)}
    
    def get_calibration_data_by_bucket(
        self,
        incident_type: Optional[str] = None
    ) -> List[CalibrationData]:
        """
        Get detailed calibration data by confidence bucket.
        
        Args:
            incident_type: Filter by incident type (None for all)
            
        Returns:
            List of CalibrationData objects
        """
        try:
            if incident_type:
                query = text("""
                    SELECT * FROM confidence_calibration_metrics
                    WHERE incident_type = :incident_type
                    ORDER BY confidence_bucket DESC
                """)
                params = {"incident_type": incident_type}
            else:
                query = text("""
                    SELECT 
                        confidence_bucket,
                        'ALL' as incident_type,
                        SUM(total_diagnoses) as total_diagnoses,
                        SUM(correct_diagnoses) as correct_diagnoses,
                        ROUND(AVG(actual_accuracy)::numeric, 3) as actual_accuracy,
                        ROUND(AVG(avg_reported_confidence)::numeric, 3) as avg_reported_confidence,
                        ROUND(AVG(calibration_error)::numeric, 3) as calibration_error
                    FROM confidence_calibration_metrics
                    GROUP BY confidence_bucket
                    ORDER BY confidence_bucket DESC
                """)
                params = {}
            
            with self.engine.connect() as conn:
                result = conn.execute(query, params)
                rows = result.fetchall()
            
            return [
                CalibrationData(
                    confidence_bucket=float(row[0]),
                    total_samples=int(row[2]),
                    correct_samples=int(row[3]),
                    actual_accuracy=float(row[4]),
                    avg_reported_confidence=float(row[5]),
                    calibration_error=float(row[6])
                )
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"Failed to get calibration data: {str(e)}", exc_info=True)
            return []
    
    def get_calibration_stats(self, incident_type: Optional[str] = None) -> Optional[Dict]:
        """
        Get calibration statistics for historical accuracy feedback.
        Used to inform LLM about its past performance.
        
        Args:
            incident_type: Specific incident type (None for all types)
            
        Returns:
            Dict with:
            - total_samples: Total feedback records
            - confidence_buckets: List of {confidence, accuracy, count, gap}
            - overall_overconfidence: Average overconfidence gap
            - common_mistakes: List of common error patterns
        """
        try:
            # Get data by bucket
            bucket_data = self.get_calibration_data_by_bucket(incident_type)
            
            if not bucket_data:
                return None
            
            # Calculate stats
            total_samples = sum(d.total_samples for d in bucket_data)
            
            if total_samples < 5:
                return {
                    'total_samples': total_samples,
                    'insufficient_data': True
                }
            
            # Format bucket data
            confidence_buckets = [
                {
                    'confidence': d.avg_reported_confidence,
                    'accuracy': d.actual_accuracy,
                    'count': d.total_samples,
                    'gap': d.calibration_error
                }
                for d in bucket_data
            ]
            
            # Calculate overall overconfidence
            overall_gap = sum(d['gap'] * d['count'] for d in confidence_buckets) / total_samples
            
            # Get common mistakes (high overconfidence cases)
            common_mistakes = []
            for bucket in confidence_buckets:
                if bucket['gap'] > 0.2 and bucket['count'] >= 3:
                    common_mistakes.append({
                        'description': f"At {bucket['confidence']:.0%} confidence, only {bucket['accuracy']:.0%} accurate ({bucket['count']} cases)"
                    })
            
            return {
                'total_samples': total_samples,
                'confidence_buckets': confidence_buckets,
                'overall_overconfidence': overall_gap,
                'common_mistakes': common_mistakes
            }
            
        except Exception as e:
            logger.error(f"Failed to get calibration stats: {str(e)}", exc_info=True)
            return None
