# Device Enrichment Service

**Service Name:** `smart-noc-device-enrichment`  
**Image:** `smart-noc_device-enrichment` (custom)  
**Technology:** Flask (Python 3.9)  
**Status:** Core Service  
**Uptime Target:** 99.9%

---

## Overview

The Device Enrichment Service provides **real-time device metadata lookup** for log enrichment. It acts as a high-performance caching layer between Logstash and the PostgreSQL device inventory database, using a **3-tier caching strategy** (Redis → LRU → PostgreSQL) to achieve sub-second response times.

**Key Capability:** Transforms device IPs into rich metadata (vendor, model, OS version, CLI syntax) required for vendor-specific AI diagnosis and remediation.

---

## Service Configuration

### Ports
- **8080 (internal):** Flask HTTP API
- **8081 (host):** Mapped external port

### Resources
- **Memory:** 256MB-512MB
- **CPU:** 0.5 cores
- **Storage:** None (stateless)

### Environment Variables
```
POSTGRES_HOST: postgres
POSTGRES_PORT: 5432
POSTGRES_DB: smart_noc
POSTGRES_USER: noc_admin
POSTGRES_PASSWORD: noc_password
REDIS_HOST: redis
REDIS_PORT: 6379
REDIS_DB: 0
REDIS_TTL: 3600  # 1 hour cache expiration
```

---

## Architecture Components

### 1. **HTTP API (Flask)**

#### **Endpoints**

**GET /device/<device_id>**
- **Purpose:** Retrieve device metadata by device ID or IP address
- **Input:** `device_id` (string) - device identifier (IP address or hostname)
- **Output:** JSON with device metadata
- **Cache:** 3-tier (Redis → LRU → PostgreSQL)
- **Response Time:** 58ms (cached) / 83ms (cold)

**Example Request:**
```http
GET /device/10.139.38.188 HTTP/1.1
Host: device-enrichment:8080
```

**Example Response (200 OK):**
```json
{
  "device_id": "10.139.38.188",
  "vendor": "Extreme Networks",
  "device_family": "EXOS",
  "model": "X690-48x (2-slot stack)",
  "os_version": "32.6.1.2",
  "cli_syntax": "EXOS",
  "device_role": "core",
  "management_ip": "10.139.38.188"
}
```

**Example Response (404 Not Found):**
```json
{
  "error": "Device not found",
  "device_id": "10.139.38.199"
}
```

---

**GET /health**
- **Purpose:** Health check endpoint for Docker/Kubernetes
- **Input:** None
- **Output:** JSON with service status
- **Response Time:** <10ms

**Example Response (200 OK):**
```json
{
  "status": "healthy",
  "database": "connected",
  "redis_cache": "connected"
}
```

**Example Response (503 Service Unavailable):**
```json
{
  "status": "unhealthy",
  "database": "disconnected",
  "redis_cache": "connected",
  "error": "PostgreSQL connection failed"
}
```

---

**GET /cache/info**
- **Purpose:** Cache statistics for monitoring
- **Input:** None
- **Output:** JSON with cache hit/miss metrics

**Example Response:**
```json
{
  "redis_hits": 103,
  "redis_misses": 17,
  "hit_rate": 0.86,
  "total_requests": 120,
  "cache_size_mb": 2.3
}
```

---

**POST /cache/clear**
- **Purpose:** Manual cache invalidation
- **Input:** Optional `device_id` to clear specific entry
- **Output:** Confirmation message
- **Use Case:** After device updates in database

**Example Request:**
```http
POST /cache/clear HTTP/1.1
Host: device-enrichment:8080
Content-Type: application/json

{
  "device_id": "10.139.38.188"
}
```

**Example Response:**
```json
{
  "status": "success",
  "cleared": ["10.139.38.188"],
  "message": "Cache cleared for 1 device(s)"
}
```

---

### 2. **3-Tier Caching Strategy**

#### **Tier 1: Redis Cache**

**Technology:** Redis 7.x  
**Purpose:** Distributed cache shared across multiple service instances  
**TTL:** 3600 seconds (1 hour)  
**Hit Rate:** 86% (production measured)

**Key Format:**
```
device:{device_id}
```

**Stored Value:**
```json
{
  "device_id": "10.139.38.188",
  "vendor": "Extreme Networks",
  "device_family": "EXOS",
  ...
}
```

**Operations:**
```python
# Cache hit
value = redis_client.get(f"device:{device_id}")

# Cache miss → fetch from DB → store in Redis
redis_client.setex(f"device:{device_id}", ttl=3600, value=json_data)
```

**Benefits:**
- Shared across multiple enrichment service instances
- Persistent across service restarts
- Network latency: ~1ms

---

#### **Tier 2: LRU In-Memory Cache**

**Technology:** Python `functools.lru_cache`  
**Purpose:** Process-local cache (fastest access)  
**Capacity:** 1000 devices (configurable)  
**Hit Rate:** 60-70% on top of Redis

**Implementation:**
```python
@lru_cache(maxsize=1000)
def get_device_from_db(device_id):
    # Query PostgreSQL
    return device_metadata
```

**Benefits:**
- Zero network latency (<1ms lookup)
- Automatic eviction (LRU policy)
- Thread-safe

**Limitation:**
- Not shared across service instances
- Lost on service restart

---

#### **Tier 3: PostgreSQL Database**

**Table:** `devices`  
**Purpose:** Source of truth for device inventory  
**Query Time:** 50-80ms (cold)

**Schema:**
```sql
CREATE TABLE devices (
    device_id VARCHAR(100) PRIMARY KEY,
    management_ip INET UNIQUE,
    vendor VARCHAR(100),
    device_family VARCHAR(100),
    model VARCHAR(200),
    os_version VARCHAR(50),
    cli_syntax VARCHAR(50),
    device_role VARCHAR(50),
    site VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Query Logic:**
```sql
SELECT device_id, vendor, device_family, model, os_version, cli_syntax, device_role
FROM devices
WHERE device_id = %s OR management_ip::text = %s
LIMIT 1;
```

**Note:** Queries by `device_id` OR `management_ip` to handle both identifiers

---

### 3. **Cache Performance**

**Request Flow:**

```
Client Request → Flask
                  ↓
           Check LRU Cache
                  ↓ (miss)
           Check Redis Cache
                  ↓ (miss)
           Query PostgreSQL
                  ↓
           Store in Redis
                  ↓
           Return to Flask
                  ↓
           Response to Client
```

**Measured Latencies:**
- **LRU Hit:** 0.5ms
- **Redis Hit:** 2ms (Redis lookup only)
- **PostgreSQL Cold:** 83ms (full query + caching)
- **Average (86% Redis hit rate):** 8ms

**Performance Improvement:**
- **Redis vs Cold:** 58ms / 83ms = **30% faster**
- **LRU vs Cold:** 0.5ms / 83ms = **99.4% faster**

---

## PostgreSQL Integration

### Connection Pool
**Library:** `psycopg2`  
**Pool Size:** 5-10 connections (configurable)  
**Timeout:** 10 seconds

**Configuration:**
```python
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'postgres'),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'database': os.getenv('POSTGRES_DB', 'smart_noc'),
    'user': os.getenv('POSTGRES_USER', 'noc_admin'),
    'password': os.getenv('POSTGRES_PASSWORD', 'noc_password')
}
```

### Error Handling
- **Connection Failure:** Retry 3 times with exponential backoff
- **Query Timeout:** Return 503 error after 10 seconds
- **Data Not Found:** Return 404 with error message

---

## Redis Integration

### Connection
**Library:** `redis-py`  
**Connection Type:** Single connection (thread-safe)  
**Timeout:** 3 seconds

**Configuration:**
```python
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'redis'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=int(os.getenv('REDIS_DB', 0)),
    decode_responses=True,
    socket_timeout=3
)
```

### Error Handling
- **Connection Failure:** Fall through to PostgreSQL (degraded mode)
- **Timeout:** Skip Redis, query database directly
- **Cache Poisoning:** TTL ensures stale data auto-expires

---

## Dependencies

### Upstream
- **Logstash:** Primary consumer (HTTP filter)
- **Manual Tools:** curl, Postman for testing

### Downstream
- **PostgreSQL:** `devices` table (read-only)
- **Redis:** Cache storage (read/write)

---

## Data Flow

```
Logstash → HTTP GET /device/{id} → Flask
                                      ↓
                                  LRU Cache?
                                  ↓ (miss)
                              Redis Cache?
                                  ↓ (miss)
                              PostgreSQL Query
                                  ↓
                              Cache in Redis
                                  ↓
                              Return JSON → Logstash
                                              ↓
                                        Enriched Log
```

---

## Performance Characteristics

### Throughput
- **Tested:** 500 requests/second (single instance)
- **Capacity:** 2,000 requests/second (with Redis)
- **Bottleneck:** PostgreSQL connections (10 max)

### Latency (Production Measured)
- **P50:** 2ms (Redis hit)
- **P95:** 60ms (PostgreSQL cold)
- **P99:** 85ms (slow queries)

### Cache Efficiency
- **Redis Hit Rate:** 86%
- **LRU Hit Rate:** 60% (of Redis misses)
- **Database Queries:** ~8% of total requests

---

## Monitoring & Health

### Health Check
**Docker Healthcheck:**
```yaml
healthcheck:
  test: ["CMD-SHELL", "python -c 'import requests; requests.get(\"http://localhost:8080/health\", timeout=3)' || exit 1"]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 10s
```

**Expected Output:**
```json
{"status": "healthy", "database": "connected", "redis_cache": "connected"}
```

### Metrics Endpoints
```bash
# Cache statistics
curl http://localhost:8081/cache/info

# Health status
curl http://localhost:8081/health
```

### Logs
```bash
docker logs smart-noc-device-enrichment --tail 100
```

**Normal Output:**
```
2026-06-13 22:51:55 | INFO | → Request: GET /device/10.139.38.188
2026-06-13 22:51:55 | INFO | ✓ Device found in Redis cache: 10.139.38.188
2026-06-13 22:51:55 | INFO | ← Response: 200 OK - Extreme Networks EXOS
```

**Error Indicators:**
```
| ERROR | PostgreSQL connection failed
| WARNING | Redis unavailable, using database only
| ERROR | Device not found: 10.139.38.199
```

---

## Troubleshooting

### Issue: All Requests Slow (>80ms)

**Symptoms:**
- Every request takes 80+ ms
- Redis hit rate = 0%

**Diagnosis:**
```bash
# Check Redis connectivity
docker exec smart-noc-device-enrichment redis-cli -h redis PING

# Check Redis keys
docker exec smart-noc-redis redis-cli KEYS "device:*"
```

**Resolution:**
1. Verify Redis service is running
2. Check Redis password/config
3. Clear and rebuild cache: `curl -X POST http://localhost:8081/cache/clear`

---

### Issue: 404 Errors for Existing Devices

**Symptoms:**
- Known devices returning 404
- Database has the device

**Diagnosis:**
```bash
# Check PostgreSQL connectivity
docker exec smart-noc-device-enrichment psql -h postgres -U noc_admin -d smart_noc -c "SELECT COUNT(*) FROM devices;"

# Query specific device
docker exec smart-noc-postgres psql -U noc_admin -d smart_noc -c "SELECT * FROM devices WHERE device_id='10.139.38.188';"
```

**Resolution:**
1. Verify device exists in database
2. Check device_id format matches query
3. Clear cache and retry

---

### Issue: Memory Leak

**Symptoms:**
- Memory usage grows over time
- Container OOM (Out of Memory) killed

**Diagnosis:**
```bash
# Check memory usage
docker stats smart-noc-device-enrichment

# Check cache size
curl http://localhost:8081/cache/info
```

**Resolution:**
1. Reduce LRU cache size: `maxsize=500`
2. Lower Redis TTL: `TTL=1800` (30 min)
3. Restart service periodically

---

## Scaling Considerations

### Horizontal Scaling
- Deploy multiple instances behind load balancer
- Redis ensures cache coherency across instances
- Database connection pool shared via PgBouncer

### Vertical Scaling
- Increase memory for larger LRU cache
- Not CPU-intensive (I/O bound)

### Optimization
- Database query optimization (indexes on `device_id`, `management_ip`)
- Redis clustering for massive scale (10K+ devices)
- Read replicas for PostgreSQL

---

## Security

### Network
- Internal service (not exposed externally)
- Firewall port 8080 to only Logstash subnet

### Data
- Database credentials via environment variables (not hardcoded)
- Redis requires AUTH (password protected)

### Access Control
- No authentication on API (internal use only)
- Future: API key for external integrations

---

## Deployment

### Docker Compose
```yaml
device-enrichment:
  build: ./services/device-enrichment
  ports:
    - "8081:8080"
  environment:
    POSTGRES_HOST: postgres
    REDIS_HOST: redis
    REDIS_TTL: 3600
  depends_on:
    postgres:
      condition: service_healthy
    redis:
      condition: service_started
  healthcheck:
    test: ["CMD-SHELL", "python -c 'import requests; requests.get(\"http://localhost:8080/health\", timeout=3)'"]
    interval: 30s
```

### Dependencies
```
Flask==3.0.0
psycopg2-binary==2.9.9
redis==5.0.1
requests==2.31.0  # For healthcheck
```

---

## Related Documentation

- [Logstash Service](01-logstash.md)
- [PostgreSQL Schema](08-postgres.md)
- [Redis Cache](09-redis.md)
- [Complete Architecture](../02-architecture/COMPLETE_ARCHITECTURE.md)
