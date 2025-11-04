"""
In-memory response caching with TTL for API calls.

Reduces API calls by caching frequently requested data like photo lists.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional


class CacheEntry:
    """
    Cache entry with time-to-live (TTL) expiration.
    
    Stores a value along with its creation time. Entries automatically
    expire after the specified TTL period.
    
    Attributes:
        value: The cached value
        created_at: Datetime when entry was created
        ttl_seconds: Time to live in seconds
        
    Example:
        >>> entry = CacheEntry("data", ttl_seconds=60)
        >>> entry.is_expired()
        False
        >>> # After 60+ seconds...
        >>> entry.is_expired()
        True
    """
    
    def __init__(self, value: Any, ttl_seconds: int = 3600):
        """
        Initialize cache entry.
        
        Args:
            value: Value to cache
            ttl_seconds: Time to live in seconds (default: 3600 = 1 hour)
            
        Returns:
            None
        """
        self.value = value
        self.created_at = datetime.now()
        self.ttl_seconds = ttl_seconds
    
    def is_expired(self) -> bool:
        """
        Check if cache entry has expired.
        
        Returns:
            True if entry age exceeds TTL, False otherwise
            
        Example:
            >>> entry = CacheEntry("data", ttl_seconds=1)
            >>> entry.is_expired()
            False
        """
        age = (datetime.now() - self.created_at).total_seconds()
        return age > self.ttl_seconds
    
    def age_seconds(self) -> float:
        """
        Get age of cache entry in seconds.
        
        Returns:
            Age of entry in seconds since creation
        """
        return (datetime.now() - self.created_at).total_seconds()


class APIResponseCache:
    """
    In-memory cache for API responses with TTL.
    
    Stores API responses in memory with automatic expiration based on
    time-to-live. Useful for reducing repeated API calls during the
    same session or operation.
    
    Key features:
    - Automatic expiration of stale entries
    - Per-entry TTL configuration
    - Cache statistics
    - Manual clear operation
    
    Attributes:
        cache: Dictionary storing CacheEntry objects
        ttl_seconds: Default TTL for new entries
        
    Example:
        >>> cache = APIResponseCache(ttl_seconds=3600)
        >>> cache.set("users:123", user_data)
        >>> cached = cache.get("users:123")
        >>> if cached:
        ...     print("Using cached data")
    """
    
    def __init__(self, ttl_seconds: int = 3600):
        """
        Initialize response cache.
        
        Args:
            ttl_seconds: Default time-to-live for cached entries (default: 3600)
            
        Returns:
            None
        """
        self.cache: Dict[str, CacheEntry] = {}
        self.ttl_seconds = ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get cached value if not expired.
        
        Automatically removes expired entries and returns None if entry
        is not found or has expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value if found and not expired, None otherwise
            
        Example:
            >>> cache = APIResponseCache()
            >>> cache.set("key", "value")
            >>> cache.get("key")
            'value'
            >>> cache.get("nonexistent")
            None
        """
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        
        # Check if expired
        if entry.is_expired():
            del self.cache[key]
            return None
        
        return entry.value
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """
        Cache a value.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Custom TTL for this entry (default: use cache default)
            
        Returns:
            None
            
        Example:
            >>> cache = APIResponseCache()
            >>> cache.set("key", "value")
            >>> cache.set("key2", "value2", ttl_seconds=60)
        """
        ttl = ttl_seconds if ttl_seconds is not None else self.ttl_seconds
        self.cache[key] = CacheEntry(value, ttl)
    
    def has(self, key: str) -> bool:
        """
        Check if key exists in cache and is not expired.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists and is not expired
        """
        if key not in self.cache:
            return False
        
        entry = self.cache[key]
        if entry.is_expired():
            del self.cache[key]
            return False
        
        return True
    
    def delete(self, key: str) -> bool:
        """
        Remove an entry from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if entry was deleted, False if not found
        """
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    def clear(self) -> None:
        """
        Clear all cache entries.
        
        Removes all cached values, including unexpired entries.
        
        Returns:
            None
        """
        self.cache.clear()
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from cache.
        
        Returns:
            Number of entries removed
        """
        expired_keys = [
            key for key, entry in self.cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        return len(expired_keys)
    
    def stats(self) -> Dict[str, int]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats:
            - entries: Total entries in cache
            - expired: Number of expired entries (not yet cleaned)
            - valid: Number of non-expired entries
            
        Example:
            >>> cache = APIResponseCache()
            >>> cache.set("key1", "value1")
            >>> cache.set("key2", "value2")
            >>> cache.stats()
            {'entries': 2, 'expired': 0, 'valid': 2}
        """
        expired = sum(1 for e in self.cache.values() if e.is_expired())
        
        return {
            'entries': len(self.cache),
            'expired': expired,
            'valid': len(self.cache) - expired,
        }
    
    def __repr__(self) -> str:
        """Return string representation."""
        stats = self.stats()
        return (
            f"APIResponseCache(entries={stats['entries']}, "
            f"valid={stats['valid']}, expired={stats['expired']}, "
            f"ttl={self.ttl_seconds}s)"
        )
