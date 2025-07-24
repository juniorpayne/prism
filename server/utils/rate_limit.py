"""Simple rate limiting utilities for API endpoints."""

from typing import Dict, Tuple
from datetime import datetime, timezone, timedelta
import asyncio

# In-memory rate limit storage (in production, use Redis or similar)
_rate_limit_store: Dict[str, Tuple[int, datetime]] = {}
_lock = asyncio.Lock()


async def check_rate_limit(key: str, max_attempts: int = 10, window: int = 3600) -> bool:
    """
    Check if a rate limit has been exceeded.
    
    Args:
        key: Unique identifier for the rate limit (e.g., "revoke_all:user_id")
        max_attempts: Maximum number of attempts allowed
        window: Time window in seconds
        
    Returns:
        True if the action is allowed, False if rate limited
    """
    async with _lock:
        now = datetime.now(timezone.utc)
        window_delta = timedelta(seconds=window)
        
        # Clean up old entries
        keys_to_remove = []
        for k, (count, timestamp) in _rate_limit_store.items():
            if now - timestamp > window_delta:
                keys_to_remove.append(k)
        
        for k in keys_to_remove:
            del _rate_limit_store[k]
        
        # Check current rate limit
        if key in _rate_limit_store:
            count, first_attempt = _rate_limit_store[key]
            if now - first_attempt <= window_delta:
                if count >= max_attempts:
                    return False
                _rate_limit_store[key] = (count + 1, first_attempt)
            else:
                # Window has expired, reset
                _rate_limit_store[key] = (1, now)
        else:
            # First attempt
            _rate_limit_store[key] = (1, now)
        
        return True