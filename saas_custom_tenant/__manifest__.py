# -*- coding: utf-8 -*-

{
    'name': 'SaaS Multi-Tenancy Platform',
    'summary': 'Complete customizable SaaS platform with configuration wizard',
    'description': """
        Odoo 19 SaaS Multi-Tenancy Platform
        ===================================

        A fully customizable SaaS platform that allows users to deploy their own
        multi-tenant Odoo instances with easy configuration through the UI.

        Key Features:
        =============

        🚀 **Easy Setup Wizard**
        • First-time installation guide
        • Step-by-step configuration
        • Automatic environment detection
        • One-click deployment setup

        ⚙️ **Flexible Configuration**
        • Custom master instance port
        • Configurable tenant port ranges
        • Subdomain or localhost deployment modes
        • SSL/HTTPS configuration options
        • Custom branding and themes

        🏢 **Multi-Tenant Management**
        • Unlimited tenant creation
        • Automatic database provisioning
        • Docker container isolation
        • Resource usage monitoring
        • Trial and subscription plans

        🎨 **Professional Branding**
        • Custom company logos and colors
        • Configurable email templates
        • White-label ready
        • Mobile-responsive design

        🔒 **Enterprise Security**
        • Isolated tenant environments
        • Secure credential management
        • SSL certificate management
        • Access control and permissions

        📊 **Monitoring & Analytics**
        • Tenant usage statistics
        • Performance monitoring
        • Automated backup systems
        • Resource allocation tracking

        🌐 **Multiple Deployment Modes**
        • Localhost development setup
        • Cloud hosting ready
        • Subdomain routing
        • Reverse proxy integration

        Perfect for:
        =============
        • SaaS providers
        • Multi-company deployments
        • Development agencies
        • Enterprise hosting
        • Educational institutions

        Installation:
        ============
        1. Install module from Odoo Apps store
        2. Follow the setup wizard
        3. Configure your settings
        4. Start deploying tenant instances!
    """,

    'category': 'Extra Tools',
    'version': '19.0.1.0.0',
    'author': 'Your Company Name',
    'website': 'https://yourcompany.com',
    'depends': [
        'base',
        'website',
        'auth_signup',
        'mail',
        'portal',
        'crm',
        'sale_management'
    ],
    'external_dependencies': {
        'python': ['docker', 'psycopg2-binary', 'passlib'],
    },
    'data': [
        # Security and access control
        'security/ir.model.access.csv',
        'security/security.xml',

        # Configuration data
        'data/default_config.xml',
        'data/subscription_plans.xml',
        'data/email_templates.xml',

        # Setup wizard
        'wizard/setup_wizard_views.xml',

        # Configuration views
        'views/tenant_config_views.xml',
        'views/subscription_plan_views.xml',
        'views/tenant_management_views.xml',
        'views/dashboard_views.xml',

        # Website views
        'views/website_templates.xml',
        'views/website_menu.xml',

        # Reports
        'views/report_templates.xml',
    ],
    'demo': [
        'data/demo_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'saas_custom_tenant/static/src/css/tenant_admin.css',
            'saas_custom_tenant/static/src/js/tenant_dashboard.js',
            'saas_custom_tenant/static/src/js/setup_wizard.js',
        ],
        'web.assets_frontend': [
            'saas_custom_tenant/static/src/css/tenant_portal.css',
            'saas_custom_tenant/static/src/js/tenant_signup.js',
        ],
        'web.qunit_suite_tests': [
            'saas_custom_tenant/static/tests/**/*.js',
        ],
    },
    'images': [
        'static/description/banner.png',
        'static/description/setup_wizard.png',
        'static/description/dashboard.png',
        'static/description/tenant_management.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'pre_init_hook': 'pre_init_hook',
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'sequence': 100,
}