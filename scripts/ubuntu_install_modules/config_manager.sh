#!/bin/bash

# Template for creating the configuration manager
# This script is called by the main install_ubuntu_server.sh script

create_config_manager() {
    local install_dir=$1
    
    # Create core directory and required modules
    mkdir -p "${install_dir}/core"
    echo '"""Core functionality for Robot Mower Control Panel."""' > "${install_dir}/core/__init__.py"
    
    log "Creating configuration manager..."
    cat > "${install_dir}/core/config.py" << EOF
"""
Configuration manager for Robot Mower Control Panel.
"""

import os
import yaml
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages configuration for the Robot Mower Control Panel."""
    
    def __init__(self, config_dir):
        """Initialize configuration manager.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = config_dir
        self.config = {}
        self.load_config()
    
    def load_config(self):
        """Load configuration from files."""
        # Try to load local config first
        local_config_path = os.path.join(self.config_dir, 'local_config.yaml')
        default_config_path = os.path.join(self.config_dir, 'default_config.yaml')
        
        if os.path.exists(local_config_path):
            self._load_file(local_config_path)
        elif os.path.exists(default_config_path):
            self._load_file(default_config_path)
        else:
            logger.warning("No configuration file found")
    
    def _load_file(self, path):
        """Load configuration from a file.
        
        Args:
            path: Path to configuration file
        """
        try:
            with open(path, 'r') as f:
                self.config.update(yaml.safe_load(f) or {})
            logger.info(f"Loaded configuration from {path}")
        except Exception as e:
            logger.error(f"Error loading configuration from {path}: {e}")
    
    def get(self, key, default=None):
        """Get a configuration value.
        
        Args:
            key: Configuration key (dot-separated for nested keys)
            default: Default value if key is not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key, value):
        """Set a configuration value.
        
        Args:
            key: Configuration key (dot-separated for nested keys)
            value: Value to set
        """
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
EOF
}

# Create default configuration file
create_default_config() {
    local install_dir=$1
    
    log "Creating default configuration file..."
    mkdir -p "${install_dir}/config"
    
    cat > "${install_dir}/config/default_config.yaml" << EOF
# Robot Mower Control Panel Default Configuration

# Web interface configuration
web:
  host: "0.0.0.0"
  port: 7799
  debug: false
  enable_https: false
  ssl_cert: "/opt/robot-mower-control-panel/certs/cert.pem"
  ssl_key: "/opt/robot-mower-control-panel/certs/key.pem"

# SLAM map configuration
slam:
  map_resolution: 0.05  # meters per pixel
  map_size: 100.0  # meters
  max_range: 10.0  # meters

# Path planning configuration
path_planning:
  default_overlap: 15  # percent
  default_pattern: "parallel"  # parallel, spiral, contour
  obstacle_padding: 0.5  # meters

# Robot configuration
robot:
  max_speed: 0.5  # meters per second
  min_speed: 0.1  # meters per second
  max_turn_rate: 30.0  # degrees per second
  battery_low_threshold: 20  # percent
  blade_width: 0.25  # meters

# Security configuration
security:
  admin_username: "admin"
  admin_password_hash: "$2b$12$QZKJNBgYPF.MXbewTbhSQ.1tvVr0/l1Vj6dQZyd.Sf2tTK5F8NhLq"  # Default: admin123
  jwt_secret: "change_this_in_local_config"
  session_timeout: 3600  # seconds

# Logging configuration
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  max_file_size: 10485760  # 10 MB
  max_files: 5
EOF
}
