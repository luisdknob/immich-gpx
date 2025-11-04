"""Tests for post-update verification in update_photo_positions."""
import pytest
from unittest.mock import Mock, patch
from immich_gpx import update_photo_positions
from tests.builders import photo, gps_point, match
from tests.mocks import MockRequestsSession


@patch('requests.Session')
def test_update_verification_success(mock_session_class, logger):
    """Test successful update with verification."""
    mock_session_class.return_value = MockRequestsSession.with_photo_update('photo1', 41.0, -71.0)
    matches = [match(photo('photo1'), gps_point(41.0, -71.0))]
    
    result = update_photo_positions(matches, "https://test.com", logger=logger, api_key="test-key")
    
    assert result is not None
    assert mock_session_class.return_value.put.called
    assert mock_session_class.return_value.get.called


@patch('requests.Session')
def test_silent_failure_detection(mock_session_class, logger):
    """Test detection of silent API failures (API returns success but doesn't update)."""
    mock_session_class.return_value = MockRequestsSession.with_silent_failure('photo1')
    matches = [match(photo('photo1'), gps_point(41.0, -71.0))]
    
    result = update_photo_positions(matches, "https://test.com", logger=logger, api_key="test-key", enable_xmp=False)
    
    assert result is not None
    assert mock_session_class.return_value.put.called
    assert mock_session_class.return_value.get.called


@patch('builtins.input', return_value='n')  # Mock user declining rescan
@patch('immich_gpx.xmp_writer.XMPWriter.write_xmp_file')
@patch('requests.Session')
def test_xmp_creation_on_verification_failure(mock_session_class, mock_xmp_write, mock_input, logger):
    """Test XMP creation triggered when verification fails."""
    mock_session_class.return_value = MockRequestsSession.with_silent_failure('photo1')
    mock_xmp_write.return_value = '/path/to/test.jpg.xmp'
    
    matches = [match(photo('photo1', name='/path/to/test.jpg'), gps_point(41.0, -71.0))]
    
    result = update_photo_positions(matches, "https://test.com", logger=logger, api_key="test-key", enable_xmp=True)
    
    assert result is not None
    assert mock_xmp_write.called


@patch('requests.Session')
def test_mixed_success_and_failure(mock_session_class, logger):
    """Test handling of mixed successful and failed verifications."""
    session = MockRequestsSession.with_success()
    
    # Mock GET responses - one success, one failure
    get_responses = [
        Mock(
            json=Mock(return_value={'id': 'photo1', 'exifInfo': {'latitude': 41.0, 'longitude': -71.0}}),
            raise_for_status=Mock(return_value=None)
        ),
        Mock(
            json=Mock(return_value={'id': 'photo2', 'exifInfo': {'latitude': None, 'longitude': None}}),
            raise_for_status=Mock(return_value=None)
        ),
    ]
    session.get.side_effect = get_responses
    mock_session_class.return_value = session
    
    matches = [
        match(photo('photo1', name='test1.jpg'), gps_point(41.0, -71.0)),
        match(photo('photo2', name='test2.jpg'), gps_point(42.0, -72.0))
    ]
    
    result = update_photo_positions(matches, "https://test.com", logger=logger, api_key="test-key")
    
    assert result is not None
    assert session.put.call_count == 2
    assert session.get.call_count == 2


@patch('requests.Session')
def test_verification_with_without_gps_mode(mock_session_class, logger):
    """Test verification skips photos with existing GPS in without-gps mode."""
    mock_session_class.return_value = MockRequestsSession.with_photo_update('photo2', 42.0, -72.0)
    
    matches = [
        match(photo('photo1', 40.0, -70.0, name='with_gps.jpg'), gps_point(41.0, -71.0)),
        match(photo('photo2', name='without_gps.jpg'), gps_point(42.0, -72.0))
    ]
    
    result = update_photo_positions(matches, "https://test.com", logger=logger, api_key="test-key", mode='without-gps')
    
    assert result is not None
    assert mock_session_class.return_value.put.call_count == 1


@patch('requests.Session')
def test_api_exception_handling(mock_session_class, logger):
    """Test handling of API exceptions during PUT."""
    mock_session_class.return_value = MockRequestsSession.with_api_failure("Connection failed")
    matches = [match(photo('photo1'), gps_point(41.0, -71.0))]
    
    result = update_photo_positions(matches, "https://test.com", logger=logger, api_key="test-key", enable_xmp=False)
    
    assert result is not None


@patch('requests.Session')
def test_verification_exception_handling(mock_session_class, logger):
    """Test handling of exceptions during verification GET."""
    session = MockRequestsSession.with_success()
    session.get.side_effect = Exception("Verification failed")
    mock_session_class.return_value = session
    
    matches = [match(photo('photo1'), gps_point(41.0, -71.0))]
    
    result = update_photo_positions(matches, "https://test.com", logger=logger, api_key="test-key", enable_xmp=False)
    
    assert result is not None


def test_no_api_key_error(logger):
    """Test error when no API key provided."""
    matches = [match(photo('photo1'), gps_point(41.0, -71.0))]
    
    result = update_photo_positions(matches, "https://test.com", logger=logger, api_key=None)
    
    assert result is None


def test_invalid_mode_error(logger):
    """Test error with invalid update mode."""
    matches = [match(photo('photo1'), gps_point(41.0, -71.0))]
    
    result = update_photo_positions(matches, "https://test.com", logger=logger, api_key="test-key", mode='invalid')
    
    assert result is None
