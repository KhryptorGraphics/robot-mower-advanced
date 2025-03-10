#!/bin/bash

# Robot Mower Advanced - Ubuntu Server Installation Script
#
# This script installs all dependencies and sets up the Robot Mower
# Advanced Control Panel on an Ubuntu server. It configures the system
# to serve the control panel on port 7799.
#

set -e  # Exit immediately if a command exits with non-zero status
INSTALL_DIR="/opt/robot-mower-control-panel"
LOG_FILE="/tmp/robot_mower_control_panel_install.log"
CONTROL_PANEL_PORT=7799
SERVICE_NAME="robot-mower-control-panel"
GIT_REPO="https://github.com/khryptorgraphics/robot-mower-advanced.git"

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
    apt-get install -y python3-pip python3-dev python3-venv nginx git \
    build-essential libssl-dev libffi-dev supervisor >> "$LOG_FILE" 2>&1

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
    
    if [ ! -f "${INSTALL_DIR}/web/app.py" ]; then
        log "Creating web app module..."
        cat > "${INSTALL_DIR}/web/app.py" << EOF
"""
Robot Mower Control Panel Web Interface

This module provides the web interface for the Robot Mower Control Panel.
"""

import os
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_socketio import SocketIO

logger = logging.getLogger(__name__)

class WebInterface:
    """Web interface for the Robot Mower Control Panel."""
    
    def __init__(self, config, **services):
        """Initialize the web interface.
        
        Args:
            config: Configuration object
            **services: Service dependencies
        """
        self.config = config
        self.services = services
        self.app = Flask(__name__, 
                         template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
                         static_folder=os.path.join(os.path.dirname(__file__), 'static'))
        self.app.secret_key = os.urandom(24)
        self.socketio = SocketIO(self.app)
        
        self._setup_routes()
        self._setup_socketio_events()
        
        # Log configuration
        self.port = config.get("web.port", 7799)
        self.host = config.get("web.host", "0.0.0.0")
        self.debug = config.get("web.debug", False)
        self.use_ssl = config.get("web.enable_https", False)
        
        if self.use_ssl:
            self.cert_file = config.get("web.ssl_cert", "")
            self.key_file = config.get("web.ssl_key", "")
            
            if not os.path.exists(self.cert_file) or not os.path.exists(self.key_file):
                logger.warning("SSL certificate or key not found, disabling HTTPS")
                self.use_ssl = False
    
    def _setup_routes(self):
        """Set up Flask routes."""
        app = self.app
        
        @app.route('/')
        def index():
            return render_template('index.html')
        
        @app.route('/login', methods=['GET', 'POST'])
        def login():
            if request.method == 'POST':
                username = request.form.get('username')
                password = request.form.get('password')
                
                # Simple default authentication
                if username == 'admin' and password == 'admin123':
                    session['logged_in'] = True
                    session['username'] = username
                    return redirect(url_for('dashboard'))
                else:
                    return render_template('login.html', error='Invalid credentials')
            
            return render_template('login.html')
        
        @app.route('/dashboard')
        def dashboard():
            if not session.get('logged_in'):
                return redirect(url_for('login'))
            return render_template('additional/dashboard.html')
        
        @app.route('/zones')
        def zones():
            if not session.get('logged_in'):
                return redirect(url_for('login'))
            return render_template('additional/zones.html')
        
        @app.route('/api/status')
        def status():
            return jsonify({
                'status': 'online',
                'version': '1.0.0',
                'uptime': '0 days, 0 hours, 0 minutes'
            })
    
    def _setup_socketio_events(self):
        """Set up SocketIO event handlers."""
        socketio = self.socketio
        
        @socketio.on('connect')
        def handle_connect():
            logger.info("Client connected")
        
        @socketio.on('disconnect')
        def handle_disconnect():
            logger.info("Client disconnected")
    
    def start(self):
        """Start the web interface."""
        logger.info(f"Starting web interface on {self.host}:{self.port}")
        
        if self.use_ssl:
            logger.info("Using HTTPS")
            ssl_context = (self.cert_file, self.key_file)
        else:
            ssl_context = None
        
        self.socketio.run(self.app, host=self.host, port=self.port, 
                          debug=self.debug, ssl_context=ssl_context)
    
    def stop(self):
        """Stop the web interface."""
        logger.info("Stopping web interface")
        # No explicit stop needed for Flask development server
EOF
    fi
    
    # Create __init__.py in web directory if it doesn't exist
    if [ ! -f "${INSTALL_DIR}/web/__init__.py" ]; then
        echo '"""Web interface package for Robot Mower Control Panel."""' > "${INSTALL_DIR}/web/__init__.py"
    fi
    
    # Create core directory and required modules
    mkdir -p "${INSTALL_DIR}/core"
    echo '"""Core functionality for Robot Mower Control Panel."""' > "${INSTALL_DIR}/core/__init__.py"
    
    # Create a simple config manager
    cat > "${INSTALL_DIR}/core/config.py" << EOF
"""
Configuration manager for Robot Mower Control Panel.
"""

import os
import yaml
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages configuration for the Robot Mower Control Panel."""
    
    def __init__(self, config_dir):
        """Initialize configuration manager.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = config_dir
        self.config = {}
        self.load_config()
    
    def load_config(self):
        """Load configuration from files."""
        # Try to load local config first
        local_config_path = os.path.join(self.config_dir, 'local_config.yaml')
        default_config_path = os.path.join(self.config_dir, 'default_config.yaml')
        
        if os.path.exists(local_config_path):
            self._load_file(local_config_path)
        elif os.path.exists(default_config_path):
            self._load_file(default_config_path)
        else:
            logger.warning("No configuration file found")
    
    def _load_file(self, path):
        """Load configuration from a file.
        
        Args:
            path: Path to configuration file
        """
        try:
            with open(path, 'r') as f:
                self.config.update(yaml.safe_load(f) or {})
            logger.info(f"Loaded configuration from {path}")
        except Exception as e:
            logger.error(f"Error loading configuration from {path}: {e}")
    
    def get(self, key, default=None):
        """Get a configuration value.
        
        Args:
            key: Configuration key (dot-separated for nested keys)
            default: Default value if key is not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key, value):
        """Set a configuration value.
        
        Args:
            key: Configuration key (dot-separated for nested keys)
            value: Value to set
        """
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
EOF

    # Create requirements file for the control panel
    cat > "${INSTALL_DIR}/requirements.txt" << EOF
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
EOF

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

# Function to create control panel launcher script
create_launcher() {
    log "Creating launcher script..."
    cat > "${INSTALL_DIR}/run_control_panel.py" << EOF
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
    config.set("web.port", ${CONTROL_PANEL_PORT})

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
    chmod +x "${INSTALL_DIR}/run_control_panel.py"

    log "Launcher script created successfully."
}

# Function to set up HTTPS (optional)
setup_https() {
    log "Setting up HTTPS for web interface..."

    # Create directory for certificates
    mkdir -p "${INSTALL_DIR}/certs"

    # Generate self-signed certificates
    log "Generating self-signed certificates..."
    openssl req -x509 -newkey rsa:4096 -nodes -out "${INSTALL_DIR}/certs/cert.pem" \
        -keyout "${INSTALL_DIR}/certs/key.pem" -days 365 \
        -subj "/CN=Robot Mower Control Panel" >> "$LOG_FILE" 2>&1

    # Update permissions
    chmod 600 "${INSTALL_DIR}/certs/key.pem"

    # Update local configuration to use HTTPS
    if [ -f "${INSTALL_DIR}/config/local_config.yaml" ]; then
        # Create a backup of the existing config
        cp "${INSTALL_DIR}/config/local_config.yaml" "${INSTALL_DIR}/config/local_config.yaml.bak"
        
        # This is a simplified approach to update YAML - a more robust solution would use a YAML parser
        if grep -q "^web:" "${INSTALL_DIR}/config/local_config.yaml"; then
            # Web section exists, update it
            sed -i '/^web:/,/^[a-z]/{s/enable_ssl: false/enable_ssl: true/g}' "${INSTALL_DIR}/config/local_config.yaml"
            sed -i '/^web:/,/^[a-z]/{s/ssl_cert: ""/ssl_cert: "certs\/cert.pem"/g}' "${INSTALL_DIR}/config/local_config.yaml"
            sed -i '/^web:/,/^[a-z]/{s/ssl_key: ""/ssl_key: "certs\/key.pem"/g}' "${INSTALL_DIR}/config/local_config.yaml"
        else
            # Web section doesn't exist, add it
            cat >> "${INSTALL_DIR}/config/local_config.yaml" << EOF

# HTTPS Configuration
web:
  enable_ssl: true
  ssl_cert: "certs/cert.pem"
  ssl_key: "certs/key.pem"
  port: ${CONTROL_PANEL_PORT}
EOF
        fi
        
        log "HTTPS configuration updated in local_config.yaml"
    else
        # Create minimal config if it doesn't exist
        mkdir -p "${INSTALL_DIR}/config"
        cat > "${INSTALL_DIR}/config/local_config.yaml" << EOF
# Robot Mower Control Panel Configuration

system:
  app_name: "RobotMowerControlPanel"
  data_dir: "data"
  log_level: "INFO"
  log_file: "logs/control_panel.log"

# Web interface settings
web:
  enabled: true
  host: "0.0.0.0"
  port: ${CONTROL_PANEL_PORT}
  enable_ssl: true
  ssl_cert: "certs/cert.pem"
  ssl_key: "certs/key.pem"
  require_login: true
EOF
        log "Created new local_config.yaml with HTTPS enabled"
    fi
}

# Function to create systemd service
create_service() {
    log "Creating systemd service..."

    # Create service file
    cat > "/etc/systemd/system/${SERVICE_NAME}.service" << EOF
[Unit]
Description=Robot Mower Advanced Control Panel
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=${INSTALL_DIR}
ExecStart=${INSTALL_DIR}/venv/bin/python3 ${INSTALL_DIR}/run_control_panel.py
Restart=always
RestartSec=5
Environment="PATH=${INSTALL_DIR}/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=${INSTALL_DIR}"

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and enable the service
    systemctl daemon-reload >> "$LOG_FILE" 2>&1
    systemctl enable "${SERVICE_NAME}.service" >> "$LOG_FILE" 2>&1

    log "Service created and enabled successfully."
}

# Function to set up Nginx as a reverse proxy (optional)
setup_nginx() {
    log "Setting up Nginx as a reverse proxy..."

    # Install Nginx if not already installed
    apt-get install -y nginx >> "$LOG_FILE" 2>&1

    # Create Nginx site configuration
    cat > "/etc/nginx/sites-available/${SERVICE_NAME}" << EOF
server {
    listen 80;
    server_name _;

    # Redirect all HTTP traffic to HTTPS on the control panel port
    location / {
        return 301 https://\$host:${CONTROL_PANEL_PORT}\$request_uri;
    }
}

server {
    # Listen on the control panel port with SSL
    listen ${CONTROL_PANEL_PORT} ssl http2;
    server_name _;

    # SSL certificates
    ssl_certificate ${INSTALL_DIR}/certs/cert.pem;
    ssl_certificate_key ${INSTALL_DIR}/certs/key.pem;

    # SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers 'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;

    # Security headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Proxy settings for the control panel
    location / {
        proxy_pass http://127.0.0.1:7800;  # Internal port
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
EOF

    # Update the control panel config to listen on internal port
    if [ -f "${INSTALL_DIR}/config/local_config.yaml" ]; then
        # Create a backup of the config
        cp "${INSTALL_DIR}/config/local_config.yaml" "${INSTALL_DIR}/config/local_config.yaml.bak"
        
        # Update the port
        sed -i "s/port: ${CONTROL_PANEL_PORT}/port: 7800/" "${INSTALL_DIR}/config/local_config.yaml"
    fi

    # Enable the site and restart Nginx
    ln -sf "/etc/nginx/sites-available/${SERVICE_NAME}" "/etc/nginx/sites-enabled/"

    # Remove default site
    rm -f /etc/nginx/sites-enabled/default

    # Check Nginx configuration
    nginx -t >> "$LOG_FILE" 2>&1

    # Restart Nginx
    systemctl restart nginx >> "$LOG_FILE" 2>&1

    log "Nginx configured as reverse proxy."
}

# Function to set permissions
set_permissions() {
    log "Setting permissions..."

    # Owner should be the user that runs the service (www-data)
    chown -R www-data:www-data "${INSTALL_DIR}"

    # Make sure logs directory is writable
    chmod 755 "${INSTALL_DIR}/logs"
    
    # Ensure execution permissions on the launcher script
    chmod +x "${INSTALL_DIR}/run_control_panel.py"
}

# Function to open firewall port
configure_firewall() {
    log "Configuring firewall..."

    # Check if ufw is installed
    if command -v ufw > /dev/null; then
        log "Allowing port ${CONTROL_PANEL_PORT} through ufw..."
        ufw allow ${CONTROL_PANEL_PORT}/tcp >> "$LOG_FILE" 2>&1

        # Also allow HTTP/HTTPS for Nginx if installed
        if [ -x "$(command -v nginx)" ]; then
            ufw allow 80/tcp >> "$LOG_FILE" 2>&1
            ufw allow 443/tcp >> "$LOG_FILE" 2>&1
        fi
    else
        log "UFW not installed. Please configure your firewall manually to allow port ${CONTROL_PANEL_PORT}."
    fi
}

# Function to start services
start_services() {
    log "Starting services..."

    # Start the control panel service
    systemctl start "${SERVICE_NAME}.service" >> "$LOG_FILE" 2>&1

    # Check if Nginx is installed and start it
    if [ -x "$(command -v nginx)" ]; then
        systemctl start nginx >> "$LOG_FILE" 2>&1
    fi

    log "Services started successfully."
}

# Function to display installation completion
display_completion() {
    log "Control Panel installation completed successfully!"

    # Get server IP for instructions
    SERVER_IP=$(hostname -I | awk '{print $1}')

    echo "======================================================"
    echo "   Robot Mower Advanced Control Panel installed!"
    echo "======================================================"
    echo ""
    echo "You can access the control panel at:"
    if [ -x "$(command -v nginx)" ]; then
        echo "  https://${SERVER_IP}:${CONTROL_PANEL_PORT}"
    else
        if grep -q "enable_ssl: true" "${INSTALL_DIR}/config/local_config.yaml"; then
            echo "  https://${SERVER_IP}:${CONTROL_PANEL_PORT}"
        else
            echo "  http://${SERVER_IP}:${CONTROL_PANEL_PORT}"
        fi
    fi
    echo ""
    echo "Default login credentials:"
    echo "  Username: admin"
    echo "  Password: admin123"
    echo ""
    echo "IMPORTANT: Change the default password after logging in!"
    echo ""
    echo "For troubleshooting check the logs:"
    echo "  ${INSTALL_DIR}/logs/control_panel.log"
    echo "  ${LOG_FILE}"
    echo ""
}

# Function to handle interactive setup
interactive_setup() {
    echo "Robot Mower Advanced Control Panel - Interactive Setup"
    echo "---------------------------------------------------"
    echo "This script will install the Robot Mower Advanced Control Panel"
    echo "on this Ubuntu server and make it available on port ${CONTROL_PANEL_PORT}."
    echo ""

    read -p "Would you like to proceed with installation? (y/n): " continue_install
    if [[ ! "$continue_install" =~ ^[Yy]$ ]]; then
        echo "Installation aborted."
        exit 0
    fi

    # Ask about optional features
    read -p "Would you like to set up HTTPS? (y/n) [y recommended]: " setup_https_option
    read -p "Would you like to use Nginx as a reverse proxy? (y/n) [y recommended]: " use_nginx_option

    # Perform installation
    check_root
    update_system
    install_dependencies
    create_install_dir
    clone_repository
    setup_python_env
    create_launcher

    # Optional HTTPS setup
    if [[ "$setup_https_option" =~ ^[Yy]$ ]]; then
        setup_https
    fi

    # Create service
    create_service

    # Optional Nginx setup
    if [[ "$use_nginx_option" =~ ^[Yy]$ ]]; then
        setup_nginx
    fi

    # Final steps
    set_permissions
    configure_firewall
    start_services
    display_completion
}

# Main execution
echo "Robot Mower Advanced Control Panel Installation"
echo "=============================================="
echo "This script will install the Robot Mower Advanced Control Panel"
echo "on your Ubuntu server."
echo "Log file: $LOG_FILE"
echo ""

interactive_setup
