"""Pytest configuration and fixtures for immich_gpx_linker tests."""
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
