"""Tests for post-update verification in update_photo_positions."""
import pytest
from unittest.mock import Mock, patch, MagicMock, call
import logging
from immich_gpx import update_photo_positions


@patch('requests.Session.get')
@patch('requests.Session.put')
def test_update_verification_success(mock_put, mock_get):
    """Test successful update with verification."""
    logger = logging.getLogger('test')
    
    # Mock successful PUT response
    mock_put_response = Mock()
    mock_put_response.raise_for_status.return_value = None
    mock_put.return_value = mock_put_response
    
    # Mock GET response with updated coordinates
    mock_get_response = Mock()
    mock_get_response.raise_for_status.return_value = None
    mock_get_response.json.return_value = {
        'id': 'photo1',
        'exifInfo': {
            'latitude': 41.0,
            'longitude': -71.0
        }
    }
    mock_get.return_value = mock_get_response
    
    matches = [
        {
            'photo': {'id': 'photo1', 'name': 'test.jpg', 'latitude': None, 'longitude': None},
            'gps_point': {'latitude': 41.0, 'longitude': -71.0, 'elevation': 100}
        }
    ]
    
    result = update_photo_positions(matches, "https://test.com", logger=logger, api_key="test-key")
    
    assert result is not None
    # Verify PUT was called (update)
    assert mock_put.called
    # Verify GET was called (verification)
    assert mock_get.called


@patch('requests.Session.get')
@patch('requests.Session.put')
def test_silent_failure_detection(mock_put, mock_get):
    """Test detection of silent API failures (API returns success but doesn't update)."""
    logger = logging.getLogger('test')
    
    # Mock successful PUT response
    mock_put_response = Mock()
    mock_put_response.raise_for_status.return_value = None
    mock_put.return_value = mock_put_response
    
    # Mock GET response with UNCHANGED coordinates (silent failure!)
    mock_get_response = Mock()
    mock_get_response.raise_for_status.return_value = None
    mock_get_response.json.return_value = {
        'id': 'photo1',
        'exifInfo': {
            'latitude': None,  # Coordinates NOT updated despite successful PUT
            'longitude': None
        }
    }
    mock_get.return_value = mock_get_response
    
    matches = [
        {
            'photo': {'id': 'photo1', 'name': 'test.jpg', 'latitude': None, 'longitude': None},
            'gps_point': {'latitude': 41.0, 'longitude': -71.0, 'elevation': 100}
        }
    ]
    
    result = update_photo_positions(matches, "https://test.com", logger=logger, api_key="test-key", enable_xmp=False)
    
    assert result is not None
    # Both PUT and GET should be called
    assert mock_put.called
    assert mock_get.called


@patch('requests.Session.get')
@patch('requests.Session.put')
@patch('immich_gpx.xmp_writer.XMPWriter.write_xmp_file')
def test_xmp_creation_on_verification_failure(mock_xmp_write, mock_put, mock_get):
    """Test XMP creation triggered when verification fails."""
    logger = logging.getLogger('test')
    
    # Mock successful PUT response
    mock_put_response = Mock()
    mock_put_response.raise_for_status.return_value = None
    mock_put.return_value = mock_put_response
    
    # Mock GET response showing silent failure
    mock_get_response = Mock()
    mock_get_response.raise_for_status.return_value = None
    mock_get_response.json.return_value = {
        'id': 'photo1',
        'exifInfo': {
            'latitude': None,
            'longitude': None
        }
    }
    mock_get.return_value = mock_get_response
    
    # Mock XMP file creation
    mock_xmp_write.return_value = '/path/to/test.jpg.xmp'
    
    matches = [
        {
            'photo': {'id': 'photo1', 'name': '/path/to/test.jpg', 'latitude': None, 'longitude': None},
            'gps_point': {'latitude': 41.0, 'longitude': -71.0, 'elevation': 100}
        }
    ]
    
    with patch('builtins.input', return_value='n'):  # Skip rescan prompt
        result = update_photo_positions(
            matches, 
            "https://test.com", 
            logger=logger, 
            api_key="test-key", 
            enable_xmp=True
        )
    
    assert result is not None
    # XMP file creation should be called for the failed photo
    assert mock_xmp_write.called


@patch('requests.Session.get')
@patch('requests.Session.put')
def test_mixed_success_and_failure(mock_put, mock_get):
    """Test handling of mixed successful and failed verifications."""
    logger = logging.getLogger('test')
    
    # Mock successful PUT response
    mock_put_response = Mock()
    mock_put_response.raise_for_status.return_value = None
    mock_put.return_value = mock_put_response
    
    # Mock GET responses - one success, one failure
    mock_get_responses = [
        # First photo - successful verification
        Mock(
            json=Mock(return_value={
                'id': 'photo1',
                'exifInfo': {'latitude': 41.0, 'longitude': -71.0}
            }),
            raise_for_status=Mock(return_value=None)
        ),
        # Second photo - silent failure
        Mock(
            json=Mock(return_value={
                'id': 'photo2',
                'exifInfo': {'latitude': None, 'longitude': None}
            }),
            raise_for_status=Mock(return_value=None)
        ),
    ]
    mock_get.side_effect = mock_get_responses
    
    matches = [
        {
            'photo': {'id': 'photo1', 'name': 'test1.jpg', 'latitude': None, 'longitude': None},
            'gps_point': {'latitude': 41.0, 'longitude': -71.0, 'elevation': 100}
        },
        {
            'photo': {'id': 'photo2', 'name': 'test2.jpg', 'latitude': None, 'longitude': None},
            'gps_point': {'latitude': 42.0, 'longitude': -72.0, 'elevation': 200}
        }
    ]
    
    result = update_photo_positions(matches, "https://test.com", logger=logger, api_key="test-key")
    
    assert result is not None
    # Two PUTs for both photos
    assert mock_put.call_count == 2
    # Two GETs for verification
    assert mock_get.call_count == 2


@patch('requests.Session.get')
@patch('requests.Session.put')
def test_verification_with_without_gps_mode(mock_put, mock_get):
    """Test verification skips photos with existing GPS in without-gps mode."""
    logger = logging.getLogger('test')
    
    mock_put_response = Mock()
    mock_put_response.raise_for_status.return_value = None
    mock_put.return_value = mock_put_response
    
    mock_get_response = Mock()
    mock_get_response.raise_for_status.return_value = None
    mock_get_response.json.return_value = {
        'id': 'photo1',
        'exifInfo': {'latitude': 41.0, 'longitude': -71.0}
    }
    mock_get.return_value = mock_get_response
    
    matches = [
        {
            'photo': {'id': 'photo1', 'name': 'with_gps.jpg', 'latitude': 40.0, 'longitude': -70.0},
            'gps_point': {'latitude': 41.0, 'longitude': -71.0, 'elevation': 100}
        },
        {
            'photo': {'id': 'photo2', 'name': 'without_gps.jpg', 'latitude': None, 'longitude': None},
            'gps_point': {'latitude': 42.0, 'longitude': -72.0, 'elevation': 200}
        }
    ]
    
    result = update_photo_positions(
        matches, 
        "https://test.com", 
        logger=logger, 
        api_key="test-key",
        mode='without-gps'
    )
    
    assert result is not None
    # Only one PUT (for photo without GPS)
    assert mock_put.call_count == 1
    # Only one GET (for verification of photo without GPS)
    assert mock_get.call_count == 1


@patch('requests.Session.put')
def test_api_exception_handling(mock_put):
    """Test handling of API exceptions during PUT."""
    logger = logging.getLogger('test')
    
    # Mock exception on PUT
    import requests
    mock_put.side_effect = requests.exceptions.ConnectionError("Connection failed")
    
    matches = [
        {
            'photo': {'id': 'photo1', 'name': 'test.jpg', 'latitude': None, 'longitude': None},
            'gps_point': {'latitude': 41.0, 'longitude': -71.0, 'elevation': 100}
        }
    ]
    
    result = update_photo_positions(matches, "https://test.com", logger=logger, api_key="test-key", enable_xmp=False)
    
    assert result is not None


@patch('requests.Session.get')
@patch('requests.Session.put')
def test_verification_exception_handling(mock_put, mock_get):
    """Test handling of exceptions during verification."""
    logger = logging.getLogger('test')
    
    mock_put_response = Mock()
    mock_put_response.raise_for_status.return_value = None
    mock_put.return_value = mock_put_response
    
    # Mock exception on GET
    import requests
    mock_get.side_effect = requests.exceptions.Timeout("Verification timeout")
    
    matches = [
        {
            'photo': {'id': 'photo1', 'name': 'test.jpg', 'latitude': None, 'longitude': None},
            'gps_point': {'latitude': 41.0, 'longitude': -71.0, 'elevation': 100}
        }
    ]
    
    result = update_photo_positions(matches, "https://test.com", logger=logger, api_key="test-key", enable_xmp=False)
    
    assert result is not None


@patch('requests.Session.get')
@patch('requests.Session.put')
def test_no_api_key_error(mock_put, mock_get):
    """Test that missing API key returns None."""
    logger = logging.getLogger('test')
    
    matches = [
        {
            'photo': {'id': 'photo1', 'name': 'test.jpg', 'latitude': None, 'longitude': None},
            'gps_point': {'latitude': 41.0, 'longitude': -71.0, 'elevation': 100}
        }
    ]
    
    result = update_photo_positions(matches, "https://test.com", logger=logger, api_key=None)
    
    assert result is None
    # No API calls should be made
    assert not mock_put.called
    assert not mock_get.called


@patch('requests.Session.get')
@patch('requests.Session.put')
def test_invalid_mode_error(mock_put, mock_get):
    """Test that invalid mode returns None."""
    logger = logging.getLogger('test')
    
    matches = [
        {
            'photo': {'id': 'photo1', 'name': 'test.jpg', 'latitude': None, 'longitude': None},
            'gps_point': {'latitude': 41.0, 'longitude': -71.0, 'elevation': 100}
        }
    ]
    
    result = update_photo_positions(
        matches, 
        "https://test.com", 
        logger=logger, 
        api_key="test-key",
        mode='invalid-mode'
    )
    
    assert result is None
    # No API calls should be made
    assert not mock_put.called
    assert not mock_get.called
