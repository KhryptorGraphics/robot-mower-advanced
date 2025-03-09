"""
Environmental Sensor Implementations

Provides concrete implementations of environmental sensors like
rain sensors, tilt sensors, and other environment monitoring devices.
"""

import time
import threading
import logging
import math
from typing import Tuple

try:
    import RPi.GPIO as GPIO
    RPI_AVAILABLE = True
except ImportError:
    RPI_AVAILABLE = False
    # Use a mock for development on non-RPi systems
    from unittest.mock import MagicMock
    GPIO = MagicMock()

from ..interfaces import RainSensor, TiltSensor
from ...core.config import ConfigManager


class DigitalRainSensor(RainSensor):
    """Implementation of a digital rain sensor"""
    
    def __init__(self, config: ConfigManager):
        """Initialize the rain sensor"""
        self.config = config
        self.logger = logging.getLogger("RainSensor")
        self._is_initialized = False
        
        # Get configuration
        self._enabled = config.get("hardware.sensors.rain_sensor.enable", True)
        self._pin = config.get("hardware.sensors.rain_sensor.pin", 27)
        
        # State
        self._is_raining = False
        self._rain_intensity = 0.0
        
        # Monitoring thread
        self._running = False
        self._monitor_thread = None
    
    def initialize(self) -> bool:
        """Initialize the rain sensor hardware"""
        if not self._enabled:
            self.logger.info("Rain sensor disabled in config")
            return False
        
        if not RPI_AVAILABLE:
            self.logger.error("RPi.GPIO is not available")
            return False
        
        if self._is_initialized:
            return True
        
        try:
            # Set up GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # Set up rain sensor pin with pull-up
            GPIO.setup(self._pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            # Add event detection
            GPIO.add_event_detect(self._pin, GPIO.BOTH, callback=self._rain_callback)
            
            # Start monitoring thread
            self._start_monitoring()
            
            self._is_initialized = True
            self.logger.info("Rain sensor initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing rain sensor: {str(e)}")
            # Clean up if initialization failed
            self.cleanup()
            return False
    
    def _rain_callback(self, channel) -> None:
        """Callback for rain sensor pin change"""
        # When pin is LOW, rain is detected (sensor is active-low)
        self._is_raining = GPIO.input(self._pin) == GPIO.LOW
        
        if self._is_raining:
            self.logger.info("Rain detected")
        else:
            self.logger.info("Rain stopped")
    
    def _start_monitoring(self) -> None:
        """Start the monitoring thread"""
        if self._running:
            return
        
        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="RainSensorThread"
        )
        self._monitor_thread.start()
    
    def _stop_monitoring(self) -> None:
        """Stop the monitoring thread"""
        self._running = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=1.0)
    
    def _monitor_loop(self) -> None:
        """Loop to monitor rain intensity"""
        rain_count = 0
        interval = 60  # 60 seconds
        last_update = time.time()
        
        while self._running and self._is_initialized:
            try:
                current_time = time.time()
                
                # Check if rain is currently detected
                if self._is_raining:
                    rain_count += 1
                
                # Update intensity every minute
                if current_time - last_update >= interval:
                    # Calculate intensity (0.0 to 1.0)
                    # Assume max rain is 60 counts per minute
                    self._rain_intensity = min(1.0, rain_count / 60.0)
                    
                    # Reset counters
                    rain_count = 0
                    last_update = current_time
                
                # Sleep to save CPU
                time.sleep(1.0)
                
            except Exception as e:
                self.logger.error(f"Error in rain monitoring: {str(e)}")
                time.sleep(1.0)
    
    def is_raining(self) -> bool:
        """Check if rain is detected"""
        if not self._is_initialized:
            return False
        
        return self._is_raining
    
    def get_rain_intensity(self) -> float:
        """Get the rain intensity (0.0 to 1.0)"""
        if not self._is_initialized:
            return 0.0
        
        return self._rain_intensity
    
    def cleanup(self) -> None:
        """Clean up resources used by the rain sensor"""
        self._stop_monitoring()
        
        if self._is_initialized and RPI_AVAILABLE:
            try:
                GPIO.remove_event_detect(self._pin)
                GPIO.cleanup(self._pin)
            except:
                pass
        
        self._is_initialized = False
        self.logger.info("Rain sensor cleaned up")


class DigitalTiltSensor(TiltSensor):
    """Implementation of a digital tilt sensor using an IMU or dedicated tilt switch"""
    
    def __init__(self, config: ConfigManager):
        """Initialize the tilt sensor"""
        self.config = config
        self.logger = logging.getLogger("TiltSensor")
        self._is_initialized = False
        
        # Get configuration
        self._enabled = config.get("hardware.sensors.tilt_sensor.enable", True)
        self._pin = config.get("hardware.sensors.tilt_sensor.pin", 22)
        self._use_imu = config.get("hardware.sensors.tilt_sensor.use_imu", False)
        
        # Tilt thresholds (in degrees)
        self._max_tilt_angle = config.get("hardware.sensors.tilt_sensor.max_tilt_angle", 30.0)
        self._upside_down_angle = config.get("hardware.sensors.tilt_sensor.upside_down_angle", 170.0)
        
        # State
        self._tilt_x = 0.0
        self._tilt_y = 0.0
        self._is_tilted = False
        self._is_upside_down = False
        
        # IMU reference (will be set if use_imu is True)
        self._imu = None
    
    def initialize(self) -> bool:
        """Initialize the tilt sensor hardware"""
        if not self._enabled:
            self.logger.info("Tilt sensor disabled in config")
            return False
        
        if self._is_initialized:
            return True
        
        try:
            if self._use_imu:
                # Using IMU for tilt detection
                # This would be set by the hardware factory
                self.logger.info("Using IMU for tilt detection")
                # The IMU will be injected later
                self._is_initialized = True
                return True
            else:
                # Using dedicated tilt switch
                if not RPI_AVAILABLE:
                    self.logger.error("RPi.GPIO is not available")
                    return False
                
                # Set up GPIO
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                
                # Set up tilt sensor pin with pull-up
                GPIO.setup(self._pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                
                # Add event detection
                GPIO.add_event_detect(self._pin, GPIO.BOTH, callback=self._tilt_callback)
                
                self._is_initialized = True
                self.logger.info("Tilt sensor initialized")
                return True
                
        except Exception as e:
            self.logger.error(f"Error initializing tilt sensor: {str(e)}")
            # Clean up if initialization failed
            self.cleanup()
            return False
    
    def _tilt_callback(self, channel) -> None:
        """Callback for tilt switch pin change"""
        # When pin is LOW, tilt is detected (sensor is active-low)
        self._is_tilted = GPIO.input(self._pin) == GPIO.LOW
        
        if self._is_tilted:
            self.logger.warning("Tilt detected")
        else:
            self.logger.info("Tilt resolved")
    
    def set_imu(self, imu) -> None:
        """Set the IMU reference for tilt detection"""
        self._imu = imu
        self._use_imu = True
    
    def is_tilted(self) -> bool:
        """Check if the mower is tilted beyond a safe threshold"""
        if not self._is_initialized:
            return False
        
        if self._use_imu and self._imu:
            # Get orientation from IMU
            roll, pitch, _ = self._imu.get_orientation()
            
            # Convert to degrees
            roll_deg = math.degrees(roll)
            pitch_deg = math.degrees(pitch)
            
            # Update tilt angles
            self._tilt_x = roll_deg
            self._tilt_y = pitch_deg
            
            # Check if tilted beyond threshold
            self._is_tilted = (abs(roll_deg) > self._max_tilt_angle or 
                              abs(pitch_deg) > self._max_tilt_angle)
            
            # Check if upside down
            self._is_upside_down = abs(roll_deg) > self._upside_down_angle
            
            return self._is_tilted
        else:
            # Using dedicated tilt switch
            return self._is_tilted
    
    def get_tilt_angle(self) -> Tuple[float, float]:
        """Get the current tilt angle in degrees"""
        if not self._is_initialized:
            return (0.0, 0.0)
        
        if self._use_imu and self._imu:
            # Get orientation from IMU
            roll, pitch, _ = self._imu.get_orientation()
            
            # Convert to degrees
            self._tilt_x = math.degrees(roll)
            self._tilt_y = math.degrees(pitch)
        
        return (self._tilt_x, self._tilt_y)
    
    def is_upside_down(self) -> bool:
        """Check if the mower is upside down"""
        if not self._is_initialized:
            return False
        
        if self._use_imu and self._imu:
            # Get orientation from IMU
            roll, pitch, _ = self._imu.get_orientation()
            
            # Convert to degrees
            roll_deg = math.degrees(roll)
            
            # Check if upside down (roll > 170 degrees)
            self._is_upside_down = abs(roll_deg) > self._upside_down_angle
            
            return self._is_upside_down
        else:
            # Using dedicated tilt switch, we can't differentiate
            # between tilted and upside down
            return False
    
    def cleanup(self) -> None:
        """Clean up resources used by the tilt sensor"""
        if not self._is_initialized:
            return
        
        if not self._use_imu and RPI_AVAILABLE:
            try:
                GPIO.remove_event_detect(self._pin)
                GPIO.cleanup(self._pin)
            except:
                pass
        
        self._is_initialized = False
        self.logger.info("Tilt sensor cleaned up")
