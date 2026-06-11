"""
Risk Assessor - Evaluates remediation risk for incidents
Determines safety level for autonomous execution
"""

from typing import Dict, Any, Tuple
from datetime import datetime, time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from loguru import logger


class RiskAssessor:
    """Assess risk level for autonomous remediation"""
    
    # Risk scoring weights
    WEIGHTS = {
        'device_criticality': 0.40,  # Most important factor
        'blast_radius': 0.25,         # How many devices affected
        'time_sensitivity': 0.20,     # Business hours vs off-hours
        'change_complexity': 0.15      # How complex is the remediation
    }
    
    # Business hours definition
    BUSINESS_HOURS_START = time(8, 0)   # 8:00 AM
    BUSINESS_HOURS_END = time(18, 0)     # 6:00 PM
    
    def __init__(self, engine):
        self.engine = engine
        self.Session = sessionmaker(bind=engine)
        self.device_criticality_cache = {}
        self._load_device_criticality()
    
    def _load_device_criticality(self):
        """Load device criticality from database"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT device_name, criticality, business_impact, requires_approval
                    FROM device_criticality
                """))
                
                for row in result:
                    self.device_criticality_cache[row[0]] = {
                        'criticality': row[1],
                        'business_impact': row[2],
                        'requires_approval': row[3]
                    }
            
            logger.info(f"✓ Loaded criticality for {len(self.device_criticality_cache)} devices")
        except Exception as e:
            logger.error(f"Failed to load device criticality: {e}")
    
    def assess_risk(
        self,
        incident: Dict[str, Any],
        diagnosis: Dict[str, Any]
    ) -> Tuple[str, float, Dict[str, Any]]:
        """
        Assess risk level for remediation
        
        Returns:
            (risk_level, risk_score, factors)
            risk_level: 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
            risk_score: 0.0-1.0
            factors: Dict of individual risk factors
        """
        factors = {}
        
        # 1. Device criticality score
        device_criticality_score = self._assess_device_criticality(incident, factors)
        
        # 2. Blast radius score
        blast_radius_score = self._assess_blast_radius(incident, factors)
        
        # 3. Time sensitivity score
        time_sensitivity_score = self._assess_time_sensitivity(incident, factors)
        
        # 4. Change complexity score
        change_complexity_score = self._assess_change_complexity(diagnosis, factors)
        
        # Calculate weighted overall risk score
        overall_risk_score = (
            device_criticality_score * self.WEIGHTS['device_criticality'] +
            blast_radius_score * self.WEIGHTS['blast_radius'] +
            time_sensitivity_score * self.WEIGHTS['time_sensitivity'] +
            change_complexity_score * self.WEIGHTS['change_complexity']
        )
        
        # Determine risk level
        risk_level = self._score_to_level(overall_risk_score)
        
        # Log assessment
        logger.info(
            f"📊 Risk Assessment: {risk_level} (score: {overall_risk_score:.2f}) "
            f"for incident #{incident.get('incident_number', 'unknown')}"
        )
        logger.debug(f"   Device Criticality: {device_criticality_score:.2f}")
        logger.debug(f"   Blast Radius: {blast_radius_score:.2f}")
        logger.debug(f"   Time Sensitivity: {time_sensitivity_score:.2f}")
        logger.debug(f"   Change Complexity: {change_complexity_score:.2f}")
        
        factors['overall_risk_score'] = overall_risk_score
        
        return risk_level, overall_risk_score, factors
    
    def _assess_device_criticality(self, incident: Dict[str, Any], factors: Dict) -> float:
        """
        Assess device criticality (40% of total risk)
        Returns score 0.0-1.0 (higher = more risky)
        """
        primary_device = incident.get('primary_device')
        affected_devices = incident.get('affected_devices', [])
        
        if isinstance(affected_devices, str):
            # Parse JSON string if needed
            import json
            try:
                affected_devices = json.loads(affected_devices)
            except:
                affected_devices = [affected_devices] if affected_devices else []
        
        # Check all affected devices
        max_criticality = 0.0
        criticality_details = []
        
        for device in [primary_device] + list(affected_devices):
            if not device:
                continue
                
            device_info = self.device_criticality_cache.get(device, {
                'criticality': 'MEDIUM',
                'business_impact': 'MEDIUM',
                'requires_approval': False
            })
            
            # Map criticality to score
            criticality_score = {
                'LOW': 0.25,
                'MEDIUM': 0.50,
                'HIGH': 0.75,
                'CRITICAL': 1.0
            }.get(device_info['criticality'], 0.50)
            
            max_criticality = max(max_criticality, criticality_score)
            
            criticality_details.append({
                'device': device,
                'criticality': device_info['criticality'],
                'score': criticality_score,
                'requires_approval': device_info['requires_approval']
            })
        
        factors['device_criticality_score'] = max_criticality
        factors['device_criticality_details'] = criticality_details
        factors['highest_device_criticality'] = criticality_details[0]['criticality'] if criticality_details else 'MEDIUM'
        
        return max_criticality
    
    def _assess_blast_radius(self, incident: Dict[str, Any], factors: Dict) -> float:
        """
        Assess blast radius (25% of total risk)
        More devices affected = higher risk
        Returns score 0.0-1.0
        """
        affected_count = incident.get('affected_device_count', 1)
        anomaly_count = incident.get('anomaly_count', 1)
        
        # Score based on device count
        # 1 device = 0.2, 2-3 devices = 0.4, 4-5 devices = 0.6, 6-10 = 0.8, 10+ = 1.0
        if affected_count <= 1:
            device_score = 0.2
        elif affected_count <= 3:
            device_score = 0.4
        elif affected_count <= 5:
            device_score = 0.6
        elif affected_count <= 10:
            device_score = 0.8
        else:
            device_score = 1.0
        
        # Adjust for anomaly complexity
        # More anomalies = more complex issue = higher risk
        anomaly_factor = min(anomaly_count / 10.0, 0.3)  # Cap at 0.3
        
        blast_radius_score = min(device_score + anomaly_factor, 1.0)
        
        factors['blast_radius_score'] = blast_radius_score
        factors['affected_device_count'] = affected_count
        factors['anomaly_count'] = anomaly_count
        
        return blast_radius_score
    
    def _assess_time_sensitivity(self, incident: Dict[str, Any], factors: Dict) -> float:
        """
        Assess time sensitivity (20% of total risk)
        Business hours = higher risk
        Returns score 0.0-1.0
        """
        now = datetime.now()
        current_time = now.time()
        is_weekday = now.weekday() < 5  # Monday = 0, Sunday = 6
        
        # Business hours check
        is_business_hours = (
            is_weekday and 
            self.BUSINESS_HOURS_START <= current_time <= self.BUSINESS_HOURS_END
        )
        
        # Incident severity factor
        severity = incident.get('severity', 'MEDIUM')
        severity_score = {
            'LOW': 0.2,
            'MEDIUM': 0.5,
            'HIGH': 0.8,
            'CRITICAL': 1.0
        }.get(severity, 0.5)
        
        # Higher risk during business hours
        if is_business_hours:
            time_score = severity_score * 1.2  # 20% increase during business hours
        else:
            time_score = severity_score * 0.7  # 30% reduction off-hours
        
        time_score = min(time_score, 1.0)  # Cap at 1.0
        
        factors['time_sensitivity_score'] = time_score
        factors['is_business_hours'] = is_business_hours
        factors['is_weekday'] = is_weekday
        factors['current_time'] = current_time.strftime('%H:%M:%S')
        factors['severity'] = severity
        
        return time_score
    
    def _assess_change_complexity(self, diagnosis: Dict[str, Any], factors: Dict) -> float:
        """
        Assess remediation complexity (15% of total risk)
        More complex changes = higher risk
        Returns score 0.0-1.0
        """
        remediation_plan = diagnosis.get('remediation_plan', [])
        
        if not remediation_plan:
            factors['change_complexity_score'] = 0.5
            factors['remediation_step_count'] = 0
            return 0.5
        
        step_count = len(remediation_plan)
        
        # Analyze remediation steps for complexity
        complexity_score = 0.0
        risky_keywords = ['reboot', 'restart', 'reload', 'shutdown', 'delete', 'remove', 'format']
        safe_keywords = ['show', 'display', 'verify', 'check', 'view']
        
        risky_commands = 0
        safe_commands = 0
        
        for step in remediation_plan:
            command = step.get('command', '').lower()
            action = step.get('action', '').lower()
            
            # Check for risky operations
            if any(keyword in command or keyword in action for keyword in risky_keywords):
                risky_commands += 1
            elif any(keyword in command or keyword in action for keyword in safe_keywords):
                safe_commands += 1
        
        # Base complexity on step count
        # 1-2 steps = 0.2, 3-4 = 0.4, 5-6 = 0.6, 7-10 = 0.8, 10+ = 1.0
        if step_count <= 2:
            base_complexity = 0.2
        elif step_count <= 4:
            base_complexity = 0.4
        elif step_count <= 6:
            base_complexity = 0.6
        elif step_count <= 10:
            base_complexity = 0.8
        else:
            base_complexity = 1.0
        
        # Adjust for risky commands
        risky_factor = min(risky_commands * 0.2, 0.4)  # Each risky command adds 0.2, cap at 0.4
        safe_factor = min(safe_commands * 0.1, 0.2)     # Each safe command reduces by 0.1, cap at -0.2
        
        complexity_score = base_complexity + risky_factor - safe_factor
        complexity_score = max(0.1, min(complexity_score, 1.0))  # Clamp to 0.1-1.0
        
        factors['change_complexity_score'] = complexity_score
        factors['remediation_step_count'] = step_count
        factors['risky_command_count'] = risky_commands
        factors['safe_command_count'] = safe_commands
        
        return complexity_score
    
    def _score_to_level(self, score: float) -> str:
        """Convert risk score to risk level"""
        if score >= 0.75:
            return 'CRITICAL'
        elif score >= 0.60:
            return 'HIGH'
        elif score >= 0.40:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def save_risk_assessment(
        self,
        incident_number: int,
        risk_level: str,
        risk_score: float,
        factors: Dict[str, Any]
    ):
        """Save risk assessment to database"""
        try:
            with self.Session() as session:
                session.execute(
                    text("""
                        INSERT INTO incident_risk_assessment (
                            incident_number,
                            risk_level,
                            device_criticality,
                            blast_radius_score,
                            time_sensitivity_score,
                            change_complexity_score,
                            overall_risk_score,
                            factors
                        ) VALUES (
                            :incident_number,
                            :risk_level,
                            :device_criticality,
                            :blast_radius_score,
                            :time_sensitivity_score,
                            :change_complexity_score,
                            :overall_risk_score,
                            CAST(:factors AS jsonb)
                        )
                    """),
                    {
                        'incident_number': incident_number,
                        'risk_level': risk_level,
                        'device_criticality': factors.get('highest_device_criticality', 'MEDIUM'),
                        'blast_radius_score': factors.get('blast_radius_score', 0.5),
                        'time_sensitivity_score': factors.get('time_sensitivity_score', 0.5),
                        'change_complexity_score': factors.get('change_complexity_score', 0.5),
                        'overall_risk_score': risk_score,
                        'factors': json.dumps(factors)
                    }
                )
                session.commit()
                logger.info(f"✓ Risk assessment saved for incident #{incident_number}")
        except Exception as e:
            logger.error(f"Failed to save risk assessment: {e}")
            raise


import json

if __name__ == '__main__':
    # Test risk assessor
    from sqlalchemy import create_engine
    
    DATABASE_URL = "postgresql://noc_admin:noc_admin_password@localhost:5432/smart_noc"
    engine = create_engine(DATABASE_URL)
    
    assessor = RiskAssessor(engine)
    
    # Test incident
    test_incident = {
        'incident_number': 999,
        'primary_device': 'access-switch-12',
        'affected_devices': ['access-switch-12'],
        'affected_device_count': 1,
        'anomaly_count': 2,
        'severity': 'MEDIUM'
    }
    
    test_diagnosis = {
        'remediation_plan': [
            {'command': 'show vlan', 'action': 'Verify VLAN configuration'},
            {'command': 'switchport mode trunk', 'action': 'Fix trunk port'}
        ]
    }
    
    risk_level, risk_score, factors = assessor.assess_risk(test_incident, test_diagnosis)
    
    print(f"\n✅ Risk Assessment Test:")
    print(f"   Risk Level: {risk_level}")
    print(f"   Risk Score: {risk_score:.2f}")
    print(f"   Factors: {json.dumps(factors, indent=2)}")
