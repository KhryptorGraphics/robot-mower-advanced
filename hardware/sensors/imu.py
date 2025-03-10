"""
MPU6050 IMU Sensor Implementation

This module provides a concrete implementation of the IMUSensor interface 
for the MPU6050 inertial measurement unit, commonly used in robotics projects.
"""

import time
import threading
import logging
import math
from typing import Dict, List, Tuple, Optional, Any
import numpy as np

try:
    import smbus
    SMBUS_AVAILABLE = True
except ImportError:
    SMBUS_AVAILABLE = False
    # Use a mock for development on non-RPi systems
    from unittest.mock import MagicMock
    smbus = MagicMock()

from ..interfaces import IMUSensor


class MPU6050IMUSensor(IMUSensor):
    """
    Implementation of MPU6050 IMU sensor
    
    Provides access to accelerometer and gyroscope data, as well as
    derived orientation values through sensor fusion.
    """
    
    # MPU6050 Register Map
    PWR_MGMT_1 = 0x6B
    SMPLRT_DIV = 0x19
    CONFIG = 0x1A
    GYRO_CONFIG = 0x1B
    ACCEL_CONFIG = 0x1C
    INT_ENABLE = 0x38
    ACCEL_XOUT_H = 0x3B
    ACCEL_YOUT_H = 0x3D
    ACCEL_ZOUT_H = 0x3F
    TEMP_OUT_H = 0x41
    GYRO_XOUT_H = 0x43
    GYRO_YOUT_H = 0x45
    GYRO_ZOUT_H = 0x47
    
    # Scaling factors
    ACCEL_SCALE_FACTOR = {
        0: 16384.0,  # ±2g
        1: 8192.0,   # ±4g
        2: 4096.0,   # ±8g
        3: 2048.0    # ±16g
    }
    
    GYRO_SCALE_FACTOR = {
        0: 131.0,    # ±250°/s
        1: 65.5,     # ±500°/s
        2: 32.8,     # ±1000°/s
        3: 16.4      # ±2000°/s
    }
    
    def __init__(self, config):
        """
        Initialize the MPU6050 IMU sensor
        
        Args:
            config: Configuration manager
        """
        self.logger = logging.getLogger("MPU6050IMUSensor")
        self.config = config
        self._is_initialized = False
        
        # Get configuration values with defaults
        self.i2c_bus = config.get("hardware.sensors.imu.i2c_bus", 1)
        self.i2c_address = config.get("hardware.sensors.imu.i2c_address", 0x68)
        
        # Get offset corrections from config
        self.roll_offset = config.get("hardware.sensors.imu.orientation_correction.roll_offset_deg", 0.0)
        self.pitch_offset = config.get("hardware.sensors.imu.orientation_correction.pitch_offset_deg", 0.0)
        self.yaw_offset = config.get("hardware.sensors.imu.orientation_correction.yaw_offset_deg", 0.0)
        
        # Configuration settings
        self.gyro_range = 0  # 0=250deg/s, 1=500deg/s, 2=1000deg/s, 3=2000deg/s
        self.accel_range = 0  # 0=2g, 1=4g, 2=8g, 3=16g
        self.dlpf_mode = 6    # Digital Low Pass Filter mode
        
        # State
        self._bus = None
        self._acceleration = (0.0, 0.0, 0.0)
        self._gyroscope = (0.0, 0.0, 0.0)
        self._orientation = (0.0, 0.0, 0.0)  # roll, pitch, yaw in radians
        self._temperature = 0.0
        
        # Calibration
        self._accel_offset = (0.0, 0.0, 0.0)
        self._gyro_offset = (0.0, 0.0, 0.0)
        
        # Kalman filter for orientation
        self._roll = 0.0
        self._pitch = 0.0
        self._yaw = 0.0
        self._last_time = time.time()
        
        # Lock for thread safety
        self._lock = threading.Lock()
        
        # Update thread
        self._update_thread = None
        self._running = False
        self._update_interval = 0.01  # 100Hz
        
        self.logger.debug(f"MPU6050 sensor configured with I2C bus={self.i2c_bus}, address=0x{self.i2c_address:02X}")
    
    def initialize(self) -> bool:
        """Initialize the IMU sensor"""
        if not SMBUS_AVAILABLE:
            self.logger.warning("smbus is not available, using mock implementation")
            self._is_initialized = True
            return True
        
        if self._is_initialized:
            return True
        
        try:
            # Initialize I2C bus
            self._bus = smbus.SMBus(self.i2c_bus)
            
            # Wake up the MPU6050
            self._bus.write_byte_data(self.i2c_address, self.PWR_MGMT_1, 0)
            
            # Configure the device
            self._bus.write_byte_data(self.i2c_address, self.SMPLRT_DIV, 7)  # Sample rate = 8kHz/(7+1) = 1kHz
            self._bus.write_byte_data(self.i2c_address, self.CONFIG, self.dlpf_mode)  # Digital Low Pass Filter
            
            # Set gyroscope range
            gyro_config = self.gyro_range << 3
            self._bus.write_byte_data(self.i2c_address, self.GYRO_CONFIG, gyro_config)
            
            # Set accelerometer range
            accel_config = self.accel_range << 3
            self._bus.write_byte_data(self.i2c_address, self.ACCEL_CONFIG, accel_config)
            
            # Enable data ready interrupt
            self._bus.write_byte_data(self.i2c_address, self.INT_ENABLE, 1)
            
            # Start calibration
            self._calibrate()
            
            # Start update thread
            self._running = True
            self._update_thread = threading.Thread(target=self._update_loop, daemon=True)
            self._update_thread.start()
            
            self._is_initialized = True
            self.logger.info("MPU6050 IMU sensor initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize MPU6050 IMU sensor: {e}")
            return False
    
    def _calibrate(self) -> None:
        """Calibrate the sensor by measuring bias offsets"""
        if not SMBUS_AVAILABLE:
            return
        
        self.logger.info("Calibrating MPU6050...")
        
        # Number of samples to use for calibration
        num_samples = 100
        
        # Storage for samples
        accel_x_samples = []
        accel_y_samples = []
        accel_z_samples = []
        gyro_x_samples = []
        gyro_y_samples = []
        gyro_z_samples = []
        
        # Collect samples
        for _ in range(num_samples):
            ax, ay, az = self._read_raw_accel()
            gx, gy, gz = self._read_raw_gyro()
            
            accel_x_samples.append(ax)
            accel_y_samples.append(ay)
            accel_z_samples.append(az)
            gyro_x_samples.append(gx)
            gyro_y_samples.append(gy)
            gyro_z_samples.append(gz)
            
            time.sleep(0.01)  # 10ms delay between samples
        
        # Calculate average offsets
        accel_x_offset = sum(accel_x_samples) / num_samples
        accel_y_offset = sum(accel_y_samples) / num_samples
        accel_z_offset = sum(accel_z_samples) / num_samples - self.ACCEL_SCALE_FACTOR[self.accel_range]  # Remove gravity (1g)
        
        gyro_x_offset = sum(gyro_x_samples) / num_samples
        gyro_y_offset = sum(gyro_y_samples) / num_samples
        gyro_z_offset = sum(gyro_z_samples) / num_samples
        
        # Store offsets
        self._accel_offset = (accel_x_offset, accel_y_offset, accel_z_offset)
        self._gyro_offset = (gyro_x_offset, gyro_y_offset, gyro_z_offset)
        
        self.logger.info(f"Calibration complete. Accelerometer offsets: {self._accel_offset}, Gyroscope offsets: {self._gyro_offset}")
    
    def _update_loop(self) -> None:
        """Background thread for continuous sensor updates"""
        while self._running:
            self._update_sensor_data()
            time.sleep(self._update_interval)
    
    def _update_sensor_data(self) -> None:
        """Read and update all sensor data"""
        try:
            # If SMBus isn't available, generate mock data
            if not SMBUS_AVAILABLE:
                self._generate_mock_data()
                return
            
            # Read raw values
            ax, ay, az = self._read_raw_accel()
            gx, gy, gz = self._read_raw_gyro()
            temp = self._read_raw_temp()
            
            # Apply offsets and scaling
            ax = (ax - self._accel_offset[0]) / self.ACCEL_SCALE_FACTOR[self.accel_range]
            ay = (ay - self._accel_offset[1]) / self.ACCEL_SCALE_FACTOR[self.accel_range]
            az = (az - self._accel_offset[2]) / self.ACCEL_SCALE_FACTOR[self.accel_range]
            
            gx = (gx - self._gyro_offset[0]) / self.GYRO_SCALE_FACTOR[self.gyro_range] * (math.pi / 180.0)  # Convert to rad/s
            gy = (gy - self._gyro_offset[1]) / self.GYRO_SCALE_FACTOR[self.gyro_range] * (math.pi / 180.0)
            gz = (gz - self._gyro_offset[2]) / self.GYRO_SCALE_FACTOR[self.gyro_range] * (math.pi / 180.0)
            
            temp = temp / 340.0 + 36.53  # Convert to degrees Celsius
            
            # Update state
            with self._lock:
                self._acceleration = (ax, ay, az)
                self._gyroscope = (gx, gy, gz)
                self._temperature = temp
                
                # Update orientation using complementary filter
                self._update_orientation()
                
        except Exception as e:
            self.logger.error(f"Error updating sensor data: {e}")
    
    def _read_raw_accel(self) -> Tuple[float, float, float]:
        """Read raw accelerometer values"""
        if not SMBUS_AVAILABLE:
            return (0.0, 0.0, 0.0)
        
        # Read 6 bytes starting from ACCEL_XOUT_H (3 axes, 2 bytes each)
        data = self._bus.read_i2c_block_data(self.i2c_address, self.ACCEL_XOUT_H, 6)
        
        # Combine high and low bytes
        x = (data[0] << 8) | data[1]
        y = (data[2] << 8) | data[3]
        z = (data[4] << 8) | data[5]
        
        # Convert from two's complement
        if x > 0x7FFF:
            x = x - 0x10000
        if y > 0x7FFF:
            y = y - 0x10000
        if z > 0x7FFF:
            z = z - 0x10000
        
        return (x, y, z)
    
    def _read_raw_gyro(self) -> Tuple[float, float, float]:
        """Read raw gyroscope values"""
        if not SMBUS_AVAILABLE:
            return (0.0, 0.0, 0.0)
        
        # Read 6 bytes starting from GYRO_XOUT_H (3 axes, 2 bytes each)
        data = self._bus.read_i2c_block_data(self.i2c_address, self.GYRO_XOUT_H, 6)
        
        # Combine high and low bytes
        x = (data[0] << 8) | data[1]
        y = (data[2] << 8) | data[3]
        z = (data[4] << 8) | data[5]
        
        # Convert from two's complement
        if x > 0x7FFF:
            x = x - 0x10000
        if y > 0x7FFF:
            y = y - 0x10000
        if z > 0x7FFF:
            z = z - 0x10000
        
        return (x, y, z)
    
    def _read_raw_temp(self) -> float:
        """Read raw temperature value"""
        if not SMBUS_AVAILABLE:
            return 0.0
        
        # Read 2 bytes starting from TEMP_OUT_H
        data = self._bus.read_i2c_block_data(self.i2c_address, self.TEMP_OUT_H, 2)
        
        # Combine high and low bytes
        temp = (data[0] << 8) | data[1]
        
        # Convert from two's complement
        if temp > 0x7FFF:
            temp = temp - 0x10000
        
        return temp
    
    def _generate_mock_data(self) -> None:
        """Generate mock sensor data for testing/simulation"""
        # Generate simulated accelerometer data (with Earth's gravity)
        ax = np.random.normal(0.0, 0.01)
        ay = np.random.normal(0.0, 0.01)
        az = np.random.normal(1.0, 0.01)  # 1g in the Z-axis
        
        # Generate simulated gyroscope data (near zero for stationary sensor)
        gx = np.random.normal(0.0, 0.01)
        gy = np.random.normal(0.0, 0.01)
        gz = np.random.normal(0.0, 0.01)
        
        # Temperature around room temperature
        temp = np.random.normal(25.0, 0.1)
        
        # Update state
        with self._lock:
            self._acceleration = (ax, ay, az)
            self._gyroscope = (gx, gy, gz)
            self._temperature = temp
            
            # Update orientation using the simulated data
            self._update_orientation()
    
    def _update_orientation(self) -> None:
        """Update orientation estimates using a complementary filter"""
        # Get current time and calculate dt
        current_time = time.time()
        dt = current_time - self._last_time
        self._last_time = current_time
        
        # Skip if dt is too large (indicates a long pause or initialization)
        if dt > 0.1:
            dt = 0.01
        
        # Get accelerometer and gyroscope data
        ax, ay, az = self._acceleration
        gx, gy, gz = self._gyroscope
        
        # Calculate roll and pitch from accelerometer (in radians)
        accel_roll = math.atan2(ay, az)
        accel_pitch = math.atan2(-ax, math.sqrt(ay*ay + az*az))
        
        # Complementary filter for roll and pitch
        # Alpha determines how much we trust the accelerometer vs gyroscope
        alpha = 0.98
        
        # Update roll and pitch with complementary filter
        self._roll = alpha * (self._roll + gx * dt) + (1 - alpha) * accel_roll
        self._pitch = alpha * (self._pitch + gy * dt) + (1 - alpha) * accel_pitch
        
        # Integrate gyro for yaw (we can't correct yaw with accelerometer)
        self._yaw += gz * dt
        
        # Apply offsets
        roll_with_offset = self._roll + math.radians(self.roll_offset)
        pitch_with_offset = self._pitch + math.radians(self.pitch_offset)
        yaw_with_offset = self._yaw + math.radians(self.yaw_offset)
        
        # Update orientation state
        self._orientation = (roll_with_offset, pitch_with_offset, yaw_with_offset)
    
    def get_acceleration(self) -> Tuple[float, float, float]:
        """
        Get the current acceleration values
        
        Returns:
            Tuple of (x, y, z) acceleration in m/s²
        """
        if not self._is_initialized and not self.initialize():
            return (0.0, 0.0, 0.0)
        
        with self._lock:
            return self._acceleration
    
    def get_gyroscope(self) -> Tuple[float, float, float]:
        """
        Get the current gyroscope values
        
        Returns:
            Tuple of (x, y, z) rotation rates in rad/s
        """
        if not self._is_initialized and not self.initialize():
            return (0.0, 0.0, 0.0)
        
        with self._lock:
            return self._gyroscope
    
    def get_orientation(self) -> Tuple[float, float, float]:
        """
        Get the current orientation
        
        Returns:
            Tuple of (roll, pitch, yaw) in radians
        """
        if not self._is_initialized and not self.initialize():
            return (0.0, 0.0, 0.0)
        
        with self._lock:
            return self._orientation
    
    def is_moving(self) -> bool:
        """
        Check if the IMU detects movement
        
        Returns:
            True if movement is detected, False otherwise
        """
        if not self._is_initialized and not self.initialize():
            return False
        
        with self._lock:
            # Calculate magnitude of angular velocity
            gx, gy, gz = self._gyroscope
            gyro_magnitude = math.sqrt(gx*gx + gy*gy + gz*gz)
            
            # Check if magnitude exceeds threshold
            threshold = 0.1  # rad/s, adjust as needed
            return gyro_magnitude > threshold
    
    def calibrate(self) -> bool:
        """
        Calibrate the IMU sensor
        
        Returns:
            Success or failure
        """
        if not self._is_initialized and not self.initialize():
            return False
        
        try:
            self._calibrate()
            return True
        except Exception as e:
            self.logger.error(f"Calibration failed: {e}")
            return False
    
    def cleanup(self) -> None:
        """Clean up resources used by the IMU sensor"""
        self._running = False
        if self._update_thread and self._update_thread.is_alive():
            self._update_thread.join(timeout=1.0)
        
        self._is_initialized = False
        self.logger.debug("Cleaned up MPU6050 IMU sensor")
