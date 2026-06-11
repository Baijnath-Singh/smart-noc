"""
Rollback Manager - Configuration backup and rollback capability
Ensures safe remediation by storing pre-change snapshots
"""

import json
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from loguru import logger


class RollbackManager:
    """Manage configuration snapshots and rollback operations"""
    
    def __init__(self, engine):
        self.engine = engine
        self.Session = sessionmaker(bind=engine)
    
    def create_snapshot(
        self,
        incident_number: int,
        device_name: str,
        configuration: str,
        snapshot_type: str = 'pre_remediation',
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Create configuration snapshot before remediation
        
        Returns:
            snapshot_id
        """
        try:
            # Calculate config hash for integrity verification
            config_hash = hashlib.sha256(configuration.encode()).hexdigest()
            
            with self.Session() as session:
                result = session.execute(
                    text("""
                        INSERT INTO configuration_snapshots (
                            incident_number,
                            device_name,
                            snapshot_type,
                            configuration,
                            config_hash,
                            metadata
                        ) VALUES (
                            :incident_number,
                            :device_name,
                            :snapshot_type,
                            :configuration,
                            :config_hash,
                            :metadata
                        )
                        RETURNING id
                    """),
                    {
                        'incident_number': incident_number,
                        'device_name': device_name,
                        'snapshot_type': snapshot_type,
                        'configuration': configuration,
                        'config_hash': config_hash,
                        'metadata': json.dumps(metadata or {})
                    }
                )
                snapshot_id = result.scalar()
                session.commit()
                
                logger.info(
                    f"✓ Configuration snapshot created for {device_name} "
                    f"(incident #{incident_number}, snapshot ID: {snapshot_id})"
                )
                
                return snapshot_id
                
        except Exception as e:
            logger.error(f"Failed to create configuration snapshot: {e}")
            raise
    
    def get_snapshot(self, snapshot_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve configuration snapshot"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT 
                            id, incident_number, device_name, snapshot_type,
                            configuration, config_hash, metadata, created_at
                        FROM configuration_snapshots
                        WHERE id = :snapshot_id
                    """),
                    {'snapshot_id': snapshot_id}
                ).fetchone()
                
                if not result:
                    return None
                
                return {
                    'id': result[0],
                    'incident_number': result[1],
                    'device_name': result[2],
                    'snapshot_type': result[3],
                    'configuration': result[4],
                    'config_hash': result[5],
                    'metadata': result[6] if result[6] else {},  # Already a dict from JSONB
                    'created_at': result[7]
                }
        except Exception as e:
            logger.error(f"Failed to retrieve snapshot: {e}")
            return None
    
    def execute_rollback(
        self,
        incident_number: int,
        snapshot_id: int,
        rollback_reason: str = 'manual_request',
        triggered_by: str = 'autonomous_system'
    ) -> bool:
        """
        Execute rollback to previous configuration
        
        This is a simulated rollback for the prototype.
        In production, this would:
        1. Connect to device via SSH/NETCONF
        2. Apply snapshot configuration
        3. Verify configuration was applied
        4. Run validation tests
        
        Returns:
            True if rollback successful
        """
        try:
            # Get snapshot
            snapshot = self.get_snapshot(snapshot_id)
            if not snapshot:
                logger.error(f"Snapshot {snapshot_id} not found")
                return False
            
            device_name = snapshot['device_name']
            config = snapshot['configuration']
            
            logger.info(f"🔄 Executing rollback for {device_name} (incident #{incident_number})")
            
            start_time = datetime.now()
            
            # SIMULATED: In production, execute actual rollback
            # For now, we'll simulate a successful rollback
            success = True
            error_message = None
            commands_executed = {
                'method': 'config_replace',
                'device': device_name,
                'snapshot_id': snapshot_id,
                'config_lines': len(config.split('\n')) if config else 0
            }
            
            # Simulate rollback time (1-5 seconds based on config size)
            import time
            time.sleep(0.5)  # Simulated execution time
            
            end_time = datetime.now()
            duration_seconds = int((end_time - start_time).total_seconds())
            
            # Record rollback in history
            with self.Session() as session:
                session.execute(
                    text("""
                        INSERT INTO rollback_history (
                            incident_number,
                            snapshot_id,
                            rollback_reason,
                            status,
                            started_at,
                            completed_at,
                            duration_seconds,
                            success,
                            error_message,
                            commands_executed,
                            triggered_by
                        ) VALUES (
                            :incident_number,
                            :snapshot_id,
                            :rollback_reason,
                            :status,
                            :started_at,
                            :completed_at,
                            :duration_seconds,
                            :success,
                            :error_message,
                            :commands_executed,
                            :triggered_by
                        )
                    """),
                    {
                        'incident_number': incident_number,
                        'snapshot_id': snapshot_id,
                        'rollback_reason': rollback_reason,
                        'status': 'completed' if success else 'failed',
                        'started_at': start_time,
                        'completed_at': end_time,
                        'duration_seconds': duration_seconds,
                        'success': success,
                        'error_message': error_message,
                        'commands_executed': json.dumps(commands_executed),
                        'triggered_by': triggered_by
                    }
                )
                session.commit()
            
            if success:
                logger.success(
                    f"✅ Rollback completed successfully for {device_name} "
                    f"(took {duration_seconds}s)"
                )
            else:
                logger.error(f"❌ Rollback failed for {device_name}: {error_message}")
            
            return success
            
        except Exception as e:
            logger.error(f"Rollback execution failed: {e}")
            
            # Record failure
            try:
                with self.Session() as session:
                    session.execute(
                        text("""
                            INSERT INTO rollback_history (
                                incident_number,
                                snapshot_id,
                                rollback_reason,
                                status,
                                success,
                                error_message,
                                triggered_by
                            ) VALUES (
                                :incident_number,
                                :snapshot_id,
                                :rollback_reason,
                                'failed',
                                false,
                                :error_message,
                                :triggered_by
                            )
                        """),
                        {
                            'incident_number': incident_number,
                            'snapshot_id': snapshot_id,
                            'rollback_reason': rollback_reason,
                            'error_message': str(e),
                            'triggered_by': triggered_by
                        }
                    )
                    session.commit()
            except:
                pass
            
            return False
    
    def verify_snapshot_integrity(self, snapshot_id: int) -> bool:
        """Verify snapshot hasn't been corrupted"""
        try:
            snapshot = self.get_snapshot(snapshot_id)
            if not snapshot:
                return False
            
            # Recalculate hash
            config = snapshot['configuration']
            calculated_hash = hashlib.sha256(config.encode()).hexdigest()
            stored_hash = snapshot['config_hash']
            
            if calculated_hash != stored_hash:
                logger.error(
                    f"❌ Snapshot {snapshot_id} integrity check FAILED "
                    f"(hash mismatch)"
                )
                return False
            
            logger.info(f"✓ Snapshot {snapshot_id} integrity verified")
            return True
            
        except Exception as e:
            logger.error(f"Snapshot integrity check failed: {e}")
            return False


if __name__ == '__main__':
    # Test rollback manager
    from sqlalchemy import create_engine
    
    DATABASE_URL = "postgresql://noc_admin:noc_admin_password@localhost:5432/smart_noc"
    engine = create_engine(DATABASE_URL)
    
    manager = RollbackManager(engine)
    
    # Test snapshot creation
    test_config = """
! Sample device configuration
hostname test-switch-01
!
interface GigabitEthernet0/1
 description Test interface
 switchport mode access
 switchport access vlan 100
!
end
"""
    
    print("\n✅ Testing Rollback Manager:")
    
    snapshot_id = manager.create_snapshot(
        incident_number=999,
        device_name='test-switch-01',
        configuration=test_config,
        metadata={'test': True, 'version': '1.0'}
    )
    print(f"   Created snapshot ID: {snapshot_id}")
    
    # Verify integrity
    is_valid = manager.verify_snapshot_integrity(snapshot_id)
    print(f"   Integrity check: {'✓ PASS' if is_valid else '✗ FAIL'}")
    
    # Test rollback
    success = manager.execute_rollback(
        incident_number=999,
        snapshot_id=snapshot_id,
        rollback_reason='test_rollback',
        triggered_by='test_script'
    )
    print(f"   Rollback execution: {'✓ SUCCESS' if success else '✗ FAILED'}")
