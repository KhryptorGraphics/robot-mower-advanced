"""
Status Indicator Implementations

Provides concrete implementations of status indicators like LEDs,
buzzers, or displays for visual and auditory feedback.
"""

import time
import threading
import logging
from typing import Optional

try:
    import RPi.GPIO as GPIO
    RPI_AVAILABLE = True
except ImportError:
    RPI_AVAILABLE = False
    # Use a mock for development on non-RPi systems
    from unittest.mock import MagicMock
    GPIO = MagicMock()

from ..interfaces import StatusIndicator
from ...core.config import ConfigManager


class LEDStatusIndicator(StatusIndicator):
    """Status indicator using LEDs connected to GPIO pins"""
    
    def __init__(self, config: ConfigManager):
        """Initialize the status indicator"""
        self.config = config
        self.logger = logging.getLogger("StatusIndicator")
        self._is_initialized = False
        
        # Get configuration
        self._green_led_pin = config.get("hardware.sensors.leds.status_led_green", 12)
        self._red_led_pin = config.get("hardware.sensors.leds.status_led_red", 13)
        self._blue_led_pin = config.get("hardware.sensors.leds.status_led_blue", 14)
        
        # State
        self._current_status = "idle"
    
    def initialize(self) -> bool:
        """Initialize the status indicator hardware"""
        if not RPI_AVAILABLE:
            self.logger.error("RPi.GPIO is not available")
            return False
        
        if self._is_initialized:
            return True
        
        try:
            # Set up GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # Set up LED pins
            for pin in [self._green_led_pin, self._red_led_pin, self._blue_led_pin]:
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.LOW)
            
            self._is_initialized = True
            self.logger.info("Status indicator initialized")
            
            # Set initial status
            self.set_status("idle")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing status indicator: {str(e)}")
            # Clean up if initialization failed
            self.cleanup()
            return False
    
    def set_status(self, status: str, color: Optional[str] = None) -> None:
        """
        Set the status indicator
        
        Args:
            status: Status to indicate (e.g., "idle", "running", "error")
            color: Optional color to use (e.g., "red", "green", "blue")
        """
        if not self._is_initialized:
            self.logger.error("Status indicator not initialized")
            return
        
        self._current_status = status
        
        # If color is specified, use it
        if color:
            self._set_color(color)
            return
        
        # Otherwise, set color based on status
        if status == "idle":
            self._set_color("green")
        elif status == "running":
            self._set_color("blue")
        elif status == "error":
            self._set_color("red")
        elif status == "charging":
            self._set_color("yellow")  # Green + Red
        elif status == "low_battery":
            self._set_color("purple")  # Red + Blue
        else:
            self._set_color("off")
    
    def _set_color(self, color: str) -> None:
        """Set the LED color"""
        # Turn all LEDs off first
        GPIO.output(self._red_led_pin, GPIO.LOW)
        GPIO.output(self._green_led_pin, GPIO.LOW)
        GPIO.output(self._blue_led_pin, GPIO.LOW)
        
        # Set color
        if color == "red":
            GPIO.output(self._red_led_pin, GPIO.HIGH)
        elif color == "green":
            GPIO.output(self._green_led_pin, GPIO.HIGH)
        elif color == "blue":
            GPIO.output(self._blue_led_pin, GPIO.HIGH)
        elif color == "yellow":
            GPIO.output(self._red_led_pin, GPIO.HIGH)
            GPIO.output(self._green_led_pin, GPIO.HIGH)
        elif color == "purple":
            GPIO.output(self._red_led_pin, GPIO.HIGH)
            GPIO.output(self._blue_led_pin, GPIO.HIGH)
        elif color == "cyan":
            GPIO.output(self._green_led_pin, GPIO.HIGH)
            GPIO.output(self._blue_led_pin, GPIO.HIGH)
        elif color == "white":
            GPIO.output(self._red_led_pin, GPIO.HIGH)
            GPIO.output(self._green_led_pin, GPIO.HIGH)
            GPIO.output(self._blue_led_pin, GPIO.HIGH)
    
    def set_error(self, error_code: int) -> None:
        """Signal an error with the given error code"""
        if not self._is_initialized:
            return
        
        self.logger.warning(f"Error code {error_code} signaled")
        
        # Set status to error
        self.set_status("error")
        
        # Blink red LED to indicate error code
        # This is a non-blocking implementation that blinks in the background
        threading.Thread(
            target=self._blink_error_code,
            args=(error_code,),
            daemon=True
        ).start()
    
    def _blink_error_code(self, error_code: int) -> None:
        """Blink the red LED to indicate an error code"""
        # Save original state
        original_status = self._current_status
        
        # Blink the error code
        for _ in range(3):  # Repeat the pattern 3 times
            # Off period
            GPIO.output(self._red_led_pin, GPIO.LOW)
            GPIO.output(self._green_led_pin, GPIO.LOW)
            GPIO.output(self._blue_led_pin, GPIO.LOW)
            time.sleep(1.0)
            
            # Blink error code
            for i in range(error_code):
                GPIO.output(self._red_led_pin, GPIO.HIGH)
                time.sleep(0.2)
                GPIO.output(self._red_led_pin, GPIO.LOW)
                time.sleep(0.2)
            
            # Wait between repetitions
            time.sleep(1.0)
        
        # Restore original state
        self.set_status(original_status)
    
    def clear(self) -> None:
        """Clear all indicators"""
        if not self._is_initialized:
            return
        
        # Turn all LEDs off
        GPIO.output(self._red_led_pin, GPIO.LOW)
        GPIO.output(self._green_led_pin, GPIO.LOW)
        GPIO.output(self._blue_led_pin, GPIO.LOW)
        
        self._current_status = "off"
    
    def cleanup(self) -> None:
        """Clean up resources used by the status indicator"""
        if not self._is_initialized:
            return
        
        # Clear all indicators
        self.clear()
        
        # Clean up GPIO
        for pin in [self._red_led_pin, self._green_led_pin, self._blue_led_pin]:
            try:
                GPIO.cleanup(pin)
            except:
                pass
        
        self._is_initialized = False
        self.logger.info("Status indicator cleaned up")
