#!/bin/bash
# DNS Deployment Rollback Script (SCRUM-125)
# Provides safe rollback procedures for PowerDNS integration

set -e

# Configuration
DEPLOYMENT_DIR="$HOME/prism-deployment"
BACKUP_DIR="$HOME/prism-dns-backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Function to check if running in production
check_environment() {
    if [[ ! -d "$DEPLOYMENT_DIR" ]]; then
        error "Deployment directory not found: $DEPLOYMENT_DIR"
        exit 1
    fi
    
    if [[ ! -f "$DEPLOYMENT_DIR/docker-compose.production.yml" ]]; then
        error "Production docker-compose file not found"
        exit 1
    fi
    
    log "Environment check passed"
}

# Function to create backup before rollback
create_backup() {
    log "Creating backup before rollback..."
    
    mkdir -p "$BACKUP_DIR/rollback_$TIMESTAMP"
    
    # Backup current configuration
    if [[ -f "$DEPLOYMENT_DIR/.env.production" ]]; then
        cp "$DEPLOYMENT_DIR/.env.production" "$BACKUP_DIR/rollback_$TIMESTAMP/"
    fi
    
    if [[ -f "$DEPLOYMENT_DIR/.env.powerdns" ]]; then
        cp "$DEPLOYMENT_DIR/.env.powerdns" "$BACKUP_DIR/rollback_$TIMESTAMP/"
    fi
    
    # Backup PowerDNS data if exists
    if docker compose -f "$DEPLOYMENT_DIR/docker-compose.powerdns.yml" ps | grep -q powerdns; then
        log "Backing up PowerDNS data..."
        docker compose -f "$DEPLOYMENT_DIR/docker-compose.powerdns.yml" exec powerdns-db \
            pg_dump -U powerdns powerdns > "$BACKUP_DIR/rollback_$TIMESTAMP/powerdns_backup.sql" || true
    fi
    
    # Backup application database
    if [[ -f "$DEPLOYMENT_DIR/data/prism.db" ]]; then
        cp "$DEPLOYMENT_DIR/data/prism.db" "$BACKUP_DIR/rollback_$TIMESTAMP/"
    fi
    
    success "Backup created at: $BACKUP_DIR/rollback_$TIMESTAMP"
}

# Function to disable PowerDNS integration
disable_powerdns() {
    log "Disabling PowerDNS integration..."
    
    cd "$DEPLOYMENT_DIR"
    
    # Update environment variables to disable PowerDNS
    if [[ -f ".env.production" ]]; then
        # Backup current env
        cp .env.production .env.production.backup_$TIMESTAMP
        
        # Set PowerDNS to disabled
        sed -i 's/POWERDNS_ENABLED=true/POWERDNS_ENABLED=false/' .env.production
        sed -i 's/POWERDNS_FEATURE_FLAG_PERCENTAGE=[0-9]*/POWERDNS_FEATURE_FLAG_PERCENTAGE=0/' .env.production
        
        success "PowerDNS disabled in configuration"
    else
        warn "No .env.production file found"
    fi
}

# Function to stop PowerDNS services
stop_powerdns_services() {
    log "Stopping PowerDNS services..."
    
    cd "$DEPLOYMENT_DIR"
    
    if [[ -f "docker-compose.powerdns.yml" ]]; then
        # Stop PowerDNS containers
        docker compose -f docker-compose.powerdns.yml down || true
        
        # Remove PowerDNS volumes if requested
        if [[ "$1" == "--remove-volumes" ]]; then
            warn "Removing PowerDNS volumes (data will be lost)..."
            docker volume rm prism-dns_powerdns-db-data 2>/dev/null || true
        fi
        
        success "PowerDNS services stopped"
    else
        warn "PowerDNS compose file not found"
    fi
}

# Function to restart main application
restart_application() {
    log "Restarting main application..."
    
    cd "$DEPLOYMENT_DIR"
    
    # Restart main services
    docker compose -f docker-compose.production.yml restart
    
    # Wait for services to stabilize
    log "Waiting for services to stabilize..."
    sleep 30
    
    # Health check
    if curl -f -m 10 -s http://localhost:8081/api/health > /dev/null; then
        success "Application restarted successfully"
    else
        error "Application health check failed"
        return 1
    fi
}

# Function to verify rollback
verify_rollback() {
    log "Verifying rollback..."
    
    # Check that PowerDNS is not running
    if docker compose -f "$DEPLOYMENT_DIR/docker-compose.powerdns.yml" ps 2>/dev/null | grep -q powerdns; then
        warn "PowerDNS containers are still running"
    else
        success "PowerDNS containers stopped"
    fi
    
    # Check DNS config endpoint
    if curl -f -s http://localhost:8081/api/dns/config | grep -q '"powerdns_enabled":false'; then
        success "PowerDNS integration disabled in API"
    else
        warn "PowerDNS may still be enabled in API"
    fi
    
    # Check main application health
    if curl -f -m 10 -s http://localhost:8081/api/health > /dev/null; then
        success "Main application is healthy"
    else
        error "Main application health check failed"
        return 1
    fi
    
    log "Rollback verification completed"
}

# Function to show rollback status
show_status() {
    echo ""
    echo "============================================="
    echo "DNS DEPLOYMENT ROLLBACK STATUS"
    echo "============================================="
    echo ""
    
    # Application status
    echo "Main Application:"
    if docker compose -f "$DEPLOYMENT_DIR/docker-compose.production.yml" ps | grep -q "prism-server.*Up"; then
        echo "  ✅ Prism Server: Running"
    else
        echo "  ❌ Prism Server: Not Running"
    fi
    
    if docker compose -f "$DEPLOYMENT_DIR/docker-compose.production.yml" ps | grep -q "prism-nginx.*Up"; then
        echo "  ✅ Nginx: Running"
    else
        echo "  ❌ Nginx: Not Running"
    fi
    
    # PowerDNS status
    echo ""
    echo "PowerDNS Integration:"
    if docker compose -f "$DEPLOYMENT_DIR/docker-compose.powerdns.yml" ps 2>/dev/null | grep -q powerdns; then
        echo "  ⚠️  PowerDNS: Still Running (manual cleanup needed)"
    else
        echo "  ✅ PowerDNS: Stopped"
    fi
    
    # Configuration status
    echo ""
    echo "Configuration:"
    if [[ -f "$DEPLOYMENT_DIR/.env.production" ]] && grep -q "POWERDNS_ENABLED=false" "$DEPLOYMENT_DIR/.env.production"; then
        echo "  ✅ PowerDNS: Disabled"
    else
        echo "  ⚠️  PowerDNS: May still be enabled"
    fi
    
    echo ""
    echo "============================================="
}

# Function to show help
show_help() {
    echo "DNS Deployment Rollback Script"
    echo ""
    echo "Usage: $0 [OPTIONS] <COMMAND>"
    echo ""
    echo "Commands:"
    echo "  disable-only     Disable PowerDNS without stopping services"
    echo "  stop-services    Stop PowerDNS services only"
    echo "  full-rollback    Complete rollback (disable + stop + restart)"
    echo "  status          Show current rollback status"
    echo "  help            Show this help message"
    echo ""
    echo "Options:"
    echo "  --remove-volumes  Remove PowerDNS data volumes (DESTRUCTIVE)"
    echo "  --force          Skip confirmation prompts"
    echo ""
    echo "Examples:"
    echo "  $0 status"
    echo "  $0 disable-only"
    echo "  $0 full-rollback"
    echo "  $0 stop-services --remove-volumes"
}

# Main execution
main() {
    local command="$1"
    local force_flag="false"
    local remove_volumes=""
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --force)
                force_flag="true"
                shift
                ;;
            --remove-volumes)
                remove_volumes="--remove-volumes"
                shift
                ;;
            disable-only|stop-services|full-rollback|status|help)
                command="$1"
                shift
                ;;
            *)
                shift
                ;;
        esac
    done
    
    # Show help if no command
    if [[ -z "$command" ]]; then
        show_help
        exit 0
    fi
    
    case "$command" in
        help)
            show_help
            ;;
        status)
            check_environment
            show_status
            ;;
        disable-only)
            check_environment
            if [[ "$force_flag" != "true" ]]; then
                warn "This will disable PowerDNS integration. Continue? (y/N)"
                read -r response
                if [[ ! "$response" =~ ^[Yy]$ ]]; then
                    log "Rollback cancelled"
                    exit 0
                fi
            fi
            create_backup
            disable_powerdns
            restart_application
            verify_rollback
            show_status
            ;;
        stop-services)
            check_environment
            if [[ "$force_flag" != "true" ]] && [[ -n "$remove_volumes" ]]; then
                error "WARNING: --remove-volumes will permanently delete PowerDNS data!"
                warn "Continue? (y/N)"
                read -r response
                if [[ ! "$response" =~ ^[Yy]$ ]]; then
                    log "Rollback cancelled"
                    exit 0
                fi
            fi
            create_backup
            stop_powerdns_services "$remove_volumes"
            show_status
            ;;
        full-rollback)
            check_environment
            if [[ "$force_flag" != "true" ]]; then
                error "This will perform a complete PowerDNS rollback!"
                warn "Continue? (y/N)"
                read -r response
                if [[ ! "$response" =~ ^[Yy]$ ]]; then
                    log "Rollback cancelled"
                    exit 0
                fi
            fi
            create_backup
            disable_powerdns
            stop_powerdns_services "$remove_volumes"
            restart_application
            verify_rollback
            show_status
            ;;
        *)
            error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"