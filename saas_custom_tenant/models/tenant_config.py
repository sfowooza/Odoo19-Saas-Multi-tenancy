# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging
import socket
import subprocess

_logger = logging.getLogger(__name__)


class TenantConfiguration(models.Model):
    _name = 'saas.tenant.config'
    _description = 'SaaS Tenant Configuration'
    _rec_name = 'company_name'
    _order = 'create_date desc'

    # Company Information
    company_name = fields.Char(string='Company Name', required=True,
                             help='Your company name for branding')
    company_logo = fields.Binary(string='Company Logo', attachment=True,
                               help='Upload your company logo for branding')
    company_email = fields.Char(string='Company Email', required=True,
                               help='Email for system notifications')
    company_phone = fields.Char(string='Company Phone',
                               help='Contact phone number')
    company_website = fields.Char(string='Company Website',
                                 help='Your company website URL')

    # Master Instance Configuration
    master_port = fields.Integer(string='Master Port', required=True, default=8069,
                               help='Port for the main Odoo instance (usually 8069)')
    master_host = fields.Char(string='Master Host', required=True, default='localhost',
                             help='Hostname or IP where master instance runs')

    # Tenant Port Configuration
    tenant_port_start = fields.Integer(string='Tenant Port Start', required=True, default=8000,
                                    help='Starting port number for tenant instances')
    tenant_port_end = fields.Integer(string='Tenant Port End', required=True, default=9000,
                                  help='Ending port number for tenant instances')
    max_tenants = fields.Integer(string='Maximum Tenants', default=1000,
                               help='Maximum number of tenants allowed')

    # Deployment Mode
    deployment_mode = fields.Selection([
        ('localhost', 'Localhost - Port Based'),
        ('subdomain', 'Subdomain - Domain Based'),
        ('hybrid', 'Hybrid - Both Ports and Subdomains')
    ], string='Deployment Mode', required=True, default='localhost',
       help='Choose how tenants will be accessed')

    # Domain Configuration (for subdomain mode)
    main_domain = fields.Char(string='Main Domain',
                            help='Your main domain for subdomain-based deployment (e.g., yourcompany.com)')
    use_ssl = fields.Boolean(string='Use SSL/HTTPS', default=False,
                           help='Enable SSL for tenant instances')
    ssl_cert_path = fields.Char(string='SSL Certificate Path',
                               help='Path to SSL certificate file')
    ssl_key_path = fields.Char(string='SSL Private Key Path',
                              help='Path to SSL private key file')

    # Database Configuration
    db_host = fields.Char(string='Database Host', required=True, default='localhost',
                         help='Database server hostname')
    db_port = fields.Integer(string='Database Port', required=True, default=5432,
                           help='Database server port')
    db_user = fields.Char(string='Database User', required=True, default='odoo',
                         help='Database username')
    db_password = fields.Char(string='Database Password', password=True,
                             help='Database password (will be encrypted)')
    db_template = fields.Char(string='Database Template', default='template1',
                            help='Database template for new tenant databases')

    # Docker Configuration
    docker_network = fields.Char(string='Docker Network', default='saas-network',
                                help='Docker network name for tenant containers')
    docker_image = fields.Char(string='Docker Image', default='odoo:19',
                             help='Docker image to use for tenant instances')
    container_memory_limit = fields.Char(string='Container Memory Limit', default='1g',
                                       help='Memory limit per tenant container')
    container_cpu_limit = fields.Char(string='Container CPU Limit', default='1.0',
                                    help='CPU limit per tenant container')

    # Email Configuration
    email_from = fields.Char(string='Email From', required=True,
                           help='Email address for sending notifications')
    smtp_server = fields.Char(string='SMTP Server', required=True,
                           help='SMTP server for email sending')
    smtp_port = fields.Integer(string='SMTP Port', default=587,
                             help='SMTP port')
    smtp_use_ssl = fields.Boolean(string='Use SSL/TLS', default=True,
                                 help='Use SSL/TLS for SMTP')

    # Features Configuration
    enable_trials = fields.Boolean(string='Enable Free Trials', default=True,
                                 help='Allow users to sign up for free trials')
    trial_days = fields.Integer(string='Trial Days', default=14,
                              help='Number of days for free trial')
    auto_approve = fields.Boolean(string='Auto-Approve Tenants', default=False,
                                help='Automatically approve new tenant requests')
    enable_monitoring = fields.Boolean(string='Enable Monitoring', default=True,
                                     help='Monitor tenant resource usage')
    enable_backups = fields.Boolean(string='Enable Backups', default=True,
                                  help='Enable automatic backups')

    # Branding Configuration
    primary_color = fields.Char(string='Primary Color', default='#007bff',
                               help='Primary theme color')
    secondary_color = fields.Char(string='Secondary Color', default='#6c757d',
                                help='Secondary theme color')
    custom_css = fields.Text(string='Custom CSS',
                           help='Additional CSS for custom styling')

    # Status and System Fields
    is_configured = fields.Boolean(string='Is Configured', default=False,
                                help='Whether the system has been configured')
    is_active = fields.Boolean(string='Active', default=True,
                             help='Whether this configuration is active')
    setup_complete = fields.Boolean(string='Setup Complete', default=False,
                                   help='Whether initial setup is complete')

    # Computed fields
    total_tenants = fields.Integer(string='Total Tenants', compute='_compute_total_tenants')
    active_tenants = fields.Integer(string='Active Tenants', compute='_compute_active_tenants')
    available_ports = fields.Integer(string='Available Ports', compute='_compute_available_ports')

    @api.depends('deployment_mode', 'tenant_port_start', 'tenant_port_end')
    def _compute_available_ports(self):
        """Calculate available tenant ports"""
        for record in self:
            if record.deployment_mode in ['localhost', 'hybrid']:
                record.available_ports = record.tenant_port_end - record.tenant_port_start + 1
            else:
                record.available_ports = 0

    def _compute_total_tenants(self):
        """Calculate total number of tenants"""
        Tenant = self.env['saas.tenant.instance']
        for record in self:
            record.total_tenants = Tenant.search_count([])

    def _compute_active_tenants(self):
        """Calculate number of active tenants"""
        Tenant = self.env['saas.tenant.instance']
        for record in self:
            record.active_tenants = Tenant.search_count([('state', '=', 'active')])

    @api.constrains('tenant_port_start', 'tenant_port_end')
    def _check_port_range(self):
        """Validate port range"""
        for record in self:
            if record.tenant_port_start >= record.tenant_port_end:
                raise ValidationError(_('Tenant Port Start must be less than Tenant Port End'))
            if record.tenant_port_start < 1024 or record.tenant_port_end > 65535:
                raise ValidationError(_('Port numbers must be between 1024 and 65535'))
            available_ports = record.tenant_port_end - record.tenant_port_start + 1
            if available_ports < record.max_tenants:
                raise ValidationError(_('Port range (%d ports) cannot accommodate maximum tenants (%d)') %
                                    (available_ports, record.max_tenants))

    @api.constrains('master_port')
    def _check_master_port(self):
        """Validate master port"""
        for record in self:
            if record.master_port < 1 or record.master_port > 65535:
                raise ValidationError(_('Master Port must be between 1 and 65535'))

    @api.constrains('main_domain')
    def _check_main_domain(self):
        """Validate main domain for subdomain mode"""
        for record in self:
            if record.deployment_mode in ['subdomain', 'hybrid'] and not record.main_domain:
                raise ValidationError(_('Main Domain is required for subdomain-based deployment'))

    def action_test_connection(self):
        """Test database and system connectivity"""
        self.ensure_one()

        try:
            # Test database connection
            import psycopg2
            conn = psycopg2.connect(
                host=self.db_host,
                port=self.db_port,
                database='postgres',
                user=self.db_user,
                password=self.db_password
            )
            conn.close()

            # Test port availability
            if self.deployment_mode in ['localhost', 'hybrid']:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex((self.master_host, self.master_port))
                sock.close()

                if result != 0:
                    raise UserError(_('Cannot connect to master instance at %s:%s') %
                                  (self.master_host, self.master_port))

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Test Successful'),
                    'message': _('All systems are properly configured!'),
                    'type': 'success',
                }
            }

        except Exception as e:
            raise UserError(_('Connection test failed: %s') % str(e))

    def action_save_configuration(self):
        """Save and apply configuration"""
        self.ensure_one()

        # Validate all settings
        self._check_port_range()
        self._check_master_port()
        if self.deployment_mode in ['subdomain', 'hybrid']:
            self._check_main_domain()

        # Mark as configured and setup complete
        self.is_configured = True
        self.setup_complete = True

        # Create default subscription plans if none exist
        if not self.env['saas.subscription.plan'].search_count([]):
            self._create_default_plans()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Configuration Saved'),
                'message': _('Your SaaS platform is now ready!'),
                'type': 'success',
            }
        }

    def _create_default_plans(self):
        """Create default subscription plans"""
        Plan = self.env['saas.subscription.plan']

        plans = [
            {
                'name': 'Starter',
                'description': 'Perfect for small businesses',
                'price': 29.99,
                'max_users': 5,
                'storage_gb': 10,
                'trial_days': 14,
                'sequence': 1,
                'is_active': True,
            },
            {
                'name': 'Professional',
                'description': 'Ideal for growing businesses',
                'price': 79.99,
                'max_users': 20,
                'storage_gb': 50,
                'trial_days': 14,
                'sequence': 2,
                'is_active': True,
            },
            {
                'name': 'Enterprise',
                'description': 'For large organizations',
                'price': 199.99,
                'max_users': 100,
                'storage_gb': 200,
                'trial_days': 21,
                'sequence': 3,
                'is_active': True,
            }
        ]

        for plan_data in plans:
            Plan.create(plan_data)

    def action_refresh_stats(self):
        """Refresh tenant statistics"""
        # This will trigger computed fields to recalculate
        self._compute_total_tenants()
        self._compute_active_tenants()
        self._compute_available_ports()

    @api.model
    def get_current_config(self):
        """Get current active configuration"""
        config = self.search([('is_active', '=', True)], limit=1)
        if not config:
            config = self.create({
                'company_name': 'Your Company',
                'company_email': 'admin@yourcompany.com',
                'is_active': True,
            })
        return config

    def get_next_available_port(self):
        """Get next available tenant port"""
        self.ensure_one()

        if self.deployment_mode not in ['localhost', 'hybrid']:
            return None

        Tenant = self.env['saas.tenant.instance']
        used_ports = Tenant.search([]).mapped('port')

        for port in range(self.tenant_port_start, self.tenant_port_end + 1):
            if port not in used_ports:
                return port

        return None

    def generate_tenant_url(self, subdomain, port=None):
        """Generate tenant URL based on deployment mode"""
        self.ensure_one()

        if self.deployment_mode == 'localhost' and port:
            protocol = 'https' if self.use_ssl else 'http'
            return f"{protocol}://{self.main_host}:{port}"
        elif self.deployment_mode in ['subdomain', 'hybrid'] and self.main_domain:
            protocol = 'https' if self.use_ssl else 'http'
            return f"{protocol}://{subdomain}.{self.main_domain}"
        else:
            return None