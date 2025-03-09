"""
RobotMower Advanced Sensors Module
==================================

Provides sensor implementations for the RobotMower system.
This module organizes sensors by type into separate modules
for better maintainability and organization.
"""

# Import all sensor implementations
from .distance import UltrasonicSensor
from .imu import MPU6050IMUSensor
from .gps import NMEAGPSSensor
from .camera import RaspberryPiCamera
from .power import SimplePowerMonitor
from .indicators import LEDStatusIndicator
from .environment import DigitalRainSensor, DigitalTiltSensor

__all__ = [
    # Distance sensors
    'UltrasonicSensor',
    
    # IMU sensors
    'MPU6050IMUSensor',
    
    # GPS sensors
    'NMEAGPSSensor',
    
    # Camera implementations
    'RaspberryPiCamera',
    
    # Power management
    'SimplePowerMonitor',
    
    # Status indicators
    'LEDStatusIndicator',
    
    # Environmental sensors
    'DigitalRainSensor',
    'DigitalTiltSensor'
]
