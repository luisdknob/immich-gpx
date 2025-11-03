"""
Tests for configuration file loading and validation.

Tests the ConfigLoader class including YAML parsing, validation,
and configuration merging.
"""

import pytest
import os
import tempfile
import logging

from immich_gpx.config_loader import ConfigLoader


class TestConfigLoader:
    """Tests for ConfigLoader class."""
    
    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
immich:
  url: http://localhost:2283
  api_key: test-key
  verify_ssl: false
  timeout: 20
matching:
  threshold: 120
performance:
  cache_ttl: 1800
  rate_limit_requests: 50
  rate_limit_window: 30
logging:
  verbose: true
  log_file: /var/log/app.log
""")
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    def test_config_loader_initialization(self):
        """Test ConfigLoader initialization."""
        loader = ConfigLoader('config.yaml')
        assert loader.config_path == 'config.yaml'
        assert loader.config == {}
        assert loader.logger is not None
    
    def test_config_loader_with_custom_logger(self):
        """Test ConfigLoader with custom logger."""
        custom_logger = logging.getLogger('test_logger')
        loader = ConfigLoader('config.yaml', logger=custom_logger)
        assert loader.logger is custom_logger
    
    def test_load_valid_config(self, temp_config_file):
        """Test loading valid config file."""
        loader = ConfigLoader(temp_config_file)
        config = loader.load()
        
        assert config is not None
        assert config['immich']['url'] == 'http://localhost:2283'
        assert config['immich']['api_key'] == 'test-key'
        assert config['immich']['verify_ssl'] is False
        assert config['immich']['timeout'] == 20
    
    def test_load_nonexistent_file(self):
        """Test loading nonexistent config file."""
        loader = ConfigLoader('/nonexistent/config.yaml')
        
        with pytest.raises(FileNotFoundError):
            loader.load()
    
    def test_load_empty_config(self):
        """Test loading empty config file uses defaults."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("")
            temp_path = f.name
        
        try:
            loader = ConfigLoader(temp_path)
            config = loader.load()
            
            # Should have default values
            assert config['immich']['url'] is None
            assert config['immich']['timeout'] == 10
            assert config['matching']['threshold'] == 60
        finally:
            os.remove(temp_path)
    
    def test_config_merging_with_defaults(self, temp_config_file):
        """Test that config merges with defaults."""
        loader = ConfigLoader(temp_config_file)
        config = loader.load()
        
        # Values from file should override defaults
        assert config['immich']['timeout'] == 20
        
        # Default values should be present for unspecified keys
        assert 'logging' in config
        assert config['logging']['verbose'] is True
    
    def test_get_immich_config(self, temp_config_file):
        """Test getting immich-specific config."""
        loader = ConfigLoader(temp_config_file)
        loader.load()
        
        immich_cfg = loader.get_immich_config()
        assert immich_cfg['url'] == 'http://localhost:2283'
        assert immich_cfg['api_key'] == 'test-key'
        assert immich_cfg['timeout'] == 20
    
    def test_get_matching_config(self, temp_config_file):
        """Test getting matching-specific config."""
        loader = ConfigLoader(temp_config_file)
        loader.load()
        
        matching_cfg = loader.get_matching_config()
        assert matching_cfg['threshold'] == 120
    
    def test_get_performance_config(self, temp_config_file):
        """Test getting performance-specific config."""
        loader = ConfigLoader(temp_config_file)
        loader.load()
        
        perf_cfg = loader.get_performance_config()
        assert perf_cfg['cache_ttl'] == 1800
        assert perf_cfg['rate_limit_requests'] == 50
        assert perf_cfg['rate_limit_window'] == 30
    
    def test_validate_valid_config(self, temp_config_file):
        """Test validation passes for valid config."""
        loader = ConfigLoader(temp_config_file)
        loader.load()
        
        assert loader.validate() is True
    
    def test_validate_negative_cache_ttl(self):
        """Test validation fails for negative cache_ttl."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
performance:
  cache_ttl: -100
""")
            temp_path = f.name
        
        try:
            loader = ConfigLoader(temp_path)
            loader.load()
            
            with pytest.raises(ValueError, match="cache_ttl must be non-negative"):
                loader.validate()
        finally:
            os.remove(temp_path)
    
    def test_validate_zero_rate_limit_requests(self):
        """Test validation fails for zero rate_limit_requests."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
performance:
  rate_limit_requests: 0
""")
            temp_path = f.name
        
        try:
            loader = ConfigLoader(temp_path)
            loader.load()
            
            with pytest.raises(ValueError, match="rate_limit_requests must be positive"):
                loader.validate()
        finally:
            os.remove(temp_path)
    
    def test_validate_negative_threshold(self):
        """Test validation fails for negative threshold."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
matching:
  threshold: -50
""")
            temp_path = f.name
        
        try:
            loader = ConfigLoader(temp_path)
            loader.load()
            
            with pytest.raises(ValueError, match="threshold must be positive"):
                loader.validate()
        finally:
            os.remove(temp_path)
    
    def test_validate_before_load(self):
        """Test validation fails if config not loaded."""
        loader = ConfigLoader('config.yaml')
        
        with pytest.raises(ValueError, match="Configuration not loaded"):
            loader.validate()
    
    def test_invalid_yaml_syntax(self):
        """Test loading invalid YAML syntax."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
immich:
  url: http://localhost:2283
  invalid syntax: [unclosed bracket
""")
            temp_path = f.name
        
        try:
            loader = ConfigLoader(temp_path)
            
            with pytest.raises(ValueError, match="Invalid YAML configuration"):
                loader.load()
        finally:
            os.remove(temp_path)
    
    def test_config_not_dict(self):
        """Test error when YAML root is not a dictionary."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
- item1
- item2
- item3
""")
            temp_path = f.name
        
        try:
            loader = ConfigLoader(temp_path)
            
            with pytest.raises(ValueError, match="Configuration must be a YAML dictionary"):
                loader.load()
        finally:
            os.remove(temp_path)
    
    def test_repr(self):
        """Test string representation."""
        loader = ConfigLoader('config.yaml')
        repr_str = repr(loader)
        
        assert 'ConfigLoader' in repr_str
        assert 'config.yaml' in repr_str


class TestDefaultConfig:
    """Tests for default configuration values."""
    
    def test_default_immich_config(self):
        """Test default immich configuration."""
        defaults = ConfigLoader.DEFAULT_CONFIG
        
        immich = defaults['immich']
        assert immich['url'] is None
        assert immich['api_key'] is None
        assert immich['verify_ssl'] is True
        assert immich['timeout'] == 10
    
    def test_default_matching_config(self):
        """Test default matching configuration."""
        defaults = ConfigLoader.DEFAULT_CONFIG
        
        matching = defaults['matching']
        assert matching['threshold'] == 60
    
    def test_default_performance_config(self):
        """Test default performance configuration."""
        defaults = ConfigLoader.DEFAULT_CONFIG
        
        perf = defaults['performance']
        assert perf['cache_ttl'] == 3600
        assert perf['rate_limit_requests'] == 100
        assert perf['rate_limit_window'] == 60
    
    def test_default_logging_config(self):
        """Test default logging configuration."""
        defaults = ConfigLoader.DEFAULT_CONFIG
        
        logging = defaults['logging']
        assert logging['verbose'] is False
        assert logging['log_file'] is None
