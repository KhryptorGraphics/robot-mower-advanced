#!/bin/bash

# Core installation functions for the Raspberry Pi
# This script is called by the main install_raspberry_pi.sh script

# Function to update package lists
update_system() {
    log "Updating package lists..."
    apt-get update >> "$LOG_FILE" 2>&1
    log "Upgrading installed packages..."
    apt-get upgrade -y >> "$LOG_FILE" 2>&1
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
        "${INSTALL_DIR}/data/slam_maps"
        "${INSTALL_DIR}/data/path_plans"
    )

    # Create each directory
    for DIR in "${DIRS[@]}"; do
        mkdir -p "$DIR" >> "$LOG_FILE" 2>&1
        chown -R pi:pi "$DIR" >> "$LOG_FILE" 2>&1
    done

    log "Directories created successfully."
}

# Function to add user to required groups
add_user_to_groups() {
    USER="pi"
    log "Adding user ${USER} to required groups..."
    usermod -a -G dialout,i2c,spi,gpio,input,video "$USER" >> "$LOG_FILE" 2>&1
    log "User added to required groups."
}

# Check if the installation is successful
check_installation() {
    log "Checking installation..."
    
    # Check if service is running or enabled
    if systemctl is-enabled --quiet robot-mower.service; then
        log "Service robot-mower.service is enabled."
    else
        log "WARNING: Service robot-mower.service is not enabled!"
    fi
    
    # Check if web service is running or enabled
    if systemctl is-enabled --quiet robot-mower-web.service; then
        log "Service robot-mower-web.service is enabled."
    else
        log "WARNING: Service robot-mower-web.service is not enabled!"
    fi
    
    # Check if dependencies are installed
    if [ -d "${INSTALL_DIR}/venv" ]; then
        log "Python virtual environment is set up."
    else
        log "WARNING: Python virtual environment is not set up correctly!"
    fi
    
    log "Installation check completed."
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

# Print installation summary
print_summary() {
    log "=============================================="
    log "Robot Mower Advanced Installation Summary"
    log "=============================================="
    log "Installation Directory: ${INSTALL_DIR}"
    log "Log File: ${LOG_FILE}"
    log ""
    log "Web Interface URL: http://$(hostname -I | awk '{print $1}'):7799"
    log "Default Admin Username: admin"
    log "Default Admin Password: admin"
    log ""
    log "To check service status: systemctl status robot-mower.service"
    log "To check web interface status: systemctl status robot-mower-web.service"
    log ""
    log "Configuration Directory: ${INSTALL_DIR}/config"
    log "Logs Directory: ${INSTALL_DIR}/logs"
    log ""
    log "Installation completed successfully!"
    log "=============================================="
}
