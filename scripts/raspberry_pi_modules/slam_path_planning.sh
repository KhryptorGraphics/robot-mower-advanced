#!/bin/bash

# SLAM and Path Planning module for the Raspberry Pi
# This script is called by the main install_raspberry_pi.sh script

# Function to configure SLAM and Advanced Path Planning
configure_slam_and_path_planning() {
    log "Configuring SLAM and Advanced Path Planning settings..."
    
    if [ -f "${INSTALL_DIR}/config/local_config.yaml" ]; then
        # Check if SLAM section already exists
        if ! grep -q "^slam:" "${INSTALL_DIR}/config/local_config.yaml"; then
            # Add SLAM and path planning configuration to local config
            cat >> "${INSTALL_DIR}/config/local_config.yaml" << EOF

# SLAM configuration
slam:
  enabled: true
  map_resolution: 0.05  # meters per pixel
  map_size: 100.0  # size in meters
  add_pose_interval: 1.0  # seconds
  mapping_interval: 0.5  # seconds
  localization_interval: 0.1  # seconds
  optimization_interval: 5.0  # seconds
  gps_weight: 0.7
  imu_weight: 0.8
  odometry_weight: 0.5
  visual_odometry_scale: 0.01

# Navigation configuration
navigation:
  path_planning:
    enabled: true
    safety_margin_m: 0.2  # meters
    edge_detection_enabled: true
    edge_follow_distance_m: 0.1  # meters
  obstacle_avoidance:
    enabled: true
    detection_range_m: 3.0  # meters
    stop_distance_m: 0.5  # meters
  pattern: "adaptive"  # parallel, spiral, zigzag, perimeter_first, adaptive, custom
  overlap_percent: 15.0
  cutting_direction_degrees: 0.0
EOF
            log "Added SLAM and Path Planning configuration to local_config.yaml"
        fi
    fi
}

# Function to verify SLAM and path planning requirements
verify_slam_requirements() {
    log "Verifying SLAM and path planning requirements..."
    
    if [ -d "${INSTALL_DIR}" ]; then
        # Check if Python packages are installed
        cd "${INSTALL_DIR}"
        . venv/bin/activate
        
        # Check if required libraries are available
        MISSING_PKGS=()
        for pkg in numpy matplotlib scipy g2o-python shapely; do
            if ! pip freeze | grep -i "$pkg" > /dev/null; then
                MISSING_PKGS+=("$pkg")
            fi
        done
        
        if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
            log "Installing missing SLAM dependencies: ${MISSING_PKGS[*]}"
            pip install ${MISSING_PKGS[@]} >> "$LOG_FILE" 2>&1
        else
            log "All SLAM dependencies are installed."
        fi
        
        deactivate
    else
        log "Installation directory not found. Cannot verify SLAM requirements."
    fi
}

# Function to setup SLAM data directories
setup_slam_directories() {
    log "Setting up SLAM data directories..."
    
    if [ -d "${INSTALL_DIR}" ]; then
        # Create necessary directories
        mkdir -p "${INSTALL_DIR}/data/slam_maps"
        mkdir -p "${INSTALL_DIR}/data/path_plans"
        mkdir -p "${INSTALL_DIR}/data/calibration"
        
        # Set correct permissions
        chown -R pi:pi "${INSTALL_DIR}/data"
        
        log "SLAM data directories set up successfully."
    else
        log "Installation directory not found. Cannot set up SLAM directories."
    fi
}
