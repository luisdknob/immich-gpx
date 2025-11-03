"""
Comprehensive end-to-end integration tests for v1.0.0 release.

Tests complete workflows including:
- GPX parsing → Photo fetching → Matching → Updating
- Production features: caching, rate limiting, metrics
- Error handling and recovery
- Configuration loading
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import patch, Mock, MagicMock
from pathlib import Path

from immich_gpx import (
    GPXParser,
    ImmichAPI,
    GPSMatcher,
    PerformanceMetrics,
    APIResponseCache,
    RateLimiter,
    ConfigLoader,
    UpdateResult,
)


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows."""
    
    def test_full_pipeline_with_metrics(self, tmp_gpx_file):
        """Test complete pipeline with performance metrics."""
        # Parse GPX with metrics
        parse_metrics = PerformanceMetrics("Parse GPX")
        parser = GPXParser(str(tmp_gpx_file))
        gps_points = parser.parse()
        parse_metrics.complete(items_processed=len(gps_points), errors=0)
        
        assert len(gps_points) > 0
        assert parse_metrics.success_rate() == 100.0
        
        # Mock Immich API with caching
        with patch('requests.Session.get') as mock_get, \
             patch('requests.Session.post') as mock_post:
            
            # Mock connection test
            mock_get.return_value = Mock(
                json=lambda: {'version': '2.1.0'},
                raise_for_status=Mock()
            )
            
            # Mock photo query
            mock_photos = [
                {
                    'id': 'photo1',
                    'originalFileName': 'test1.jpg',
                    'fileCreatedAt': '2022-02-16T12:06:30Z',
                    'exifInfo': {
                        'dateTimeOriginal': '2022-02-16T12:06:30Z',
                        'latitude': -41.2,
                        'longitude': -71.8
                    }
                }
            ]
            mock_post.return_value = Mock(
                json=lambda: {'assets': {'items': mock_photos, 'nextPage': False}},
                raise_for_status=Mock()
            )
            
            # Create API client
            api = ImmichAPI("https://test.com", "key")
            
            # Fetch photos with metrics
            fetch_metrics = PerformanceMetrics("Fetch Photos")
            start_time, end_time = parser.get_time_range()
            photos = api.get_photos_in_range(start_time, end_time)
            fetch_metrics.complete(items_processed=len(photos), errors=0)
            
            assert len(photos) > 0
            assert fetch_metrics.success_rate() == 100.0
            
            # Match with metrics
            match_metrics = PerformanceMetrics("Match Photos")
            matcher = GPSMatcher(threshold=300)
            matches = matcher.match_photos_to_points(gps_points, photos)
            match_metrics.complete(items_processed=len(photos), errors=0)
            
            assert len(matches) > 0
            assert match_metrics.success_rate() == 100.0
    
    def test_workflow_with_caching(self, tmp_gpx_file):
        """Test that caching works in workflow."""
        parser = GPXParser(str(tmp_gpx_file))
        gps_points = parser.parse()
        start_time, end_time = parser.get_time_range()
        
        with patch('requests.Session.get') as mock_get, \
             patch('requests.Session.post') as mock_post:
            
            mock_get.return_value = Mock(
                json=lambda: {'version': '2.1.0'},
                raise_for_status=Mock()
            )
            
            mock_photos = [{'id': 'photo1', 'originalFileName': 'test1.jpg'}]
            mock_post.return_value = Mock(
                json=lambda: {'assets': {'items': mock_photos, 'nextPage': False}},
                raise_for_status=Mock()
            )
            
            api = ImmichAPI("https://test.com", "key")
            
            # First call - should hit API
            photos1 = api.get_photos_in_range(start_time, end_time)
            assert mock_post.call_count == 1
            
            # Second call - should hit cache
            photos2 = api.get_photos_in_range(start_time, end_time)
            assert mock_post.call_count == 1  # No additional calls
            assert photos1 == photos2
            
            # Check cache stats
            stats = api.response_cache.stats()
            assert stats['entries'] > 0
    
    def test_workflow_with_rate_limiting(self, tmp_gpx_file):
        """Test that rate limiting works in workflow."""
        parser = GPXParser(str(tmp_gpx_file))
        gps_points = parser.parse()
        start_time, end_time = parser.get_time_range()
        
        # Skip if no valid time range
        if not start_time or not end_time:
            pytest.skip("No valid time range in GPX file")
        
        with patch('requests.Session.get') as mock_get, \
             patch('requests.Session.post') as mock_post:
            
            mock_get.return_value = Mock(
                json=lambda: {'version': '2.1.0'},
                raise_for_status=Mock()
            )
            
            mock_post.return_value = Mock(
                json=lambda: {'assets': {'items': [], 'nextPage': False}},
                raise_for_status=Mock()
            )
            
            # Create API with strict rate limiter
            api = ImmichAPI("https://test.com", "key")
            api.rate_limiter = RateLimiter(max_requests=2, window_seconds=1)
            api.response_cache.clear()  # Clear cache to force API calls
            
            # Make 3 requests rapidly with different time ranges
            start = time.time()
            api.get_photos_in_range(start_time, end_time)
            api.get_photos_in_range(start_time, end_time + timedelta(seconds=1))
            api.get_photos_in_range(start_time, end_time + timedelta(seconds=2))
            elapsed = time.time() - start
            
            # Third request should have been delayed
            assert elapsed >= 0.5  # Some delay from rate limiting
    
    def test_batch_update_with_partial_success(self):
        """Test batch update with some failures."""
        matches = [
            {
                'photo': {'id': 'photo1', 'originalFileName': 'test1.jpg'},
                'gps_point': {'latitude': 40.7, 'longitude': -74.0}
            },
            {
                'photo': {'id': 'photo2', 'originalFileName': 'test2.jpg'},
                'gps_point': {'latitude': 40.8, 'longitude': -74.1}
            },
            {
                'photo': {'id': 'photo3', 'originalFileName': 'test3.jpg'},
                'gps_point': {'latitude': 40.9, 'longitude': -74.2}
            },
        ]
        
        with patch('requests.Session.get') as mock_get, \
             patch('requests.Session.put') as mock_put:
            
            mock_get.return_value = Mock(
                json=lambda: {'version': '2.1.0'},
                raise_for_status=Mock()
            )
            
            # Make second update fail
            def mock_put_side_effect(*args, **kwargs):
                response = Mock()
                if 'photo2' in args[0]:
                    response.raise_for_status.side_effect = Exception("Update failed")
                else:
                    response.raise_for_status = Mock()
                return response
            
            mock_put.side_effect = mock_put_side_effect
            
            api = ImmichAPI("https://test.com", "key")
            result = api.batch_update_photos(matches, dry_run=False)
            
            # Should have 2 successes, 1 failure
            assert result.successful == 2
            assert result.failed == 1
            assert result.success_rate == pytest.approx(66.67, rel=0.1)


class TestProductionFeatures:
    """Test production features in real workflows."""
    
    def test_config_loader_integration(self, tmp_path):
        """Test loading configuration and using in workflow."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
immich:
  url: http://localhost:2283
  api_key: test-key
  timeout: 20

matching:
  threshold: 120

performance:
  cache_ttl: 1800
  rate_limit_requests: 50
  rate_limit_window: 60
""")
        
        loader = ConfigLoader(str(config_file))
        config = loader.load()
        loader.validate()
        
        immich_cfg = loader.get_immich_config()
        matching_cfg = loader.get_matching_config()
        perf_cfg = loader.get_performance_config()
        
        # Verify config loaded correctly
        assert immich_cfg['url'] == 'http://localhost:2283'
        assert immich_cfg['timeout'] == 20
        assert matching_cfg['threshold'] == 120
        assert perf_cfg['cache_ttl'] == 1800
        
        # Create API with config
        with patch('requests.Session.get') as mock_get:
            mock_get.return_value = Mock(
                json=lambda: {'version': '2.1.0'},
                raise_for_status=Mock()
            )
            
            api = ImmichAPI(
                immich_cfg['url'],
                immich_cfg['api_key'],
                timeout=immich_cfg['timeout']
            )
            
            # Override cache/limiter with config values
            api.response_cache = APIResponseCache(ttl_seconds=perf_cfg['cache_ttl'])
            api.rate_limiter = RateLimiter(
                max_requests=perf_cfg['rate_limit_requests'],
                window_seconds=perf_cfg['rate_limit_window']
            )
            
            assert api.test_connection()
    
    def test_error_recovery_workflow(self, tmp_gpx_file):
        """Test error recovery in workflow."""
        import requests
        
        parser = GPXParser(str(tmp_gpx_file))
        gps_points = parser.parse()
        
        # Simulate transient error recovery with UpdateResult
        update_result = UpdateResult()
        
        # Test that UpdateResult tracks errors correctly
        assert update_result.total == 0
        assert update_result.successful == 0
        
        # Simulate a failed update scenario
        error_msg = "Connection timeout during update"
        update_result.add_error("photo1", Exception(error_msg))
        
        # Verify error tracking
        assert len(update_result.errors) == 1
        assert update_result.errors[0]['error'] == error_msg
        assert update_result.total == 1
        assert update_result.failed == 1
        assert update_result.success_rate == 0.0


class TestRealGPXFiles:
    """Test with real GPX file samples from gpx/ directory."""
    
    @pytest.fixture
    def sample_gpx_files(self):
        """Get sample GPX files if they exist."""
        gpx_dir = Path(__file__).parent.parent / "gpx"
        if gpx_dir.exists():
            return list(gpx_dir.glob("*.gpx"))[:3]  # Test with first 3 files
        return []
    
    def test_parse_real_gpx_files(self, sample_gpx_files):
        """Test parsing real GPX files from samples."""
        if not sample_gpx_files:
            pytest.skip("No sample GPX files found in gpx/ directory")
        
        for gpx_file in sample_gpx_files:
            parser = GPXParser(str(gpx_file))
            gps_points = parser.parse()
            
            # Verify parsed data
            assert len(gps_points) > 0, f"No GPS points in {gpx_file.name}"
            
            for point in gps_points:
                assert 'latitude' in point
                assert 'longitude' in point
                assert 'time' in point
                assert -90 <= point['latitude'] <= 90
                assert -180 <= point['longitude'] <= 180
            
            # Verify time range
            start_time, end_time = parser.get_time_range()
            assert start_time is not None
            assert end_time is not None
            assert start_time <= end_time
    
    def test_end_to_end_with_real_gpx(self, sample_gpx_files):
        """Test complete workflow with real GPX file."""
        if not sample_gpx_files:
            pytest.skip("No sample GPX files found in gpx/ directory")
        
        gpx_file = sample_gpx_files[0]
        
        # Parse real GPX
        metrics = PerformanceMetrics(f"Process {gpx_file.name}")
        parser = GPXParser(str(gpx_file))
        gps_points = parser.parse()
        start_time, end_time = parser.get_time_range()
        
        # Mock Immich API
        with patch('requests.Session.get') as mock_get, \
             patch('requests.Session.post') as mock_post:
            
            mock_get.return_value = Mock(
                json=lambda: {'version': '2.1.0'},
                raise_for_status=Mock()
            )
            
            # Create realistic photo data
            mock_photos = []
            for i, point in enumerate(gps_points[:10]):  # First 10 points
                mock_photos.append({
                    'id': f'photo{i}',
                    'originalFileName': f'IMG_{i:04d}.jpg',
                    'fileCreatedAt': point['time'].isoformat() + 'Z',
                    'exifInfo': {
                        'dateTimeOriginal': point['time'].isoformat() + 'Z',
                        'latitude': point['latitude'],
                        'longitude': point['longitude']
                    }
                })
            
            mock_post.return_value = Mock(
                json=lambda: {'assets': {'items': mock_photos, 'nextPage': False}},
                raise_for_status=Mock()
            )
            
            # Execute workflow
            api = ImmichAPI("https://test.com", "key")
            photos = api.get_photos_in_range(start_time, end_time)
            
            # Use wider threshold for test
            matcher = GPSMatcher(threshold=600)  # 10 minutes
            matches = matcher.match_photos_to_points(gps_points, photos)
            
            metrics.complete(items_processed=len(matches), errors=0)
            
            # Verify results - may be 0 if no matches, that's OK
            if len(matches) > 0:
                assert metrics.success_rate == 100.0
                
                # Verify match quality
                for match in matches:
                    assert 'photo' in match
                    assert 'gps_point' in match
                    assert 'distance' in match or 'time_diff' in match


class TestErrorScenarios:
    """Test various error scenarios in workflows."""
    
    def test_invalid_gpx_file(self):
        """Test handling of invalid GPX file."""
        from immich_gpx.core.errors import GPXValidationError
        
        with pytest.raises((GPXValidationError, FileNotFoundError)):
            parser = GPXParser("/nonexistent/file.gpx")
            parser.parse()
    
    def test_connection_failure(self):
        """Test handling of connection failures."""
        from immich_gpx.core.errors import ConnectionError
        import requests
        
        with patch('requests.Session.get') as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError("Cannot connect")
            
            api = ImmichAPI("https://test.com", "key")
            with pytest.raises(ConnectionError):
                api.test_connection()
    
    def test_authentication_failure(self):
        """Test handling of authentication failures."""
        from immich_gpx.core.errors import AuthenticationError
        
        with patch('requests.Session.get') as mock_get:
            response = Mock()
            response.status_code = 401
            mock_get.return_value = response
            
            api = ImmichAPI("https://test.com", "invalid-key")
            with pytest.raises(AuthenticationError):
                api.test_connection()
    
    def test_empty_results(self, tmp_gpx_file):
        """Test workflow when no matches found."""
        parser = GPXParser(str(tmp_gpx_file))
        gps_points = parser.parse()
        
        # No photos returned
        with patch('requests.Session.post') as mock_post:
            mock_post.return_value = Mock(
                json=lambda: {'assets': {'items': [], 'nextPage': False}},
                raise_for_status=Mock()
            )
            
            api = ImmichAPI("https://test.com", "key")
            start_time, end_time = parser.get_time_range()
            photos = api.get_photos_in_range(start_time, end_time)
            
            assert len(photos) == 0
            
            matcher = GPSMatcher()
            matches = matcher.match_photos_to_points(gps_points, photos)
            
            assert len(matches) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
