"""
DEPRECATED: This module has been reorganized into separate files.

The sensor implementations have been moved to the 'sensors/' directory
for better organization and maintainability. Please use the modules in
that directory instead of this file.

Import path changes:
- from hardware.sensors import X  →  from hardware import X
                                  or from hardware.sensors.Y import X

See the hardware/sensors/README.md file for more information on the new structure.
"""

# Re-export sensor implementations from the new module structure
# This maintains backward compatibility but warns about deprecation
import warnings

warnings.warn(
    "The 'hardware.sensors' module is deprecated. "
    "Use the modules in 'hardware.sensors.*' instead.",
    DeprecationWarning,
    stacklevel=2
)

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

__all__ = [
    'UltrasonicSensor',
    'MPU6050IMUSensor',
    'NMEAGPSSensor',
    'RaspberryPiCamera',
    'SimplePowerMonitor',
    'LEDStatusIndicator',
    'DigitalRainSensor',
    'DigitalTiltSensor'
]
