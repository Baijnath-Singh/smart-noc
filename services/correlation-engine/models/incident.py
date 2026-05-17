"""
Smart NOC - Incident Management

Helper functions for creating and managing incidents
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from loguru import logger

from models.database import Incident, IncidentAnomaly, IncidentTimeline


class IncidentManager:
    """Manages incident creation, updates, and queries"""
    
    def __init__(self, config: dict):
        """Initialize incident manager"""
        self.config = config
        self.correlation_config = config.get('correlation', {})
    
    def create_incident(
        self,
        db: Session,
        anomalies: List[Dict],
        incident_type: str,
        correlation_method: str,
        metadata: Optional[Dict] = None
    ) -> Incident:
        """
        Create a new incident from correlated anomalies
        
        Args:
            db: Database session
            anomalies: List of anomaly dictionaries
            incident_type: Type of incident
            correlation_method: Method used for correlation
            metadata: Additional incident metadata
            
        Returns:
            Created incident object
        """
        if not anomalies:
            raise ValueError("Cannot create incident without anomalies")
        
        # Calculate incident severity based on anomalies
        severity = self._calculate_severity(anomalies)
        
        # Get affected devices
        affected_devices = list(set(a.get('device_id') for a in anomalies if a.get('device_id')))
        
        # Determine primary device (most anomalies)
        device_counts = {}
        for anomaly in anomalies:
            device_id = anomaly.get('device_id')
            if device_id:
                device_counts[device_id] = device_counts.get(device_id, 0) + 1
        primary_device = max(device_counts.items(), key=lambda x: x[1])[0] if device_counts else None
        
        # Get time range
        timestamps = [datetime.fromisoformat(a['timestamp'].replace('Z', '+00:00')) 
                     for a in anomalies if a.get('timestamp')]
        start_time = min(timestamps) if timestamps else datetime.utcnow()
        
        # Calculate impact score
        impact_score = self._calculate_impact(anomalies, len(affected_devices))
        
        # Get next incident number
        max_number = db.query(func.max(Incident.incident_number)).scalar() or 0
        
        # Create incident
        incident = Incident(
            incident_number=max_number + 1,
            incident_type=incident_type,
            severity=severity,
            status='ACTIVE',
            affected_device_count=len(affected_devices),
            affected_devices=affected_devices,
            primary_device=primary_device,
            anomaly_count=len(anomalies),
            start_time=start_time,
            correlation_method=correlation_method,
            correlation_confidence=self._calculate_correlation_confidence(anomalies, correlation_method),
            impact_score=impact_score,
            incident_metadata=metadata or {}
        )
        
        db.add(incident)
        db.flush()  # Get incident.id for anomaly linking
        
        # Add anomalies to incident
        for anomaly in anomalies:
            self.add_anomaly_to_incident(db, incident, anomaly)
        
        # Create timeline entry
        self._add_timeline_event(
            db, incident.id, 'CREATED',
            f"Incident created with {len(anomalies)} anomaly(ies) via {correlation_method}"
        )
        
        db.commit()
        
        logger.success(f"Created incident #{incident.incident_number}: {incident_type} (severity: {severity}, devices: {len(affected_devices)})")
        
        return incident
    
    def add_anomaly_to_incident(self, db: Session, incident: Incident, anomaly: Dict):
        """Add an anomaly to an existing incident"""
        incident_anomaly = IncidentAnomaly(
            incident_id=incident.id,
            anomaly_id=anomaly.get('fingerprint', str(anomaly.get('timestamp'))),
            device_id=anomaly.get('device_id', 'unknown'),
            anomaly_type=anomaly.get('anomaly_type', 'UNKNOWN'),
            detection_method=anomaly.get('detection_method', 'UNKNOWN'),
            confidence=anomaly.get('confidence'),
            timestamp=datetime.fromisoformat(anomaly['timestamp'].replace('Z', '+00:00')) if anomaly.get('timestamp') else datetime.utcnow(),
            anomaly_data=anomaly
        )
        db.add(incident_anomaly)
    
    def find_active_incidents(
        self,
        db: Session,
        time_window_minutes: int = 5,
        incident_type: Optional[str] = None
    ) -> List[Incident]:
        """
        Find active incidents within a time window
        
        Args:
            db: Database session
            time_window_minutes: Time window to look back
            incident_type: Optional filter by incident type
            
        Returns:
            List of active incidents
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)
        
        query = db.query(Incident).filter(
            and_(
                Incident.status.in_(['ACTIVE', 'INVESTIGATING']),
                Incident.start_time >= cutoff_time
            )
        )
        
        if incident_type:
            query = query.filter(Incident.incident_type == incident_type)
        
        return query.order_by(Incident.start_time.desc()).all()
    
    def update_incident_status(self, db: Session, incident: Incident, new_status: str, reason: str = ''):
        """Update incident status"""
        old_status = incident.status
        incident.status = new_status
        
        if new_status in ['RESOLVED', 'CLOSED']:
            incident.end_time = datetime.utcnow()
            incident.resolved_at = datetime.utcnow()
        
        self._add_timeline_event(
            db, incident.id, 'STATUS_CHANGED',
            f"Status changed from {old_status} to {new_status}. {reason}",
            previous_status=old_status,
            new_status=new_status
        )
        
        db.commit()
        logger.info(f"Incident #{incident.incident_number} status: {old_status} → {new_status}")
    
    def _calculate_severity(self, anomalies: List[Dict]) -> str:
        """Calculate incident severity from anomalies"""
        severity_weights = self.correlation_config.get('severity_weights', {
            'CRITICAL': 100,
            'HIGH': 75,
            'MEDIUM': 50,
            'LOW': 25
        })
        
        # Collect anomaly severities
        total_score = 0
        count = 0
        
        for anomaly in anomalies:
            severity = anomaly.get('severity', 'MEDIUM')
            total_score += severity_weights.get(severity, 50)
            count += 1
        
        avg_score = total_score / count if count > 0 else 50
        
        # Determine incident severity
        if avg_score >= 90:
            return 'CRITICAL'
        elif avg_score >= 70:
            return 'HIGH'
        elif avg_score >= 40:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _calculate_impact(self, anomalies: List[Dict], device_count: int) -> float:
        """Calculate business impact score (0-100)"""
        # Simple impact calculation based on:
        # - Number of affected devices (40%)
        # - Number of anomalies (30%)
        # - Severity average (30%)
        
        device_score = min(device_count * 10, 40)  # Cap at 40
        anomaly_score = min(len(anomalies) * 3, 30)  # Cap at 30
        
        severity_map = {'CRITICAL': 30, 'HIGH': 22, 'MEDIUM': 15, 'LOW': 7}
        severity_scores = [severity_map.get(a.get('severity', 'MEDIUM'), 15) for a in anomalies]
        avg_severity_score = sum(severity_scores) / len(severity_scores) if severity_scores else 15
        
        return round(device_score + anomaly_score + avg_severity_score, 2)
    
    def _calculate_correlation_confidence(self, anomalies: List[Dict], method: str) -> float:
        """Calculate confidence in correlation accuracy"""
        # Base confidence by method
        method_confidence = {
            'TIME_BASED': 60.0,
            'PATTERN_BASED': 75.0,
            'TOPOLOGY_BASED': 85.0,
            'MULTI_METHOD': 90.0
        }
        
        base_confidence = method_confidence.get(method, 50.0)
        
        # Boost confidence if anomalies are similar
        types = [a.get('anomaly_type') for a in anomalies]
        if len(set(types)) == 1:  # All same type
            base_confidence += 10
        
        # Boost if multiple devices
        devices = set(a.get('device_id') for a in anomalies if a.get('device_id'))
        if len(devices) >= 3:
            base_confidence += 5
        
        return round(min(base_confidence, 100.0), 2)
    
    def _add_timeline_event(
        self,
        db: Session,
        incident_id: str,
        event_type: str,
        description: str,
        previous_status: Optional[str] = None,
        new_status: Optional[str] = None
    ):
        """Add event to incident timeline"""
        event = IncidentTimeline(
            incident_id=incident_id,
            event_type=event_type,
            description=description,
            previous_status=previous_status,
            new_status=new_status
        )
        db.add(event)
