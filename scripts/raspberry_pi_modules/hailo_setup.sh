#!/bin/bash

# Hailo NPU setup module for the Raspberry Pi
# This script is called by the main install_raspberry_pi.sh script

# Function to install Hailo NPU SDK
install_hailo_sdk() {
    log "Setting up Hailo NPU HAT..."
    
    # Check if Hailo is already installed
    if python3 -c "import hailo" &>/dev/null; then
        log "Hailo SDK already installed, skipping."
        return 0
    fi
    
    log "Installing Hailo SDK dependencies..."
    apt-get install -y libssl-dev libusb-1.0-0-dev libudev-dev >> "$LOG_FILE" 2>&1
    
    # Create directory for Hailo software
    HAILO_DIR="/opt/hailo"
    mkdir -p "${HAILO_DIR}"
    mkdir -p "${HAILO_DIR}/models"
    
    # Download Hailo SDK
    log "Downloading Hailo SDK..."
    cd /tmp
    
    # Download HailoRT package (adjust URL as needed for the latest version)
    wget -q https://hailo.ai/developer/hailort/download/hailort_latest_arm.deb -O hailort.deb >> "$LOG_FILE" 2>&1
    
    # Install HailoRT
    log "Installing Hailo Runtime..."
    apt-get install -y ./hailort.deb >> "$LOG_FILE" 2>&1
    
    # Install Hailo Python API
    log "Installing Hailo Python API..."
    if [ -d "${INSTALL_DIR}" ]; then
        cd "${INSTALL_DIR}"
        . venv/bin/activate
        pip install hailo-ai >> "$LOG_FILE" 2>&1
        deactivate
    fi
    
    # Setup udev rules for Hailo
    log "Setting up udev rules for Hailo..."
    if [ ! -f "/etc/udev/rules.d/99-hailo.rules" ]; then
        echo 'SUBSYSTEM=="usb", ATTRS{idVendor}=="03e7", MODE="0666"' > /etc/udev/rules.d/99-hailo.rules
        udevadm control --reload-rules && udevadm trigger
    fi
    
    # Download a sample model for testing
    log "Downloading YOLOv5 model for Hailo..."
    mkdir -p "${HAILO_DIR}/models"
    wget -q https://hailo.ai/developer/models/yolov5/yolov5m_wo_spp_60p.hef -O "${HAILO_DIR}/models/yolov5m.hef" >> "$LOG_FILE" 2>&1
    
    log "Hailo NPU HAT setup completed"
}

# Function to configure Hailo NPU
configure_hailo() {
    log "Configuring Hailo NPU settings..."
    
    if [ -f "${INSTALL_DIR}/config/local_config.yaml" ]; then
        # Check if hailo section already exists
        if ! grep -q "^hailo:" "${INSTALL_DIR}/config/local_config.yaml"; then
            # Add Hailo configuration to local config
            cat >> "${INSTALL_DIR}/config/local_config.yaml" << EOF

# Hailo NPU configuration
hailo:
  enabled: true
  model_path: "/opt/hailo/models/yolov5m.hef"
  confidence_threshold: 0.5
  input_shape: [640, 640]
  class_filter: ["person", "bicycle", "car", "motorcycle", "dog", "cat", "potted plant"]

# Camera configuration
camera:
  enabled: true
  width: 640
  height: 480
  fps: 30
  index: 0

# Object detection configuration
object_detection:
  enabled: true
  safety_critical_zone: 1.5  # meters
  obstacle_zone: 3.0  # meters
EOF
            log "Added Hailo NPU configuration to local_config.yaml"
        fi
    fi
}
