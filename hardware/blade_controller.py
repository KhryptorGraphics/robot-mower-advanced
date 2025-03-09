"""
Blade Controller Implementation

Provides concrete implementations of the BladeController interface 
for controlling the mower cutting blade with safety features.
"""

import time
import threading
import logging
from typing import Dict, Any, Optional
import math

try:
    import RPi.GPIO as GPIO
    RPI_AVAILABLE = True
except ImportError:
    RPI_AVAILABLE = False
    # Use a mock for development on non-RPi systems
    from unittest.mock import MagicMock
    GPIO = MagicMock()

from .interfaces import BladeController
from ..core.config import ConfigManager


class BaseBladeController(BladeController):
    """Base class for blade controllers with common functionality"""
    
    def __init__(self, config: ConfigManager):
        """Initialize the blade controller"""
        self.config = config
        self.logger = logging.getLogger("BladeController")
        self._is_initialized = False
        
        # Blade state
        self._running = False
        self._speed = 0.0
        self._height_mm = config.get("autonomy.mowing.cutting_height", 35)  # Default height in mm
        
        # Safety features
        self._safety_enabled = config.get("hardware.blade_motor.safety_enabled", True)
        self._safety_timeout = config.get("hardware.blade_motor.safety_timeout", 5.0)  # seconds
        self._safety_timer = None
        self._emergency_stop_active = False
        
        # RPM calculation
        self._rpm = 0.0
        self._rpm_counter = 0
        self._rpm_last_time = time.time()
        self._rpm_lock = threading.Lock()
    
    def set_speed(self, speed: float) -> bool:
        """
        Set the speed of the blade
        
        Args:
            speed: Speed value (0.0 to 1.0)
            
        Returns:
            Success or failure
        """
        if not self._is_initialized:
            self.logger.error("Blade controller not initialized")
            return False
        
        if self._emergency_stop_active:
            self.logger.warning("Cannot set speed - emergency stop is active")
            return False
        
        # Clamp speed to valid range
        speed = max(0.0, min(1.0, speed))
        
        # Store the speed value
        self._speed = speed
        
        # Actual implementation in subclass
        return True
    
    def start(self) -> bool:
        """Start the blade at the last set speed"""
        if not self._is_initialized:
            self.logger.error("Blade controller not initialized")
            return False
        
        if self._emergency_stop_active:
            self.logger.warning("Cannot start blade - emergency stop is active")
            return False
        
        if self._running:
            # Already running
            return True
        
        self._running = True
        
        # Start safety timer if enabled
        if self._safety_enabled:
            self._start_safety_timer()
        
        self.logger.info(f"Blade started with speed {self._speed:.1f}")
        return True
    
    def stop(self) -> bool:
        """Stop the blade"""
        if not self._is_initialized:
            return False
        
        if not self._running:
            # Already stopped
            return True
        
        self._running = False
        
        # Cancel safety timer
        if self._safety_timer:
            self._safety_timer.cancel()
            self._safety_timer = None
        
        self.logger.info("Blade stopped")
        return True
    
    def is_running(self) -> bool:
        """Check if the blade is running"""
        return self._running
    
    def get_speed(self) -> float:
        """Get the current speed of the blade (0.0 to 1.0)"""
        return self._speed
    
    def get_rpm(self) -> float:
        """Get the current RPM of the blade"""
        return self._rpm
    
    def set_height(self, height_mm: int) -> bool:
        """
        Set the cutting height of the blade in millimeters
        
        Args:
            height_mm: Height in millimeters
            
        Returns:
            Success or failure
        """
        # Validate height range (depends on hardware)
        min_height = self.config.get("hardware.blade_motor.min_height", 20)
        max_height = self.config.get("hardware.blade_motor.max_height", 80)
        
        if height_mm < min_height or height_mm > max_height:
            self.logger.warning(f"Height {height_mm} mm is outside valid range ({min_height}-{max_height} mm)")
            return False
        
        # Store the height value
        self._height_mm = height_mm
        
        # Implementation specific to hardware in subclass
        self.logger.info(f"Blade height set to {height_mm} mm")
        return True
    
    def get_height(self) -> int:
        """Get the current cutting height in millimeters"""
        return self._height_mm
    
    def emergency_stop(self) -> bool:
        """Emergency stop the blade"""
        self._emergency_stop_active = True
        self.stop()
        self.logger.warning("Blade emergency stop activated")
        return True
    
    def _start_safety_timer(self) -> None:
        """Start safety timer that will stop the blade if not reset"""
        if self._safety_timer:
            self._safety_timer.cancel()
        
        self._safety_timer = threading.Timer(self._safety_timeout, self._safety_timeout_callback)
        self._safety_timer.daemon = True
        self._safety_timer.start()
    
    def _safety_timeout_callback(self) -> None:
        """Called when safety timer expires"""
        self.logger.warning("Safety timeout expired - stopping blade")
        self.stop()
    
    def _reset_safety_timer(self) -> None:
        """Reset the safety timer to prevent automatic stop"""
        if self._safety_enabled and self._running:
            self._start_safety_timer()
    
    def _rpm_sensor_callback(self, channel) -> None:
        """Callback for RPM sensor input"""
        with self._rpm_lock:
            self._rpm_counter += 1
    
    def _update_rpm(self) -> None:
        """Update the calculated RPM value"""
        current_time = time.time()
        with self._rpm_lock:
            elapsed = current_time - self._rpm_last_time
            
            # Calculate RPM if at least 0.5 seconds has passed
            if elapsed >= 0.5:
                # Convert counter to RPM
                pulses_per_rev = self.config.get("hardware.blade_motor.pulses_per_rev", 1)
                self._rpm = (self._rpm_counter / pulses_per_rev) * (60.0 / elapsed)
                
                # Reset counter and timer
                self._rpm_counter = 0
                self._rpm_last_time = current_time


class RPiBladeController(BaseBladeController):
    """Blade controller implementation for Raspberry Pi GPIO"""
    
    def __init__(self, config: ConfigManager):
        """Initialize the blade controller"""
        super().__init__(config)
        
        # Get pin configuration
        self._enable_pin = config.get("hardware.blade_motor.enable_pin", 5)
        self._pwm_pin = config.get("hardware.blade_motor.pwm_pin", 6)
        self._speed_sensor_pin = config.get("hardware.blade_motor.speed_sensor_pin", 12)
        self._safety_switch_pin = config.get("hardware.blade_motor.safety_switch_pin", 13)
        
        # Height adjustment pins (servo or stepper motor)
        self._height_enable_pin = config.get("hardware.blade_motor.height_enable_pin", None)
        self._height_dir_pin = config.get("hardware.blade_motor.height_dir_pin", None)
        self._height_step_pin = config.get("hardware.blade_motor.height_step_pin", None)
        self._height_feedback_pin = config.get("hardware.blade_motor.height_feedback_pin", None)
        
        # PWM settings
        self._pwm_frequency = config.get("hardware.blade_motor.pwm_frequency", 1000)
        self._pwm = None
        
        # Height control settings
        self._use_servo_height = config.get("hardware.blade_motor.use_servo_height", False)
        self._height_servo = None
        self._height_servo_min = config.get("hardware.blade_motor.height_servo_min", 0)
        self._height_servo_max = config.get("hardware.blade_motor.height_servo_max", 180)
        
        # Monitoring thread
        self._monitor_thread = None
        self._monitoring = False
    
    def initialize(self) -> bool:
        """Initialize the blade controller hardware"""
        if not RPI_AVAILABLE:
            self.logger.error("RPi.GPIO is not available")
            return False
        
        if self._is_initialized:
            return True
        
        try:
            # Set up GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # Set up blade motor pins
            GPIO.setup(self._enable_pin, GPIO.OUT)
            GPIO.setup(self._pwm_pin, GPIO.OUT)
            GPIO.output(self._enable_pin, GPIO.LOW)
            
            # Set up speed sensor pin
            GPIO.setup(self._speed_sensor_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(self._speed_sensor_pin, GPIO.RISING, callback=self._rpm_sensor_callback)
            
            # Set up safety switch pin
            GPIO.setup(self._safety_switch_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(self._safety_switch_pin, GPIO.FALLING, callback=self._safety_switch_callback)
            
            # Set up height adjustment pins
            if self._use_servo_height:
                # Use servo for height adjustment
                try:
                    import pigpio
                    self._pigpio = pigpio.pi()
                    if not self._pigpio.connected:
                        self.logger.warning("Failed to connect to pigpio daemon")
                        self._use_servo_height = False
                    else:
                        # Height servo pin should be set
                        if self._height_enable_pin is not None:
                            self._height_servo = self._height_enable_pin
                except ImportError:
                    self.logger.warning("pigpio not available, servo height control disabled")
                    self._use_servo_height = False
            elif (self._height_enable_pin is not None and
                 self._height_dir_pin is not None and
                 self._height_step_pin is not None):
                # Use stepper motor for height adjustment
                GPIO.setup(self._height_enable_pin, GPIO.OUT)
                GPIO.setup(self._height_dir_pin, GPIO.OUT)
                GPIO.setup(self._height_step_pin, GPIO.OUT)
                
                # Initialize to disabled
                GPIO.output(self._height_enable_pin, GPIO.HIGH)  # Most stepper drivers use HIGH for disable
            
            # Set up PWM for blade speed control
            self._pwm = GPIO.PWM(self._pwm_pin, self._pwm_frequency)
            self._pwm.start(0)
            
            # Start monitoring thread
            self._start_monitoring()
            
            self._is_initialized = True
            self.logger.info("Blade controller initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing blade controller: {str(e)}")
            # Clean up if initialization failed
            self.cleanup()
            return False
    
    def set_speed(self, speed: float) -> bool:
        """Set the speed of the blade"""
        # Call the base method to check initialization and safety
        if not super().set_speed(speed):
            return False
        
        # Apply PWM duty cycle
        duty = speed * 100.0
        self._pwm.ChangeDutyCycle(duty)
        
        # Enable the blade motor if speed > 0
        if speed > 0:
            GPIO.output(self._enable_pin, GPIO.HIGH)
            
            # Start the blade if not already running
            if not self._running:
                self.start()
        else:
            # Stop the blade if speed is 0
            if self._running:
                self.stop()
        
        return True
    
    def stop(self) -> bool:
        """Stop the blade"""
        # Call the base method to handle common functionality
        if not super().stop():
            return False
        
        # Disable the blade motor
        GPIO.output(self._enable_pin, GPIO.LOW)
        self._pwm.ChangeDutyCycle(0)
        
        return True
    
    def set_height(self, height_mm: int) -> bool:
        """Set the cutting height of the blade in millimeters"""
        # Call the base method to validate height and update stored value
        if not super().set_height(height_mm):
            return False
        
        if not self._is_initialized:
            return False
        
        # Implement height adjustment based on the hardware
        if self._use_servo_height and self._height_servo is not None:
            try:
                # Map height to servo position
                min_height = self.config.get("hardware.blade_motor.min_height", 20)
                max_height = self.config.get("hardware.blade_motor.max_height", 80)
                
                # Calculate servo position (map height range to servo range)
                height_range = max_height - min_height
                height_percent = (height_mm - min_height) / height_range
                
                servo_range = self._height_servo_max - self._height_servo_min
                servo_pos = int(self._height_servo_min + (height_percent * servo_range))
                
                # Set servo position
                self._pigpio.set_servo_pulsewidth(self._height_servo, servo_pos)
                
                self.logger.info(f"Height servo set to position {servo_pos}")
                return True
            except Exception as e:
                self.logger.error(f"Error setting servo height: {str(e)}")
                return False
        elif (self._height_enable_pin is not None and
             self._height_dir_pin is not None and
             self._height_step_pin is not None):
            try:
                # Use stepper motor control for height
                # This is a simplified implementation
                
                # Calculate target position
                current_height = self._height_mm
                steps_per_mm = self.config.get("hardware.blade_motor.steps_per_mm", 10)
                
                # Calculate steps needed
                steps = int(abs(height_mm - current_height) * steps_per_mm)
                
                # Set direction
                direction = height_mm > current_height
                GPIO.output(self._height_dir_pin, GPIO.HIGH if direction else GPIO.LOW)
                
                # Enable stepper driver
                GPIO.output(self._height_enable_pin, GPIO.LOW)  # Most stepper drivers use LOW for enable
                
                # Step the motor
                step_delay = 0.001  # 1ms between steps
                for _ in range(steps):
                    GPIO.output(self._height_step_pin, GPIO.HIGH)
                    time.sleep(step_delay)
                    GPIO.output(self._height_step_pin, GPIO.LOW)
                    time.sleep(step_delay)
                
                # Disable stepper driver
                GPIO.output(self._height_enable_pin, GPIO.HIGH)
                
                self.logger.info(f"Height adjusted to {height_mm}mm using {steps} steps")
                return True
            except Exception as e:
                self.logger.error(f"Error adjusting height with stepper motor: {str(e)}")
                # Disable stepper driver in case of error
                GPIO.output(self._height_enable_pin, GPIO.HIGH)
                return False
        else:
            # No height adjustment hardware defined
            self.logger.warning("No height adjustment hardware configured")
            return False
    
    def _safety_switch_callback(self, channel) -> None:
        """Callback for safety switch (emergency stop)"""
        # Check if the safety switch is actually triggered (LOW)
        if GPIO.input(self._safety_switch_pin) == GPIO.LOW:
            self.logger.warning("Safety switch triggered - emergency stop")
            self.emergency_stop()
    
    def _start_monitoring(self) -> None:
        """Start the monitoring thread"""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="BladeMonitoring"
        )
        self._monitor_thread.start()
    
    def _stop_monitoring(self) -> None:
        """Stop the monitoring thread"""
        self._monitoring = False
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=1.0)
    
    def _monitoring_loop(self) -> None:
        """Background thread for blade monitoring"""
        while self._monitoring and self._is_initialized:
            # Update RPM calculation
            self._update_rpm()
            
            # Reset safety timer if blade is running
            if self._running and self._safety_enabled:
                self._reset_safety_timer()
            
            # Check if we should stop the blade due to zero speed
            if self._running and self._speed == 0:
                self.stop()
            
            # Check for stall (blade rotating too slowly while power is applied)
            if self._running and self._speed > 0.3 and self._rpm < 100:
                self.logger.warning("Possible blade stall detected (low RPM while power applied)")
            
            # Sleep to control monitoring rate
            time.sleep(0.5)
    
    def cleanup(self) -> None:
        """Clean up resources used by the blade controller"""
        self._stop_monitoring()
        
        if self._pwm:
            self._pwm.stop()
        
        # Cancel safety timer if active
        if self._safety_timer:
            self._safety_timer.cancel()
            self._safety_timer = None
        
        # Stop blade
        self.stop()
        
        # Clean up GPIO pins
        if self._is_initialized:
            # Remove event detection
            try:
                GPIO.remove_event_detect(self._speed_sensor_pin)
                GPIO.remove_event_detect(self._safety_switch_pin)
            except:
                pass
            
            # Clean up specific pins
            pins_to_cleanup = [
                self._enable_pin, self._pwm_pin, self._speed_sensor_pin, self._safety_switch_pin
            ]
            
            if not self._use_servo_height:
                # Add stepper pins if used
                if self._height_enable_pin is not None:
                    pins_to_cleanup.append(self._height_enable_pin)
                if self._height_dir_pin is not None:
                    pins_to_cleanup.append(self._height_dir_pin)
                if self._height_step_pin is not None:
                    pins_to_cleanup.append(self._height_step_pin)
            
            # Clean up each pin
            for pin in pins_to_cleanup:
                if pin is not None and GPIO.getmode() is not None:
                    try:
                        GPIO.cleanup(pin)
                    except:
                        pass
        
        # Clean up servo if used
        if self._use_servo_height and hasattr(self, '_pigpio') and self._pigpio.connected:
            if self._height_servo is not None:
                try:
                    self._pigpio.set_servo_pulsewidth(self._height_servo, 0)
                except:
                    pass
            self._pigpio.stop()
        
        self._is_initialized = False
        self.logger.info("Blade controller cleaned up")


class PWMBladeController(RPiBladeController):
    """Simplified blade controller that just uses PWM without additional features"""
    
    def __init__(self, config: ConfigManager):
        """Initialize the blade controller with simplified config"""
        # Just inherit from the full implementation
        super().__init__(config)
