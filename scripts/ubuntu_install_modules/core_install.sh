#!/bin/bash

# Core installation functions for the Ubuntu Server
# This script is called by the main install_ubuntu_server.sh script

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
    apt-get install -y python3-pip python3-dev python3-venv nginx git \
    build-essential libssl-dev libffi-dev supervisor \
    cmake libusb-1.0-0-dev pkg-config libswscale-dev libavcodec-dev \
    libavformat-dev libgstreamer1.0-dev libv4l-dev \
    python3-numpy python3-opencv python3-matplotlib >> "$LOG_FILE" 2>&1

    log "Installing Python packages..."
    python3 -m pip install --upgrade pip >> "$LOG_FILE" 2>&1
}

# Function to create installation directory
create_install_dir() {
    log "Creating installation directory..."
    mkdir -p "${INSTALL_DIR}"

    log "Creating required subdirectories..."
    mkdir -p "${INSTALL_DIR}/logs"
    mkdir -p "${INSTALL_DIR}/config"
    mkdir -p "${INSTALL_DIR}/certs"
    mkdir -p "${INSTALL_DIR}/data"
    mkdir -p "${INSTALL_DIR}/data/slam_maps"
    mkdir -p "${INSTALL_DIR}/data/path_plans"
}

# Function to clone the repository
clone_repository() {
    log "Cloning repository..."
    cd /tmp

    if [ -d "/tmp/robot-mower-advanced" ]; then
        log "Removing existing temporary clone..."
        rm -rf /tmp/robot-mower-advanced
    fi

    git clone "${GIT_REPO}" >> "$LOG_FILE" 2>&1

    log "Copying control panel files to installation directory..."
    # Copy required files to installation directory
    cp -r /tmp/robot-mower-advanced/web "${INSTALL_DIR}/"
    cp -r /tmp/robot-mower-advanced/config "${INSTALL_DIR}/"

    # Create web directory and app.py if they don't exist
    mkdir -p "${INSTALL_DIR}/web"
    
    # Create __init__.py in web directory if it doesn't exist
    if [ ! -f "${INSTALL_DIR}/web/__init__.py" ]; then
        echo '"""Web interface package for Robot Mower Control Panel."""' > "${INSTALL_DIR}/web/__init__.py"
    fi
    
    # Clean up
    rm -rf /tmp/robot-mower-advanced
}

# Function to set up Python environment
setup_python_env() {
    log "Setting up Python virtual environment..."
    cd "${INSTALL_DIR}"

    # Create virtual environment
    python3 -m venv venv >> "$LOG_FILE" 2>&1

    # Activate and install requirements
    . venv/bin/activate
    pip install -r requirements.txt >> "$LOG_FILE" 2>&1
    pip install gunicorn >> "$LOG_FILE" 2>&1
    deactivate

    log "Python environment set up successfully."
}

# Check if the installation is successful
check_installation() {
    log "Checking installation..."
    
    # Check if service is running
    if systemctl is-active --quiet ${SERVICE_NAME}; then
        log "Service ${SERVICE_NAME} is running."
    else
        log "WARNING: Service ${SERVICE_NAME} is not running!"
    fi
    
    # Check if Nginx is running
    if systemctl is-active --quiet nginx; then
        log "Nginx is running."
    else
        log "WARNING: Nginx is not running!"
    fi
    
    # Try to connect to the web server
    if curl -s --head http://localhost:${CONTROL_PANEL_PORT} | grep "200 OK" > /dev/null; then
        log "Web server is responding to requests."
    else
        log "WARNING: Web server is not responding to requests!"
    fi
    
    log "Installation check completed."
}

# Print installation summary
print_summary() {
    log "=============================================="
    log "Robot Mower Control Panel Installation Summary"
    log "=============================================="
    log "Installation Directory: ${INSTALL_DIR}"
    log "Control Panel Port: ${CONTROL_PANEL_PORT}"
    log "Service Name: ${SERVICE_NAME}"
    log "Log File: ${LOG_FILE}"
    log ""
    log "Web Interface URL: http://$(hostname -I | awk '{print $1}')"
    log "Default Admin Username: admin"
    log "Default Admin Password: admin123"
    log ""
    log "To check service status: systemctl status ${SERVICE_NAME}"
    log "To stop service: systemctl stop ${SERVICE_NAME}"
    log "To start service: systemctl start ${SERVICE_NAME}"
    log "To restart service: systemctl restart ${SERVICE_NAME}"
    log ""
    log "Configuration Directory: ${INSTALL_DIR}/config"
    log "Logs Directory: ${INSTALL_DIR}/logs"
    log ""
    log "Installation completed successfully!"
    log "=============================================="
}
