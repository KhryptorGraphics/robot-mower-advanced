"""
Hardware Factory

Provides factory functions for creating hardware component instances
with proper dependency injection and configuration.
"""

import logging
from typing import Dict, Any, Optional, List, Type

from .interfaces import (
    MotorController, BladeController, DistanceSensor, IMUSensor,
    GPSSensor, Camera, PowerManagement, StatusIndicator, RainSensor, TiltSensor
)
from .motor_controller import PWMMotorController
from .blade_controller import RPiBladeController, PWMBladeController
from .sensors.distance import UltrasonicSensor
from .sensors.imu import MPU6050IMUSensor
from .sensors.gps import NMEAGPSSensor
from .sensors.camera import RaspberryPiCamera
from .sensors.power import SimplePowerMonitor
from .sensors.indicators import LEDStatusIndicator
from .sensors.environment import DigitalRainSensor, DigitalTiltSensor

from ..core.config import ConfigManager
from ..core.dependency_injection import ServiceLocator


class HardwareFactory:
    """Factory for creating hardware component instances"""
    
    def __init__(self, config: ConfigManager, service_locator: ServiceLocator):
        """Initialize the hardware factory"""
        self.config = config
        self.service_locator = service_locator
        self.logger = logging.getLogger("HardwareFactory")
        
        # Cache for singleton instances
        self._instances = {}
    
    def create_motor_controller(self) -> MotorController:
        """Create a motor controller instance"""
        if "motor_controller" in self._instances:
            return self._instances["motor_controller"]
        
        controller_type = self.config.get("hardware.motor_controller.type", "pwm")
        
        if controller_type.lower() == "pwm":
            controller = PWMMotorController(self.config)
        else:
            self.logger.warning(f"Unknown motor controller type: {controller_type}, using PWM")
            controller = PWMMotorController(self.config)
        
        # Initialize the controller
        if not controller.initialize():
            self.logger.error("Failed to initialize motor controller")
        
        # Cache the instance
        self._instances["motor_controller"] = controller
        return controller
    
    def create_blade_controller(self) -> BladeController:
        """Create a blade controller instance"""
        if "blade_controller" in self._instances:
            return self._instances["blade_controller"]
        
        controller_type = self.config.get("hardware.blade_motor.type", "rpi")
        
        if controller_type.lower() == "rpi":
            controller = RPiBladeController(self.config)
        elif controller_type.lower() == "pwm":
            controller = PWMBladeController(self.config)
        else:
            self.logger.warning(f"Unknown blade controller type: {controller_type}, using RPi")
            controller = RPiBladeController(self.config)
        
        # Initialize the controller
        if not controller.initialize():
            self.logger.error("Failed to initialize blade controller")
        
        # Cache the instance
        self._instances["blade_controller"] = controller
        return controller
    
    def create_distance_sensor(self, name: str = "front") -> DistanceSensor:
        """Create a distance sensor instance"""
        # Distance sensors are not singletons since we might have multiple
        cache_key = f"distance_sensor_{name}"
        if cache_key in self._instances:
            return self._instances[cache_key]
        
        sensor = UltrasonicSensor(self.config, name)
        
        # Initialize the sensor
        if not sensor.initialize():
            self.logger.error(f"Failed to initialize distance sensor: {name}")
        
        # Cache the instance
        self._instances[cache_key] = sensor
        return sensor
    
    def create_imu_sensor(self) -> IMUSensor:
        """Create an IMU sensor instance"""
        if "imu_sensor" in self._instances:
            return self._instances["imu_sensor"]
        
        sensor = MPU6050IMUSensor(self.config)
        
        # Initialize the sensor
        if not sensor.initialize():
            self.logger.error("Failed to initialize IMU sensor")
        
        # Cache the instance
        self._instances["imu_sensor"] = sensor
        return sensor
    
    def create_gps_sensor(self) -> GPSSensor:
        """Create a GPS sensor instance"""
        if "gps_sensor" in self._instances:
            return self._instances["gps_sensor"]
        
        sensor = NMEAGPSSensor(self.config)
        
        # Initialize the sensor
        if not sensor.initialize():
            self.logger.error("Failed to initialize GPS sensor")
        
        # Cache the instance
        self._instances["gps_sensor"] = sensor
        return sensor
    
    def create_camera(self) -> Camera:
        """Create a camera instance"""
        if "camera" in self._instances:
            return self._instances["camera"]
        
        camera = RaspberryPiCamera(self.config)
        
        # Initialize the camera
        if not camera.initialize():
            self.logger.error("Failed to initialize camera")
        
        # Cache the instance
        self._instances["camera"] = camera
        return camera
    
    def create_power_management(self) -> PowerManagement:
        """Create a power management instance"""
        if "power_management" in self._instances:
            return self._instances["power_management"]
        
        power = SimplePowerMonitor(self.config)
        
        # Initialize the power management
        if not power.initialize():
            self.logger.error("Failed to initialize power management")
        
        # Cache the instance
        self._instances["power_management"] = power
        return power
    
    def create_status_indicator(self) -> StatusIndicator:
        """Create a status indicator instance"""
        if "status_indicator" in self._instances:
            return self._instances["status_indicator"]
        
        indicator = LEDStatusIndicator(self.config)
        
        # Initialize the indicator
        if not indicator.initialize():
            self.logger.error("Failed to initialize status indicator")
        
        # Cache the instance
        self._instances["status_indicator"] = indicator
        return indicator
    
    def create_rain_sensor(self) -> RainSensor:
        """Create a rain sensor instance"""
        if "rain_sensor" in self._instances:
            return self._instances["rain_sensor"]
        
        sensor = DigitalRainSensor(self.config)
        
        # Initialize the sensor
        if not sensor.initialize():
            self.logger.error("Failed to initialize rain sensor")
        
        # Cache the instance
        self._instances["rain_sensor"] = sensor
        return sensor
    
    def create_tilt_sensor(self) -> TiltSensor:
        """Create a tilt sensor instance"""
        if "tilt_sensor" in self._instances:
            return self._instances["tilt_sensor"]
        
        # Check if we should use IMU for tilt sensing
        use_imu = self.config.get("hardware.sensors.tilt_sensor.use_imu", False)
        
        sensor = DigitalTiltSensor(self.config)
        
        # Initialize the sensor
        if not sensor.initialize():
            self.logger.error("Failed to initialize tilt sensor")
        
        # If using IMU for tilt, connect the IMU to the tilt sensor
        if use_imu:
            # Create/get the IMU
            imu = self.create_imu_sensor()
            # Connect it to the tilt sensor
            sensor.set_imu(imu)
        
        # Cache the instance
        self._instances["tilt_sensor"] = sensor
        return sensor
    
    def create_all_sensors(self) -> Dict[str, Any]:
        """Create all sensor instances"""
        sensors = {}
        
        # Create distance sensors
        distance_sensors = []
        ultrasonic_configs = self.config.get("hardware.sensors.ultrasonic", [])
        
        if isinstance(ultrasonic_configs, list):
            for sensor_config in ultrasonic_configs:
                if isinstance(sensor_config, dict) and "name" in sensor_config:
                    name = sensor_config["name"]
                    distance_sensors.append(self.create_distance_sensor(name))
        
        # If no sensors were created, create a default one
        if not distance_sensors:
            distance_sensors.append(self.create_distance_sensor())
        
        sensors["distance_sensors"] = distance_sensors
        
        # Create other sensors
        sensors["imu"] = self.create_imu_sensor()
        sensors["gps"] = self.create_gps_sensor()
        sensors["camera"] = self.create_camera()
        sensors["power"] = self.create_power_management()
        sensors["status_indicator"] = self.create_status_indicator()
        sensors["rain_sensor"] = self.create_rain_sensor()
        sensors["tilt_sensor"] = self.create_tilt_sensor()
        
        return sensors
    
    def cleanup_all(self) -> None:
        """Clean up all hardware resources"""
        for key, instance in self._instances.items():
            try:
                self.logger.info(f"Cleaning up {key}")
                instance.cleanup()
            except Exception as e:
                self.logger.error(f"Error cleaning up {key}: {str(e)}")
        
        # Clear the instances
        self._instances.clear()
