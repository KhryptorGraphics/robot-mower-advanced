#!/bin/bash

# Robot Mower Advanced - Raspberry Pi Installation Script
#
# This script installs all dependencies and sets up the Robot Mower
# Advanced software on a Raspberry Pi. It configures the system for
# automatic startup and creates all required directories.
#

set -e  # Exit immediately if a command exits with non-zero status
INSTALL_DIR="/home/pi/robot-mower-advanced"
LOG_FILE="/tmp/robot_mower_install.log"
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
MODULES_DIR="${SCRIPT_DIR}/raspberry_pi_modules"

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
    
    # Source dependencies module
    if [ -f "${MODULES_DIR}/dependencies.sh" ]; then
        source "${MODULES_DIR}/dependencies.sh"
    else
        log "ERROR: Dependencies module not found"
        exit 1
    fi
    
    # Source Hailo setup module
    if [ -f "${MODULES_DIR}/hailo_setup.sh" ]; then
        source "${MODULES_DIR}/hailo_setup.sh"
    else
        log "ERROR: Hailo setup module not found"
        exit 1
    fi
    
    # Source SLAM and path planning module
    if [ -f "${MODULES_DIR}/slam_path_planning.sh" ]; then
        source "${MODULES_DIR}/slam_path_planning.sh"
    else
        log "ERROR: SLAM and path planning module not found"
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

# Function to handle interactive setup
interactive_setup() {
    echo "Robot Mower Advanced - Interactive Setup"
    echo "---------------------------------------"
    echo "This script will guide you through the installation process."
    echo ""

    read -p "Would you like to proceed with installation? (y/n): " continue_install
    if [[ ! "$continue_install" =~ ^[Yy]$ ]]; then
        echo "Installation aborted."
        exit 0
    fi

    # Optional configurations
    read -p "Would you like to set up HTTPS for the web interface? (y/n): " setup_https_option
    read -p "Would you like to enable SLAM and advanced path planning? (y/n): " setup_slam_option
    read -p "Would you like to install Hailo NPU support? (y/n): " setup_hailo_option
    read -p "Would you like to configure network settings? (y/n): " setup_network_option

    # Run installation steps
    check_root
    update_system
    install_dependencies
    enable_interfaces
    add_user_to_groups
    clone_repository
    create_directories
    create_default_config
    
    # Configure Hailo if requested
    if [[ "$setup_hailo_option" =~ ^[Yy]$ ]]; then
        install_hailo_sdk
        configure_hailo
    fi
    
    # Configure SLAM if requested
    if [[ "$setup_slam_option" =~ ^[Yy]$ ]]; then
        configure_slam_and_path_planning
        verify_slam_requirements
        setup_slam_directories
    fi
    
    # Setup services
    create_service
    setup_web_interface
    create_startup_scripts
    verify_services

    # Optional steps
    if [[ "$setup_network_option" =~ ^[Yy]$ ]]; then
        setup_network
    fi

    if [[ "$setup_https_option" =~ ^[Yy]$ ]]; then
        setup_https
    fi

    # Final steps
    print_summary
    finalize
}

# Main execution function
main() {
    # Clear or create log file
    > "$LOG_FILE"
    
    log "Starting Robot Mower Advanced installation..."
    
    # Source all module scripts
    source_modules
    
    # Begin interactive setup
    echo "Robot Mower Advanced Installation"
    echo "================================="
    echo "This script will install the Robot Mower Advanced software on your Raspberry Pi."
    echo "Log file: $LOG_FILE"
    echo ""

    interactive_setup
}

# Run main function if the script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
