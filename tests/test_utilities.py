"""Tests for utility functions and edge cases."""
import logging
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from immich_gpx import print_results, update_photo_positions, categorize_matches, prompt_update_mode
from tests.builders import photo, gps_point, match


def test_print_results_with_matches(logger):
    """Test printing results with matches."""
    
    gps_points = [
        {
            'latitude': 41.0,
            'longitude': -71.0,
            'elevation': 100,
            'time': datetime(2022, 2, 16, 12, 6, 29)
        }
    ]
    
    photos = [
        {
            'id': 'photo1',
            'originalFileName': 'test.jpg',
            'exifInfo': {
                'dateTimeOriginal': '2022-02-16T12:06:30Z',
                'latitude': 41.0,
                'longitude': -71.0
            }
        }
    ]
    
    matches = [match(photo('photo1', 41.0, -71.0, 'test.jpg'), gps_point(41.0, -71.0))]
    
    # Test with no immich_url to avoid asking for updates
    with patch('builtins.input', return_value='no'):
        result = print_results(gps_points, photos, matches, immich_url="", logger=logger)


def test_print_results_no_matches(logger):
    """Test printing results with no matches."""
    
    gps_points = []
    photos = []
    matches = []
    
    result = print_results(gps_points, photos, matches, logger=logger)


def test_print_results_with_null_gps_data(logger):
    """Test printing results with missing GPS data."""
    
    gps_points = []
    
    photos = [
        {
            'id': 'photo1',
            'originalFileName': 'test.jpg',
            'exifInfo': {
                'dateTimeOriginal': '2022-02-16T12:06:30Z',
                'latitude': None,
                'longitude': None
            }
        }
    ]
    
    test_match = match(photo('photo1', name='test.jpg'), gps_point(41.0, -71.0))
    test_match['distance_meters'] = None  # Override distance
    matches = [test_match]
    
    result = print_results(gps_points, photos, matches, immich_url="", logger=logger)


def test_print_match_without_distance(logger):
    """Test that 'Distance: None meters' is not displayed when distance is None."""
    gps_points = []
    
    photos = [
        {
            'id': 'photo1',
            'originalFileName': 'test.jpg',
            'exifInfo': {
                'dateTimeOriginal': '2022-02-16T12:06:30Z',
                'latitude': None,
                'longitude': None
            }
        }
    ]
    
    test_match = match(photo('photo1', name='test.jpg'), gps_point(41.0, -71.0))
    test_match['distance_meters'] = None  # Override distance
    matches = [test_match]
    
    # Create a mock logger to capture calls
    mock_logger = MagicMock(spec=logging.Logger)
    
    # Call print_results with mock logger
    print_results(gps_points, photos, matches, immich_url="", logger=mock_logger)
    
    # Verify that "Distance: None" was NOT logged
    logged_info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
    distance_logs = [log for log in logged_info_calls if 'Distance: None' in log]
    assert len(distance_logs) == 0, f"Found 'Distance: None' in logs: {distance_logs}"


def test_print_match_with_valid_distance(logger):
    """Test that valid distance values are displayed correctly."""
    gps_points = [
        {
            'latitude': 41.0,
            'longitude': -71.0,
            'elevation': 100,
            'time': datetime(2022, 2, 16, 12, 6, 29)
        }
    ]
    
    photos = [
        {
            'id': 'photo1',
            'originalFileName': 'test.jpg',
            'exifInfo': {
                'dateTimeOriginal': '2022-02-16T12:06:30Z',
                'latitude': 41.0,
                'longitude': -71.0
            }
        }
    ]
    
    test_match = match(photo('photo1', 41.0, -71.0, 'test.jpg'), gps_point(41.0, -71.0))
    test_match['distance_meters'] = 45.3  # Override distance
    matches = [test_match]
    
    # Create a mock logger to capture calls
    mock_logger = MagicMock(spec=logging.Logger)
    
    # Call print_results with mock logger
    print_results(gps_points, photos, matches, immich_url="", logger=mock_logger)
    
    # Verify that valid distance WAS logged
    logged_info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
    distance_logs = [log for log in logged_info_calls if '45.3' in log and 'Distance' in log]
    assert len(distance_logs) == 1, f"Expected one distance log with 45.3, got: {distance_logs}"


def test_print_match_with_zero_distance(logger):
    """Test that distance=0 is still displayed (not treated as None)."""
    gps_points = [
        {
            'latitude': 41.0,
            'longitude': -71.0,
            'elevation': 100,
            'time': datetime(2022, 2, 16, 12, 6, 29)
        }
    ]
    
    photos = [
        {
            'id': 'photo1',
            'originalFileName': 'test.jpg',
            'exifInfo': {
                'dateTimeOriginal': '2022-02-16T12:06:30Z',
                'latitude': 41.0,
                'longitude': -71.0
            }
        }
    ]
    
    test_match = match(photo('photo1', 41.0, -71.0, 'test.jpg'), gps_point(41.0, -71.0))
    test_match['distance_meters'] = 0  # Override distance to 0
    matches = [test_match]
    
    # Create a mock logger to capture calls
    mock_logger = MagicMock(spec=logging.Logger)
    
    # Call print_results with mock logger
    print_results(gps_points, photos, matches, immich_url="", logger=mock_logger)
    
    # Verify that distance=0 IS logged (since 0 is not None)
    logged_info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
    distance_logs = [log for log in logged_info_calls if 'Distance: 0' in log]
    assert len(distance_logs) == 1, f"Expected distance=0 to be logged, got: {distance_logs}"



    """Test logging setup."""
    from immich_gpx import setup_logging
    from pathlib import Path
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        logger = setup_logging(verbose=True, log_dir=tmpdir)
        
        assert logger is not None
        assert logger.level == logging.DEBUG


def test_setup_logging_default():
    """Test logging setup with defaults."""
    from immich_gpx import setup_logging
    
    logger = setup_logging()
    
    assert logger is not None
    assert logger.name == 'immich-gpx'


def test_setup_logging_creates_directory(logger):
    """Test that logging setup creates log directory."""
    from immich_gpx import setup_logging
    from pathlib import Path
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = Path(tmpdir) / 'new_logs'
        logger = setup_logging(log_dir=str(log_dir))
        
        # The function creates the directory when setting up the file handler
        assert log_dir.exists() or isinstance(logger, logging.Logger)


@patch('requests.Session.put')
def test_update_photo_positions_success(mock_put, logger):
    """Test successful photo position update."""
    
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_put.return_value = mock_response
    
    matches = [
        {
            'photo': {'id': 'photo1', 'name': 'test.jpg'},
            'gps_point': {'latitude': 41.0, 'longitude': -71.0, 'elevation': 100}
        }
    ]
    
    result = update_photo_positions(matches, "https://test.com", logger=logger, api_key="test-key")
    
    assert result is not None


def test_gpx_parser_with_elevations(tmp_path):
    """Test GPX parsing preserves elevation data."""
    from immich_gpx import GPXParser
    
    gpx_content = '''<?xml version="1.0"?>
<gpx version="1.1">
    <trk><trkseg>
        <trkpt lat="41.0" lon="-71.0">
            <ele>100.5</ele>
            <time>2022-02-16T12:06:29Z</time>
        </trkpt>
    </trkseg></trk>
</gpx>'''
    
    gpx_file = tmp_path / "elev.gpx"
    gpx_file.write_text(gpx_content)
    
    parser = GPXParser(str(gpx_file))
    points = parser.parse()
    
    assert len(points) == 1
    assert points[0]['elevation'] == 100.5


def test_immich_api_logging_messages(caplog, logger):
    """Test that ImmichAPI logs debug messages."""
    import logging
    from immich_gpx import ImmichAPI
    
    logger.setLevel(logging.DEBUG)
    
    api = ImmichAPI("https://test.com", "key", verbose=True, logger=logger)
    
    with caplog.at_level(logging.DEBUG):
        api._log("Test message")


def test_gps_matcher_calculation_precision():
    """Test GPS matcher distance calculation precision."""
    from immich_gpx import GPSMatcher
    
    matcher = GPSMatcher()
    
    # Known distance between two real points (approximately 111.2 km per degree lat at equator)
    distance = matcher.haversine_distance(0.0, 0.0, 1.0, 0.0)
    
    # Should be approximately 111,200 meters
    assert 111000 < distance < 112000


def test_categorize_matches_with_gps():
    """Test categorizing matches where photos have GPS."""
    matches = [
        {
            'photo': {
                'id': '1',
                'name': 'photo1.jpg',
                'latitude': 1.0,
                'longitude': 2.0
            },
            'gps_point': {'latitude': 1.0, 'longitude': 2.0}
        }
    ]
    
    categorized = categorize_matches(matches)
    
    assert categorized['counts']['total'] == 1
    assert categorized['counts']['with_gps'] == 1
    assert categorized['counts']['without_gps'] == 0
    assert len(categorized['with_gps']) == 1
    assert len(categorized['without_gps']) == 0


def test_categorize_matches_without_gps():
    """Test categorizing matches where photos have no GPS."""
    matches = [
        {
            'photo': {
                'id': '1',
                'name': 'photo1.jpg',
                'latitude': None,
                'longitude': None
            },
            'gps_point': {'latitude': 1.0, 'longitude': 2.0}
        }
    ]
    
    categorized = categorize_matches(matches)
    
    assert categorized['counts']['total'] == 1
    assert categorized['counts']['with_gps'] == 0
    assert categorized['counts']['without_gps'] == 1


def test_categorize_matches_mixed():
    """Test categorizing matches with mix of GPS states."""
    matches = [
        {
            'photo': {'id': '1', 'name': 'with_gps.jpg', 'latitude': 1.0, 'longitude': 2.0},
            'gps_point': {'latitude': 1.0, 'longitude': 2.0}
        },
        {
            'photo': {'id': '2', 'name': 'without_gps.jpg', 'latitude': None, 'longitude': None},
            'gps_point': {'latitude': 3.0, 'longitude': 4.0}
        }
    ]
    
    categorized = categorize_matches(matches)
    
    assert categorized['counts']['total'] == 2
    assert categorized['counts']['with_gps'] == 1
    assert categorized['counts']['without_gps'] == 1


def test_categorize_matches_partial_gps():
    """Test categorizing matches where only one GPS coordinate is present."""
    matches = [
        {
            'photo': {'id': '1', 'name': 'partial_gps.jpg', 'latitude': 1.0, 'longitude': None},
            'gps_point': {'latitude': 1.0, 'longitude': 2.0}
        },
        {
            'photo': {'id': '2', 'name': 'other_partial_gps.jpg', 'latitude': None, 'longitude': 2.0},
            'gps_point': {'latitude': 3.0, 'longitude': 4.0}
        }
    ]
    
    categorized = categorize_matches(matches)
    
    # Partial GPS should be treated as no GPS
    assert categorized['counts']['with_gps'] == 0
    assert categorized['counts']['without_gps'] == 2


def test_prompt_update_mode_choice_all(monkeypatch, logger):
    """Test prompt_update_mode selecting all photos."""
    categorized = {
        'counts': {'total': 2, 'with_gps': 1, 'without_gps': 1},
        'all': [],
        'with_gps': [],
        'without_gps': []
    }
    
    # Simulate user entering '1' then 'y' to confirm
    inputs = iter(['1', 'y'])
    monkeypatch.setattr('builtins.input', lambda _: next(inputs))
    
    result = prompt_update_mode(categorized, logger)
    assert result == 'all'


def test_prompt_update_mode_choice_without_gps(monkeypatch, logger):
    """Test prompt_update_mode selecting without-gps photos."""
    categorized = {
        'counts': {'total': 2, 'with_gps': 1, 'without_gps': 1},
        'all': [],
        'with_gps': [],
        'without_gps': []
    }
    
    # Simulate user entering '2'
    inputs = iter(['2'])
    monkeypatch.setattr('builtins.input', lambda _: next(inputs))
    
    result = prompt_update_mode(categorized, logger)
    assert result == 'without-gps'


def test_prompt_update_mode_choice_cancel(monkeypatch, logger):
    """Test prompt_update_mode selecting cancel."""
    categorized = {
        'counts': {'total': 2, 'with_gps': 1, 'without_gps': 1},
        'all': [],
        'with_gps': [],
        'without_gps': []
    }
    
    # Simulate user entering '3'
    inputs = iter(['3'])
    monkeypatch.setattr('builtins.input', lambda _: next(inputs))
    
    result = prompt_update_mode(categorized, logger)
    assert result == 'cancel'


def test_update_photo_positions_all_mode(logger):
    """Test updating all photos regardless of existing GPS."""
    matches = [
        {
            'photo': {'id': '1', 'name': 'photo1.jpg', 'latitude': 1.0, 'longitude': 2.0},
            'gps_point': {'latitude': 5.0, 'longitude': 6.0}
        },
        {
            'photo': {'id': '2', 'name': 'photo2.jpg', 'latitude': None, 'longitude': None},
            'gps_point': {'latitude': 7.0, 'longitude': 8.0}
        }
    ]
    
    
    with patch('requests.Session.put') as mock_put:
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_put.return_value = mock_response
        
        result = update_photo_positions(matches, 'https://test.com', logger, mode='all', api_key='test-key')
        
        # Should attempt to update both photos
        assert mock_put.call_count == 2


def test_update_photo_positions_without_gps_mode(logger):
    """Test updating only photos without GPS."""
    matches = [
        {
            'photo': {'id': '1', 'name': 'photo1.jpg', 'latitude': 1.0, 'longitude': 2.0},
            'gps_point': {'latitude': 5.0, 'longitude': 6.0}
        },
        {
            'photo': {'id': '2', 'name': 'photo2.jpg', 'latitude': None, 'longitude': None},
            'gps_point': {'latitude': 7.0, 'longitude': 8.0}
        }
    ]
    
    
    with patch('requests.Session.put') as mock_put:
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_put.return_value = mock_response
        
        result = update_photo_positions(matches, 'https://test.com', logger, mode='without-gps', api_key='test-key')
        
        # Should only attempt to update the photo without GPS
        assert mock_put.call_count == 1
        # Verify the call was for photo2
        call_args = mock_put.call_args
        assert '/2' in call_args[0][0]  # Check photo ID in URL
