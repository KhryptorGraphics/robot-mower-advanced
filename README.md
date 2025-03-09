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

## Hardware Requirements

- **Computing Platform**: Raspberry Pi 4B+ (or newer) recommended
- **Motors**: DC motors with encoders or brushless motors with ESC
- **Sensors**:
  - Ultrasonic distance sensors for obstacle detection
  - IMU for tilt and motion detection
  - GPS for positioning
  - Camera for object detection (optional)
  - Rain sensor (optional)
  - Power monitoring
- **Connectivity**: Wi-Fi for remote control

## Installation

See [SETUP.md](SETUP.md) for detailed installation and setup instructions.

Quick start:

```bash
# Clone the repository
git clone https://github.com/khryptorgraphics/robot-mower-advanced.git
cd robot-mower-advanced

# Install dependencies
pip install -r requirements.txt

# Create a local configuration
cp config/default_config.yaml config/local_config.yaml

# Edit the configuration to match your hardware
nano config/local_config.yaml

# Run in simulation mode (no hardware required)
python main.py --sim
```

## Usage

### Basic Operation

Start the robot mower with default settings:

```bash
python main.py
```

### Command Line Options

- `--config PATH` - Specify a configuration file path
- `--log-level LEVEL` - Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `--data-dir PATH` - Override data directory path
- `--dev` - Run in development mode (more verbose output)
- `--no-web` - Disable web interface
- `--sim` - Run in simulation mode (no physical hardware)
- `--test` - Run system test and exit

### Web Interface

Access the web interface at:

```
http://<raspberry-pi-ip>:8080
```

Default credentials:
- Username: `admin`
- Password: `admin123` (change this immediately!)

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

## Development

The system follows a modular design with clear interfaces between components. Each hardware component has an abstract interface that can be implemented for different hardware.

Key architecture concepts:

- **Dependency Injection**: Components request their dependencies through constructor parameters
- **Hardware Abstraction**: Hardware interfaces define contracts that implementations must follow
- **Service Locator**: The Application class maintains a service container for system components

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
