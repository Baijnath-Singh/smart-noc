#!/usr/bin/env python3
"""
Device Enrichment Service
Simple Flask API that provides device metadata for log enrichment
Uses Redis cache -> LRU cache -> PostgreSQL (3-tier caching)
"""
import os
import json
import logging
from flask import Flask, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
from functools import lru_cache
import redis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'postgres'),
    'port': os.getenv('POSTGRES_PORT', '5432'),
    'database': os.getenv('POSTGRES_DB', 'smart_noc'),
    'user': os.getenv('POSTGRES_USER', 'noc_admin'),
    'password': os.getenv('POSTGRES_PASSWORD', 'noc_password')
}

# Redis configuration
REDIS_CONFIG = {
    'host': os.getenv('REDIS_HOST', 'redis'),
    'port': int(os.getenv('REDIS_PORT', '6379')),
    'db': int(os.getenv('REDIS_DB', '0')),
    'decode_responses': True
}

# Cache TTL (Time To Live)
REDIS_TTL = int(os.getenv('REDIS_TTL', '3600'))  # 1 hour default

# Initialize Redis connection
try:
    redis_client = redis.Redis(**REDIS_CONFIG)
    redis_client.ping()
    logger.info(f"✓ Connected to Redis at {REDIS_CONFIG['host']}:{REDIS_CONFIG['port']}")
except Exception as e:
    logger.warning(f"⚠ Redis connection failed, will use LRU cache only: {e}")
    redis_client = None


def get_db_connection():
    """Create database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise


@lru_cache(maxsize=1000)
def get_device_from_db(device_id):
    """
    Query device information from database (Layer 3: Database)
    Uses LRU cache to reduce database queries (cache 1000 devices)
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Query by device_id or management_ip
        cur.execute("""
            SELECT 
                device_id,
                vendor,
                device_family,
                model,
                os_version,
                cli_syntax,
                device_role
            FROM devices 
            WHERE device_id = %s OR management_ip::text = %s
            LIMIT 1
        """, (device_id, device_id))
        
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        if result:
            return dict(result)
        else:
            return None
            
    except Exception as e:
        logger.error(f"Database query error for {device_id}: {e}")
        return None


def get_device_with_cache(device_id):
    """
    Get device information with 3-tier caching:
    1. Redis cache (fastest, ~1ms)
    2. LRU cache (fast, in-memory)
    3. PostgreSQL database (slowest, ~20ms)
    """
    cache_key = f"device:{device_id}"
    
    # Layer 1: Try Redis cache
    if redis_client:
        try:
            cached = redis_client.get(cache_key)
            if cached:
                logger.info(f"✓ Device found in Redis cache: {device_id}")
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Redis cache read error: {e}")
    
    # Layer 2 & 3: LRU cache -> Database
    device_info = get_device_from_db(device_id)
    
    if device_info:
        logger.info(f"✓ Device found: {device_id} -> {device_info['vendor']} {device_info['device_family']}")
        
        # Store in Redis for next time
        if redis_client:
            try:
                redis_client.setex(
                    cache_key,
                    REDIS_TTL,
                    json.dumps(device_info)
                )
            except Exception as e:
                logger.warning(f"Redis cache write error: {e}")
        
        return device_info
    else:
        logger.warning(f"✗ Device not found: {device_id}")
        return None


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        conn = get_db_connection()
        conn.close()
        db_status = "connected"
    except:
        db_status = "disconnected"
    
    # Check Redis
    redis_status = "disconnected"
    if redis_client:
        try:
            redis_client.ping()
            redis_status = "connected"
        except:
            redis_status = "error"
    
    overall_status = "healthy" if db_status == "connected" else "unhealthy"
    
    return jsonify({
        "status": overall_status,
        "database": db_status,
        "redis_cache": redis_status
    }), 200 if overall_status == "healthy" else 503


@app.route('/device/<device_id>', methods=['GET'])
def get_device(device_id):
    """
    Get device information by device_id or IP address
    Uses 3-tier caching for optimal performance
    
    Example:
        GET /device/10.139.38.188
        
    Returns:
        {
            "device_id": "10.139.38.188",
            "vendor": "Extreme Networks",
            "device_family": "EXOS",
            "model": "X690-48x (2-slot stack)",
            "os_version": "32.6.1.2",
            "cli_syntax": "EXOS",
            "device_role": "core"
        }
    """
    logger.info(f"→ Request: GET /device/{device_id}")
    
    device_info = get_device_with_cache(device_id)
    
    if device_info:
        logger.info(f"← Response: 200 OK - {device_info['vendor']} {device_info['device_family']}")
        return jsonify(device_info), 200
    else:
        logger.warning(f"← Response: 404 Not Found - {device_id}")
        return jsonify({
            "error": "Device not found",
            "device_id": device_id,
            "message": f"No device information available for {device_id}"
        }), 404


@app.route('/cache/clear', methods=['POST'])
def clear_cache():
    """Clear all caches (Redis + LRU)"""
    cleared = []
    
    # Clear LRU cache
    get_device_from_db.cache_clear()
    cleared.append("LRU cache")
    
    # Clear Redis cache
    if redis_client:
        try:
            # Clear all device keys
            keys = redis_client.keys("device:*")
            if keys:
                redis_client.delete(*keys)
                cleared.append(f"Redis cache ({len(keys)} keys)")
            else:
                cleared.append("Redis cache (0 keys)")
        except Exception as e:
            logger.error(f"Redis cache clear error: {e}")
    
    logger.info(f"Caches cleared: {', '.join(cleared)}")
    return jsonify({
        "message": "Caches cleared successfully",
        "cleared": cleared
    }), 200


@app.route('/cache/info', methods=['GET'])
def cache_info():
    """Get cache statistics for all cache layers"""
    lru_info = get_device_from_db.cache_info()
    
    result = {
        "lru_cache": {
            "hits": lru_info.hits,
            "misses": lru_info.misses,
            "maxsize": lru_info.maxsize,
            "currsize": lru_info.currsize,
            "hit_rate": f"{lru_info.hits / (lru_info.hits + lru_info.misses) * 100:.2f}%" if (lru_info.hits + lru_info.misses) > 0 else "N/A"
        }
    }
    
    # Redis cache info
    if redis_client:
        try:
            redis_info = redis_client.info('stats')
            redis_keys = len(redis_client.keys("device:*"))
            result["redis_cache"] = {
                "status": "connected",
                "cached_devices": redis_keys,
                "ttl_seconds": REDIS_TTL,
                "keyspace_hits": redis_info.get('keyspace_hits', 0),
                "keyspace_misses": redis_info.get('keyspace_misses', 0)
            }
        except Exception as e:
            result["redis_cache"] = {
                "status": "error",
                "error": str(e)
            }
    else:
        result["redis_cache"] = {
            "status": "disconnected"
        }
    
    return jsonify(result), 200


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("Device Enrichment Service Starting")
    logger.info("=" * 60)
    logger.info(f"Database: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    logger.info(f"Redis Cache: {REDIS_CONFIG['host']}:{REDIS_CONFIG['port']} (TTL: {REDIS_TTL}s)")
    logger.info(f"LRU Cache: 1000 devices (in-memory)")
    logger.info("Caching Strategy: Redis -> LRU -> PostgreSQL (3-tier)")
    logger.info("Endpoints:")
    logger.info("  GET  /device/<device_id>  - Get device information")
    logger.info("  GET  /health              - Health check")
    logger.info("  GET  /cache/info          - Cache statistics")
    logger.info("  POST /cache/clear         - Clear cache")
    logger.info("=" * 60)
    
    # Run Flask app
    app.run(
        host='0.0.0.0',
        port=8080,
        debug=False
    )
