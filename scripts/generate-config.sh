#!/bin/bash
# Configuration Generation Script for Prism DNS
# Generates environment-specific configuration files from templates

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENVIRONMENTS_DIR="${PROJECT_ROOT}/environments"

# Default values
ENVIRONMENT=""
OUTPUT_DIR=""
VALIDATE_ONLY=false
VERBOSE=false
DRY_RUN=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${BLUE}[INFO]${NC} $1"
    fi
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

# Help function
show_help() {
    cat << EOF
Prism DNS Configuration Generator

USAGE:
    $0 [OPTIONS] --environment ENVIRONMENT

DESCRIPTION:
    Generates environment-specific configuration files from templates.
    Substitutes environment variables and validates required settings.

OPTIONS:
    -e, --environment ENV    Target environment (development|staging|production)
    -o, --output DIR         Output directory (default: current environment dir)
    -v, --validate-only      Only validate configuration, don't generate files
    -n, --dry-run           Show what would be generated without creating files
    --verbose               Enable verbose output
    -h, --help              Show this help message

EXAMPLES:
    # Generate development configuration
    $0 --environment development

    # Generate production config with custom output
    $0 --environment production --output /opt/prism-dns/config

    # Validate staging configuration without generating files
    $0 --environment staging --validate-only

    # Dry run to see what would be generated
    $0 --environment production --dry-run --verbose

ENVIRONMENT VARIABLES:
    The following variables are required for each environment:

    Development:
        API_SECRET_KEY (optional, defaults to dev key)

    Staging/Production:
        DATABASE_PASSWORD     - Database password
        API_SECRET_KEY       - Application secret key
        SERVER_HOST          - Server hostname
        SERVER_DOMAIN        - Server domain name

    Optional (all environments):
        NOTIFICATION_WEBHOOK_URL - Webhook for notifications
        EXTERNAL_API_BASE_URL   - External API base URL
        ALERT_EMAIL            - Email for alerts
        ALERT_SLACK_WEBHOOK    - Slack webhook for alerts
        SENTRY_DSN             - Sentry error tracking DSN
        REDIS_PASSWORD         - Redis password (production only)

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
            -o|--output)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            -v|--validate-only)
                VALIDATE_ONLY=true
                shift
                ;;
            -n|--dry-run)
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

    # Set default output directory
    if [[ -z "$OUTPUT_DIR" ]]; then
        OUTPUT_DIR="${ENVIRONMENTS_DIR}/${ENVIRONMENT}"
    fi
}

# Validate required environment variables
validate_environment_variables() {
    local env="$1"
    local missing_vars=()
    local optional_vars=()

    log_info "Validating environment variables for $env environment..."

    case "$env" in
        development)
            # Development has minimal requirements
            if [[ -z "${API_SECRET_KEY:-}" ]]; then
                optional_vars+=("API_SECRET_KEY")
            fi
            ;;
        staging|production)
            # Production environments require secure configuration
            [[ -z "${DATABASE_PASSWORD:-}" ]] && missing_vars+=("DATABASE_PASSWORD")
            [[ -z "${API_SECRET_KEY:-}" ]] && missing_vars+=("API_SECRET_KEY")
            [[ -z "${SERVER_HOST:-}" ]] && missing_vars+=("SERVER_HOST")
            [[ -z "${SERVER_DOMAIN:-}" ]] && missing_vars+=("SERVER_DOMAIN")
            
            if [[ "$env" == "production" ]]; then
                [[ -z "${REDIS_PASSWORD:-}" ]] && optional_vars+=("REDIS_PASSWORD")
            fi
            ;;
    esac

    # Check optional variables
    [[ -z "${NOTIFICATION_WEBHOOK_URL:-}" ]] && optional_vars+=("NOTIFICATION_WEBHOOK_URL")
    [[ -z "${EXTERNAL_API_BASE_URL:-}" ]] && optional_vars+=("EXTERNAL_API_BASE_URL")
    [[ -z "${ALERT_EMAIL:-}" ]] && optional_vars+=("ALERT_EMAIL")
    [[ -z "${ALERT_SLACK_WEBHOOK:-}" ]] && optional_vars+=("ALERT_SLACK_WEBHOOK")
    [[ -z "${SENTRY_DSN:-}" ]] && optional_vars+=("SENTRY_DSN")

    # Report missing required variables
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "Missing required environment variables for $env:"
        for var in "${missing_vars[@]}"; do
            log_error "  - $var"
        done
        return 1
    fi

    # Report missing optional variables
    if [[ ${#optional_vars[@]} -gt 0 ]] && [[ "$VERBOSE" == "true" ]]; then
        log_warning "Optional environment variables not set:"
        for var in "${optional_vars[@]}"; do
            log_warning "  - $var"
        done
    fi

    log_success "Environment variable validation passed"
    return 0
}

# Substitute environment variables in template
substitute_template() {
    local template_file="$1"
    local output_file="$2"

    log_info "Processing template: $(basename "$template_file")"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN: Would generate $output_file"
        return 0
    fi

    # Create output directory if it doesn't exist
    mkdir -p "$(dirname "$output_file")"

    # Use envsubst to substitute variables, but preserve undefined variables
    envsubst < "$template_file" > "$output_file"

    # Set appropriate permissions
    chmod 600 "$output_file"

    log_success "Generated: $output_file"
}

# Validate generated configuration
validate_configuration() {
    local config_file="$1"

    if [[ ! -f "$config_file" ]]; then
        log_error "Configuration file not found: $config_file"
        return 1
    fi

    log_info "Validating configuration file: $(basename "$config_file")"

    # Check for unsubstituted variables (still contains \${VAR})
    local unsubstituted
    unsubstituted=$(grep -o '\${[^}]*}' "$config_file" || true)
    
    if [[ -n "$unsubstituted" ]]; then
        log_warning "Found unsubstituted variables in $config_file:"
        echo "$unsubstituted" | sort -u | while read -r var; do
            log_warning "  $var"
        done
    fi

    # Check for required fields based on environment
    local env
    env=$(grep "^ENVIRONMENT=" "$config_file" | cut -d'=' -f2 || echo "unknown")
    
    case "$env" in
        production|staging)
            if grep -q "dev-secret-key-change-me" "$config_file"; then
                log_error "Development secret key found in $env configuration!"
                return 1
            fi
            ;;
    esac

    log_success "Configuration validation passed"
    return 0
}

# Generate nginx configuration
generate_nginx_config() {
    local env="$1"
    local env_dir="$2"
    local nginx_template="${env_dir}/nginx.${env}.conf.template"
    local nginx_config="${env_dir}/nginx.${env}.conf"

    if [[ -f "$nginx_template" ]]; then
        log_info "Generating nginx configuration for $env..."
        substitute_template "$nginx_template" "$nginx_config"
    else
        log_info "No nginx template found for $env environment"
    fi
}

# Main execution function
main() {
    parse_args "$@"

    log_info "Starting configuration generation for $ENVIRONMENT environment"
    log_info "Project root: $PROJECT_ROOT"
    log_info "Output directory: $OUTPUT_DIR"

    # Check if environment directory exists
    local env_dir="${ENVIRONMENTS_DIR}/${ENVIRONMENT}"
    if [[ ! -d "$env_dir" ]]; then
        log_error "Environment directory not found: $env_dir"
        exit 1
    fi

    # Validate environment variables
    if ! validate_environment_variables "$ENVIRONMENT"; then
        log_error "Environment variable validation failed"
        exit 1
    fi

    # If validate-only mode, exit here
    if [[ "$VALIDATE_ONLY" == "true" ]]; then
        log_success "Validation completed successfully"
        exit 0
    fi

    # Generate .env file
    local env_template="${env_dir}/.env.template"
    local env_output="${OUTPUT_DIR}/.env"

    if [[ -f "$env_template" ]]; then
        substitute_template "$env_template" "$env_output"
        validate_configuration "$env_output"
    else
        log_error "Environment template not found: $env_template"
        exit 1
    fi

    # Generate nginx configuration if template exists
    generate_nginx_config "$ENVIRONMENT" "$env_dir"

    # Copy docker-compose override file
    local docker_override_src="${env_dir}/docker-compose.override.yml"
    local docker_override_dst="${OUTPUT_DIR}/docker-compose.override.yml"
    
    if [[ -f "$docker_override_src" ]]; then
        if [[ "$DRY_RUN" == "true" ]]; then
            log_info "DRY RUN: Would copy $docker_override_src to $docker_override_dst"
        else
            cp "$docker_override_src" "$docker_override_dst"
            log_success "Copied: $docker_override_dst"
        fi
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log_success "DRY RUN completed - no files were actually generated"
    else
        log_success "Configuration generation completed for $ENVIRONMENT environment"
        log_info "Generated files in: $OUTPUT_DIR"
    fi
}

# Run main function with all arguments
main "$@"