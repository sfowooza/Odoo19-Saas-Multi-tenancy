# Odoo 19 SaaS Multi-Tenancy Platform 🚀

A fully customizable SaaS platform that allows you to deploy your own multi-tenant Odoo instances with easy configuration through the UI.

## ✨ Key Features

### 🔧 **Easy Setup Wizard**
- **Step-by-step configuration** - No technical knowledge required
- **Environment detection** - Automatically detects your setup
- **Connection testing** - Validate database and port connectivity
- **One-click deployment** - Start deploying tenants immediately

### ⚙️ **Flexible Configuration**
- **Custom master port** - Set your main Odoo instance port
- **Configurable port ranges** - Define tenant port ranges (8000-9000, etc.)
- **Multiple deployment modes** - Localhost, subdomain, or hybrid
- **SSL/HTTPS support** - Secure tenant deployments
- **Database configuration** - Flexible database settings

### 🏢 **Multi-Tenant Management**
- **Unlimited tenants** - Scale as your business grows
- **Automatic provisioning** - Background tenant creation
- **Docker isolation** - Secure container-based deployment
- **Resource monitoring** - Track usage and performance
- **Trial management** - Built-in trial period support

### 🎨 **Professional Branding**
- **Custom company logo** - Add your own branding
- **Color themes** - Customize look and feel
- **Email templates** - Professional communications
- **White-label ready** - Perfect for resellers

### 🔒 **Enterprise Security**
- **Isolated environments** - Each tenant is fully isolated
- **Secure credentials** - Encrypted password management
- **Access control** - Role-based permissions
- **SSL certificates** - Secure tenant communications

## 🚀 Quick Start

### Installation

1. **Install Module**
   - Download from Odoo Apps store
   - Install in your Odoo instance
   - Setup wizard will start automatically

2. **Run Setup Wizard**
   - Configure company information
   - Set deployment preferences
   - Configure database connection
   - Choose trial/subscription settings

3. **Start Deploying**
   - Create subscription plans
   - Set up pricing tiers
   - Begin accepting tenant signups

### Requirements

- **Odoo 19** - Latest Odoo 19 version
- **Docker** - For container isolation
- **PostgreSQL** - Database server
- **Python 3.8+** - Required Python version

### Installation Commands

```bash
# Clone the repository
git clone https://github.com/sfowooza/Odoo19-Saas-Multi-tenancy.git

# Copy to your Odoo addons directory
cp -r Odoo19-Saas-Multi-tenancy/saas_custom_tenant /path/to/odoo/addons/

# Update module list
./odoo-bin -d your_database -u base --stop-after-init

# Install module through Odoo UI or CLI
./odoo-bin -d your_database -i saas_custom_tenant --stop-after-init
```

## 📋 Configuration Options

### Deployment Modes

1. **Localhost (Port-Based)**
   - Tenants accessible via different ports
   - Example: `localhost:8001`, `localhost:8002`
   - Perfect for development and internal hosting

2. **Subdomain (Domain-Based)**
   - Tenants accessible via subdomains
   - Example: `client1.yourdomain.com`, `client2.yourdomain.com`
   - Ideal for production SaaS platforms

3. **Hybrid Mode**
   - Both ports and subdomains supported
   - Maximum flexibility for different use cases

### Port Configuration

- **Master Port**: Your main Odoo instance (default: 8069)
- **Tenant Range**: Starting and ending ports for tenants
- **Auto Assignment**: Automatic port allocation
- **Conflict Detection**: Prevents port conflicts

### Database Setup

- **Host**: Database server address
- **Port**: Database server port (default: 5432)
- **User**: Database username (default: odoo)
- **Password**: Secure database password
- **Template**: Database template for new tenants

## 💼 Use Cases

### **SaaS Providers**
- Offer Odoo as a service to clients
- Automated tenant provisioning
- Subscription billing integration

### **Multi-Company Deployments**
- Separate Odoo instances per company
- Centralized administration
- Resource allocation control

### **Development Agencies**
- Quick client demo environments
- Isolated development spaces
- Easy client onboarding

### **Educational Institutions**
- Separate instances per class/student
- Academic license management
- Resource usage monitoring

## 📊 Features Overview

| Feature | Description |
|---------|-------------|
| **Auto-Provisioning** | Automatic tenant database and container creation |
| **Port Management** | Dynamic port assignment and conflict detection |
| **Trial Management** | Built-in free trial periods with auto-expiry |
| **Monitoring** | Real-time resource usage and performance tracking |
| **Backup System** | Automated backups and disaster recovery |
| **Email Integration** | Automated emails for trials, renewals, and notifications |
| **API Access** | RESTful API for integration with external systems |
| **Multi-Language** | Support for multiple languages and currencies |
| **Mobile Responsive** | Works on all devices and screen sizes |

## 🔧 Advanced Configuration

### Docker Settings

```yaml
# Docker Network Configuration
network: saas-network
image: odoo:19
memory_limit: 1g
cpu_limit: 1.0
```

### SSL Configuration

```bash
# SSL Certificate Paths
ssl_cert_path: /path/to/cert.pem
ssl_key_path: /path/to/key.pem
```

### Email Templates

- Welcome emails for new tenants
- Trial expiry notifications
- Password reset emails
- Subscription renewal reminders

## 📈 Scalability

- **Horizontal Scaling**: Add more Odoo instances as needed
- **Load Balancing**: Nginx load balancer configuration
- **Database Clustering**: PostgreSQL replication support
- **Container Orchestration**: Kubernetes integration ready

## 🔒 Security Features

- **Data Isolation**: Each tenant has separate database
- **Container Security**: Docker security best practices
- **Access Control**: Role-based permissions
- **SSL/TLS Encryption**: Secure data transmission
- **Password Security**: Encrypted credential storage

## 📞 Support

- **Documentation**: Complete user guide and API documentation
- **Community**: Active user community and forums
- **Updates**: Regular updates with new features and security patches
- **Enterprise**: Premium support available for enterprise deployments

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## 📄 License

This module is licensed under the LGPL-3 License. See [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- Odoo SA for the excellent Odoo framework
- Docker team for containerization technology
- PostgreSQL for reliable database management
- Our amazing community of users and contributors

---

**Made with ❤️ by Your Company**

*Transform your Odoo deployment into a professional SaaS platform today!*