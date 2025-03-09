# Robot Mower Advanced - Sensors Module

This module provides implementations of various sensors used in the robot mower system. The sensors are organized by their functionality and provide a clean abstraction layer over the hardware.

## Directory Structure

Each sensor type is separated into its own file for better organization and maintainability:

- `__init__.py` - Exports all sensor implementations
- `distance.py` - Distance sensor implementations (ultrasonic sensors)
- `imu.py` - IMU (Inertial Measurement Unit) sensor implementations
- `gps.py` - GPS sensor implementations
- `camera.py` - Camera and vision sensor implementations
- `power.py` - Power management and battery monitoring
- `indicators.py` - Status indicators such as LEDs
- `environment.py` - Environmental sensors like rain and tilt sensors

## Sensor Implementations

### Distance Sensors
- `UltrasonicSensor` - HC-SR04 ultrasonic distance sensor

### IMU Sensors
- `MPU6050IMUSensor` - MPU6050 I2C IMU sensor for orientation and movement detection

### GPS Sensors
- `NMEAGPSSensor` - GPS module using NMEA protocol over serial

### Cameras
- `RaspberryPiCamera` - Raspberry Pi Camera Module implementation

### Power Management
- `SimplePowerMonitor` - Battery voltage and current monitoring with ADC

### Status Indicators
- `LEDStatusIndicator` - RGB LED status indicator

### Environmental Sensors
- `DigitalRainSensor` - Digital rain sensor implementation
- `DigitalTiltSensor` - Tilt sensor using IMU or dedicated tilt switch

## Development Guidelines

When adding new sensor implementations:

1. Implement the appropriate interface from `hardware/interfaces.py`
2. Place the implementation in the appropriate file based on sensor type
3. Add the implementation to the `__init__.py` exports
4. Update the factory in `hardware/factory.py` to create instances of the new sensor

All sensor implementations should follow these principles:

- Initialize hardware resources in the `initialize()` method
- Clean up resources in the `cleanup()` method
- Provide thread-safety for sensor readings
- Include proper error handling and logging
- Support hot-plugging when possible (graceful degradation if sensor not available)
