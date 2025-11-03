"""
Configuration file loader for immich-gpx-linker.

Supports loading settings from YAML configuration files for more flexible
application setup. Allows users to define defaults for API URLs, timeouts,
and other parameters without command-line flags.

Classes:
    ConfigLoader: Load and validate YAML configuration files
    
File Format: YAML with sections for different components
"""

import os
import logging
from typing import Dict, Optional, Any

try:
    import yaml
except ImportError:
    yaml = None


class ConfigLoader:
    """
    Load and validate YAML configuration files.
    
    Supports loading application settings from YAML format for more flexible
    configuration management. Can merge settings from multiple sources
    (config file, environment variables, CLI arguments).
    
    Attributes:
        config_path (str): Path to YAML configuration file
        config (dict): Parsed configuration dictionary
        logger (logging.Logger): Logger instance
        
    Example:
        >>> loader = ConfigLoader('config.yaml')
        >>> config = loader.load()
        >>> url = config.get('immich', {}).get('url')
    """
    
    # Default configuration schema
    DEFAULT_CONFIG = {
        'immich': {
            'url': None,
            'api_key': None,
            'verify_ssl': True,
            'timeout': 10,
        },
        'matching': {
            'threshold': 60,
        },
        'performance': {
            'cache_ttl': 3600,
            'rate_limit_requests': 100,
            'rate_limit_window': 60,
        },
        'logging': {
            'verbose': False,
            'log_file': None,
        },
    }
    
    def __init__(
        self,
        config_path: str,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        """
        Initialize config loader.
        
        Args:
            config_path: Path to YAML configuration file
            logger: Optional logger instance (defaults to 'immich-gpx')
            
        Returns:
            None
        """
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self.logger = logger or logging.getLogger('immich-gpx')
    
    def load(self) -> Dict[str, Any]:
        """
        Load and parse YAML configuration file.
        
        Loads YAML configuration, validates structure, and merges with defaults.
        Returns merged configuration with all required keys present.
        
        Returns:
            Dictionary with configuration settings merged with defaults
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If YAML is invalid or configuration is malformed
            
        Example:
            >>> loader = ConfigLoader('config.yaml')
            >>> config = loader.load()
            >>> print(config['immich']['url'])
            'http://localhost:2283'
        """
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        if yaml is None:
            raise ImportError("PyYAML is required for config file support. Install with: pip install pyyaml")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                file_config = yaml.safe_load(f)
            
            if file_config is None:
                file_config = {}
            
            if not isinstance(file_config, dict):
                raise ValueError(f"Configuration must be a YAML dictionary, got {type(file_config)}")
            
            # Merge with defaults
            self.config = self._merge_config(self.DEFAULT_CONFIG.copy(), file_config)
            
            self.logger.debug(f"Loaded configuration from {self.config_path}")
            return self.config
            
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML configuration: {e}")
    
    def _merge_config(
        self,
        defaults: Dict[str, Any],
        overrides: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Merge override configuration with defaults.
        
        Args:
            defaults: Default configuration dictionary
            overrides: Override configuration dictionary
            
        Returns:
            Merged configuration dictionary
        """
        result = defaults.copy()
        
        for key, value in overrides.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def get_immich_config(self) -> Dict[str, Any]:
        """
        Get Immich-specific configuration.
        
        Returns:
            Dictionary with immich settings: url, api_key, verify_ssl, timeout
            
        Example:
            >>> loader = ConfigLoader('config.yaml')
            >>> loader.load()
            >>> immich_cfg = loader.get_immich_config()
            >>> url = immich_cfg['url']
        """
        return self.config.get('immich', {})
    
    def get_matching_config(self) -> Dict[str, Any]:
        """
        Get matching-specific configuration.
        
        Returns:
            Dictionary with matching settings: threshold
        """
        return self.config.get('matching', {})
    
    def get_performance_config(self) -> Dict[str, Any]:
        """
        Get performance-specific configuration.
        
        Returns:
            Dictionary with performance settings: cache_ttl, rate_limit_requests, rate_limit_window
        """
        return self.config.get('performance', {})
    
    def validate(self) -> bool:
        """
        Validate configuration settings.
        
        Checks that required settings are present and have valid values.
        Immich URL and API key can be None (will be provided via CLI/env).
        
        Returns:
            True if configuration is valid
            
        Raises:
            ValueError: If validation fails
        """
        if not self.config:
            raise ValueError("Configuration not loaded. Call load() first.")
        
        # Validate performance settings
        perf_cfg = self.get_performance_config()
        if perf_cfg.get('cache_ttl', 0) < 0:
            raise ValueError("cache_ttl must be non-negative")
        
        if perf_cfg.get('rate_limit_requests', 0) <= 0:
            raise ValueError("rate_limit_requests must be positive")
        
        if perf_cfg.get('rate_limit_window', 0) <= 0:
            raise ValueError("rate_limit_window must be positive")
        
        # Validate matching settings
        match_cfg = self.get_matching_config()
        if match_cfg.get('threshold', 0) <= 0:
            raise ValueError("threshold must be positive")
        
        return True
    
    def __repr__(self) -> str:
        """Return string representation."""
        return f"ConfigLoader(config_path={self.config_path!r}, loaded={bool(self.config)})"
