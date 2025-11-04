"""
Test HTTP/HTTPS redirect handling in ImmichAPI.

Verifies that when a server redirects from HTTP to HTTPS,
the client correctly updates its base URL for subsequent requests.
"""

import pytest
import requests
from unittest.mock import Mock, patch, MagicMock
from immich_gpx.core.immich_client import ImmichAPI


def test_redirect_updates_base_url():
    """Test that redirect detection updates the base URL."""
    api = ImmichAPI('http://localhost:2283', 'test-api-key')
    
    # Create a mock response that represents a redirect
    # response.history contains the intermediate responses (3xx redirects)
    # response.url contains the final URL after all redirects
    mock_response = Mock(spec=requests.Response)
    mock_response.status_code = 200
    mock_response.history = [Mock()]  # Non-empty list indicates redirect occurred
    mock_response.url = 'https://localhost:2283/api/server/version'  # Final URL after redirect
    mock_response.json.return_value = {'major': 2, 'minor': 2, 'patch': 1}
    
    with patch.object(api.session, 'request', return_value=mock_response):
        response = api._make_request('GET', 'http://localhost:2283/api/server/version')
        
        # Verify redirect was detected and base URL was updated
        assert api.url == 'https://localhost:2283'
        assert response == mock_response


def test_no_redirect_keeps_base_url():
    """Test that requests without redirects don't change the base URL."""
    api = ImmichAPI('http://localhost:2283', 'test-api-key')
    original_url = api.url
    
    # Create a mock response with no redirect (empty history)
    mock_response = Mock(spec=requests.Response)
    mock_response.status_code = 200
    mock_response.history = []  # Empty list means no redirect
    mock_response.url = 'http://localhost:2283/api/server/version'
    mock_response.json.return_value = {'major': 2, 'minor': 2, 'patch': 1}
    
    with patch.object(api.session, 'request', return_value=mock_response):
        response = api._make_request('GET', 'http://localhost:2283/api/server/version')
        
        # Verify URL was not changed
        assert api.url == original_url
        assert response == mock_response


def test_redirect_http_to_https():
    """Test HTTP to HTTPS redirect scenario from real error."""
    api = ImmichAPI('http://photos.hl.servicetag.com.br', 'test-api-key')
    
    # Simulate what requests library does:
    # - Initial request to HTTP returns 301/302 with Location: HTTPS
    # - Then follow redirect automatically (allow_redirects=True)
    # - response.history contains the initial 301 response
    # - response.url is the final URL (HTTPS)
    mock_redirect_response = Mock(spec=requests.Response)
    mock_redirect_response.status_code = 200
    mock_redirect_response.history = [Mock(status_code=301)]  # Indicate 301 redirect occurred
    mock_redirect_response.url = 'https://photos.hl.servicetag.com.br/api/server/version'
    mock_redirect_response.json.return_value = {'major': 2, 'minor': 2, 'patch': 1}
    
    with patch.object(api.session, 'request', return_value=mock_redirect_response):
        # First request (test_connection)
        response1 = api._make_request('GET', 'http://photos.hl.servicetag.com.br/api/server/version')
        
        # URL should be updated to HTTPS
        assert api.url == 'https://photos.hl.servicetag.com.br'
        
        # Now a second request should use the updated HTTPS URL
        # In real usage, get_photos_in_range would construct URL with api.url
        # which should now be HTTPS
        second_request_url = f"{api.url}/api/search/metadata"
        assert second_request_url.startswith('https://')
        assert 'https://photos.hl.servicetag.com.br' in second_request_url


def test_redirect_preserves_path_not_important():
    """Test that redirect updates only the base URL, not the full request path."""
    api = ImmichAPI('http://localhost:2283', 'test-api-key')
    
    mock_response = Mock(spec=requests.Response)
    mock_response.status_code = 200
    mock_response.history = [Mock()]
    # Redirect to HTTPS with same path
    mock_response.url = 'https://localhost:2283/api/server/version'
    mock_response.json.return_value = {'major': 2, 'minor': 2, 'patch': 1}
    
    with patch.object(api.session, 'request', return_value=mock_response):
        api._make_request('GET', 'http://localhost:2283/api/server/version')
        
        # Base URL should be updated (scheme changed)
        assert api.url == 'https://localhost:2283'


def test_trailing_slash_handling():
    """Test that trailing slashes don't prevent URL matching."""
    api = ImmichAPI('http://localhost:2283/', 'test-api-key')  # Note: trailing slash
    
    # The __init__ strips trailing slash, so api.url should be without it
    assert api.url == 'http://localhost:2283'
    
    mock_response = Mock(spec=requests.Response)
    mock_response.status_code = 200
    mock_response.history = [Mock()]
    mock_response.url = 'https://localhost:2283/api/server/version'
    
    with patch.object(api.session, 'request', return_value=mock_response):
        api._make_request('GET', 'http://localhost:2283/api/server/version')
        
        # Should update to HTTPS correctly
        assert api.url == 'https://localhost:2283'


def test_redirect_with_different_port():
    """Test redirect that changes port number."""
    api = ImmichAPI('http://localhost:2283', 'test-api-key')
    
    mock_response = Mock(spec=requests.Response)
    mock_response.status_code = 200
    mock_response.history = [Mock()]
    # Redirect to different port (e.g., reverse proxy scenario)
    mock_response.url = 'https://localhost:3000/api/server/version'
    
    with patch.object(api.session, 'request', return_value=mock_response):
        api._make_request('GET', 'http://localhost:2283/api/server/version')
        
        # Should update base URL with new port
        assert api.url == 'https://localhost:3000'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
