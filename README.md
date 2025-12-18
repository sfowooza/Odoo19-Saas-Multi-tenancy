# 🏢 Odoo 19 SaaS Multi-Tenancy Platform

[![License](https://img.shields.io/badge/License-LGPL%203-blue.svg)](LICENSE)
[![Odoo Version](https://img.shields.io/badge/Odoo-19.0-green.svg)](https://www.odoo.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)

A complete, production-ready SaaS multi-tenancy platform for Odoo 19 that allows you to create and manage multiple Odoo instances with ease. Perfect for building your own SaaS business or providing multi-tenant solutions to clients.

## ✨ Features

### 🚀 Core Features
- **Dual Deployment Modes**: Localhost (ports) or Subdomain (cloud)
- **Docker-based Tenant Isolation**: Each tenant gets a dedicated container
- **Automatic Port Assignment**: Dynamic port allocation for tenant instances
- **Nginx Reverse Proxy**: Automatic subdomain → port mapping
- **Background Provisioning**: Instant signup with async tenant creation
- **Database Management**: Automatic database creation per tenant

### 💼 Business Features
- **Subscription Plans**: Create multiple pricing tiers (Free, Basic, Professional, Enterprise)
- **Trial Management**: Configurable trial periods with auto-expiration
- **Module Restrictions**: Control which Odoo modules are available per plan
- **Upgrade System**: Admin approval workflow for plan upgrades
- **Resource Monitoring**: CPU, memory, and storage tracking
- **Admin Dashboard**: Complete tenant lifecycle management

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Git
- 4GB+ RAM (for multiple tenants)

### Installation (5 Minutes)

1. **Clone the Repository**
   ```bash
   git clone https://github.com/sfowooza/Odoo19-Saas-Multi-tenancy.git
   cd Odoo19-Saas-Multi-tenancy
   ```

2. **Start the Platform**
   ```bash
   docker-compose up -d
   ```

3. **Access Your SaaS Platform**
   - **Main App**: http://localhost:7001
   - **Admin Panel**: http://localhost:7001/web
   - **pgAdmin**: http://localhost:5050 (admin@odoo.com / admin)

4. **Install the SaaS Module**
   - Go to http://localhost:7001/web
   - Login with admin/admin
   - Navigate to Apps → Remove "Apps" filter
   - Search for "SaaS Signup Module"
   - Click Install

That's it! Your SaaS platform is ready to accept tenant sign-ups.

## 📱 Using the Platform

### For Users (Tenant Sign-up)
1. Go to http://localhost:7001/saas/signup
2. Fill in your company details
3. Choose a subscription plan
4. Your Odoo instance will be created automatically
5. Access your instance at the provided URL

### For Administrators
1. **Setup Configuration**: Go to Settings → SaaS Configuration
2. **Configure Plans**: Create custom subscription plans
3. **Manage Tenants**: View, suspend, or delete tenant instances
4. **Monitor Resources**: Track resource usage across all tenants
5. **Approve Upgrades**: Review and approve tenant upgrade requests

## 🛠️ One-Click Installation

For automatic setup, run our installer:

```bash
curl -fsSL https://raw.githubusercontent.com/sfowooza/Odoo19-Saas-Multi-tenancy/main/install.sh | bash
```

## 📁 Project Structure

```
Odoo19-Saas-Multi-tenancy/
├── saas_signup/                 # Main SaaS module
│   ├── controllers/             # HTTP routes and APIs
│   ├── models/                  # Data models
│   ├── views/                   # UI views and templates
│   ├── static/                  # CSS, JS, images
│   └── data/                    # Default configurations
├── config/                     # Odoo configuration
├── docker-compose.yml          # Docker services
├── install.sh                  # Quick installer
├── SETUP.md                   # Detailed setup guide
├── DEVELOPMENT.md              # Development guide
└── README.md                  # This file
```

## 📚 Documentation

- **[SETUP.md](SETUP.md)**: Detailed installation and configuration guide
- **[DEVELOPMENT.md](DEVELOPMENT.md)**: Development and customization guide
- **[Issues](https://github.com/sfowooza/Odoo19-Saas-Multi-tenancy/issues)**: Report bugs and request features

## 🔧 Configuration & Customization

### Quick Configuration
1. Edit `docker-compose.yml` to customize ports and passwords
2. Go to Settings → SaaS Configuration in Odoo admin panel
3. Configure your subscription plans and deployment settings

### Customization Options
- Add new subscription plans
- Customize sign-up forms
- Extend tenant functionality
- Add custom modules to plans

For detailed customization instructions, see [DEVELOPMENT.md](DEVELOPMENT.md).

## 🚀 Advanced Features

### Production Deployment
- SSL/HTTPS support
- Load balancing
- Auto-scaling
- Backup strategies

### Monitoring & Management
- Resource usage tracking
- Tenant analytics
- Performance monitoring
- Automated alerts

See [SETUP.md](SETUP.md) for production deployment guide.

## 🤝 Contributing

We welcome contributions! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the LGPL-3 License. See [LICENSE](LICENSE) for details.

## 🙏 Support

- **Documentation**: [README.md](README.md), [SETUP.md](SETUP.md), [DEVELOPMENT.md](DEVELOPMENT.md)
- **Issues**: [GitHub Issues](https://github.com/sfowooza/Odoo19-Saas-Multi-tenancy/issues)
- **Community**: [GitHub Discussions](https://github.com/sfowooza/Odoo19-Saas-Multi-tenancy/discussions)

---

**⭐ Star this repository if it helps you build your SaaS business!**

Made with ❤️ for the Odoo community
