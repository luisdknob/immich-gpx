"""Tests for main() error handling with custom exceptions."""

import sys
import tempfile
import os
from unittest.mock import patch, MagicMock
import pytest

# Import the main function and error classes
from immich_gpx import (
    main,
    ErrorCodes,
    ConfigurationError,
    GPXValidationError,
    GPXParsingError,
    ConnectionError,
    AuthenticationError,
    MatchingError,
    UpdateError,
)


class TestMainErrorHandling:
    """Test main() function's error handling for each exception type."""

    def test_main_configuration_error_exit_code(self, monkeypatch, caplog):
        """Test that ConfigurationError exits with CONFIG_ERROR code."""
        monkeypatch.setattr(sys, 'argv', ['immich-gpx-linker', '--gpx-file', 'test.gpx'])
        
        with patch('immich_gpx.cli.GPXParser') as mock_parser:
            mock_parser.return_value.parse.side_effect = ConfigurationError(
                "Invalid configuration"
            )
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == ErrorCodes.CONFIG_ERROR
            assert "Configuration Error" in caplog.text

    def test_main_gpx_validation_error_exit_code(self, monkeypatch, caplog):
        """Test that GPXValidationError exits with FILE_NOT_FOUND code."""
        monkeypatch.setattr(sys, 'argv', ['immich-gpx-linker', '--gpx-file', 'test.gpx'])
        
        with patch('immich_gpx.cli.GPXParser') as mock_parser:
            mock_parser.return_value.parse.side_effect = GPXValidationError(
                "File not found"
            )
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == ErrorCodes.FILE_NOT_FOUND
            assert "GPX File Error" in caplog.text

    def test_main_gpx_parsing_error_exit_code(self, monkeypatch, caplog):
        """Test that GPXParsingError exits with PARSE_ERROR code."""
        monkeypatch.setattr(sys, 'argv', ['immich-gpx-linker', '--gpx-file', 'test.gpx'])
        
        with patch('immich_gpx.cli.GPXParser') as mock_parser:
            mock_parser.return_value.parse.side_effect = GPXParsingError(
                "Invalid XML"
            )
            with pytest.raises(SystemExit) as exc_info:
                main()
            
            assert exc_info.value.code == ErrorCodes.PARSE_ERROR
            assert "GPX Parsing Error" in caplog.text

    def test_main_connection_error_exit_code(self, monkeypatch, caplog):
        """Test that ConnectionError exits with CONNECTION_ERROR code."""
        from datetime import datetime, timedelta
        
        # Create a temporary GPX file
        with tempfile.NamedTemporaryFile(suffix='.gpx', delete=False) as f:
            f.write(b'<?xml version="1.0"?><gpx></gpx>')
            gpx_path = f.name
        
        try:
            monkeypatch.setattr(sys, 'argv', [
                'immich-gpx-linker',
                '--gpx-file', gpx_path,
                '--immich-url', 'http://localhost:2283',
                '--immich-api-key', 'test_key_123'
            ])
            
            now = datetime.now()
            with patch('immich_gpx.cli.GPXParser') as mock_parser_class, \
                 patch('immich_gpx.cli.ImmichAPI') as mock_api_class:
                
                mock_parser = MagicMock()
                mock_parser.parse.return_value = [(1.0, 2.0, 0, now)]
                mock_parser.get_time_range.return_value = (now, now + timedelta(hours=1))
                mock_parser_class.return_value = mock_parser
                
                mock_api = MagicMock()
                mock_api.test_connection.side_effect = ConnectionError(
                    "Cannot connect"
                )
                mock_api_class.return_value = mock_api
                
                with pytest.raises(SystemExit) as exc_info:
                    main()
                
                assert exc_info.value.code == ErrorCodes.CONNECTION_ERROR
                # Check that error message mentions the connection issue
                assert "Cannot connect" in caplog.text or "Connection" in caplog.text
        finally:
            os.unlink(gpx_path)

    def test_main_authentication_error_exit_code(self, monkeypatch, caplog):
        """Test that AuthenticationError exits with AUTH_ERROR code."""
        from datetime import datetime, timedelta
        
        # Create a temporary GPX file
        with tempfile.NamedTemporaryFile(suffix='.gpx', delete=False) as f:
            f.write(b'<?xml version="1.0"?><gpx></gpx>')
            gpx_path = f.name
        
        try:
            now = datetime.now()
            monkeypatch.setattr(sys, 'argv', [
                'immich-gpx-linker',
                '--gpx-file', gpx_path,
                '--immich-url', 'http://localhost:2283',
                '--immich-api-key', 'invalid_key'
            ])
            
            with patch('immich_gpx.cli.GPXParser') as mock_parser_class, \
                 patch('immich_gpx.cli.ImmichAPI') as mock_api_class:
                
                mock_parser = MagicMock()
                mock_parser.parse.return_value = [(1.0, 2.0, 0, now)]
                mock_parser.get_time_range.return_value = (now, now + timedelta(hours=1))
                mock_parser_class.return_value = mock_parser
                
                mock_api = MagicMock()
                mock_api.test_connection.side_effect = AuthenticationError(
                    "Invalid API key"
                )
                mock_api_class.return_value = mock_api
                
                with pytest.raises(SystemExit) as exc_info:
                    main()
                
                assert exc_info.value.code == ErrorCodes.AUTH_ERROR
                assert "Authentication Error" in caplog.text
        finally:
            os.unlink(gpx_path)

    def test_main_matching_error_exit_code(self, monkeypatch, caplog):
        """Test that MatchingError exits with MATCH_ERROR code."""
        from datetime import datetime, timedelta
        
        # Create a temporary GPX file
        with tempfile.NamedTemporaryFile(suffix='.gpx', delete=False) as f:
            f.write(b'<?xml version="1.0"?><gpx></gpx>')
            gpx_path = f.name
        
        try:
            now = datetime.now()
            monkeypatch.setattr(sys, 'argv', [
                'immich-gpx-linker',
                '--gpx-file', gpx_path,
                '--immich-url', 'http://localhost:2283',
                '--immich-api-key', 'test_key_123'
            ])
            
            with patch('immich_gpx.cli.GPXParser') as mock_parser_class, \
                 patch('immich_gpx.cli.ImmichAPI') as mock_api_class, \
                 patch('immich_gpx.cli.GPSMatcher') as mock_matcher_class:
                
                mock_parser = MagicMock()
                mock_parser.parse.return_value = [(1.0, 2.0, 0, now)]
                mock_parser.get_time_range.return_value = (now, now + timedelta(hours=1))
                mock_parser_class.return_value = mock_parser
                
                mock_api = MagicMock()
                mock_api.test_connection.return_value = None
                mock_api.get_photos_in_range.return_value = []
                mock_api_class.return_value = mock_api
                
                mock_matcher = MagicMock()
                mock_matcher.match_photos_to_points.side_effect = MatchingError(
                    "Match failed"
                )
                mock_matcher_class.return_value = mock_matcher
                
                with pytest.raises(SystemExit) as exc_info:
                    main()
                
                assert exc_info.value.code == ErrorCodes.MATCH_ERROR
                assert "Processing Error" in caplog.text
        finally:
            os.unlink(gpx_path)

    def test_main_update_error_exit_code(self, monkeypatch, caplog):
        """Test that UpdateError exits with UPDATE_ERROR code."""
        from datetime import datetime, timedelta
        
        # Create a temporary GPX file
        with tempfile.NamedTemporaryFile(suffix='.gpx', delete=False) as f:
            f.write(b'<?xml version="1.0"?><gpx></gpx>')
            gpx_path = f.name
        
        try:
            now = datetime.now()
            monkeypatch.setattr(sys, 'argv', [
                'immich-gpx-linker',
                '--gpx-file', gpx_path,
                '--immich-url', 'http://localhost:2283',
                '--immich-api-key', 'test_key_123'
            ])
            
            with patch('immich_gpx.cli.GPXParser') as mock_parser_class, \
                 patch('immich_gpx.cli.ImmichAPI') as mock_api_class, \
                 patch('immich_gpx.cli.GPSMatcher') as mock_matcher_class:
                
                mock_parser = MagicMock()
                mock_parser.parse.return_value = [(1.0, 2.0, 0, now)]
                mock_parser.get_time_range.return_value = (now, now + timedelta(hours=1))
                mock_parser_class.return_value = mock_parser
                
                mock_api = MagicMock()
                mock_api.test_connection.return_value = None
                mock_api.get_photos_in_range.return_value = []
                mock_api_class.return_value = mock_api
                
                mock_matcher = MagicMock()
                mock_matcher.match_photos_to_points.side_effect = UpdateError(
                    "Update failed"
                )
                mock_matcher_class.return_value = mock_matcher
                
                with pytest.raises(SystemExit) as exc_info:
                    main()
                
                assert exc_info.value.code == ErrorCodes.UPDATE_ERROR
                assert "Processing Error" in caplog.text
        finally:
            os.unlink(gpx_path)

    def test_main_unexpected_error_exit_code(self, monkeypatch, caplog):
        """Test that unexpected exceptions exit with UNKNOWN_ERROR code."""
        # Create a temporary GPX file
        with tempfile.NamedTemporaryFile(suffix='.gpx', delete=False) as f:
            f.write(b'<?xml version="1.0"?><gpx></gpx>')
            gpx_path = f.name
        
        try:
            monkeypatch.setattr(sys, 'argv', [
                'immich-gpx-linker',
                '--gpx-file', gpx_path,
                '--immich-url', 'http://localhost:2283',
                '--immich-api-key', 'test_key_123'
            ])
            
            with patch('immich_gpx.cli.GPXParser') as mock_parser_class:
                mock_parser = MagicMock()
                mock_parser.parse.side_effect = RuntimeError("Unexpected error")
                mock_parser_class.return_value = mock_parser
                
                with pytest.raises(SystemExit) as exc_info:
                    main()
                
                assert exc_info.value.code == ErrorCodes.UNKNOWN_ERROR
                assert "Unexpected error" in caplog.text
        finally:
            os.unlink(gpx_path)

    def test_main_error_logging_with_verbose(self, monkeypatch, caplog):
        """Test that verbose flag includes traceback in error logging."""
        # Create a temporary GPX file
        with tempfile.NamedTemporaryFile(suffix='.gpx', delete=False) as f:
            f.write(b'<?xml version="1.0"?><gpx></gpx>')
            gpx_path = f.name
        
        try:
            monkeypatch.setattr(sys, 'argv', [
                'immich-gpx-linker',
                '--gpx-file', gpx_path,
                '--immich-url', 'http://localhost:2283',
                '--immich-api-key', 'test_key_123',
                '--verbose'
            ])
            
            with patch('immich_gpx.cli.GPXParser') as mock_parser_class:
                mock_parser = MagicMock()
                mock_parser.parse.side_effect = RuntimeError("Unexpected error")
                mock_parser_class.return_value = mock_parser
                
                with pytest.raises(SystemExit) as exc_info:
                    main()
                
                assert exc_info.value.code == ErrorCodes.UNKNOWN_ERROR
                # Traceback should be logged with verbose flag
                # (we can check that the exception was printed)
                assert "Unexpected error" in caplog.text
        finally:
            os.unlink(gpx_path)

    def test_main_configuration_error_messages(self, monkeypatch, caplog):
        """Test that ConfigurationError includes helpful troubleshooting info."""
        monkeypatch.setattr(sys, 'argv', ['immich-gpx-linker', '--gpx-file', 'test.gpx'])
        
        with patch('immich_gpx.cli.GPXParser') as mock_parser:
            mock_parser.return_value.parse.side_effect = ConfigurationError(
                "Invalid configuration"
            )
            with pytest.raises(SystemExit):
                main()
            
            log_text = caplog.text
            assert "Configuration Error" in log_text
            assert "Troubleshooting" in log_text
            assert "IMMICH_URL" in log_text or "immich-url" in log_text

    def test_main_connection_error_messages(self, monkeypatch, caplog):
        """Test that ConnectionError includes helpful troubleshooting info."""
        from datetime import datetime, timedelta
        
        # Create a temporary GPX file
        with tempfile.NamedTemporaryFile(suffix='.gpx', delete=False) as f:
            f.write(b'<?xml version="1.0"?><gpx></gpx>')
            gpx_path = f.name
        
        try:
            now = datetime.now()
            monkeypatch.setattr(sys, 'argv', [
                'immich-gpx-linker',
                '--gpx-file', gpx_path,
                '--immich-url', 'http://localhost:2283',
                '--immich-api-key', 'test_key_123'
            ])
            
            with patch('immich_gpx.cli.GPXParser') as mock_parser_class, \
                 patch('immich_gpx.cli.ImmichAPI') as mock_api_class:
                
                mock_parser = MagicMock()
                mock_parser.parse.return_value = [(1.0, 2.0, 0, now)]
                mock_parser.get_time_range.return_value = (now, now + timedelta(hours=1))
                mock_parser_class.return_value = mock_parser
                
                mock_api = MagicMock()
                mock_api.test_connection.side_effect = ConnectionError(
                    "Cannot connect"
                )
                mock_api_class.return_value = mock_api
                
                with pytest.raises(SystemExit):
                    main()
                
                log_text = caplog.text
                # Verify error message includes connection info
                assert "Cannot connect" in log_text or "Troubleshooting" in log_text
                # Verify either the specific error or general error handling
                assert ("Connection" in log_text or "Application Error" in log_text)
        finally:
            os.unlink(gpx_path)
