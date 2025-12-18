#!/bin/bash
# ==============================================
# SaaS Platform Production Server Setup
# ==============================================
# This script sets up the infrastructure for
# multi-tenant Odoo SaaS platform with:
# - Docker network for tenant isolation
# - Shared PostgreSQL database
# - Nginx reverse proxy
# - SSL with Let's Encrypt
# ==============================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
MAIN_DOMAIN="${MAIN_DOMAIN:-yourdomain.com}"
EMAIL="${EMAIL:-admin@yourdomain.com}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-odoo}"
ODOO_ADMIN_PASSWORD="${ODOO_ADMIN_PASSWORD:-admin}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}SaaS Platform Server Setup${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Domain: $MAIN_DOMAIN"
echo "Email: $EMAIL"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root or with sudo${NC}"
    exit 1
fi

# Update system
echo -e "${YELLOW}[1/8] Updating system...${NC}"
apt-get update -qq
apt-get upgrade -y -qq

# Install Docker
echo -e "${YELLOW}[2/8] Installing Docker...${NC}"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    systemctl enable docker
    systemctl start docker
    echo -e "${GREEN}✓ Docker installed${NC}"
else
    echo -e "${GREEN}✓ Docker already installed${NC}"
fi

# Install Docker Compose
echo -e "${YELLOW}[3/8] Installing Docker Compose...${NC}"
if ! command -v docker-compose &> /dev/null; then
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo -e "${GREEN}✓ Docker Compose installed${NC}"
else
    echo -e "${GREEN}✓ Docker Compose already installed${NC}"
fi

# Create Docker network
echo -e "${YELLOW}[4/8] Creating Docker network...${NC}"
docker network create saas_network 2>/dev/null || echo -e "${GREEN}✓ Network already exists${NC}"

# Create directories
echo -e "${YELLOW}[5/8] Creating directories...${NC}"
mkdir -p /opt/saas/tenants
mkdir -p /var/log/nginx
mkdir -p /var/www/certbot
mkdir -p /etc/nginx/sites-available
mkdir -p /etc/nginx/sites-enabled
echo -e "${GREEN}✓ Directories created${NC}"

# Install and configure Nginx
echo -e "${YELLOW}[6/8] Installing Nginx...${NC}"
if ! command -v nginx &> /dev/null; then
    apt-get install -y nginx
    systemctl enable nginx
    echo -e "${GREEN}✓ Nginx installed${NC}"
else
    echo -e "${GREEN}✓ Nginx already installed${NC}"
fi

# Create Nginx main config
cat > /etc/nginx/nginx.conf << 'EOF'
user www-data;
worker_processes auto;
pid /run/nginx.pid;
include /etc/nginx/modules-enabled/*.conf;

events {
    worker_connections 2048;
    use epoll;
    multi_accept on;
}

http {
    # Basic Settings
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    server_tokens off;

    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # SSL Settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;

    # Logging
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;

    # Gzip Settings
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss application/rss+xml font/truetype font/opentype application/vnd.ms-fontobject image/svg+xml;

    # Include site configs
    include /etc/nginx/sites-enabled/*;
}
EOF

# Create main domain config (landing page)
cat > /etc/nginx/sites-available/main.conf << EOF
# Main domain landing page
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name $MAIN_DOMAIN www.$MAIN_DOMAIN;

    # Let's Encrypt ACME challenge
    location ^~ /.well-known/acme-challenge/ {
        default_type "text/plain";
        root /var/www/certbot;
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl http2 default_server;
    listen [::]:443 ssl http2 default_server;
    server_name $MAIN_DOMAIN www.$MAIN_DOMAIN;

    ssl_certificate /etc/letsencrypt/live/$MAIN_DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$MAIN_DOMAIN/privkey.pem;

    root /var/www/html;
    index index.html;

    location / {
        try_files \$uri \$uri/ =404;
    }
}
EOF

ln -sf /etc/nginx/sites-available/main.conf /etc/nginx/sites-enabled/main.conf
rm -f /etc/nginx/sites-enabled/default

# Install Certbot
echo -e "${YELLOW}[7/8] Installing Certbot for SSL...${NC}"
if ! command -v certbot &> /dev/null; then
    apt-get install -y certbot python3-certbot-nginx
    echo -e "${GREEN}✓ Certbot installed${NC}"
else
    echo -e "${GREEN}✓ Certbot already installed${NC}"
fi

# Setup PostgreSQL container
echo -e "${YELLOW}[8/8] Setting up PostgreSQL...${NC}"
if ! docker ps | grep -q postgres_saas; then
    docker run -d \
        --name postgres_saas \
        --network saas_network \
        -e POSTGRES_USER=odoo \
        -e POSTGRES_PASSWORD=$POSTGRES_PASSWORD \
        -e POSTGRES_DB=postgres \
        -v postgres_data:/var/lib/postgresql/data \
        --restart unless-stopped \
        postgres:15
    echo -e "${GREEN}✓ PostgreSQL container created${NC}"
else
    echo -e "${GREEN}✓ PostgreSQL already running${NC}"
fi

# Test Nginx config
nginx -t

# Restart Nginx
systemctl restart nginx

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo "1. Get SSL certificate:"
echo "   sudo certbot certonly --nginx -d $MAIN_DOMAIN -d *.$MAIN_DOMAIN --email $EMAIL"
echo ""
echo "2. Clone your Odoo repository:"
echo "   git clone https://github.com/yourusername/Odoo-19-SaaS.git /opt/odoo19"
echo ""
echo "3. Start main Odoo instance:"
echo "   cd /opt/odoo19 && docker-compose up -d"
echo ""
echo "4. Setup auto-renewal for SSL:"
echo "   echo '0 0 * * * certbot renew --quiet' | crontab -"
echo ""
echo -e "${GREEN}Server is ready for SaaS deployment!${NC}"
