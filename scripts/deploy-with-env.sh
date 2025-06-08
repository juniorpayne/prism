#!/bin/bash
# Environment-Aware Deployment Script for Prism DNS
# Integrates environment management with deployment process

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Default values
ENVIRONMENT=""
TARGET_HOST=""
DEPLOY_TYPE="docker-compose"
BACKUP_BEFORE_DEPLOY=true
VALIDATE_CONFIG=true
FORCE_DEPLOY=false
DRY_RUN=false
VERBOSE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

log_verbose() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${BLUE}[VERBOSE]${NC} $1"
    fi
}

# Help function
show_help() {
    cat << EOF
Prism DNS Environment-Aware Deployment Script

USAGE:
    $0 [OPTIONS] --environment ENVIRONMENT [--target-host HOST]

DESCRIPTION:
    Deploys Prism DNS using environment-specific configurations.
    Automatically generates configuration files and handles secrets.

OPTIONS:
    -e, --environment ENV    Target environment (development|staging|production)
    -t, --target-host HOST   Target host for deployment (for remote deployments)
    -d, --deploy-type TYPE   Deployment type (docker-compose|registry) [default: docker-compose]
    --no-backup             Skip backup before deployment
    --no-validate           Skip configuration validation
    --force                 Force deployment even if validation fails
    --dry-run               Show what would be deployed without executing
    --verbose               Enable verbose output
    -h, --help              Show this help message

EXAMPLES:
    # Deploy to development environment locally
    $0 --environment development

    # Deploy to production with backup and validation
    $0 --environment production --target-host 35.170.180.10

    # Deploy using registry images
    $0 --environment production --deploy-type registry

    # Dry run for staging deployment
    $0 --environment staging --dry-run --verbose

DEPLOYMENT TYPES:
    docker-compose          Build and deploy using local docker-compose
    registry               Deploy using pre-built images from container registry

ENVIRONMENT VARIABLES:
    Required for remote deployments:
        SSH_PRIVATE_KEY      - SSH private key for remote access
        
    Environment-specific variables (see generate-config.sh for details):
        DATABASE_PASSWORD    - Database password
        API_SECRET_KEY      - Application secret key
        SERVER_HOST         - Server hostname
        SERVER_DOMAIN       - Server domain name

EOF
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -t|--target-host)
                TARGET_HOST="$2"
                shift 2
                ;;
            -d|--deploy-type)
                DEPLOY_TYPE="$2"
                shift 2
                ;;
            --no-backup)
                BACKUP_BEFORE_DEPLOY=false
                shift
                ;;
            --no-validate)
                VALIDATE_CONFIG=false
                shift
                ;;
            --force)
                FORCE_DEPLOY=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # Validate required arguments
    if [[ -z "$ENVIRONMENT" ]]; then
        log_error "Environment is required. Use --environment to specify."
        show_help
        exit 1
    fi

    # Validate environment
    if [[ ! "$ENVIRONMENT" =~ ^(development|staging|production)$ ]]; then
        log_error "Invalid environment: $ENVIRONMENT"
        log_error "Valid environments: development, staging, production"
        exit 1
    fi

    # Validate deploy type
    if [[ ! "$DEPLOY_TYPE" =~ ^(docker-compose|registry)$ ]]; then
        log_error "Invalid deploy type: $DEPLOY_TYPE"
        log_error "Valid deploy types: docker-compose, registry"
        exit 1
    fi

    # For production, require explicit target host
    if [[ "$ENVIRONMENT" == "production" && -z "$TARGET_HOST" ]]; then
        log_error "Target host is required for production deployments"
        exit 1
    fi
}

# Generate configuration files
generate_configuration() {
    log_info "Generating configuration for $ENVIRONMENT environment..."
    
    local config_script="${SCRIPT_DIR}/generate-config.sh"
    local config_args="--environment $ENVIRONMENT"
    
    if [[ "$VERBOSE" == "true" ]]; then
        config_args="$config_args --verbose"
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        config_args="$config_args --dry-run"
    fi
    
    if ! "$config_script" $config_args; then
        log_error "Configuration generation failed"
        exit 1
    fi
    
    log_success "Configuration generated successfully"
}

# Validate deployment prerequisites
validate_prerequisites() {
    log_info "Validating deployment prerequisites..."
    
    # Check if docker is available
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check docker compose
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not available"
        exit 1
    fi
    
    # Check environment-specific requirements
    case "$ENVIRONMENT" in
        production)
            # Production requires specific checks
            if [[ -z "${DATABASE_PASSWORD:-}" ]]; then
                log_error "DATABASE_PASSWORD environment variable is required for production"
                exit 1
            fi
            
            if [[ -z "${API_SECRET_KEY:-}" ]]; then
                log_error "API_SECRET_KEY environment variable is required for production"
                exit 1
            fi
            ;;
        staging)
            # Staging requires database password
            if [[ -z "${DATABASE_PASSWORD:-}" ]]; then
                log_error "DATABASE_PASSWORD environment variable is required for staging"
                exit 1
            fi
            ;;
        development)
            # Development has minimal requirements
            log_verbose "Development environment - minimal prerequisites"
            ;;
    esac
    
    log_success "Prerequisites validation passed"
}

# Create backup before deployment
create_backup() {
    if [[ "$BACKUP_BEFORE_DEPLOY" != "true" ]]; then
        log_info "Skipping backup (--no-backup specified)"
        return 0
    fi
    
    log_info "Creating backup before deployment..."
    
    local backup_script="${SCRIPT_DIR}/backup.sh"
    if [[ -f "$backup_script" ]]; then
        local backup_args="--environment $ENVIRONMENT"
        
        if [[ -n "$TARGET_HOST" ]]; then
            backup_args="$backup_args --target-host $TARGET_HOST"
        fi
        
        if [[ "$DRY_RUN" == "true" ]]; then
            backup_args="$backup_args --dry-run"
        fi
        
        if "$backup_script" $backup_args; then
            log_success "Backup created successfully"
        else
            log_warning "Backup failed, but continuing with deployment"
        fi
    else
        log_warning "Backup script not found, skipping backup"
    fi
}

# Deploy using docker-compose
deploy_docker_compose() {
    log_info "Deploying using docker-compose..."
    
    local env_dir="${PROJECT_ROOT}/environments/${ENVIRONMENT}"
    local compose_file="${PROJECT_ROOT}/docker-compose.yml"
    local override_file="${env_dir}/docker-compose.override.yml"
    local env_file="${env_dir}/.env"
    
    # Prepare compose command
    local compose_cmd="docker compose"
    compose_cmd="$compose_cmd -f $compose_file"
    
    if [[ -f "$override_file" ]]; then
        compose_cmd="$compose_cmd -f $override_file"
    fi
    
    if [[ -f "$env_file" ]]; then
        compose_cmd="$compose_cmd --env-file $env_file"
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would execute: $compose_cmd up -d"
        return 0
    fi
    
    # Execute deployment
    cd "$PROJECT_ROOT"
    
    log_info "Pulling latest images..."
    eval "$compose_cmd pull"
    
    log_info "Starting services..."
    eval "$compose_cmd up -d"
    
    # Wait for services to be healthy
    log_info "Waiting for services to start..."
    sleep 10
    
    # Check service health
    if eval "$compose_cmd ps" | grep -q "unhealthy\|Exit"; then
        log_error "Some services failed to start properly"
        eval "$compose_cmd logs"
        exit 1
    fi
    
    log_success "Docker Compose deployment completed"
}

# Deploy using registry images
deploy_registry() {
    log_info "Deploying using registry images..."
    
    local registry_script="${SCRIPT_DIR}/deploy-registry.sh"
    if [[ ! -f "$registry_script" ]]; then
        log_error "Registry deployment script not found: $registry_script"
        exit 1
    fi
    
    local registry_args="--environment $ENVIRONMENT"
    
    if [[ -n "$TARGET_HOST" ]]; then
        registry_args="$registry_args --target-host $TARGET_HOST"
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        registry_args="$registry_args --dry-run"
    fi
    
    if [[ "$VERBOSE" == "true" ]]; then
        registry_args="$registry_args --verbose"
    fi
    
    if ! "$registry_script" $registry_args; then
        log_error "Registry deployment failed"
        exit 1
    fi
    
    log_success "Registry deployment completed"
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."
    
    local health_endpoint="http://localhost:8081/api/health"
    local max_attempts=12
    local attempt=1
    
    if [[ -n "$TARGET_HOST" ]]; then
        health_endpoint="http://${TARGET_HOST}:8081/api/health"
    fi
    
    while [[ $attempt -le $max_attempts ]]; do
        log_verbose "Health check attempt $attempt/$max_attempts..."
        
        if curl -sf "$health_endpoint" > /dev/null 2>&1; then
            log_success "Service is healthy and responding"
            return 0
        fi
        
        sleep 5
        ((attempt++))
    done
    
    log_error "Service failed health check after $max_attempts attempts"
    return 1
}

# Cleanup on failure
cleanup_on_failure() {
    log_warning "Deployment failed, performing cleanup..."
    
    # This could include rollback logic
    # For now, just log the failure
    log_error "Deployment cleanup completed"
}

# Main execution function
main() {
    parse_args "$@"
    
    log_info "Starting deployment for $ENVIRONMENT environment"
    log_info "Deploy type: $DEPLOY_TYPE"
    
    if [[ -n "$TARGET_HOST" ]]; then
        log_info "Target host: $TARGET_HOST"
    fi
    
    # Set up error handling
    trap cleanup_on_failure ERR
    
    # Execute deployment steps
    validate_prerequisites
    generate_configuration
    create_backup
    
    case "$DEPLOY_TYPE" in
        docker-compose)
            deploy_docker_compose
            ;;
        registry)
            deploy_registry
            ;;
        *)
            log_error "Unknown deploy type: $DEPLOY_TYPE"
            exit 1
            ;;
    esac
    
    # Verify deployment unless dry run
    if [[ "$DRY_RUN" != "true" ]]; then
        if verify_deployment; then
            log_success "Deployment verification passed"
        else
            log_error "Deployment verification failed"
            exit 1
        fi
    fi
    
    if [[ "$DRY_RUN" == "true" ]]; then
        log_success "DRY RUN completed successfully"
    else
        log_success "Deployment completed successfully for $ENVIRONMENT environment"
    fi
}

# Run main function with all arguments
main "$@"