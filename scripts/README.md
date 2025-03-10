# Robot Mower Advanced Installation Scripts

This directory contains installation scripts for the Robot Mower Advanced system.

## Ubuntu Server Installation

The `install_ubuntu_server.sh` script sets up the Robot Mower Advanced Control Panel on an Ubuntu server. It configures the system to serve the control panel on port 7799.

### Modular Design

The installation process has been split into multiple modular scripts for better maintainability and ease of customization:

- **Main Script**: `install_ubuntu_server.sh` - Coordinates the entire installation process
- **Module Scripts** (in `ubuntu_install_modules/` directory):
  - `core_install.sh` - Core installation functions (system updates, dependencies, directories)
  - `web_app_template.sh` - Flask web application template creation
  - `html_templates.sh` - HTML templates for the web interface
  - `config_manager.sh` - Configuration manager and default configuration
  - `service_setup.sh` - System service setup, Nginx configuration, and requirements

### Installation Process

The script performs the following steps:
1. Checks if running as root
2. Sources all module scripts
3. Updates the system and installs dependencies
4. Creates installation directories
5. Clones the repository and sets up files
6. Creates web app and templates
7. Creates configuration manager and configuration files
8. Sets up Python environment
9. Creates launcher and sets up services
10. Performs installation checks and prints a summary

### Usage

```bash
sudo ./install_ubuntu_server.sh
```

### Requirements

- Ubuntu Server (18.04 or newer)
- Root privileges
- Internet connection (for package installation)

### Default Installation

- **Installation Directory**: `/opt/robot-mower-control-panel`
- **Web Interface Port**: 7799
- **Service Name**: `robot-mower-control-panel`
- **Default Admin Username**: admin
- **Default Admin Password**: admin123

## Raspberry Pi Installation

The `install_raspberry_pi.sh` script installs the Robot Mower Advanced software on a Raspberry Pi.

### Usage

```bash
sudo ./install_raspberry_pi.sh
```

## Customization

To customize the installation, you can modify the appropriate module script:

- For web application changes: Edit `ubuntu_install_modules/web_app_template.sh`
- For HTML template changes: Edit `ubuntu_install_modules/html_templates.sh`
- For configuration changes: Edit `ubuntu_install_modules/config_manager.sh`
- For service setup changes: Edit `ubuntu_install_modules/service_setup.sh`
- For core installation changes: Edit `ubuntu_install_modules/core_install.sh`

You can also modify the main script to change installation directories, ports, or other global settings.
