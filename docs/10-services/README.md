# Smart NOC Services Documentation

This directory contains comprehensive documentation for all Smart NOC services. Each service document includes architecture details, configuration, data models, performance characteristics, and troubleshooting guides.

---

## Service Documentation Index

### Core Processing Services

1. **[Logstash](01-logstash.md)** - Syslog ingestion, parsing, and enrichment
   - Ports: 5000 (UDP/TCP), 9600 (monitoring)
   - Grok patterns for RFC3164, RFC5424, Extreme Networks
   - HTTP enrichment integration
   - Event type detection and interface extraction

2. **[Device Enrichment](02-device-enrichment.md)** - Device metadata lookup service
   - Port: 8081 (HTTP API)
   - 3-tier caching: Redis → LRU → PostgreSQL
   - 86% cache hit rate, 58ms avg response
   - REST endpoints: `/device/<id>`, `/health`, `/cache/info`

3. **[Anomaly Detector](03-anomaly-detector.md)** - Real-time anomaly detection
   - Rule-based patterns (flapping, auth, BGP)
   - ML-based detection (Isolation Forest)
   - Enrichment field propagation
   - Publishes to Kafka `anomalies` topic

4. **[Correlation Engine](04-correlation-engine.md)** - Incident creation from anomalies
   - Temporal-spatial correlation algorithms
   - Multi-anomaly grouping (5-minute window)
   - Severity calculation and deduplication
   - Publishes to Kafka `incidents` topic

5. **[LLM Diagnosis](05-llm-diagnosis.md)** - AI-powered root cause analysis
   - Groq Mixtral-8x7B integration
   - ChromaDB vector similarity search
   - Vendor-specific command generation
   - Command validation and safety checks

6. **[Remediation Agent](06-remediation-agent.md)** - Command execution service
   - Current: Simulation mode (logs only)
   - Future: SSH/NETCONF device connector
   - Multi-layer safety framework
   - Audit trail in PostgreSQL

### Infrastructure Services

7. **[Kafka](07-kafka.md)** - Event streaming backbone
   - Ports: 9092-9093
   - Topics: `network-logs`, `anomalies`, `incidents`, `incidents-diagnosed`
   - 10K+ messages/second throughput
   - Consumer group monitoring and lag tracking

8. **[PostgreSQL](08-postgres.md)** - Persistent data store
   - Port: 5432
   - Tables: `devices`, `incidents`, `incident_anomalies`, `anomalies`, etc.
   - 50-500GB storage
   - Indexed for performance

9. **[Redis](09-redis.md)** - High-speed caching layer
   - Port: 6380 (host), 6379 (internal)
   - 86% cache hit rate
   - LRU eviction policy
   - 512MB-1GB memory

10. **[ChromaDB](10-chromadb.md)** - Vector knowledge base
    - Port: 8000 (HTTP API)
    - Collection: `kb_articles` (23-100+ documents)
    - Embedding: all-MiniLM-L6-v2 (384 dimensions)
    - Cosine similarity search

---

## Quick Reference

### Service Ports

| Service | Port(s) | Protocol | Access |
|---------|---------|----------|--------|
| Logstash | 5000, 9600 | UDP/TCP, HTTP | External (devices), Internal |
| Device Enrichment | 8081 | HTTP | Internal |
| Kafka | 9092-9093 | TCP | Internal |
| PostgreSQL | 5432 | TCP | Internal |
| Redis | 6380 | TCP | Internal |
| ChromaDB | 8000 | HTTP | Internal |
| Grafana | 3000 | HTTP | External (operators) |
| Kafka UI | 8080 | HTTP | External (operators) |

### Data Flow

```
Network Devices → Logstash (5000)
                      ↓
              Device Enrichment (8081)
                      ↓
              Kafka (network-logs)
                      ↓
              Anomaly Detector
                      ↓
              Kafka (anomalies)
                      ↓
              Correlation Engine
                      ↓
              Kafka (incidents)
                      ↓
              LLM Diagnosis (+ ChromaDB 8000)
                      ↓
              Kafka (incidents-diagnosed)
                      ↓
              Remediation Agent
```

### Health Checks

```bash
# Check all services
docker ps --format "table {{.Names}}\t{{.Status}}"

# Test Logstash
echo "<189>Test message" | nc -u localhost 5000

# Test Device Enrichment
curl http://localhost:8081/health

# Test Kafka topics
docker exec smart-noc-kafka kafka-topics.sh --list --bootstrap-server localhost:9092

# Test PostgreSQL
docker exec smart-noc-postgres pg_isready -U noc_admin

# Test Redis
docker exec smart-noc-redis redis-cli PING

# Test ChromaDB
curl http://localhost:8000/api/v1/heartbeat
```

### Common Issues & Solutions

| Issue | Service | Solution Document |
|-------|---------|------------------|
| Messages not enriched | Device Enrichment | [02-device-enrichment.md#troubleshooting](02-device-enrichment.md#troubleshooting) |
| No anomalies detected | Anomaly Detector | [03-anomaly-detector.md#troubleshooting](03-anomaly-detector.md#troubleshooting) |
| No incidents created | Correlation Engine | [04-correlation-engine.md#troubleshooting](04-correlation-engine.md#troubleshooting) |
| LLM generic commands | LLM Diagnosis | [05-llm-diagnosis.md#troubleshooting](05-llm-diagnosis.md#troubleshooting) |
| Consumer lag | Kafka | [07-kafka.md#troubleshooting](07-kafka.md#troubleshooting) |
| Cache misses | Redis | [09-redis.md#troubleshooting](09-redis.md#troubleshooting) |

---

## Architecture Overview

For a complete understanding of how all services work together, see:
- **[Complete Architecture Document](../02-architecture/COMPLETE_ARCHITECTURE.md)**

This master document includes:
- System overview and business value
- Comprehensive architecture diagrams
- End-to-end data flow
- Performance characteristics
- Scalability and resilience
- Security architecture
- Deployment guide
- Future roadmap

---

## Getting Started

### Read Services in Order

**For New Team Members:**
1. Start with [Complete Architecture](../02-architecture/COMPLETE_ARCHITECTURE.md) for big picture
2. Follow data flow: Logstash → Device Enrichment → Anomaly Detector → Correlation → LLM → Remediation
3. Deep dive into services you'll work on

**For Operators:**
- Focus on [Kafka](07-kafka.md), [PostgreSQL](08-postgres.md), [Redis](09-redis.md)
- Learn health checks and monitoring
- Understand troubleshooting procedures

**For Developers:**
- Read all core processing services (01-06)
- Understand Kafka message schemas
- Review data models in PostgreSQL

---

## Document Conventions

Each service document follows this structure:
1. **Overview:** Purpose and capabilities
2. **Configuration:** Ports, resources, environment variables
3. **Architecture Components:** Detailed breakdown of functionality
4. **Dependencies:** Upstream and downstream services
5. **Data Flow:** How data moves through the service
6. **Performance Characteristics:** Throughput, latency, resources
7. **Monitoring & Health:** Health checks, logs, metrics
8. **Troubleshooting:** Common issues and resolutions
9. **Related Documentation:** Links to other relevant docs

---

## Contributing

When updating service documentation:
1. Keep diagrams and code examples up to date
2. Add troubleshooting sections for new issues
3. Update performance metrics after optimizations
4. Link to related documentation
5. Maintain consistent formatting

---

**Last Updated:** June 15, 2026  
**Maintainer:** Smart NOC Team
