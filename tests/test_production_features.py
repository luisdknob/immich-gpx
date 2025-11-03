"""
Comprehensive tests for production-grade features.

Tests caching, rate limiting, performance metrics, and other features
that ensure production readiness.
"""

import pytest
import time
from datetime import datetime

from immich_gpx.cache import CacheEntry, APIResponseCache
from immich_gpx.rate_limiter import RateLimiter
from immich_gpx.metrics import PerformanceMetrics


class TestCacheEntry:
    """Tests for CacheEntry class."""
    
    def test_cache_entry_creation(self):
        """Test creating cache entry."""
        entry = CacheEntry("test_value", ttl_seconds=60)
        assert entry.value == "test_value"
        assert entry.ttl_seconds == 60
        assert entry.created_at is not None
    
    def test_cache_entry_not_expired_immediately(self):
        """Test entry is not expired immediately."""
        entry = CacheEntry("value", ttl_seconds=60)
        assert entry.is_expired() is False
    
    def test_cache_entry_expired_after_ttl(self):
        """Test entry expires after TTL."""
        entry = CacheEntry("value", ttl_seconds=1)
        assert entry.is_expired() is False
        time.sleep(1.1)
        assert entry.is_expired() is True
    
    def test_cache_entry_age_seconds(self):
        """Test age calculation."""
        entry = CacheEntry("value", ttl_seconds=60)
        time.sleep(0.1)
        age = entry.age_seconds()
        assert age >= 0.1
        assert age < 1.0


class TestAPIResponseCache:
    """Tests for APIResponseCache class."""
    
    def test_cache_initialization(self):
        """Test cache initializes empty."""
        cache = APIResponseCache(ttl_seconds=3600)
        assert len(cache.cache) == 0
        stats = cache.stats()
        assert stats['entries'] == 0
    
    def test_cache_set_and_get(self):
        """Test setting and getting cache values."""
        cache = APIResponseCache()
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
    
    def test_cache_miss_returns_none(self):
        """Test missing key returns None."""
        cache = APIResponseCache()
        assert cache.get("nonexistent") is None
    
    def test_cache_expiration(self):
        """Test cache entries expire."""
        cache = APIResponseCache(ttl_seconds=1)
        cache.set("key", "value")
        assert cache.get("key") == "value"
        time.sleep(1.1)
        assert cache.get("key") is None
    
    def test_cache_custom_ttl(self):
        """Test custom TTL per entry."""
        cache = APIResponseCache(ttl_seconds=10)
        cache.set("key1", "value1", ttl_seconds=1)
        cache.set("key2", "value2", ttl_seconds=10)
        
        time.sleep(1.1)
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
    
    def test_cache_has_method(self):
        """Test has method."""
        cache = APIResponseCache()
        cache.set("key", "value")
        assert cache.has("key") is True
        assert cache.has("nonexistent") is False
    
    def test_cache_delete(self):
        """Test deleting cache entry."""
        cache = APIResponseCache()
        cache.set("key", "value")
        assert cache.delete("key") is True
        assert cache.get("key") is None
        assert cache.delete("key") is False
    
    def test_cache_clear(self):
        """Test clearing all cache."""
        cache = APIResponseCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert len(cache.cache) == 2
        
        cache.clear()
        assert len(cache.cache) == 0
        assert cache.get("key1") is None
    
    def test_cache_cleanup_expired(self):
        """Test cleanup removes expired entries."""
        cache = APIResponseCache(ttl_seconds=1)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        time.sleep(1.1)
        removed = cache.cleanup_expired()
        
        assert removed == 2
        assert len(cache.cache) == 0
    
    def test_cache_stats(self):
        """Test cache statistics."""
        cache = APIResponseCache(ttl_seconds=10)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        stats = cache.stats()
        assert stats['entries'] == 2
        assert stats['valid'] == 2
        assert stats['expired'] == 0
    
    def test_cache_stats_with_expired(self):
        """Test stats counts expired entries."""
        cache = APIResponseCache(ttl_seconds=1)
        cache.set("key1", "value1")
        
        time.sleep(1.1)
        
        stats = cache.stats()
        assert stats['entries'] == 1
        assert stats['expired'] == 1
        assert stats['valid'] == 0
    
    def test_cache_repr(self):
        """Test cache string representation."""
        cache = APIResponseCache()
        cache.set("key", "value")
        repr_str = repr(cache)
        assert "APIResponseCache" in repr_str
        assert "entries=1" in repr_str


class TestRateLimiter:
    """Tests for RateLimiter class."""
    
    def test_rate_limiter_allows_requests_within_limit(self):
        """Test rate limiter allows requests within limit."""
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        assert limiter.allow_request() is True
        assert limiter.allow_request() is True
        assert limiter.allow_request() is True
    
    def test_rate_limiter_denies_over_limit(self):
        """Test rate limiter denies requests over limit."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        assert limiter.allow_request() is True
        assert limiter.allow_request() is True
        assert limiter.allow_request() is False
    
    def test_rate_limiter_window_reset(self):
        """Test rate limit resets after window."""
        limiter = RateLimiter(max_requests=1, window_seconds=1)
        assert limiter.allow_request() is True
        assert limiter.allow_request() is False
        
        time.sleep(1.1)
        assert limiter.allow_request() is True
    
    def test_rate_limiter_wait_if_needed(self):
        """Test wait_if_needed blocks until allowed."""
        limiter = RateLimiter(max_requests=1, window_seconds=1)
        assert limiter.allow_request() is True
        
        start = time.time()
        limiter.wait_if_needed()
        elapsed = time.time() - start
        
        assert elapsed >= 0.9  # Should have waited ~1 second
    
    def test_rate_limiter_requests_remaining(self):
        """Test requests_remaining calculation."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        assert limiter.requests_remaining() == 5
        
        limiter.allow_request()
        assert limiter.requests_remaining() == 4
        
        limiter.allow_request()
        assert limiter.requests_remaining() == 3
    
    def test_rate_limiter_reset(self):
        """Test resetting rate limiter."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        limiter.allow_request()
        limiter.allow_request()
        
        assert limiter.requests_remaining() == 0
        limiter.reset()
        assert limiter.requests_remaining() == 2
    
    def test_rate_limiter_stats(self):
        """Test rate limiter statistics."""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        limiter.allow_request()
        limiter.allow_request()
        
        stats = limiter.stats()
        assert stats['max_requests'] == 10
        assert stats['window_seconds'] == 60
        assert stats['current_requests'] == 2
        assert stats['remaining'] == 8
    
    def test_rate_limiter_repr(self):
        """Test rate limiter string representation."""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        limiter.allow_request()
        
        repr_str = repr(limiter)
        assert "RateLimiter" in repr_str
        assert "max=10" in repr_str


class TestPerformanceMetrics:
    """Tests for PerformanceMetrics class."""
    
    def test_metrics_initialization(self):
        """Test metrics initializes properly."""
        metrics = PerformanceMetrics("Test Operation")
        assert metrics.operation == "Test Operation"
        assert metrics.start_time is not None
        assert metrics.end_time is None
        assert metrics.duration_seconds == 0.0
    
    def test_metrics_complete(self):
        """Test completing metrics."""
        metrics = PerformanceMetrics("Test")
        time.sleep(0.1)
        metrics.complete(items_processed=100, errors=5)
        
        assert metrics.end_time is not None
        assert metrics.duration_seconds >= 0.1
        assert metrics.items_processed == 100
        assert metrics.errors == 5
    
    def test_metrics_throughput_calculation(self):
        """Test throughput calculation."""
        metrics = PerformanceMetrics("Test")
        time.sleep(0.1)
        metrics.complete(items_processed=10, errors=0)
        
        assert metrics.items_per_second > 0
        assert metrics.items_per_second >= 50  # At least 50 items/sec
    
    def test_metrics_duration_millis(self):
        """Test duration in milliseconds."""
        metrics = PerformanceMetrics("Test")
        time.sleep(0.1)
        metrics.complete(items_processed=10)
        
        millis = metrics.duration_millis()
        assert millis >= 100  # At least 100ms
    
    def test_metrics_success_count(self):
        """Test success count calculation."""
        metrics = PerformanceMetrics("Test")
        metrics.complete(items_processed=100, errors=10)
        
        assert metrics.success_count() == 90
    
    def test_metrics_success_rate(self):
        """Test success rate calculation."""
        metrics = PerformanceMetrics("Test")
        metrics.complete(items_processed=100, errors=10)
        
        assert metrics.success_rate() == 90.0
    
    def test_metrics_success_rate_zero(self):
        """Test success rate with no items."""
        metrics = PerformanceMetrics("Test")
        metrics.complete(items_processed=0, errors=0)
        
        assert metrics.success_rate() == 0.0
    
    def test_metrics_summary(self):
        """Test summary message."""
        metrics = PerformanceMetrics("Parse GPX")
        metrics.complete(items_processed=150, errors=0)
        
        summary = metrics.summary()
        assert "Parse GPX" in summary
        assert "150 items" in summary
        assert "0 errors" in summary
    
    def test_metrics_detailed_summary(self):
        """Test detailed summary message."""
        metrics = PerformanceMetrics("Update Photos")
        metrics.complete(items_processed=100, errors=10)
        
        summary = metrics.detailed_summary()
        assert "Update Photos" in summary
        assert "100 items" in summary
        assert "90 successful" in summary
        assert "90.0%" in summary
        assert "10 errors" in summary
    
    def test_metrics_repr(self):
        """Test metrics string representation."""
        metrics = PerformanceMetrics("Test")
        metrics.complete(items_processed=100)
        
        repr_str = repr(metrics)
        assert "PerformanceMetrics" in repr_str
        assert "Test" in repr_str
        assert "items=100" in repr_str


class TestProductionFeaturesIntegration:
    """Integration tests for production features together."""
    
    def test_cache_and_rate_limiter_together(self):
        """Test cache and rate limiter work together."""
        cache = APIResponseCache(ttl_seconds=10)
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        # Simulate API calls
        for i in range(3):
            if limiter.allow_request():
                cache.set(f"key{i}", f"value{i}")
        
        assert cache.stats()['entries'] == 3
        assert limiter.requests_remaining() == 2
    
    def test_metrics_with_batch_processing(self):
        """Test metrics track batch processing."""
        metrics = PerformanceMetrics("Batch Process")
        
        # Simulate batch processing
        time.sleep(0.05)
        
        metrics.complete(items_processed=200, errors=5)
        
        summary = metrics.detailed_summary()
        assert "200 items" in summary
        assert "195 successful" in summary
        assert "97.5%" in summary
    
    def test_cache_expiration_with_metrics(self):
        """Test cache expiration tracked with metrics."""
        cache = APIResponseCache(ttl_seconds=1)
        metrics = PerformanceMetrics("Cache Operations")
        
        # Add items to cache
        for i in range(5):
            cache.set(f"key{i}", f"value{i}")
        
        assert cache.stats()['valid'] == 5
        
        # Wait for expiration
        time.sleep(1.1)
        
        # Check expired
        expired_removed = cache.cleanup_expired()
        metrics.complete(items_processed=expired_removed)
        
        assert metrics.success_count() == 5
