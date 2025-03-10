"""
Ultrasonic Distance Sensor Implementation

This module provides a concrete implementation of the DistanceSensor interface
for HC-SR04 ultrasonic sensors commonly used in robotics projects.
"""

import time
import threading
import logging
from typing import Dict, List, Tuple, Optional, Any
import statistics

try:
    import RPi.GPIO as GPIO
    RPI_AVAILABLE = True
except ImportError:
    RPI_AVAILABLE = False
    # Use a mock for development on non-RPi systems
    from unittest.mock import MagicMock
    GPIO = MagicMock()

from ..interfaces import DistanceSensor


class UltrasonicSensor(DistanceSensor):
    """
    Implementation of HC-SR04 ultrasonic distance sensor
    
    Uses pulse timing to measure distance based on the speed of sound.
    """
    
    def __init__(self, config, name: str = "front"):
        """
        Initialize the ultrasonic sensor
        
        Args:
            config: Configuration manager
            name: Name/identifier for this sensor (e.g., "front", "left", "right")
        """
        self.logger = logging.getLogger(f"UltrasonicSensor_{name}")
        self.config = config
        self.name = name
        self._is_initialized = False
        
        # Find configuration for this sensor based on name
        ultrasonic_configs = config.get("hardware.sensors.ultrasonic", [])
        
        # Find the config that matches our name
        sensor_config = None
        for cfg in ultrasonic_configs:
            if isinstance(cfg, dict) and cfg.get("name") == name:
                sensor_config = cfg
                break
        
        # If no specific config found, use default values
        if sensor_config is None:
            self.logger.warning(f"No configuration found for ultrasonic sensor '{name}', using defaults")
            sensor_config = {}
        
        # Get configuration values with defaults
        self.trigger_pin = sensor_config.get("trigger_pin", 0)
        self.echo_pin = sensor_config.get("echo_pin", 0)
        self.max_distance = sensor_config.get("max_distance_m", 4.0)  # Max distance in meters
        self.min_distance = 0.02  # 2cm minimum reliable detection distance
        self.orientation = sensor_config.get("orientation_deg", 0)  # Orientation in degrees
        
        # State
        self._last_distance = -1.0
        self._distance_history = []  # For filtering/smoothing
        self._history_size = 5  # Number of readings to keep for filtering
        self._lock = threading.Lock()  # For thread safety
        
        # Timing constants
        self.SPEED_OF_SOUND = 343.0  # m/s at standard conditions
        self.MAX_TIMEOUT = 0.1  # Maximum wait time for echo pulse in seconds
        
        self.logger.debug(f"Ultrasonic sensor '{name}' configured with trigger_pin={self.trigger_pin}, echo_pin={self.echo_pin}")
    
    def initialize(self) -> bool:
        """Initialize the sensor hardware"""
        if not RPI_AVAILABLE:
            self.logger.warning("RPi.GPIO is not available, using mock implementation")
            self._is_initialized = True
            return True
        
        if self._is_initialized:
            return True
        
        try:
            # Set up GPIO pins
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.trigger_pin, GPIO.OUT)
            GPIO.setup(self.echo_pin, GPIO.IN)
            
            # Set trigger to low
            GPIO.output(self.trigger_pin, GPIO.LOW)
            time.sleep(0.1)  # Short delay to let the sensor settle
            
            self._is_initialized = True
            self.logger.info(f"Ultrasonic sensor '{self.name}' initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ultrasonic sensor '{self.name}': {e}")
            return False
    
    def get_distance(self) -> float:
        """
        Get the current distance measurement
        
        Returns:
            Distance in meters or -1 if error/no reading
        """
        if not self._is_initialized and not self.initialize():
            return -1.0
        
        # If GPIO is not available, return a simulated value
        if not RPI_AVAILABLE:
            # Return a simulated value between 0.5 and 2.0 meters
            import random
            distance = random.uniform(0.5, 2.0)
            self._update_distance_history(distance)
            return distance
        
        try:
            # Trigger a new measurement
            GPIO.output(self.trigger_pin, GPIO.HIGH)
            time.sleep(0.00001)  # 10 microsecond pulse
            GPIO.output(self.trigger_pin, GPIO.LOW)
            
            # Wait for echo pin to go high (start of echo pulse)
            start_time = time.time()
            while GPIO.input(self.echo_pin) == GPIO.LOW:
                if time.time() - start_time > self.MAX_TIMEOUT:
                    self.logger.debug(f"Echo timeout waiting for rising edge on '{self.name}'")
                    return self._last_distance
            
            pulse_start = time.time()
            
            # Wait for echo pin to go low (end of echo pulse)
            while GPIO.input(self.echo_pin) == GPIO.HIGH:
                if time.time() - pulse_start > self.MAX_TIMEOUT:
                    self.logger.debug(f"Echo timeout waiting for falling edge on '{self.name}'")
                    return self._last_distance
            
            pulse_end = time.time()
            
            # Calculate pulse duration and distance
            pulse_duration = pulse_end - pulse_start
            
            # Speed of sound is ~343 m/s, and the pulse goes out and back (divide by 2)
            distance = (pulse_duration * self.SPEED_OF_SOUND) / 2.0
            
            # Limit to valid range
            if distance < self.min_distance or distance > self.max_distance:
                self.logger.debug(f"Distance out of range: {distance:.2f}m on '{self.name}'")
                return self._last_distance
            
            # Update history and return
            self._update_distance_history(distance)
            return distance
            
        except Exception as e:
            self.logger.error(f"Error getting distance on '{self.name}': {e}")
            return self._last_distance
    
    def _update_distance_history(self, distance: float) -> None:
        """
        Update the distance history and calculate filtered distance
        
        Args:
            distance: New distance measurement
        """
        with self._lock:
            # Add to history
            self._distance_history.append(distance)
            
            # Limit history size
            if len(self._distance_history) > self._history_size:
                self._distance_history.pop(0)
            
            # Calculate median filtered distance
            if self._distance_history:
                self._last_distance = statistics.median(self._distance_history)
            else:
                self._last_distance = distance
    
    def is_obstacle_detected(self, threshold_distance: float) -> bool:
        """
        Check if an obstacle is detected within the threshold distance
        
        Args:
            threshold_distance: Distance threshold in meters
            
        Returns:
            True if obstacle is detected, False otherwise
        """
        distance = self.get_distance()
        if distance < 0:
            return False  # Error/no reading
        
        return distance <= threshold_distance
    
    def get_name(self) -> str:
        """Get the name/identifier of this sensor"""
        return self.name
    
    def get_min_distance(self) -> float:
        """Get the minimum measurable distance in meters"""
        return self.min_distance
    
    def get_max_distance(self) -> float:
        """Get the maximum measurable distance in meters"""
        return self.max_distance
    
    def cleanup(self) -> None:
        """Clean up resources used by the sensor"""
        if RPI_AVAILABLE and self._is_initialized:
            try:
                GPIO.cleanup(self.trigger_pin)
                GPIO.cleanup(self.echo_pin)
                self._is_initialized = False
                self.logger.debug(f"Cleaned up ultrasonic sensor '{self.name}'")
            except Exception as e:
                self.logger.error(f"Error cleaning up ultrasonic sensor '{self.name}': {e}")
