"""
Web Interface Module

This module provides a web-based user interface for monitoring and controlling
the robot mower remotely through a browser. Includes a dashboard, status monitoring,
control options, and access to various mower features and settings.
"""

import os
import json
import logging
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import time
import math
from functools import wraps

from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory, session
from flask_socketio import SocketIO, emit
import jwt
import bcrypt
import secrets

from ..core.config import ConfigManager
from ..hardware.interfaces import PowerManagement, GPSPosition
from ..perception.lawn_health import LawnHealthAnalyzer
from ..perception.growth_prediction import GrassGrowthPredictor
from ..navigation.zone_management import ZoneManager
from ..maintenance.maintenance_tracker import MaintenanceTracker
from ..security.theft_protection import TheftProtection, TheftStatus
from ..scheduling.weather_scheduler import WeatherBasedScheduler


class WebInterface:
    """
    Class providing a web interface for the robot mower
    
    Provides a dashboard, status monitoring, and remote control capabilities.
    """
    
    def __init__(self, 
                 config: ConfigManager,
                 power_manager: Optional[PowerManagement] = None,
                 zone_manager: Optional[ZoneManager] = None,
                 health_analyzer: Optional[LawnHealthAnalyzer] = None,
                 growth_predictor: Optional[GrassGrowthPredictor] = None,
                 maintenance_tracker: Optional[MaintenanceTracker] = None,
                 theft_protection: Optional[TheftProtection] = None,
                 weather_scheduler: Optional[WeatherBasedScheduler] = None):
        """
        Initialize the web interface
        
        Args:
            config: Configuration manager
            power_manager: Power management interface
            zone_manager: Zone management module
            health_analyzer: Lawn health analyzer
            growth_predictor: Grass growth predictor
            maintenance_tracker: Maintenance tracking module
            theft_protection: Theft protection module
            weather_scheduler: Weather-based scheduler
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.power_manager = power_manager
        self.zone_manager = zone_manager
        self.health_analyzer = health_analyzer
        self.growth_predictor = growth_predictor
        self.maintenance_tracker = maintenance_tracker
        self.theft_protection = theft_protection
        self.weather_scheduler = weather_scheduler
        
        # Configuration
        self.host = config.get("web.host", "0.0.0.0")
        self.port = config.get("web.port", 8080)
        self.debug = config.get("web.debug", False)
        self.enable_https = config.get("web.enable_https", False)
        self.cert_file = config.get("web.cert_file", "")
        self.key_file = config.get("web.key_file", "")
        self.require_login = config.get("web.require_login", True)
        self.session_timeout = config.get("web.session_timeout", 3600)  # 1 hour
        self.jwt_secret = config.get("web.jwt_secret", secrets.token_hex(32))
        
        # Paths
        data_dir = config.get("system.data_dir", "data")
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        static_dir = os.path.join(os.path.dirname(__file__), "static")
        self.users_file = os.path.join(data_dir, "web_users.json")
        
        # Create directories if needed
        os.makedirs(os.path.dirname(self.users_file), exist_ok=True)
        os.makedirs(template_dir, exist_ok=True)
        os.makedirs(static_dir, exist_ok=True)
        
        # Initialize Flask app
        self.app = Flask(__name__, 
                        template_folder=template_dir,
                        static_folder=static_dir)
        self.app.secret_key = secrets.token_hex(16)
        
        # Initialize Socket.IO for real-time updates
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # Users and authentication
        self.users = self._load_users()
        if not self.users and self.require_login:
            self._create_default_admin()
        
        # Status tracking
        self.last_status_update = 0
        self.status_update_interval = 1.0  # seconds
        self.telemetry_history: Dict[str, List[Dict[str, Any]]] = {
            "battery_level": [],
            "temperature": [],
            "motor_load": [],
            "errors": []
        }
        self.max_history_points = 100
        
        # Status flags
        self.is_running = False
        self.server_thread = None
        self.update_thread = None
        
        # Register routes and socket events
        self._register_routes()
        self._register_socket_events()
        
        self.logger.info("Web interface initialized")
    
    def _load_users(self) -> Dict[str, Dict[str, Any]]:
        """
        Load users from file
        
        Returns:
            Dictionary of users
        """
        if os.path.exists(self.users_file):
            try:
                with open(self.users_file, 'r') as f:
                    users = json.load(f)
                
                self.logger.info(f"Loaded {len(users)} users")
                return users
            except Exception as e:
                self.logger.error(f"Error loading users: {e}")
        
        return {}
    
    def _save_users(self) -> None:
        """Save users to file"""
        try:
            with open(self.users_file, 'w') as f:
                json.dump(self.users, f, indent=2)
            
            self.logger.debug("Saved user data")
        except Exception as e:
            self.logger.error(f"Error saving users: {e}")
    
    def _create_default_admin(self) -> None:
        """Create a default admin user"""
        default_password = "admin123"  # This is just an initial password that should be changed
        hashed_password = bcrypt.hashpw(default_password.encode('utf-8'), bcrypt.gensalt())
        
        self.users = {
            "admin": {
                "password_hash": hashed_password.decode('utf-8'),
                "role": "admin",
                "name": "Administrator",
                "created_at": datetime.now().isoformat()
            }
        }
        
        self._save_users()
        self.logger.warning("Created default admin user. Please change the password!")
    
    def _register_routes(self) -> None:
        """Register Flask routes"""
        app = self.app
        
        # Authentication decorator
        def login_required(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if not self.require_login:
                    return f(*args, **kwargs)
                
                # Check if user is logged in via session
                if 'user_id' not in session:
                    # Check if user has a valid JWT token in Authorization header
                    auth_header = request.headers.get('Authorization')
                    if auth_header and auth_header.startswith('Bearer '):
                        token = auth_header[7:]  # Remove 'Bearer ' prefix
                        try:
                            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
                            if 'user_id' in payload:
                                # Valid token, proceed
                                return f(*args, **kwargs)
                        except jwt.PyJWTError:
                            pass
                    
                    # No valid session or token, redirect to login
                    return redirect(url_for('login', next=request.url))
                
                return f(*args, **kwargs)
            return decorated_function
        
        # Routes
        @app.route('/')
        @login_required
        def index():
            return render_template('index.html', 
                                  user=session.get('user_id'),
                                  page='dashboard')
        
        @app.route('/login', methods=['GET', 'POST'])
        def login():
            error = None
            
            if request.method == 'POST':
                username = request.form['username']
                password = request.form['password']
                
                if username in self.users:
                    stored_hash = self.users[username]['password_hash'].encode('utf-8')
                    if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
                        session['user_id'] = username
                        session['role'] = self.users[username]['role']
                        
                        # Redirect to requested page or default to dashboard
                        next_page = request.args.get('next') or url_for('index')
                        return redirect(next_page)
                
                error = "Invalid username or password"
            
            return render_template('login.html', error=error)
        
        @app.route('/logout')
        def logout():
            session.pop('user_id', None)
            session.pop('role', None)
            return redirect(url_for('login'))
        
        @app.route('/api/token', methods=['POST'])
        def get_token():
            if not request.is_json:
                return jsonify({"error": "Missing JSON"}), 400
            
            username = request.json.get('username')
            password = request.json.get('password')
            
            if not username or not password:
                return jsonify({"error": "Missing username or password"}), 400
            
            if username in self.users:
                stored_hash = self.users[username]['password_hash'].encode('utf-8')
                if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
                    # Generate token
                    expiration = datetime.utcnow() + timedelta(seconds=self.session_timeout)
                    payload = {
                        'user_id': username,
                        'role': self.users[username]['role'],
                        'exp': expiration
                    }
                    token = jwt.encode(payload, self.jwt_secret, algorithm='HS256')
                    
                    return jsonify({
                        'token': token,
                        'expires': expiration.isoformat(),
                        'user': {
                            'username': username,
                            'role': self.users[username]['role'],
                            'name': self.users[username].get('name', username)
                        }
                    })
            
            return jsonify({"error": "Invalid username or password"}), 401
        
        @app.route('/dashboard')
        @login_required
        def dashboard():
            return render_template('dashboard.html',
                                 user=session.get('user_id'),
                                 page='dashboard')
        
        @app.route('/zones')
        @login_required
        def zones():
            return render_template('zones.html',
                                 user=session.get('user_id'),
                                 page='zones')
        
        @app.route('/schedule')
        @login_required
        def schedule():
            return render_template('schedule.html',
                                 user=session.get('user_id'),
                                 page='schedule')
        
        @app.route('/maintenance')
        @login_required
        def maintenance():
            return render_template('maintenance.html',
                                 user=session.get('user_id'),
                                 page='maintenance')
        
        @app.route('/settings')
        @login_required
        def settings():
            # Only admin users can access settings
            if session.get('role') != 'admin':
                return redirect(url_for('index'))
            
            return render_template('settings.html',
                                 user=session.get('user_id'),
                                 page='settings')
        
        @app.route('/api/status')
        @login_required
        def api_status():
            return jsonify(self._get_system_status())
        
        @app.route('/api/mower/start', methods=['POST'])
        @login_required
        def api_start_mower():
            if self.zone_manager:
                zone_id = request.json.get('zone_id')
                if zone_id is not None:
                    # In a real implementation, this would start the mower in the specified zone
                    self.logger.info(f"API request to start mower in zone {zone_id}")
                    return jsonify({"status": "started", "zone_id": zone_id})
                else:
                    # Start mowing using current schedule/configuration
                    self.logger.info("API request to start mower with current schedule")
                    return jsonify({"status": "started"})
            
            return jsonify({"error": "Zone manager not available"}), 500
        
        @app.route('/api/mower/stop', methods=['POST'])
        @login_required
        def api_stop_mower():
            # In a real implementation, this would stop the mower
            self.logger.info("API request to stop mower")
            return jsonify({"status": "stopped"})
        
        @app.route('/api/mower/dock', methods=['POST'])
        @login_required
        def api_dock_mower():
            # In a real implementation, this would send the mower to the dock
            self.logger.info("API request to dock mower")
            return jsonify({"status": "docking"})
        
        @app.route('/api/zones')
        @login_required
        def api_zones():
            if self.zone_manager:
                zones = []
                for zone in self.zone_manager.get_all_zones():
                    zones.append({
                        "id": zone.id,
                        "name": zone.name,
                        "area": zone.area,
                        "enabled": zone.enabled,
                        "boundary_points": len(zone.boundary),
                        "no_mow_areas": len(zone.no_mow_areas),
                        "pattern": zone.settings.pattern.value
                    })
                return jsonify(zones)
            
            return jsonify([])
        
        @app.route('/api/weather')
        @login_required
        def api_weather():
            if self.weather_scheduler:
                return jsonify(self.weather_scheduler.get_weather_summary())
            
            return jsonify({"available": False, "message": "Weather scheduler not available"})
        
        @app.route('/api/maintenance')
        @login_required
        def api_maintenance():
            if self.maintenance_tracker:
                return jsonify(self.maintenance_tracker.get_maintenance_summary())
            
            return jsonify({"available": False, "message": "Maintenance tracker not available"})
        
        @app.route('/api/growth')
        @login_required
        def api_growth():
            if self.growth_predictor:
                return jsonify(self.growth_predictor.get_growth_summary())
            
            return jsonify({"available": False, "message": "Growth predictor not available"})
        
        @app.route('/api/health')
        @login_required
        def api_health():
            if self.health_analyzer:
                # Get the latest health report
                latest_report = self.health_analyzer.get_latest_report()
                if latest_report:
                    return jsonify({
                        "available": True,
                        "status": latest_report.health_status.value,
                        "timestamp": latest_report.timestamp.isoformat(),
                        "issues": latest_report.issues,
                        "recommendations": latest_report.recommendations
                    })
            
            return jsonify({"available": False, "message": "Health analyzer not available"})
        
        @app.route('/api/users', methods=['GET'])
        @login_required
        def api_get_users():
            # Only admin users can access user list
            if session.get('role') != 'admin':
                return jsonify({"error": "Unauthorized"}), 403
            
            user_list = []
            for username, user_data in self.users.items():
                user_list.append({
                    "username": username,
                    "role": user_data["role"],
                    "name": user_data.get("name", username),
                    "created_at": user_data.get("created_at")
                })
            
            return jsonify(user_list)
        
        @app.route('/api/users', methods=['POST'])
        @login_required
        def api_create_user():
            # Only admin users can create users
            if session.get('role') != 'admin':
                return jsonify({"error": "Unauthorized"}), 403
            
            if not request.is_json:
                return jsonify({"error": "Missing JSON"}), 400
            
            username = request.json.get('username')
            password = request.json.get('password')
            name = request.json.get('name', username)
            role = request.json.get('role', 'user')
            
            if not username or not password:
                return jsonify({"error": "Missing username or password"}), 400
            
            if username in self.users:
                return jsonify({"error": "User already exists"}), 409
            
            if role not in ['admin', 'user']:
                return jsonify({"error": "Invalid role"}), 400
            
            # Create new user
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            self.users[username] = {
                "password_hash": hashed_password.decode('utf-8'),
                "role": role,
                "name": name,
                "created_at": datetime.now().isoformat()
            }
            
            self._save_users()
            self.logger.info(f"Created new user: {username}")
            
            return jsonify({
                "username": username,
                "role": role,
                "name": name,
                "created_at": self.users[username]["created_at"]
            }), 201
        
        @app.route('/api/users/<username>', methods=['DELETE'])
        @login_required
        def api_delete_user(username):
            # Only admin users can delete users
            if session.get('role') != 'admin':
                return jsonify({"error": "Unauthorized"}), 403
            
            if username not in self.users:
                return jsonify({"error": "User not found"}), 404
            
            # Prevent deleting the last admin user
            if self.users[username]["role"] == "admin" and len([u for u in self.users.values() if u["role"] == "admin"]) <= 1:
                return jsonify({"error": "Cannot delete the last admin user"}), 409
            
            # Delete user
            del self.users[username]
            self._save_users()
            self.logger.info(f"Deleted user: {username}")
            
            return jsonify({"success": True})
        
        @app.route('/api/users/<username>/password', methods=['PUT'])
        @login_required
        def api_change_password(username):
            # Users can change their own password, admins can change any password
            if session.get('role') != 'admin' and session.get('user_id') != username:
                return jsonify({"error": "Unauthorized"}), 403
            
            if not request.is_json:
                return jsonify({"error": "Missing JSON"}), 400
            
            password = request.json.get('password')
            
            if not password:
                return jsonify({"error": "Missing password"}), 400
            
            if username not in self.users:
                return jsonify({"error": "User not found"}), 404
            
            # Change password
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            self.users[username]["password_hash"] = hashed_password.decode('utf-8')
            self._save_users()
            self.logger.info(f"Changed password for: {username}")
            
            return jsonify({"success": True})
    
    def _register_socket_events(self) -> None:
        """Register Socket.IO event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect():
            # Authenticate socket connections
            auth = request.args.get('token')
            if self.require_login and not auth:
                return False
            
            if self.require_login:
                try:
                    jwt.decode(auth, self.jwt_secret, algorithms=['HS256'])
                except jwt.PyJWTError:
                    return False
            
            self.logger.debug("Client connected to socket")
            emit('status', self._get_system_status())
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            self.logger.debug("Client disconnected from socket")
        
        @self.socketio.on('get_status')
        def handle_get_status():
            emit('status', self._get_system_status())
        
        @self.socketio.on('start_mower')
        def handle_start_mower(data):
            zone_id = data.get('zone_id')
            self.logger.info(f"Socket request to start mower in zone {zone_id}")
            # In a real implementation, this would start the mower
            emit('command_result', {
                "command": "start",
                "success": True,
                "zone_id": zone_id
            })
        
        @self.socketio.on('stop_mower')
        def handle_stop_mower():
            self.logger.info("Socket request to stop mower")
            # In a real implementation, this would stop the mower
            emit('command_result', {
                "command": "stop",
                "success": True
            })
        
        @self.socketio.on('control_manual')
        def handle_control_manual(data):
            # Manual control commands
            direction = data.get('direction')
            speed = min(1.0, max(0.0, data.get('speed', 0.5)))
            
            self.logger.debug(f"Manual control: {direction} at speed {speed}")
            # In a real implementation, this would control the mower
            emit('command_result', {
                "command": "manual",
                "direction": direction,
                "speed": speed,
                "success": True
            })
    
    def _status_update_loop(self) -> None:
        """Background thread for status updates"""
        while self.is_running:
            current_time = time.time()
            
            # Update status at regular intervals
            if current_time - self.last_status_update >= self.status_update_interval:
                try:
                    status = self._get_system_status()
                    self.socketio.emit('status', status)
                    
                    # Update telemetry history
                    self._update_telemetry_history(status)
                    
                    self.last_status_update = current_time
                except Exception as e:
                    self.logger.error(f"Error updating status: {e}")
            
            # Sleep a bit
            time.sleep(0.5)
    
    def _update_telemetry_history(self, status: Dict[str, Any]) -> None:
        """
        Update telemetry history
        
        Args:
            status: Status data
        """
        timestamp = datetime.now().isoformat()
        
        # Update battery level history
        if 'power' in status and 'battery_level' in status['power']:
            self.telemetry_history['battery_level'].append({
                'timestamp': timestamp,
                'value': status['power']['battery_level']
            })
        
        # Update temperature history
        if 'sensors' in status and 'temperature' in status['sensors']:
            self.telemetry_history['temperature'].append({
                'timestamp': timestamp,
                'value': status['sensors']['temperature']
            })
        
        # Update motor load history
        if 'motors' in status and 'load' in status['motors']:
            self.telemetry_history['motor_load'].append({
                'timestamp': timestamp,
                'value': status['motors']['load']
            })
        
        # Update error history
        if 'errors' in status and status['errors']:
            for error in status['errors']:
                self.telemetry_history['errors'].append({
                    'timestamp': timestamp,
                    'value': error
                })
        
        # Limit history size
        for key in self.telemetry_history:
            if len(self.telemetry_history[key]) > self.max_history_points:
                self.telemetry_history[key] = self.telemetry_history[key][-self.max_history_points:]
    
    def _get_system_status(self) -> Dict[str, Any]:
        """
        Get current system status
        
        Returns:
            Status dictionary
        """
        status = {
            "timestamp": datetime.now().isoformat(),
            "state": "idle",  # Default state
            "errors": [],
            "warnings": []
        }
        
        # Add power status
        if self.power_manager:
            battery_level = self.power_manager.get_battery_percentage()
            charging = self.power_manager.is_charging()
            
            status["power"] = {
                "battery_level": battery_level,
                "charging": charging,
                "estimated_runtime": self._estimate_runtime(battery_level)
            }
        
        # Add zone status
        if self.zone_manager:
            current_zone = self.zone_manager.get_current_zone()
            status["zone"] = {
                "current_zone": current_zone.name if current_zone else None,
                "current_zone_id": self.zone_manager.current_zone_id,
                "zone_count": len(self.zone_manager.get_all_zones())
            }
        
        # Add mower status (in a real system, this would be retrieved from the mower controller)
        # This is a mock implementation
        status["mower"] = {
            "state": "idle",  # idle, mowing, docking, error
            "blade_on": False,
            "movement": "stopped",  # stopped, moving, turning
            "speed": 0.0,
            "progress": 0.0,  # 0-100%
            "estimated_completion": None
        }
        
        # Add sensor data (mocked)
        status["sensors"] = {
            "temperature": 25.0,  # C
            "humidity": 45.0,  # %
            "light_level": 80.0,  # %
            "rain_detected": False
        }
        
        # Add motor status (mocked)
        status["motors"] = {
            "left_speed": 0.0,
            "right_speed": 0.0,
            "blade_speed": 0.0,
            "load": 0.0
        }
        
        # Add position status
        if self.theft_protection:
            position = self.theft_protection.current_position
            if position:
                status["position"] = {
                    "latitude": position.latitude,
                    "longitude": position.longitude,
                    "accuracy": position.accuracy,
                    "timestamp": datetime.fromtimestamp(position.timestamp).isoformat()
                }
        
        # Add security status
        if self.theft_protection:
            status["security"] = {
                "status": self.theft_protection.current_status.value,
                "alarm_active": self.theft_protection.alarm_active,
                "within_geofence": self.theft_protection._is_within_geofence(),
                "last_update": datetime.fromtimestamp(self.theft_protection.last_update_time).isoformat() 
                               if self.theft_protection.last_update_time > 0 else None
            }
        
        # Add maintenance status
        if self.maintenance_tracker:
            maintenance_summary = self.maintenance_tracker.get_maintenance_summary()
            status["maintenance"] = {
                "overdue_count": maintenance_summary.get("overdue_count", 0),
                "due_soon_count": maintenance_summary.get("due_soon_count", 0),
                "has_critical": maintenance_summary.get("has_critical_maintenance", False),
                "next_item": maintenance_summary.get("next_maintenance", {}).get("name") 
                            if maintenance_summary.get("next_maintenance") else None
            }
            
            # Add maintenance warnings
            if maintenance_summary.get("has_critical_maintenance", False):
                status["warnings"].append("Maintenance overdue")
        
        # Add weather status
        if self.weather_scheduler:
            weather_summary = self.weather_scheduler.get_weather_summary()
            if weather_summary.get("available", False):
                status["weather"] = {
                    "condition": weather_summary.get("current_condition"),
                    "temperature": weather_summary.get("current_temperature"),
                    "description": weather_summary.get("current_description"),
                    "rain_expected_24h": weather_summary.get("rain_expected_24h", False)
                }
                
                # Add weather warnings
                if weather_summary.get("rain_expected_24h", False):
                    status["warnings"].append("Rain expected in next 24 hours")
        
        # Add growth status
        if self.growth_predictor:
            growth_summary = self.growth_predictor.get_growth_summary()
            if growth_summary.get("available", False):
                status["growth"] = {
                    "average_rate": growth_summary.get("average_growth_rate"),
                    "days_until_mowing": growth_summary.get("days_until_mowing"),
                    "next_mowing_date": growth_summary.get("next_mowing_date")
                }
        
        # Add health status
        if self.health_analyzer and self.health_analyzer.last_report:
            status["health"] = {
                "status": self.health_analyzer.last_report.health_status.value,
                "issues_count": len(self.health_analyzer.last_report.issues),
                "recommendations_count": len(self.health_analyzer.last_report.recommendations)
            }
        
        return status
    
    def _estimate_runtime(self, battery_level: float) -> float:
        """
        Estimate remaining runtime based on battery level
        
        Args:
            battery_level: Battery level (0-100%)
            
        Returns:
            Estimated runtime in hours
        """
        # This is a simple estimation model
        # In a real system, this would take into account current power consumption, mowing conditions, etc.
        if battery_level <= 0:
            return 0
        
        # Maximum runtime when battery is at 100%
        max_runtime = self.config.get("hardware.battery.max_runtime_hours", 4.0)
        
        # Calculate estimated runtime (simple linear model)
        # In a real system, this would be a non-linear curve based on discharge characteristics
        estimated_runtime = (battery_level / 100.0) * max_runtime
        
        return estimated_runtime
    
    def start(self) -> bool:
        """
        Start the web interface server
        
        Returns:
            Success or failure
        """
        if self.is_running:
            self.logger.warning("Web interface already running")
            return True
        
        self.is_running = True
        
        # Start update thread
        self.update_thread = threading.Thread(target=self._status_update_loop, daemon=True)
        self.update_thread.start()
        
        # Start server thread
        if self.enable_https and self.cert_file and self.key_file:
            # HTTPS
            context = (self.cert_file, self.key_file)
            server_kwargs = {
                "host": self.host,
                "port": self.port,
                "ssl_context": context,
                "debug": self.debug,
                "use_reloader": False
            }
        else:
            # HTTP
            server_kwargs = {
                "host": self.host,
                "port": self.port,
                "debug": self.debug,
                "use_reloader": False
            }
        
        # Use socketio instead of standard Flask for better real-time capabilities
        self.server_thread = threading.Thread(
            target=self.socketio.run,
            args=(self.app,),
            kwargs=server_kwargs,
            daemon=True
        )
        self.server_thread.start()
        
        self.logger.info(f"Web interface started on {'https' if self.enable_https else 'http'}://{self.host}:{self.port}")
        return True
    
    def stop(self) -> None:
        """Stop the web interface server"""
        self.is_running = False
        
        # Stop threads
        if self.update_thread:
            self.update_thread.join(timeout=2.0)
        
        # Server thread cannot be easily stopped, will be terminated when process exits
        self.logger.info("Web interface stopped")
