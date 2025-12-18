#!/bin/bash

# 🏢 Odoo 19 SaaS Multi-Tenancy Platform - Quick Installer
# This script automatically sets up the SaaS platform

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print colored output
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

# Check if Docker is installed
check_docker() {
    print_status "Checking Docker installation..."
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        echo "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    print_success "Docker is installed"
}

# Check if Docker Compose is installed
check_docker_compose() {
    print_status "Checking Docker Compose installation..."
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    print_success "Docker Compose is installed"
}

# Check system requirements
check_requirements() {
    print_status "Checking system requirements..."

    # Check RAM
    TOTAL_RAM=$(free -m | awk 'NR==2{printf "%.0f", $2/1024}')
    if [ "$TOTAL_RAM" -lt 4 ]; then
        print_warning "System has less than 4GB RAM. Performance may be limited."
    else
        print_success "System RAM: ${TOTAL_RAM}GB"
    fi

    # Check available disk space
    AVAILABLE_SPACE=$(df -BG . | awk 'NR==2 {print $4}' | sed 's/G//')
    if [ "$AVAILABLE_SPACE" -lt 10 ]; then
        print_warning "Less than 10GB disk space available."
    else
        print_success "Available disk space: ${AVAILABLE_SPACE}GB"
    fi
}

# Install dependencies
install_dependencies() {
    print_status "Installing dependencies..."

    if command -v apt-get &> /dev/null; then
        sudo apt-get update -qq
        sudo apt-get install -y git curl
    elif command -v yum &> /dev/null; then
        sudo yum update -y
        sudo yum install -y git curl
    elif command -v brew &> /dev/null; then
        brew update
        brew install git curl
    else
        print_warning "Could not detect package manager. Please install git and curl manually."
    fi
}

# Clone or update repository
setup_repository() {
    print_status "Setting up the repository..."

    if [ -d "Odoo19-Saas-Multi-tenancy" ]; then
        print_warning "Directory already exists. Updating..."
        cd Odoo19-Saas-Multi-tenancy
        git pull origin main
    else
        print_status "Cloning repository..."
        git clone https://github.com/sfowooza/Odoo19-Saas-Multi-tenancy.git
        cd Odoo19-Saas-Multi-tenancy
    fi

    print_success "Repository setup complete"
}

# Create configuration files
setup_configuration() {
    print_status "Setting up configuration..."

    # Copy configuration if it doesn't exist
    if [ ! -f "config/odoo.conf" ]; then
        mkdir -p config
        cat > config/odoo.conf << 'EOF'
[options]
; Database Configuration
db_host = db
db_port = 5432
db_user = odoo
db_password = odoo
db_maxconn = 64

; General Configuration
addons_path = /mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons
data_dir = /var/lib/odoo
logfile = /var/log/odoo/odoo.log

; Server Configuration
xmlrpc = True
xmlrpc_port = 8069
xmlrpc_interface = 0.0.0.0
longpolling_port = 8072

; Security
admin_passwd = admin
list_db = True

; Performance
workers = 0
limit_request = 8192
limit_memory_soft = 2147483648
limit_memory_hard = 2684354560

; Demo data (set to False in production)
without_demo = False

; Disable problematic modules
server_wide_modules = base,mail,web
EOF
        print_success "Created odoo.conf"
    else
        print_status "odoo.conf already exists"
    fi
}

# Check for port conflicts
check_ports() {
    print_status "Checking for port conflicts..."

    # Check if main Odoo port is available
    if netstat -tuln 2>/dev/null | grep -q ":7001 "; then
        print_warning "Port 7001 is already in use."
        print_status "Checking for alternative ports..."

        for port in 8001 9001 10001; do
            if ! netstat -tuln 2>/dev/null | grep -q ":$port "; then
                print_status "Using alternative port: $port"
                # Update docker-compose.yml with alternative port
                sed -i "s/7001:8069/$port:8069/" docker-compose.yml
                break
            fi
        done
    fi

    # Check pgAdmin port
    if netstat -tuln 2>/dev/null | grep -q ":5050 "; then
        print_warning "Port 5050 is already in use, using 5051 for pgAdmin."
        sed -i "s/5050:80/5051:80/" docker-compose.yml
    fi

    print_success "Port configuration complete"
}

# Launch Docker containers
launch_services() {
    print_status "Starting Docker services..."

    # Check for port conflicts first
    check_ports

    # Stop any existing containers
    docker-compose down

    # Build and start services
    docker-compose up -d --build

    print_success "Docker services started"
}

# Get the actual Odoo port being used
get_odoo_port() {
    local port=$(grep -o '0\.0\.0\.0:\([0-9]*\)->8069' docker-compose.yml | head -1 | cut -d: -f2)
    echo ${port:-7001}  # Default to 7001 if not found
}

# Get the actual pgAdmin port being used
get_pgadmin_port() {
    local port=$(grep -o '0\.0\.0\.0:\([0-9]*\)->80' docker-compose.yml | head -1 | cut -d: -f2)
    echo ${port:-5050}  # Default to 5050 if not found
}

# Wait for services to be ready
wait_for_services() {
    print_status "Waiting for services to be ready..."

    # Wait for database
    print_status "Waiting for database..."
    for i in {1..30}; do
        if docker-compose exec -T db pg_isready -U odoo &> /dev/null; then
            print_success "Database is ready"
            break
        fi
        if [ $i -eq 30 ]; then
            print_error "Database failed to start"
            exit 1
        fi
        sleep 2
    done

    # Wait for Odoo
    print_status "Waiting for Odoo..."
    for i in {1..60}; do
        if curl -s http://localhost:7001/web/database/selector &> /dev/null; then
            print_success "Odoo is ready"
            break
        fi
        if [ $i -eq 60 ]; then
            print_error "Odoo failed to start"
            print_status "Check logs with: docker-compose logs odoo19"
            exit 1
        fi
        sleep 3
    done
}

# Display next steps
display_next_steps() {
    # Get actual ports being used
    ODOO_PORT=$(get_odoo_port)
    PGADMIN_PORT=$(get_pgadmin_port)

    echo ""
    echo "🎉 Installation Complete!"
    echo ""
    echo "Your Odoo 19 SaaS Multi-Tenancy Platform is now running."
    echo ""
    echo "📱 Access Information:"
    echo "   • Main Odoo App: http://localhost:$ODOO_PORT"
    echo "   • Admin Panel:   http://localhost:$ODOO_PORT/web"
    echo "   • pgAdmin:       http://localhost:$PGADMIN_PORT"
    echo ""
    echo "🔑 Default Credentials:"
    echo "   • Odoo Admin:   admin / admin"
    echo "   • pgAdmin:       admin@odoo.com / admin"
    echo ""
    echo "📋 Next Steps:"
    echo "   1. Open http://localhost:$ODOO_PORT/web"
    echo "   2. Login with admin/admin"
    echo "   3. Go to Apps → Remove 'Apps' filter"
    echo "   4. Search for 'SaaS Signup Module'"
    echo "   5. Click Install"
    echo ""
    echo "📚 Documentation:"
    echo "   • README.md:     Full documentation"
    echo "   • SETUP.md:      Detailed setup guide"
    echo "   • DEVELOPMENT.md: Development and customization"
    echo ""
    echo "🛠️ Useful Commands:"
    echo "   • View logs:     docker-compose logs -f odoo19"
    echo "   • Stop services: docker-compose down"
    echo "   • Restart:       docker-compose restart"
    echo "   • Update:        git pull && docker-compose up -d --build"
    echo ""
}

# Error handler
cleanup() {
    if [ $? -ne 0 ]; then
        print_error "Installation failed!"
        echo ""
        echo "Please check the error messages above and try again."
        echo ""
        echo "For help, visit: https://github.com/sfowooza/Odoo19-Saas-Multi-tenancy/issues"
    fi
}

# Main installation function
main() {
    echo "🏢 Odoo 19 SaaS Multi-Tenancy Platform Installer"
    echo "================================================="
    echo ""

    # Set up error handling
    trap cleanup ERR

    # Run installation steps
    check_docker
    check_docker_compose
    check_requirements
    install_dependencies
    setup_repository
    setup_configuration
    launch_services
    wait_for_services
    display_next_steps

    print_success "Installation completed successfully! 🎉"
}

# Run main function
main "$@"