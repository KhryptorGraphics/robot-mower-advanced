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

### Detailed Hardware List with Model Numbers

#### Raspberry Pi Setup

- **Compute Platform**:
  - **Raspberry Pi 4 Model B** (8GB RAM recommended, 4GB minimum) - [Raspberry Pi 4 Model B](https://www.raspberrypi.com/products/raspberry-pi-4-model-b/)
  - **32GB+ SanDisk Extreme Pro microSD card** (high endurance for prolonged logging)
  - **Raspberry Pi PoE HAT** or **Argon ONE M.2 Case** with cooling fan

- **Sensors**:
  - **Ultrasonic Sensors**: 6× HC-SR04 or 4× MaxBotix MB1240 (superior performance)
    - Front: 2× sensors (HC-SR04P or MaxBotix MB1240)
    - Sides: 2× sensors (HC-SR04P or MaxBotix MB1240)
    - Rear: 2× sensors (HC-SR04P or MaxBotix MB1240)
  
  - **IMU Sensor**: MPU-6050 or MPU-9250 (9-axis IMU recommended)
    - MPU-9250 preferred for Magnetometer functionality
    - Alternative: BNO055 for built-in sensor fusion
  
  - **Wheel Encoders**: 
    - LM393 Speed Sensor (2× units) or
    - AS5048A Magnetic Rotary Encoder (higher precision)
  
  - **Camera Module**: 
    - Raspberry Pi Camera Module 3 Wide (preferred)
    - Alternative: Raspberry Pi HQ Camera with 6mm Wide Angle Lens
  
  - **GPS Module**:
    - Standard: NEO-6M GPS Module
    - High Precision: NEO-M8P RTK GPS Module (centimeter precision)
    - Professional: Emlid Reach M2 RTK GPS (survey-grade)
  
  - **Optional Sensors**:
    - **ToF Sensors**: 3× VL53L1X Time-of-Flight sensors
    - **Rain Sensor**: YL-83 or FC-37 Rain Detection Module
    - **Tilt Sensor**: ADXL345 Accelerometer
    - **Grass Height Sensor**: ToF VL53L0X with custom mount

- **Motor Control**:
  - For Small Mowers:
    - **Motor Driver**: L298N Dual H-Bridge Motor Driver (up to 2A per channel)
    - Alternative: TB6612FNG Dual Motor Driver (better efficiency than L298N)
  
  - For Medium Mowers:
    - **Motor Driver**: Cytron 13A DC Motor Driver (MDD10A or MD13S)
    - Alternative: Pololu Dual G2 High-Power Motor Driver 18v18 or 24v13
  
  - For Large/Heavy Mowers:
    - **Motor Driver**: Sabertooth 2X32 or RoboClaw 2x30A Motor Controller
    - Alternative: ODrive v3.6 for brushless motor control
  
  - **Cutting Motor Control**:
    - BTS7960 43A High-Power Motor Driver for blade motor
    - Alternative: MOSFET IRF3205 with suitable gate driver

- **Power System**:
  - **Battery**:
    - **LiFePO4**: 4S 12.8V 20Ah battery pack (longer life, safer chemistry)
    - Alternative: 6S or 7S Li-ion 24V battery for higher power systems
    - Recommended Brands: RB/GBS/LiitoKala for LiFePO4, LiitoKala for Li-ion
  
  - **Power Management**:
    - DC-DC Converter: LM2596 based buck converter (3A version)
    - High-Current Version: DROK Buck Converter 8A or XL4016 DC-DC Converter
    - Power Monitoring: INA219 Current/Voltage Sensor
  
  - **Charging**:
    - TP4056 Li-ion Charging Boards (for small systems)
    - Robust Solution: Battery Management System (BMS) for 4S or 6S battery
    - Charging Contacts: 2× Spring-loaded Pogo Pins (gold-plated)

- **Additional Hardware**:
  - **Emergency Stop**: Red Mushroom E-Stop Button with NC contacts
  - **Status Display**: 0.96" OLED I2C Display (SSD1306 controller)
  - **Indicators**: 5× 5mm RGB LEDs for status indication
  - **Buttons/Switches**: 3× Waterproof Momentary Push Buttons
  - **Enclosure**: IP65 Rated ABS Enclosure (200×120×75mm minimum)
  - **Optional NPU**: Hailo-8 or Hailo-8L NPU for AI acceleration
  - **Wiring/Connectors**: 
    - JST connectors for sensors
    - XT60/XT90 connectors for power
    - Waterproof M12 connectors for external connections

#### Control Panel Server Setup

- **Minimum System Requirements**:
  - **SBC Option**: Raspberry Pi 4 (4GB) or ODROID-N2+
  - **Mini PC Option**: Intel NUC (Celeron or better)
  - **Server Option**: Any Ubuntu-compatible server with 2GB+ RAM
  - **Storage**: 32GB SSD/eMMC minimum, 120GB SSD recommended
  - **Network**: Ethernet preferred, WiFi 5 (802.11ac) or better
  - Recommended Models:
    - Budget: Raspberry Pi 4 8GB
    - Mid-range: ODROID-N2+ or Intel NUC7CJYH
    - Premium: Intel NUC10i3FNK or Dell Optiplex 3060 Micro

- **Network Requirements**:
  - **Router**: Any modern router with VPN capability
  - **For Remote Access**: Port forwarding capability or VPN
  - **Optional**: TP-Link Omada or Ubiquiti UniFi access points for better coverage
  - **For Large Areas**: Outdoor wireless AP with directional antenna

### Optional Components with Recommended Models

- **Docking Station**:
  - **Charging Contacts**: 2× Gold-plated Spring Contacts (200mA minimum)
  - **Guidance System**:
    - Visual: ArUco Markers (600×600mm, weatherproof print)
    - Alternative: 4× IR Beacons (TSOP38238 IR Receiver based)
  - **Weather Protection**: IP65 Rated Enclosure with Rain Cover
  - **Power Supply**: 24V 5A Power Supply with IP67 Rating

- **Boundary Markers**:
  - **Visual Markers**: 
    - Weatherproof ArUco Markers (15x15cm printed on Coroplast)
    - QR Code Markers (laminated, 10×10cm minimum)
  - **RFID Markers**: 
    - 125KHz RFID Tags with ID-12LA RFID Reader
  - **Boundary Wire (optional)**:
    - 2.5mm² Copper Wire, PVC Insulated
    - Underground Installation: Use 1.5mm² for ease of installation

- **Advanced Add-ons**:
  - **Lawn Quality Sensors**:
    - Soil Moisture: Capacitive Soil Moisture Sensor v1.2
    - Soil Temperature: DS18B20 Waterproof Temperature Sensor
  - **RTK Base Station**:
    - DIY: Raspberry Pi Zero 2 W with NEO-M8P GNSS
    - Commercial: Emlid Reach RS+ or Reach RS2
  - **Additional Cameras**:
    - Forward-looking: Raspberry Pi Camera Module 3
    - Downward-facing: OV5647 Camera Module (low-cost)
  - **Weather Station Integration**:
    - DIY: BME280 Temperature/Humidity/Pressure Sensor
    - Commercial: Ambient Weather WS-2902C Integration

## Detailed Installation Guide

This guide provides step-by-step instructions for installing the Robot Mower Advanced system on both the Raspberry Pi (mower controller) and Ubuntu Server (control panel).

### Raspberry Pi Installation (Mower Controller)

#### 1. Hardware Assembly

1. **Prepare the Enclosure**:
   - Install the Raspberry Pi in an IP65-rated enclosure
   - Mount the cooling fan and ensure proper ventilation
   - Install the emergency stop button in an easily accessible location

2. **Connect Sensors**:
   - **Ultrasonic Sensors** (HC-SR04):
     - Connect VCC to 5V power supply
     - Connect GND to ground
     - Connect TRIG pins to GPIO pins as configured in `config/local_config.yaml`
     - Connect ECHO pins through a voltage divider (two resistors: 1kΩ and 2kΩ) to GPIO pins

   - **IMU Sensor** (MPU6050):
     - Connect VCC to 3.3V power supply
     - Connect GND to ground
     - Connect SCL to GPIO3 (I2C1 SCL)
     - Connect SDA to GPIO2 (I2C1 SDA)

   - **Wheel Encoders**:
     - Connect VCC to 5V power supply
     - Connect GND to ground
     - Connect signal pins to GPIO pins as configured

   - **Camera Module**:
     - Connect the camera to the CSI connector on the Raspberry Pi
     - Secure the ribbon cable with the connector latch

3. **Motor Controller Setup**:
   - **L298N Motor Driver** (for both drive motors):
     - Connect motor power supply (VCC) to battery power (12-24V)
     - Connect logic power supply to 5V (or use 5V from driver if available)
     - Connect IN1, IN2, IN3, IN4 to GPIO pins as configured
     - Connect ENA and ENB to PWM-capable GPIO pins
     - Connect motor outputs to DC motors

   - **Cutting Motor Control**:
     - For high-power motors, use a separate BTS7960 or MOSFET controller
     - Connect to appropriately rated GPIO pins through optocouplers for isolation

4. **Power Management**:
   - Install DC-DC converter to regulate battery voltage to 5V for Raspberry Pi
   - Connect INA219 current sensor in-line with power supply to monitor consumption
   - Wire emergency stop button to interrupt motor controllers

#### 2. Software Installation

1. **Prepare the Raspberry Pi**:
   ```bash
   # Flash Raspberry Pi OS Bullseye (64-bit recommended) to SD card using Raspberry Pi Imager
   # Boot and perform initial setup
   # Enable required interfaces:
   sudo raspi-config
   # Select: Interface Options > Camera > Enable
   # Select: Interface Options > I2C > Enable
   # Select: Interface Options > SPI > Enable
   
   # Update the system
   sudo apt update && sudo apt upgrade -y
   
   # Install required packages
   sudo apt install -y git python3-pip python3-venv
   ```

2. **Clone the Repository**:
   ```bash
   git clone https://github.com/khryptorgraphics/robot-mower-advanced.git
   cd robot-mower-advanced
   ```

3. **Run the Installation Script**:
   ```bash
   # Make installation script executable
   chmod +x scripts/install_raspberry_pi.sh
   
   # Run the installation script
   sudo ./scripts/install_raspberry_pi.sh
   ```

4. **Post-Installation Configuration**:
   - Edit the configuration file to match your hardware setup:
   ```bash
   # Edit configuration with nano editor
   nano config/local_config.yaml
   
   # Adjust GPIO pin assignments to match your wiring
   # Configure motor parameters
   # Set up sensor calibration values
   ```

   - Test the sensor connections:
   ```bash
   # Navigate to the project directory
   cd ~/robot-mower-advanced
   
   # Run the sensor test utility
   python3 utils/test_sensors.py
   ```

5. **Start the System**:
   ```bash
   # Start the system manually for testing
   cd ~/robot-mower-advanced
   ./start.sh
   
   # Or, enable the systemd service for automatic startup
   sudo systemctl enable robot-mower.service
   sudo systemctl start robot-mower.service
   ```

### Ubuntu Server Installation (Control Panel)

#### 1. Hardware Setup

1. **Prepare the Server**:
   - Install Ubuntu Server 20.04 LTS or newer on your chosen hardware
   - Ensure the system has a static IP address on your local network
   - Open port 7799 in the firewall for the web interface

2. **Network Configuration**:
   ```bash
   # Update the system
   sudo apt update && sudo apt upgrade -y
   
   # Install required packages
   sudo apt install -y git python3-pip python3-venv nginx
   
   # Configure firewall
   sudo ufw allow 7799/tcp
   sudo ufw enable
   ```

#### 2. Software Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/khryptorgraphics/robot-mower-advanced.git
   cd robot-mower-advanced
   ```

2. **Run the Installation Script**:
   ```bash
   # Make installation script executable
   chmod +x scripts/install_ubuntu_server.sh
   
   # Run the installation script
   sudo ./scripts/install_ubuntu_server.sh
   ```

3. **Configuration**:
   - Edit the configuration file to set up the control panel:
   ```bash
   # Edit configuration
   nano config/local_config.yaml
   
   # Set the mower's IP address
   # Configure authentication
   # Adjust web interface settings
   ```

4. **Start the Control Panel**:
   ```bash
   # Start the service
   sudo systemctl start robot-mower-web.service
   
   # Enable automatic startup
   sudo systemctl enable robot-mower-web.service
   ```

5. **Access the Web Interface**:
   - Open a web browser and navigate to `http://[server-ip]:7799`
   - Log in with the default credentials:
     - Username: `admin`
     - Password: `admin`
   - Change the default password immediately after first login

### Connecting the Systems

1. **Network Configuration**:
   - Ensure both systems are on the same local network
   - Configure the Raspberry Pi to connect to your WiFi network:
   ```bash
   sudo raspi-config
   # Select: System Options > Wireless LAN
   # Enter your WiFi SSID and password
   ```

2. **Security Setup** (optional but recommended):
   - Generate and install SSL certificates for secure communication:
   ```bash
   # On the Ubuntu Server
   cd ~/robot-mower-advanced
   sudo ./scripts/generate_ssl_cert.sh
   ```

3. **Testing Communication**:
   - From the Ubuntu server, test connectivity to the Raspberry Pi:
   ```bash
   ping [raspberry-pi-ip]
   ```
   
   - Test the API connection:
   ```bash
   curl http://[raspberry-pi-ip]:5000/api/status
   ```

4. **Final Configuration**:
   - In the web interface, navigate to Settings > Connection
   - Enter the Raspberry Pi's IP address
   - Click "Test Connection" to verify
   - Save the configuration

### Troubleshooting Hardware Issues

#### Common GPIO Issues

- **Ultrasonic Sensors Not Responding**:
  - Verify 5V power is reaching the sensors (measure with multimeter)
  - Check GPIO pin assignments in configuration
  - Ensure voltage dividers are installed for ECHO pins
  - Test each sensor individually using the test script

- **Motor Control Problems**:
  - Verify PWM frequency configuration (1-5kHz recommended)
  - Check for sufficient power supply current capacity
  - Measure motor controller logic inputs with multimeter
  - Isolate motor power from Raspberry Pi power to prevent interference

- **IMU Sensor Issues**:
  - Run `sudo i2cdetect -y 1` to verify I2C connection
  - Check I2C address configuration (0x68 is default for MPU6050)
  - Keep I2C cables short and away from power cables
  - Run calibration utility: `python3 utils/calibrate_imu.py`

- **Camera Problems**:
  - Verify camera enabled in `raspi-config`
  - Check ribbon cable connection (blue side faces away from ethernet port)
  - Test camera with: `libcamera-still -o test.jpg`
  - Ensure adequate lighting for vision functions

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
