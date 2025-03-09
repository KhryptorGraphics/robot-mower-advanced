"""
RobotMower Advanced Core Module
===============================

Core functionality for the RobotMower system, handling
configuration, logging, and dependency injection.
"""

from .config import ConfigManager
from .logger import LogManager
from .application import Application
from .dependency_injection import Container

__all__ = ['ConfigManager', 'LogManager', 'Application', 'Container']
