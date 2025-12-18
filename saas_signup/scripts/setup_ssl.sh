#!/bin/bash
# SSL Certificate Setup for SaaS Platform
# Supports wildcard certificates for subdomain-based deployments

DOMAIN="${1:-yourdomain.com}"
EMAIL="${2:-admin@$DOMAIN}"

echo "=========================================="
echo "SaaS Platform - SSL Setup"
echo "=========================================="
echo "Domain: $DOMAIN"
echo "Email: $EMAIL"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: This script must be run as root"
    exit 1
fi

# Install certbot
echo "Installing Certbot..."
apt-get update
apt-get install -y certbot

echo ""
echo "=========================================="
echo "SSL Certificate Options:"
echo "=========================================="
echo "1. Manual DNS Challenge (works with any DNS provider)"
echo "2. Automated with Cloudflare (requires API token)"
echo "3. Automated with Route53 (requires AWS credentials)"
echo ""
read -p "Select option (1-3): " OPTION

case $OPTION in
    1)
        echo ""
        echo "Using manual DNS challenge..."
        echo "You will need to add TXT records to your DNS provider"
        echo ""
        certbot certonly \
            --manual \
            --preferred-challenges dns \
            -d "$DOMAIN" \
            -d "*.$DOMAIN" \
            --email "$EMAIL" \
            --agree-tos \
            --no-eff-email
        ;;
    
    2)
        echo ""
        echo "Cloudflare Setup..."
        read -p "Enter Cloudflare API Token: " CF_TOKEN
        
        # Create credentials file
        mkdir -p /etc/letsencrypt
        cat > /etc/letsencrypt/cloudflare.ini <<EOF
dns_cloudflare_api_token = $CF_TOKEN
EOF
        chmod 600 /etc/letsencrypt/cloudflare.ini
        
        # Install plugin
        apt-get install -y python3-certbot-dns-cloudflare
        
        # Get certificate
        certbot certonly \
            --dns-cloudflare \
            --dns-cloudflare-credentials /etc/letsencrypt/cloudflare.ini \
            -d "$DOMAIN" \
            -d "*.$DOMAIN" \
            --email "$EMAIL" \
            --agree-tos
        ;;
    
    3)
        echo ""
        echo "Route53 Setup..."
        read -p "Enter AWS Access Key ID: " AWS_KEY
        read -p "Enter AWS Secret Access Key: " AWS_SECRET
        
        # Create credentials file
        mkdir -p /root/.aws
        cat > /root/.aws/credentials <<EOF
[default]
aws_access_key_id = $AWS_KEY
aws_secret_access_key = $AWS_SECRET
EOF
        
        # Install plugin
        apt-get install -y python3-certbot-dns-route53
        
        # Get certificate
        certbot certonly \
            --dns-route53 \
            -d "$DOMAIN" \
            -d "*.$DOMAIN" \
            --email "$EMAIL" \
            --agree-tos
        ;;
    
    *)
        echo "Invalid option"
        exit 1
        ;;
esac

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✓ SSL Certificate Installed Successfully"
    echo "=========================================="
    echo "Certificate: /etc/letsencrypt/live/$DOMAIN/fullchain.pem"
    echo "Private Key: /etc/letsencrypt/live/$DOMAIN/privkey.pem"
    echo ""
    echo "Update your Nginx config to use these certificates"
    echo "Then run: systemctl reload nginx"
    echo ""
    echo "Auto-renewal is configured via cron"
else
    echo ""
    echo "ERROR: SSL setup failed"
    exit 1
fi
