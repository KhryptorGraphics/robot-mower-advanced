#!/bin/bash

# Dependencies installation module for the Raspberry Pi
# This script is called by the main install_raspberry_pi.sh script

# Function to install required packages
install_dependencies() {
    log "Installing required packages..."
    apt-get install -y python3-pip python3-dev python3-numpy python3-opencv \
    python3-smbus python3-yaml git i2c-tools libopenjp2-7 libatlas-base-dev \
    libjpeg-dev libwebp-dev libtiff5 screen cmake build-essential libusb-1.0-0-dev \
    pkg-config libswscale-dev libavcodec-dev libavformat-dev libgstreamer1.0-dev \
    libv4l-dev python3-picamera libgpiod2 python3-rpi.gpio usbutils \
    bluetooth libbluetooth-dev python3-serial \
    libsuitesparse-dev libeigen3-dev libceres-dev python3-matplotlib >> "$LOG_FILE" 2>&1

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
        
        # Install additional dependencies for SLAM and advanced path planning
        log "Installing additional dependencies for SLAM and advanced path planning..."
        pip install g2o-python shapely >> "$LOG_FILE" 2>&1
        
        deactivate
    else
        log "Installation directory not found. Clone the repository first."
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
