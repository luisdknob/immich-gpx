"""
Configuration management for immich-gpx.

Handles configuration from command-line args, environment variables, and defaults.
Config dataclass validates all settings on initialization.
"""

import os
from pathlib import Path

from .errors import ConfigurationError, GPXValidationError
from .validation import (
    validate_api_key,
    validate_gpx_file,
    validate_immich_url,
    validate_threshold,
    validate_timeout,
)


# Configuration constants for default values and validation
DEFAULT_TIME_THRESHOLD_SECONDS = 60  # Match GPS points within 60 seconds of photo time
DEFAULT_API_TIMEOUT_SECONDS = 10     # API requests timeout after 10 seconds
DEFAULT_VERIFY_SSL = True             # Verify SSL certificates by default
TIME_BUFFER_BEFORE_MINUTES = 60      # Query photos 60 minutes before GPX track
TIME_BUFFER_AFTER_MINUTES = 2        # Query photos 2 minutes after GPX track

# Rollback configuration defaults
DEFAULT_ROLLBACK_ENABLED = True       # Enable rollback by default
DEFAULT_ROLLBACK_DIR = "./rollback"   # Default rollback directory
DEFAULT_ROLLBACK_MAX_SESSIONS = 10    # Keep last 10 rollback sessions

# API key validation
MIN_API_KEY_LENGTH = 10              # Minimum expected API key length


class Config:
    """Application configuration with validation.
    
    Loads settings from CLI args, environment variables, and defaults.
    Validates GPX file, Immich URL, API key, and numeric parameters.
    """
    
    # Default configuration values
    DEFAULT_THRESHOLD = DEFAULT_TIME_THRESHOLD_SECONDS
    DEFAULT_TIMEOUT = DEFAULT_API_TIMEOUT_SECONDS
    DEFAULT_VERIFY_SSL = DEFAULT_VERIFY_SSL
    TIME_BUFFER_BEFORE_MINUTES = TIME_BUFFER_BEFORE_MINUTES
    TIME_BUFFER_AFTER_MINUTES = TIME_BUFFER_AFTER_MINUTES
    
    # Rollback defaults
    DEFAULT_ROLLBACK_ENABLED = DEFAULT_ROLLBACK_ENABLED
    DEFAULT_ROLLBACK_DIR = DEFAULT_ROLLBACK_DIR
    DEFAULT_ROLLBACK_MAX_SESSIONS = DEFAULT_ROLLBACK_MAX_SESSIONS
    
    def __init__(self) -> None:
        """
        Initialize configuration with default values.
        
        Args:
            None
            
        Returns:
            None
        """
        self.immich_url: str = None
        self.immich_api_key: str = None
        self.gpx_file: str = None
        self.threshold: float = self.DEFAULT_THRESHOLD
        self.timeout: int = self.DEFAULT_TIMEOUT
        self.verify_ssl: bool = self.DEFAULT_VERIFY_SSL
        self.verbose: bool = False
        
        # Rollback configuration
        self.rollback_enabled: bool = self.DEFAULT_ROLLBACK_ENABLED
        self.rollback_dir: str = self.DEFAULT_ROLLBACK_DIR
        self.rollback_max_sessions: int = self.DEFAULT_ROLLBACK_MAX_SESSIONS
    
    @classmethod
    def from_args_and_env(cls, args) -> 'Config':
        """
        Create and validate configuration from command-line arguments and environment.
        
        Merges configuration sources with defined precedence:
        1. Command-line arguments override environment variables
        2. Environment variables override defaults
        3. Built-in defaults used for unspecified values
        
        Args:
            args: Parsed command-line arguments from argparse.ArgumentParser
                Expected attributes:
                - gpx_file: required path to GPX file
                - immich_url: optional Immich server URL
                - immich_api_key: optional API key
                - threshold: time threshold (default: 60)
                - timeout: request timeout (default: 10)
                - no_verify_ssl: boolean flag to disable SSL verification
                - verbose: boolean flag for verbose output
        
        Returns:
            Config instance with all values set and validated
        
        Raises:
            ConfigurationError: If any validation check fails
            GPXValidationError: If GPX file not found
            
        Example:
            >>> import argparse
            >>> parser = argparse.ArgumentParser()
            >>> # ... add arguments ...
            >>> args = parser.parse_args()
            >>> config = Config.from_args_and_env(args)
        """
        # Create new config instance
        config = cls()
        
        # GPX file (required)
        config.gpx_file = args.gpx_file
        
        # Immich credentials: CLI args take precedence over environment
        config.immich_url = args.immich_url or os.getenv('IMMICH_URL')
        config.immich_api_key = args.immich_api_key or os.getenv('IMMICH_API_KEY')
        
        # Optional parameters: use CLI args
        config.threshold = args.threshold
        config.timeout = args.timeout
        config.verify_ssl = not args.no_verify_ssl
        config.verbose = args.verbose
        
        # Rollback configuration from environment or defaults
        config.rollback_enabled = os.getenv('ROLLBACK_ENABLED', 'true').lower() == 'true'
        config.rollback_dir = os.getenv('ROLLBACK_DIR', config.DEFAULT_ROLLBACK_DIR)
        config.rollback_max_sessions = int(os.getenv('ROLLBACK_MAX_SESSIONS', config.DEFAULT_ROLLBACK_MAX_SESSIONS))
        
        # Validate all parameters
        config.validate()
        
        return config
    
    def validate(self) -> None:
        """
        Validate all configuration parameters comprehensively.
        
        Validation checks using validation module:
        - GPX file exists, readable, valid format, contains track points
        - Immich URL format and scheme validation
        - API key format and content validation
        - Threshold and timeout range validation
        
        Args:
            None
            
        Returns:
            None
            
        Raises:
            ConfigurationError: For any validation failure
            GPXValidationError: If GPX file not found or inaccessible
            
        Example:
            >>> config = Config()
            >>> config.immich_url = 'invalid'
            >>> config.validate()  # Raises ConfigurationError
        """
        if not self.gpx_file:
            raise ConfigurationError("GPX file path is required")
        
        try:
            validate_gpx_file(self.gpx_file)
        except ValueError as e:
            raise GPXValidationError(str(e)) from e
        
        if not self.immich_url:
            raise ConfigurationError(
                "IMMICH_URL is required. Set via --immich-url or IMMICH_URL environment variable."
            )
        
        try:
            validate_immich_url(self.immich_url)
        except ValueError as e:
            raise ConfigurationError(str(e)) from e
        
        if not self.immich_api_key:
            raise ConfigurationError(
                "IMMICH_API_KEY is required. Set via --immich-api-key or IMMICH_API_KEY environment variable."
            )
        
        try:
            validate_api_key(self.immich_api_key)
        except ValueError as e:
            raise ConfigurationError(str(e)) from e
        
        try:
            validate_threshold(self.threshold)
        except ValueError as e:
            raise ConfigurationError(str(e)) from e
        
        try:
            validate_timeout(self.timeout)
        except ValueError as e:
            raise ConfigurationError(str(e)) from e
    
    def __repr__(self) -> str:
        """
        Return string representation of configuration (with sensitive data masked).
        
        Hides API key and only shows last 4 characters for security purposes.
        Useful for logging configuration without exposing credentials.
        
        Args:
            None
            
        Returns:
            String representation with masked API key
            
        Example:
            >>> config = Config()
            >>> config.immich_api_key = 'super-secret-key-12345'
            >>> repr(config)
            "Config(...immich_api_key='***2345'...)"
        """
        # Mask API key: show only last 4 characters
        masked_key = f"***{self.immich_api_key[-4:] if self.immich_api_key and len(self.immich_api_key) >= 4 else '***'}"
        
        return (
            f"Config(gpx_file='{self.gpx_file}', "
            f"immich_url='{self.immich_url}', "
            f"immich_api_key='{masked_key}', "
            f"threshold={self.threshold}, "
            f"timeout={self.timeout}, "
            f"verify_ssl={self.verify_ssl}, "
            f"verbose={self.verbose}, "
            f"rollback_enabled={self.rollback_enabled}, "
            f"rollback_dir='{self.rollback_dir}', "
            f"rollback_max_sessions={self.rollback_max_sessions})"
        )
