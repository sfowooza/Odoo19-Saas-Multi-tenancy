# 🛠️ Setup and Installation Guide

## Detailed Setup Instructions

### System Requirements

#### Minimum Requirements
- **RAM**: 4GB (Recommended: 8GB+ for multiple tenants)
- **CPU**: 2 cores (Recommended: 4+ cores)
- **Storage**: 50GB SSD (Recommended: 100GB+)
- **OS**: Linux, macOS, or Windows with Docker Desktop

#### Software Requirements
- Docker Engine 20.10+
- Docker Compose 2.0+
- Git 2.0+

### Step-by-Step Installation

#### 1. Install Docker and Docker Compose

**Ubuntu/Debian:**
```bash
# Update package index
sudo apt-get update

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add your user to docker group
sudo usermod -aG docker $USER
```

**macOS:**
```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Docker Desktop
brew install --cask docker
```

**Windows:**
1. Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop)

#### 2. Clone and Configure the Repository

```bash
# Clone the repository
git clone https://github.com/sfowooza/Odoo19-Saas-Multi-tenancy.git
cd Odoo19-Saas-Multi-tenancy

# Copy configuration files
cp config/odoo.conf.example config/odoo.conf

# Edit configuration if needed
nano config/odoo.conf
```

#### 3. Customize Configuration

Edit `docker-compose.yml` to customize your setup:

```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: postgres
      POSTGRES_USER: odoo
      POSTGRES_PASSWORD: your_secure_password  # Change this!
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  odoo19:
    image: odoo:19.0
    depends_on:
      - db
    ports:
      - "7001:8069"  # Main Odoo port
      - "7002:8072"  # Chat port
    environment:
      HOST: db
      PORT: 5432
      USER: odoo
      PASSWORD: your_secure_password  # Match the DB password
      ADMIN_PASSWORD: your_admin_password  # Change this!
    volumes:
      - ./config:/etc/odoo
      - ./saas_signup:/mnt/extra-addons
      - odoo_data:/var/lib/odoo
    restart: unless-stopped

  pgadmin:
    image: dpage/pgadmin4:latest
    environment:
      PGADMIN_DEFAULT_EMAIL: your-email@domain.com
      PGADMIN_DEFAULT_PASSWORD: your_pgadmin_password
    ports:
      - "5050:80"
    depends_on:
      - db

volumes:
  postgres_data:
  odoo_data:
```

#### 4. Launch the Platform

```bash
# Start all services
docker-compose up -d

# Check if services are running
docker-compose ps

# View logs (optional)
docker-compose logs -f odoo19
```

#### 5. Initial Setup

1. **Access Odoo**: http://localhost:7001/web
2. **Login**: Use the credentials from your `docker-compose.yml`
3. **Install SaaS Module**:
   - Click "Apps" in the top menu
   - Remove the "Apps" filter (search box)
   - Search for "SaaS Signup Module"
   - Click "Install"

#### 6. Configure SaaS Settings

1. **Access Configuration**: Settings → SaaS Configuration
2. **Basic Settings**:
   - **Deployment Mode**: Choose between Localhost or Subdomain
   - **Port Range**: Set the range for tenant ports (e.g., 8000-9000)
   - **Database Host**: Usually 'localhost' or 'db'
   - **Admin Password**: Master password for tenant creation

3. **Email Configuration** (Optional):
   - Configure SMTP settings for tenant notifications
   - Set up email templates

### Production Deployment

#### SSL/HTTPS Setup

1. **Obtain SSL Certificate**:
```bash
# Using Certbot
sudo apt-get install certbot
sudo certbot certonly --standalone -d yourdomain.com -d *.yourdomain.com
```

2. **Update Docker Compose for Production**:
```yaml
# Add nginx service
nginx:
  image: nginx:alpine
  ports:
    - "80:80"
    - "443:443"
  volumes:
    - ./nginx.conf:/etc/nginx/nginx.conf
    - ./ssl:/etc/ssl/certs
  depends_on:
    - odoo19
```

#### Database Optimization

1. **PostgreSQL Configuration**:
```bash
# Edit postgresql.conf
shared_buffers = 256MB
effective_cache_size = 1GB
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
```

2. **Connection Pooling**:
```yaml
# In docker-compose.yml
odoo19:
  environment:
    DB_MAXCONN: 64
    WORKERS: 4
```

### Monitoring and Logging

#### Log Management

1. **Configure Log Rotation**:
```yaml
# In docker-compose.yml
odoo19:
  logging:
    driver: "json-file"
    options:
      max-size: "10m"
      max-file: "3"
```

2. **Access Logs**:
```bash
# View Odoo logs
docker-compose logs -f odoo19

# View database logs
docker-compose logs -f db
```

#### Resource Monitoring

1. **System Monitoring**:
```bash
# Install monitoring tools
sudo apt-get install htop iotop

# Monitor Docker containers
docker stats
```

2. **Database Monitoring**:
```sql
-- Connect to database and monitor
SELECT pid, usename, application, state, query_start
FROM pg_stat_activity
WHERE state = 'active';
```

### Troubleshooting

#### Common Issues and Solutions

1. **Port Conflicts**:
```bash
# Check what's using port 7001
sudo netstat -tulpn | grep :7001

# Change port in docker-compose.yml
ports:
  - "8080:8069"  # Use different port
```

2. **Database Connection Issues**:
```bash
# Check database status
docker-compose exec db pg_isready -U odoo

# Test connection
docker-compose exec odoo19 python -c "import psycopg2; print('OK')"
```

3. **Module Installation Fails**:
```bash
# Update module list
docker-compose exec odoo19 odoo -d db1 -u base --stop-after-init

# Restart Odoo
docker-compose restart odoo19
```

4. **Memory Issues**:
```bash
# Increase Docker memory limits
# In Docker Desktop settings
# Or add to docker-compose.yml:
odoo19:
  deploy:
    resources:
      limits:
        memory: 4G
```

5. **Permission Issues**:
```bash
# Fix file permissions
sudo chown -R $USER:$USER ./
chmod -R 755 saas_signup/
```

### Backup and Recovery

#### Database Backup

1. **Automated Backups**:
```bash
# Create backup script
cat > backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec db pg_dump -U odoo postgres > backup_$DATE.sql
gzip backup_$DATE.sql
EOF

chmod +x backup.sh

# Add to crontab
crontab -e
# Add: 0 2 * * * /path/to/backup.sh
```

2. **Manual Backup**:
```bash
# Backup entire database
docker-compose exec db pg_dump -U odoo postgres > backup.sql

# Backup specific tenant
docker-compose exec db pg_dump -U odoo tenant_database > tenant_backup.sql
```

#### File System Backup

```bash
# Backup Odoo data
sudo tar -czf odoo_backup_$(date +%Y%m%d).tar.gz odoo_data/

# Backup configuration files
tar -czf config_backup_$(date +%Y%m%d).tar.gz config/ docker-compose.yml
```

### Security Best Practices

1. **Change Default Passwords**:
   - Database password
   - Admin password
   - pgAdmin password

2. **Network Security**:
   - Use firewall (ufw/iptables)
   - Restrict database access to localhost only
   - Use VPN for remote access

3. **Regular Updates**:
   - Update Docker images
   - Update Odoo modules
   - Apply security patches

4. **Access Control**:
   - Use strong passwords
   - Enable 2FA where possible
   - Regular user access reviews

This setup guide should help you get your SaaS platform running smoothly in both development and production environments.