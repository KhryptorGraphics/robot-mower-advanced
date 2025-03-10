# Robot Mower Advanced

An advanced robotic lawn mower platform with SLAM mapping, computer vision, path planning, and remote control capabilities. This open-source project provides a comprehensive solution for building and operating an autonomous lawn mower with sophisticated features typically found in high-end commercial systems.

![Robot Mower Advanced](https://placehold.co/600x400/forest/white?text=Robot+Mower+Advanced)

## Table of Contents

- [Features](#features)
- [System Architecture](#system-architecture)
- [Hardware Requirements](#hardware-requirements)
  - [Raspberry Pi Setup](#raspberry-pi-setup)
  - [Control Panel Server Setup](#control-panel-server-setup)
  - [Optional Components](#optional-components)
- [Installation](#installation)
  - [Raspberry Pi Installation](#raspberry-pi-installation)
  - [Ubuntu Server Installation](#ubuntu-server-installation)
- [Configuration](#configuration)
  - [Core Settings](#core-settings)
  - [SLAM Configuration](#slam-configuration)
  - [Path Planning Configuration](#path-planning-configuration)
  - [Hardware Configuration](#hardware-configuration)
  - [Web Interface Configuration](#web-interface-configuration)
- [Usage](#usage)
  - [Web Interface](#web-interface)
  - [Zone Management](#zone-management)
  - [Scheduling](#scheduling)
  - [Manual Control](#manual-control)
  - [Monitoring](#monitoring)
- [Software Architecture](#software-architecture)
  - [Directory Structure](#directory-structure)
  - [Core Components](#core-components)
  - [Module Interaction](#module-interaction)
- [Troubleshooting](#troubleshooting)
- [Maintenance](#maintenance)
- [Contributing](#contributing)
- [License](#license)

## Features

- **SLAM Mapping**: Creates and maintains a map of your lawn using sensor fusion
  - Integrates data from GPS, IMU, wheel encoders, and cameras
  - Performs real-time graph optimization to improve accuracy
  - Stores and loads maps for persistent operation

- **Computer Vision**: Detects obstacles, boundaries, and lawn health
  - Object detection using Hailo NPU (if available) or CPU-based inference
  - Boundary detection to identify lawn edges and obstacles
  - Lawn health monitoring with regular aerial photos

- **Advanced Path Planning**: Efficient mowing patterns based on lawn shape
  - Multiple cutting patterns: parallel, spiral, zigzag, perimeter-first, adaptive
  - Dynamic obstacle avoidance with safety margins
  - Edge detection and following for clean boundaries

- **Remote Control**: Web interface for monitoring and control
  - Real-time status monitoring and visualization
  - Manual override and joystick control
  - Custom zone definition and management
  - Live camera feed with obstacle highlighting

- **Smart Scheduling**: Weather-aware mowing schedule
  - Integration with weather forecast data (optional)
  - Configurable time slots and zone preferences
  - Battery-aware scheduling to ensure complete coverage

- **Safety Features**: Comprehensive obstacle detection and avoidance
  - Multiple ultrasonic sensors for 360° coverage
  - Emergency stop on obstacle detection
  - Tilt and bump sensors for safety
  - Children and pet detection with extra safety margins

- **Extensible Framework**: Modular design for easy customization
  - Configurable hardware support for different sensors and motors
  - Plugin architecture for custom extensions
  - Comprehensive logging and debugging tools

## System Architecture

The Robot Mower Advanced system consists of two main components:

1. **Raspberry Pi Controller**: Installed on the mower itself
   - Handles real-time control, sensor integration, and decision making
   - Runs the core SLAM and navigation algorithms
   - Communicates with motor controllers and sensors
   - Operates autonomously when disconnected from the network

2. **Control Panel Server**: Runs on a separate Ubuntu machine
   - Provides the web interface for remote control and monitoring
   - Stores long-term data and statistics
   - Handles scheduling and higher-level planning
   - Serves as the central point for user interaction

These components communicate over your local network using a secure protocol, with the mower operating independently when network connectivity is unavailable.

```
                  ┌───────────────────┐         ┌───────────────────┐
                  │   Raspberry Pi    │         │   Ubuntu Server   │
                  │   (on Mower)      │◄────────►   (Control Panel) │
                  └───────────────────┘         └───────────────────┘
                           ▲                             ▲
                           │                             │
                           ▼                             ▼
┌───────────────────────────────────────┐   ┌───────────────────────────────┐
│ • Motors & Motion Control             │   │ • Web Interface               │
│ • Sensors (Ultrasonic, GPS, IMU)      │   │ • Data Storage & Analysis     │
│ • Camera & Computer Vision            │   │ • User Authentication         │
│ • SLAM & Path Planning                │   │ • Scheduling & Zone Management │
│ • Safety Monitoring                   │   │ • Weather Integration         │
└───────────────────────────────────────┘   └───────────────────────────────┘
```

## Hardware Requirements

### Raspberry Pi Setup

- **Compute Platform**:
  - Raspberry Pi 4 (4GB+ RAM recommended)
  - 32GB+ microSD card (high endurance recommended)
  - Cooling case or heatsinks

- **Sensors**:
  - 4-6× Ultrasonic sensors (HC-SR04 or similar) for obstacle detection
  - IMU sensor (MPU6050 or similar) for orientation and tilt detection
  - Wheel encoders for odometry
  - Camera module (Raspberry Pi Camera v2 or better)
  - Optional: GPS module (with RTK support for enhanced precision)
  - Optional: Time-of-Flight (ToF) distance sensors for improved accuracy

- **Motor Control**:
  - Motor controller board (L298N or similar for small mowers)
  - Alternatively: Robust MOSFET-based H-bridges for larger mowers
  - PWM control for speed regulation
  - Current sensing for motor monitoring

- **Power System**:
  - 12V/24V battery system (LiFePO4 recommended for longer life)
  - DC-DC converter for Raspberry Pi power supply
  - Power monitoring circuit
  - Charging dock contacts (if implementing automated charging)

- **Additional Hardware**:
  - Rain sensor
  - Emergency stop button
  - Status LEDs and/or small display
  - 3D-printed or custom-built enclosure for electronics
  - Optional: Hailo NPU for accelerated computer vision

### Control Panel Server Setup

- **System Requirements**:
  - Any Ubuntu-compatible system (18.04 or newer)
  - Minimum 2GB RAM, recommended 4GB
  - 10GB+ storage space
  - Network connection to the Raspberry Pi (Ethernet or WiFi)
  - Can be a physical machine, VM, or cloud instance

- **Network Requirements**:
  - Local network with the mower (for direct control)
  - Internet connection (optional, for weather data)
  - Static IP recommended or proper DNS setup
  - Firewall configuration to allow access to Control Panel port (7799)

### Optional Components

- **Docking Station**:
  - Charging contacts compatible with the mower
  - Weather protection
  - Guide markers for precise docking

- **Boundary Markers**:
  - Physical markers for SLAM alignment
  - QR codes or ArUco markers for vision-based localization
  - Optional: Boundary wire system for traditional boundaries

- **Advanced Add-ons**:
  - Lawn quality sensors (soil moisture, etc.)
  - RTK base station for cm-level GPS precision
  - Additional cameras for better coverage
  - Weather station integration

## Installation

### Raspberry Pi Installation

The installation script is modular and allows for customization of which components to install.

1. **Prepare the Raspberry Pi**:
   ```bash
   # Flash Raspberry Pi OS (64-bit recommended)
   # Boot and perform initial setup (enable SSH, I2C, SPI, Camera)
   sudo apt update && sudo apt upgrade -y
   ```

2. **Clone the Repository**:
   ```bash
   git clone https://github.com/khryptorgraphics/robot-mower-advanced.git
   cd robot-mower-advanced
   ```

3. **Run the Installation Script**:
   ```bash
   sudo ./scripts/install_raspberry_pi.sh
   ```
   The script will guide you through the installation process with the following options:
   - Core system installation
   - Hardware interface configuration
   - Optional Hailo NPU integration
   - SLAM and path planning configuration
   - Web interface setup
   - Service configuration

4. **Modules Installed**:
   The Raspberry Pi installation includes several specialized modules:
   - `core_install.sh`: Core system installation and repository management
   - `dependencies.sh`: Hardware dependencies and Python packages
   - `hailo_setup.sh`: Optional Hailo NPU configuration for enhanced vision
   - `slam_path_planning.sh`: SLAM and navigation system setup
   - `service_setup.sh`: Systemd services for automatic startup

5. **Post-Installation**:
   After installation, the system will prompt for a reboot:
   ```bash
   sudo reboot
   ```

### Ubuntu Server Installation

1. **Prepare the Ubuntu Server**:
   ```bash
   # Install Ubuntu Server 20.04 LTS or newer
   sudo apt update && sudo apt upgrade -y
   ```

2. **Clone the Repository**:
   ```bash
   git clone https://github.com/khryptorgraphics/robot-mower-advanced.git
   cd robot-mower-advanced
   ```

3. **Run the Installation Script**:
   ```bash
   sudo ./scripts/install_ubuntu_server.sh
   ```
   The script will guide you through the installation process with the following options:
   - Core system installation
   - Web application setup
   - Database configuration
   - Nginx configuration
   - Service setup

4. **Modules Installed**:
   The Ubuntu Server installation includes several specialized modules:
   - `core_install.sh`: Core system installation and dependencies
   - `web_app_template.sh`: Flask web application setup
   - `html_templates.sh`: Web interface HTML templates
   - `config_manager.sh`: Configuration file management
   - `service_setup.sh`: Nginx and systemd service configuration

5. **Post-Installation**:
   After installation, the Control Panel will be available at:
   ```
   http://[server-ip]:7799
   ```
   Default login credentials:
   - Username: admin
   - Password: admin (change this immediately after first login)

## Configuration

All configuration is managed through YAML files located in the `config/` directory:

### Core Settings

**File: config/local_config.yaml**

```yaml
# System configuration
system:
  data_dir: "/home/pi/robot-mower-advanced/data"
  log_level: "info"  # debug, info, warning, error
  log_to_file: true
  log_file: "logs/robot_mower.log"
  enable_remote_monitoring: true
  enable_telemetry: true

# Mower hardware configuration
mower:
  name: "LawnMaster 5000"
  cutting_width_mm: 320
  max_speed_mps: 0.5  # meters per second
  min_turning_radius_m: 0.5
  wheel_diameter_mm: 200
  encoder_pulses_per_revolution: 20
  battery_capacity_mah: 5000
  battery_voltage: 24.0
  low_battery_threshold: 20  # percent
  critical_battery_threshold: 10  # percent
```

### SLAM Configuration

```yaml
# SLAM configuration
slam:
  enabled: true
  map_resolution: 0.05  # meters per pixel
  map_size: 100.0  # size in meters
  add_pose_interval: 1.0  # seconds
  mapping_interval: 0.5  # seconds
  localization_interval: 0.1  # seconds
  optimization_interval: 5.0  # seconds
  gps_weight: 0.7
  imu_weight: 0.8
  odometry_weight: 0.5
  visual_odometry_scale: 0.01
  map_save_interval: 60  # seconds
```

### Path Planning Configuration

```yaml
# Navigation configuration
navigation:
  path_planning:
    enabled: true
    safety_margin_m: 0.2  # meters
    edge_detection_enabled: true
    edge_follow_distance_m: 0.1  # meters
  obstacle_avoidance:
    enabled: true
    detection_range_m: 3.0  # meters
    stop_distance_m: 0.5  # meters
  pattern: "adaptive"  # parallel, spiral, zigzag, perimeter_first, adaptive, custom
  overlap_percent: 15.0
  cutting_direction_degrees: 0.0
  speed_normal: 0.4  # meters per second
  speed_edge: 0.3  # meters per second for edge following
  speed_docking: 0.2  # meters per second for docking
```

### Hardware Configuration

```yaml
# Motor configuration
motors:
  left_motor:
    forward_pin: 17
    backward_pin: 18
    pwm_pin: 12
    pwm_frequency: 1000
  right_motor:
    forward_pin: 22
    backward_pin: 23
    pwm_pin: 13
    pwm_frequency: 1000
  cutting_motor:
    enable_pin: 24
    pwm_pin: 25
    pwm_frequency: 1000

# Sensor configuration
sensors:
  ultrasonic:
    - name: "front"
      trigger_pin: 5
      echo_pin: 6
    - name: "left_front"
      trigger_pin: 19
      echo_pin: 26
    - name: "right_front"
      trigger_pin: 16
      echo_pin: 20
    - name: "rear"
      trigger_pin: 21
      echo_pin: 7
  imu:
    i2c_bus: 1
    i2c_address: 0x68
  gps:
    enabled: true
    serial_port: "/dev/ttyACM0"
    baud_rate: 9600
  camera:
    enabled: true
    width: 640
    height: 480
    fps: 30
    index: 0
```

### Web Interface Configuration

```yaml
# Web interface configuration
web:
  enabled: true
  host: "0.0.0.0"
  port: 7799
  debug: false
  enable_ssl: false
  ssl_cert: ""
  ssl_key: ""
  session_lifetime: 86400  # seconds (24 hours)
  enable_camera_stream: true
  camera_stream_quality: 75
  camera_stream_fps: 10
```

## Usage

### Web Interface

The web interface provides a comprehensive dashboard for monitoring and controlling the robot mower. It's accessible at `http://[server-ip]:7799` after installation.

#### Main Dashboard

![Dashboard](https://placehold.co/800x600/grey/white?text=Robot+Mower+Dashboard)

The main dashboard provides:
- Current status and battery level
- Mowing progress and statistics
- Live map view with mower position
- Quick controls (Start, Stop, Return to Dock)
- Alert notifications
- Current weather conditions (if configured)

#### Control Panel

The control panel allows direct control over the mower's operations:
- Manual joystick control
- Pattern selection
- Cutting height adjustment
- Speed settings
- Motor status monitoring
- Emergency stop

### Zone Management

Zones can be defined to specify different mowing areas, each with their own settings:

1. Navigate to the Zone Management page
2. Click "Add New Zone"
3. Draw the zone perimeter on the map
4. Set zone properties:
   - Name and priority
   - Mowing pattern
   - Cutting height
   - Schedule preferences
   - Edge handling behavior
5. Save the zone configuration

Zones can be organized into mowing sequences for efficient lawn maintenance.

### Scheduling

The scheduling system allows you to set up automated mowing sessions:

1. Navigate to the Scheduling page
2. Create a new schedule with:
   - Start time and duration
   - Days of the week
   - Zones to mow
   - Weather conditions to avoid
3. Enable/disable schedules as needed

The system will automatically follow the schedule, taking into account battery levels and weather conditions.

### Manual Control

For direct control of the mower:

1. Navigate to the Manual Control page
2. Use the directional pad or keyboard controls
3. Adjust speed using the slider
4. Enable/disable cutting motor
5. Monitor sensor readings in real-time

### Monitoring

The monitoring section provides detailed information about the mower's operation:

- Battery trends and charging cycles
- Coverage maps showing mowed areas
- Sensor data history
- Motor performance metrics
- System log viewer

## Software Architecture

### Directory Structure

```
robot-mower-advanced/
├── config/                 # Configuration files
│   ├── default_config.yaml # Default configuration (do not edit)
│   └── local_config.yaml   # Local configuration (overrides defaults)
├── data/                   # Data storage directory
│   ├── lawn_images/        # Captured lawn images
│   ├── lawn_reports/       # Generated reports
│   ├── slam_maps/          # SLAM-generated maps
│   └── zone_definitions/   # Mowing zone definitions
├── hardware/               # Hardware interface modules
│   ├── motor_control.py    # Motor control interface
│   ├── sensors/            # Sensor interface modules
│   └── peripherals/        # Additional hardware interfaces
├── navigation/             # Navigation and path planning
│   ├── advanced_path_planning.py # Advanced path planning
│   ├── obstacle_avoidance.py     # Obstacle avoidance system
│   └── path_execution.py   # Path execution controller
├── perception/             # Perception system
│   ├── camera_processor.py # Camera data processing
│   ├── hailo_integration.py # Hailo NPU integration
│   ├── object_detection.py # Object detection system
│   └── slam/               # SLAM implementation
│       ├── slam_core.py    # Core SLAM functionality
│       └── map_manager.py  # Map management
├── scripts/                # Installation and utility scripts
│   ├── install_raspberry_pi.sh     # Raspberry Pi installation
│   ├── install_ubuntu_server.sh    # Ubuntu Server installation
│   ├── raspberry_pi_modules/       # Raspberry Pi installation modules
│   └── ubuntu_install_modules/     # Ubuntu Server installation modules
├── utils/                  # Utility functions
│   ├── config_manager.py   # Configuration management
│   ├── telemetry.py        # Telemetry and data collection
│   └── logging_setup.py    # Logging configuration
├── web/                    # Web interface
│   ├── server.py           # Flask web server
│   ├── static/             # Static web assets
│   └── templates/          # HTML templates
├── main.py                 # Main application entry point
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

### Core Components

#### Perception System

The perception system processes sensor data to understand the mower's environment:

- **SLAM Module**: Performs simultaneous localization and mapping
  - Integrates sensor data from GPS, IMU, wheel encoders
  - Maintains a consistent map of the environment
  - Provides real-time position estimates

- **Computer Vision**: Processes camera data
  - Object detection for obstacles and boundaries
  - Lawn health analysis
  - Visual odometry for motion estimation

- **Sensor Fusion**: Combines data from multiple sensors
  - Kalman filtering for improved accuracy
  - Uncertainty handling and confidence estimation
  - Fault detection and sensor validation

#### Navigation System

The navigation system plans and executes mowing paths:

- **Path Planning**: Plans efficient mowing patterns
  - Multiple pattern types (parallel, spiral, etc.)
  - Coverage optimization
  - Path adaptation based on obstacles

- **Obstacle Avoidance**: Ensures safe operation
  - Real-time obstacle detection
  - Path adjustment to avoid obstacles
  - Safety margin enforcement

- **Motion Control**: Manages motor commands
  - Speed and direction control
  - Smooth acceleration and deceleration
  - Precision turning

#### Web Interface

The web interface provides user interaction:

- **Flask Backend**: Handles API requests and business logic
  - RESTful API for mower control
  - WebSocket for real-time updates
  - Authentication and security

- **Frontend**: User interface components
  - Responsive dashboard
  - Interactive map visualization
  - Controls and settings management

### Module Interaction

The system uses an event-driven architecture with these main interaction patterns:

1. **Perception Pipeline**:
   ```
   Sensors → Data Preprocessing → Feature Extraction → SLAM → World Model
   ```

2. **Decision Making**:
   ```
   World Model → Path Planning → Obstacle Avoidance → Motion Commands
   ```

3. **Control Loop**:
   ```
   Motion Commands → Motor Controllers → Encoders → Feedback → Adjustment
   ```

4. **User Interaction**:
   ```
   Web UI → API Calls → Command Processing → Status Updates → Web UI
   ```

## Troubleshooting

### Common Issues

#### Mower Won't Start

1. **Check power**:
   ```bash
   # On the Raspberry Pi
   sudo systemctl status robot-mower.service
   # Check voltage
   python3 -c "import hardware.power_monitor as pm; print(pm.get_battery_voltage())"
   ```

2. **Check for errors**:
   ```bash
   # View logs
   sudo journalctl -u robot-mower.service -n 100
   ```

3. **Check hardware connections**:
   - Verify motor controller connections
   - Check for blown fuses
   - Ensure emergency stop is not engaged

#### Web Interface Unavailable

1. **Check service status**:
   ```bash
   # On the Ubuntu server
   sudo systemctl status robot-mower-web.service
   ```

2. **Check network connectivity**:
   ```bash
   ping [raspberry-pi-ip]
   ```

3. **Check firewall settings**:
   ```bash
   sudo ufw status
   # Ensure port 7799 is allowed
   sudo ufw allow 7799/tcp
   ```

#### Poor Navigation Performance

1. **Check sensor data**:
   ```bash
   # On the Raspberry Pi
   python3 -c "import utils.diagnostics as diag; diag.run_sensor_test()"
   ```

2. **Verify SLAM map**:
   - Check the generated map in the web interface
   - Ensure the map has good coverage
   - Look for inconsistencies in the map

3. **Recalibrate sensors**:
   ```bash
   # Run calibration tool
   cd /home/pi/robot-mower-advanced
   python3 utils/calibrate_sensors.py
   ```

### Diagnostic Tools

The system includes several diagnostic tools to help troubleshoot issues:

1. **Hardware Test**:
   ```bash
   cd /home/pi/robot-mower-advanced
   python3 utils/hardware_test.py
   ```
   This runs a comprehensive test of all hardware components.

2. **SLAM Diagnostics**:
   ```bash
   cd /home/pi/robot-mower-advanced
   python3 perception/slam/diagnostic.py
   ```
   This checks the SLAM system and can generate diagnostic maps.

3. **Network Diagnostics**:
   ```bash
   cd /home/pi/robot-mower-advanced
   python3 utils/network_diagnostic.py
   ```
   This verifies connectivity between the Raspberry Pi and Control Panel.

## Maintenance

### Regular Maintenance Tasks

#### Software Updates

```bash
# On both Raspberry Pi and Ubuntu server
cd /home/pi/robot-mower-advanced  # Or appropriate path
git pull
sudo ./scripts/update.sh
```

#### Database Maintenance

```bash
# On Ubuntu server
cd /home/ubuntu/robot-mower-advanced  # Or appropriate path
python3 utils/maintain_database.py
```

#### Log Rotation

Log rotation is configured automatically, but you can manually rotate logs:

```bash
# On Raspberry Pi
sudo logrotate -f /etc/logrotate.d/robot-mower
```

### Hardware Maintenance

Regular hardware maintenance should include:

1. **Blade Inspection and Replacement**:
   - Check blades for damage every 20-30 hours of operation
   - Replace blades when dulled or damaged

2. **Sensor Cleaning**:
   - Clean ultrasonic sensors with compressed air
   - Wipe camera lens with microfiber cloth
   - Remove debris from wheel encoders

3. **Battery Maintenance**:
   - Check battery terminals for corrosion
   - Perform full discharge/charge cycle monthly
   - Replace batteries every 2-3 years

4. **Mechanical Inspection**:
   - Check for loose screws and connections
   - Inspect wheels and drive train
   - Lubricate moving parts as needed

## Contributing

To contribute to the project, please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Environment Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/robot-mower-advanced.git
cd robot-mower-advanced

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest
```

### Coding Standards

- Follow PEP 8 for Python code
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Write unit tests for new functionality
- Keep modules focused and single-purpose

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Note**: This is an open-source project, and while we strive to make it as reliable and safe as possible, use it at your own risk. Always maintain proper supervision of autonomous lawn mowing equipment.
