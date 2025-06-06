#!/bin/bash
# Deployment Utilities for Prism DNS
# This script provides utility functions for deployment operations

set -euo pipefail

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

# Function to check if a service is healthy
check_service_health() {
    local service_name="$1"
    local health_url="$2"
    local max_attempts="${3:-30}"
    local wait_time="${4:-5}"
    
    log_info "Checking health of $service_name..."
    
    for ((i=1; i<=max_attempts; i++)); do
        if curl -sf "$health_url" > /dev/null 2>&1; then
            log_success "$service_name is healthy (attempt $i/$max_attempts)"
            return 0
        fi
        
        log_warning "$service_name health check failed (attempt $i/$max_attempts)"
        if [[ $i -lt $max_attempts ]]; then
            sleep $wait_time
        fi
    done
    
    log_error "$service_name failed health check after $max_attempts attempts"
    return 1
}

# Function to wait for container to be ready
wait_for_container() {
    local container_name="$1"
    local max_attempts="${2:-60}"
    local wait_time="${3:-2}"
    
    log_info "Waiting for container $container_name to be ready..."
    
    for ((i=1; i<=max_attempts; i++)); do
        if docker ps --filter "name=$container_name" --filter "status=running" | grep -q "$container_name"; then
            log_success "Container $container_name is running (attempt $i/$max_attempts)"
            return 0
        fi
        
        if [[ $i -lt $max_attempts ]]; then
            sleep $wait_time
        fi
    done
    
    log_error "Container $container_name failed to start after $max_attempts attempts"
    return 1
}

# Function to perform rolling update
rolling_update() {
    local service_name="$1"
    local compose_file="$2"
    local scale_up="${3:-2}"
    local scale_down="${4:-1}"
    
    log_info "Performing rolling update for $service_name..."
    
    # Check if docker-compose is available
    local DOCKER_COMPOSE
    if command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE="docker-compose"
    elif docker compose version &> /dev/null; then
        DOCKER_COMPOSE="docker compose"
    else
        log_error "Docker Compose is not available"
        return 1
    fi
    
    # Scale up the service
    log_info "Scaling up $service_name to $scale_up instances..."
    if ! $DOCKER_COMPOSE -f "$compose_file" up -d --no-deps --scale "$service_name=$scale_up" "$service_name"; then
        log_error "Failed to scale up $service_name"
        return 1
    fi
    
    # Wait for new instances to be healthy
    sleep 30
    
    # Scale down to target number
    log_info "Scaling down $service_name to $scale_down instances..."
    if ! $DOCKER_COMPOSE -f "$compose_file" up -d --no-deps --scale "$service_name=$scale_down" "$service_name"; then
        log_error "Failed to scale down $service_name"
        return 1
    fi
    
    log_success "Rolling update completed for $service_name"
}

# Function to create deployment backup
create_backup() {
    local backup_name="$1"
    local source_dir="$2"
    
    local backup_dir="$HOME/deployment-backups/$backup_name"
    
    log_info "Creating backup: $backup_name"
    
    mkdir -p "$backup_dir"
    
    # Backup docker-compose files
    for file in docker-compose.production.yml docker-compose.registry.yml .env; do
        if [[ -f "$source_dir/$file" ]]; then
            cp "$source_dir/$file" "$backup_dir/"
            log_info "Backed up: $file"
        fi
    done
    
    # Save current container status
    docker ps --filter "name=prism-" --format "table {{.Names}}\t{{.Image}}\t{{.Status}}" > "$backup_dir/containers-before.txt"
    
    # Save deployment metadata
    cat > "$backup_dir/backup-info.txt" << EOF
Backup Created: $(date -u '+%Y-%m-%d %H:%M:%S UTC')
Source Directory: $source_dir
Backup Directory: $backup_dir
Created By: $(whoami)
Host: $(hostname)
EOF
    
    log_success "Backup created successfully: $backup_dir"
}

# Function to restore from backup
restore_backup() {
    local backup_name="$1"
    local target_dir="$2"
    
    local backup_dir="$HOME/deployment-backups/$backup_name"
    
    if [[ ! -d "$backup_dir" ]]; then
        log_error "Backup not found: $backup_dir"
        return 1
    fi
    
    log_info "Restoring from backup: $backup_name"
    
    # Restore docker-compose files
    for file in docker-compose.production.yml docker-compose.registry.yml .env; do
        if [[ -f "$backup_dir/$file" ]]; then
            cp "$backup_dir/$file" "$target_dir/"
            log_info "Restored: $file"
        fi
    done
    
    log_success "Backup restored successfully from: $backup_dir"
}

# Function to cleanup old backups
cleanup_old_backups() {
    local keep_count="${1:-10}"
    local backup_base_dir="$HOME/deployment-backups"
    
    if [[ ! -d "$backup_base_dir" ]]; then
        log_info "No backup directory found"
        return 0
    fi
    
    log_info "Cleaning up old backups (keeping $keep_count most recent)..."
    
    # Count current backups
    local backup_count=$(ls -1 "$backup_base_dir" 2>/dev/null | wc -l)
    
    if [[ $backup_count -le $keep_count ]]; then
        log_info "Only $backup_count backups found, no cleanup needed"
        return 0
    fi
    
    # Remove old backups
    local to_remove=$((backup_count - keep_count))
    log_info "Removing $to_remove old backups..."
    
    ls -1t "$backup_base_dir" | tail -n "$to_remove" | while read -r backup; do
        rm -rf "$backup_base_dir/$backup"
        log_info "Removed old backup: $backup"
    done
    
    log_success "Backup cleanup completed"
}

# Function to run comprehensive health checks
comprehensive_health_check() {
    local environment="${1:-production}"
    local timeout="${2:-60}"
    
    log_info "Running comprehensive health checks for $environment environment..."
    
    local health_checks_failed=false
    
    # Check container status
    log_info "Checking container status..."
    local required_containers=("prism-server" "prism-nginx" "prism-database")
    
    for container in "${required_containers[@]}"; do
        if docker ps --filter "name=$container" --filter "status=running" | grep -q "$container"; then
            log_success "Container $container is running"
        else
            log_error "Container $container is not running"
            health_checks_failed=true
        fi
    done
    
    # Check service endpoints
    log_info "Checking service endpoints..."
    
    # Web interface
    if check_service_health "Web Interface" "http://localhost/" 12 5; then
        log_success "Web interface health check passed"
    else
        log_error "Web interface health check failed"
        health_checks_failed=true
    fi
    
    # API health endpoint
    if check_service_health "API Health" "http://localhost/api/health" 12 5; then
        log_success "API health check passed"
    else
        log_error "API health check failed"
        health_checks_failed=true
    fi
    
    # TCP DNS server
    log_info "Checking TCP DNS server..."
    if nc -z localhost 8080 2>/dev/null; then
        log_success "TCP DNS server is listening"
    else
        log_error "TCP DNS server is not responding"
        health_checks_failed=true
    fi
    
    # Check container logs for recent errors
    log_info "Checking container logs for errors..."
    
    for container in "${required_containers[@]}"; do
        if docker logs "$container" --since 5m 2>&1 | grep -i "error\|exception\|failed" | head -5; then
            log_warning "Found recent errors in $container logs"
        else
            log_success "No recent errors in $container logs"
        fi
    done
    
    # Check disk space
    log_info "Checking disk space..."
    local disk_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [[ $disk_usage -gt 90 ]]; then
        log_warning "Disk usage is high: ${disk_usage}%"
    else
        log_success "Disk usage is normal: ${disk_usage}%"
    fi
    
    # Check memory usage
    log_info "Checking memory usage..."
    local memory_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    if [[ $memory_usage -gt 90 ]]; then
        log_warning "Memory usage is high: ${memory_usage}%"
    else
        log_success "Memory usage is normal: ${memory_usage}%"
    fi
    
    # Final health check result
    if [[ "$health_checks_failed" == "true" ]]; then
        log_error "Comprehensive health check FAILED"
        return 1
    else
        log_success "Comprehensive health check PASSED"
        return 0
    fi
}

# Function to run smoke tests
run_smoke_tests() {
    local environment="${1:-production}"
    
    log_info "Running smoke tests for $environment environment..."
    
    local tests_failed=false
    
    # Test 1: Web interface content
    log_info "Test 1: Web interface content..."
    if curl -s http://localhost/ | grep -q "Prism"; then
        log_success "Web interface contains expected content"
    else
        log_error "Web interface content test failed"
        tests_failed=true
    fi
    
    # Test 2: API health endpoint structure
    log_info "Test 2: API health endpoint structure..."
    local health_response=$(curl -s http://localhost/api/health)
    if echo "$health_response" | grep -q "status"; then
        log_success "Health endpoint returning expected structure"
    else
        log_error "Health endpoint structure test failed"
        tests_failed=true
    fi
    
    # Test 3: TCP DNS server connectivity
    log_info "Test 3: TCP DNS server connectivity..."
    if echo "test-query" | nc -w 5 localhost 8080; then
        log_success "TCP DNS server accepting connections"
    else
        log_error "TCP DNS server connectivity test failed"
        tests_failed=true
    fi
    
    # Test 4: Database connectivity (through API)
    log_info "Test 4: Database connectivity..."
    # This would depend on having a database status endpoint
    # For now, we'll check if the database container is responding
    if docker exec prism-database pg_isready -U prism > /dev/null 2>&1; then
        log_success "Database connectivity test passed"
    else
        log_error "Database connectivity test failed"
        tests_failed=true
    fi
    
    # Test 5: File system permissions
    log_info "Test 5: File system permissions..."
    if docker exec prism-server test -w /app/data; then
        log_success "File system permissions test passed"
    else
        log_error "File system permissions test failed"
        tests_failed=true
    fi
    
    # Final smoke test result
    if [[ "$tests_failed" == "true" ]]; then
        log_error "Smoke tests FAILED"
        return 1
    else
        log_success "All smoke tests PASSED"
        return 0
    fi
}

# Function to get deployment info
get_deployment_info() {
    local compose_file="${1:-docker-compose.registry.yml}"
    
    log_info "Deployment Information:"
    echo "=========================="
    echo "Date: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
    echo "Host: $(hostname)"
    echo "User: $(whoami)"
    echo "Compose File: $compose_file"
    echo ""
    
    if [[ -f "$compose_file" ]]; then
        echo "Container Images:"
        grep "image:" "$compose_file" | sed 's/^[[:space:]]*//' || true
    fi
    
    echo ""
    echo "Running Containers:"
    docker ps --filter "name=prism-" --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}" || true
    
    echo ""
    echo "Container Resource Usage:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" $(docker ps --filter "name=prism-" --format "{{.Names}}") 2>/dev/null || true
}

# Export functions for use in other scripts
export -f log_info log_success log_warning log_error
export -f check_service_health wait_for_container rolling_update
export -f create_backup restore_backup cleanup_old_backups
export -f comprehensive_health_check run_smoke_tests get_deployment_info