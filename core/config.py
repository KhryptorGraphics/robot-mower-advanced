"""
Configuration Management System

Handles loading, validating, and accessing configuration data from YAML files.
Provides a unified interface for accessing all system configuration.
"""

import os
import yaml
import logging
from typing import Any, Dict, List, Optional, TypeVar, Generic, Union, cast
from pathlib import Path
import json
from functools import lru_cache

T = TypeVar('T')

class ConfigError(Exception):
    """Exception raised for configuration errors"""
    pass

class ConfigPath:
    """Helper class to navigate nested configuration paths with dot notation"""
    
    def __init__(self, config_data: Dict[str, Any], path: str = ""):
        self._config_data = config_data
        self._path = path
    
    def __getattr__(self, name: str) -> 'ConfigPath':
        """Allow dot notation access: config.hardware.motors"""
        new_path = f"{self._path}.{name}" if self._path else name
        return ConfigPath(self._config_data, new_path)
    
    def get(self, default: Optional[T] = None) -> Union[T, Any]:
        """Get value at current path, returning default if not found"""
        if not self._path:
            return self._config_data
        
        parts = self._path.split('.')
        data = self._config_data
        
        try:
            for part in parts:
                if isinstance(data, dict) and part in data:
                    data = data[part]
                else:
                    return default
            return data
        except (KeyError, TypeError):
            return default
    
    def __call__(self, default: Optional[T] = None) -> Union[T, Any]:
        """Shorthand for get()"""
        return self.get(default)
    
    def exists(self) -> bool:
        """Check if the path exists in the config"""
        if not self._path:
            return True
        
        parts = self._path.split('.')
        data = self._config_data
        
        try:
            for part in parts:
                if isinstance(data, dict) and part in data:
                    data = data[part]
                else:
                    return False
            return True
        except (KeyError, TypeError):
            return False


class ConfigManager:
    """
    Manages configuration loading, validation, and access.
    
    Features:
    - Loads configuration from YAML files
    - Merges default config with user-provided overrides
    - Validates configuration against schema (future)
    - Provides dot notation access to configuration values
    - Caches config access for performance
    """
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern to ensure only one ConfigManager instance"""
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config_dir: Optional[str] = None, config_name: str = "default_config.yaml"):
        """Initialize the configuration manager"""
        # Skip re-initialization if already initialized
        if getattr(self, "_initialized", False):
            return
            
        self.logger = logging.getLogger("ConfigManager")
        self._config_data: Dict[str, Any] = {}
        
        # Set config directory
        if config_dir is None:
            # Use default location relative to current file
            current_dir = Path(__file__).parent.parent
            self._config_dir = current_dir / "config"
        else:
            self._config_dir = Path(config_dir)
        
        self._config_file = self._config_dir / config_name
        self.reload()
        self._initialized = True
    
    def reload(self) -> None:
        """Reload configuration from files"""
        self.logger.info(f"Loading configuration from {self._config_file}")
        
        try:
            # Start with default config
            with open(self._config_file, 'r') as f:
                self._config_data = yaml.safe_load(f)
            
            # Look for user config override
            user_config_file = self._config_dir / "user_config.yaml"
            if user_config_file.exists():
                self.logger.info(f"Loading user configuration from {user_config_file}")
                with open(user_config_file, 'r') as f:
                    user_config = yaml.safe_load(f)
                
                # Merge user config with default
                self._merge_configs(self._config_data, user_config)
            
            self.logger.info("Configuration loaded successfully")
        except Exception as e:
            self.logger.error(f"Error loading configuration: {str(e)}")
            raise ConfigError(f"Failed to load configuration: {str(e)}")
    
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """
        Recursively merge override config into base config
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                self._merge_configs(base[key], value)
            else:
                # Override or add values
                base[key] = value
    
    @property
    def config(self) -> ConfigPath:
        """Get the root config path object for dot notation access"""
        return ConfigPath(self._config_data)
    
    def get(self, path: str, default: Optional[T] = None) -> Union[T, Any]:
        """
        Get a configuration value by path string (e.g., 'hardware.motors.left_motor.enable_pin')
        Returns default if path doesn't exist
        """
        parts = path.split('.')
        data = self._config_data
        
        try:
            for part in parts:
                data = data[part]
            return data
        except (KeyError, TypeError):
            return default
    
    def set(self, path: str, value: Any) -> None:
        """
        Set a configuration value by path string
        Creates intermediate dictionaries if they don't exist
        """
        parts = path.split('.')
        data = self._config_data
        
        # Navigate to the parent of the leaf node
        for i, part in enumerate(parts[:-1]):
            if part not in data or not isinstance(data[part], dict):
                data[part] = {}
            data = data[part]
        
        # Set the leaf value
        data[parts[-1]] = value
    
    def save(self, file_path: Optional[str] = None) -> None:
        """
        Save current configuration to a file
        """
        if file_path is None:
            file_path = self._config_dir / "user_config.yaml"
        
        try:
            with open(file_path, 'w') as f:
                yaml.dump(self._config_data, f, default_flow_style=False)
            self.logger.info(f"Configuration saved to {file_path}")
        except Exception as e:
            self.logger.error(f"Error saving configuration: {str(e)}")
            raise ConfigError(f"Failed to save configuration: {str(e)}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Return the full configuration as a dictionary"""
        return self._config_data.copy()
    
    def to_json(self) -> str:
        """Return the full configuration as a JSON string"""
        return json.dumps(self._config_data, indent=2)
