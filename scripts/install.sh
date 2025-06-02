#!/bin/bash
# Prism DNS Server Installation Script (SCRUM-18)
# Automated installation and setup for production deployment

set -e  # Exit on any error

# Configuration
INSTALL_DIR="/opt/prism-dns"
CONFIG_DIR="/etc/prism"
LOG_DIR="/var/log/prism"
DATA_DIR="/var/lib/prism"
SERVICE_USER="prism"
SERVICE_GROUP="prism"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check OS
    if [[ ! -f /etc/os-release ]]; then
        log_error "Unsupported operating system"
        exit 1
    fi
    
    source /etc/os-release
    log_info "Operating System: $PRETTY_NAME"
    
    # Check Python 3.8+
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi
    
    local python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    log_info "Python version: $python_version"
    
    # Check if version is 3.8+
    if [[ $(echo "$python_version 3.8" | tr " " "\n" | sort -V | head -n1) != "3.8" ]]; then
        log_error "Python 3.8 or higher is required"
        exit 1
    fi
    
    # Check systemd
    if ! command -v systemctl &> /dev/null; then
        log_warning "systemd not found, service installation will be skipped"
    fi
    
    log_success "Prerequisites check passed"
}

# Function to create system user
create_user() {
    log_info "Creating system user: $SERVICE_USER"
    
    if id "$SERVICE_USER" &>/dev/null; then
        log_info "User $SERVICE_USER already exists"
    else
        useradd -r -s /bin/false -d "$INSTALL_DIR" "$SERVICE_USER"
        log_success "User $SERVICE_USER created"
    fi
}

# Function to create directories
create_directories() {
    log_info "Creating directories..."
    
    local dirs=("$INSTALL_DIR" "$CONFIG_DIR" "$LOG_DIR" "$DATA_DIR")
    
    for dir in "${dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            log_info "Created directory: $dir"
        fi
    done
    
    # Set ownership
    chown -R "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR" "$LOG_DIR" "$DATA_DIR"
    chown root:root "$CONFIG_DIR"
    chmod 755 "$CONFIG_DIR"
    
    log_success "Directories created and configured"
}

# Function to install Python dependencies
install_dependencies() {
    log_info "Installing Python dependencies..."
    
    # Create virtual environment
    python3 -m venv "$INSTALL_DIR/venv"
    source "$INSTALL_DIR/venv/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install dependencies (assuming requirements.txt is in project root)
    if [[ -f "requirements.txt" ]]; then
        pip install -r requirements.txt
        log_success "Dependencies installed from requirements.txt"
    else
        # Install common dependencies
        pip install fastapi uvicorn pydantic pyyaml
        log_success "Basic dependencies installed"
    fi
    
    deactivate
}

# Function to copy application files
copy_application() {
    log_info "Copying application files..."
    
    # Copy server code
    cp -r server/ "$INSTALL_DIR/"
    
    # Copy configuration
    if [[ -f "config/server.example.yaml" ]]; then
        cp config/server.example.yaml "$CONFIG_DIR/server.yaml"
        log_info "Configuration template copied to $CONFIG_DIR/server.yaml"
    fi
    
    # Copy startup scripts
    cp scripts/start_server.sh "$INSTALL_DIR/"
    chmod +x "$INSTALL_DIR/start_server.sh"
    
    # Set ownership
    chown -R "$SERVICE_USER:$SERVICE_GROUP" "$INSTALL_DIR"
    
    log_success "Application files copied"
}

# Function to install systemd service
install_service() {
    if ! command -v systemctl &> /dev/null; then
        log_warning "systemd not available, skipping service installation"
        return
    fi
    
    log_info "Installing systemd service..."
    
    # Update service file paths
    sed -e "s|/opt/prism-dns|$INSTALL_DIR|g" \
        -e "s|/etc/prism|$CONFIG_DIR|g" \
        -e "s|User=prism|User=$SERVICE_USER|g" \
        -e "s|Group=prism|Group=$SERVICE_GROUP|g" \
        scripts/prism-server.service > /etc/systemd/system/prism-server.service
    
    # Reload systemd
    systemctl daemon-reload
    
    # Enable service
    systemctl enable prism-server
    
    log_success "Systemd service installed and enabled"
}

# Function to configure firewall
configure_firewall() {
    log_info "Configuring firewall..."
    
    if command -v ufw &> /dev/null; then
        ufw allow 8080/tcp comment "Prism DNS TCP"
        ufw allow 8081/tcp comment "Prism DNS API"
        log_success "UFW firewall rules added"
    elif command -v firewall-cmd &> /dev/null; then
        firewall-cmd --permanent --add-port=8080/tcp
        firewall-cmd --permanent --add-port=8081/tcp
        firewall-cmd --reload
        log_success "firewalld rules added"
    else
        log_warning "No supported firewall found, please open ports 8080 and 8081 manually"
    fi
}

# Function to show installation summary
show_summary() {
    log_success "Prism DNS Server installation completed!"
    echo
    log_info "Installation Summary:"
    echo "  - Application directory: $INSTALL_DIR"
    echo "  - Configuration file: $CONFIG_DIR/server.yaml"
    echo "  - Log directory: $LOG_DIR"
    echo "  - Data directory: $DATA_DIR"
    echo "  - Service user: $SERVICE_USER"
    echo
    log_info "Next Steps:"
    echo "  1. Edit configuration: sudo nano $CONFIG_DIR/server.yaml"
    echo "  2. Start service: sudo systemctl start prism-server"
    echo "  3. Check status: sudo systemctl status prism-server"
    echo "  4. View logs: sudo journalctl -u prism-server -f"
    echo
    log_info "Service URLs:"
    echo "  - TCP Server: localhost:8080"
    echo "  - API Server: http://localhost:8081"
    echo "  - Health Check: http://localhost:8081/health"
}

# Main installation function
main() {
    log_info "Prism DNS Server Installation Script"
    log_info "Installing to: $INSTALL_DIR"
    echo
    
    check_root
    check_prerequisites
    create_user
    create_directories
    install_dependencies
    copy_application
    install_service
    configure_firewall
    show_summary
}

# Run installation
main "$@"