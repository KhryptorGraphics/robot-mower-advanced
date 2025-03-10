#!/bin/bash

# Template for creating the web app module
# This script is called by the main install_ubuntu_server.sh script

create_web_app() {
    local install_dir=$1
    
    if [ ! -f "${install_dir}/web/app.py" ]; then
        log "Creating web app module..."
        cat > "${install_dir}/web/app.py" << EOF
"""
Robot Mower Control Panel Web Interface

This module provides the web interface for the Robot Mower Control Panel.
"""

import os
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file
from flask_socketio import SocketIO
import io
import base64
import matplotlib.pyplot as plt
import numpy as np
import json

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
            
        @app.route('/slam_map')
        def slam_map():
            if not session.get('logged_in'):
                return redirect(url_for('login'))
            return render_template('additional/slam_map.html')
        
        @app.route('/path_planning')
        def path_planning():
            if not session.get('logged_in'):
                return redirect(url_for('login'))
            return render_template('additional/path_planning.html')
        
        @app.route('/api/status')
        def status():
            return jsonify({
                'status': 'online',
                'version': '1.0.0',
                'uptime': '0 days, 0 hours, 0 minutes'
            })
            
        @app.route('/api/slam_map/latest')
        def get_latest_slam_map():
            try:
                # In a real implementation, this would fetch the latest SLAM map
                # For now, return a placeholder image
                
                # Generate a placeholder map
                fig, ax = plt.subplots(figsize=(10, 10))
                grid = np.zeros((100, 100))
                
                # Create a simple map with some obstacles
                grid[20:30, 20:30] = 1  # obstacle
                grid[60:70, 40:80] = 1  # obstacle
                grid[40:60, 20:30] = 1  # obstacle
                
                # Plot the map
                ax.imshow(grid, cmap='gray_r', origin='lower')
                ax.set_title('SLAM Map')
                ax.set_xlabel('X (meters)')
                ax.set_ylabel('Y (meters)')
                
                # Add a robot position
                ax.plot(50, 50, 'ro', markersize=10)
                
                # Save to a BytesIO object
                img_data = io.BytesIO()
                fig.savefig(img_data, format='png')
                img_data.seek(0)
                plt.close(fig)
                
                # Return the image
                return send_file(img_data, mimetype='image/png')
            
            except Exception as e:
                logger.error(f"Error generating SLAM map: {e}")
                return jsonify({'error': str(e)}), 500
                
        @app.route('/api/path_planning/zones')
        def get_path_planning_zones():
            try:
                # In a real implementation, this would fetch the actual zones
                # For now, return placeholder data
                zones = [
                    {
                        'id': 'zone1',
                        'name': 'Main Lawn',
                        'perimeter': [[0, 0], [0, 10], [10, 10], [10, 0]],
                        'pattern': 'parallel',
                        'direction_degrees': 0,
                        'overlap_percent': 15
                    },
                    {
                        'id': 'zone2',
                        'name': 'Side Garden',
                        'perimeter': [[12, 0], [12, 8], [20, 8], [20, 0]],
                        'pattern': 'spiral',
                        'overlap_percent': 10
                    }
                ]
                return jsonify(zones)
            
            except Exception as e:
                logger.error(f"Error fetching path planning zones: {e}")
                return jsonify({'error': str(e)}), 500
    
    def _setup_socketio_events(self):
        """Set up SocketIO event handlers."""
        socketio = self.socketio
        
        @socketio.on('connect')
        def handle_connect():
            logger.info("Client connected")
        
        @socketio.on('disconnect')
        def handle_disconnect():
            logger.info("Client disconnected")
            
        @socketio.on('request_status_update')
        def handle_status_request():
            # In a real implementation, this would fetch the actual status
            status_data = {
                'battery': 78,
                'position': {'x': 5.2, 'y': 3.7, 'theta': 45},
                'status': 'mowing',
                'progress': 65,
                'current_zone': 'Main Lawn',
                'remaining_time': '35 minutes'
            }
            socketio.emit('status_update', status_data)
    
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
    if [ ! -f "${install_dir}/web/__init__.py" ]; then
        echo '"""Web interface package for Robot Mower Control Panel."""' > "${install_dir}/web/__init__.py"
    fi
}
