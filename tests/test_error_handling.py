"""
Tests for UpdateResult class in error_handling module.

UpdateResult is the only remaining class in error_handling after cleanup.
"""

import pytest
from immich_gpx.error_handling import UpdateResult


class TestUpdateResult:
    """Tests for UpdateResult dataclass."""
    
    def test_update_result_initialization(self):
        """Test UpdateResult initializes with correct defaults."""
        result = UpdateResult()
        
        assert result.successful == 0
        assert result.failed == 0
        assert result.skipped == 0
        assert len(result.errors) == 0
        assert result.total == 0
        assert result.success_rate == 0.0
    
    def test_update_result_total(self):
        """Test total calculation."""
        result = UpdateResult(successful=5, failed=2, skipped=3)
        assert result.total == 10
    
    def test_update_result_success_rate(self):
        """Test success rate calculation."""
        result = UpdateResult(successful=8, failed=2)
        assert result.success_rate == 80.0
    
    def test_update_result_success_rate_zero_total(self):
        """Test success rate when total is zero."""
        result = UpdateResult()
        assert result.success_rate == 0.0
    
    def test_update_result_add_error(self):
        """Test adding error to result."""
        result = UpdateResult()
        error = ValueError("Test error")
        
        result.add_error("photo123", error)
        
        assert result.failed == 1
        assert len(result.errors) == 1
        assert result.errors[0]['item_id'] == "photo123"
        assert result.errors[0]['error'] == "Test error"
        assert result.errors[0]['error_type'] == "ValueError"
    
    def test_update_result_summary(self):
        """Test summary string generation."""
        result = UpdateResult(successful=8, failed=1, skipped=1)
        summary = result.summary()
        
        assert "Processed 10 items" in summary
        assert "8 updated" in summary
        assert "1 failed" in summary
        assert "1 skipped" in summary
        assert "80.0% success rate" in summary
    
    def test_update_result_repr(self):
        """Test __repr__ method."""
        result = UpdateResult(successful=5, failed=1, skipped=2)
        repr_str = repr(result)
        
        assert "UpdateResult" in repr_str
        assert "successful=5" in repr_str
        assert "failed=1" in repr_str
        assert "skipped=2" in repr_str
        assert "total=8" in repr_str
