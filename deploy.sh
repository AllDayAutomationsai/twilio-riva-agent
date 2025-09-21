#!/bin/bash
#
# Deployment Script for Twilio RIVA Voice Agent
# Handles installation, configuration, and management
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BASE_DIR="/home/ubuntu/twilio_riva_agent"
SYSTEMD_DIR="$BASE_DIR/systemd"
SERVICE_NAME="twilio-riva-agent"
VENV_DIR="$BASE_DIR/venv"

# Functions
print_status() {
    echo -e "${GREEN}[*]${NC} $1"
}

print_error() {
    echo -e "${RED}[!]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

check_root() {
    if [ "$EUID" -eq 0 ]; then
        print_error "This script should not be run as root for security reasons"
        exit 1
    fi
}

check_dependencies() {
    print_status "Checking dependencies..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        exit 1
    fi
    
    # Check npm
    if ! command -v npm &> /dev/null; then
        print_warning "npm is not installed. Installing..."
        sudo apt update && sudo apt install -y npm
    fi
    
    # Check Docker (for RIVA)
    if ! command -v docker &> /dev/null; then
        print_warning "Docker is not installed. RIVA services may not work."
    fi
    
    # Check ngrok
    if ! command -v ngrok &> /dev/null; then
        print_warning "ngrok is not installed. Installing..."
        curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
        echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
        sudo apt update && sudo apt install ngrok
    fi
    
    print_status "Dependencies checked"
}

setup_environment() {
    print_status "Setting up Python virtual environment..."
    
    if [ ! -d "$VENV_DIR" ]; then
        python3 -m venv "$VENV_DIR"
    fi
    
    source "$VENV_DIR/bin/activate"
    
    print_status "Installing Python packages..."
    pip install --upgrade pip
    
    if [ -f "$BASE_DIR/requirements.txt" ]; then
        pip install -r "$BASE_DIR/requirements.txt"
    fi
    
    # Install additional packages for monitoring and performance
    pip install psutil pyyaml
    
    print_status "Python environment ready"
}

configure_env() {
    print_status "Configuring environment variables..."
    
    if [ ! -f "$BASE_DIR/.env" ]; then
        print_warning ".env file not found. Creating from template..."
        if [ -f "$BASE_DIR/.env.example" ]; then
            cp "$BASE_DIR/.env.example" "$BASE_DIR/.env"
            print_warning "Please edit $BASE_DIR/.env with your actual credentials"
            read -p "Press enter to continue after editing .env file..."
        else
            print_error ".env.example not found. Please create .env file manually"
            exit 1
        fi
    fi
    
    # Validate required environment variables
    source "$BASE_DIR/.env"
    
    required_vars=("TWILIO_ACCOUNT_SID" "TWILIO_AUTH_TOKEN" "OPENAI_API_KEY")
    missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        print_error "Missing required environment variables: ${missing_vars[*]}"
        print_error "Please edit $BASE_DIR/.env file"
        exit 1
    fi
    
    print_status "Environment configured"
}

create_directories() {
    print_status "Creating necessary directories..."
    
    mkdir -p "$BASE_DIR/logs"
    mkdir -p "$BASE_DIR/pids"
    mkdir -p "$BASE_DIR/config"
    mkdir -p "$BASE_DIR/data"
    
    print_status "Directories created"
}

install_service() {
    print_status "Installing systemd service..."
    
    # Copy service file
    sudo cp "$SYSTEMD_DIR/twilio-riva-agent.service" "/etc/systemd/system/${SERVICE_NAME}.service"
    
    # Reload systemd
    sudo systemctl daemon-reload
    
    # Enable service (but don't start yet)
    sudo systemctl enable "$SERVICE_NAME"
    
    print_status "Service installed and enabled"
}

start_service() {
    print_status "Starting service..."
    
    sudo systemctl start "$SERVICE_NAME"
    
    # Wait for service to start
    sleep 5
    
    if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
        print_status "Service started successfully"
    else
        print_error "Service failed to start"
        sudo systemctl status "$SERVICE_NAME" --no-pager
        exit 1
    fi
}

stop_service() {
    print_status "Stopping service..."
    
    sudo systemctl stop "$SERVICE_NAME"
    
    print_status "Service stopped"
}

restart_service() {
    print_status "Restarting service..."
    
    sudo systemctl restart "$SERVICE_NAME"
    
    # Wait for service to restart
    sleep 5
    
    if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
        print_status "Service restarted successfully"
    else
        print_error "Service failed to restart"
        sudo systemctl status "$SERVICE_NAME" --no-pager
        exit 1
    fi
}

status_service() {
    print_status "Service status:"
    sudo systemctl status "$SERVICE_NAME" --no-pager
    
    # Check if monitoring is available
    if curl -s http://localhost:9090/health > /dev/null 2>&1; then
        print_status "Health check:"
        curl -s http://localhost:9090/health | python3 -m json.tool
    fi
}

uninstall_service() {
    print_status "Uninstalling service..."
    
    # Stop service if running
    if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
        sudo systemctl stop "$SERVICE_NAME"
    fi
    
    # Disable and remove service
    sudo systemctl disable "$SERVICE_NAME"
    sudo rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
    sudo systemctl daemon-reload
    
    print_status "Service uninstalled"
}

test_deployment() {
    print_status "Running deployment tests..."
    
    # Check if services are accessible
    services=(
        "http://localhost:8080"  # WebSocket
        "http://localhost:5000"  # TwiML
        "http://localhost:9090"  # Monitoring
    )
    
    for service in "${services[@]}"; do
        if curl -s "$service" > /dev/null 2>&1; then
            print_status "$service is accessible"
        else
            print_warning "$service is not accessible"
        fi
    done
    
    # Check health endpoint
    if curl -s http://localhost:9090/health > /dev/null 2>&1; then
        health_status=$(curl -s http://localhost:9090/health | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])")
        print_status "Health status: $health_status"
    fi
    
    print_status "Deployment tests completed"
}

show_logs() {
    print_status "Showing recent logs..."
    
    if [ -f "$BASE_DIR/logs/service.log" ]; then
        tail -n 50 "$BASE_DIR/logs/service.log"
    else
        sudo journalctl -u "$SERVICE_NAME" -n 50 --no-pager
    fi
}

backup_config() {
    print_status "Creating configuration backup..."
    
    backup_dir="$BASE_DIR/backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    # Backup important files
    cp "$BASE_DIR/.env" "$backup_dir/" 2>/dev/null || true
    cp -r "$BASE_DIR/config" "$backup_dir/" 2>/dev/null || true
    
    print_status "Backup created at $backup_dir"
}

# Main menu
show_menu() {
    echo ""
    echo "Twilio RIVA Voice Agent Deployment Manager"
    echo "==========================================="
    echo "1. Install (full setup)"
    echo "2. Start service"
    echo "3. Stop service"
    echo "4. Restart service"
    echo "5. Show status"
    echo "6. Show logs"
    echo "7. Test deployment"
    echo "8. Backup configuration"
    echo "9. Uninstall service"
    echo "0. Exit"
    echo ""
}

# Parse command line arguments
if [ $# -eq 1 ]; then
    case "$1" in
        install)
            check_root
            check_dependencies
            setup_environment
            configure_env
            create_directories
            install_service
            start_service
            test_deployment
            ;;
        start)
            start_service
            ;;
        stop)
            stop_service
            ;;
        restart)
            restart_service
            ;;
        status)
            status_service
            ;;
        logs)
            show_logs
            ;;
        test)
            test_deployment
            ;;
        backup)
            backup_config
            ;;
        uninstall)
            uninstall_service
            ;;
        *)
            print_error "Unknown command: $1"
            echo "Usage: $0 {install|start|stop|restart|status|logs|test|backup|uninstall}"
            exit 1
            ;;
    esac
else
    # Interactive menu
    while true; do
        show_menu
        read -p "Select option: " option
        
        case $option in
            1)
                check_root
                check_dependencies
                setup_environment
                configure_env
                create_directories
                install_service
                start_service
                test_deployment
                ;;
            2)
                start_service
                ;;
            3)
                stop_service
                ;;
            4)
                restart_service
                ;;
            5)
                status_service
                ;;
            6)
                show_logs
                ;;
            7)
                test_deployment
                ;;
            8)
                backup_config
                ;;
            9)
                uninstall_service
                ;;
            0)
                exit 0
                ;;
            *)
                print_error "Invalid option"
                ;;
        esac
        
        read -p "Press enter to continue..."
    done
fi
