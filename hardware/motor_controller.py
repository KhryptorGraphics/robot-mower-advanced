"""
Motor Controller Implementation

Provides concrete implementations of the MotorController interface 
for different hardware configurations.
"""

import time
import threading
import logging
from typing import Dict, Tuple, Any, Optional, List, Callable
import math

try:
    import RPi.GPIO as GPIO
    RPI_AVAILABLE = True
except ImportError:
    RPI_AVAILABLE = False
    # Use a mock for development on non-RPi systems
    from unittest.mock import MagicMock
    GPIO = MagicMock()

from .interfaces import MotorController, PIDConfig, MotorState
from ..core.config import ConfigManager


class PIDController:
    """PID controller implementation for motor speed control"""
    
    def __init__(self, p: float = 0.0, i: float = 0.0, d: float = 0.0, max_i: float = 100.0):
        self.kp = p
        self.ki = i
        self.kd = d
        self.max_i = max_i
        
        self.previous_error = 0.0
        self.integral = 0.0
        self.last_time = time.time()
    
    def update(self, setpoint: float, process_variable: float) -> float:
        """
        Update the PID controller with a new setpoint and process_variable
        
        Args:
            setpoint: Desired value
            process_variable: Current measured value
            
        Returns:
            Control output
        """
        current_time = time.time()
        dt = current_time - self.last_time
        
        # Avoid division by zero and ensure dt is reasonable
        if dt < 0.001:
            dt = 0.001
        
        # Calculate error
        error = setpoint - process_variable
        
        # Proportional term
        p_term = self.kp * error
        
        # Integral term
        self.integral += error * dt
        # Apply anti-windup
        self.integral = max(-self.max_i, min(self.integral, self.max_i))
        i_term = self.ki * self.integral
        
        # Derivative term (on change in process variable, not error)
        d_term = self.kd * (error - self.previous_error) / dt if dt > 0 else 0
        
        # Store values for next iteration
        self.previous_error = error
        self.last_time = current_time
        
        # Calculate output
        output = p_term + i_term + d_term
        
        return output
    
    def reset(self) -> None:
        """Reset the PID controller"""
        self.previous_error = 0.0
        self.integral = 0.0
        self.last_time = time.time()


class BaseMotorController(MotorController):
    """Base class for motor controllers with common functionality"""
    
    def __init__(self, config: ConfigManager):
        """Initialize the motor controller"""
        self.config = config
        self.logger = logging.getLogger("MotorController")
        self._is_initialized = False
        
        # Motor state
        self._left_motor_state = MotorState.STOPPED
        self._right_motor_state = MotorState.STOPPED
        self._left_speed = 0.0
        self._right_speed = 0.0
        
        # Safety features
        self._safety_stop = False
        self._max_acceleration = 0.5  # Change in speed per second
        self._min_safe_voltage = 12.0
        
        # PID controllers
        left_pid_config = self._get_pid_config('left_motor')
        right_pid_config = self._get_pid_config('right_motor')
        
        self._left_pid = PIDController(
            p=left_pid_config.p,
            i=left_pid_config.i,
            d=left_pid_config.d,
            max_i=left_pid_config.max_i
        )
        self._right_pid = PIDController(
            p=right_pid_config.p,
            i=right_pid_config.i,
            d=right_pid_config.d,
            max_i=right_pid_config.max_i
        )
        
        # Encoder counts
        self._left_encoder_count = 0
        self._right_encoder_count = 0
        self._left_encoder_prev = 0
        self._right_encoder_prev = 0
        self._encoder_lock = threading.Lock()
        
        # Control loop
        self._control_loop_running = False
        self._control_loop_thread = None
    
    def _get_pid_config(self, motor_name: str) -> PIDConfig:
        """Get PID configuration for the specified motor"""
        pid_config = PIDConfig()
        
        # Get PID parameters from config
        pid_config.p = self.config.get(f"hardware.motors.{motor_name}.pid.p", 0.5)
        pid_config.i = self.config.get(f"hardware.motors.{motor_name}.pid.i", 0.1)
        pid_config.d = self.config.get(f"hardware.motors.{motor_name}.pid.d", 0.05)
        pid_config.max_i = self.config.get(f"hardware.motors.{motor_name}.pid.max_i", 50)
        
        return pid_config
    
    def set_pid_parameters(self, left_pid: PIDConfig, right_pid: PIDConfig) -> None:
        """Set PID control parameters for the motors"""
        self._left_pid.kp = left_pid.p
        self._left_pid.ki = left_pid.i
        self._left_pid.kd = left_pid.d
        self._left_pid.max_i = left_pid.max_i
        
        self._right_pid.kp = right_pid.p
        self._right_pid.ki = right_pid.i
        self._right_pid.kd = right_pid.d
        self._right_pid.max_i = right_pid.max_i
        
        # Reset PID controllers
        self._left_pid.reset()
        self._right_pid.reset()
    
    def move(self, direction: str, speed: float) -> bool:
        """
        Move in a specified direction
        
        Args:
            direction: Direction to move ("forward", "backward", "left", "right", "stop")
            speed: Speed to move at (0.0 to 1.0)
            
        Returns:
            Success or failure
        """
        # Clamp speed to valid range
        speed = max(0.0, min(1.0, speed))
        
        if direction == "forward":
            return self.set_speed(speed, speed)
        elif direction == "backward":
            return self.set_speed(-speed, -speed)
        elif direction == "left":
            return self.set_speed(-speed * 0.5, speed)
        elif direction == "right":
            return self.set_speed(speed, -speed * 0.5)
        elif direction == "stop":
            return self.stop()
        else:
            self.logger.warning(f"Invalid direction: {direction}")
            return False
    
    def get_encoder_counts(self) -> Tuple[int, int]:
        """Get the encoder counts for the left and right motors"""
        with self._encoder_lock:
            return self._left_encoder_count, self._right_encoder_count
    
    def reset_encoder_counts(self) -> None:
        """Reset the encoder counts to zero"""
        with self._encoder_lock:
            self._left_encoder_count = 0
            self._right_encoder_count = 0
            self._left_encoder_prev = 0
            self._right_encoder_prev = 0
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of the motors"""
        left_encoder, right_encoder = self.get_encoder_counts()
        
        return {
            "left_motor": {
                "state": self._left_motor_state.name,
                "speed": self._left_speed,
                "encoder_count": left_encoder
            },
            "right_motor": {
                "state": self._right_motor_state.name,
                "speed": self._right_speed,
                "encoder_count": right_encoder
            },
            "safety_stop": self._safety_stop
        }
    
    def _start_control_loop(self) -> None:
        """Start the control loop thread"""
        if self._control_loop_running:
            return
        
        self._control_loop_running = True
        self._control_loop_thread = threading.Thread(
            target=self._control_loop,
            daemon=True,
            name="MotorControlLoop"
        )
        self._control_loop_thread.start()
    
    def _stop_control_loop(self) -> None:
        """Stop the control loop thread"""
        self._control_loop_running = False
        if self._control_loop_thread and self._control_loop_thread.is_alive():
            self._control_loop_thread.join(timeout=1.0)
    
    def _control_loop(self) -> None:
        """Control loop for PID control"""
        # To be implemented by subclasses
        pass
    
    def _left_encoder_callback(self, channel) -> None:
        """Callback for left encoder pulses"""
        with self._encoder_lock:
            self._left_encoder_count += 1
    
    def _right_encoder_callback(self, channel) -> None:
        """Callback for right encoder pulses"""
        with self._encoder_lock:
            self._right_encoder_count += 1
    
    def _ramp_speed(self, current: float, target: float, max_change: float) -> float:
        """
        Ramp speed to avoid sudden changes
        
        Args:
            current: Current speed
            target: Target speed
            max_change: Maximum change in speed
            
        Returns:
            New speed
        """
        if target > current:
            return min(current + max_change, target)
        else:
            return max(current - max_change, target)
    
    def _emergency_stop(self) -> None:
        """Emergency stop all motors"""
        self._safety_stop = True
        self.stop()
        self.logger.warning("Emergency stop triggered")


class RPiMotorController(BaseMotorController):
    """Motor controller implementation for Raspberry Pi GPIO"""
    
    def __init__(self, config: ConfigManager):
        """Initialize the motor controller"""
        super().__init__(config)
        
        # Get pin configuration
        self._left_enable_pin = config.get("hardware.motors.left_motor.enable_pin", 17)
        self._left_forward_pin = config.get("hardware.motors.left_motor.forward_pin", 27)
        self._left_reverse_pin = config.get("hardware.motors.left_motor.reverse_pin", 22)
        self._left_encoder_pin = config.get("hardware.motors.left_motor.encoder_pin", 10)
        
        self._right_enable_pin = config.get("hardware.motors.right_motor.enable_pin", 23)
        self._right_forward_pin = config.get("hardware.motors.right_motor.forward_pin", 24)
        self._right_reverse_pin = config.get("hardware.motors.right_motor.reverse_pin", 25)
        self._right_encoder_pin = config.get("hardware.motors.right_motor.encoder_pin", 11)
        
        # PWM settings
        self._pwm_frequency = config.get("hardware.motors.pwm_frequency", 100)
        self._left_pwm = None
        self._right_pwm = None
    
    def initialize(self) -> bool:
        """Initialize the motor controller hardware"""
        if not RPI_AVAILABLE:
            self.logger.error("RPi.GPIO is not available")
            return False
        
        if self._is_initialized:
            return True
        
        try:
            # Set up GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # Set up motor pins
            for pin in [self._left_enable_pin, self._left_forward_pin, self._left_reverse_pin,
                       self._right_enable_pin, self._right_forward_pin, self._right_reverse_pin]:
                GPIO.setup(pin, GPIO.OUT)
                GPIO.output(pin, GPIO.LOW)
            
            # Set up encoder pins
            for pin in [self._left_encoder_pin, self._right_encoder_pin]:
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            # Set up encoder interrupts
            GPIO.add_event_detect(self._left_encoder_pin, GPIO.RISING, callback=self._left_encoder_callback)
            GPIO.add_event_detect(self._right_encoder_pin, GPIO.RISING, callback=self._right_encoder_callback)
            
            # Set up PWM
            self._left_pwm = GPIO.PWM(self._left_enable_pin, self._pwm_frequency)
            self._right_pwm = GPIO.PWM(self._right_enable_pin, self._pwm_frequency)
            
            # Start PWM with 0% duty cycle (stopped)
            self._left_pwm.start(0)
            self._right_pwm.start(0)
            
            # Start control loop
            self._start_control_loop()
            
            self._is_initialized = True
            self.logger.info("Motor controller initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing motor controller: {str(e)}")
            # Clean up if initialization failed
            self.cleanup()
            return False
    
    def set_speed(self, left_speed: float, right_speed: float) -> bool:
        """Set the speed of the left and right motors"""
        if not self._is_initialized:
            self.logger.error("Motor controller not initialized")
            return False
        
        if self._safety_stop:
            self.logger.warning("Cannot set speed - safety stop is active")
            return False
        
        # Clamp speeds to valid range (-1.0 to 1.0)
        left_speed = max(-1.0, min(1.0, left_speed))
        right_speed = max(-1.0, min(1.0, right_speed))
        
        # Update motor state and direction
        if left_speed > 0:
            self._left_motor_state = MotorState.FORWARD
            GPIO.output(self._left_forward_pin, GPIO.HIGH)
            GPIO.output(self._left_reverse_pin, GPIO.LOW)
        elif left_speed < 0:
            self._left_motor_state = MotorState.REVERSE
            GPIO.output(self._left_forward_pin, GPIO.LOW)
            GPIO.output(self._left_reverse_pin, GPIO.HIGH)
        else:
            self._left_motor_state = MotorState.STOPPED
            GPIO.output(self._left_forward_pin, GPIO.LOW)
            GPIO.output(self._left_reverse_pin, GPIO.LOW)
        
        if right_speed > 0:
            self._right_motor_state = MotorState.FORWARD
            GPIO.output(self._right_forward_pin, GPIO.HIGH)
            GPIO.output(self._right_reverse_pin, GPIO.LOW)
        elif right_speed < 0:
            self._right_motor_state = MotorState.REVERSE
            GPIO.output(self._right_forward_pin, GPIO.LOW)
            GPIO.output(self._right_reverse_pin, GPIO.HIGH)
        else:
            self._right_motor_state = MotorState.STOPPED
            GPIO.output(self._right_forward_pin, GPIO.LOW)
            GPIO.output(self._right_reverse_pin, GPIO.LOW)
        
        # Update target speeds
        self._left_speed = left_speed
        self._right_speed = right_speed
        
        # Apply PWM duty cycle (absolute value since direction is set by pins)
        left_duty = abs(left_speed) * 100.0
        right_duty = abs(right_speed) * 100.0
        
        self._left_pwm.ChangeDutyCycle(left_duty)
        self._right_pwm.ChangeDutyCycle(right_duty)
        
        return True
    
    def stop(self) -> bool:
        """Stop all motors"""
        if not self._is_initialized:
            return False
        
        # Set all direction pins to LOW
        GPIO.output(self._left_forward_pin, GPIO.LOW)
        GPIO.output(self._left_reverse_pin, GPIO.LOW)
        GPIO.output(self._right_forward_pin, GPIO.LOW)
        GPIO.output(self._right_reverse_pin, GPIO.LOW)
        
        # Set PWM duty cycle to 0
        self._left_pwm.ChangeDutyCycle(0)
        self._right_pwm.ChangeDutyCycle(0)
        
        # Update state
        self._left_motor_state = MotorState.STOPPED
        self._right_motor_state = MotorState.STOPPED
        self._left_speed = 0.0
        self._right_speed = 0.0
        
        return True
    
    def _control_loop(self) -> None:
        """Control loop for PID control and ramp limiting"""
        last_time = time.time()
        
        while self._control_loop_running:
            current_time = time.time()
            dt = current_time - last_time
            
            # Limit control loop to 50Hz (20ms)
            if dt < 0.02:
                time.sleep(0.02 - dt)
                continue
            
            last_time = current_time
            
            # Process encoder counts for speed calculation
            with self._encoder_lock:
                left_encoder_diff = self._left_encoder_count - self._left_encoder_prev
                right_encoder_diff = self._right_encoder_count - self._right_encoder_prev
                
                self._left_encoder_prev = self._left_encoder_count
                self._right_encoder_prev = self._right_encoder_count
            
            # Could apply PID control here based on encoder feedback
            # For now, we're just using simple PWM control
            
            # Check for stall conditions (no encoder pulses when speed > 0)
            # This is just a basic example - real implementations would be more sophisticated
            if abs(self._left_speed) > 0.1 and left_encoder_diff == 0:
                self.logger.warning("Left motor may be stalled")
            
            if abs(self._right_speed) > 0.1 and right_encoder_diff == 0:
                self.logger.warning("Right motor may be stalled")
    
    def cleanup(self) -> None:
        """Clean up resources used by the motor controller"""
        self._stop_control_loop()
        
        if self._left_pwm:
            self._left_pwm.stop()
        
        if self._right_pwm:
            self._right_pwm.stop()
        
        # Only clean up our pins
        for pin in [self._left_enable_pin, self._left_forward_pin, self._left_reverse_pin,
                  self._right_enable_pin, self._right_forward_pin, self._right_reverse_pin]:
            # Check if pin was set up
            if GPIO.getmode() is not None:
                GPIO.cleanup(pin)
        
        # Remove event detection on encoder pins
        try:
            GPIO.remove_event_detect(self._left_encoder_pin)
            GPIO.remove_event_detect(self._right_encoder_pin)
        except:
            pass
        
        self._is_initialized = False
        self.logger.info("Motor controller cleaned up")


class PWMMotorController(RPiMotorController):
    """Motor controller that uses PWM directly without PID control"""
    # This just inherits from RPiMotorController, as it's already PWM based


class EncoderMotorController(RPiMotorController):
    """Enhanced motor controller with PID control using encoder feedback"""
    
    def __init__(self, config: ConfigManager):
        """Initialize the motor controller"""
        super().__init__(config)
        
        # Speed calculation variables
        self._pulses_per_rotation = config.get("hardware.motors.encoder_pulses_per_rotation", 12)
        self._wheel_circumference = config.get("hardware.motors.wheel_circumference", 0.47)  # meters
        self._left_speed_actual = 0.0
        self._right_speed_actual = 0.0
        
        # Speed control
        self._use_pid = config.get("hardware.motors.use_pid", True)
    
    def _control_loop(self) -> None:
        """Control loop for PID control using encoder feedback"""
        last_time = time.time()
        
        while self._control_loop_running:
            current_time = time.time()
            dt = current_time - last_time
            
            # Limit control loop to 50Hz (20ms)
            if dt < 0.02:
                time.sleep(0.02 - dt)
                continue
            
            last_time = current_time
            
            # Calculate actual motor speeds from encoder counts
            with self._encoder_lock:
                left_encoder_diff = self._left_encoder_count - self._left_encoder_prev
                right_encoder_diff = self._right_encoder_count - self._right_encoder_prev
                
                self._left_encoder_prev = self._left_encoder_count
                self._right_encoder_prev = self._right_encoder_count
            
            # Convert encoder pulses to meters per second
            # pulses / dt * meters/rotation / pulses/rotation
            if dt > 0:
                self._left_speed_actual = (left_encoder_diff / dt) * (self._wheel_circumference / self._pulses_per_rotation)
                self._right_speed_actual = (right_encoder_diff / dt) * (self._wheel_circumference / self._pulses_per_rotation)
                
                # Normalize to -1.0 to 1.0 range (assuming max speed of 1 m/s)
                max_speed = 1.0  # m/s
                self._left_speed_actual = self._left_speed_actual / max_speed
                self._right_speed_actual = self._right_speed_actual / max_speed
                
                # Apply sign based on motor direction
                if self._left_motor_state == MotorState.REVERSE:
                    self._left_speed_actual = -abs(self._left_speed_actual)
                
                if self._right_motor_state == MotorState.REVERSE:
                    self._right_speed_actual = -abs(self._right_speed_actual)
            
            # Apply PID control if enabled
            if self._use_pid and not self._safety_stop:
                # Get current PWM duty cycles
                left_duty = abs(self._left_speed) * 100.0
                right_duty = abs(self._right_speed) * 100.0
                
                # Calculate PID output
                left_output = self._left_pid.update(abs(self._left_speed), abs(self._left_speed_actual))
                right_output = self._right_pid.update(abs(self._right_speed), abs(self._right_speed_actual))
                
                # Apply PID output to duty cycle
                left_duty = max(0, min(100, left_duty + left_output))
                right_duty = max(0, min(100, right_duty + right_output))
                
                # Apply PWM duty cycle
                if self._left_pwm and self._right_pwm:
                    self._left_pwm.ChangeDutyCycle(left_duty)
                    self._right_pwm.ChangeDutyCycle(right_duty)
            
            # Check for stall conditions
            stall_detection_threshold = 0.2  # 20% of expected speed
            
            if (abs(self._left_speed) > 0.1 and 
                abs(self._left_speed_actual) < abs(self._left_speed) * stall_detection_threshold):
                self.logger.warning("Left motor may be stalled")
            
            if (abs(self._right_speed) > 0.1 and 
                abs(self._right_speed_actual) < abs(self._right_speed) * stall_detection_threshold):
                self.logger.warning("Right motor may be stalled")
    
    def get_status(self) -> Dict[str, Any]:
        """Get the status of the motors"""
        # Get base status
        status = super().get_status()
        
        # Add actual speeds
        status["left_motor"]["actual_speed"] = self._left_speed_actual
        status["right_motor"]["actual_speed"] = self._right_speed_actual
        
        # Add PID status
        status["pid_enabled"] = self._use_pid
        
        return status
