"""Pytest configuration and fixtures for immich_gpx_linker tests."""
import logging
import pytest
from pathlib import Path
from datetime import datetime, timezone


@pytest.fixture
def sample_gpx_content():
    """Sample GPX file content with 3 trackpoints."""
    return '''<?xml version="1.0"?>
<gpx version="1.1" creator="test">
  <trk>
    <name>Test Track</name>
    <trkseg>
      <trkpt lat="41.0" lon="-71.0">
        <ele>100</ele>
        <time>2022-02-16T12:06:29Z</time>
      </trkpt>
      <trkpt lat="41.05" lon="-71.05">
        <ele>102</ele>
        <time>2022-02-16T12:07:29Z</time>
      </trkpt>
      <trkpt lat="41.1" lon="-71.1">
        <ele>105</ele>
        <time>2022-02-16T12:08:29Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>'''


@pytest.fixture
def empty_gpx_content():
    """Empty GPX file content."""
    return '''<?xml version="1.0"?>
<gpx version="1.1" creator="test">
  <trk>
    <trkseg>
    </trkseg>
  </trk>
</gpx>'''


@pytest.fixture
def gpx_with_waypoints():
    """GPX file with waypoints instead of trackpoints."""
    return '''<?xml version="1.0"?>
<gpx version="1.1" creator="test">
  <wpt lat="41.5" lon="-71.5">
    <time>2022-02-16T12:06:29Z</time>
  </wpt>
</gpx>'''


@pytest.fixture
def tmp_gpx_file(tmp_path, sample_gpx_content):
    """Create a temporary GPX file with sample content."""
    gpx_file = tmp_path / "test.gpx"
    gpx_file.write_text(sample_gpx_content)
    return gpx_file


@pytest.fixture
def sample_photo_data():
    """Sample photo data from Immich API."""
    return {
        'id': 'photo1',
        'originalFileName': 'IMG_001.jpg',
        'type': 'image',
        'mimeType': 'image/jpeg',
        'exifInfo': {
            'make': 'Apple',
            'model': 'iPhone 13',
            'exifImageWidth': 1920,
            'exifImageHeight': 1080,
            'orientation': '1',
            'dateTimeOriginal': '2022-02-16T12:06:30+00:00',
            'modifyDate': '2022-02-16T12:06:30+00:00',
            'timeZone': 'UTC',
            'latitude': None,
            'longitude': None,
            'altitude': None
        }
    }


@pytest.fixture
def mock_immich_response():
    """Mock Immich API response for photo query."""
    return [
        {
            'id': 'photo1',
            'originalFileName': 'test1.jpg',
            'type': 'image',
            'mimeType': 'image/jpeg',
            'exifInfo': {
                'dateTimeOriginal': '2022-02-16T12:06:30+00:00',
                'latitude': None,
                'longitude': None
            }
        },
        {
            'id': 'photo2',
            'originalFileName': 'test2.jpg',
            'type': 'image',
            'mimeType': 'image/jpeg',
            'exifInfo': {
                'dateTimeOriginal': '2022-02-16T12:07:30+00:00',
                'latitude': None,
                'longitude': None
            }
        }
    ]


@pytest.fixture
def gps_points():
    """Sample GPS points for matching tests."""
    return [
        {
            'latitude': 41.0,
            'longitude': -71.0,
            'elevation': 100,
            'time': datetime(2022, 2, 16, 12, 6, 29, tzinfo=timezone.utc)
        },
        {
            'latitude': 41.05,
            'longitude': -71.05,
            'elevation': 102,
            'time': datetime(2022, 2, 16, 12, 7, 29, tzinfo=timezone.utc)
        },
        {
            'latitude': 41.1,
            'longitude': -71.1,
            'elevation': 105,
            'time': datetime(2022, 2, 16, 12, 8, 29, tzinfo=timezone.utc)
        }
    ]


def create_mock_response(json_data):
    """
    Create a proper mock response object that handles urlparse and other operations.
    
    This factory function creates a Mock that properly supports:
    - json() method
    - raise_for_status() method
    - response.history attribute
    - Proper string representation for URL parsing
    """
    from unittest.mock import Mock, PropertyMock
    
    response = Mock()
    response.json = Mock(return_value=json_data)
    response.raise_for_status = Mock()
    response.history = []
    response.status_code = 200
    response.text = str(json_data)
    
    # Ensure the mock can be used in string operations
    response.__str__ = Mock(return_value="<Mock Response>")
    response.__repr__ = Mock(return_value="<Mock Response>")
    
    return response


@pytest.fixture
def create_api_mock_response():
    """Fixture providing the mock response factory."""
    return create_mock_response


# Centralized fixtures from various test files

@pytest.fixture
def logger():
    """Test logger instance."""
    return logging.getLogger("test")


@pytest.fixture
def temp_rollback_dir(tmp_path):
    """Temporary rollback directory for rollback tests."""
    rollback_dir = tmp_path / "rollback"
    return rollback_dir


@pytest.fixture
def rollback_manager(temp_rollback_dir, logger):
    """RollbackManager instance with temp directory."""
    from immich_gpx.rollback import RollbackManager
    return RollbackManager(rollback_dir=temp_rollback_dir, logger=logger)


@pytest.fixture
def temp_xmp_dir(tmp_path):
    """Temporary XMP output directory for XMP tests."""
    xmp_dir = tmp_path / "xmp"
    return xmp_dir


@pytest.fixture
def xmp_writer(temp_xmp_dir, logger):
    """XMPWriter instance with temp directory."""
    from immich_gpx.xmp_writer import XMPWriter
    return XMPWriter(output_directory=temp_xmp_dir, logger=logger)
