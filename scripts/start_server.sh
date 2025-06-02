#!/bin/bash
# Prism DNS Server Startup Script (SCRUM-18)
# Cross-platform startup script for production deployment

set -e  # Exit on any error

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default configuration
DEFAULT_CONFIG="$PROJECT_ROOT/config/server.yaml"
DEFAULT_VENV="$PROJECT_ROOT/venv"

# Parse command line arguments
CONFIG_FILE="$DEFAULT_CONFIG"
VENV_PATH="$DEFAULT_VENV"
DAEMON_MODE=false
PID_FILE=""

show_help() {
    cat << EOF
Prism DNS Server Startup Script

USAGE:
    $0 [OPTIONS]

OPTIONS:
    -c, --config FILE    Configuration file path (default: $DEFAULT_CONFIG)
    -v, --venv PATH      Virtual environment path (default: $DEFAULT_VENV)
    -d, --daemon         Run as daemon (background process)
    -p, --pid FILE       PID file for daemon mode
    -h, --help           Show this help message

EXAMPLES:
    $0                                    # Start with default configuration
    $0 -c /etc/prism/server.yaml         # Start with custom config
    $0 -d -p /var/run/prism-server.pid   # Start as daemon
    
ENVIRONMENT VARIABLES:
    PRISM_SERVER_TCP_PORT     Override TCP server port
    PRISM_SERVER_API_PORT     Override API server port
    PRISM_DATABASE_PATH       Override database file path
    PRISM_LOGGING_LEVEL       Override logging level
    
EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -v|--venv)
            VENV_PATH="$2"
            shift 2
            ;;
        -d|--daemon)
            DAEMON_MODE=true
            shift
            ;;
        -p|--pid)
            PID_FILE="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            show_help
            exit 1
            ;;
    esac
done

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check Python version
    if ! command -v python3 &> /dev/null; then
        echo "Error: Python 3 is required but not installed" >&2
        exit 1
    fi
    
    local python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    log "Python version: $python_version"
    
    # Check virtual environment
    if [[ ! -d "$VENV_PATH" ]]; then
        echo "Error: Virtual environment not found at $VENV_PATH" >&2
        echo "Please create it with: python3 -m venv $VENV_PATH" >&2
        exit 1
    fi
    
    # Check configuration file
    if [[ ! -f "$CONFIG_FILE" ]]; then
        if [[ "$CONFIG_FILE" == "$DEFAULT_CONFIG" ]]; then
            log "Configuration file not found, using defaults"
        else
            echo "Error: Configuration file not found: $CONFIG_FILE" >&2
            exit 1
        fi
    else
        log "Using configuration: $CONFIG_FILE"
    fi
    
    log "Prerequisites check passed"
}

# Function to activate virtual environment
activate_venv() {
    log "Activating virtual environment..."
    source "$VENV_PATH/bin/activate"
    
    # Check if server module is available
    if ! python3 -c "import server.main" &> /dev/null; then
        echo "Error: Server module not found. Please install dependencies:" >&2
        echo "  pip install -r requirements.txt" >&2
        exit 1
    fi
    
    log "Virtual environment activated"
}

# Function to start server
start_server() {
    cd "$PROJECT_ROOT"
    
    local cmd="python3 -m server.main"
    
    # Add config file if it exists
    if [[ -f "$CONFIG_FILE" ]]; then
        cmd="$cmd --config '$CONFIG_FILE'"
    fi
    
    if [[ "$DAEMON_MODE" == true ]]; then
        log "Starting Prism DNS Server as daemon..."
        
        # Setup daemon mode
        local log_file="$PROJECT_ROOT/server_daemon.log"
        
        if [[ -n "$PID_FILE" ]]; then
            # Start as daemon with PID file
            nohup $cmd > "$log_file" 2>&1 &
            local server_pid=$!
            echo $server_pid > "$PID_FILE"
            log "Server started as daemon with PID $server_pid"
            log "PID file: $PID_FILE"
            log "Log file: $log_file"
        else
            # Start as daemon without PID file
            nohup $cmd > "$log_file" 2>&1 &
            local server_pid=$!
            log "Server started as daemon with PID $server_pid"
            log "Log file: $log_file"
        fi
    else
        log "Starting Prism DNS Server..."
        log "Press Ctrl+C to stop"
        
        # Start in foreground
        exec $cmd
    fi
}

# Function to handle cleanup on exit
cleanup() {
    if [[ "$DAEMON_MODE" == false ]]; then
        log "Shutting down..."
    fi
}

# Setup signal handlers
trap cleanup EXIT

# Main execution
main() {
    log "Prism DNS Server Startup Script"
    log "Project root: $PROJECT_ROOT"
    
    check_prerequisites
    activate_venv
    start_server
}

# Run main function
main "$@"