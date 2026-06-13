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
            'remediation_lessons': None,  # Phase 1: Remediation lessons
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
            # Phase 1 & 2: Get remediation lessons (SQL or ChromaDB based on config)
            if config.REMEDIATION_LESSONS_SOURCE == 'chromadb' and self.vector_kb:
                # Phase 2: Use ChromaDB semantic search
                search_query = self._build_vector_search_query(incident)
                context['remediation_lessons'] = self._get_remediation_lessons_chromadb(
                    search_query,
                    incident_type,
                    limit=config.REMEDIATION_LESSONS_COUNT
                )
            else:
                # Phase 1: Use SQL exact-match query
                context['remediation_lessons'] = self._get_remediation_lessons(
                    incident_type,
                    limit=3
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
                
                # Find relevant KB articles (pass anomalies for event_type extraction)
                context['vector_kb_articles'] = self._get_vector_relevant_kb(
                    search_query,
                    incident_type,
                    primary_device,
                    context['anomalies']  # Pass anomalies for better event_type matching
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
    
    def _get_remediation_lessons(
        self, 
        incident_type: str, 
        limit: int = 3
    ) -> str:
        """Get lessons learned from past successful remediations (Phase 1)"""
        try:
            with self.Session() as session:
                query = text("""
                    SELECT 
                        i.incident_number,
                        i.primary_device,
                        r.success,
                        r.actions_taken,
                        r.resolution_time_seconds,
                        r.final_phase,
                        r.lessons_learned,
                        r.executed_at
                    FROM remediation_executions r
                    JOIN incidents i ON r.incident_id = i.id
                    WHERE i.incident_type = :incident_type
                      AND r.lessons_learned IS NOT NULL
                      AND r.lessons_learned != ''
                    ORDER BY r.executed_at DESC
                    LIMIT :limit
                """)
                
                result = session.execute(
                    query, 
                    {'incident_type': incident_type, 'limit': limit}
                )
                
                lessons = []
                for row in result:
                    outcome = "✅ SUCCESS" if row.success else "❌ FAILED"
                    time_str = f"{row.resolution_time_seconds:.1f}s" if row.resolution_time_seconds else "N/A"
                    
                    lessons.append(
                        f"- Incident #{row.incident_number} ({row.primary_device}): {outcome}\n"
                        f"  Phase: {row.final_phase}, Actions: {row.actions_taken}, Time: {time_str}\n"
                        f"  Lesson: {row.lessons_learned}"
                    )
                
                if lessons:
                    return f"Past remediation results for {incident_type}:\n" + "\n\n".join(lessons)
                else:
                    return f"No remediation history available for {incident_type} yet"
                    
        except Exception as e:
            logger.error(f"Error fetching remediation lessons: {e}")
            return "Remediation history unavailable"
    
    def _get_remediation_lessons_chromadb(
        self, 
        search_query: str,
        incident_type: str,
        limit: int = 5
    ) -> str:
        """Get lessons learned via ChromaDB semantic search (Phase 2)"""
        try:
            if not self.vector_kb:
                return "ChromaDB not available, falling back to SQL"
            
            # Enhance query with incident type for better semantic matching
            enhanced_query = f"{incident_type} {search_query}"
            
            # Generate query embedding
            query_embedding = self.vector_kb.model.encode(enhanced_query).tolist()
            
            # Search remediation_commands collection
            results = self.vector_kb.commands.query(
                query_embeddings=[query_embedding],
                n_results=limit
            )
            
            lessons = []
            if results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    distance = results['distances'][0][i]
                    similarity = 1 - distance  # Convert distance to similarity
                    
                    # Filter by minimum similarity threshold
                    if similarity < config.REMEDIATION_LESSONS_MIN_SIMILARITY:
                        continue
                    
                    doc_text = results['documents'][0][i]
                    metadata = results['metadatas'][0][i]
                    
                    # Format lesson with similarity score
                    lessons.append(
                        f"- Incident #{metadata.get('incident_number', 'N/A')} "
                        f"({metadata.get('device', 'unknown')}) "
                        f"[similarity: {similarity:.2f}]\n"
                        f"  Type: {metadata.get('incident_type', 'UNKNOWN')}, "
                        f"Actions: {metadata.get('actions_count', 0)}, "
                        f"Time: {metadata.get('resolution_time_seconds', 0):.1f}s\n"
                        f"  {doc_text}"
                    )
            
            if lessons:
                return (
                    f"Past remediation results (semantic search, threshold: {config.REMEDIATION_LESSONS_MIN_SIMILARITY}):\\n"
                    + "\\n\\n".join(lessons)
                )
            else:
                return f"No similar remediation history found (tried semantic search with threshold {config.REMEDIATION_LESSONS_MIN_SIMILARITY})"
                
        except Exception as e:
            logger.error(f"Error in ChromaDB remediation search: {e}")
            # Fallback to SQL
            return self._get_remediation_lessons(incident_type, limit=3)
    
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
        """
        Find similar past incidents and format them as few-shot examples
        
        This replaces static few-shot examples with dynamic, relevant examples
        from actual past diagnoses.
        """
        if not self.vector_kb:
            return None
        
        try:
            # Search for similar incidents (get top 2-3 for few-shot)
            results = self.vector_kb.find_similar_incidents(
                query_text=query_text,
                top_k=min(config.VECTOR_SIMILAR_INCIDENTS_COUNT, 3),  # Limit to 2-3 for few-shot
                min_similarity=config.VECTOR_MIN_SIMILARITY,
                incident_type=incident_type if incident_type and incident_type != 'UNKNOWN' else None
            )
            
            if not results or len(results) == 0:
                logger.info("No similar incidents found for few-shot examples")
                return None
            
            # Fetch full diagnosis details from database for selected incidents
            few_shot_examples = []
            
            for result in results[:2]:  # Use top 2 as few-shot examples
                metadata = result.get('metadata', {})
                incident_number = metadata.get('incident_number')
                
                if not incident_number:
                    continue
                
                # Fetch full incident data from database
                try:
                    from sqlalchemy import text
                    query = text("""
                        SELECT 
                            incident_number,
                            incident_type,
                            primary_device,
                            affected_devices,
                            severity,
                            root_cause,
                            remediation_plan
                        FROM incidents
                        WHERE incident_number = :incident_number
                        AND root_cause IS NOT NULL
                        AND remediation_plan IS NOT NULL
                    """)
                    
                    # Use connection context for SQLAlchemy 2.0 compatibility
                    with self.engine.connect() as conn:
                        result_proxy = conn.execute(query, {"incident_number": incident_number})
                        incident_data = result_proxy.fetchone()
                    
                    if incident_data:
                        # Parse remediation plan (it's stored as TEXT JSON)
                        import json
                        try:
                            remediation_plan = json.loads(incident_data[6]) if incident_data[6] else []
                        except:
                            remediation_plan = []
                        
                        # Format as few-shot example
                        example = self._format_as_few_shot_example(
                            incident_number=incident_data[0],
                            incident_type=incident_data[1],
                            primary_device=incident_data[2],
                            affected_devices=incident_data[3],
                            severity=incident_data[4],
                            root_cause=incident_data[5],
                            remediation_plan=remediation_plan,
                            relevance=result.get('relevance', 0.0)
                        )
                        
                        few_shot_examples.append(example)
                        
                except Exception as e:
                    logger.warning(f"Failed to fetch incident #{incident_number} details: {e}")
                    continue
            
            if not few_shot_examples:
                logger.info("No complete diagnoses found for few-shot examples")
                return None
            
            # Format as few-shot learning section
            header = f"\n**Few-Shot Examples (from {len(few_shot_examples)} similar past incidents):**\n\n"
            formatted_examples = header + "\n\n".join(few_shot_examples)
            
            logger.info(f"Generated {len(few_shot_examples)} dynamic few-shot examples from similar incidents")
            return formatted_examples
            
        except Exception as e:
            logger.error(f"Vector similar incidents search failed: {e}")
            return None
    
    def _format_as_few_shot_example(
        self,
        incident_number: int,
        incident_type: str,
        primary_device: str,
        affected_devices: list,
        severity: str,
        root_cause: str,
        remediation_plan: list,
        relevance: float
    ) -> str:
        """Format an incident as a few-shot example"""
        import json
        
        # Build concise input description
        devices_str = ', '.join(affected_devices) if isinstance(affected_devices, list) else str(affected_devices)
        
        input_desc = f"Incident Type: {incident_type}, Devices: {devices_str}, Severity: {severity}"
        
        # Build output JSON (truncate long plans to save tokens)
        output_json = {
            "root_cause": root_cause[:200] if root_cause else "Unknown",  # Truncate long root causes
            "remediation_plan": remediation_plan[:3] if remediation_plan else []  # Keep first 3 steps
        }
        
        # Format as example
        example = f"""EXAMPLE (Incident #{incident_number}, relevance: {relevance:.2f}):
Input: {input_desc}

Output:
```json
{json.dumps(output_json, indent=2)}
```"""
        
        return example
    
    def _get_vector_relevant_kb(
        self,
        query_text: str,
        incident_type: Optional[str] = None,
        device_id: Optional[str] = None,
        anomalies: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[str]:
        """Find relevant knowledge base articles using vector search"""
        if not self.vector_kb:
            return None
        
        try:
            # Extract actual event_type from anomalies for more precise KB matching
            event_type_for_search = None
            if anomalies:
                # Count occurrences of each event type
                from collections import Counter
                event_type_counts = Counter()
                for anomaly in anomalies:
                    anomaly_data = anomaly.get('anomaly_data', {})
                    event_type = anomaly_data.get('event_type')
                    if event_type:
                        event_type_counts[event_type] += 1
                
                if event_type_counts:
                    # Prioritize specific event types over generic ones
                    # Generic types to deprioritize
                    generic_types = {'CONFIG_MISMATCH', 'UNKNOWN', 'ML_DETECTED_ANOMALY'}
                    
                    # Filter out generic types if we have specific ones
                    specific_types = {et: count for et, count in event_type_counts.items() 
                                     if et not in generic_types}
                    
                    if specific_types:
                        # Use the most common specific event type
                        event_type_for_search = max(specific_types.items(), key=lambda x: x[1])[0]
                        logger.info(f"Extracted event_type from anomalies: {event_type_for_search} "
                                   f"(count: {specific_types[event_type_for_search]}, "
                                   f"all types: {dict(event_type_counts)})")
                    else:
                        # Fall back to most common generic type
                        event_type_for_search = event_type_counts.most_common(1)[0][0]
                        logger.info(f"Using generic event_type: {event_type_for_search} "
                                   f"(all types: {dict(event_type_counts)})")
            
            # Fallback to incident_type if no event_type found in anomalies
            if not event_type_for_search:
                event_type_for_search = incident_type if incident_type and incident_type != 'UNKNOWN' else None
            
            # Enhanced vendor and platform detection
            # PRIORITY 1: Use device info from enriched log messages (from device inventory)
            vendor = "generic"
            platform = None
            device_model = None
            device_os = None
            cli_syntax = None
            
            # Check if anomalies have device info from database enrichment
            if anomalies:
                first_anomaly = anomalies[0]
                if 'device_vendor' in first_anomaly:
                    vendor_full = first_anomaly.get('device_vendor', '').lower()
                    vendor = vendor_full.split()[0] if vendor_full else "generic"  # "Extreme Networks" -> "extreme"
                    platform = first_anomaly.get('device_family', '').lower()
                    device_model = first_anomaly.get('device_model')
                    device_os = first_anomaly.get('device_os_version')
                    cli_syntax = first_anomaly.get('device_cli_syntax', '').upper()
                    logger.info(f"Using device inventory data - Vendor: {vendor}, Platform: {platform}, "
                               f"Model: {device_model}, OS: {device_os}, CLI: {cli_syntax}")
            
            # PRIORITY 2: Fallback to heuristic detection from device_id/hostname
            if vendor == "generic" and device_id:
                device_lower = device_id.lower()
                logger.info(f"Device inventory not found, using heuristic detection for: {device_id}")
                
                # Extreme Networks detection
                if any(x in device_lower for x in ["exos", "extreme", "summit", "x460", "x670", "x440"]):
                    vendor = "extreme"
                    platform = "exos"
                elif any(x in device_lower for x in ["voss", "vsp", "fabric"]):
                    vendor = "extreme"
                    platform = "voss"
                
                # Cisco detection
                elif any(x in device_lower for x in ["cisco", "cat", "nexus", "catalyst"]):
                    vendor = "cisco"
                    if "nexus" in device_lower:
                        platform = "nxos"
                    else:
                        platform = "ios"
                
                # Juniper detection
                elif any(x in device_lower for x in ["juniper", "mx", "ex", "qfx", "srx"]):
                    vendor = "juniper"
                    platform = "junos"
                
                # HP/Aruba detection
                elif any(x in device_lower for x in ["aruba", "procurve", "hp"]):
                    vendor = "hp"
                    platform = "aruba"
            
            logger.info(f"Final device context - Vendor: {vendor}, Platform: {platform} from device: {device_id}")
            
            # Search for relevant KB articles with enhanced multi-query search
            # Try with filters first, if no results, retry without filters for broader semantic match
            results = self.vector_kb.find_relevant_kb(
                query_text=query_text,
                event_type=event_type_for_search,  # Use actual event_type from anomalies
                vendor=vendor,
                platform=platform,
                top_k=config.VECTOR_KB_ARTICLES_COUNT,
                use_multi_query=True,  # Enable enhanced search
                min_relevance=0.50  # Minimum relevance threshold
            )
            
            # Fallback: If no results with filters, try without filters for semantic matching
            if not results:
                logger.info(f"No KB articles found with filters, retrying with broader search")
                results = self.vector_kb.find_relevant_kb(
                    query_text=query_text,
                    event_type=None,
                    vendor=None,
                    platform=None,
                    top_k=config.VECTOR_KB_ARTICLES_COUNT,
                    use_multi_query=True,
                    min_relevance=0.40  # Lower threshold for fallback
                )
            
            if not results:
                return None
            
            # Format results with enhanced metrics
            lines = [f"Knowledge Base Articles (Enhanced Multi-Query Search - {len(results)} found):\n"]
            for i, result in enumerate(results, 1):
                metadata = result.get('metadata', {})
                relevance = result.get('relevance', 0.0)
                matched_queries = result.get('matched_queries', 1)
                query_types = result.get('query_types', [])
                content = result.get('text', '')  # Note: 'text' not 'content' from vector_service
                
                # Build vendor/platform string
                vendor_str = metadata.get('vendor', 'generic')
                platform = metadata.get('platform')
                if platform:
                    vendor_str = f"{vendor_str}/{platform}"
                
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
                    elif 'Remediation' in line or 'Resolution' in line or 'Quick Fix' in line:
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
                
                # Format article header with enhanced metrics
                lines.append(
                    f"{i}. **{metadata.get('title', 'Unknown')}** "
                    f"(Event: {metadata.get('event_type', 'N/A')}, "
                    f"Vendor: {vendor_str}, "
                    f"Success: {metadata.get('success_rate', 'N/A')})\n"
                    f"   Relevance: {relevance:.3f} "
                )
                
                # Add multi-query metrics if available
                if matched_queries > 1:
                    lines[-1] += f"(matched {matched_queries} queries)"
                lines[-1] += "\n"
                
                # Log which KB article was retrieved with enhanced info
                kb_id = result.get('article_id', 'unknown')
                logger.info(f"  → KB Article {i}: {kb_id} - {metadata.get('title', 'Unknown')} "
                           f"(relevance: {relevance:.3f}, queries: {matched_queries})")
                
                if root_causes:
                    lines.append(f"   Common Root Causes:")
                    for cause in root_causes[:2]:
                        lines.append(f"     • {cause}")
                
                if remediation:
                    lines.append(f"   Remediation Steps:")
                    for step in remediation[:2]:
                        lines.append(f"     • {step}")
                
                lines.append("")
            
            logger.info(f"Found {len(results)} relevant KB articles via enhanced multi-query vector search")
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Vector KB search failed: {e}")
            return None
