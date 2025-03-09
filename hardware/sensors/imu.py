"""
IMU (Inertial Measurement Unit) Sensor Implementations

Provides concrete implementations of IMU sensors for orientation,
motion detection, and navigation.
"""

import time
import threading
import logging
import math
from typing import Dict, List, Tuple, Optional, Any

try:
    import smbus2
    SMBUS_AVAILABLE = True
except ImportError:
    SMBUS_AVAILABLE = False
    # Use a mock for development without I2C
    from unittest.mock import MagicMock
    smbus2 = MagicMock()

from ..interfaces import IMUSensor
from ...core.config import ConfigManager


class MPU6050IMUSensor(IMUSensor):
    """Implementation of an MPU6050 IMU sensor over I2C"""
    
    # MPU6050 registers
    _MPU6050_ADDR = 0x68
    _PWR_MGMT_1 = 0x6B
    _GYRO_XOUT_H = 0x43
    _ACCEL_XOUT_H = 0x3B
    
    def __init__(self, config: ConfigManager):
        """Initialize the IMU sensor"""
        self.config = config
        self.logger = logging.getLogger("MPU6050IMU")
        self._is_initialized = False
        
        # Get configuration
        self._i2c_bus = config.get("hardware.sensors.imu.i2c_bus", 1)
        self._i2c_address = config.get("hardware.sensors.imu.i2c_address", self._MPU6050_ADDR)
        self._update_rate = config.get("hardware.sensors.imu.update_rate", 100)  # Hz
        
        # Calibration offsets
        self._accel_offsets = [0.0, 0.0, 0.0]
        self._gyro_offsets = [0.0, 0.0, 0.0]
        
        # Current state
        self._bus = None
        self._accel = [0.0, 0.0, 0.0]
        self._gyro = [0.0, 0.0, 0.0]
        self._orientation = [0.0, 0.0, 0.0]  # roll, pitch, yaw in radians
        
        # Thread for continuous reading
        self._running = False
        self._read_thread = None
        self._data_lock = threading.Lock()
        
        # Movement detection
        self._moving = False
        self._movement_threshold = config.get("hardware.sensors.imu.movement_threshold", 0.2)  # m/s²
    
    def initialize(self) -> bool:
        """Initialize the IMU sensor"""
        if not SMBUS_AVAILABLE:
            self.logger.error("smbus2 is not available")
            return False
        
        if self._is_initialized:
            return True
        
        try:
            # Initialize I2C
            self._bus = smbus2.SMBus(self._i2c_bus)
            
            # Wake up the MPU6050
            self._bus.write_byte_data(self._i2c_address, self._PWR_MGMT_1, 0)
            
            # Short pause to let the sensor wake up
            time.sleep(0.1)
            
            # Perform initial calibration
            self.calibrate()
            
            # Start the read thread
            self._start_read_thread()
            
            self._is_initialized = True
            self.logger.info("MPU6050 IMU initialized")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing MPU6050 IMU: {str(e)}")
            # Clean up if initialization failed
            self.cleanup()
            return False
    
    def _start_read_thread(self) -> None:
        """Start the thread that continuously reads data from the IMU"""
        if self._running:
            return
        
        self._running = True
        self._read_thread = threading.Thread(
            target=self._read_loop,
            daemon=True,
            name="IMU_ReadThread"
        )
        self._read_thread.start()
    
    def _stop_read_thread(self) -> None:
        """Stop the read thread"""
        self._running = False
        if self._read_thread and self._read_thread.is_alive():
            self._read_thread.join(timeout=1.0)
    
    def _read_loop(self) -> None:
        """Loop that continuously reads data from the IMU"""
        last_update = time.time()
        update_interval = 1.0 / self._update_rate
        
        # For orientation calculation
        last_time = time.time()
        
        while self._running and self._is_initialized:
            try:
                # Calculate time since last reading
                current_time = time.time()
                dt = current_time - last_time
                last_time = current_time
                
                # Only update at the configured rate
                if current_time - last_update < update_interval:
                    time.sleep(0.001)
                    continue
                
                last_update = current_time
                
                # Read accelerometer data (6 bytes)
                accel_data = self._bus.read_i2c_block_data(self._i2c_address, self._ACCEL_XOUT_H, 6)
                
                # Convert to acceleration values (g)
                accel_x = (accel_data[0] << 8 | accel_data[1]) / 16384.0
                accel_y = (accel_data[2] << 8 | accel_data[3]) / 16384.0
                accel_z = (accel_data[4] << 8 | accel_data[5]) / 16384.0
                
                # Apply calibration offsets
                accel_x -= self._accel_offsets[0]
                accel_y -= self._accel_offsets[1]
                accel_z -= self._accel_offsets[2]
                
                # Read gyroscope data (6 bytes)
                gyro_data = self._bus.read_i2c_block_data(self._i2c_address, self._GYRO_XOUT_H, 6)
                
                # Convert to rotation rate (rad/s)
                gyro_x = (gyro_data[0] << 8 | gyro_data[1]) / 131.0 * math.pi / 180.0
                gyro_y = (gyro_data[2] << 8 | gyro_data[3]) / 131.0 * math.pi / 180.0
                gyro_z = (gyro_data[4] << 8 | gyro_data[5]) / 131.0 * math.pi / 180.0
                
                # Apply calibration offsets
                gyro_x -= self._gyro_offsets[0]
                gyro_y -= self._gyro_offsets[1]
                gyro_z -= self._gyro_offsets[2]
                
                # Convert acceleration to m/s²
                accel_x *= 9.81
                accel_y *= 9.81
                accel_z *= 9.81
                
                # Update orientation using complementary filter
                # Calculate roll and pitch from accelerometer
                accel_roll = math.atan2(accel_y, accel_z)
                accel_pitch = math.atan2(-accel_x, math.sqrt(accel_y*accel_y + accel_z*accel_z))
                
                # Integrate gyro rates to get orientation
                roll = self._orientation[0] + gyro_x * dt
                pitch = self._orientation[1] + gyro_y * dt
                yaw = self._orientation[2] + gyro_z * dt
                
                # Complementary filter to combine gyro and accelerometer data
                alpha = 0.98  # Filter coefficient
                roll = alpha * roll + (1 - alpha) * accel_roll
                pitch = alpha * pitch + (1 - alpha) * accel_pitch
                
                # Normalize yaw to 0-2π
                while yaw < 0:
                    yaw += 2 * math.pi
                while yaw >= 2 * math.pi:
                    yaw -= 2 * math.pi
                
                # Update values with thread safety
                with self._data_lock:
                    self._accel = [accel_x, accel_y, accel_z]
                    self._gyro = [gyro_x, gyro_y, gyro_z]
                    self._orientation = [roll, pitch, yaw]
                    
                    # Detect movement (simple acceleration threshold)
                    accel_magnitude = math.sqrt(accel_x*accel_x + accel_y*accel_y + accel_z*accel_z)
                    # Subtract gravity
                    accel_magnitude = abs(accel_magnitude - 9.81)
                    self._moving = accel_magnitude > self._movement_threshold
            
            except Exception as e:
                self.logger.error(f"Error reading from IMU: {str(e)}")
                time.sleep(0.1)  # Short delay to avoid tight loop on error
    
    def get_acceleration(self) -> Tuple[float, float, float]:
        """Get the current acceleration values in m/s²"""
        with self._data_lock:
            return tuple(self._accel)
    
    def get_gyroscope(self) -> Tuple[float, float, float]:
        """Get the current gyroscope values in rad/s"""
        with self._data_lock:
            return tuple(self._gyro)
    
    def get_orientation(self) -> Tuple[float, float, float]:
        """Get the current orientation in radians (roll, pitch, yaw)"""
        with self._data_lock:
            return tuple(self._orientation)
    
    def is_moving(self) -> bool:
        """Check if the IMU detects movement"""
        with self._data_lock:
            return self._moving
    
    def calibrate(self) -> bool:
        """Calibrate the IMU sensor"""
        if not self._is_initialized or self._bus is None:
            self.logger.error("Cannot calibrate IMU - not initialized")
            return False
        
        self.logger.info("Calibrating IMU - keep the mower still...")
        
        # Store original thread state
        was_running = self._running
        if was_running:
            self._stop_read_thread()
        
        try:
            # Number of samples for calibration
            num_samples = 100
            
            # Storage for samples
            accel_samples = [[], [], []]
            gyro_samples = [[], [], []]
            
            # Collect samples
            for _ in range(num_samples):
                # Read accelerometer data
                accel_data = self._bus.read_i2c_block_data(self._i2c_address, self._ACCEL_XOUT_H, 6)
                
                # Convert to acceleration values
                accel_x = (accel_data[0] << 8 | accel_data[1]) / 16384.0
                accel_y = (accel_data[2] << 8 | accel_data[3]) / 16384.0
                accel_z = (accel_data[4] << 8 | accel_data[5]) / 16384.0
                
                # Store samples
                accel_samples[0].append(accel_x)
                accel_samples[1].append(accel_y)
                accel_samples[2].append(accel_z)
                
                # Read gyroscope data
                gyro_data = self._bus.read_i2c_block_data(self._i2c_address, self._GYRO_XOUT_H, 6)
                
                # Convert to rotation rate
                gyro_x = (gyro_data[0] << 8 | gyro_data[1]) / 131.0 * math.pi / 180.0
                gyro_y = (gyro_data[2] << 8 | gyro_data[3]) / 131.0 * math.pi / 180.0
                gyro_z = (gyro_data[4] << 8 | gyro_data[5]) / 131.0 * math.pi / 180.0
                
                # Store samples
                gyro_samples[0].append(gyro_x)
                gyro_samples[1].append(gyro_y)
                gyro_samples[2].append(gyro_z)
                
                # Short delay between samples
                time.sleep(0.01)
            
            # Calculate average values
            accel_avg = [sum(axis) / num_samples for axis in accel_samples]
            gyro_avg = [sum(axis) / num_samples for axis in gyro_samples]
            
            # Set offsets
            # For accelerometer, we want to zero X and Y, but keep Z at 1g
            self._accel_offsets = [accel_avg[0], accel_avg[1], accel_avg[2] - 1.0]
            
            # For gyroscope, we want to zero all axes
            self._gyro_offsets = gyro_avg
            
            self.logger.info("IMU calibration complete")
            
            # Restart thread if it was running
            if was_running:
                self._start_read_thread()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error calibrating IMU: {str(e)}")
            
            # Restart thread if it was running
            if was_running:
                self._start_read_thread()
            
            return False
    
    def cleanup(self) -> None:
        """Clean up resources used by the IMU sensor"""
        self._stop_read_thread()
        
        if self._bus:
            self._bus.close()
            self._bus = None
        
        self._is_initialized = False
        self.logger.info("MPU6050 IMU cleaned up")
