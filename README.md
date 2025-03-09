# Robot Mower Advanced

An advanced autonomous robot mower control system with modular sensor architecture, designed for DIY enthusiasts and developers looking to build custom robotic lawn mowers.

[![GitHub license](https://img.shields.io/github/license/KhryptorGraphics/robot-mower-advanced)](https://github.com/KhryptorGraphics/robot-mower-advanced/blob/main/LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue)](https://www.python.org/downloads/)
[![Raspberry Pi](https://img.shields.io/badge/raspberry%20pi-4%2B-red)](https://www.raspberrypi.org/)

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Hardware Requirements](#hardware-requirements)
4. [Software Prerequisites](#software-prerequisites)
5. [Installation](#installation)
6. [Configuration](#configuration)
7. [Deployment](#deployment)
8. [Troubleshooting](#troubleshooting)
9. [Contributing](#contributing)
10. [License](#license)

## Overview

Robot Mower Advanced is a complete software solution for building autonomous robotic lawn mowers. This system features a modular architecture that separates hardware abstractions from navigation algorithms and user interfaces, making it highly adaptable to different hardware configurations and use cases.

### Key Features

- **Modular Sensor Architecture**: Easily add, modify, or replace sensors without affecting other components
- **Comprehensive Hardware Abstractions**: Swap hardware implementations without changing application code
- **Dependency Injection System**: Facilitates testing and component replacement
- **Configuration-Based Setup**: Customize for different hardware setups through configuration
- **Advanced Navigation**: GPS-based path planning with obstacle avoidance
- **Multi-threaded Design**: Ensures responsive operation across all system components
- **Simulator Support**: Develop and test without physical hardware

## System Architecture

The system is organized into the following modules:

- `/hardware` - Hardware abstractions and implementations
  - `/hardware/sensors` - Modular sensor implementations
  - `/hardware/interfaces.py` - Abstract interfaces for hardware components
  - `/hardware/factory.py` - Factory for creating hardware instances
  - `/hardware/motor_controller.py` - Drive motor implementations
  - `/hardware/blade_controller.py` - Cutting blade control implementations
- `/core` - Core system components
  - `/core/config.py` - Configuration management
  - `/core/logger.py` - Logging utilities
  - `/core/dependency_injection.py` - Service locator and DI container
  - `/core/application.py` - Main application logic
- `/autonomy` - Autonomous control algorithms
- `/navigation` - Navigation and path planning
- `/perception` - Computer vision and environment perception
- `/web` - Web interface for monitoring and control
- `/api` - API for external integrations
- `/mobile` - Mobile app integration
- `/data` - Data storage and management
- `/ml` - Machine learning models
- `/utils` - Utility functions and helpers

## Hardware Requirements

### Recommended Components

#### Computing Platform

- **Raspberry Pi 4B+ (4GB or 8GB RAM)** - Main controller
- **Power supply**: 5V 3A USB-C power supply with battery backup
- **Storage**: 32GB+ microSD card (Class 10 or higher)

#### Motor System

- **Drive Motors**: 2x 12V DC brushed motors with encoders (100-300W)
  - Alternatives: 24V brushless motors with ESC
- **Motor Controller**: Dual H-bridge controller (e.g., Cytron MDD10A, BTS7960)
  - Current rating: 10A minimum per channel
- **Blade Motor**: 12-24V brushless motor with ESC (200-500W)
  - Alternative: High-torque DC motor with PWM control

#### Sensors

- **GPS**: u-blox NEO-M8N GPS module with external antenna
- **IMU**: MPU6050 or MPU9250 for orientation detection
- **Distance Sensors**: 3-5x HC-SR04 ultrasonic sensors or VL53L0X ToF sensors
  - Front: 2-3 sensors
  - Sides: 1-2 sensors
- **Camera**: Raspberry Pi Camera Module V2 or HQ Camera Module
- **Environment Sensors**:
  - Rain sensor: FC-37 or YL-83
  - Tilt sensor: Built-in to MPU6050 or dedicated tilt switch
- **Power Monitoring**: INA219 current/voltage sensor
- **Status Indicators**: RGB LEDs or small OLED display

#### Power System

- **Main Battery**: 4S LiPo battery (14.8V, 10000mAh+) or sealed lead-acid
- **Charging**: Solar panel with charge controller (optional)
- **Regulation**: 5V step-down regulator for Raspberry Pi

#### Mechanical Components

- **Chassis**: Weather-resistant enclosure with proper ventilation
- **Wheels**: 2x driven wheels + 1-2 caster/free wheels
- **Cutting System**: Single or multiple blade system with protective housing

### Minimum Requirements

For a basic implementation:

- Raspberry Pi 3B+
- 2x DC motors with simple H-bridge controller
- 1x blade motor with simple PWM control
- 2x ultrasonic sensors
- Basic IMU (MPU6050)
- 12V battery power system

## Software Prerequisites

- **Operating System**: Raspberry Pi OS (Debian Bullseye or newer)
- **Python**: 3.7 or newer
- **Required Libraries**:
  - RPi.GPIO or gpiozero
  - numpy
  - pyyaml
  - smbus2 (for I2C sensors)
  - picamera2
  - pyserial (for GPS)

## Installation

### Basic Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/KhryptorGraphics/robot-mower-advanced.git
   cd robot-mower-advanced
   ```

2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a configuration file:
   ```bash
   cp config/example_config.yaml config/local_config.yaml
   ```

4. Customize the configuration file based on your hardware setup (see [Configuration](#configuration))

5. Run the system:
   ```bash
   python main.py --config config/local_config.yaml
   ```

### Docker Installation

For development and testing without physical hardware:

1. Build the Docker image:
   ```bash
   docker build -t robot-mower-advanced .
   ```

2. Run the container:
   ```bash
   docker run -p 8080:8080 -v $(pwd)/config:/app/config robot-mower-advanced
   ```

### Raspberry Pi Installation Script

For a complete installation on a fresh Raspberry Pi:

```bash
curl -sSL https://raw.githubusercontent.com/KhryptorGraphics/robot-mower-advanced/main/setup/install.sh | bash
```

## Configuration

The system uses YAML configuration files to define hardware setup, sensor parameters, and operational settings.

### Example Configuration

```yaml
# Basic system configuration
system:
  name: "Robot Mower Advanced"
  log_level: "INFO"
  log_file: "/var/log/robot_mower.log"
  units: "metric"  # or "imperial"

# Hardware configuration
hardware:
  # Motor controller settings
  motor_controller:
    type: "pwm"  # or "gpiozero"
    left_enable_pin: 5
    left_forward_pin: 24
    left_reverse_pin: 23
    right_enable_pin: 6
    right_forward_pin: 27
    right_reverse_pin: 22
    pwm_frequency: 1000

  # Blade motor settings
  blade_motor:
    type: "rpi"  # or "pwm" for ESC
    pin: 18
    relay_pin: 26
    pwm_frequency: 1000
    soft_start: true
    soft_start_duration: 2.0

  # Sensor configurations
  sensors:
    # Ultrasonic sensors
    ultrasonic:
      - name: "front_center"
        trigger_pin: 16
        echo_pin: 20
        min_distance: 5  # cm
        max_distance: 400  # cm
      - name: "front_left"
        trigger_pin: 17
        echo_pin: 21
        min_distance: 5
        max_distance: 300
      - name: "front_right"
        trigger_pin: 26
        echo_pin: 19
        min_distance: 5
        max_distance: 300
    
    # IMU settings
    imu:
      i2c_bus: 1
      i2c_address: 0x68  # MPU6050 default address
      update_rate: 100  # Hz
      movement_threshold: 0.2  # m/s²
    
    # GPS settings
    gps:
      uart_port: "/dev/ttyS0"
      baud_rate: 9600
      update_rate: 1  # Hz
    
    # Camera settings
    camera:
      enable: true
      width: 1280
      height: 720
      fps: 30
      format: "RGB"
    
    # Battery monitoring
    battery:
      voltage_pin: 4
      current_pin: 17
      capacity_mah: 10000
      cells: 4
      low_voltage_threshold: 13.2  # V
      critical_voltage_threshold: 12.8  # V
    
    # Status LEDs
    leds:
      status_led_green: 12
      status_led_red: 13
      status_led_blue: 14
    
    # Environmental sensors
    rain_sensor:
      enable: true
      pin: 27
    
    tilt_sensor:
      enable: true
      use_imu: true  # Use IMU for tilt detection
      pin: 22  # Only used if use_imu is false
      max_tilt_angle: 30.0  # degrees
      upside_down_angle: 170.0  # degrees

# Navigation settings
navigation:
  gps_precision: 0.5  # meters
  waypoint_tolerance: 1.0  # meters
  perimeter_file: "data/perimeter.json"
  obstacles_file: "data/obstacles.json"
  lawn_pattern: "parallel"  # or "spiral", "random"
  max_speed: 0.3  # m/s

# Mowing settings
mowing:
  blade_speed: 0.8  # 0.0 to 1.0
  cutting_height: 50  # mm
  safety_timeout: 30  # seconds
  rain_delay: 3600  # seconds to wait after rain before mowing
  auto_return_home: true  # Auto return to charging station
```

### Hardware-Specific Configurations

Configurations for popular hardware setups are available in the `config/hardware` directory:

- `config/hardware/raspberrypi4_standard.yaml` - Standard Raspberry Pi 4 setup
- `config/hardware/raspberrypi3_minimal.yaml` - Minimal Raspberry Pi 3 setup
- `config/hardware/simulation.yaml` - Simulation configuration without physical hardware

## Deployment

### Development Environment

For development and testing:

```bash
# Run in development mode with console output
python main.py --config config/local_config.yaml --dev
```

### Production Deployment

For production deployment on a robot mower:

1. Set up the system to run as a service:
   ```bash
   sudo cp setup/robot-mower.service /etc/systemd/system/
   sudo systemctl enable robot-mower
   sudo systemctl start robot-mower
   ```

2. Monitor the service status:
   ```bash
   sudo systemctl status robot-mower
   ```

3. View logs:
   ```bash
   sudo journalctl -u robot-mower -f
   ```

### Web Interface

The system includes a web interface for monitoring and control:

1. Access the web interface at `http://<raspberry-pi-ip>:8080`
2. Default credentials:
   - Username: `admin`
   - Password: `robotmower`

### Remote Access

For remote access and monitoring:

1. Set up port forwarding on your router to expose port 8080 (optional, security risk)
2. Better option: Set up a VPN server on your local network
3. Use the mobile app for simplified remote control

## Troubleshooting

### Common Issues

#### Hardware Detection Problems

If sensors or motors aren't detected:

1. Check GPIO pin configurations in your config file
2. Verify I2C/SPI/UART interfaces are enabled:
   ```bash
   sudo raspi-config
   # Navigate to Interface Options and enable I2C, SPI, Serial as needed
   ```
3. Test individual components:
   ```bash
   python tools/test_hardware.py --component ultrasonic --pin 16,20
   ```

#### Motor Control Issues

If motors aren't responding correctly:

1. Check wiring and connections
2. Verify motor controller power (separate from Pi power)
3. Test motors directly:
   ```bash
   python tools/test_motors.py --left-speed 0.5 --right-speed 0.5
   ```

#### GPS Signal Problems

For GPS issues:

1. Ensure clear sky view for the antenna
2. Check UART configuration and connections
3. Verify GPS module has power
4. Monitor raw GPS data:
   ```bash
   python tools/monitor_gps.py
   ```

### Diagnostic Commands

Run diagnostics to check system health:

```bash
python tools/run_diagnostics.py --full
```

View system status:

```bash
python tools/system_status.py
```

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
