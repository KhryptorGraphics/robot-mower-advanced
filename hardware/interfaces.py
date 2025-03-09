"""
Hardware Component Interfaces

This module defines the interfaces (abstract classes) for all hardware components
to be used in the Robot Mower system. These interfaces establish contracts that
all concrete implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import Protocol, Dict, List, Optional, Tuple, Union, Any
from enum import Enum
import numpy as np


class PIDConfig:
    """PID controller configuration"""
    
    def __init__(self, p: float = 0.0, i: float = 0.0, d: float = 0.0, max_i: float = 100.0):
        self.p = p
        self.i = i
        self.d = d
        self.max_i = max_i


class MotorState(Enum):
    """Motor state enumeration"""
    STOPPED = 0
    FORWARD = 1
    REVERSE = 2
    BRAKING = 3
    ERROR = 4


class MotorController(ABC):
    """Interface for motor controllers"""
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the motor controller hardware"""
        pass
    
    @abstractmethod
    def set_speed(self, left_speed: float, right_speed: float) -> bool:
        """
        Set the speed of the left and right motors
        
        Args:
            left_speed: Speed of left motor (-1.0 to 1.0, negative for reverse)
            right_speed: Speed of right motor (-1.0 to 1.0, negative for reverse)
            
        Returns:
            Success or failure
        """
        pass
    
    @abstractmethod
    def move(self, direction: str, speed: float) -> bool:
        """
        Move in a specified direction
        
        Args:
            direction: Direction to move ("forward", "backward", "left", "right", "stop")
            speed: Speed to move at (0.0 to 1.0)
            
        Returns:
            Success or failure
        """
        pass
    
    @abstractmethod
    def stop(self) -> bool:
        """Stop all motors"""
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get the status of the motors"""
        pass
    
    @abstractmethod
    def set_pid_parameters(self, left_pid: PIDConfig, right_pid: PIDConfig) -> None:
        """Set PID control parameters for the motors"""
        pass
    
    @abstractmethod
    def get_encoder_counts(self) -> Tuple[int, int]:
        """Get the encoder counts for the left and right motors"""
        pass
    
    @abstractmethod
    def reset_encoder_counts(self) -> None:
        """Reset the encoder counts to zero"""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources used by the motor controller"""
        pass


class BladeController(ABC):
    """Interface for blade motor controllers"""
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the blade controller hardware"""
        pass
    
    @abstractmethod
    def set_speed(self, speed: float) -> bool:
        """
        Set the speed of the blade
        
        Args:
            speed: Speed value (0.0 to 1.0)
            
        Returns:
            Success or failure
        """
        pass
    
    @abstractmethod
    def start(self) -> bool:
        """Start the blade at the last set speed"""
        pass
    
    @abstractmethod
    def stop(self) -> bool:
        """Stop the blade"""
        pass
    
    @abstractmethod
    def is_running(self) -> bool:
        """Check if the blade is running"""
        pass
    
    @abstractmethod
    def get_speed(self) -> float:
        """Get the current speed of the blade (0.0 to 1.0)"""
        pass
    
    @abstractmethod
    def get_rpm(self) -> float:
        """Get the current RPM of the blade"""
        pass
    
    @abstractmethod
    def set_height(self, height_mm: int) -> bool:
        """
        Set the cutting height of the blade in millimeters
        
        Args:
            height_mm: Height in millimeters
            
        Returns:
            Success or failure
        """
        pass
    
    @abstractmethod
    def get_height(self) -> int:
        """Get the current cutting height in millimeters"""
        pass
    
    @abstractmethod
    def emergency_stop(self) -> bool:
        """Emergency stop the blade"""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources used by the blade controller"""
        pass


class DistanceSensor(ABC):
    """Interface for distance sensors (ultrasonic, lidar, etc.)"""
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the sensor hardware"""
        pass
    
    @abstractmethod
    def get_distance(self) -> float:
        """
        Get the current distance measurement
        
        Returns:
            Distance in meters
        """
        pass
    
    @abstractmethod
    def is_obstacle_detected(self, threshold_distance: float) -> bool:
        """
        Check if an obstacle is detected within the threshold distance
        
        Args:
            threshold_distance: Distance threshold in meters
            
        Returns:
            True if obstacle is detected, False otherwise
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the name/identifier of this sensor"""
        pass
    
    @abstractmethod
    def get_min_distance(self) -> float:
        """Get the minimum measurable distance in meters"""
        pass
    
    @abstractmethod
    def get_max_distance(self) -> float:
        """Get the maximum measurable distance in meters"""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources used by the sensor"""
        pass


class IMUSensor(ABC):
    """Interface for IMU (Inertial Measurement Unit) sensors"""
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the IMU sensor"""
        pass
    
    @abstractmethod
    def get_acceleration(self) -> Tuple[float, float, float]:
        """
        Get the current acceleration values
        
        Returns:
            Tuple of (x, y, z) acceleration in m/s²
        """
        pass
    
    @abstractmethod
    def get_gyroscope(self) -> Tuple[float, float, float]:
        """
        Get the current gyroscope values
        
        Returns:
            Tuple of (x, y, z) rotation rates in rad/s
        """
        pass
    
    @abstractmethod
    def get_orientation(self) -> Tuple[float, float, float]:
        """
        Get the current orientation
        
        Returns:
            Tuple of (roll, pitch, yaw) in radians
        """
        pass
    
    @abstractmethod
    def is_moving(self) -> bool:
        """
        Check if the IMU detects movement
        
        Returns:
            True if movement is detected, False otherwise
        """
        pass
    
    @abstractmethod
    def calibrate(self) -> bool:
        """
        Calibrate the IMU sensor
        
        Returns:
            Success or failure
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources used by the IMU sensor"""
        pass


class GPSPosition:
    """Represents a GPS position"""
    
    def __init__(self, latitude: float, longitude: float, altitude: float = 0.0, 
                 accuracy: float = 0.0, timestamp: float = 0.0):
        self.latitude = latitude
        self.longitude = longitude
        self.altitude = altitude
        self.accuracy = accuracy
        self.timestamp = timestamp
    
    def __str__(self) -> str:
        return f"({self.latitude:.6f}, {self.longitude:.6f}, alt: {self.altitude:.1f}m, acc: {self.accuracy:.1f}m)"


class GPSSensor(ABC):
    """Interface for GPS sensors"""
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the GPS sensor"""
        pass
    
    @abstractmethod
    def get_position(self) -> Optional[GPSPosition]:
        """
        Get the current GPS position
        
        Returns:
            GPSPosition object or None if position is not available
        """
        pass
    
    @abstractmethod
    def has_fix(self) -> bool:
        """
        Check if the GPS has a fix
        
        Returns:
            True if GPS has a fix, False otherwise
        """
        pass
    
    @abstractmethod
    def get_speed(self) -> float:
        """
        Get the current speed from GPS
        
        Returns:
            Speed in meters per second
        """
        pass
    
    @abstractmethod
    def get_heading(self) -> float:
        """
        Get the current heading from GPS
        
        Returns:
            Heading in degrees (0-359)
        """
        pass
    
    @abstractmethod
    def get_num_satellites(self) -> int:
        """
        Get the number of satellites in view
        
        Returns:
            Number of satellites
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources used by the GPS sensor"""
        pass


class PowerManagement(ABC):
    """Interface for power management and battery monitoring"""
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the power management system"""
        pass
    
    @abstractmethod
    def get_battery_voltage(self) -> float:
        """
        Get the current battery voltage
        
        Returns:
            Battery voltage in volts
        """
        pass
    
    @abstractmethod
    def get_battery_current(self) -> float:
        """
        Get the current battery current
        
        Returns:
            Battery current in amperes
        """
        pass
    
    @abstractmethod
    def get_battery_temperature(self) -> float:
        """
        Get the battery temperature
        
        Returns:
            Battery temperature in Celsius
        """
        pass
    
    @abstractmethod
    def get_battery_percentage(self) -> float:
        """
        Get the battery percentage
        
        Returns:
            Battery percentage (0-100)
        """
        pass
    
    @abstractmethod
    def is_charging(self) -> bool:
        """
        Check if the battery is currently charging
        
        Returns:
            True if charging, False otherwise
        """
        pass
    
    @abstractmethod
    def is_low_battery(self) -> bool:
        """
        Check if the battery is low
        
        Returns:
            True if battery is low, False otherwise
        """
        pass
    
    @abstractmethod
    def get_power_consumption(self) -> float:
        """
        Get the current power consumption
        
        Returns:
            Power consumption in watts
        """
        pass
    
    @abstractmethod
    def get_remaining_runtime(self) -> int:
        """
        Get the estimated remaining runtime
        
        Returns:
            Estimated runtime in minutes
        """
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """Shut down the system"""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources used by the power management system"""
        pass


class StatusIndicator(ABC):
    """Interface for status indicator hardware (LEDs, etc.)"""
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the status indicator hardware"""
        pass
    
    @abstractmethod
    def set_status(self, status: str, color: Optional[str] = None) -> None:
        """
        Set the status indicator
        
        Args:
            status: Status to indicate (e.g., "idle", "running", "error")
            color: Optional color to use (e.g., "red", "green", "blue")
        """
        pass
    
    @abstractmethod
    def set_error(self, error_code: int) -> None:
        """
        Signal an error with the given error code
        
        Args:
            error_code: Error code to indicate
        """
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all indicators"""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources used by the status indicator"""
        pass


class RainSensor(ABC):
    """Interface for rain sensors"""
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the rain sensor hardware"""
        pass
    
    @abstractmethod
    def is_raining(self) -> bool:
        """
        Check if rain is detected
        
        Returns:
            True if rain is detected, False otherwise
        """
        pass
    
    @abstractmethod
    def get_rain_intensity(self) -> float:
        """
        Get the rain intensity
        
        Returns:
            Rain intensity (0.0 to 1.0)
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources used by the rain sensor"""
        pass


class TiltSensor(ABC):
    """Interface for tilt sensors"""
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the tilt sensor hardware"""
        pass
    
    @abstractmethod
    def is_tilted(self) -> bool:
        """
        Check if the mower is tilted beyond a safe threshold
        
        Returns:
            True if tilted, False otherwise
        """
        pass
    
    @abstractmethod
    def get_tilt_angle(self) -> Tuple[float, float]:
        """
        Get the current tilt angle
        
        Returns:
            Tuple of (x_tilt, y_tilt) in degrees
        """
        pass
    
    @abstractmethod
    def is_upside_down(self) -> bool:
        """
        Check if the mower is upside down
        
        Returns:
            True if upside down, False otherwise
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources used by the tilt sensor"""
        pass


class Camera(ABC):
    """Interface for camera hardware"""
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the camera hardware"""
        pass
    
    @abstractmethod
    def capture_image(self) -> np.ndarray:
        """
        Capture a still image
        
        Returns:
            Image as numpy array
        """
        pass
    
    @abstractmethod
    def start_video_stream(self) -> bool:
        """
        Start the video stream
        
        Returns:
            Success or failure
        """
        pass
    
    @abstractmethod
    def stop_video_stream(self) -> None:
        """Stop the video stream"""
        pass
    
    @abstractmethod
    def get_frame(self) -> np.ndarray:
        """
        Get the latest frame from the video stream
        
        Returns:
            Frame as numpy array
        """
        pass
    
    @abstractmethod
    def set_resolution(self, width: int, height: int) -> bool:
        """
        Set the camera resolution
        
        Args:
            width: Width in pixels
            height: Height in pixels
            
        Returns:
            Success or failure
        """
        pass
    
    @abstractmethod
    def get_resolution(self) -> Tuple[int, int]:
        """
        Get the current camera resolution
        
        Returns:
            Tuple of (width, height) in pixels
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources used by the camera"""
        pass
