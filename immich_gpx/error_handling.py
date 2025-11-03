"""
Error handling and result tracking utilities for immich-gpx.

Provides UpdateResult dataclass for tracking batch operation outcomes,
including successes, failures, and skipped items.

Components:
    UpdateResult: Track partial success in batch operations

Usage:
    >>> result = UpdateResult()
    >>> for photo in photos:
    ...     try:
    ...         update_photo(photo)
    ...         result.successful += 1
    ...     except Exception as e:
    ...         result.add_error(photo['id'], e)
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class UpdateResult:
    """
    Result of a batch update operation.
    
    Tracks the outcome of attempting to update multiple items,
    including successes, failures, and skipped items. Useful for
    reporting partial success in batch operations.
    
    Attributes:
        successful: Number of items successfully updated
        failed: Number of items that failed
        skipped: Number of items skipped (e.g., dry-run mode)
        errors: List of error details for failed items
        
    Example:
        >>> result = UpdateResult()
        >>> for photo in photos:
        ...     try:
        ...         update_photo(photo)
        ...         result.successful += 1
        ...     except Exception as e:
        ...         result.add_error(photo['id'], e)
        
        >>> print(result.summary())
        'Processed 100 photos: 95 updated, 3 failed, 2 skipped (95.0% success rate)'
    """
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    errors: List[Dict[str, str]] = field(default_factory=list)
    
    @property
    def total(self) -> int:
        """Total number of items processed."""
        return self.successful + self.failed + self.skipped
    
    @property
    def success_rate(self) -> float:
        """Percentage of successful updates (0-100)."""
        if self.total == 0:
            return 0.0
        return (self.successful / self.total) * 100
    
    def add_error(self, item_id: str, error: Exception) -> None:
        """
        Record an error for a failed item.
        
        Args:
            item_id: Identifier of the item that failed
            error: Exception that occurred
            
        Returns:
            None
        """
        self.errors.append({
            'item_id': item_id,
            'error': str(error),
            'error_type': type(error).__name__,
        })
        self.failed += 1
    
    def summary(self) -> str:
        """
        Generate human-readable summary of update results.
        
        Returns:
            Summary string with counts and success rate
            
        Example:
            >>> result = UpdateResult(successful=95, failed=3, skipped=2)
            >>> result.summary()
            'Processed 100 photos: 95 updated, 3 failed, 2 skipped (95.0% success rate)'
        """
        return (
            f"Processed {self.total} items: "
            f"{self.successful} updated, "
            f"{self.failed} failed, "
            f"{self.skipped} skipped "
            f"({self.success_rate:.1f}% success rate)"
        )
    
    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"UpdateResult(successful={self.successful}, failed={self.failed}, "
            f"skipped={self.skipped}, total={self.total}, "
            f"success_rate={self.success_rate:.1f}%)"
        )
