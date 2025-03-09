"""
RobotMower Advanced Hardware Module
==================================

Provides hardware abstractions, interfaces, and implementations
for interacting with the robot mower's physical components.
"""

# Export interfaces
from .interfaces import (
    MotorController, BladeController, 
    DistanceSensor, IMUSensor, GPSSensor, Camera,
    PowerManagement, StatusIndicator, RainSensor, TiltSensor,
    GPSPosition
)

# Export implementations
from .motor_controller import PWMMotorController
from .blade_controller import RPiBladeController, PWMBladeController

# Export sensor implementations
from .sensors import (
    UltrasonicSensor,
    MPU6050IMUSensor,
    NMEAGPSSensor,
    RaspberryPiCamera,
    SimplePowerMonitor,
    LEDStatusIndicator,
    DigitalRainSensor,
    DigitalTiltSensor
)

# Export factory
from .factory import HardwareFactory

__all__ = [
    # Interfaces
    'MotorController', 'BladeController', 
    'DistanceSensor', 'IMUSensor', 'GPSSensor', 'Camera',
    'PowerManagement', 'StatusIndicator', 'RainSensor', 'TiltSensor',
    'GPSPosition',
    
    # Implementations
    'PWMMotorController',
    'RPiBladeController', 'PWMBladeController',
    
    # Sensors
    'UltrasonicSensor',
    'MPU6050IMUSensor',
    'NMEAGPSSensor',
    'RaspberryPiCamera',
    'SimplePowerMonitor',
    'LEDStatusIndicator',
    'DigitalRainSensor',
    'DigitalTiltSensor',
    
    # Factory
    'HardwareFactory'
]
