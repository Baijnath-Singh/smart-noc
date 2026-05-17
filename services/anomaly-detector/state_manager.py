"""
State Manager - Redis-based sliding window management

Maintains temporal state for anomaly detection (e.g., event counts in time windows).
"""

import redis
import json
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from loguru import logger


class StateManager:
    """Manages state using Redis for sliding window operations"""
    
    def __init__(self, redis_host='redis', redis_port=6379, redis_db=0):
        """Initialize Redis connection"""
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True
        )
        logger.info(f"Connected to Redis at {redis_host}:{redis_port}")
    
    def add_event(self, key: str, event_data: Dict, ttl_seconds: int = 300):
        """
        Add event to a time-series list with automatic expiration
        
        Args:
            key: Redis key (e.g., "interface_events:R1:Gi0/1")
            event_data: Event dictionary with timestamp
            ttl_seconds: Time to live in seconds
        """
        timestamp = event_data.get('timestamp', time.time())
        scored_value = json.dumps(event_data)
        
        # Add to sorted set with timestamp as score
        self.redis_client.zadd(key, {scored_value: timestamp})
        
        # Set expiration
        self.redis_client.expire(key, ttl_seconds)
    
    def get_events_in_window(self, key: str, window_minutes: int = 5) -> List[Dict]:
        """
        Get all events in the last N minutes
        
        Args:
            key: Redis key
            window_minutes: Size of sliding window
            
        Returns:
            List of events in the window
        """
        now = time.time()
        min_timestamp = now - (window_minutes * 60)
        
        # Remove old events outside window
        self.redis_client.zremrangebyscore(key, '-inf', min_timestamp)
        
        # Get events in window
        events_json = self.redis_client.zrangebyscore(key, min_timestamp, '+inf')
        
        events = []
        for event_json in events_json:
            try:
                events.append(json.loads(event_json))
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse event: {event_json}")
        
        return events
    
    def count_events_in_window(self, key: str, window_minutes: int = 5) -> int:
        """Count events in sliding window"""
        now = time.time()
        min_timestamp = now - (window_minutes * 60)
        
        # Remove old events
        self.redis_client.zremrangebyscore(key, '-inf', min_timestamp)
        
        # Count remaining
        return self.redis_client.zcard(key)
    
    def increment_counter(self, key: str, ttl_seconds: int = 300) -> int:
        """
        Increment a counter with expiration
        
        Args:
            key: Counter key
            ttl_seconds: Expiration time
            
        Returns:
            New counter value
        """
        value = self.redis_client.incr(key)
        self.redis_client.expire(key, ttl_seconds)
        return value
    
    def get_counter(self, key: str) -> int:
        """Get counter value"""
        value = self.redis_client.get(key)
        return int(value) if value else 0
    
    def set_json(self, key: str, data: Dict, ttl_seconds: Optional[int] = None):
        """Store JSON data"""
        self.redis_client.set(key, json.dumps(data))
        if ttl_seconds:
            self.redis_client.expire(key, ttl_seconds)
    
    def get_json(self, key: str) -> Optional[Dict]:
        """Retrieve JSON data"""
        data = self.redis_client.get(key)
        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON from key: {key}")
        return None
    
    def cleanup_old_keys(self, pattern: str, older_than_minutes: int = 60):
        """
        Clean up old keys matching pattern
        
        Args:
            pattern: Redis key pattern (e.g., "interface_events:*")
            older_than_minutes: Delete keys older than this
        """
        cursor = 0
        deleted_count = 0
        
        while True:
            cursor, keys = self.redis_client.scan(cursor, match=pattern, count=100)
            
            for key in keys:
                # Check if key has any recent activity
                ttl = self.redis_client.ttl(key)
                if ttl == -1:  # No expiration set
                    self.redis_client.expire(key, 300)  # Set default expiration
                
            if cursor == 0:
                break
        
        logger.info(f"Cleanup completed. Pattern: {pattern}")
