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
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
MODULES_DIR="${SCRIPT_DIR}/ubuntu_install_modules"

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

# Source all module scripts
source_modules() {
    log "Sourcing module scripts..."
    
    # Check if modules directory exists
    if [ ! -d "${MODULES_DIR}" ]; then
        log "ERROR: Modules directory not found at ${MODULES_DIR}"
        exit 1
    fi
    
    # Source core installation module
    if [ -f "${MODULES_DIR}/core_install.sh" ]; then
        source "${MODULES_DIR}/core_install.sh"
    else
        log "ERROR: Core installation module not found"
        exit 1
    fi
    
    # Source web app template module
    if [ -f "${MODULES_DIR}/web_app_template.sh" ]; then
        source "${MODULES_DIR}/web_app_template.sh"
    else
        log "ERROR: Web app template module not found"
        exit 1
    fi
    
    # Source HTML templates module
    if [ -f "${MODULES_DIR}/html_templates.sh" ]; then
        source "${MODULES_DIR}/html_templates.sh"
    else
        log "ERROR: HTML templates module not found"
        exit 1
    fi
    
    # Source config manager module
    if [ -f "${MODULES_DIR}/config_manager.sh" ]; then
        source "${MODULES_DIR}/config_manager.sh"
    else
        log "ERROR: Config manager module not found"
        exit 1
    fi
    
    # Source service setup module
    if [ -f "${MODULES_DIR}/service_setup.sh" ]; then
        source "${MODULES_DIR}/service_setup.sh"
    else
        log "ERROR: Service setup module not found"
        exit 1
    fi
    
    log "All modules sourced successfully."
}

# Main installation function
main() {
    # Clear or create log file
    > "$LOG_FILE"
    
    log "Starting Robot Mower Control Panel installation..."
    
    # Check if running as root
    check_root
    
    # Source all module scripts
    source_modules
    
    # Update system and install dependencies
    update_system
    install_dependencies
    
    # Create installation directory
    create_install_dir
    
    # Clone repository and set up files
    clone_repository
    
    # Create web app and templates
    create_web_app "${INSTALL_DIR}"
    create_html_templates "${INSTALL_DIR}"
    
    # Create configuration manager and configuration files
    create_config_manager "${INSTALL_DIR}"
    create_default_config "${INSTALL_DIR}"
    
    # Create requirements and setup Python environment
    create_requirements_file "${INSTALL_DIR}"
    setup_python_env
    
    # Create launcher and setup services
    create_launcher "${INSTALL_DIR}" "${CONTROL_PANEL_PORT}"
    setup_systemd_service "${INSTALL_DIR}" "${SERVICE_NAME}"
    setup_nginx "${INSTALL_DIR}" "${CONTROL_PANEL_PORT}"
    
    # Check installation and print summary
    check_installation
    print_summary
    
    log "Installation completed!"
}

# Run main function if the script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
