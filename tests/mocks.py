"""
Standardized mock patterns for HTTP requests and API responses.

MockRequestsSession provides reusable patterns for common API mocking scenarios.
"""

from unittest.mock import Mock, MagicMock
from typing import Dict, Optional, List


class MockRequestsSession:
    """Standard mock for requests.Session with common patterns."""
    
    @staticmethod
    def with_success():
        """
        Mock successful API calls (generic).
        
        Returns:
            MagicMock session with successful responses
        """
        session = MagicMock()
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {}
        response.status_code = 200
        session.put.return_value = response
        session.get.return_value = response
        session.post.return_value = response
        session.request.return_value = response
        return session
    
    @staticmethod
    def with_photo_update(photo_id: str, lat: float, lon: float):
        """
        Mock successful photo GPS update with verification.
        
        Simulates:
        1. PUT to update coordinates (success)
        2. GET to verify coordinates (returns updated values)
        
        Args:
            photo_id: Photo ID being updated
            lat: Latitude coordinate
            lon: Longitude coordinate
        
        Returns:
            MagicMock session
        """
        session = MagicMock()
        
        # PUT response (update operation)
        put_response = Mock()
        put_response.raise_for_status.return_value = None
        put_response.status_code = 200
        session.put.return_value = put_response
        
        # GET response (verification operation)
        get_response = Mock()
        get_response.raise_for_status.return_value = None
        get_response.status_code = 200
        get_response.json.return_value = {
            'id': photo_id,
            'exifInfo': {
                'latitude': lat,
                'longitude': lon
            }
        }
        session.get.return_value = get_response
        
        return session
    
    @staticmethod
    def with_silent_failure(photo_id: str):
        """
        Mock silent API failure (PUT succeeds but coordinates don't persist).
        
        Useful for testing read-only library detection.
        
        Args:
            photo_id: Photo ID
        
        Returns:
            MagicMock session
        """
        session = MagicMock()
        
        # PUT appears successful
        put_response = Mock()
        put_response.raise_for_status.return_value = None
        put_response.status_code = 200
        session.put.return_value = put_response
        
        # GET shows coordinates NOT updated
        get_response = Mock()
        get_response.raise_for_status.return_value = None
        get_response.status_code = 200
        get_response.json.return_value = {
            'id': photo_id,
            'exifInfo': {
                'latitude': None,
                'longitude': None
            }
        }
        session.get.return_value = get_response
        
        return session
    
    @staticmethod
    def with_api_failure(error_message: str = "API Error"):
        """
        Mock API failure (connection/timeout error).
        
        Args:
            error_message: Error message
        
        Returns:
            MagicMock session that raises exception
        """
        session = MagicMock()
        session.put.side_effect = Exception(error_message)
        session.get.side_effect = Exception(error_message)
        session.post.side_effect = Exception(error_message)
        return session
    
    @staticmethod
    def with_http_redirect(from_url: str, to_url: str):
        """
        Mock HTTP redirect (e.g., HTTP → HTTPS).
        
        Args:
            from_url: Original URL
            to_url: Redirect target URL
        
        Returns:
            MagicMock session with redirect history
        """
        session = MagicMock()
        
        response = Mock()
        response.raise_for_status.return_value = None
        response.status_code = 200
        response.url = to_url
        
        # Add redirect history
        redirect_response = Mock()
        redirect_response.url = from_url
        redirect_response.status_code = 301
        response.history = [redirect_response]
        
        session.get.return_value = response
        session.request.return_value = response
        
        return session


def mock_api_response(data: Dict, status_code: int = 200) -> Mock:
    """
    Create a mock API response.
    
    Args:
        data: Response JSON data
        status_code: HTTP status code
    
    Returns:
        Mock response object
    
    Examples:
        >>> response = mock_api_response({'id': 'photo1'})
        >>> response = mock_api_response({'error': 'Not found'}, 404)
    """
    response = Mock()
    response.json.return_value = data
    response.status_code = status_code
    response.raise_for_status.return_value = None if status_code < 400 else Exception(f"HTTP {status_code}")
    return response


def mock_immich_photos(count: int = 3) -> List[Dict]:
    """
    Create mock Immich photo API responses.
    
    Args:
        count: Number of photos to generate
    
    Returns:
        List of photo dicts
    
    Examples:
        >>> photos = mock_immich_photos(5)
        >>> len(photos)
        5
    """
    photos = []
    for i in range(1, count + 1):
        photos.append({
            'id': f'photo{i}',
            'originalFileName': f'IMG_{i:03d}.jpg',
            'type': 'image',
            'mimeType': 'image/jpeg',
            'exifInfo': {
                'dateTimeOriginal': f'2022-02-16T12:0{i}:30+00:00',
                'latitude': None,
                'longitude': None
            }
        })
    return photos
