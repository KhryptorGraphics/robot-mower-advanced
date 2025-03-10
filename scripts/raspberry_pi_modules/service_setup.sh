#!/bin/bash

# Service setup module for the Raspberry Pi
# This script is called by the main install_raspberry_pi.sh script

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

# Function to verify services are set up correctly
verify_services() {
    log "Verifying service setup..."
    
    # Check main service
    if systemctl is-enabled robot-mower.service &>/dev/null; then
        log "Main service is enabled."
    else
        log "WARNING: Main service is not enabled."
    fi
    
    # Check web service
    if systemctl is-enabled robot-mower-web.service &>/dev/null; then
        log "Web interface service is enabled."
    else
        log "WARNING: Web interface service is not enabled."
    fi
    
    # Display service status
    if systemctl status robot-mower.service &>/dev/null; then
        systemctl status robot-mower.service --no-pager >> "$LOG_FILE" 2>&1
    fi
    
    if systemctl status robot-mower-web.service &>/dev/null; then
        systemctl status robot-mower-web.service --no-pager >> "$LOG_FILE" 2>&1
    fi
    
    log "Service verification completed."
}

# Function to create startup scripts
create_startup_scripts() {
    log "Creating startup scripts..."
    
    if [ -d "${INSTALL_DIR}" ]; then
        # Create a startup script for manual execution
        cat > "${INSTALL_DIR}/start.sh" << EOF
#!/bin/bash
# Manual startup script for Robot Mower Advanced

# Start the main service
sudo systemctl start robot-mower.service

# Start the web interface
sudo systemctl start robot-mower-web.service

echo "Robot Mower Advanced services started."
EOF

        # Create a stop script
        cat > "${INSTALL_DIR}/stop.sh" << EOF
#!/bin/bash
# Manual stop script for Robot Mower Advanced

# Stop the main service
sudo systemctl stop robot-mower.service

# Stop the web interface
sudo systemctl stop robot-mower-web.service

echo "Robot Mower Advanced services stopped."
EOF

        # Make scripts executable
        chmod +x "${INSTALL_DIR}/start.sh" "${INSTALL_DIR}/stop.sh"
        chown pi:pi "${INSTALL_DIR}/start.sh" "${INSTALL_DIR}/stop.sh"
        
        log "Startup scripts created successfully."
    else
        log "Installation directory not found. Cannot create startup scripts."
    fi
}
