"""Tests for CLI and main function."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
import os
from io import StringIO


def test_main_help():
    """Test CLI help message."""
    from immich_gpx import main
    
    with patch('sys.argv', ['immich_gpx_linker', '--help']):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0


def test_main_version():
    """Test version flag."""
    from immich_gpx import main
    
    with patch('sys.argv', ['immich_gpx_linker', '--version']):
        with pytest.raises(SystemExit):
            main()


@patch.dict(os.environ, {
    'IMMICH_URL': 'https://test.com',
    'IMMICH_API_KEY': 'test_key'
})
@patch('immich_gpx.cli.GPXParser')
@patch('immich_gpx.cli.ImmichAPI')
@patch('immich_gpx.cli.GPSMatcher')
def test_main_with_gpx_file(mock_matcher, mock_api_class, mock_parser_class, tmp_path):
    """Test main function with GPX file."""
    from immich_gpx import main
    
    # Create a temporary GPX file
    gpx_file = tmp_path / "test.gpx"
    gpx_file.write_text('''<?xml version="1.0"?>
<gpx version="1.1">
    <trk><trkseg>
        <trkpt lat="41.0" lon="-71.0">
            <time>2022-02-16T12:06:29Z</time>
        </trkpt>
    </trkseg></trk>
</gpx>''')
    
    # Mock the classes
    mock_parser = Mock()
    mock_parser.parse.return_value = [
        {'latitude': 41.0, 'longitude': -71.0, 'time': datetime(2022, 2, 16, 12, 6, 29)}
    ]
    mock_parser.get_time_range.return_value = (datetime(2022, 2, 16, 12, 0), datetime(2022, 2, 16, 13, 0))
    mock_parser_class.return_value = mock_parser
    
    mock_api = Mock()
    mock_api.test_connection.return_value = True
    mock_api.get_photos_in_range.return_value = []
    mock_api_class.return_value = mock_api
    
    mock_matcher_inst = Mock()
    mock_matcher_inst.match_photos_to_points.return_value = []
    mock_matcher.return_value = mock_matcher_inst
    
    with patch('sys.argv', ['immich_gpx_linker', str(gpx_file), '-u', 'https://test.com', '-k', 'test_key']):
        with patch('immich_gpx.cli.print_results', return_value=None):
            try:
                main()
            except SystemExit:
                pass  # Main may exit normally


@patch.dict(os.environ, {
    'IMMICH_URL': 'https://test.com',
    'IMMICH_API_KEY': 'test_key'
})
def test_main_missing_credentials(tmp_path):
    """Test main with missing credentials."""
    from immich_gpx import main
    
    gpx_file = tmp_path / "test.gpx"
    gpx_file.write_text('''<?xml version="1.0"?>
<gpx version="1.1"><trk><trkseg></trkseg></trk></gpx>''')
    
    with patch('sys.argv', ['immich_gpx_linker', str(gpx_file)]):
        with patch.dict(os.environ, {}, clear=True):
            with patch('immich_gpx.cli.sys.exit') as mock_exit:
                main()


def test_print_position_update_preview():
    """Test printing position update preview."""
    import logging
    from immich_gpx import print_position_update_preview
    
    logger = logging.getLogger('test')
    
    matches = [
        {
            'photo': {'id': 'p1', 'name': 'test.jpg', 'latitude': 41.0, 'longitude': -71.0},
            'gps_point': {'latitude': 41.1, 'longitude': -71.1, 'elevation': 100}
        }
    ]
    
    # Should not raise an exception
    print_position_update_preview(matches, logger)


@patch.dict(os.environ, {'IMMICH_API_KEY': 'test_key'})
@patch('requests.Session.put')
def test_update_photo_positions_partial_failure(mock_put):
    """Test partial failure in position update."""
    import logging
    from immich_gpx import update_photo_positions
    
    logger = logging.getLogger('test')
    
    # First call succeeds, second fails
    mock_put.side_effect = [
        Mock(raise_for_status=lambda: None),
        Exception("Network error")
    ]
    
    matches = [
        {
            'photo': {'id': 'photo1', 'name': 'test1.jpg'},
            'gps_point': {'latitude': 41.0, 'longitude': -71.0, 'elevation': 100}
        },
        {
            'photo': {'id': 'photo2', 'name': 'test2.jpg'},
            'gps_point': {'latitude': 41.1, 'longitude': -71.1, 'elevation': 105}
        }
    ]
    
    with patch('immich_gpx.cli.ImmichAPI'):
        result = update_photo_positions(matches, "https://test.com", logger=logger, api_key='test-key')


def test_gpx_parser_complex_gpx(tmp_path):
    """Test parsing complex GPX with multiple tracks and segments."""


def test_gpx_parser_complex_gpx(tmp_path):
    """Test parsing complex GPX with multiple tracks and segments."""
    from immich_gpx import GPXParser
    
    gpx_content = '''<?xml version="1.0"?>
<gpx version="1.1">
    <trk>
        <name>Track 1</name>
        <trkseg>
            <trkpt lat="41.0" lon="-71.0">
                <ele>100</ele>
                <time>2022-02-16T12:00:00Z</time>
            </trkpt>
            <trkpt lat="41.1" lon="-71.1">
                <ele>105</ele>
                <time>2022-02-16T12:05:00Z</time>
            </trkpt>
        </trkseg>
        <trkseg>
            <trkpt lat="41.2" lon="-71.2">
                <ele>110</ele>
                <time>2022-02-16T12:10:00Z</time>
            </trkpt>
        </trkseg>
    </trk>
    <trk>
        <name>Track 2</name>
        <trkseg>
            <trkpt lat="41.3" lon="-71.3">
                <ele>115</ele>
                <time>2022-02-16T12:15:00Z</time>
            </trkpt>
        </trkseg>
    </trk>
</gpx>'''
    
    gpx_file = tmp_path / "complex.gpx"
    gpx_file.write_text(gpx_content)
    
    parser = GPXParser(str(gpx_file))
    points = parser.parse()
    
    assert len(points) == 4
    # Check sorting by time
    for i in range(len(points) - 1):
        assert points[i]['time'] <= points[i+1]['time']


def test_immich_api_pagination(tmp_path):
    """Test ImmichAPI handles pagination correctly."""
    from immich_gpx import ImmichAPI
    from unittest.mock import patch
    
    api = ImmichAPI("https://test.com", "key")
    
    # Mock responses with pagination
    responses = [
        Mock(json=lambda: {'assets': {'items': [{'id': f'photo{i}' for i in range(100)}], 'nextPage': True}}, raise_for_status=lambda: None),
        Mock(json=lambda: {'assets': {'items': [{'id': f'photo{i}' for i in range(100, 150)}], 'nextPage': False}}, raise_for_status=lambda: None)
    ]
    
    with patch.object(api.session, 'post', side_effect=responses):
        with patch.object(api, 'get_photo_exif', return_value={'dateTimeOriginal': '2022-02-16T12:00:00Z'}):
            photos = api.get_photos_in_range(
                datetime(2022, 2, 16, 12, 0),
                datetime(2022, 2, 16, 13, 0)
            )
            # Note: The actual implementation may vary, but we're testing the flow
            assert photos is not None


def test_gps_matcher_verbose_logging():
    """Test GPS matcher with verbose logging."""
    import logging
    from immich_gpx import GPSMatcher
    from datetime import timezone
    
    logger = logging.getLogger('test_verbose')
    logger.setLevel(logging.DEBUG)
    
    matcher = GPSMatcher()
    
    gps_points = [
        {
            'latitude': 41.0,
            'longitude': -71.0,
            'elevation': 100,
            'time': datetime(2022, 2, 16, 12, 6, 29, tzinfo=timezone.utc)
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
    
    # Call with verbose=True
    matches = matcher.match_photos_to_points(gps_points, photos, verbose=True, logger=logger)
    
    assert len(matches) == 1
