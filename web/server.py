#!/usr/bin/env python3
"""
Robot Mower Advanced Web Server

This module implements the web server for the Robot Mower Advanced system,
providing a web interface for monitoring and controlling the mower.
"""

import os
import sys
import json
import logging
import datetime
import threading
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash, send_file
from flask_socketio import SocketIO, emit
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import configuration management
from core.config import ConfigManager
from core.logger import setup_logger

# Create logger
logger = logging.getLogger('web_server')

class User(UserMixin):
    """User class for Flask-Login"""
    def __init__(self, id, username, password_hash, role="user"):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.role = role
    
    def check_password(self, password):
        """Check password hash"""
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        """Check if user is admin"""
        return self.role == "admin"


class WebInterface:
    """Web interface for the Robot Mower Advanced system."""
    
    def __init__(self, config, power_manager=None, navigation_manager=None, 
                 zone_manager=None, mower_controller=None, scheduler=None,
                 maintenance_tracker=None, health_analyzer=None, 
                 growth_predictor=None, theft_protection=None, 
                 weather_scheduler=None):
        """
        Initialize the web interface.
        
        Args:
            config: Configuration object
            power_manager: Power management system
            navigation_manager: Navigation system
            zone_manager: Zone management system
            mower_controller: Mower controller
            scheduler: Scheduling system
            maintenance_tracker: Maintenance tracking system
            health_analyzer: Lawn health analysis system
            growth_predictor: Grass growth prediction system
            theft_protection: Anti-theft system
            weather_scheduler: Weather-based scheduling system
        """
        self.config = config
        
        # Store service dependencies
        self.services = {
            'power_manager': power_manager,
            'navigation_manager': navigation_manager,
            'zone_manager': zone_manager,
            'mower_controller': mower_controller,
            'scheduler': scheduler,
            'maintenance_tracker': maintenance_tracker,
            'health_analyzer': health_analyzer,
            'growth_predictor': growth_predictor,
            'theft_protection': theft_protection,
            'weather_scheduler': weather_scheduler
        }
        
        # Create Flask app
        self.app = Flask(__name__, 
                          template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
                          static_folder=os.path.join(os.path.dirname(__file__), 'static'))
        
        # Set secret key for session management
        secret_key = config.get("web.secret_key", os.urandom(24))
        self.app.secret_key = secret_key
        
        # Initialize SocketIO
        self.socketio = SocketIO(self.app, async_mode='eventlet', cors_allowed_origins="*")
        
        # Initialize login manager
        self.login_manager = LoginManager()
        self.login_manager.init_app(self.app)
        self.login_manager.login_view = 'login'
        
        # Set up users
        self.users = self._load_users()
        
        # Set up routes and Socket.IO event handlers
        self._setup_routes()
        self._setup_socketio_events()
        
        # Get web server configuration
        self.host = config.get("web.host", "0.0.0.0")
        self.port = config.get("web.port", 8080)
        self.debug = config.get("web.debug", False)
        self.enable_ssl = config.get("web.enable_ssl", False)
        
        # SSL certificate and key paths
        if self.enable_ssl:
            self.cert_file = config.get("web.ssl_cert", "")
            self.key_file = config.get("web.ssl_key", "")
            
            if not (os.path.exists(self.cert_file) and os.path.exists(self.key_file)):
                logger.warning("SSL certificate or key not found, disabling HTTPS")
                self.enable_ssl = False
        
        # Status update thread
        self.status_thread = None
        self.running = False
        
        logger.info("Web interface initialized")
    
    def _load_users(self) -> Dict[str, User]:
        """
        Load users from configuration.
        
        Returns:
            Dictionary of username to User object
        """
        users = {}
        
        # Get default admin credentials
        admin_username = self.config.get("web.username", "admin")
        admin_password = self.config.get("web.password", "admin")
        
        # Create default admin user with hash
        users[admin_username] = User(
            id=admin_username,
            username=admin_username,
            password_hash=generate_password_hash(admin_password),
            role="admin"
        )
        
        # Additional users can be loaded from configuration
        additional_users = self.config.get("web.users", {})
        for username, user_data in additional_users.items():
            if username != admin_username:  # Skip if already added
                users[username] = User(
                    id=username,
                    username=username,
                    password_hash=user_data.get("password_hash", ""),
                    role=user_data.get("role", "user")
                )
        
        return users
    
    @property
    def mower_controller(self):
        """Get mower controller"""
        return self.services.get('mower_controller')
    
    @property
    def navigation_manager(self):
        """Get navigation manager"""
        return self.services.get('navigation_manager')
    
    @property
    def zone_manager(self):
        """Get zone manager"""
        return self.services.get('zone_manager')
    
    @property
    def scheduler(self):
        """Get scheduler"""
        return self.services.get('scheduler')
    
    def _setup_routes(self):
        """Set up Flask routes for the web interface."""
        
        @self.login_manager.user_loader
        def load_user(user_id):
            """Load user for Flask-Login"""
            return self.users.get(user_id)
        
        @self.app.route('/')
        def index():
            """Render main page or redirect to login"""
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            return render_template('index.html', user=current_user.username, page='index')
        
        @self.app.route('/login', methods=['GET', 'POST'])
        def login():
            """Handle login form"""
            if current_user.is_authenticated:
                return redirect(url_for('index'))
            
            if request.method == 'POST':
                username = request.form.get('username')
                password = request.form.get('password')
                
                user = self.users.get(username)
                if user and user.check_password(password):
                    login_user(user)
                    next_page = request.args.get('next')
                    return redirect(next_page or url_for('index'))
                else:
                    flash('Invalid username or password', 'danger')
            
            return render_template('login.html')
        
        @self.app.route('/logout')
        @login_required
        def logout():
            """Handle logout"""
            logout_user()
            return redirect(url_for('login'))
        
        @self.app.route('/dashboard')
        @login_required
        def dashboard():
            """Render dashboard page"""
            return render_template('additional/dashboard.html', user=current_user.username, page='dashboard')
        
        @self.app.route('/zones')
        @login_required
        def zones():
            """Render zones page"""
            return render_template('additional/zones.html', user=current_user.username, page='zones')
        
        @self.app.route('/schedule')
        @login_required
        def schedule():
            """Render schedule page"""
            return render_template('additional/schedule.html', user=current_user.username, page='schedule')
        
        @self.app.route('/maintenance')
        @login_required
        def maintenance():
            """Render maintenance page"""
            return render_template('additional/maintenance.html', user=current_user.username, page='maintenance')
        
        @self.app.route('/settings')
        @login_required
        def settings():
            """Render settings page"""
            return render_template('additional/settings.html', user=current_user.username, page='settings')
        
        @self.app.route('/api/v1/status')
        @login_required
        def api_status():
            """API endpoint for getting system status"""
            return jsonify(self._get_status())
        
        @self.app.route('/api/v1/mower/start', methods=['POST'])
        @login_required
        def api_start_mower():
            """API endpoint for starting the mower"""
            zone_id = request.json.get('zone_id') if request.json else None
            
            if self.mower_controller:
                success = self.mower_controller.start(zone_id=zone_id)
                return jsonify({'success': success})
            
            return jsonify({'success': False, 'error': 'Mower controller not available'})
        
        @self.app.route('/api/v1/mower/stop', methods=['POST'])
        @login_required
        def api_stop_mower():
            """API endpoint for stopping the mower"""
            if self.mower_controller:
                success = self.mower_controller.stop()
                return jsonify({'success': success})
            
            return jsonify({'success': False, 'error': 'Mower controller not available'})
        
        @self.app.route('/api/v1/mower/pause', methods=['POST'])
        @login_required
        def api_pause_mower():
            """API endpoint for pausing the mower"""
            if self.mower_controller:
                success = self.mower_controller.pause()
                return jsonify({'success': success})
            
            return jsonify({'success': False, 'error': 'Mower controller not available'})
        
        @self.app.route('/api/v1/mower/dock', methods=['POST'])
        @login_required
        def api_dock_mower():
            """API endpoint for docking the mower"""
            if self.mower_controller:
                success = self.mower_controller.return_to_dock()
                return jsonify({'success': success})
            
            return jsonify({'success': False, 'error': 'Mower controller not available'})
        
        @self.app.route('/api/v1/zones', methods=['GET'])
        @login_required
        def api_get_zones():
            """API endpoint for getting zones"""
            if self.zone_manager:
                zones = self.zone_manager.get_zones()
                return jsonify({'success': True, 'zones': zones})
            
            # Return dummy data if zone manager not available
            return jsonify({
                'success': True,
                'zones': [
                    {
                        'id': 1,
                        'name': 'Front Yard',
                        'active': True,
                        'area': 60,
                        'mowing_pattern': 'grid',
                        'cutting_height': 45,
                        'last_mowed': '2 days ago',
                        'progress': 100
                    },
                    {
                        'id': 2,
                        'name': 'Back Yard',
                        'active': True,
                        'area': 120,
                        'mowing_pattern': 'lines',
                        'cutting_height': 50,
                        'last_mowed': 'Yesterday',
                        'progress': 75
                    },
                    {
                        'id': 3,
                        'name': 'Side Garden',
                        'active': True,
                        'area': 45,
                        'mowing_pattern': 'spiral',
                        'cutting_height': 35,
                        'last_mowed': '4 days ago',
                        'progress': 0
                    },
                    {
                        'id': 4,
                        'name': 'Play Area',
                        'active': False,
                        'area': 25,
                        'mowing_pattern': 'perimeter',
                        'cutting_height': 40,
                        'last_mowed': 'Never',
                        'progress': 0
                    }
                ]
            })
        
        @self.app.route('/api/v1/zones/<int:zone_id>', methods=['GET'])
        @login_required
        def api_get_zone(zone_id):
            """API endpoint for getting a specific zone"""
            if self.zone_manager:
                zone = self.zone_manager.get_zone(zone_id)
                if zone:
                    return jsonify({'success': True, 'zone': zone})
                return jsonify({'success': False, 'error': 'Zone not found'})
            
            return jsonify({'success': False, 'error': 'Zone manager not available'})
        
        @self.app.route('/api/v1/zones', methods=['POST'])
        @login_required
        def api_create_zone():
            """API endpoint for creating a zone"""
            if not self.zone_manager:
                return jsonify({'success': False, 'error': 'Zone manager not available'})
            
            zone_data = request.json
            if not zone_data:
                return jsonify({'success': False, 'error': 'No data provided'})
            
            try:
                zone_id = self.zone_manager.add_zone(zone_data)
                return jsonify({'success': True, 'zone_id': zone_id})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/v1/zones/<int:zone_id>', methods=['PUT'])
        @login_required
        def api_update_zone(zone_id):
            """API endpoint for updating a zone"""
            if not self.zone_manager:
                return jsonify({'success': False, 'error': 'Zone manager not available'})
            
            zone_data = request.json
            if not zone_data:
                return jsonify({'success': False, 'error': 'No data provided'})
            
            try:
                success = self.zone_manager.update_zone(zone_id, zone_data)
                return jsonify({'success': success})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/v1/zones/<int:zone_id>', methods=['DELETE'])
        @login_required
        def api_delete_zone(zone_id):
            """API endpoint for deleting a zone"""
            if not self.zone_manager:
                return jsonify({'success': False, 'error': 'Zone manager not available'})
            
            try:
                success = self.zone_manager.delete_zone(zone_id)
                return jsonify({'success': success})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/v1/schedule', methods=['GET'])
        @login_required
        def api_get_schedule():
            """API endpoint for getting the schedule"""
            if self.scheduler:
                schedule = self.scheduler.get_schedule()
                return jsonify({'success': True, 'schedule': schedule})
            
            # Return dummy schedule data if scheduler not available
            return jsonify({
                'success': True,
                'schedule': [
                    {
                        'id': 1,
                        'day': 'monday',
                        'start_time': '10:00',
                        'duration': 60,
                        'zone_id': 1,
                        'active': True
                    },
                    {
                        'id': 2,
                        'day': 'thursday',
                        'start_time': '14:00',
                        'duration': 90,
                        'zone_id': 2,
                        'active': True
                    },
                    {
                        'id': 3,
                        'day': 'saturday',
                        'start_time': '09:00',
                        'duration': 120,
                        'zone_id': 0,  # All zones
                        'active': True
                    }
                ]
            })
        
        @self.app.route('/api/v1/schedule', methods=['POST'])
        @login_required
        def api_add_schedule():
            """API endpoint for adding a schedule item"""
            if not self.scheduler:
                return jsonify({'success': False, 'error': 'Scheduler not available'})
            
            schedule_data = request.json
            if not schedule_data:
                return jsonify({'success': False, 'error': 'No data provided'})
            
            try:
                schedule_id = self.scheduler.add_schedule(schedule_data)
                return jsonify({'success': True, 'schedule_id': schedule_id})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/v1/schedule/<int:schedule_id>', methods=['PUT'])
        @login_required
        def api_update_schedule(schedule_id):
            """API endpoint for updating a schedule item"""
            if not self.scheduler:
                return jsonify({'success': False, 'error': 'Scheduler not available'})
            
            schedule_data = request.json
            if not schedule_data:
                return jsonify({'success': False, 'error': 'No data provided'})
            
            try:
                success = self.scheduler.update_schedule(schedule_id, schedule_data)
                return jsonify({'success': success})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/v1/schedule/<int:schedule_id>', methods=['DELETE'])
        @login_required
        def api_delete_schedule(schedule_id):
            """API endpoint for deleting a schedule item"""
            if not self.scheduler:
                return jsonify({'success': False, 'error': 'Scheduler not available'})
            
            try:
                success = self.scheduler.delete_schedule(schedule_id)
                return jsonify({'success': success})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/v1/settings', methods=['GET'])
        @login_required
        def api_get_settings():
            """API endpoint for getting settings"""
            # Get settings from configuration
            settings = {
                'system': {
                    'units': self.config.get('system.units', 'metric'),
                    'timezone': self.config.get('system.timezone', 'UTC'),
                    'log_level': self.config.get('system.log_level', 'INFO')
                },
                'hardware': {
                    'mower_width': self.config.get('hardware.mower_width', 0.28),
                    'wheel_diameter': self.config.get('hardware.wheel_diameter', 0.2),
                    'wheel_base': self.config.get('hardware.wheel_base', 0.35),
                    'max_speed': self.config.get('hardware.max_speed', 0.5),
                    'max_turn_rate': self.config.get('hardware.max_turn_rate', 45)
                },
                'navigation': {
                    'mowing_pattern': self.config.get('navigation.mowing_pattern', 'adaptive'),
                    'line_direction': self.config.get('navigation.line_direction', 0.0),
                    'path_overlap_percent': self.config.get('navigation.path_overlap_percent', 10.0),
                    'perimeter_passes': self.config.get('navigation.perimeter_passes', 2),
                    'obstacle_buffer': self.config.get('navigation.obstacle_buffer', 0.3)
                },
                'schedule': {
                    'enabled': self.config.get('schedule.enabled', True),
                    'max_run_time': self.config.get('schedule.max_run_time', 120),
                    'rain_delay': self.config.get('schedule.rain_delay', 360)
                },
                'security': {
                    'pin_code': self.config.get('security.pin_code', '0000'),
                    'auto_lock': self.config.get('security.auto_lock', True),
                    'lock_timeout': self.config.get('security.lock_timeout', 300)
                },
                'web': {
                    'port': self.config.get('web.port', 8080),
                    'enable_ssl': self.config.get('web.enable_ssl', False)
                }
            }
            
            return jsonify({'success': True, 'settings': settings})
        
        @self.app.route('/api/v1/settings', methods=['PUT'])
        @login_required
        def api_update_settings():
            """API endpoint for updating settings"""
            if not current_user.is_admin():
                return jsonify({'success': False, 'error': 'Admin privileges required'})
            
            settings = request.json
            if not settings:
                return jsonify({'success': False, 'error': 'No data provided'})
            
            # Update settings in configuration
            try:
                for section, values in settings.items():
                    for key, value in values.items():
                        self.config.set(f"{section}.{key}", value)
                
                # Save configuration
                self.config.save()
                
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/v1/maintenance', methods=['GET'])
        @login_required
        def api_get_maintenance():
            """API endpoint for getting maintenance information"""
            if self.services.get('maintenance_tracker'):
                maintenance = self.services['maintenance_tracker'].get_maintenance_info()
                return jsonify({'success': True, 'maintenance': maintenance})
            
            # Return dummy maintenance data if tracker not available
            return jsonify({
                'success': True,
                'maintenance': {
                    'blade_replacement': {
                        'name': 'Blade Replacement',
                        'last_maintenance': '2025-02-15T10:30:00Z',
                        'hours_run': 15,
                        'hours_interval': 25,
                        'due_in_hours': 10,
                        'status': 'ok'
                    },
                    'filter_cleaning': {
                        'name': 'Filter Cleaning',
                        'last_maintenance': '2025-03-01T14:00:00Z',
                        'hours_run': 8,
                        'hours_interval': 10,
                        'due_in_hours': 2,
                        'status': 'warning'
                    },
                    'general_inspection': {
                        'name': 'General Inspection',
                        'last_maintenance': '2025-02-01T09:00:00Z',
                        'hours_run': 45,
                        'hours_interval': 50,
                        'due_in_hours': 5,
                        'status': 'ok'
                    },
                    'wheel_cleaning': {
                        'name': 'Wheel Cleaning',
                        'last_maintenance': '2025-03-05T16:30:00Z',
                        'hours_run': 12,
                        'hours_interval': 10,
                        'due_in_hours': -2,
                        'status': 'overdue'
                    }
                }
            })
        
        @self.app.route('/api/v1/maintenance/<item_id>', methods=['POST'])
        @login_required
        def api_record_maintenance(item_id):
            """API endpoint for recording maintenance"""
            if not self.services.get('maintenance_tracker'):
                return jsonify({'success': False, 'error': 'Maintenance tracker not available'})
            
            try:
                success = self.services['maintenance_tracker'].record_maintenance(item_id)
                return jsonify({'success': success})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/v1/lawn/health', methods=['GET'])
        @login_required
        def api_get_lawn_health():
            """API endpoint for getting lawn health information"""
            if self.services.get('health_analyzer'):
                health = self.services['health_analyzer'].get_lawn_health()
                return jsonify({'success': True, 'health': health})
            
            # Return dummy lawn health data if analyzer not available
            return jsonify({
                'success': True,
                'health': {
                    'overall': 85,
                    'zones': {
                        1: 90,
                        2: 75,
                        3: 85,
                        4: 88
                    },
                    'recommendations': [
                        'Increase watering in zone 2',
                        'Consider fertilizing in the next week',
                        'Adjust cutting height to 5cm for better growth'
                    ]
                }
            })
        
        @self.app.route('/api/v1/weather', methods=['GET'])
        @login_required
        def api_get_weather():
            """API endpoint for getting weather information"""
            if self.services.get('weather_scheduler'):
                weather = self.services['weather_scheduler'].get_weather()
                return jsonify({'success': True, 'weather': weather})
            
            # Return dummy weather data if scheduler not available
            return jsonify({
                'success': True,
                'weather': {
                    'current': {
                        'condition': 'clear',
                        'temperature': 22,
                        'humidity': 65,
                        'wind_speed': 3,
                        'rain_probability': 0
                    },
                    'forecast': [
                        {
                            'day': 'Today',
                            'condition': 'clear',
                            'temperature_high': 25,
                            'temperature_low': 18,
                            'rain_probability': 0
                        },
                        {
                            'day': 'Tomorrow',
                            'condition': 'cloudy',
                            'temperature_high': 23,
                            'temperature_low': 17,
                            'rain_probability': 30
                        },
                        {
                            'day': 'Day 3',
                            'condition': 'rain',
                            'temperature_high': 20,
                            'temperature_low': 15,
                            'rain_probability': 80
                        }
                    ]
                }
            })
        
        @self.app.route('/api/v1/activity', methods=['GET'])
        @login_required
        def api_get_activity():
            """API endpoint for getting recent activity"""
            # Return dummy activity data
            return jsonify({
                'success': True,
                'activity': [
                    {
                        'id': 1,
                        'timestamp': '2025-03-09T21:00:00Z',
                        'type': 'mowing_completed',
                        'description': 'Front yard mowing completed successfully. 98% coverage achieved.',
                        'zone_id': 1
                    },
                    {
                        'id': 2,
                        'timestamp': '2025-03-09T19:00:00Z',
                        'type': 'obstacle_detected',
                        'description': 'Temporary obstacle detected and avoided in the east section.',
                        'zone_id': 1
                    },
                    {
                        'id': 3,
                        'timestamp': '2025-03-08T15:30:00Z',
                        'type': 'battery_charged',
                        'description': 'Battery charged to 100%. Charging time: 3h 25m.'
                    },
                    {
                        'id': 4,
                        'timestamp': '2025-03-07T12:00:00Z',
                        'type': 'system_update',
                        'description': 'System updated to version 2.1.4. New features added.'
                    }
                ]
            })
        
        @self.app.route('/api/v1/mower/manual-control', methods=['POST'])
        @login_required
        def api_manual_control():
            """API endpoint for manual control of the mower"""
            if not self.mower_controller:
                return jsonify({'success': False, 'error': 'Mower controller not available'})
            
            control_data = request.json
            if not control_data:
                return jsonify({'success': False, 'error': 'No data provided'})
            
            command = control_data.get('command')
            speed = control_data.get('speed', 0.5)
            duration = control_data.get('duration', 1.0)
            
            try:
                success = self.mower_controller.manual_control(command, speed, duration)
                return jsonify({'success': success})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/v1/logs', methods=['GET'])
        @login_required
        def api_get_logs():
            """API endpoint for getting system logs"""
            if not current_user.is_admin():
                return jsonify({'success': False, 'error': 'Admin privileges required'})
            
            lines = request.args.get('lines', 100, type=int)
            level = request.args.get('level', 'INFO')
            
            # Return dummy log data
            return jsonify({
                'success': True,
                'logs': [
                    {
                        'timestamp': '2025-03-09T23:45:12Z',
                        'level': 'INFO',
                        'module': 'main',
                        'message': 'System started successfully'
                    },
                    {
                        'timestamp': '2025-03-09T23:45:15Z',
                        'level': 'INFO',
                        'module': 'navigation',
                        'message': 'GPS position acquired: 47.6062, -122.3321'
                    },
                    {
                        'timestamp': '2025-03-09T23:46:01Z',
                        'level': 'WARNING',
                        'module': 'mower',
                        'message': 'Battery level below 30%, consider charging soon'
                    },
                    {
                        'timestamp': '2025-03-09T23:47:30Z',
                        'level': 'INFO',
                        'module': 'theft_protection',
                        'message': 'Perimeter check complete, no intrusions detected'
                    }
                ]
            })
        
        @self.app.route('/api/v1/perception/obstacles', methods=['GET'])
        @login_required
        def api_get_obstacles():
            """API endpoint for getting current obstacle detections"""
            return jsonify({
                'success': True,
                'obstacles': [
                    {
                        'id': 1,
                        'timestamp': '2025-03-10T00:10:15Z',
                        'class': 'person',
                        'confidence': 0.95,
                        'distance': 4.2,
                        'position': {
                            'x': 2.3,
                            'y': 1.5
                        },
                        'size': {
                            'width': 0.5,
                            'height': 1.7
                        },
                        'is_safety_critical': True
                    },
                    {
                        'id': 2,
                        'timestamp': '2025-03-10T00:10:15Z',
                        'class': 'dog',
                        'confidence': 0.87,
                        'distance': 6.1,
                        'position': {
                            'x': -1.2,
                            'y': 2.3
                        },
                        'size': {
                            'width': 0.4,
                            'height': 0.5
                        },
                        'is_safety_critical': True
                    }
                ]
            })
    
    def _setup_socketio_events(self):
        """Set up Socket.IO event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection"""
            logger.info(f"Client connected: {request.sid}")
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection"""
            logger.info(f"Client disconnected: {request.sid}")
        
        @self.socketio.on('get_status')
        def handle_get_status():
            """Handle status request"""
            emit('status', self._get_status())
        
        @self.socketio.on('start_mower')
        def handle_start_mower(data):
            """Handle mower start request"""
            zone_id = data.get('zone_id') if data else None
            
            if self.mower_controller:
                success = self.mower_controller.start(zone_id=zone_id)
                emit('mower_command_result', {'command': 'start', 'success': success})
            else:
                emit('mower_command_result', {'command': 'start', 'success': False, 'error': 'Mower controller not available'})
        
        @self.socketio.on('stop_mower')
        def handle_stop_mower():
            """Handle mower stop request"""
            if self.mower_controller:
                success = self.mower_controller.stop()
                emit('mower_command_result', {'command': 'stop', 'success': success})
            else:
                emit('mower_command_result', {'command': 'stop', 'success': False, 'error': 'Mower controller not available'})
        
        @self.socketio.on('pause_mower')
        def handle_pause_mower():
            """Handle mower pause request"""
            if self.mower_controller:
                success = self.mower_controller.pause()
                emit('mower_command_result', {'command': 'pause', 'success': success})
            else:
                emit('mower_command_result', {'command': 'pause', 'success': False, 'error': 'Mower controller not available'})
        
        @self.socketio.on('dock_mower')
        def handle_dock_mower():
            """Handle mower return to dock request"""
            if self.mower_controller:
                success = self.mower_controller.return_to_dock()
                emit('mower_command_result', {'command': 'dock', 'success': success})
            else:
                emit('mower_command_result', {'command': 'dock', 'success': False, 'error': 'Mower controller not available'})
    
    def _get_status(self) -> Dict[str, Any]:
        """
        Get system status.
        
        Returns:
            Dictionary with system status information
        """
        # Get status from services
        status = {
            'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
            'mower': self._get_mower_status(),
            'power': self._get_power_status(),
            'navigation': self._get_navigation_status(),
            'zone': self._get_zone_status(),
            'schedule': self._get_schedule_status(),
            'maintenance': self._get_maintenance_status(),
            'weather': self._get_weather_status(),
            'system': self._get_system_status()
        }
        
        return status
    
    def _get_mower_status(self) -> Dict[str, Any]:
        """Get mower status"""
        if self.mower_controller:
            return self.mower_controller.get_status()
        
        # Return dummy data if mower controller not available
        return {
            'state': 'idle',
            'progress': 0,
            'runtime': 0,
            'blade_rpm': 0,
            'error': None
        }
    
    def _get_power_status(self) -> Dict[str, Any]:
        """Get power status"""
        if self.services.get('power_manager'):
            return self.services['power_manager'].get_status()
        
        # Return dummy data if power manager not available
        return {
            'battery_level': 85,
            'charging': False,
            'voltage': 24.5,
            'current': 1.2,
            'temperature': 28
        }
    
    def _get_navigation_status(self) -> Dict[str, Any]:
        """Get navigation status"""
        if self.navigation_manager:
            return self.navigation_manager.get_status()
        
        # Return dummy data if navigation manager not available
        return {
            'position': {'x': 12.5, 'y': 8.3},
            'orientation': 45.0,
            'speed': 0.0,
            'gps_quality': 'good',
            'satellites': 8
        }
    
    def _get_zone_status(self) -> Dict[str, Any]:
        """Get zone status"""
        if self.zone_manager:
            return self.zone_manager.get_status()
        
        # Return dummy data if zone manager not available
        return {
            'current_zone': 'Front Yard',
            'current_zone_id': 1,
            'zone_count': 4,
            'active_zones': 3,
            'total_area': 250
        }
    
    def _get_schedule_status(self) -> Dict[str, Any]:
        """Get schedule status"""
        if self.scheduler:
            return self.scheduler.get_status()
        
        # Return dummy data if scheduler not available
        return {
            'enabled': True,
            'next_mowing': 'Tomorrow 10:00',
            'next_zone_id': 1,
            'rain_delay_active': False
        }
    
    def _get_maintenance_status(self) -> Dict[str, Any]:
        """Get maintenance status"""
        if self.services.get('maintenance_tracker'):
            return self.services['maintenance_tracker'].get_status()
        
        # Return dummy data if maintenance tracker not available
        return {
            'blade_wear': 15,
            'total_mowing_hours': 45,
            'maintenance_due': 'Filter cleaning in 2 hours'
        }
    
    def _get_weather_status(self) -> Dict[str, Any]:
        """Get weather status"""
        if self.services.get('weather_scheduler'):
            return self.services['weather_scheduler'].get_status()
        
        # Return dummy data if weather scheduler not available
        return {
            'condition': 'clear',
            'temperature': 22,
            'humidity': 65,
            'wind_speed': 3,
            'rain_probability': 0,
            'rain_expected_24h': False
        }
    
    def _get_system_status(self) -> Dict[str, Any]:
        """Get system status"""
        # Get system stats
        return {
            'cpu_usage': 25,
            'memory_usage': 45,
            'disk_usage': 30,
            'temperature': 40,
            'uptime': '2d 7h 35m'
        }
    
    def start_status_updates(self) -> None:
        """Start status update thread"""
        if self.running:
            logger.warning("Status updates already running")
            return
        
        self.running = True
        self.status_thread = threading.Thread(target=self._status_update_loop)
        self.status_thread.daemon = True
        self.status_thread.start()
        
        logger.info("Status update thread started")
    
    def stop_status_updates(self) -> None:
        """Stop status update thread"""
        self.running = False
        
        if self.status_thread and self.status_thread.is_alive():
            self.status_thread.join(timeout=2.0)
        
        logger.info("Status update thread stopped")
    
    def _status_update_loop(self) -> None:
        """Status update loop"""
        logger.info("Status update loop started")
        
        while self.running:
            try:
                # Get status
                status = self._get_status()
                
                # Emit status update to all connected clients
                self.socketio.emit('status', status)
                
                # Sleep a bit
                time.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Error in status update loop: {e}")
                time.sleep(5.0)
    
    def run(self) -> None:
        """Run the web server"""
        logger.info(f"Starting web server on {self.host}:{self.port}")
        
        # Start status updates
        self.start_status_updates()
        
        try:
            if self.enable_ssl:
                # Run with SSL
                self.socketio.run(
                    self.app,
                    host=self.host,
                    port=self.port,
                    debug=self.debug,
                    certfile=self.cert_file,
                    keyfile=self.key_file,
                    use_reloader=False
                )
            else:
                # Run without SSL
                self.socketio.run(
                    self.app,
                    host=self.host,
                    port=self.port,
                    debug=self.debug,
                    use_reloader=False
                )
        except Exception as e:
            logger.error(f"Error running web server: {e}")
        finally:
            # Stop status updates
            self.stop_status_updates()


def main():
    """Run the web server as a standalone application"""
    # Set up logging
    setup_logger(level=logging.INFO)
    
    # Load configuration
    config = ConfigManager("config/local_config.yaml", "config/default_config.yaml")
    
    # Create web interface
    web_interface = WebInterface(config)
    
    # Run web server
    web_interface.run()


if __name__ == "__main__":
    main()
