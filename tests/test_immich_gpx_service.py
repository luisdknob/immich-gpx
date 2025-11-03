"""Tests for ImmichGPXService and microservice integration."""
import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from immich_gpx import ImmichGPXService, ProcessResult


def test_immich_gpx_service_initialization():
    """Test service initialization."""
    service = ImmichGPXService(
        immich_url="https://test.com",
        immich_api_key="test_key_1234567890"
    )
    
    assert service.immich_url == "https://test.com"
    assert service.immich_api_key == "test_key_1234567890"
    assert service.threshold == 60
    assert service.timeout == 10
    assert service.verify_ssl is True


def test_immich_gpx_service_custom_params():
    """Test service with custom parameters."""
    service = ImmichGPXService(
        immich_url="http://localhost:2283",
        immich_api_key="custom_key_1234567890",
        threshold=120,
        timeout=30,
        verify_ssl=False
    )
    
    assert service.threshold == 120
    assert service.timeout == 30
    assert service.verify_ssl is False


def test_immich_gpx_service_custom_logger():
    """Test service with custom logger."""
    logger = logging.getLogger('test')
    service = ImmichGPXService(
        immich_url="https://test.com",
        immich_api_key="test_key_1234567890",
        logger=logger
    )
    
    assert service.logger is logger


def test_process_result_initialization():
    """Test ProcessResult initialization."""
    result = ProcessResult(
        matches=[],
        gps_points_count=50,
        photos_count=100,
        matched_count=25,
        with_gps_count=10,
        without_gps_count=15
    )
    
    assert result.matched_count == 25
    assert result.with_gps_count == 10
    assert result.without_gps_count == 15


def test_process_result_repr():
    """Test ProcessResult string representation."""
    result = ProcessResult(
        matches=[],
        gps_points_count=50,
        photos_count=100,
        matched_count=25,
        with_gps_count=10,
        without_gps_count=15
    )
    
    repr_str = repr(result)
    assert "gps_points=50" in repr_str
    assert "photos=100" in repr_str
    assert "matched=25" in repr_str


@patch('immich_gpx.core.service.ImmichAPI')
def test_service_test_connection_success(mock_api_class):
    """Test successful connection test."""
    mock_api = Mock()
    mock_api_class.return_value = mock_api
    
    service = ImmichGPXService(
        immich_url="https://test.com",
        immich_api_key="test_key_1234567890"
    )
    
    result = service.test_connection()
    assert result is True
    mock_api.test_connection.assert_called_once()


@patch('immich_gpx.core.service.ImmichAPI')
def test_service_test_connection_failure(mock_api_class):
    """Test failed connection test."""
    from immich_gpx import ConnectionError
    
    mock_api = Mock()
    mock_api.test_connection.side_effect = ConnectionError("Connection failed")
    mock_api_class.return_value = mock_api
    
    service = ImmichGPXService(
        immich_url="https://test.com",
        immich_api_key="test_key_1234567890"
    )
    
    with pytest.raises(ConnectionError):
        service.test_connection()


@patch('immich_gpx.core.service.ImmichAPI')
@patch('immich_gpx.core.service.GPXParser')
@patch('immich_gpx.core.service.GPSMatcher')
def test_service_process_gpx_file(mock_matcher_class, mock_parser_class, mock_api_class):
    """Test GPX file processing."""
    from datetime import datetime
    
    # Setup mocks
    mock_parser = Mock()
    mock_parser_class.return_value = mock_parser
    mock_parser.parse.return_value = [
        {'latitude': 1.0, 'longitude': 2.0, 'time': datetime(2022, 2, 16, 12, 6, 29)}
    ]
    mock_parser.get_time_range.return_value = (
        datetime(2022, 2, 16, 12, 6, 29),
        datetime(2022, 2, 16, 12, 6, 29)
    )
    
    mock_api = Mock()
    mock_api_class.return_value = mock_api
    mock_api.get_photos_in_range.return_value = [
        {
            'id': 'photo1',
            'originalFileName': 'test.jpg',
            'exifInfo': {'dateTimeOriginal': '2022-02-16T12:06:30Z', 'latitude': None, 'longitude': None}
        }
    ]
    
    mock_matcher = Mock()
    mock_matcher_class.return_value = mock_matcher
    mock_matcher.match_photos_to_points.return_value = [
        {
            'photo': {'id': 'photo1', 'name': 'test.jpg', 'latitude': None, 'longitude': None},
            'gps_point': {'latitude': 1.0, 'longitude': 2.0}
        }
    ]
    
    service = ImmichGPXService(
        immich_url="https://test.com",
        immich_api_key="test_key_1234567890"
    )
    
    with patch('pathlib.Path.exists', return_value=True):
        result = service.process_gpx_file('test.gpx')
    
    assert isinstance(result, ProcessResult)
    assert result.gps_points_count == 1
    assert result.matched_count == 1
    assert result.without_gps_count == 1


@patch('immich_gpx.core.service.ImmichAPI')
def test_service_update_photos_all_mode(mock_api_class):
    """Test updating all photos."""
    mock_api = Mock()
    mock_api_class.return_value = mock_api
    mock_api.update_photo_exif.return_value = True
    
    service = ImmichGPXService(
        immich_url="https://test.com",
        immich_api_key="test_key_1234567890"
    )
    
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
    
    result = service.update_photos(matches, mode='all')
    
    assert result['total'] == 2
    assert result['updated_count'] == 2
    assert result['skipped_count'] == 0
    assert result['failed_count'] == 0


@patch('immich_gpx.core.service.ImmichAPI')
def test_service_update_photos_without_gps_mode(mock_api_class):
    """Test updating only photos without GPS."""
    mock_api = Mock()
    mock_api_class.return_value = mock_api
    mock_api.update_photo_exif.return_value = True
    
    service = ImmichGPXService(
        immich_url="https://test.com",
        immich_api_key="test_key_1234567890"
    )
    
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
    
    result = service.update_photos(matches, mode='without-gps')
    
    assert result['total'] == 2
    assert result['updated_count'] == 1
    assert result['skipped_count'] == 1
    assert result['failed_count'] == 0


@patch('immich_gpx.core.service.ImmichAPI')
def test_service_update_photos_invalid_mode(mock_api_class):
    """Test invalid update mode."""
    mock_api = Mock()
    mock_api_class.return_value = mock_api
    
    service = ImmichGPXService(
        immich_url="https://test.com",
        immich_api_key="test_key_1234567890"
    )
    
    with pytest.raises(ValueError, match="Invalid update mode"):
        service.update_photos([], mode='invalid')
