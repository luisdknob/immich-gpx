"""Tests for ImmichAPI class."""
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from datetime import datetime
from immich_gpx import ImmichAPI, ConnectionError, AuthenticationError


@pytest.fixture
def immich_api():
    """Create ImmichAPI instance."""
    return ImmichAPI(
        url="https://photos.example.com",
        api_key="test_key",
        verbose=False,
        verify_ssl=True,
        timeout=10
    )


def test_init(immich_api):
    """Test ImmichAPI initialization."""
    assert immich_api.url == "https://photos.example.com"
    assert immich_api.api_key == "test_key"
    assert immich_api.timeout == 10
    assert immich_api.verify_ssl is True


def test_init_strips_trailing_slash():
    """Test URL trailing slash removal."""
    api = ImmichAPI("https://photos.example.com/", "key")
    assert api.url == "https://photos.example.com"


@patch('immich_gpx.core.immich_client.ImmichAPI._make_request')
def test_connection_success(mock_request, immich_api):
    """Test successful connection."""
    mock_response = Mock()
    mock_response.json.return_value = {'major': 2, 'minor': 2, 'patch': 1}
    mock_response.raise_for_status.return_value = None
    mock_response.status_code = 200
    mock_request.return_value = mock_response
    
    result = immich_api.test_connection()
    
    assert result is True
    mock_request.assert_called_once()


@patch('immich_gpx.core.immich_client.ImmichAPI._make_request')
def test_connection_failure(mock_request, immich_api):
    """Test connection failure."""
    mock_request.side_effect = requests.exceptions.ConnectionError("Failed")
    
    with pytest.raises(ConnectionError):
        immich_api.test_connection()


@patch('immich_gpx.core.immich_client.ImmichAPI._make_request')
def test_get_photos_in_range(mock_request, immich_api, mock_immich_response):
    """Test fetching photos in time range."""
    mock_response = Mock()
    # API returns assets in a dict with items
    mock_response.json.return_value = {'assets': {'items': mock_immich_response, 'nextPage': False}}
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response
    
    start = datetime(2022, 2, 16, 12, 0, 0)
    end = datetime(2022, 2, 16, 13, 0, 0)
    
    with patch.object(immich_api, 'get_photo_exif', return_value={'dateTimeOriginal': '2022-02-16T12:06:30Z'}):
        photos = immich_api.get_photos_in_range(start, end)
    
    assert len(photos) == 2
    assert photos[0]['id'] == 'photo1'


@patch('immich_gpx.core.immich_client.ImmichAPI._make_request')
def test_get_photo_exif(mock_request, immich_api):
    """Test fetching photo EXIF data."""
    mock_response = Mock()
    mock_response.json.return_value = {
        'exifInfo': {
            'dateTimeOriginal': '2022-02-16T12:06:30Z',
            'latitude': 41.0,
            'longitude': -71.0
        }
    }
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response
    
    exif = immich_api.get_photo_exif('photo123')
    
    assert exif is not None
    assert exif['dateTimeOriginal'] == '2022-02-16T12:06:30Z'
    assert exif['latitude'] == 41.0


@patch('immich_gpx.core.immich_client.ImmichAPI._make_request')
def test_get_photo_exif_error(mock_request, immich_api):
    """Test EXIF fetch error handling."""
    mock_request.side_effect = requests.exceptions.RequestException("Error")
    
    exif = immich_api.get_photo_exif('photo123')
    
    assert exif is None


def test_init_with_logger():
    """Test initialization with logger parameter."""
    import logging
    logger = logging.getLogger('test_api_logger')
    
    api = ImmichAPI("https://test.com", "key", logger=logger)
    assert api.logger is logger


@patch('immich_gpx.core.immich_client.ImmichAPI._make_request')
def test_get_photos_empty_response(mock_request, immich_api):
    """Test handling empty photo response."""
    mock_response = Mock()
    mock_response.json.return_value = {'assets': {'items': [], 'nextPage': False}}
    mock_response.raise_for_status.return_value = None
    mock_request.return_value = mock_response
    
    start = datetime(2022, 2, 16, 12, 0, 0)
    end = datetime(2022, 2, 16, 13, 0, 0)
    
    photos = immich_api.get_photos_in_range(start, end)
    
    assert len(photos) == 0


@patch('immich_gpx.core.immich_client.ImmichAPI._make_request')
def test_get_photos_network_error(mock_request, immich_api):
    """Test network error handling."""
    mock_request.side_effect = requests.exceptions.Timeout("Timeout")
    
    start = datetime(2022, 2, 16, 12, 0, 0)
    end = datetime(2022, 2, 16, 13, 0, 0)
    
    with pytest.raises(RuntimeError, match="Error fetching photos"):
        immich_api.get_photos_in_range(start, end)
