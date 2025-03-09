# Robot Mower Advanced

An advanced control system for autonomous robotic lawn mowers with edge detection, obstacle avoidance, weather-based scheduling, and more.

## Overview

Robot Mower Advanced is a complete software solution for controlling autonomous lawn mowing robots. It provides a robust foundation of core functionality with advanced features like weather-based scheduling, lawn health analysis, and anti-theft protection. The system is designed for use with Raspberry Pi hardware but can be adapted to other platforms.

## Features

- **Multi-Zone Management**: Define and manage multiple lawn zones with different mowing patterns
- **Edge Detection and Following**: Precisely mow along the edges of the lawn for a clean finish
- **Advanced Navigation**: Multiple mowing patterns including parallel, spiral, zigzag and perimeter-first
- **Object Detection**: Identify and avoid obstacles, with special attention to safety-critical objects
- **Lawn Health Analysis**: Monitor lawn health and get recommendations for improvements
- **Grass Growth Prediction**: Smart scheduling based on predicted grass growth rates
- **Weather-Based Scheduling**: Automatically adjust mowing schedule based on weather forecasts
- **Maintenance Tracking**: Track blade replacement, cleaning, and other maintenance tasks
- **Anti-Theft Protection**: GPS tracking and geofencing with alerts for unauthorized movement
- **Web Interface**: Control and monitor the mower from any browser
- **Robust Architecture**: Modular design with dependency injection and hardware abstraction

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
├── main.py               # Main entry point
├── requirements.txt      # Python dependencies
├── SETUP.md              # Detailed setup instructions
└── README.md             # This file
```

## Hardware Recommendations

### Recommended Components

#### Computing Platform
- **Primary Controller**: Raspberry Pi 4B+ with 4GB RAM (8GB for optimal performance)
- **Storage**: 32GB+ Class 10 microSD card or USB SSD for improved reliability
- **Power Management**: UPS HAT for safe shutdown during low power
- **Connectivity**: Raspberry Pi with built-in Wi-Fi or external Wi-Fi adapter with antenna

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

## Deployment & Installation

### Initial System Setup

1. **Operating System Installation**:
   ```bash
   # Download Raspberry Pi Imager from https://www.raspberrypi.com/software/
   # Flash Raspberry Pi OS (64-bit) to your microSD card
   # Enable SSH during setup for headless operation
   ```

2. **Basic System Configuration**:
   ```bash
   # Update system packages
   sudo apt update && sudo apt upgrade -y
   
   # Install required system dependencies
   sudo apt install -y python3-pip python3-dev python3-numpy python3-opencv \
   python3-smbus python3-yaml git i2c-tools libopenjp2-7 libatlas-base-dev \
   libjpeg-dev libwebp-dev libtiff5 screen
   
   # Enable required interfaces
   sudo raspi-config nonint do_i2c 0
   sudo raspi-config nonint do_camera 0
   sudo raspi-config nonint do_serial 0
   
   # Reboot to apply changes
   sudo reboot
   ```

3. **Network Configuration**:
   ```bash
   # Set up static IP (recommended for reliable access)
   sudo nano /etc/dhcpcd.conf
   
   # Add the following (adjust for your network):
   interface wlan0
   static ip_address=192.168.1.100/24
   static routers=192.168.1.1
   static domain_name_servers=192.168.1.1
   
   # For Wi-Fi connection
   sudo nano /etc/wpa_supplicant/wpa_supplicant.conf
   
   # Add:
   network={
       ssid="YourWiFiName"
       psk="YourWiFiPassword"
       priority=1
   }
   ```

### Software Installation

1. **Clone and Configure Repository**:
   ```bash
   # Clone the repository
   git clone https://github.com/KhryptorGraphics/robot-mower-advanced.git
   cd robot-mower-advanced

   # Install Python dependencies
   pip3 install -r requirements.txt

   # Create required directories
   mkdir -p data logs data/lawn_images data/lawn_reports data/detections
   
   # Create local configuration
   cp config/default_config.yaml config/local_config.yaml
   
   # Customize configuration (critical step)
   nano config/local_config.yaml
   ```

2. **Hardware Interface Setup**:
   
   Edit your config/local_config.yaml to match your hardware:
   
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
     
     sensors:
       # Configure each sensor with appropriate pins
       ultrasonic:
         - name: "front"
           trigger_pin: 5
           echo_pin: 6
         - name: "left"
           trigger_pin: 17
           echo_pin: 27
         - name: "right"
           trigger_pin: 22
           echo_pin: 23
       
       # Additional sensor configurations...
   ```

3. **Integration Testing**:
   ```bash
   # Run system in simulation mode first
   python3 main.py --sim
   
   # Test individual components
   python3 tests/test_motors.py
   python3 tests/test_sensors.py
   
   # Run with hardware but without motion
   python3 main.py --test
   ```

### Production Deployment

1. **System Service Setup**:
   ```bash
   # Create systemd service for automatic startup
   sudo nano /etc/systemd/system/robot-mower.service
   ```
   
   Add the following content:
   ```
   [Unit]
   Description=Robot Mower Advanced Service
   After=network.target
   
   [Service]
   User=pi
   WorkingDirectory=/home/pi/robot-mower-advanced
   ExecStart=/usr/bin/python3 main.py
   Restart=on-failure
   RestartSec=5
   
   [Install]
   WantedBy=multi-user.target
   ```
   
   Enable and start the service:
   ```bash
   sudo systemctl enable robot-mower.service
   sudo systemctl start robot-mower.service
   sudo systemctl status robot-mower.service
   ```

2. **Web Interface Setup**:
   
   Basic web access (http):
   ```
   http://<raspberry-pi-ip>:8080
   ```
   
   Secure HTTPS setup:
   ```bash
   # Generate self-signed certificates
   mkdir -p certs
   openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes
   
   # Update configuration for HTTPS
   nano config/local_config.yaml
   ```
   
   Add to configuration:
   ```yaml
   web:
     enable_https: true
     cert_file: "certs/cert.pem"
     key_file: "certs/key.pem"
     port: 8443  # Standard HTTPS port is also an option
   ```

3. **Remote Monitoring Setup**:
   ```bash
   # Configure email alerts
   nano config/local_config.yaml
   ```
   
   Add notification settings:
   ```yaml
   security:
     theft_protection:
       email_notifications: true
       email_recipient: "your-email@example.com"
       email_sender: "mower-alerts@yourdomain.com"
       email_smtp_server: "smtp.yourdomain.com"
       email_smtp_port: 587
       email_smtp_username: "username"
       email_smtp_password: "password"
   ```

4. **Data Backup Configuration**:
   ```bash
   # Set up automated backups of configuration and data
   nano backup.sh
   ```
   
   Add backup script:
   ```bash
   #!/bin/bash
   BACKUP_DIR="/home/pi/backups"
   TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
   
   mkdir -p $BACKUP_DIR
   
   # Backup config and critical data
   tar -czvf $BACKUP_DIR/robot_mower_backup_$TIMESTAMP.tar.gz \
     config/ \
     data/lawn_reports/ \
     data/zone_definitions/ \
     data/maintenance_logs/ \
     logs/
   
   # Rotate backups (keep last 10)
   ls -t $BACKUP_DIR/robot_mower_backup_*.tar.gz | tail -n +11 | xargs -r rm
   ```
   
   Make executable and set up as cron job:
   ```bash
   chmod +x backup.sh
   crontab -e
   ```
   
   Add to crontab:
   ```
   0 2 * * * /home/pi/robot-mower-advanced/backup.sh
   ```

### Field Calibration and Operation

1. **IMU Calibration**:
   ```bash
   # Run the IMU calibration tool
   python3 tools/calibrate_imu.py
   
   # Follow on-screen instructions to place the robot on level surface
   # and rotate it through different positions
   ```

2. **Lawn Zone Definition**:
   ```bash
   # Set up lawn boundaries using the web interface
   # Navigate to http://<raspberry-pi-ip>:8080/zones
   
   # Or use the command-line tool
   python3 tools/define_zones.py
   ```

3. **Perimeter Calibration**:
   ```bash
   # For best edge following results, perform a perimeter learning run
   python3 tools/learn_perimeter.py
   ```

4. **Test Operation**:
   ```bash
   # Run a short test mowing cycle under supervision
   python3 main.py --test-run
   ```

5. **Full Operation**:
   ```bash
   # Start normal operation
   sudo systemctl start robot-mower.service
   
   # Monitor logs during initial operation
   tail -f logs/robot_mower.log
   ```

### Troubleshooting and Maintenance

1. **Common Issues and Solutions**:
   - **Hardware Not Detected**:
     ```bash
     # Check I2C devices
     i2cdetect -y 1
     
     # Check USB devices
     lsusb
     
     # Check GPIO permissions
     sudo usermod -a -G gpio,i2c,dialout pi
     ```
   
   - **GPS No Fix**:
     ```bash
     # Check GPS data stream
     cat /dev/ttyAMA0
     # or
     python3 tools/test_gps.py
     ```
   
   - **Connectivity Issues**:
     ```bash
     # Test network
     ping -c 4 google.com
     
     # Check network interfaces
     ifconfig
     
     # Restart networking
     sudo systemctl restart networking
     ```

2. **Regular Maintenance Tasks**:
   
   Update software:
   ```bash
   cd robot-mower-advanced
   git pull
   pip3 install -r requirements.txt
   sudo systemctl restart robot-mower.service
   ```
   
   Database maintenance:
   ```bash
   # Clean up old logs
   python3 tools/cleanup_logs.py --older-than 30
   
   # Optimize database
   python3 tools/optimize_db.py
   ```
   
   Hardware maintenance:
   ```bash
   # Run diagnostics
   python3 tools/hardware_diagnostics.py
   
   # Check battery health
   python3 tools/battery_health.py
   ```

3. **Remote Access Setup**:
   ```bash
   # Enable SSH tunneling for remote access:
   ssh -R 8022:localhost:22 your-server.com
   
   # For persistent connection, install autossh:
   sudo apt install autossh
   
   # Create persistent tunnel
   autossh -M 0 -o "ServerAliveInterval 30" -o "ServerAliveCountMax 3" -R 8022:localhost:22 user@your-server.com
   ```

4. **Long-term Storage Preparation**:
   ```bash
   # Run the winterization procedure
   python3 tools/prepare_storage.py
   
   # System shutdown
   sudo shutdown now
   
   # Remove battery or install battery maintainer for winter storage
   ```

## Advanced Integration Options

### Weather Integration
- Create an account at [OpenWeatherMap](https://openweathermap.org/api)
- Add your API key to config/local_config.yaml:
  ```yaml
  weather:
    api:
      enabled: true
      key: "your-api-key"
      provider: "openweathermap"
  ```

### Solar Charging
- Add solar panel configuration:
  ```yaml
  power:
    solar:
      enabled: true
      panel_voltage: 18
      charge_controller: "pwm"  # or "mppt"
  ```

### RTK GPS
- For centimeter-level accuracy:
  ```yaml
  sensors:
    gps:
      type: "rtk"
      base_station: "ntrip"
      ntrip_server: "your-rtk-caster.com:2101"
      ntrip_user: "username"
      ntrip_password: "password"
      ntrip_mountpoint: "MOUNTPOINT"
  ```

### Camera Vision
- Enable advanced vision:
  ```yaml
  perception:
    camera:
      enabled: true
      resolution: [640, 480]
      framerate: 30
      object_detection: true
      model_type: "tiny-yolo"
  ```

## Usage

### Basic Operation

Start the robot mower with default settings:

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

### Web Interface

Access the web interface at:

```
http://<raspberry-pi-ip>:8080
```

Default credentials:
- Username: `admin`
- Password: `admin123` (change this immediately!)

### Mobile App Control

A companion mobile app is available for Android and iOS:

1. Download "Robot Mower Controller" from Google Play or App Store
2. Connect to the same network as your Raspberry Pi
3. Enter your robot's IP address and web interface credentials
4. Enjoy remote control and monitoring from your mobile device

## Configuration

The system is configured using YAML files in the `config` directory. See `config/default_config.yaml` for a complete example with documentation.

Key configuration sections:

- `system` - System-wide settings
- `hardware` - Hardware component configuration
- `navigation` - Navigation and path planning settings
- `perception` - Object detection and lawn analysis
- `mowing` - Basic mowing parameters
- `security` - Anti-theft settings
- `web` - Web interface configuration
- `scheduling` - Scheduling and timing settings
- `maintenance` - Maintenance intervals and notifications
- `weather` - Weather API configuration
- `location` - Location settings

### Configuration Examples

#### Mowing Patterns Configuration

```yaml
navigation:
  patterns:
    default: "parallel"  # Options: parallel, spiral, zigzag, perimeter_first
    parallel:
      angle: 45  # degrees, relative to yard orientation
      spacing: 0.8  # multiplier of cutting width
    spiral:
      start_radius: 0.5  # meters
      spacing: 0.8  # meters
    zigzag:
      line_length: 5.0  # meters
      spacing: 0.8  # multiplier of cutting width
    perimeter_first:
      enabled: true
      passes: 2  # Number of perimeter passes before starting pattern
  
  obstacle_avoidance:
    strategy: "dynamic"  # Options: simple, dynamic, learning
    min_distance: 0.3  # meters
    slowdown_distance: 0.8  # meters
    learning_enabled: true
```

#### Weather Adaptation Settings

```yaml
scheduling:
  weather_adaptation:
    enabled: true
    rain_threshold: 60  # Probability percentage to skip mowing
    temperature_min: 5  # Celsius, below this temperature mowing is skipped
    temperature_max: 35  # Celsius, above this temperature mowing is limited
  
  grass_growth:
    modeling_enabled: true
    target_height: 50  # mm
    cut_height: 30  # mm
    growth_rate_base: 3.0  # mm per day in ideal conditions
```

#### Advanced Security Configuration

```yaml
security:
  theft_protection:
    enabled: true
    geofence_radius: 50  # meters
    alert_methods:
      sms: true
      email: true
      siren: true
    accelerometer_sensitivity: 0.8  # 0.0-1.0
  
  access_control:
    allow_remote: true
    require_2fa: true
    session_timeout: 1800  # seconds
    failed_login_delay: 5  # seconds
    max_failed_attempts: 5
```

## Development and Extension

The system follows a modular design with clear interfaces between components. Each hardware component has an abstract interface that can be implemented for different hardware.

### Key Architecture Concepts

- **Dependency Injection**: Components request their dependencies through constructor parameters
- **Hardware Abstraction**: Hardware interfaces define contracts that implementations must follow
- **Service Locator**: The Application class maintains a service container for system components
- **Event System**: Communication between modules occurs through an event bus
- **Strategy Pattern**: Different algorithms can be swapped at runtime

### Creating Custom Hardware Support

1. Identify the appropriate interface in `hardware/interfaces.py`
2. Create a new implementation in the appropriate directory
3. Register your implementation in `hardware/factory.py`

Example for a custom motor controller:

```python
# hardware/motor_controller.py
from hardware.interfaces import MotorControllerInterface

class MyCustomMotorController(MotorControllerInterface):
    def __init__(self, config):
        self.config = config
        # Initialize your hardware here
    
    def set_motor_speed(self, motor, speed):
        # Implementation for your specific hardware
        pass
    
    def stop_all(self):
        # Implementation for your specific hardware
        pass

# Then in hardware/factory.py, add:
elif motor_controller_type == "my_custom":
    return MyCustomMotorController(config)
```

### API and Integration Points

The system provides several integration points for extensions:

- **REST API**: `/api/v1` endpoints for programmatic control
- **WebSocket Events**: Real-time updates via `/ws` endpoint
- **Plugin System**: Load custom plugins from the `plugins/` directory
- **Custom Sensors**: Add new sensor types by implementing sensor interfaces
- **Custom UI Components**: Extend the web interface with new components

## Commercial Considerations

### Production Deployment Recommendations

For commercial or high-reliability deployments:

1. **Hardware Redundancy**:
   - Dual IMU sensors
   - Multiple distance sensors with overlapping fields of view
   - Redundant motor encoders

2. **Reliability Features**:
   - UPS (Uninterruptible Power Supply) for safe shutdown
   - Watchdog timer implementation
   - Error recovery strategies
   - Automatic diagnostic routines

3. **Security Hardening**:
   - Change all default credentials
   - Implement certificate-based authentication
   - Regular security updates
   - Network segregation (dedicated IoT network)

4. **Production Scaling**:
   - Centralized fleet management
   - Remote monitoring and analytics
   - Automated update distribution
   - Telemetry collection and analysis

### Support Resources

- **Documentation**: Complete system documentation at [docs.robot-mower-advanced.org](https://docs.robot-mower-advanced.org)
- **Community Forum**: Join discussions at [forum.robot-mower-advanced.org](https://forum.robot-mower-advanced.org)
- **Commercial Support**: Available for enterprise deployments at [support@robot-mower-advanced.org](mailto:support@robot-mower-advanced.org)
- **Training**: Online courses available for system integrators

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
