"""
Smart NOC - Database Connection and Models

SQLAlchemy ORM for PostgreSQL incident storage
"""

from sqlalchemy import create_engine, Column, String, Integer, Float, TIMESTAMP, JSON, ForeignKey, CheckConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

Base = declarative_base()


class Incident(Base):
    """Main incident table"""
    __tablename__ = 'incidents'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_number = Column(Integer, unique=True, nullable=False)
    incident_type = Column(String(100), nullable=False)
    severity = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default='ACTIVE')
    
    affected_device_count = Column(Integer, nullable=False, default=0)
    affected_devices = Column(JSON, nullable=False, default=[])
    primary_device = Column(String(255))
    anomaly_count = Column(Integer, nullable=False, default=0)
    
    start_time = Column(TIMESTAMP, nullable=False)
    end_time = Column(TIMESTAMP)
    duration_seconds = Column(Integer)
    
    correlation_method = Column(String(50), nullable=False)
    correlation_confidence = Column(Float)
    impact_score = Column(Float)
    
    root_cause = Column(String)
    remediation_plan = Column(String)
    incident_metadata = Column(JSON, default={})
    
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = Column(TIMESTAMP)
    
    # Relationships
    anomalies = relationship("IncidentAnomaly", back_populates="incident", cascade="all, delete-orphan")
    timeline = relationship("IncidentTimeline", back_populates="incident", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint("severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')", name='incidents_severity_check'),
        CheckConstraint("status IN ('ACTIVE', 'INVESTIGATING', 'RESOLVED', 'CLOSED')", name='incidents_status_check'),
    )
    
    def to_dict(self):
        """Convert incident to dictionary for Kafka publishing"""
        return {
            'id': str(self.id),
            'incident_number': self.incident_number,
            'incident_type': self.incident_type,
            'severity': self.severity,
            'status': self.status,
            'affected_device_count': self.affected_device_count,
            'affected_devices': self.affected_devices,
            'primary_device': self.primary_device,
            'anomaly_count': self.anomaly_count,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration_seconds,
            'correlation_method': self.correlation_method,
            'correlation_confidence': self.correlation_confidence,
            'impact_score': self.impact_score,
            'incident_metadata': self.incident_metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class IncidentAnomaly(Base):
    """Many-to-many relationship between incidents and anomalies"""
    __tablename__ = 'incident_anomalies'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(UUID(as_uuid=True), ForeignKey('incidents.id', ondelete='CASCADE'), nullable=False)
    
    anomaly_id = Column(String(255), nullable=False)
    device_id = Column(String(255), nullable=False)
    anomaly_type = Column(String(100), nullable=False)
    detection_method = Column(String(50), nullable=False)
    confidence = Column(Float)
    timestamp = Column(TIMESTAMP, nullable=False)
    anomaly_data = Column(JSON, nullable=False, default={})
    
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    
    # Relationships
    incident = relationship("Incident", back_populates="anomalies")


class IncidentTimeline(Base):
    """Incident audit trail"""
    __tablename__ = 'incident_timeline'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    incident_id = Column(UUID(as_uuid=True), ForeignKey('incidents.id', ondelete='CASCADE'), nullable=False)
    
    event_type = Column(String(50), nullable=False)
    description = Column(String, nullable=False)
    previous_status = Column(String(20))
    new_status = Column(String(20))
    changed_by = Column(String(100), default='SYSTEM')
    event_metadata = Column(JSON, default={})
    
    created_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow)
    
    # Relationships
    incident = relationship("Incident", back_populates="timeline")


class DatabaseManager:
    """Database connection and session management"""
    
    def __init__(self, config: dict):
        """Initialize database connection"""
        db_config = config['postgres']
        connection_string = (
            f"postgresql://{db_config['user']}:{db_config['password']}"
            f"@{db_config['host']}:{db_config['port']}/{db_config['database']}"
        )
        
        self.engine = create_engine(
            connection_string,
            pool_size=db_config.get('pool_size', 5),
            max_overflow=db_config.get('max_overflow', 10),
            pool_pre_ping=True  # Verify connections before using
        )
        
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def get_session(self):
        """Get a new database session"""
        return self.SessionLocal()
    
    def create_tables(self):
        """Create all tables (if not exists)"""
        Base.metadata.create_all(bind=self.engine)
