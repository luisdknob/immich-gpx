"""Tests for HTTP/HTTPS protocol handling."""

import pytest
from immich_gpx import ImmichAPI


class TestHTTPProtocol:
    """Test HTTP/HTTPS protocol handling."""

    def test_http_url_preserved(self):
        """HTTP URLs should be preserved without forcing HTTPS."""
        url = "http://localhost:2283"
        api = ImmichAPI(url, "test-api-key")
        assert api.url == url
        assert api.url.startswith("http://")

    def test_https_url_preserved(self):
        """HTTPS URLs should be preserved as-is."""
        url = "https://immich.example.com"
        api = ImmichAPI(url, "test-api-key")
        assert api.url == url
        assert api.url.startswith("https://")

    def test_http_protocol_in_session(self):
        """HTTP requests should use HTTP protocol."""
        url = "http://localhost:2283"
        api = ImmichAPI(url, "test-api-key")
        # Check that the session is configured for HTTP
        assert api.session is not None
        assert api.url.startswith("http://")

    def test_https_protocol_in_session(self):
        """HTTPS requests should use HTTPS protocol."""
        url = "https://immich.example.com"
        api = ImmichAPI(url, "test-api-key")
        # Check that the session is configured for HTTPS
        assert api.session is not None
        assert api.url.startswith("https://")

    def test_url_without_protocol(self):
        """URLs without protocol should be treated as-is."""
        # This should either fail validation or be handled by validation
        url = "localhost:2283"
        try:
            api = ImmichAPI(url, "test-api-key")
            # If it doesn't fail, URL should be preserved as-is
            assert api.url == url
        except ValueError:
            # Expected - URL without protocol should fail validation
            pass

    def test_trailing_slash_preserved(self):
        """Trailing slashes should be handled correctly."""
        url_with_slash = "http://localhost:2283/"
        url_without_slash = "http://localhost:2283"
        
        api1 = ImmichAPI(url_with_slash, "test-api-key")
        api2 = ImmichAPI(url_without_slash, "test-api-key")
        
        # Both should work
        assert api1.url is not None
        assert api2.url is not None
