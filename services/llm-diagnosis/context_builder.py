"""
Context Builder - Aggregates incident data for LLM analysis
Fetches anomalies, device history, and similar past incidents
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

import config

# Week 2: Vector Service Integration
try:
    import sys
    sys.path.append('/vector_service')  # Add vector service directory to path
    from vector_service import VectorKnowledgeBase
    VECTOR_SERVICE_AVAILABLE = True
    logger.info("Vector service module loaded successfully")
except ImportError as e:
    logger.warning(f"Vector service not available: {e}")
    VECTOR_SERVICE_AVAILABLE = False


class ContextBuilder:
    """Builds rich context for LLM diagnosis"""
    
    def __init__(self):
        self.engine = create_engine(config.DATABASE_URL)
        self.Session = sessionmaker(bind=self.engine)
        
        # Week 2: Initialize Vector Service
        self.vector_kb = None
        if config.VECTOR_SERVICE_ENABLED and VECTOR_SERVICE_AVAILABLE:
            try:
                self.vector_kb = VectorKnowledgeBase(
                    chromadb_host=config.VECTOR_CHROMADB_HOST,
                    chromadb_port=config.VECTOR_CHROMADB_PORT
                )
                logger.info("Vector Knowledge Base initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Vector KB: {e}")
                self.vector_kb = None
        
        logger.info("Context Builder initialized")
    
    def build_context(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        """Build complete context for an incident"""
        incident_id = incident.get('id')
        incident_number = incident.get('incident_number')
        primary_device = incident.get('primary_device')
        incident_type = incident.get('incident_type')
        
        logger.info(f"Building context for incident #{incident_number}")
        
        context = {
            'incident': incident,
            'anomalies': self._get_incident_anomalies(incident_id),
            'anomaly_summary': None,
            'anomaly_types_distribution': None,
            'device_history': None,
            'similar_incidents': None,
            'temporal_pattern': None,
            # Week 2: Vector search results
            'vector_similar_incidents': None,
            'vector_kb_articles': None,
        }
        
        # Build anomaly summary
        if context['anomalies']:
            context['anomaly_summary'] = self._summarize_anomalies(context['anomalies'])
            context['anomaly_types_distribution'] = self._get_anomaly_type_distribution(context['anomalies'])
            context['temporal_pattern'] = self._analyze_temporal_pattern(context['anomalies'])
        
        # Get device history
        if primary_device:
            context['device_history'] = self._get_device_incident_history(
                primary_device,
                hours=config.CONTEXT_DEVICE_HISTORY_HOURS
            )
        
        # Find similar past incidents
        if incident_type and incident_type != 'UNKNOWN':
            context['similar_incidents'] = self._get_similar_incidents(
                incident_type,
                primary_device,
                limit=config.CONTEXT_HISTORICAL_INCIDENTS
            )
        
        # Week 2: Vector-based similarity search
        if self.vector_kb:
            try:
                # Build search query from incident
                search_query = self._build_vector_search_query(incident)
                
                # Find similar incidents via vector search
                context['vector_similar_incidents'] = self._get_vector_similar_incidents(
                    search_query,
                    incident_type
                )
                
                # Find relevant KB articles
                context['vector_kb_articles'] = self._get_vector_relevant_kb(
                    search_query,
                    incident_type,
                    primary_device
                )
                
                logger.info(f"Vector search completed for incident #{incident_number}")
            except Exception as e:
                logger.error(f"Vector search failed: {e}")
        
        return context
    
    def _get_incident_anomalies(self, incident_id: str) -> List[Dict[str, Any]]:
        """Fetch all anomalies for an incident"""
        try:
            with self.Session() as session:
                query = text("""
                    SELECT 
                        anomaly_id,
                        device_id,
                        anomaly_type,
                        detection_method,
                        confidence,
                        timestamp,
                        anomaly_data
                    FROM incident_anomalies
                    WHERE incident_id = :incident_id
                    ORDER BY timestamp
                    LIMIT :max_anomalies
                """)
                
                result = session.execute(
                    query,
                    {
                        'incident_id': incident_id,
                        'max_anomalies': config.CONTEXT_MAX_ANOMALIES
                    }
                )
                
                anomalies = []
                for row in result:
                    anomalies.append({
                        'anomaly_id': row.anomaly_id,
                        'device_id': row.device_id,
                        'anomaly_type': row.anomaly_type,
                        'detection_method': row.detection_method,
                        'confidence': float(row.confidence) if row.confidence else 0.0,
                        'timestamp': row.timestamp.isoformat() if row.timestamp else None,
                        'anomaly_data': row.anomaly_data or {}
                    })
                
                logger.debug(f"Fetched {len(anomalies)} anomalies for incident {incident_id}")
                return anomalies
                
        except Exception as e:
            logger.error(f"Error fetching anomalies: {e}")
            return []
    
    def _summarize_anomalies(self, anomalies: List[Dict[str, Any]]) -> str:
        """Create human-readable anomaly summary"""
        if not anomalies:
            return "No anomalies available"
        
        lines = []
        for i, anomaly in enumerate(anomalies[:20], 1):  # Limit to 20 for readability
            device = anomaly.get('device_id', 'unknown')
            anom_type = anomaly.get('anomaly_type', 'unknown')
            timestamp = anomaly.get('timestamp', '')
            confidence = anomaly.get('confidence', 0.0)
            method = anomaly.get('detection_method', 'unknown')
            
            # Extract key metrics from anomaly_data
            data = anomaly.get('anomaly_data', {})
            metrics = []
            if 'cpu_utilization' in data:
                metrics.append(f"CPU: {data['cpu_utilization']}%")
            if 'memory_utilization' in data:
                metrics.append(f"MEM: {data['memory_utilization']}%")
            if 'packet_loss_percent' in data:
                metrics.append(f"Loss: {data['packet_loss_percent']}%")
            if 'interface' in data:
                metrics.append(f"Interface: {data['interface']}")
            
            metrics_str = ", ".join(metrics) if metrics else ""
            
            lines.append(
                f"{i}. [{timestamp}] {device} - {anom_type} "
                f"(confidence: {confidence:.2f}, method: {method})"
                + (f" - {metrics_str}" if metrics_str else "")
            )
        
        if len(anomalies) > 20:
            lines.append(f"... and {len(anomalies) - 20} more anomalies")
        
        return "\n".join(lines)
    
    def _get_anomaly_type_distribution(self, anomalies: List[Dict[str, Any]]) -> str:
        """Get distribution of anomaly types"""
        from collections import Counter
        
        types = [a.get('anomaly_type', 'UNKNOWN') for a in anomalies]
        distribution = Counter(types)
        
        lines = []
        for anom_type, count in distribution.most_common():
            percentage = (count / len(anomalies)) * 100
            lines.append(f"- {anom_type}: {count} ({percentage:.1f}%)")
        
        return "\n".join(lines)
    
    def _analyze_temporal_pattern(self, anomalies: List[Dict[str, Any]]) -> str:
        """Analyze temporal distribution of anomalies"""
        if not anomalies:
            return "No temporal data"
        
        timestamps = [a.get('timestamp') for a in anomalies if a.get('timestamp')]
        if len(timestamps) < 2:
            return "Insufficient temporal data"
        
        # Parse timestamps
        parsed_times = []
        for ts in timestamps:
            try:
                if isinstance(ts, str):
                    parsed_times.append(datetime.fromisoformat(ts.replace('Z', '+00:00')))
                elif isinstance(ts, datetime):
                    parsed_times.append(ts)
            except:
                continue
        
        if len(parsed_times) < 2:
            return "Could not parse timestamps"
        
        parsed_times.sort()
        first = parsed_times[0]
        last = parsed_times[-1]
        duration = (last - first).total_seconds()
        
        # Calculate rate
        rate = len(parsed_times) / max(duration / 60, 1)  # anomalies per minute
        
        return (
            f"Timespan: {duration:.0f} seconds ({duration/60:.1f} minutes)\n"
            f"Anomaly rate: {rate:.2f} anomalies/minute\n"
            f"First: {first.strftime('%H:%M:%S')}, Last: {last.strftime('%H:%M:%S')}"
        )
    
    def _get_device_incident_history(self, device_id: str, hours: int = 24) -> str:
        """Get recent incident history for a device"""
        try:
            with self.Session() as session:
                cutoff_time = datetime.utcnow() - timedelta(hours=hours)
                
                query = text("""
                    SELECT 
                        incident_number,
                        incident_type,
                        severity,
                        created_at,
                        root_cause
                    FROM incidents
                    WHERE primary_device = :device_id
                      AND created_at >= :cutoff_time
                    ORDER BY created_at DESC
                    LIMIT 10
                """)
                
                result = session.execute(
                    query,
                    {'device_id': device_id, 'cutoff_time': cutoff_time}
                )
                
                incidents = []
                for row in result:
                    incidents.append(
                        f"- Incident #{row.incident_number}: {row.incident_type} "
                        f"({row.severity}) at {row.created_at.strftime('%H:%M:%S')}"
                        + (f" - {row.root_cause[:100]}..." if row.root_cause else "")
                    )
                
                if incidents:
                    return f"Recent {hours}h history for {device_id}:\n" + "\n".join(incidents)
                else:
                    return f"No incidents for {device_id} in the past {hours} hours"
                    
        except Exception as e:
            logger.error(f"Error fetching device history: {e}")
            return "Device history unavailable"
    
    def _get_similar_incidents(
        self, 
        incident_type: str, 
        device_id: Optional[str], 
        limit: int = 5
    ) -> str:
        """Find similar past incidents with diagnosis"""
        try:
            with self.Session() as session:
                query_parts = [
                    "SELECT incident_number, incident_type, severity, primary_device,",
                    "       root_cause, correlation_confidence, created_at",
                    "FROM incidents",
                    "WHERE incident_type = :incident_type",
                    "  AND root_cause IS NOT NULL",
                    "  AND created_at < NOW() - INTERVAL '1 hour'",  # Exclude very recent
                ]
                
                params = {'incident_type': incident_type, 'limit': limit}
                
                if device_id:
                    query_parts.append("  AND primary_device = :device_id")
                    params['device_id'] = device_id
                
                query_parts.extend([
                    "ORDER BY created_at DESC",
                    "LIMIT :limit"
                ])
                
                query = text("\n".join(query_parts))
                result = session.execute(query, params)
                
                incidents = []
                for row in result:
                    confidence = row.correlation_confidence if row.correlation_confidence else 0.0
                    incidents.append(
                        f"- Incident #{row.incident_number}: {row.incident_type} on {row.primary_device} "
                        f"(confidence: {confidence:.2f})\n"
                        f"  Root cause: {row.root_cause[:200]}..."
                    )
                
                if incidents:
                    return f"Similar past {incident_type} incidents:\n" + "\n\n".join(incidents)
                else:
                    return f"No similar {incident_type} incidents found with diagnosis"
                    
        except Exception as e:
            logger.error(f"Error fetching similar incidents: {e}")
            return "Similar incidents unavailable"
    
    # ============================================================================
    # Week 2: Vector Search Methods
    # ============================================================================
    
    def _build_vector_search_query(self, incident: Dict[str, Any]) -> str:
        """Build a search query from incident details"""
        parts = []
        
        # Include incident type
        if incident.get('incident_type') and incident.get('incident_type') != 'UNKNOWN':
            parts.append(incident['incident_type'].replace('_', ' '))
        
        # Include description if available
        if incident.get('description'):
            parts.append(incident['description'])
        
        # Include primary device for context
        if incident.get('primary_device'):
            parts.append(f"device {incident['primary_device']}")
        
        # Include severity
        if incident.get('severity'):
            parts.append(incident['severity'])
        
        query = " ".join(parts)
        logger.debug(f"Built vector search query: {query}")
        return query
    
    def _get_vector_similar_incidents(
        self,
        query_text: str,
        incident_type: Optional[str] = None
    ) -> Optional[str]:
        """Find similar past incidents using vector similarity search"""
        if not self.vector_kb:
            return None
        
        try:
            # Search for similar incidents
            results = self.vector_kb.find_similar_incidents(
                query_text=query_text,
                top_k=config.VECTOR_SIMILAR_INCIDENTS_COUNT,
                min_similarity=config.VECTOR_MIN_SIMILARITY,
                incident_type=incident_type if incident_type and incident_type != 'UNKNOWN' else None
            )
            
            if not results:
                return None
            
            # Format results
            lines = [f"Vector Search - Similar Past Incidents ({len(results)} found):\n"]
            for i, result in enumerate(results, 1):
                metadata = result.get('metadata', {})
                relevance = result.get('relevance', 0.0)
                
                lines.append(
                    f"{i}. [{metadata.get('incident_type', 'UNKNOWN')}] "
                    f"Incident #{metadata.get('incident_number', 'N/A')}\n"
                    f"   Device: {metadata.get('primary_device', 'unknown')}, "
                    f"Severity: {metadata.get('severity', 'unknown')}\n"
                    f"   Root Cause: {metadata.get('root_cause', 'N/A')[:150]}\n"
                    f"   Relevance: {relevance:.3f}\n"
                )
            
            logger.info(f"Found {len(results)} similar incidents via vector search")
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Vector similar incidents search failed: {e}")
            return None
    
    def _get_vector_relevant_kb(
        self,
        query_text: str,
        incident_type: Optional[str] = None,
        device_id: Optional[str] = None
    ) -> Optional[str]:
        """Find relevant knowledge base articles using vector search"""
        if not self.vector_kb:
            return None
        
        try:
            # Determine vendor from device_id
            vendor = "generic"
            if device_id:
                if "cisco" in device_id.lower() or "cat" in device_id.lower():
                    vendor = "cisco"
                elif "juniper" in device_id.lower() or "mx" in device_id.lower() or "ex" in device_id.lower():
                    vendor = "juniper"
            
            # Search for relevant KB articles with smart fallback
            # Try with filters first, if no results, retry without filters for broader semantic match
            results = self.vector_kb.find_relevant_kb(
                query_text=query_text,
                event_type=incident_type if incident_type and incident_type != 'UNKNOWN' else None,
                vendor=vendor,
                top_k=config.VECTOR_KB_ARTICLES_COUNT
            )
            
            # Fallback: If no results with filters, try without filters for semantic matching
            if not results:
                logger.info(f"No KB articles found with filters, retrying with broader search")
                results = self.vector_kb.find_relevant_kb(
                    query_text=query_text,
                    event_type=None,
                    vendor=None,
                    top_k=config.VECTOR_KB_ARTICLES_COUNT
                )
            
            if not results:
                return None
            
            # Format results
            lines = [f"Knowledge Base Articles (Vector Search - {len(results)} found):\n"]
            for i, result in enumerate(results, 1):
                metadata = result.get('metadata', {})
                relevance = result.get('relevance', 0.0)
                content = result.get('content', '')
                
                # Extract key sections from content
                content_lines = content.split('\n')
                root_causes = []
                remediation = []
                
                in_root_causes = False
                in_remediation = False
                
                for line in content_lines:
                    if 'Root Causes' in line or 'Common Causes' in line:
                        in_root_causes = True
                        in_remediation = False
                        continue
                    elif 'Remediation' in line or 'Resolution' in line:
                        in_root_causes = False
                        in_remediation = True
                        continue
                    elif line.strip().startswith('#'):
                        in_root_causes = False
                        in_remediation = False
                        continue
                    
                    if in_root_causes and line.strip() and len(root_causes) < 3:
                        root_causes.append(line.strip())
                    elif in_remediation and line.strip() and len(remediation) < 3:
                        remediation.append(line.strip())
                
                lines.append(
                    f"{i}. **{metadata.get('title', 'Unknown')}** "
                    f"(Event: {metadata.get('event_type', 'N/A')}, "
                    f"Vendor: {metadata.get('vendor', 'generic')}, "
                    f"Success: {metadata.get('success_rate', 'N/A')}%)\n"
                    f"   Relevance: {relevance:.3f}\n"
                )
                
                # Log which KB article was retrieved
                kb_id = result.get('article_id', 'unknown')
                logger.info(f"  → KB Article {i}: {kb_id} - {metadata.get('title', 'Unknown')} (relevance: {relevance:.3f})")
                
                if root_causes:
                    lines.append(f"   Common Root Causes:")
                    for cause in root_causes[:2]:
                        lines.append(f"     • {cause}")
                
                if remediation:
                    lines.append(f"   Remediation Steps:")
                    for step in remediation[:2]:
                        lines.append(f"     • {step}")
                
                lines.append("")
            
            logger.info(f"Found {len(results)} relevant KB articles via vector search")
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Vector KB search failed: {e}")
            return None
