{
    'name': 'SaaS Signup Module - Enterprise Edition',
    'icon': '/saas_signup/static/description/icon.png',
    'version': '19.0.2.0.0',
    'summary': 'Complete Multi-Tenant SaaS Platform with Localhost & Subdomain Support',
    'description': """
        Odoo 19 SaaS Signup Module
        ==========================
        Complete multi-tenant SaaS platform for Odoo 19
        
        Features:
        - Dual deployment modes: Localhost (ports) or Subdomain (cloud)
        - Docker-based tenant isolation with dynamic port assignment
        - Automatic Nginx reverse proxy configuration (subdomain → port mapping)
        - Plan-based module installation
        - Trial management with auto-expiration
        - Upgrade system with admin approval
        - Module restriction per subscription plan
        - Background provisioning for instant signup
        - Admin approval workflow
        - Complete lifecycle management (create, suspend, reactivate, delete)
        
        Perfect for creating your own Odoo SaaS platform!
    """,
    'category': 'Website/Website',
    'author': 'Avodah Systems',
    'website': 'https://avodahsystems.com',
    'depends': [
        'base',
        'website',
        'auth_signup',
        'mail',
        'portal'
    ],
    'external_dependencies': {
        'python': ['docker', 'psycopg2'],
    },
    'data': [
        'security/ir.model.access.csv',
        'data/saas_config_data.xml',             # Default SaaS configuration
        'data/subscription_plans_data.xml',
        'data/upgrade_cron.xml',
        'data/saas_cron.xml',                    # Resource monitoring crons
        'views/saas_config_views.xml',           # Load first - defines actions
        'views/saas_client_views.xml',           # Load second - defines client views
        'views/saas_config_settings_views.xml',  # Load third - defines menu items
        'views/saas_config_list_views.xml',      # Configuration list view (after menu defined)
        'views/saas_dashboard_views.xml',        # Dashboard views
        'views/saas_setup_wizard_views.xml',     # Setup wizard
        'views/website_menu_views.xml',          # Website navigation menus
        'views/saas_signup_templates.xml',
        'views/upgrade_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'saas_signup/static/src/css/saas_signup.css',
            'saas_signup/static/src/js/saas_signup.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'post_init_hook': 'post_init_hook',
    'images': ['static/description/icon.png'],
}