"""
Rate limiting for API requests.

Implements token bucket rate limiting to prevent API overload and
maintain fair API usage. Useful for limiting requests to Immich API
and other external services.

Classes:
    RateLimiter: Token bucket rate limiter

Usage:
    >>> limiter = RateLimiter(max_requests=100, window_seconds=60)
    >>> if limiter.allow_request():
    ...     make_api_call()
    >>> limiter.wait_if_needed()  # Blocks until rate limit allows
    >>> remaining = limiter.requests_remaining()
"""

import time
from collections import deque
from typing import Deque


class RateLimiter:
    """
    Token bucket rate limiter.
    
    Limits requests to a maximum rate (e.g., 100 requests per 60 seconds).
    Implements sliding window rate limiting using a deque of request timestamps.
    
    Key features:
    - Configurable request limit and time window
    - Non-blocking check with allow_request()
    - Blocking wait with wait_if_needed()
    - Request count tracking
    - Remaining capacity check
    
    Attributes:
        max_requests: Maximum requests allowed per window
        window_seconds: Time window in seconds
        requests: Deque of request timestamps
        
    Example:
        >>> limiter = RateLimiter(max_requests=10, window_seconds=60)
        >>> # Allow first 10 requests
        >>> for i in range(10):
        ...     assert limiter.allow_request()
        >>> # 11th request denied
        >>> assert not limiter.allow_request()
        >>> # Wait and try again
        >>> limiter.wait_if_needed()
        >>> assert limiter.allow_request()
    """
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum requests allowed in window (default: 100)
            window_seconds: Time window in seconds (default: 60)
            
        Returns:
            None
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Deque[float] = deque()
    
    def allow_request(self) -> bool:
        """
        Check if a request is allowed without blocking.
        
        Returns:
            True if request is allowed, False if rate limit exceeded
            
        Note:
            If True, the request timestamp is recorded.
            
        Example:
            >>> limiter = RateLimiter(max_requests=1, window_seconds=60)
            >>> limiter.allow_request()
            True
            >>> limiter.allow_request()
            False
        """
        now = time.time()
        window_start = now - self.window_seconds
        
        # Remove requests outside the window
        while self.requests and self.requests[0] < window_start:
            self.requests.popleft()
        
        # Check if we have capacity
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        
        return False
    
    def wait_if_needed(self) -> float:
        """
        Block until rate limit allows a request.
        
        Sleeps briefly and retries until a request is allowed.
        Useful for ensuring requests stay within limits.
        
        Returns:
            Time waited in seconds
            
        Example:
            >>> limiter = RateLimiter(max_requests=1, window_seconds=1)
            >>> limiter.allow_request()
            True
            >>> wait_time = limiter.wait_if_needed()
            >>> print(f"Waited {wait_time:.1f} seconds")
        """
        wait_start = time.time()
        
        while not self.allow_request():
            time.sleep(0.05)  # Sleep 50ms between retries
        
        return time.time() - wait_start
    
    def requests_remaining(self) -> int:
        """
        Get number of remaining requests in current window.
        
        Returns:
            Number of requests still allowed in current window
            
        Example:
            >>> limiter = RateLimiter(max_requests=10, window_seconds=60)
            >>> limiter.allow_request()
            True
            >>> limiter.requests_remaining()
            9
        """
        now = time.time()
        window_start = now - self.window_seconds
        
        # Count only requests in current window
        count = sum(1 for t in self.requests if t >= window_start)
        
        return max(0, self.max_requests - count)
    
    def reset(self) -> None:
        """
        Reset rate limiter, clearing all request history.
        
        Returns:
            None
        """
        self.requests.clear()
    
    def stats(self) -> dict:
        """
        Get rate limiter statistics.
        
        Returns:
            Dictionary with stats:
            - max_requests: Maximum requests allowed
            - window_seconds: Time window size
            - current_requests: Requests in current window
            - remaining: Requests remaining
            
        Example:
            >>> limiter = RateLimiter(max_requests=10)
            >>> limiter.allow_request()
            True
            >>> limiter.stats()
            {'max_requests': 10, 'window_seconds': 60, 'current_requests': 1, 'remaining': 9}
        """
        remaining = self.requests_remaining()
        current = self.max_requests - remaining
        
        return {
            'max_requests': self.max_requests,
            'window_seconds': self.window_seconds,
            'current_requests': current,
            'remaining': remaining,
        }
    
    def __repr__(self) -> str:
        """Return string representation."""
        remaining = self.requests_remaining()
        current = self.max_requests - remaining
        return (
            f"RateLimiter(max={self.max_requests}, window={self.window_seconds}s, "
            f"current={current}, remaining={remaining})"
        )
