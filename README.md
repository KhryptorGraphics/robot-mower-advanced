*** IN DEVELOPMENT

# Robot Mower Advanced

An advanced control system for autonomous robotic lawn mowers with edge detection, obstacle avoidance, weather-based scheduling, and more.

## Overview

Robot Mower Advanced is a complete software solution for controlling autonomous lawn mowing robots. It provides a robust foundation of core functionality with advanced features like weather-based scheduling, lawn health analysis, and anti-theft protection. The system is designed for use with Raspberry Pi hardware for the main control unit, with an optional Ubuntu server component that provides a remote control panel accessible on port 7799.

## System Architecture

The Robot Mower Advanced system consists of two main components:

1. **Main Control System** (Raspberry Pi): Controls the mower's hardware, sensors, and decision-making processes
2. **Remote Control Panel** (Ubuntu Server): Provides remote access and monitoring capabilities

The architecture follows a modular design with clear separation of concerns:

```
┌─────────────────────────────────────────┐      ┌─────────────────────────────────┐
│      Raspberry Pi Control System        │      │    Ubuntu Server Control Panel   │
│                                         │      │                                  │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  │      │  ┌─────────────────────────────┐│
│  │ Hardware│  │Navigation│  │Perception│  │      │  │                             ││
│  │ Control │  │  & Path  │  │ & Object │  │◄────►│  │     Web Control Panel      ││
│  │ Systems │  │ Planning │  │Detection │  │      │  │                             ││
│  └─────────┘  └─────────┘  └─────────┘  │      │  └─────────────────────────────┘│
│                                         │      │                                  │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  │      │  ┌─────────────────────────────┐│
│  │Scheduling│  │ Security │  │  Core   │  │      │  │                             ││
│  │& Weather │  │ & Theft  │  │ System  │  │      │  │      Security & Access      ││
│  │Monitoring│  │Protection│  │Services │  │      │  │                             ││
│  └─────────┘  └─────────┘  └─────────┘  │      │  └─────────────────────────────┘│
│                                         │      │                                  │
│  ┌──────────────────────────────────┐  │      │  ┌─────────────────────────────┐│
│  │                                   │  │      │  │                             ││
│  │       Local Web Interface         │  │      │  │     Configuration & Logs    ││
│  │                                   │  │      │  │                             ││
│  └──────────────────────────────────┘  │      │  └─────────────────────────────┘│
└─────────────────────────────────────────┘      └─────────────────────────────────┘
```

## Features

- **Multi-Zone Management**: Define and manage multiple lawn zones with different mowing patterns
- **Edge Detection and Following**: Precisely mow along the edges of the lawn for a clean finish
- **Advanced Navigation**: Multiple mowing patterns including parallel, spiral, zigzag, and perimeter-first
- **Object Detection**: Identify and avoid obstacles with special attention to safety-critical objects
- **Lawn Health Analysis**: Monitor lawn health and get recommendations for improvements
- **Grass Growth Prediction**: Smart scheduling based on predicted grass growth rates
- **Weather-Based Scheduling**: Automatically adjust mowing schedule based on weather forecasts
- **Maintenance Tracking**: Track blade replacement, cleaning, and other maintenance tasks
- **Anti-Theft Protection**: GPS tracking and geofencing with alerts for unauthorized movement
- **Web Interface**: Control and monitor the mower from any browser
- **Robust Architecture**: Modular design with dependency injection and hardware abstraction

## Installation

### Quick Start with Installation Scripts

We provide installation scripts for both the Raspberry Pi main control system and the Ubuntu server control panel:

#### Raspberry Pi Installation

1. Download the installation script:
   ```bash
   wget https://raw.githubusercontent.com/khryptorgraphics/robot-mower-advanced/main/scripts/install_raspberry_pi.sh
   ```

2. Make it executable and run it:
   ```bash
   chmod +x install_raspberry_pi.sh
   sudo ./install_raspberry_pi.sh
   ```

3. Follow the interactive prompts to complete the installation.

#### Ubuntu Server Control Panel Installation

1. Download the installation script:
   ```bash
   wget https://raw.githubusercontent.com/khryptorgraphics/robot-mower-advanced/main/scripts/install_ubuntu_server.sh
   ```

2. Make it executable and run it:
   ```bash
   chmod +x install_ubuntu_server.sh
   sudo ./install_ubuntu_server.sh
   ```

3. Follow the interactive prompts to complete the installation.

### Manual Installation

For detailed manual installation instructions, see [SETUP.md](SETUP.md).

## Hardware Requirements

### Computing Platform
- **Primary Controller**: Raspberry Pi 4B+ with 4GB RAM (8GB for optimal performance)
- **Storage**: 32GB+ Class 10 microSD card or USB SSD for improved reliability
- **Power Management**: UPS HAT for safe shutdown during low power
- **Connectivity**: Raspberry Pi with built-in Wi-Fi or external Wi-Fi adapter with antenna

### Sensor Suite (Minimally Required)
- **Distance Sensing**: At least 3× HC-SR04 ultrasonic sensors for basic obstacle detection
- **Orientation**: MPU6050 or MPU9250 IMU for orientation and tilt detection
- **Positioning**: GPS module (NEO-6M or NEO-M8N) for location tracking

For a complete list of recommended hardware components, see the [Hardware Recommendations](#hardware-recommendations) section.

## Configuration

### Basic Configuration

To customize your Robot Mower system, edit the local configuration file:

```bash
# On Raspberry Pi
sudo nano /home/pi/robot-mower-advanced/config/local_config.yaml

# On Ubuntu Server
sudo nano /opt/robot-mower-control-panel/config/local_config.yaml
```

### Hardware Configuration Example

Here's an example configuration for the motor controller:

```yaml
hardware:
  motor_controller:
    type: "dual_hbridge"  # Options: dual_hbridge, sabertooth, cytron, odrive
    pins:
      left_pwm: 12
      left_dir: 16
      right_pwm: 13
      right_dir: 20
      blade_pwm: 18
      blade_dir: 22
    pwm_frequency: 20000
```

### Web Interface Configuration

Example configuration for secure HTTPS access:

```yaml
web:
  enable_https: true
  cert_file: "certs/cert.pem"
  key_file: "certs/key.pem"
  port: 8080  # Port for the Raspberry Pi web interface
```

## Web Interface

Access the web interface at:

### Raspberry Pi Local Interface
```
http://<raspberry-pi-ip>:8080
```

### Ubuntu Server Remote Control Panel
```
http://<ubuntu-server-ip>:7799
```

Default credentials:
- Username: `admin`
- Password: `admin123` (change this immediately!)

## Directory Structure

```
robot-mower-advanced/
├── config/               # Configuration files
├── core/                 # Core system functionality
├── data/                 # Data storage
├── hardware/             # Hardware abstraction layer
│   └── sensors/          # Sensor implementations
├── logs/                 # Log files
├── maintenance/          # Maintenance tracking
├── navigation/           # Navigation and zone management
├── perception/           # Environmental perception
├── scheduling/           # Scheduling and timing
├── security/             # Anti-theft and security
├── web/                  # Web interface
│   ├── static/           # Static web assets
│   └── templates/        # HTML templates
├── scripts/              # Installation and utility scripts
├── main.py               # Main entry point
├── requirements.txt      # Python dependencies
├── SETUP.md              # Detailed setup instructions
└── README.md             # This file
```

## Hardware Recommendations

### Recommended Components

#### Motor System
- **Drive Motors**:
  - 2× 12-24V brushed DC motors with 100:1 gear ratio (torque over speed)
  - Alternative: Brushless motors with 50A+ ESCs for higher efficiency
  - Recommended models: MY1016 250W, Johnson/Buhler 71.4:1
- **Blade System**:
  - Direct drive: 24V 250W+ brushless motor with 30A ESC
  - Belt drive: 12V DC motor with 20:1 reduction
- **Motor Controllers**:
  - Dual H-Bridge 30A+ controller (Cytron MDD30A, Sabertooth 2×32)
  - PWM-capable for speed control
  - Regenerative braking capability recommended

#### Sensor Suite
- **Distance Sensing**:
  - 3-6× HC-SR04 ultrasonic sensors (minimum 3 for basic obstacle detection)
  - Optional: ToF (Time of Flight) sensors for improved accuracy (VL53L0X)
  - Optional: LiDAR for comprehensive mapping (YDLIDAR X4)
- **Orientation**:
  - IMU: MPU6050 or MPU9250 for orientation and tilt detection
  - Optional: 9-DoF IMU (BNO055) for simplified sensor fusion
- **Positioning**:
  - GPS: NEO-6M or NEO-M8N module with external antenna
  - Optional: RTK GPS for cm-level precision (significantly higher cost)
- **Vision**:
  - Raspberry Pi Camera V2 or HQ Camera
  - Optional: Wide-angle lens for better obstacle detection
  - Optional: Dual cameras for stereo vision and improved depth perception
- **Environment**:
  - Rain sensor (YL-83 or capacitive type)
  - Temperature/humidity sensor (DHT22)
  - Light sensor (BH1750 or TSL2561)
- **Power Monitoring**:
  - INA219 current/voltage sensor for battery monitoring
  - Voltage divider circuit for simple voltage monitoring

#### Chassis & Construction
- **Frame Material**:
  - Aluminum for lightweight strength
  - HDPE (High-Density Polyethylene) for weather resistance
  - 3D printed components for custom parts
- **Wheels**:
  - 8-10" pneumatic tires for rough terrain
  - Solid rubber for maintenance-free operation
  - Minimum of 3" width for stability
- **Enclosure**:
  - IP65+ rated enclosure for electronics
  - UV-resistant plastic for exposed components
  - Ventilation with dust/water protection

#### Power System
- **Battery**:
  - Primary: 12V-24V LiFePO4 battery (20Ah+ for 3+ hours runtime)
  - Alternative: SLA (Sealed Lead Acid) batteries (cheaper but heavier)
  - Alternative: Li-ion 18650 cells in appropriate configuration
- **Power Distribution**:
  - DC-DC converter (12V/24V → 5V 3A) for Raspberry Pi
  - Separate power rails for motors and electronics
  - Fuses for all major circuits
- **Charging**:
  - Automated charging dock with contact pads
  - Solar panel option for extended autonomous operation
  - Battery management system for LiFePO4/Li-ion batteries

### Tiered Hardware Configurations

#### Entry Level (~$300-500)
- Raspberry Pi 3B+
- 2× 12V DC motors with basic encoders
- H-Bridge motor controller
- 3× HC-SR04 ultrasonic sensors
- Basic IMU (MPU6050)
- 12V SLA battery (7-10Ah)
- Plastic chassis with solid wheels
- Basic 12V DC cutting motor

#### Standard Build (~$500-800)
- Raspberry Pi 4B (4GB)
- 2× 12V DC motors with quadrature encoders
- Dual channel 30A motor controller
- 5× HC-SR04 ultrasonic sensors
- 9-DoF IMU
- NEO-6M GPS module
- Raspberry Pi Camera
- LiFePO4 battery (15Ah)
- Aluminum/HDPE chassis with pneumatic wheels
- 24V DC cutting motor with ESC

#### Advanced Setup (~$800-1500)
- Raspberry Pi 4B (8GB)
- 2× 24V brushless motors with hall sensors
- High-quality ESCs with regenerative braking
- 2D LiDAR for mapping
- RTK GPS for precision positioning
- Stereo camera system
- Complete environmental sensor suite
- 24V 30Ah LiFePO4 battery
- Solar charging capability
- Custom aluminum chassis with suspension
- 24V brushless cutting system with multiple blades

## Usage

### Basic Operation

Start the robot mower on the Raspberry Pi with default settings:

```bash
python3 main.py
```

### Command Line Options

- `--config PATH` - Specify a configuration file path
- `--log-level LEVEL` - Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `--data-dir PATH` - Override data directory path
- `--dev` - Run in development mode (more verbose output)
- `--no-web` - Disable web interface
- `--sim` - Run in simulation mode (no physical hardware)
- `--test` - Run system test and exit
- `--update` - Update software from GitHub repository
- `--backup` - Create a backup of configuration and data
- `--restore PATH` - Restore from a backup file
- `--reset-config` - Reset to default configuration
- `--calibrate` - Run sensor calibration routines

## API Documentation

The Robot Mower system provides a RESTful API for integration with other systems. The API is available at:

```
http://<raspberry-pi-ip>:8080/api/v1/
```

Or if using HTTPS:

```
https://<raspberry-pi-ip>:8080/api/v1/
```

For the remote control panel:

```
http://<ubuntu-server-ip>:7799/api/v1/
```

API documentation is available at `/api/docs` on both interfaces.

## Troubleshooting

### Common Issues and Solutions

#### Hardware Issues

- **Motors not moving**:
  - Check wiring connections to motor controllers
  - Verify proper GPIO pin configuration in local_config.yaml
  - Ensure sufficient battery voltage
  - Check motor driver for error codes/LEDs

- **Sensors not detecting obstacles**:
  - Verify sensor wiring and connections
  - Check GPIO pin configuration in local_config.yaml
  - Test individual sensors using the test scripts
  - Check for interference from other ultrasonic sources

- **IMU orientation issues**:
  - Calibrate the IMU by running calibration routine
  - Verify proper mounting orientation on chassis
  - Check I2C address configuration

#### Software Issues

- **Web interface not loading**:
  - Check if the service is running: `sudo systemctl status robot-mower.service`
  - Verify network connectivity to the device
  - Check port configuration (default 8080 for Pi, 7799 for server)
  - Look for errors in the logs: `sudo journalctl -u robot-mower.service`

- **Control panel connection problems**:
  - Verify both Raspberry Pi and Ubuntu server are on the same network
  - Check firewall settings on Ubuntu server
  - Verify proper IP configuration in local_config.yaml

- **System crashes or freezes**:
  - Check power supply stability (use a UPS if necessary)
  - Reduce CPU/memory load by disabling unused features
  - Check operating temperature of Raspberry Pi
  - Review logs for error messages

### Diagnostic Tools

Use the included diagnostic tools to help troubleshoot issues:

```bash
# Hardware diagnostics
python3 tools/hardware_diagnostics.py

# Sensor test
python3 tools/sensor_test.py

# Motor test
python3 tools/motor_test.py

# System information
python3 tools/system_info.py
```

## Security Considerations

- **Default Password**: Change the default admin password immediately after installation
- **Network Security**: Consider using a dedicated IoT network for the mower
- **HTTPS**: Enable HTTPS for secure communication with the web interface
- **Updates**: Keep the system updated with security patches
- **Remote Access**: Use a VPN if remote access is required from outside your network

## Maintenance

### System Maintenance

- **Updates**: Update the software regularly:
  ```bash
  cd /home/pi/robot-mower-advanced
  git pull
  pip3 install -r requirements.txt
  sudo systemctl restart robot-mower.service
  ```

- **Logs**: Review and clean up logs periodically:
  ```bash
  # View recent logs
  sudo journalctl -u robot-mower.service -n 100

  # Clear old logs
  sudo journalctl --vacuum-time=7d
  ```

- **Backups**: Back up your configuration and data:
  ```bash
  python3 main.py --backup
  ```

### Hardware Maintenance

Perform regular hardware maintenance to ensure reliable operation:

- Check and clean sensors weekly
- Verify all cable connections monthly
- Test emergency stop functionality before each use
- Replace the cutting blade every 50 hours of operation
- Check battery health and connections monthly
- Clean cooling fans and vents to prevent overheating

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

If you need help with this project, you can:

- Open an issue on GitHub
- Check the [Wiki](https://github.com/khryptorgraphics/robot-mower-advanced/wiki) for additional documentation
- Join our [Discord community](https://discord.gg/robot-mower-advanced) for real-time support
