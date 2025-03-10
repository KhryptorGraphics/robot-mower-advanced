#!/bin/bash

# Template for setting up the systemd service
# This script is called by the main install_ubuntu_server.sh script

create_launcher() {
    local install_dir=$1
    local control_panel_port=$2
    
    log "Creating launcher script..."
    cat > "${install_dir}/run_control_panel.py" << EOF
#!/usr/bin/env python3
"""
Robot Mower Control Panel Launcher

This script launches the Robot Mower Advanced Control Panel
on a specified port. It configures the web server and handles
routing to the main application.
"""

import os
import sys
import logging
from pathlib import Path

# Add the installation directory to the path
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

# Import the web application
from web.app import WebInterface
from core.config import ConfigManager

# Configure logging
log_dir = os.path.join(current_dir, 'logs')
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(log_dir, 'control_panel.log'),
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('control_panel')

def main():
    """Main entry point for the control panel"""
    logger.info("Starting Robot Mower Control Panel")

    # Load configuration
    config_path = os.path.join(current_dir, 'config', 'local_config.yaml')
    if not os.path.exists(config_path):
        config_path = os.path.join(current_dir, 'config', 'default_config.yaml')

    config = ConfigManager(os.path.dirname(config_path))

    # Override web port with the control panel port
    config.set("web.port", ${control_panel_port})

    # Create web interface
    web_interface = WebInterface(
        config=config,
        power_manager=None,
        zone_manager=None,
        health_analyzer=None,
        growth_predictor=None,
        maintenance_tracker=None,
        theft_protection=None,
        weather_scheduler=None
    )

    # Start web interface
    web_interface.start()

    # Wait for termination
    try:
        import time
        while True:
            time.sleep(3600)  # Sleep for an hour (will be interrupted by SIGINT)
    except KeyboardInterrupt:
        logger.info("Shutting down Control Panel")
        web_interface.stop()

if __name__ == "__main__":
    main()
EOF

    # Make the launcher executable
    chmod +x "${install_dir}/run_control_panel.py"

    log "Launcher script created successfully."
}

setup_systemd_service() {
    local install_dir=$1
    local service_name=$2
    
    log "Setting up systemd service..."
    
    # Create systemd service file
    cat > "/etc/systemd/system/${service_name}.service" << EOF
[Unit]
Description=Robot Mower Control Panel
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${install_dir}
ExecStart=${install_dir}/venv/bin/python ${install_dir}/run_control_panel.py
Restart=on-failure
RestartSec=5
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=${service_name}

[Install]
WantedBy=multi-user.target
EOF

    log "Reloading systemd daemon..."
    systemctl daemon-reload

    # Enable the service to start on boot
    log "Enabling ${service_name} service to start on boot..."
    systemctl enable ${service_name}

    # Start the service
    log "Starting ${service_name} service..."
    systemctl start ${service_name}

    log "Systemd service setup completed."
}

setup_nginx() {
    local install_dir=$1
    local control_panel_port=$2
    
    log "Setting up Nginx as reverse proxy..."
    
    # Create Nginx configuration
    cat > "/etc/nginx/sites-available/robot-mower-control-panel.conf" << EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://localhost:${control_panel_port};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

    # Create a symbolic link to sites-enabled
    if [ -f "/etc/nginx/sites-enabled/robot-mower-control-panel.conf" ]; then
        log "Removing existing Nginx symbolic link..."
        rm /etc/nginx/sites-enabled/robot-mower-control-panel.conf
    fi
    
    log "Creating Nginx symbolic link..."
    ln -s /etc/nginx/sites-available/robot-mower-control-panel.conf /etc/nginx/sites-enabled/

    # Test Nginx configuration
    log "Testing Nginx configuration..."
    nginx -t >> "$LOG_FILE" 2>&1
    
    # Restart Nginx to apply changes
    log "Restarting Nginx..."
    systemctl restart nginx
    
    log "Nginx setup completed."
}

create_requirements_file() {
    local install_dir=$1
    
    log "Creating requirements file..."
    cat > "${install_dir}/requirements.txt" << EOF
Flask==2.2.3
Flask-SocketIO==5.3.2
PyYAML==6.0
eventlet==0.33.3
python-engineio==4.3.4
python-socketio==5.7.2
bcrypt==4.0.1
PyJWT==2.6.0
requests==2.28.2
gunicorn==20.1.0
numpy>=1.22.0
matplotlib>=3.5.0
scipy>=1.8.0
pillow>=9.0.0
opencv-python-headless>=4.6.0
EOF
    
    log "Requirements file created successfully."
}
