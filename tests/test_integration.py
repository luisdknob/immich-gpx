"""Integration tests for immich_gpx_linker."""
import pytest
from unittest.mock import patch, Mock
from datetime import datetime
from immich_gpx import GPXParser, ImmichAPI, GPSMatcher


def test_full_workflow(tmp_gpx_file, mock_immich_response):
    """Test complete workflow from GPX parsing to photo matching."""
    # Parse GPX
    parser = GPXParser(str(tmp_gpx_file))
    gps_points = parser.parse()
    assert len(gps_points) == 3
    
    # Verify GPS points have required fields
    for point in gps_points:
        assert 'latitude' in point
        assert 'longitude' in point
        assert 'time' in point
    
    # Mock Immich API
    with patch('requests.Session.post') as mock_post, \
         patch('requests.Session.get') as mock_get:
        
        # Mock connection test
        mock_get.return_value = Mock(json=lambda: {'version': '2.1.0'})
        mock_get.return_value.raise_for_status = Mock()
        
        # Mock photo query - wrap response in assets structure
        mock_post.return_value = Mock(json=lambda: {'assets': {'items': mock_immich_response, 'nextPage': False}})
        mock_post.return_value.raise_for_status = Mock()
        
        api = ImmichAPI("https://test.com", "key")
        assert api.test_connection()
        
        with patch.object(api, 'get_photo_exif', return_value={'dateTimeOriginal': '2022-02-16T12:06:30Z'}):
            photos = api.get_photos_in_range(
                datetime(2022, 2, 16, 12, 0),
                datetime(2022, 2, 16, 13, 0)
            )
        
        # Match photos
        matcher = GPSMatcher()
        matches = matcher.match_photos_to_points(gps_points, photos)
        
        assert len(matches) > 0


def test_workflow_with_logging(tmp_gpx_file, mock_immich_response):
    """Test complete workflow with logging."""
    import logging
    logger = logging.getLogger('integration_test')
    
    parser = GPXParser(str(tmp_gpx_file), logger=logger)
    gps_points = parser.parse()
    
    with patch('requests.Session.get') as mock_get:
        mock_get.return_value = Mock(json=lambda: {'version': '2.1.0'})
        mock_get.return_value.raise_for_status = Mock()
        
        api = ImmichAPI("https://test.com", "key", logger=logger)
        assert api.test_connection()
        
        matcher = GPSMatcher(logger=logger)
        assert matcher is not None


def test_workflow_empty_gps_file(tmp_path, empty_gpx_content, mock_immich_response):
    """Test workflow with empty GPX file."""
    gpx_file = tmp_path / "empty.gpx"
    gpx_file.write_text(empty_gpx_content)
    
    parser = GPXParser(str(gpx_file))
    gps_points = parser.parse()
    assert len(gps_points) == 0
    
    with patch('requests.Session.post') as mock_post:
        mock_post.return_value = Mock(json=lambda: {'assets': {'items': mock_immich_response, 'nextPage': False}})
        mock_post.return_value.raise_for_status = Mock()
        
        api = ImmichAPI("https://test.com", "key")
        with patch.object(api, 'get_photo_exif', return_value={'dateTimeOriginal': '2022-02-16T12:06:30Z'}):
            photos = api.get_photos_in_range(
                datetime(2022, 2, 16, 12, 0),
                datetime(2022, 2, 16, 13, 0)
            )
        
        matcher = GPSMatcher()
        matches = matcher.match_photos_to_points(gps_points, photos)
        
        assert len(matches) == 0


def test_workflow_no_photos(tmp_gpx_file):
    """Test workflow when API returns no photos."""
    parser = GPXParser(str(tmp_gpx_file))
    gps_points = parser.parse()
    assert len(gps_points) == 3
    
    with patch('requests.Session.post') as mock_post:
        mock_post.return_value = Mock(json=lambda: {'assets': {'items': [], 'nextPage': False}})
        mock_post.return_value.raise_for_status = Mock()
        
        api = ImmichAPI("https://test.com", "key")
        photos = api.get_photos_in_range(
            datetime(2022, 2, 16, 12, 0),
            datetime(2022, 2, 16, 13, 0)
        )
        
        matcher = GPSMatcher()
        matches = matcher.match_photos_to_points(gps_points, photos)
        
        assert len(matches) == 0


def test_workflow_time_range_extraction(tmp_gpx_file, mock_immich_response):
    """Test extracting time range from GPX and using it for API query."""
    parser = GPXParser(str(tmp_gpx_file))
    gps_points = parser.parse()
    
    start_time, end_time = parser.get_time_range()
    
    assert start_time is not None
    assert end_time is not None
    assert start_time < end_time
    
    with patch('requests.Session.post') as mock_post:
        mock_post.return_value = Mock(json=lambda: {'assets': {'items': mock_immich_response, 'nextPage': False}})
        mock_post.return_value.raise_for_status = Mock()
        
        api = ImmichAPI("https://test.com", "key")
        with patch.object(api, 'get_photo_exif', return_value={'dateTimeOriginal': '2022-02-16T12:06:30Z'}):
            photos = api.get_photos_in_range(start_time, end_time)
        
        matcher = GPSMatcher()
        matches = matcher.match_photos_to_points(gps_points, photos)
        
        # Verify matches have required structure
        for match in matches:
            assert 'photo' in match
            assert 'gps_point' in match
            assert 'time_difference_seconds' in match
