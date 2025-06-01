#!/bin/bash
# Docker Development Helper Script for Prism DNS Server (SCRUM-12)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project configuration
PROJECT_NAME="prism-server"
COMPOSE_FILE="docker-compose.yml"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if Docker is running
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
}

# Function to check if docker-compose is available
check_compose() {
    if ! command -v docker-compose >/dev/null 2>&1; then
        print_error "docker-compose is not installed. Please install docker-compose and try again."
        exit 1
    fi
}

# Function to show help
show_help() {
    echo "Prism DNS Server - Docker Development Helper"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  build           Build Docker images"
    echo "  start           Start development environment"
    echo "  stop            Stop all services"
    echo "  restart         Restart all services"
    echo "  logs            Show logs from all services"
    echo "  logs [service]  Show logs from specific service"
    echo "  test            Run test suite in container"
    echo "  shell           Open shell in server container"
    echo "  db-shell        Open shell in database container"
    echo "  clean           Remove all containers and volumes"
    echo "  status          Show status of all services"
    echo "  help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start                # Start development environment"
    echo "  $0 logs server          # Show server logs"
    echo "  $0 test                 # Run tests"
    echo "  $0 shell                # Open server shell"
    echo ""
}

# Function to build images
build() {
    print_status "Building Docker images..."
    docker-compose build
    print_success "Images built successfully"
}

# Function to start services
start() {
    print_status "Starting development environment..."
    docker-compose up -d
    print_success "Development environment started"
    print_status "Services available at:"
    print_status "  - TCP Server: localhost:8080"
    print_status "  - REST API: http://localhost:8081"
    print_status "  - API Docs: http://localhost:8081/docs"
}

# Function to stop services
stop() {
    print_status "Stopping all services..."
    docker-compose down
    print_success "All services stopped"
}

# Function to restart services
restart() {
    print_status "Restarting all services..."
    docker-compose restart
    print_success "All services restarted"
}

# Function to show logs
show_logs() {
    if [ -n "$1" ]; then
        print_status "Showing logs for service: $1"
        docker-compose logs -f "$1"
    else
        print_status "Showing logs for all services"
        docker-compose logs -f
    fi
}

# Function to run tests
run_tests() {
    print_status "Running test suite..."
    docker-compose --profile testing run --rm tests
    print_success "Tests completed"
}

# Function to open shell
open_shell() {
    service=${1:-server}
    print_status "Opening shell in $service container..."
    docker-compose exec "$service" /bin/bash
}

# Function to clean everything
clean() {
    print_warning "This will remove all containers, volumes, and images for this project."
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Cleaning up..."
        docker-compose down -v --remove-orphans
        docker system prune -f
        print_success "Cleanup completed"
    else
        print_status "Cleanup cancelled"
    fi
}

# Function to show status
show_status() {
    print_status "Service status:"
    docker-compose ps
}

# Main script logic
main() {
    # Check prerequisites
    check_docker
    check_compose

    # Change to project directory
    cd "$(dirname "$0")/.."

    # Parse command
    case "${1:-help}" in
        build)
            build
            ;;
        start)
            start
            ;;
        stop)
            stop
            ;;
        restart)
            restart
            ;;
        logs)
            show_logs "$2"
            ;;
        test)
            run_tests
            ;;
        shell)
            open_shell "$2"
            ;;
        db-shell)
            open_shell database
            ;;
        clean)
            clean
            ;;
        status)
            show_status
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "Unknown command: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"