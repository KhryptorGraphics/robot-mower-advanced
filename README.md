*** UNDER DEVELOPMENT
anyone that wants to participate totes can

# Robot Mower Advanced

An advanced robotic lawn mower platform with SLAM mapping, computer vision, path planning, and remote control capabilities. This open-source project provides a comprehensive solution for building and operating an autonomous lawn mower with sophisticated features typically found in high-end commercial systems.

![Robot Mower Advanced](https://placehold.co/600x400/forest/white?text=Robot+Mower+Advanced)

## Table of Contents

- [Features](#features)
- [System Architecture](#system-architecture)
- [Hardware Requirements](#hardware-requirements)
- [Beginner's Guide: Getting Started](#beginners-guide-getting-started)
- [Installation](#installation)
  - [Raspberry Pi Installation](#raspberry-pi-installation)
  - [Ubuntu Server Installation](#ubuntu-server-installation)
- [Understanding Configuration Files](#understanding-configuration-files)
  - [Core Settings](#core-settings)
  - [SLAM Configuration](#slam-configuration)
  - [Path Planning Configuration](#path-planning-configuration)
  - [Hardware Configuration](#hardware-configuration)
  - [Web Interface Configuration](#web-interface-configuration)
- [Usage](#usage)
- [Software Architecture](#software-architecture)
- [Troubleshooting Guide for Beginners](#troubleshooting-guide-for-beginners)
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

The Robot Mower Advanced system consists of two main components that work together:

1. **Raspberry Pi Controller**: This is the "brain" installed on the mower itself
   - It handles real-time control, reads all sensors, and makes decisions
   - Runs the core SLAM (mapping) and navigation algorithms
   - Controls the motors and interfaces with all hardware
   - Can operate independently when Wi-Fi is not available

2. **Control Panel Server**: This runs on a separate computer in your house
   - Provides a web interface you can access from any device
   - Stores data like maps, usage statistics, and settings
   - Handles scheduling and planning of mowing sessions
   - Acts as the central point for you to monitor and control the mower

These components talk to each other over your home Wi-Fi network. Even if the Wi-Fi connection is lost, your mower will continue operating safely.

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

For detailed hardware requirements, component selection, and specific model recommendations, see our [Detailed Hardware List](hardware_guide.md#complete-bill-of-materials).

For step-by-step hardware assembly instructions, wiring diagrams, and component installation guides, refer to the [Comprehensive Hardware Guide](hardware_guide.md).

## Beginner's Guide: Getting Started

If you're new to Linux or Raspberry Pi projects, here's a simple breakdown of what you'll need to do:

1. **Purchase the Required Hardware**: Use our [Hardware Guide](hardware_guide.md) to buy all the necessary components.

2. **Assemble the Hardware**: Follow the [Hardware Assembly Instructions](hardware_guide.md#mechanical-construction) to build the mower.

3. **Set Up the Raspberry Pi**: You'll install a special operating system and our software on it.

4. **Set Up the Control Panel**: You'll install our software on a computer in your home that will act as the control center.

5. **Configure and Test**: You'll adjust settings and test each component before the first use.

This may seem complex, but we'll walk you through each step in detail below!

## Installation

### Raspberry Pi Installation

This section explains how to install the software on your Raspberry Pi (the mower's "brain").

#### Step 1: Prepare Your Raspberry Pi

First, we need to set up the Raspberry Pi with its operating system and enable all the features we'll need.

```bash
# These instructions assume you've already:
# 1. Downloaded and installed Raspberry Pi OS (64-bit recommended) to an SD card
# 2. Inserted the SD card into your Raspberry Pi and powered it on
# 3. Completed the initial setup (set password, connected to Wi-Fi, etc.)

# Open a terminal and update your system (this downloads the latest software)
sudo apt update && sudo apt upgrade -y
# What this does: 'apt' is the package manager, 'update' refreshes the list of available packages,
# 'upgrade' installs newer versions, and '-y' automatically answers "yes" to prompts

# Now enable the special interfaces we need for sensors and camera
sudo raspi-config
# This opens a configuration tool. Using the arrow keys and Enter:
# Navigate to "Interface Options"
# Enable: Camera, I2C, SPI
# Select "Finish" and reboot if prompted
```

#### Step 2: Download Our Software

Next, we'll download the software from GitHub to your Raspberry Pi.

```bash
# Install Git (the tool that downloads code repositories)
sudo apt install -y git

# Download (clone) our software repository
git clone https://github.com/khryptorgraphics/robot-mower-advanced.git
# This creates a new folder called 'robot-mower-advanced' with all our code

# Enter the project directory
cd robot-mower-advanced
```

#### Step 3: Run the Installation Script

We've created an automated script that will install everything for you.

```bash
# Make the installation script executable
chmod +x scripts/install_raspberry_pi.sh
# This changes the file permission to allow execution

# Run the installation script
sudo ./scripts/install_raspberry_pi.sh
# The script will ask you questions during installation - follow the prompts
# It will install all necessary software packages and set up the system
```

#### Step 4: What the Installation Script Does

Our installation script performs several important tasks for you:

1. **Core System Installation** (`core_install.sh`): 
   - Installs Python and required system packages
   - Sets up the project environment
   - Creates necessary directories

2. **Dependencies Installation** (`dependencies.sh`):
   - Installs libraries for hardware interfaces
   - Sets up Python packages for sensors, motors, etc.
   - Configures system permissions

3. **Hailo Setup** (`hailo_setup.sh`, optional):
   - Installs Hailo NPU drivers if you have this hardware
   - Configures the vision acceleration system

4. **SLAM and Path Planning Setup** (`slam_path_planning.sh`):
   - Installs mapping and navigation libraries
   - Configures the localization system

5. **Service Setup** (`service_setup.sh`):
   - Creates system services for automatic startup
   - Sets up proper permissions
   - Configures the system to start the mower software at boot

#### Step 5: Configure Your System

After installation, you'll need to customize settings for your specific hardware.

```bash
# Edit the configuration file to match your hardware
nano config/local_config.yaml
# This opens a text editor with the configuration file

# Inside this file, adjust settings like:
# - GPIO pin numbers (to match your wiring)
# - Motor parameters (to match your motors)
# - Sensor calibration values

# Press Ctrl+O to save, then Enter, then Ctrl+X to exit
```

#### Step 6: Test Your Setup

Before putting your mower on the lawn, test that all components work correctly.

```bash
# Test sensors and motors
cd ~/robot-mower-advanced
python3 utils/test_sensors.py
# Follow the on-screen instructions to test each component
```

#### Step 7: Start the System

Finally, you can start the system either manually or set it to run automatically at boot.

```bash
# Start manually for testing
cd ~/robot-mower-advanced
./start.sh

# OR enable automatic startup
sudo systemctl enable robot-mower.service
sudo systemctl start robot-mower.service
# This registers the service to start automatically when the Pi boots
```

### Ubuntu Server Installation

This section explains how to install the Control Panel software on a separate computer running Ubuntu.

#### Step 1: Prepare Your Ubuntu Server

```bash
# Update your system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y git python3-pip python3-venv nginx
# What this installs:
# - git: to download our code
# - python3-pip and python3-venv: for Python packages
# - nginx: web server for the control panel

# Configure the firewall to allow web access
sudo ufw allow 7799/tcp
sudo ufw enable
# This opens port 7799 which the web interface will use
```

#### Step 2: Download Our Software

```bash
# Download our software
git clone https://github.com/khryptorgraphics/robot-mower-advanced.git
cd robot-mower-advanced
```

#### Step 3: Run the Installation Script

```bash
# Make the script executable
chmod +x scripts/install_ubuntu_server.sh

# Run the installation script
sudo ./scripts/install_ubuntu_server.sh
# Follow the prompts to complete installation
```

#### Step 4: What the Installation Script Does

Our Ubuntu server installation script includes several modules:

1. **Core Installation** (`core_install.sh`):
   - Sets up Python environment
   - Installs required packages
   - Creates necessary directories

2. **Web App Setup** (`web_app_template.sh`):
   - Installs Flask web framework
   - Sets up the back-end API system
   - Configures web application structure

3. **HTML Templates** (`html_templates.sh`):
   - Installs web interface files
   - Sets up the dashboard, control panels, etc.

4. **Config Manager** (`config_manager.sh`):
   - Creates configuration files
   - Sets up default settings

5. **Service Setup** (`service_setup.sh`):
   - Configures Nginx web server
   - Creates system service for automatic startup
   - Sets proper permissions

#### Step 5: Configure the Control Panel

After installation, you'll need to customize the Control Panel settings.

```bash
# Edit the configuration file
nano config/local_config.yaml

# Adjust settings like:
# - The mower's IP address (so the control panel can find it)
# - Authentication settings
# - Web interface preferences
```

#### Step 6: Start the Control Panel

```bash
# Start the service
sudo systemctl start robot-mower-web.service

# Set it to start automatically at boot
sudo systemctl enable robot-mower-web.service
```

#### Step 7: Access the Web Interface

1. Open a web browser on any device on your network
2. Navigate to `http://[your-server-ip]:7799`
3. Log in with the default credentials:
   - Username: `admin`
   - Password: `admin`
4. **Important**: Change the default password immediately!

### Connecting the Systems

Once both the Raspberry Pi and Ubuntu Server are set up, you need to connect them.

1. **Make sure both are on the same network**:
   - The Raspberry Pi and Ubuntu Server should be connected to the same home network
   - Preferably use a wired ethernet connection for the server, and Wi-Fi for the Pi

2. **Configure the connection in the web interface**:
   - Log in to the web interface
   - Go to Settings > Connection
   - Enter the Raspberry Pi's IP address
   - Test the connection
   - Save settings

3. **Test the full system**:
   - On the web dashboard, you should see the mower status
   - Try sending a simple command (like "Stop") to verify communication

## Understanding Configuration Files

All settings are stored in YAML format files in the `config/` directory. YAML is a human-readable format that uses indentation to structure data.

### Core Settings

The main configuration file is `config/local_config.yaml`. Here's what each section means:

#### System Configuration

```yaml
system:
  data_dir: "/home/pi/robot-mower-advanced/data"  # Where data is stored
  log_level: "info"  # How detailed the logs are: debug, info, warning, error
  log_to_file: true  # Whether to save logs to a file
  log_file: "logs/robot_mower.log"  # Where log files are saved
  enable_remote_monitoring: true  # Allow the control panel to monitor
  enable_telemetry: true  # Collect usage statistics
```

**Plain English Explanation**:
- `data_dir`: This is where the program saves all its data, like maps and settings
- `log_level`: Controls how detailed the log messages are:
  - `debug`: Extremely detailed (for troubleshooting)
  - `info`: Normal operation details
  - `warning`: Only warnings and errors
  - `error`: Only errors
- `log_to_file` and `log_file`: Controls whether log messages are saved to a file and where
- `enable_remote_monitoring`: Allows the control panel to see what's happening
- `enable_telemetry`: Collects data about how the system is running

#### Mower Hardware Configuration

```yaml
mower:
  name: "LawnMaster 5000"  # Your mower's nickname
  cutting_width_mm: 320  # Width of the cutting blade in millimeters
  max_speed_mps: 0.5  # Maximum speed in meters per second
  min_turning_radius_m: 0.5  # How tight it can turn, in meters
  wheel_diameter_mm: 200  # Wheel diameter in millimeters
  encoder_pulses_per_revolution: 20  # How many pulses per wheel rotation
  battery_capacity_mah: 5000  # Battery capacity in milliamp-hours
  battery_voltage: 24.0  # Battery voltage
  low_battery_threshold: 20  # Low battery warning at 20% remaining
  critical_battery_threshold: 10  # Critical battery warning at 10%
```

**Plain English Explanation**:
- `name`: Just a nickname for your mower
- `cutting_width_mm`: How wide a path your mower cuts in one pass
- `max_speed_mps`: Maximum speed - 0.5 means half a meter per second
- `min_turning_radius_m`: How sharp the mower can turn - smaller is better
- `wheel_diameter_mm`: The size of your wheels - needed for distance calculations
- `encoder_pulses_per_revolution`: How many signals your wheel sensors send per rotation
- Battery settings: Information about your battery for proper charge management
- Threshold settings: When to trigger warnings about battery level

### SLAM Configuration

SLAM stands for Simultaneous Localization And Mapping - it's how the mower creates and uses a map.

```yaml
slam:
  enabled: true  # Turn mapping on/off
  map_resolution: 0.05  # How detailed the map is (meters per pixel)
  map_size: 100.0  # Maximum map size in meters
  add_pose_interval: 1.0  # How often to record position (seconds)
  mapping_interval: 0.5  # How often to update the map (seconds)
  localization_interval: 0.1  # How often to calculate position (seconds)
  optimization_interval: 5.0  # How often to improve the map (seconds)
  gps_weight: 0.7  # How much to trust GPS data (0-1)
  imu_weight: 0.8  # How much to trust IMU data (0-1)
  odometry_weight: 0.5  # How much to trust wheel encoder data (0-1)
  visual_odometry_scale: 0.01  # Camera movement scaling factor
  map_save_interval: 60  # How often to save the map (seconds)
```

**Plain English Explanation**:
- `enabled`: Turns the mapping system on or off
- `map_resolution`: How detailed the map is - smaller numbers mean more detail
- `map_size`: The maximum size of your map in meters
- Interval settings: How often different operations happen
- Weight settings: How much the system trusts each sensor type:
  - Higher numbers (closer to 1) mean more trust
  - Lower numbers (closer to 0) mean less trust
- `map_save_interval`: How often the map is saved to storage

### Path Planning Configuration

This section controls how the mower moves around your lawn.

```yaml
navigation:
  path_planning:
    enabled: true  # Turn path planning on/off
    safety_margin_m: 0.2  # Keep this distance from obstacles (meters)
    edge_detection_enabled: true  # Detect and follow lawn edges
    edge_follow_distance_m: 0.1  # How close to follow edges (meters)
  obstacle_avoidance:
    enabled: true  # Turn obstacle avoidance on/off
    detection_range_m: 3.0  # Look this far ahead for obstacles (meters)
    stop_distance_m: 0.5  # Stop this far from obstacles (meters)
  pattern: "adaptive"  # Mowing pattern type
  overlap_percent: 15.0  # How much to overlap each pass (percent)
  cutting_direction_degrees: 0.0  # Direction to mow (degrees)
  speed_normal: 0.4  # Normal moving speed (meters per second)
  speed_edge: 0.3  # Speed when following edges
  speed_docking: 0.2  # Speed when returning to dock
```

**Plain English Explanation**:
- Path planning controls how the mower decides where to go
  - `safety_margin_m`: How far to stay away from all obstacles
  - `edge_detection_enabled`: Whether to find and follow the edges of your lawn
  - `edge_follow_distance_m`: How close to follow the lawn edges
- Obstacle avoidance controls how the mower avoids running into things
  - `detection_range_m`: How far ahead it looks for obstacles
  - `stop_distance_m`: How far from an obstacle it will stop
- `pattern`: The mowing pattern to use:
  - `parallel`: Straight back-and-forth lines (like a farmer's field)
  - `spiral`: Spiral from outside to inside or inside to outside
  - `zigzag`: Similar to parallel but with diagonal movements
  - `perimeter_first`: Mows around the edges first, then fills in
  - `adaptive`: Automatically chooses the best pattern for your lawn shape
- `overlap_percent`: How much each pass overlaps the previous one to avoid missed spots
- Speed settings control how fast the mower moves in different situations

### Hardware Configuration

This section maps physical hardware connections, especially GPIO pins on the Raspberry Pi.

```yaml
motors:
  left_motor:
    forward_pin: 17  # GPIO pin for forward direction
    backward_pin: 18  # GPIO pin for backward direction
    pwm_pin: 12  # GPIO pin for speed control
    pwm_frequency: 1000  # PWM frequency in Hz
  right_motor:
    forward_pin: 22
    backward_pin: 23
    pwm_pin: 13
    pwm_frequency: 1000
  cutting_motor:
    enable_pin: 24
    pwm_pin: 25
    pwm_frequency: 1000

sensors:
  ultrasonic:
    - name: "front"  # Front obstacle sensor
      trigger_pin: 5  # GPIO pin for trigger
      echo_pin: 6  # GPIO pin for echo
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
    i2c_bus: 1  # I2C bus for the IMU sensor
    i2c_address: 0x68  # I2C address of the IMU
  gps:
    enabled: true
    serial_port: "/dev/ttyACM0"  # Serial port for GPS
    baud_rate: 9600  # Communication speed
  camera:
    enabled: true
    width: 640  # Camera resolution width
    height: 480  # Camera resolution height
    fps: 30  # Frames per second
    index: 0  # Camera index (if multiple cameras)
```

**Plain English Explanation**:
- Motor settings define which GPIO pins control the motors
  - `forward_pin`: The pin that makes the motor go forward
  - `backward_pin`: The pin that makes the motor go backward
  - `pwm_pin`: The pin that controls speed
  - `pwm_frequency`: How fast the speed control signal pulses
- Sensor settings define how the sensors are connected
  - Ultrasonic sensors have two pins: trigger (sends signal) and echo (receives signal)
  - IMU (motion sensor) uses I2C communication protocol
  - GPS uses a serial port connection
  - Camera settings control resolution and frame rate

**Important Note**: The GPIO pin numbers must exactly match your wiring. If these are incorrect, the motors and sensors won't work!

### Web Interface Configuration

This section configures the web-based control panel.

```yaml
web:
  enabled: true  # Turn web interface on/off
  host: "0.0.0.0"  # Listen on all network interfaces
  port: 7799  # Network port to use
  debug: false  # Enable debug mode
  enable_ssl: false  # Use HTTPS instead of HTTP
  ssl_cert: ""  # Path to SSL certificate
  ssl_key: ""  # Path to SSL key
  session_lifetime: 86400  # Session duration in seconds (24 hours)
  enable_camera_stream: true  # Show camera feed
  camera_stream_quality: 75  # JPEG quality (percent)
  camera_stream_fps: 10  # Frames per second for camera stream
```

**Plain English Explanation**:
- `enabled`: Turns the web interface on or off
- `host`: Which network interface to use (0.0.0.0 means all interfaces)
- `port`: The network port number (you'll use this in your web browser)
- `debug`: Shows detailed debugging information (only for development)
- SSL settings: For secure HTTPS connections (recommended for internet access)
- `session_lifetime`: How long until you need to log in again
- Camera stream settings: Controls the live camera feed quality

## Troubleshooting Guide for Beginners

### Common Problems and Solutions

#### Problem: Cannot Access Web Interface

**Check if the web service is running**:
```bash
# This shows the status of the web service
sudo systemctl status robot-mower-web.service
```

If it shows "active (running)" in green, the service is running correctly.

If it shows any errors or "inactive", try:
```bash
# Restart the web service
sudo systemctl restart robot-mower-web.service
```

**Check if you can reach the server**:
```bash
# Replace [server-ip] with your server's IP address
ping [server-ip]
```

You should see replies. If not, there might be a network issue.

**Check firewall settings**:
```bash
# Check if port 7799 is allowed
sudo ufw status
```

If port 7799 is not in the list, allow it:
```bash
sudo ufw allow 7799/tcp
```

#### Problem: Motors Don't Move

1. **Check power**:
   - Verify battery voltage with a multimeter
   - Check if the power switch is on
   - Look for blown fuses

2. **Check motor controller connections**:
   - Verify that the GPIO pins match your configuration
   - Verify that the motor wires are securely connected

3. **Test motor controllers directly**:
   ```bash
   # Run the motor test utility
   cd ~/robot-mower-advanced
   python3 utils/test_motors.py
   ```

#### Problem: Sensors Not Working

**For Ultrasonic Sensors**:
1. Check voltage at the sensor (should be 5V)
2. Verify GPIO pin connections (trigger and echo)
3. Check for obstacles in front of the sensor during testing

**For IMU Sensor**:
```bash
# Check if the I2C device is detected
sudo i2cdetect -y 1
```
You should see a device at the address specified in your config (usually 0x68).

**For Camera**:
```bash
# Test if camera is working
libcamera-still -o test.jpg
```
This should capture an image. If it fails, check camera connection or enable the camera interface in `raspi-config`.

### Using Log Files to Diagnose Problems

Logs can help you find the cause of problems:

```bash
# View the main system log
sudo journalctl -u robot-mower.service -n 100
# This shows the last 100 messages from the mower service

# View the web interface log
sudo journalctl -u robot-mower-web.service -n 100
```

Look for lines marked as `ERROR` or `WARNING` which can indicate what's wrong.

### Getting More Help

If you're still stuck:

1. Check the [Hardware Guide](hardware_guide.md) for detailed wiring diagrams
2. Run the diagnostic tools:
   ```bash
   cd ~/robot-mower-advanced
   python3 utils/hardware_test.py
   ```
3. Share your log files and problem description in our GitHub issues section

---

For more advanced troubleshooting and detailed system information, see the [Advanced Troubleshooting](#troubleshooting) section below.

## Usage

The Robot Mower Advanced system is designed to be user-friendly through its web interface. Here's how to use it:

### Web Interface Features

Once you've set up the system and both components are communicating, you can control everything through the web interface:

#### Main Dashboard

The main dashboard gives you an overview of your mower's status:

- Current battery level and charging status
- Mowing progress and statistics (area covered, runtime)
- Live map showing the mower's position and path
- Quick controls (Start, Stop, Dock)
- Alert notifications
- Weather conditions (if configured)

#### Zone Management

Zones let you define different areas of your lawn:

1. Click "Add New Zone"
2. Draw the zone on the map
3. Set properties like name, mowing pattern, and schedule
4. Save the zone

You can create multiple zones (e.g., front yard, back yard) with different settings for each.

#### Scheduling

To set up automatic mowing:

1. Go to the Scheduling page
2. Create a new schedule with:
   - Days and times to mow
   - Which zones to include
   - Weather conditions to avoid
3. Enable/disable schedules as needed

The mower will automatically follow the schedule and return to its dock when finished.

#### Manual Control

For direct control:

1. Go to the Manual Control page
2. Use the on-screen controls to drive
3. Adjust speed using the slider
4. Turn the cutting blade on/off
5. Monitor sensor readings in real-time

This is useful for testing or for moving the mower to a specific location.

## Maintenance

Regular maintenance will keep your mower running reliably:

### Software Maintenance

```bash
# Update the software (on both Raspberry Pi and Server)
cd ~/robot-mower-advanced
git pull
sudo ./scripts/update.sh
```

### Hardware Maintenance

1. **Blades**:
   - Check for damage every 20-30 hours
   - Replace when dull or damaged

2. **Sensors**:
   - Clean ultrasonic sensors with compressed air
   - Wipe camera lens with a microfiber cloth
   - Remove debris from wheel encoders

3. **Battery**:
   - Check connections for corrosion
   - Perform a full discharge/charge cycle monthly
   - Replace batteries every 2-3 years

4. **Mechanical**:
   - Check for loose screws and bolts
   - Inspect wheels and drive system
   - Lubricate moving parts as needed

## Contributing

We welcome contributions to the project! To contribute:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Note**: This is an open-source project. While we strive to make it reliable and safe, use it at your own risk and always maintain proper supervision of autonomous lawn mowing equipment.
