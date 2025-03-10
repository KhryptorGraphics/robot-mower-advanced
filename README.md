# Robot Mower Advanced

An advanced robotic lawn mower platform with SLAM mapping, computer vision, path planning, and remote control capabilities.

## Features

- **SLAM Mapping**: Creates and maintains a map of your lawn
- **Computer Vision**: Detects obstacles, boundaries, and lawn health using cameras
- **Advanced Path Planning**: Efficient mowing patterns based on lawn shape and obstacles
- **Remote Control**: Web interface for monitoring and control
- **Smart Scheduling**: Weather-aware mowing schedule
- **Safety Features**: Comprehensive obstacle detection and avoidance
- **Extensible Framework**: Modular design for easy customization

## Hardware Requirements

### Raspberry Pi Setup

- Raspberry Pi 4 (4GB+ RAM recommended)
- Motor controller board (L298N or similar)
- Ultrasonic sensors (HC-SR04 or similar)
- IMU sensor (MPU6050 or similar)
- Camera module
- Optional: GPS module
- Optional: Hailo NPU for accelerated computer vision

### Control Panel Server Setup (Ubuntu)

- Any Ubuntu-compatible system (18.04 or newer)
- Minimum 2GB RAM
- 10GB+ storage space
- Network connection to the Raspberry Pi

## Software Architecture

The software consists of several key components:

1. **Perception System**: SLAM mapping, obstacle detection, and lawn analysis
2. **Navigation System**: Path planning and obstacle avoidance
3. **Control System**: Motor control, safety monitoring, and power management
4. **Web Interface**: Remote monitoring and control dashboard
5. **Configuration System**: Customizable settings for different lawn types

## Installation

### On Raspberry Pi (Main Robot Controller)

```bash
git clone https://github.com/khryptorgraphics/robot-mower-advanced.git
cd robot-mower-advanced
sudo ./scripts/install_raspberry_pi.sh
```

The Raspberry Pi installation script is modular and includes:

- Core system setup
- Hardware interface configuration
- Optional Hailo NPU integration
- SLAM and path planning configuration
- Systemd service setup

### On Ubuntu Server (Control Panel)

```bash
git clone https://github.com/khryptorgraphics/robot-mower-advanced.git
cd robot-mower-advanced
sudo ./scripts/install_ubuntu_server.sh
```

The Ubuntu Server installation script is modular and includes:

- Core installation components 
- Web application setup
- Configuration management
- Nginx and systemd service configuration

After installation, the control panel will be available at: `http://[server-ip]:7799`

## Configuration

The system can be configured by editing the files in the `config` directory:

- `default_config.yaml`: Default configuration (do not edit)
- `local_config.yaml`: Your custom configuration (overrides defaults)

## Development

To contribute to the project, please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
