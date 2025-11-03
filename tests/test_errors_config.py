"""Tests for error codes, custom exceptions, and configuration."""
import pytest
import os
from unittest.mock import Mock, patch
from immich_gpx import (
    ErrorCodes, 
    Config,
    ConfigurationError,
    GPXValidationError,
    GPXParsingError,
    ConnectionError,
    AuthenticationError,
    MatchingError,
    UpdateError,
    ImmichGPXLinkerError
)


# Helper function for creating valid GPX files with track points
def create_valid_gpx(path):
    """Create a valid GPX file with track points."""
    gpx_content = '''<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test" xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <trkseg>
      <trkpt lat="40.7128" lon="-74.0060">
        <ele>10.5</ele>
        <time>2024-01-15T12:00:00Z</time>
      </trkpt>
      <trkpt lat="40.7129" lon="-74.0061">
        <ele>11.5</ele>
        <time>2024-01-15T12:01:00Z</time>
      </trkpt>
    </trkseg>
  </trk>
</gpx>'''
    path.write_text(gpx_content)


class TestErrorCodes:
    """Tests for ErrorCodes class."""
    
    def test_error_codes_values(self):
        """Test error code values."""
        assert ErrorCodes.SUCCESS == 0
        assert ErrorCodes.CONFIG_ERROR == 1
        assert ErrorCodes.FILE_NOT_FOUND == 2
        assert ErrorCodes.PARSE_ERROR == 3
        assert ErrorCodes.CONNECTION_ERROR == 4
        assert ErrorCodes.AUTH_ERROR == 5
        assert ErrorCodes.MATCH_ERROR == 6
        assert ErrorCodes.UPDATE_ERROR == 7
        assert ErrorCodes.UNKNOWN_ERROR == 99
    
    def test_get_description(self):
        """Test error code descriptions."""
        assert ErrorCodes.get_description(ErrorCodes.SUCCESS) == "Operation completed successfully"
        assert ErrorCodes.get_description(ErrorCodes.CONFIG_ERROR) == "Configuration error"
        assert ErrorCodes.get_description(ErrorCodes.FILE_NOT_FOUND) == "File not found"
        assert ErrorCodes.get_description(999) == "Unknown error code"


class TestCustomExceptions:
    """Tests for custom exception classes."""
    
    def test_base_exception_initialization(self):
        """Test ImmichGPXLinkerError initialization."""
        exc = ImmichGPXLinkerError("Test error", ErrorCodes.CONFIG_ERROR)
        assert exc.message == "Test error"
        assert exc.error_code == ErrorCodes.CONFIG_ERROR
    
    def test_configuration_error(self):
        """Test ConfigurationError."""
        exc = ConfigurationError("Bad config")
        assert exc.error_code == ErrorCodes.CONFIG_ERROR
        assert exc.message == "Bad config"
    
    def test_gpx_validation_error(self):
        """Test GPXValidationError."""
        exc = GPXValidationError("File not found")
        assert exc.error_code == ErrorCodes.FILE_NOT_FOUND
    
    def test_gpx_parsing_error(self):
        """Test GPXParsingError."""
        exc = GPXParsingError("Invalid format")
        assert exc.error_code == ErrorCodes.PARSE_ERROR
    
    def test_connection_error(self):
        """Test ConnectionError."""
        exc = ConnectionError("Connection failed")
        assert exc.error_code == ErrorCodes.CONNECTION_ERROR
    
    def test_authentication_error(self):
        """Test AuthenticationError."""
        exc = AuthenticationError("Auth failed")
        assert exc.error_code == ErrorCodes.AUTH_ERROR
    
    def test_matching_error(self):
        """Test MatchingError."""
        exc = MatchingError("Match failed")
        assert exc.error_code == ErrorCodes.MATCH_ERROR
    
    def test_update_error(self):
        """Test UpdateError."""
        exc = UpdateError("Update failed")
        assert exc.error_code == ErrorCodes.UPDATE_ERROR


class TestConfig:
    """Tests for Config class."""
    
    def test_config_initialization(self):
        """Test Config initialization with defaults."""
        config = Config()
        assert config.immich_url is None
        assert config.immich_api_key is None
        assert config.gpx_file is None
        assert config.threshold == Config.DEFAULT_THRESHOLD
        assert config.timeout == Config.DEFAULT_TIMEOUT
        assert config.verify_ssl == Config.DEFAULT_VERIFY_SSL
        assert config.verbose is False
    
    def test_config_repr_masks_api_key(self):
        """Test Config __repr__ masks sensitive data."""
        config = Config()
        config.immich_url = "https://test.com"
        config.immich_api_key = "very_secret_key_1234567890"
        config.gpx_file = "test.gpx"
        
        repr_str = repr(config)
        assert "very_secret_key_1234567890" not in repr_str
        assert "***7890" in repr_str
    
    def test_config_validate_missing_gpx_file(self):
        """Test validation fails without GPX file."""
        config = Config()
        config.immich_url = "https://test.com"
        config.immich_api_key = "test_api_key_1234567890"
        
        with pytest.raises(ConfigurationError, match="GPX file path is required"):
            config.validate()
    
    def test_config_validate_nonexistent_gpx_file(self, tmp_path):
        """Test validation fails for nonexistent GPX file."""
        config = Config()
        config.gpx_file = "/nonexistent/path/file.gpx"
        config.immich_url = "https://test.com"
        config.immich_api_key = "test_api_key_1234567890"
        
        with pytest.raises(GPXValidationError, match="File not found"):
            config.validate()
    
    def test_config_validate_missing_immich_url(self, tmp_path):
        """Test validation fails without Immich URL."""
        gpx_file = tmp_path / "test.gpx"
        create_valid_gpx(gpx_file)
        
        config = Config()
        config.gpx_file = str(gpx_file)
        config.immich_api_key = "test_api_key_1234567890"
        
        with pytest.raises(ConfigurationError, match="IMMICH_URL is required"):
            config.validate()
    
    def test_config_validate_invalid_url_format(self, tmp_path):
        """Test validation fails for invalid URL format."""
        gpx_file = tmp_path / "test.gpx"
        create_valid_gpx(gpx_file)
        
        config = Config()
        config.gpx_file = str(gpx_file)
        config.immich_url = "invalid-url"
        config.immich_api_key = "test_api_key_1234567890"
        
        with pytest.raises(ConfigurationError, match="must include scheme"):
            config.validate()
    
    def test_config_validate_missing_api_key(self, tmp_path):
        """Test validation fails without API key."""
        gpx_file = tmp_path / "test.gpx"
        create_valid_gpx(gpx_file)
        
        config = Config()
        config.gpx_file = str(gpx_file)
        config.immich_url = "https://test.com"
        
        with pytest.raises(ConfigurationError, match="IMMICH_API_KEY is required"):
            config.validate()
    
    def test_config_validate_short_api_key(self, tmp_path):
        """Test validation fails for short API key."""
        gpx_file = tmp_path / "test.gpx"
        create_valid_gpx(gpx_file)
        
        config = Config()
        config.gpx_file = str(gpx_file)
        config.immich_url = "https://test.com"
        config.immich_api_key = "short"
        
        with pytest.raises(ConfigurationError, match="too short"):
            config.validate()
    
    def test_config_validate_invalid_threshold(self, tmp_path):
        """Test validation fails for invalid threshold."""
        gpx_file = tmp_path / "test.gpx"
        create_valid_gpx(gpx_file)
        
        config = Config()
        config.gpx_file = str(gpx_file)
        config.immich_url = "https://test.com"
        config.immich_api_key = "test_api_key_1234567890"
        config.threshold = -1
        
        with pytest.raises(ConfigurationError, match="Threshold must be.*seconds"):
            config.validate()
    
    def test_config_validate_invalid_timeout(self, tmp_path):
        """Test validation fails for invalid timeout."""
        gpx_file = tmp_path / "test.gpx"
        create_valid_gpx(gpx_file)
        
        config = Config()
        config.gpx_file = str(gpx_file)
        config.immich_url = "https://test.com"
        config.immich_api_key = "test_api_key_1234567890"
        config.timeout = -5
        
        with pytest.raises(ConfigurationError, match="Timeout must be.*seconds"):
            config.validate()
    
    def test_config_validate_valid_thresholds(self, tmp_path):
        """Test that valid configuration passes validation."""
        gpx_file = tmp_path / "test.gpx"
        create_valid_gpx(gpx_file)
        
        config = Config()
        config.gpx_file = str(gpx_file)
        config.immich_url = "https://test.com"
        config.immich_api_key = "test_api_key_1234567890"
        config.threshold = 60
        config.timeout = 10
        
        # Should not raise any exception
        config.validate()
    
    @patch.dict(os.environ, {
        'IMMICH_URL': 'https://env.test.com',
        'IMMICH_API_KEY': 'env_api_key_1234567890'
    })
    def test_config_from_args_and_env_env_vars(self, tmp_path):
        """Test Config.from_args_and_env with environment variables."""
        gpx_file = tmp_path / "test.gpx"
        create_valid_gpx(gpx_file)
        
        args = Mock()
        args.gpx_file = str(gpx_file)
        args.immich_url = None  # Not provided via CLI
        args.immich_api_key = None  # Not provided via CLI
        args.threshold = 60
        args.timeout = 10
        args.no_verify_ssl = False
        args.verbose = False
        
        config = Config.from_args_and_env(args)
        
        assert config.immich_url == "https://env.test.com"
        assert config.immich_api_key == "env_api_key_1234567890"
    
    def test_config_from_args_and_env_cli_override(self, tmp_path):
        """Test Config.from_args_and_env with CLI args overriding env."""
        gpx_file = tmp_path / "test.gpx"
        create_valid_gpx(gpx_file)
        
        args = Mock()
        args.gpx_file = str(gpx_file)
        args.immich_url = "https://cli.test.com"  # Provided via CLI
        args.immich_api_key = "cli_api_key_1234567890"  # Provided via CLI
        args.threshold = 120
        args.timeout = 20
        args.no_verify_ssl = True
        args.verbose = True
        
        config = Config.from_args_and_env(args)
        
        assert config.immich_url == "https://cli.test.com"
        assert config.immich_api_key == "cli_api_key_1234567890"
        assert config.threshold == 120
        assert config.timeout == 20
        assert config.verify_ssl is False
        assert config.verbose is True
