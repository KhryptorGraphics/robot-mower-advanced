# Robot Mower Advanced - Setup Guide

This document provides detailed instructions for setting up the Robot Mower Advanced software and hardware.

## Table of Contents

1. [Hardware Setup](#hardware-setup)
2. [Software Installation](#software-installation)
3. [Configuration](#configuration)
4. [Initial Testing](#initial-testing)
5. [Web Interface Setup](#web-interface-setup)
6. [Troubleshooting](#troubleshooting)

## Hardware Setup

### Recommended Hardware

- **Computing Platform**: 
  - Raspberry Pi 4B+ (2GB+ RAM recommended)
  - microSD card (16GB+ recommended)
  - Power supply (5V, 3A)

- **Mower Hardware**:
  - Chassis/frame that can house all components
  - Two drive motors with encoders (12V DC recommended)
  - Blade motor (high torque, 12-24V)
  - Motor controllers/drivers
  - 12V-24V battery (LiPo or SLA)
  - Charging station/dock

- **Sensors**:
  - 3x HC-SR04 ultrasonic distance sensors (minimum)
  - MPU6050 IMU sensor
  - GPS module (NEO-6M or similar)
  - Raspberry Pi Camera V2 or similar
  - Rain sensor (optional)
  - Battery voltage monitor
  - Status LEDs

- **Additional Components**:
  - DC-DC converter (to power Raspberry Pi from main battery)
  - Connectors, wires, and fasteners
  - Enclosure for electronics (weather-resistant)

### Wiring Diagram

Below is a simplified wiring diagram for connecting the components to a Raspberry Pi:

```
Raspberry Pi        Components
-----------        ----------
5V              -> DC-DC Converter Output, HC-SR04 VCC, MPU6050 VCC
GND             -> Common ground for all components
GPIO 12, 13     -> PWM inputs for motor drivers (left and right)
GPIO 16, 20     -> Direction inputs for motor drivers
GPIO 18         -> PWM input for blade motor controller
GPIO 22         -> Direction input for blade motor controller
GPIO 23, 24     -> Encoder A/B for left motor
GPIO 25, 26     -> Encoder A/B for right motor
GPIO 5, 6       -> Front HC-SR04 (Trigger, Echo)
GPIO 17, 27     -> Left HC-SR04 (Trigger, Echo)
GPIO 22, 23     -> Right HC-SR04 (Trigger, Echo)
GPIO 4          -> Battery voltage monitor (via voltage divider)
GPIO 16         -> Rain sensor
I2C (SDA/SCL)   -> MPU6050 IMU
Serial (TX/RX)  -> GPS module
Camera port     -> Raspberry Pi Camera
```

### Hardware Assembly Steps

1. **Prepare the chassis**:
   - Mount the drive motors and blade motor
   - Install wheels and cutting blade (with proper safety guards)
   - Create mounting points for electronics and sensors

2. **Set up the electronics enclosure**:
   - Mount the Raspberry Pi in a weather-resistant enclosure
   - Install motor controllers/drivers
   - Install the DC-DC converter
   - Ensure adequate cooling/ventilation

3. **Mount and connect sensors**:
   - Position ultrasonic sensors at the front and sides
   - Mount the camera for forward vision
   - Install the IMU in a position with minimal vibration
   - Mount the GPS module with clear sky visibility
   - Position the rain sensor where it can detect precipitation

4. **Connect the power system**:
   - Install the main battery
   - Connect the DC-DC converter to provide 5V to the Raspberry Pi
   - Wire the motor controllers to the main battery
   - Set up battery monitoring

5. **Connect the wiring**:
   - Follow the wiring diagram to connect all components
   - Use proper connectors and wire gauge for motor connections
   - Keep signal wires away from power wires to reduce interference
   - Label all connections for future maintenance

## Software Installation

### Operating System Setup

1. **Install Raspberry Pi OS**:
   ```bash
   # Download Raspberry Pi Imager tool from the official website
   # Use it to flash Raspberry Pi OS (64-bit recommended) to your microSD card
   # Boot the Raspberry Pi with the new microSD card
   ```

2. **Initial OS Configuration**:
   ```bash
   sudo raspi-config
   # Enable: I2C, Serial, Camera, SSH, expand filesystem
   # Set locale and timezone
   # Reboot after configuration
   ```

3. **Update the system**:
   ```bash
   sudo apt update
   sudo apt upgrade -y
   ```

4. **Install required packages**:
   ```bash
   sudo apt install -y python3-pip python3-numpy python3-opencv python3-smbus python3-yaml git i2c-tools
   ```

### Robot Mower Software Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/khryptorgraphics/robot-mower-advanced.git
   cd robot-mower-advanced
   ```

2. **Install Python dependencies**:
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Create required directories**:
   ```bash
   mkdir -p data logs data/lawn_images data/lawn_reports data/detections
   ```

4. **Create local configuration**:
   ```bash
   cp config/default_config.yaml config/local_config.yaml
   ```

## Configuration

### Basic Configuration

Edit the local configuration file to match your hardware setup:

```bash
nano config/local_config.yaml
```

Key settings to adjust:

1. **System settings**:
   ```yaml
   system:
     app_name: "RobotMower"
     data_dir: "data"
     log_level: "INFO"
     log_file: "logs/robot_mower.log"
     simulation_mode: false  # Set to true for testing without hardware
   ```

2. **Hardware settings**:
   - Update pin assignments to match your wiring
   - Configure motor parameters based on your motors
   - Configure sensor parameters

3. **Location settings**:
   ```yaml
   location:
     latitude: 12.3456  # Replace with your actual coordinates
     longitude: 78.9012
     city: "Your City"
     country: "Your Country"
   ```

### Advanced Configuration

For more advanced features, you may need to:

1. **Configure the weather API** (for weather-based scheduling):
   ```yaml
   weather:
     api:
       enabled: true
       key: "your-api-key"  # Get from OpenWeatherMap
       url: "https://api.openweathermap.org/data/2.5/forecast"
       provider: "openweathermap"
   ```

2. **Configure theft protection notifications**:
   ```yaml
   security:
     theft_protection:
       email_notifications: true
       email_recipient: "your-email@example.com"
       email_sender: "mower-alerts@example.com"
       email_smtp_server: "smtp.example.com"
       email_smtp_port: 587
       email_smtp_username: "username"
       email_smtp_password: "password"
   ```

## Initial Testing

### Simulation Mode Testing

To verify the software functions correctly before using physical hardware:

```bash
python3 main.py --sim
```

This will run the system in simulation mode, using mock hardware interfaces.

### Hardware Component Testing

Run individual component tests to verify hardware connections:

```bash
# Motor test
python3 tests/test_motors.py

# Sensor test
python3 tests/test_sensors.py

# GPS test
python3 tests/test_gps.py

# Camera test
python3 tests/test_camera.py
```

### Full System Test

Once individual components are verified, run a full system test:

```bash
python3 main.py --test
```

This will run a system self-diagnostic that tests each component and reports any issues.

## Web Interface Setup

### Basic Web Setup

The web interface runs automatically when the system starts. By default, it's accessible at:

```
http://<raspberry-pi-ip>:8080
```

Default credentials:
- Username: `admin`
- Password: `admin123` (change this immediately!)

### Secure HTTPS Setup

For a secure connection, enable HTTPS:

1. **Generate self-signed certificates**:
   ```bash
   cd robot-mower-advanced
   mkdir -p certs
   openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes
   ```

2. **Update configuration**:
   ```yaml
   web:
     enable_https: true
     cert_file: "certs/cert.pem"
     key_file: "certs/key.pem"
   ```

### Starting the System

To start the system as a background service:

1. **Create a systemd service**:
   ```bash
   sudo nano /etc/systemd/system/robot-mower.service
   ```

2. **Add the following content**:
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

3. **Enable and start the service**:
   ```bash
   sudo systemctl enable robot-mower.service
   sudo systemctl start robot-mower.service
   ```

4. **Check service status**:
   ```bash
   sudo systemctl status robot-mower.service
   ```

## Troubleshooting

### Common Issues

1. **Hardware Not Detected**
   - Check physical connections
   - Verify GPIO pin numbers in configuration
   - Run `i2cdetect -y 1` to check I2C devices
   - Check permissions: `sudo usermod -a -G dialout,i2c,gpio pi`

2. **Motors Not Moving**
   - Check motor driver connections
   - Verify power supply is adequate
   - Test motors directly with `python3 tests/test_motors.py`

3. **GPS No Fix**
   - Ensure the GPS has a clear view of the sky
   - Allow up to 5 minutes for first fix
   - Check serial connection: `ls -l /dev/ttyAMA0`

4. **Web Interface Not Accessible**
   - Check network connection
   - Verify the service is running
   - Check firewall settings: `sudo ufw status`

### Logs and Debugging

To access detailed logs:

```bash
tail -f logs/robot_mower.log
```

For more verbose logging, edit the configuration:

```yaml
system:
  log_level: "DEBUG"
```

### Support and Community

For additional help and community support:

- Visit the [GitHub Issues](https://github.com/khryptorgraphics/robot-mower-advanced/issues) page
- Join the [Robot Mower Discord community](https://discord.gg/robot-mower-advanced)
- Check the [Wiki](https://github.com/khryptorgraphics/robot-mower-advanced/wiki) for additional documentation
