"""
Performance metrics collection and tracking.

Tracks timing, throughput, and error rates for operations to provide
visibility into performance characteristics and bottlenecks.

Classes:
    PerformanceMetrics: Track metrics for an operation

Usage:
    >>> metrics = PerformanceMetrics("Parse GPX")
    >>> # ... do work ...
    >>> metrics.complete(items_processed=150)
    >>> print(metrics.summary())
    'Parse GPX completed in 1.23s: 150 items, 122.0 items/sec, 0 errors'
"""

from datetime import datetime
from typing import Optional


class PerformanceMetrics:
    """
    Track performance metrics for an operation.
    
    Measures operation timing, throughput (items per second),
    item counts, and error rates. Useful for understanding
    performance bottlenecks and optimization opportunities.
    
    Attributes:
        operation: Name of the operation
        start_time: When operation started
        end_time: When operation completed
        duration_seconds: Total time taken
        items_processed: Number of items processed
        items_per_second: Throughput in items/sec
        errors: Number of errors encountered
        
    Example:
        >>> metrics = PerformanceMetrics("Match GPS points")
        >>> # ... do work ...
        >>> metrics.complete(items_processed=1000, errors=5)
        >>> print(metrics.summary())
        'Match GPS points completed in 2.34s: 1000 items, 427.4 items/sec, 5 errors'
    """
    
    def __init__(self, operation: str):
        """
        Initialize performance metrics tracker.
        
        Args:
            operation: Name of operation to track
            
        Returns:
            None
        """
        self.operation = operation
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.duration_seconds = 0.0
        self.items_processed = 0
        self.items_per_second = 0.0
        self.errors = 0
    
    def complete(self, items_processed: int = 0, errors: int = 0) -> None:
        """
        Mark operation complete and finalize metrics.
        
        Args:
            items_processed: Number of items processed (default: 0)
            errors: Number of errors encountered (default: 0)
            
        Returns:
            None
            
        Example:
            >>> metrics = PerformanceMetrics("Update photos")
            >>> # ... perform updates ...
            >>> metrics.complete(items_processed=95, errors=3)
        """
        self.end_time = datetime.now()
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        self.items_processed = items_processed
        self.errors = errors
        
        # Calculate throughput
        if self.duration_seconds > 0 and items_processed > 0:
            self.items_per_second = items_processed / self.duration_seconds
    
    def duration_millis(self) -> float:
        """
        Get operation duration in milliseconds.
        
        Returns:
            Duration in milliseconds (or 0 if not completed)
        """
        return self.duration_seconds * 1000
    
    def success_count(self) -> int:
        """
        Get successful items (total processed - errors).
        
        Returns:
            Number of successfully processed items
        """
        return max(0, self.items_processed - self.errors)
    
    def success_rate(self) -> float:
        """
        Get success rate as percentage.
        
        Returns:
            Success rate from 0-100 (or 0 if no items)
        """
        if self.items_processed == 0:
            return 0.0
        return (self.success_count() / self.items_processed) * 100
    
    def summary(self) -> str:
        """
        Generate human-readable performance summary.
        
        Returns:
            Summary string with timing, throughput, and error info
            
        Example:
            >>> metrics = PerformanceMetrics("Fetch photos")
            >>> metrics.complete(items_processed=250, errors=0)
            >>> metrics.summary()
            'Fetch photos completed in 1.45s: 250 items, 172.4 items/sec, 0 errors'
        """
        return (
            f"{self.operation} completed in {self.duration_seconds:.2f}s: "
            f"{self.items_processed} items, "
            f"{self.items_per_second:.1f} items/sec, "
            f"{self.errors} errors"
        )
    
    def detailed_summary(self) -> str:
        """
        Generate detailed performance summary with rates.
        
        Returns:
            Detailed summary including success rate
            
        Example:
            >>> metrics = PerformanceMetrics("Update")
            >>> metrics.complete(items_processed=100, errors=10)
            >>> print(metrics.detailed_summary())
            'Update: 2.34s, 100 items, 42.7 items/sec, 90 successful (90.0%), 10 errors'
        """
        return (
            f"{self.operation}: {self.duration_seconds:.2f}s, "
            f"{self.items_processed} items, "
            f"{self.items_per_second:.1f} items/sec, "
            f"{self.success_count()} successful ({self.success_rate():.1f}%), "
            f"{self.errors} errors"
        )
    
    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"PerformanceMetrics(operation={self.operation}, "
            f"duration={self.duration_seconds:.2f}s, "
            f"items={self.items_processed}, "
            f"throughput={self.items_per_second:.1f}/s, "
            f"errors={self.errors})"
        )
