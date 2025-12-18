# Odoo 19 SaaS Signup Module - Enterprise Edition

**Version:** 19.0.2.0.0  
**Edition:** Enterprise  
**License:** LGPL-3

## Overview
Production-ready multi-tenant SaaS platform for Odoo 19 with advanced monitoring, resource management, and automated provisioning. Supports both localhost testing and enterprise cloud deployments.

### 🆕 Enterprise Features (v19.0.2.0.0)
- ✨ Real-time monitoring dashboard
- 📊 Resource usage tracking (CPU, RAM, Storage)
- 🔒 Resource limits per subscription plan
- ⏱️ Automated trial expiration handling
- 🗄️ Template-based fast provisioning
- 🔐 Wildcard SSL automation scripts
- 📈 Revenue and analytics tracking
- 🚨 System health alerts
- 🧹 Automatic cleanup of old tenants

### Previous Features (v19.0.1.x)
- ✅ Real-time subdomain availability checking
- ✅ Auto-domain detection
- ✅ Dual deployment modes (localhost/subdomain)
- ✅ Docker-based tenant isolation
- ✅ Plan-based module installation options.

## Features

✅ **Dual Deployment Modes**
- **Localhost/Self-Hosted**: Run tenants on different ports (8001, 8002, etc.)
- **Subdomain/Cloud**: Run tenants on subdomains (tenant1.yourdomain.com)

✅ **Complete Tenant Management**
- Instant signup with background provisioning
- Admin approval workflow
- Trial period management with auto-expiration
- Plan upgrade system
- Module restriction per plan

✅ **Plan-Based Subscriptions**
- Multiple subscription tiers
- Trial periods with automatic expiration
- Upgrade/downgrade capabilities
- Plan-specific module installations

✅ **Enterprise Monitoring & Analytics** 🆕
- Real-time dashboard with system metrics
- CPU, RAM, and disk usage tracking
- Database size monitoring per tenant
- Revenue analytics (MRR/ARR)
- System health alerts
- Recent signup tracking

✅ **Resource Management** 🆕
- CPU core limits per plan
- Memory (RAM) limits per plan
- Storage quotas with warnings
- Bandwidth limits
- Automatic enforcement via cron jobs
- Tenant suspension on limit breach

✅ **Automated Operations** 🆕
- Hourly resource usage checks
- Daily trial expiration monitoring
- Weekly cleanup of cancelled tenants
- Template-based fast provisioning
- SSL certificate auto-renewal
- Email notifications (configurable) during provisioning
- Hide non-plan modules from tenant Apps menu

✅ **Docker-Based Multi-Tenancy**
- Each tenant runs in isolated Docker container
- Separate PostgreSQL database per tenant
- Automatic container lifecycle management

✅ **Upgrade System**
- Users can request plan upgrades
- Admin approval for upgrades
- Automatic module installation on upgrade
- Trial to paid conversion

## Requirements

### System Requirements
- Odoo 19
- Docker Engine
- PostgreSQL 15+
- Python 3.10+

### Python Packages
- docker
- psycopg2
- passlib

### For Subdomain Mode (Additional)
- Nginx reverse proxy
- Domain with DNS wildcard record (*.yourdomain.com)
- SSL certificate (recommended)

## Installation

1. **Copy Module to Addons**
   ```bash
   cp -r saas_signup /path/to/odoo/addons/
   ```

2. **Update Odoo Addons List**
   - Go to Apps menu
   - Click "Update Apps List"
   - Search for "SaaS Signup Module"
   - Click Install

3. **Configure Deployment Mode**
   - Go to SaaS Management → Configuration
   - Choose deployment mode (Localhost or Subdomain)
   - For subdomain mode: Enter your main domain
   - Save configuration

## Configuration

### Localhost/Self-Hosted Mode

Best for: Development, testing, local installations

**Setup Steps:**
1. Set deployment mode to "Localhost"
2. Configure starting port (default: 8001)
3. Ensure Docker is running
4. Users will access tenants via: `http://localhost:PORT`

**No additional setup required!**

### Subdomain/Cloud Mode

Best for: Production, cloud hosting, professional SaaS

**Setup Steps:**

1. **DNS Configuration**
   - Add wildcard A record: `*.yourdomain.com` → Your server IP

2. **Module Configuration**
   - Set deployment mode to "Subdomain"
   - Enter main domain: `yourdomain.com`
   - Enable SSL if using HTTPS

3. **Nginx Configuration**
   ```nginx
   # /etc/nginx/sites-available/saas-tenants
   server {
       listen 80;
       server_name *.yourdomain.com;

       location / {
           proxy_pass http://localhost:8069;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

4. **SSL Setup (Recommended)**
   ```bash
   certbot --nginx -d *.yourdomain.com
   ```

## Usage

### For Administrators

1. **Configure Plans**
   - Go to SaaS Management → Subscription Plans
   - Edit plans and configure modules
   - Set pricing and features

2. **Approve Signups**
   - Go to SaaS Management → Clients
   - Review pending signups
   - Click "Approve" or "Reject"
   - Tenant container starts automatically on approval

3. **Manage Tenants**
   - View all tenants and their status
   - Suspend/Activate tenants
   - Approve upgrade requests
   - Monitor trial expirations

### For Users

1. **Sign Up**
   - Visit: `http://yoursite.com/saas/signup`
   - Fill in company details
   - Choose subscription plan
   - Submit (instant confirmation)

2. **Wait for Approval**
   - Background provisioning happens automatically
   - Database created
   - Plan modules installed
   - Container prepared

3. **Login After Approval**
   - **Localhost mode**: `http://localhost:PORT`
   - **Subdomain mode**: `https://yoursubdomain.yourdomain.com`
   - Use credentials from signup

4. **Upgrade Plan**
   - Visit: `http://yoursite.com/saas/upgrade?subdomain=yoursubdomain`
   - Choose new plan
   - Wait for admin approval
   - New modules installed automatically

## Module Structure

```
saas_signup/
├── __init__.py
├── __manifest__.py
├── controllers/
│   ├── __init__.py
│   ├── main.py          # Signup and provisioning
│   └── upgrade.py       # Plan upgrade handling
├── models/
│   ├── __init__.py
│   ├── saas_client.py        # Tenant management
│   ├── saas_config.py        # Configuration
│   ├── saas_subscription.py  # Plans
│   └── saas_master_password_wizard.py
├── views/
│   ├── saas_signup_templates.xml    # Public signup page
│   ├── saas_client_views.xml        # Admin views
│   ├── saas_config_views.xml
│   ├── saas_config_settings_views.xml
│   └── upgrade_templates.xml        # Upgrade pages
├── data/
│   ├── subscription_plans_data.xml  # Default plans
│   └── upgrade_cron.xml             # Trial expiration cron
├── security/
│   └── ir.model.access.csv
├── static/
│   ├── src/
│   │   ├── css/
│   │   └── js/
│   └── description/
│       └── icon.png
└── README.md
```

## Subscription Plans

### Default Plans

**Free Trial** (Free, 14 days)
- 2 Users
- 500MB Storage
- Modules: Discuss, Employees, Point of Sale, Project, Sales, Expenses

**Starter** ($19/month)
- 5 Users
- 5GB Storage
- Additional modules: Payroll, Invoicing, Website, Dashboards, CRM

**Professional** ($49/month) - Popular
- 15 Users
- 20GB Storage
- All Starter modules

**Enterprise** ($99/month)
- Unlimited Users
- 100GB Storage
- All available modules

### Customizing Plans

1. Go to SaaS Management → Subscription Plans
2. Edit any plan
3. Modify features and pricing
4. Update module list (comma-separated technical names)
5. Save

## API Endpoints

### Public Endpoints
- `GET /saas/signup` - Signup form
- `POST /saas/signup/submit` - Process signup
- `GET /saas/pricing` - Pricing page
- `GET /saas/upgrade` - Upgrade page
- `POST /saas/upgrade/request` - Request upgrade

### Admin Endpoints (Require Login)
- SaaS Management menu items
- Client approval/rejection
- Plan management
- Configuration

## Troubleshooting

### Common Issues

**1. Container won't start**
- Check Docker is running: `docker ps`
- Check logs: `docker logs odoo_tenant_SUBDOMAIN`
- Verify port not in use

**2. Can't login to tenant**
- Verify credentials from signup
- Check container is running
- Check database exists

**3. Modules not installed**
- Verify plan has module_list configured
- Check provisioning logs
- Try reinstalling modules manually

**4. Subdomain not accessible**
- Verify DNS record
- Check Nginx configuration
- Test: `ping subdomain.yourdomain.com`

### Debug Mode

Enable debug logging:
```python
# In odoo.conf
log_level = debug
log_handler = :DEBUG
```

View logs:
```bash
docker logs -f odoo19-odoo19-1
```

## Security Considerations

1. **Admin Password**: Set strong master password in configuration
2. **Database Credentials**: Keep PostgreSQL credentials secure
3. **Docker Socket**: Module needs access to Docker socket
4. **SSL**: Always use HTTPS in production (subdomain mode)
5. **Firewall**: Restrict direct port access in production

## Performance Tips

1. **Resource Limits**: Set Docker container resource limits
2. **Database Pooling**: Configure PostgreSQL connection pooling
3. **Container Cleanup**: Remove stopped containers regularly
4. **Monitoring**: Monitor container resource usage

## Backup & Recovery

### Backup Tenant Database
```bash
docker exec odoo19-db-1 pg_dump -U odoo saas_SUBDOMAIN > backup.sql
```

### Restore Tenant Database
```bash
docker exec -i odoo19-db-1 psql -U odoo saas_SUBDOMAIN < backup.sql
```

## Updates & Upgrades

To update the module:
1. Stop Odoo
2. Replace module files
3. Restart Odoo
4. Upgrade module: Apps → SaaS Signup Module → Upgrade

## Support

For issues, questions, or feature requests:
- Check documentation
- Review logs
- Contact your system administrator

## License

LGPL-3

## Credits

Developed for Odoo 19 SaaS deployments.

## Changelog

### Version 19.0.1.2.0
- Added dual deployment mode (localhost/subdomain)
- Auto-detect domain on install
- Plan-based module installation
- Upgrade system with admin approval
- Trial expiration with automatic suspension
- Module restriction per plan
- Improved provisioning with verification
- Enhanced admin UI

### Version 19.0.1.1.0
- Initial release
- Basic signup and provisioning
- Docker-based multi-tenancy
- Admin approval workflow
