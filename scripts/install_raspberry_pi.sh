#!/bin/bash

# Robot Mower Advanced - Raspberry Pi Installation Script
#
# This script installs all dependencies and sets up the Robot Mower
# Advanced software on a Raspberry Pi. It configures the system for
# automatic startup and creates all required directories.
#

set -e  # Exit immediately if a command exits with non-zero status
INSTALL_DIR="/home/pi/robot-mower-advanced"
LOG_FILE="/tmp/robot_mower_install.log"

# Function to log messages
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Function to check if running as root
check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        log "This script must be run as root. Please use sudo."
        exit 1
    fi
}

# Function to update package lists
update_system() {
    log "Updating package lists..."
    apt-get update >> "$LOG_FILE" 2>&1
    log "Upgrading installed packages..."
    apt-get upgrade -y >> "$LOG_FILE" 2>&1
}

# Function to install required packages
install_dependencies() {
    log "Installing required packages..."
    apt-get install -y python3-pip python3-dev python3-numpy python3-opencv \
    python3-smbus python3-yaml git i2c-tools libopenjp2-7 libatlas-base-dev \
    libjpeg-dev libwebp-dev libtiff5 screen cmake build-essential libusb-1.0-0-dev \
    pkg-config libswscale-dev libavcodec-dev libavformat-dev libgstreamer1.0-dev \
    libv4l-dev >> "$LOG_FILE" 2>&1

    log "Installing Python packages..."
    python3 -m pip install --upgrade pip >> "$LOG_FILE" 2>&1

    # Create a virtual environment (optional but recommended)
    log "Setting up Python virtual environment..."
    apt-get install -y python3-venv >> "$LOG_FILE" 2>&1

    if [ -d "${INSTALL_DIR}" ]; then
        cd "${INSTALL_DIR}"

        # Create and activate virtual environment if it doesn't exist
        if [ ! -d "venv" ]; then
            python3 -m venv venv >> "$LOG_FILE" 2>&1
        fi

        # Install Python dependencies from requirements.txt
        log "Installing Python dependencies from requirements.txt..."
        . venv/bin/activate
        pip install -r requirements.txt >> "$LOG_FILE" 2>&1
        deactivate
    else
        log "Installation directory not found. Clone the repository first."
    fi
}

# Function to install Hailo NPU SDK
install_hailo_sdk() {
    log "Setting up Hailo NPU HAT..."
    
    # Check if Hailo is already installed
    if python3 -c "import hailo" &>/dev/null; then
        log "Hailo SDK already installed, skipping."
        return 0
    fi
    
    log "Installing Hailo SDK dependencies..."
    apt-get install -y libssl-dev libusb-1.0-0-dev libudev-dev >> "$LOG_FILE" 2>&1
    
    # Create directory for Hailo software
    HAILO_DIR="/opt/hailo"
    mkdir -p "${HAILO_DIR}"
    mkdir -p "${HAILO_DIR}/models"
    
    # Download Hailo SDK
    log "Downloading Hailo SDK..."
    cd /tmp
    
    # Download HailoRT package (adjust URL as needed for the latest version)
    wget -q https://hailo.ai/developer/hailort/download/hailort_latest_arm.deb -O hailort.deb >> "$LOG_FILE" 2>&1
    
    # Install HailoRT
    log "Installing Hailo Runtime..."
    apt-get install -y ./hailort.deb >> "$LOG_FILE" 2>&1
    
    # Install Hailo Python API
    log "Installing Hailo Python API..."
    if [ -d "${INSTALL_DIR}" ]; then
        cd "${INSTALL_DIR}"
        . venv/bin/activate
        pip install hailo-ai >> "$LOG_FILE" 2>&1
        deactivate
    fi
    
    # Setup udev rules for Hailo
    log "Setting up udev rules for Hailo..."
    if [ ! -f "/etc/udev/rules.d/99-hailo.rules" ]; then
        echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="03e7", MODE="0666"' > /etc/udev/rules.d/99-hailo.rules
        udevadm control --reload-rules && udevadm trigger
    fi
    
    # Download a sample model for testing
    log "Downloading YOLOv5 model for Hailo..."
    mkdir -p "${HAILO_DIR}/models"
    wget -q https://hailo.ai/developer/models/yolov5/yolov5m_wo_spp_60p.hef -O "${HAILO_DIR}/models/yolov5m.hef" >> "$LOG_FILE" 2>&1
    
    log "Hailo NPU HAT setup completed"
}

# Function to configure Hailo NPU
configure_hailo() {
    log "Configuring Hailo NPU settings..."
    
    if [ -f "${INSTALL_DIR}/config/local_config.yaml" ]; then
        # Check if hailo section already exists
        if ! grep -q "^hailo:" "${INSTALL_DIR}/config/local_config.yaml"; then
            # Add Hailo configuration to local config
            cat >> "${INSTALL_DIR}/config/local_config.yaml" << EOF

# Hailo NPU configuration
hailo:
  enabled: true
  model_path: "/opt/hailo/models/yolov5m.hef"
  confidence_threshold: 0.5
  input_shape: [640, 640]
  class_filter: ["person", "bicycle", "car", "motorcycle", "dog", "cat", "potted plant"]

# Camera configuration
camera:
  enabled: true
  width: 640
  height: 480
  fps: 30
  index: 0

# Object detection configuration
object_detection:
  enabled: true
  safety_critical_zone: 1.5  # meters
  obstacle_zone: 3.0  # meters
EOF
            log "Added Hailo NPU configuration to local_config.yaml"
        fi
    fi
}

# Function to enable required interfaces
enable_interfaces() {
    log "Enabling required interfaces (I2C, SPI, Camera)..."

    # Enable I2C
    if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
        echo "dtparam=i2c_arm=on" >> /boot/config.txt
    fi

    # Enable SPI
    if ! grep -q "^dtparam=spi=on" /boot/config.txt; then
        echo "dtparam=spi=on" >> /boot/config.txt
    fi

    # Enable Camera
    if ! grep -q "^start_x=1" /boot/config.txt; then
        echo "start_x=1" >> /boot/config.txt
        echo "gpu_mem=128" >> /boot/config.txt
    fi

    # Enable Serial (but disable login shell)
    if ! grep -q "^enable_uart=1" /boot/config.txt; then
        echo "enable_uart=1" >> /boot/config.txt
    fi
    systemctl disable serial-getty@ttyAMA0.service >> "$LOG_FILE" 2>&1

    # Load I2C and SPI modules at boot
    if ! grep -q "i2c-dev" /etc/modules; then
        echo "i2c-dev" >> /etc/modules
    fi
    if ! grep -q "spi-bcm2835" /etc/modules; then
        echo "spi-bcm2835" >> /etc/modules
    fi

    log "Interfaces enabled. A reboot will be needed for changes to take effect."
}

# Function to add user to required groups
add_user_to_groups() {
    USER="pi"
    log "Adding user ${USER} to required groups..."
    usermod -a -G dialout,i2c,spi,gpio,input,video "$USER" >> "$LOG_FILE" 2>&1
    log "User added to required groups."
}

# Function to clone the repository
clone_repository() {
    if [ -d "${INSTALL_DIR}" ]; then
        log "Repository directory already exists. Updating..."
        cd "${INSTALL_DIR}"
        git pull >> "$LOG_FILE" 2>&1
    else
        log "Cloning Robot Mower Advanced repository..."
        git clone https://github.com/khryptorgraphics/robot-mower-advanced.git "${INSTALL_DIR}" >> "$LOG_FILE" 2>&1
    fi

    # Set correct permissions
    chown -R pi:pi "${INSTALL_DIR}" >> "$LOG_FILE" 2>&1
    log "Repository cloned/updated successfully."
}

# Function to create required directories
create_directories() {
    log "Creating required directories..."

    # Define directories
    DIRS=(
        "${INSTALL_DIR}/data"
        "${INSTALL_DIR}/logs"
        "${INSTALL_DIR}/config"
        "${INSTALL_DIR}/data/lawn_images"
        "${INSTALL_DIR}/data/lawn_reports"
        "${INSTALL_DIR}/data/detections"
        "${INSTALL_DIR}/data/zone_definitions"
        "${INSTALL_DIR}/data/maintenance_logs"
    )

    # Create each directory
    for DIR in "${DIRS[@]}"; do
        mkdir -p "$DIR" >> "$LOG_FILE" 2>&1
        chown -R pi:pi "$DIR" >> "$LOG_FILE" 2>&1
    done

    log "Directories created successfully."
}

# Function to create a service for auto-start
create_service() {
    log "Creating systemd service for automatic startup..."

    # Create service file
    cat > /etc/systemd/system/robot-mower.service << EOF
[Unit]
Description=Robot Mower Advanced Service
After=network.target

[Service]
User=pi
WorkingDirectory=${INSTALL_DIR}
ExecStart=${INSTALL_DIR}/venv/bin/python3 ${INSTALL_DIR}/main.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd enable and start service
    systemctl daemon-reload >> "$LOG_FILE" 2>&1
    systemctl enable robot-mower.service >> "$LOG_FILE" 2>&1

    log "Service created and enabled successfully."
}

# Function to create default configuration
create_default_config() {
    log "Setting up configuration..."

    # Create local config if it doesn't exist
    if [ -f "${INSTALL_DIR}/config/default_config.yaml" ] && [ ! -f "${INSTALL_DIR}/config/local_config.yaml" ]; then
        cp "${INSTALL_DIR}/config/default_config.yaml" "${INSTALL_DIR}/config/local_config.yaml"
        chown pi:pi "${INSTALL_DIR}/config/local_config.yaml"
        log "Created local configuration file."
    fi
}

# Function to setup the web interface
setup_web_interface() {
    log "Setting up web interface..."
    
    # Create a web server configuration if needed
    if [ -d "${INSTALL_DIR}/web" ]; then
        log "Web interface files found, configuring..."
        
        # Create a systemd service for the web server
        cat > /etc/systemd/system/robot-mower-web.service << EOF
[Unit]
Description=Robot Mower Advanced Web Interface
After=network.target

[Service]
User=pi
WorkingDirectory=${INSTALL_DIR}
ExecStart=${INSTALL_DIR}/venv/bin/python3 ${INSTALL_DIR}/web/server.py
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

        # Reload systemd, enable and start service
        systemctl daemon-reload >> "$LOG_FILE" 2>&1
        systemctl enable robot-mower-web.service >> "$LOG_FILE" 2>&1
        
        log "Web interface service created and enabled successfully."
    else
        log "Web interface directory not found. Skipping web server setup."
    fi
}

# Function to set up network (optional)
setup_network() {
    log "Setting up network..."

    # Prompt for network configuration
    read -p "Would you like to set up a static IP address? (y/n): " setup_static_ip

    if [[ "$setup_static_ip" =~ ^[Yy]$ ]]; then
        read -p "Enter static IP address (e.g. 192.168.1.100): " static_ip
        read -p "Enter network mask (e.g. 24): " network_mask
        read -p "Enter gateway (e.g. 192.168.1.1): " gateway
        read -p "Enter DNS server (e.g. 8.8.8.8): " dns_server

        # Create dhcpcd.conf entry
        cat >> /etc/dhcpcd.conf << EOF

# Static IP configuration for Robot Mower
interface wlan0
static ip_address=${static_ip}/${network_mask}
static routers=${gateway}
static domain_name_servers=${dns_server}
EOF

        log "Static IP configured. Will take effect after reboot."
    fi
}

# Function to set up HTTPS (optional)
setup_https() {
    log "Setting up HTTPS for web interface..."

    if [ -d "${INSTALL_DIR}" ]; then
        # Create certs directory
        mkdir -p "${INSTALL_DIR}/certs"

        # Generate self-signed certificates
        log "Generating self-signed certificates..."
        openssl req -x509 -newkey rsa:4096 -nodes -out "${INSTALL_DIR}/certs/cert.pem" -keyout "${INSTALL_DIR}/certs/key.pem" -days 365 -subj "/CN=Robot Mower Advanced" >> "$LOG_FILE" 2>&1

        # Update permissions
        chown -R pi:pi "${INSTALL_DIR}/certs"
        chmod 600 "${INSTALL_DIR}/certs/key.pem"

        # Update local configuration to use HTTPS
        if [ -f "${INSTALL_DIR}/config/local_config.yaml" ]; then
            # Update the web section in the config file
            sed -i '/^web:/,/^[a-z]/{s/enable_ssl: false/enable_ssl: true/}' "${INSTALL_DIR}/config/local_config.yaml"
            sed -i '/^web:/,/^[a-z]/{s/ssl_cert: ""/ssl_cert: "certs\/cert.pem"/}' "${INSTALL_DIR}/config/local_config.yaml"
            sed -i '/^web:/,/^[a-z]/{s/ssl_key: ""/ssl_key: "certs\/key.pem"/}' "${INSTALL_DIR}/config/local_config.yaml"

            log "HTTPS configuration updated in local_config.yaml"
        fi
    else
        log "Installation directory not found. Skipping HTTPS setup."
    fi
}

# Function to clean up and finalize
finalize() {
    log "Finalizing installation..."

    # Ensure correct permissions
    if [ -d "${INSTALL_DIR}" ]; then
        chown -R pi:pi "${INSTALL_DIR}"
        
        # Make main script executable
        chmod +x "${INSTALL_DIR}/main.py"
    fi

    log "Installation completed successfully!"
    log "The system will now reboot to apply all changes."
    log "After reboot the Robot Mower service will start automatically."
    log "You can access the web interface at http://[raspberry-pi-ip]:7799"
    log "Default username: admin, password: admin"
    log "IMPORTANT: Please change the default password after first login."

    read -p "Would you like to reboot now? (y/n): " reboot_now
    if [[ "$reboot_now" =~ ^[Yy]$ ]]; then
        log "Rebooting system..."
        reboot
    else
        log "Please reboot manually when convenient."
        log "Run: sudo reboot"
    fi
}

# Function to handle interactive setup
interactive_setup() {
    echo "Robot Mower Advanced - Interactive Setup"
    echo "---------------------------------------"
    echo "This script will guide you through the installation process."
    echo ""

    read -p "Would you like to proceed with installation? (y/n): " continue_install
    if [[ ! "$continue_install" =~ ^[Yy]$ ]]; then
        echo "Installation aborted."
        exit 0
    fi

    # Optional configurations
    read -p "Would you like to set up HTTPS for the web interface? (y/n): " setup_https_option

    # Run installation steps
    check_root
    update_system
    install_dependencies
    enable_interfaces
    add_user_to_groups
    clone_repository
    create_directories
    create_default_config
    install_hailo_sdk
    configure_hailo
    create_service
    setup_web_interface

    # Optional steps
    setup_network

    if [[ "$setup_https_option" =~ ^[Yy]$ ]]; then
        setup_https
    fi

    finalize
}

# Main execution
log "Starting Robot Mower Advanced installation..."
echo "Robot Mower Advanced Installation"
echo "================================="
echo "This script will install the Robot Mower Advanced software on your Raspberry Pi."
echo "Log file: $LOG_FILE"
echo ""

interactive_setup
