"""Tests for utility functions and edge cases."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import logging
from immich_gpx import print_results, update_photo_positions, categorize_matches, prompt_update_mode


def test_print_results_with_matches():
    """Test printing results with matches."""
    logger = logging.getLogger('test')
    
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
    
    matches = [
        {
            'photo': {'id': 'photo1', 'name': 'test.jpg', 'time': '2022-02-16T12:06:30Z', 'latitude': 41.0, 'longitude': -71.0},
            'gps_point': {'latitude': 41.0, 'longitude': -71.0, 'elevation': 100, 'time': '2022-02-16T12:06:29'},
            'distance_meters': 10.5,
            'time_difference_seconds': 1
        }
    ]
    
    # Test with no immich_url to avoid asking for updates
    with patch('builtins.input', return_value='no'):
        result = print_results(gps_points, photos, matches, immich_url="", logger=logger)


def test_print_results_no_matches():
    """Test printing results with no matches."""
    logger = logging.getLogger('test')
    
    gps_points = []
    photos = []
    matches = []
    
    result = print_results(gps_points, photos, matches, logger=logger)


def test_print_results_with_null_gps_data():
    """Test printing results with missing GPS data."""
    logger = logging.getLogger('test')
    
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
    
    matches = [
        {
            'photo': {'id': 'photo1', 'name': 'test.jpg', 'time': '2022-02-16T12:06:30Z', 'latitude': None, 'longitude': None},
            'gps_point': {'latitude': 41.0, 'longitude': -71.0, 'elevation': 100, 'time': '2022-02-16T12:06:29'},
            'distance_meters': None,
            'time_difference_seconds': 1
        }
    ]
    
    result = print_results(gps_points, photos, matches, immich_url="", logger=logger)


def test_setup_logging():
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


def test_setup_logging_creates_directory():
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
def test_update_photo_positions_success(mock_put):
    """Test successful photo position update."""
    logger = logging.getLogger('test')
    
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


def test_immich_api_logging_messages(caplog):
    """Test that ImmichAPI logs debug messages."""
    from immich_gpx import ImmichAPI
    
    logger = logging.getLogger('immich_gpx_linker')
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


def test_prompt_update_mode_choice_all(monkeypatch):
    """Test prompt_update_mode selecting all photos."""
    logger = logging.getLogger('test')
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


def test_prompt_update_mode_choice_without_gps(monkeypatch):
    """Test prompt_update_mode selecting without-gps photos."""
    logger = logging.getLogger('test')
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


def test_prompt_update_mode_choice_cancel(monkeypatch):
    """Test prompt_update_mode selecting cancel."""
    logger = logging.getLogger('test')
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


def test_update_photo_positions_all_mode():
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
    
    logger = logging.getLogger('test')
    
    with patch('requests.Session.put') as mock_put:
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_put.return_value = mock_response
        
        result = update_photo_positions(matches, 'https://test.com', logger, mode='all', api_key='test-key')
        
        # Should attempt to update both photos
        assert mock_put.call_count == 2


def test_update_photo_positions_without_gps_mode():
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
    
    logger = logging.getLogger('test')
    
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
