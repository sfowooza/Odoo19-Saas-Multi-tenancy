# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging
import socket

_logger = logging.getLogger(__name__)


class SaaSSetupWizard(models.TransientModel):
    _name = 'saas.setup.wizard'
    _description = 'SaaS Platform Setup Wizard'
    _order = 'step'

    # Step tracking
    step = fields.Integer(string='Current Step', default=1)
    total_steps = fields.Integer(string='Total Steps', default=4)

    # Step 1: Welcome and Basic Info
    welcome_message = fields.Text(string='Welcome Message', readonly=True,
                                 default='Welcome to SaaS Multi-Tenancy Platform Setup!\n\n'
                                         'This wizard will guide you through configuring your '
                                         'SaaS platform. It should only take a few minutes.')
    company_name = fields.Char(string='Company Name', required=True,
                               help='Your company name for branding')
    company_email = fields.Char(string='Company Email', required=True,
                               help='Email for system notifications')
    company_logo = fields.Binary(string='Company Logo', attachment=True,
                               help='Upload your company logo for branding')

    # Step 2: Deployment Configuration
    deployment_mode = fields.Selection([
        ('localhost', 'Localhost - Port Based (Recommended for development)'),
        ('subdomain', 'Subdomain - Domain Based (Recommended for production)'),
        ('hybrid', 'Hybrid - Both Ports and Subdomains')
    ], string='Deployment Mode', required=True, default='localhost',
       help='Choose how tenants will be accessed')

    master_port = fields.Integer(string='Master Port', required=True, default=8069,
                               help='Port for the main Odoo instance (usually 8069)')
    master_host = fields.Char(string='Master Host', required=True, default='localhost',
                             help='Hostname or IP where master instance runs')

    tenant_port_start = fields.Integer(string='Tenant Port Start', required=True, default=8000,
                                    help='Starting port number for tenant instances')
    tenant_port_end = fields.Integer(string='Tenant Port End', required=True, default=9000,
                                  help='Ending port number for tenant instances')
    max_tenants = fields.Integer(string='Maximum Tenants', default=1000,
                               help='Maximum number of tenants allowed')

    # Domain Configuration (for subdomain mode)
    main_domain = fields.Char(string='Main Domain',
                            help='Your main domain for subdomain-based deployment (e.g., yourcompany.com)')
    use_ssl = fields.Boolean(string='Use SSL/HTTPS', default=False,
                           help='Enable SSL for tenant instances')

    # Step 3: Database Configuration
    db_host = fields.Char(string='Database Host', required=True, default='localhost',
                         help='Database server hostname')
    db_port = fields.Integer(string='Database Port', required=True, default=5432,
                           help='Database server port')
    db_user = fields.Char(string='Database User', required=True, default='odoo',
                         help='Database username')
    db_password = fields.Char(string='Database Password', password=True,
                             help='Database password')
    test_connection = fields.Boolean(string='Test Database Connection', default=True)

    # Step 4: Final Configuration
    enable_trials = fields.Boolean(string='Enable Free Trials', default=True,
                                 help='Allow users to sign up for free trials')
    trial_days = fields.Integer(string='Trial Days', default=14,
                              help='Number of days for free trial')
    auto_approve = fields.Boolean(string='Auto-Approve Tenants', default=False,
                                help='Automatically approve new tenant requests')
    enable_monitoring = fields.Boolean(string='Enable Monitoring', default=True,
                                     help='Monitor tenant resource usage')

    # Email Configuration
    configure_email = fields.Boolean(string='Configure Email', default=True)
    email_from = fields.Char(string='Email From', default='noreply@yourcompany.com',
                           help='Email address for sending notifications')

    # State tracking
    config_id = fields.Many2one('saas.tenant.config', string='Configuration')

    @api.model
    def default_get(self, fields):
        """Set default values"""
        res = super(SaaSSetupWizard, self).default_get(fields)

        # Try to get existing configuration
        config = self.env['saas.tenant.config'].search([], limit=1)
        if config:
            for field in ['company_name', 'company_email', 'company_logo', 'deployment_mode',
                         'master_port', 'master_host', 'tenant_port_start', 'tenant_port_end',
                         'max_tenants', 'main_domain', 'use_ssl', 'db_host', 'db_port',
                         'db_user', 'db_password', 'enable_trials', 'trial_days',
                         'auto_approve', 'enable_monitoring', 'email_from']:
                if hasattr(config, field):
                    res[field] = getattr(config, field)

        return res

    def action_next(self):
        """Move to next step"""
        self.ensure_one()

        if self.step == 1:
            self._validate_step1()
            self.step = 2
        elif self.step == 2:
            self._validate_step2()
            self.step = 3
        elif self.step == 3:
            self._validate_step3()
            self.step = 4
        elif self.step == 4:
            return self.action_complete()

        return self._refresh_wizard()

    def action_previous(self):
        """Move to previous step"""
        self.ensure_one()
        if self.step > 1:
            self.step -= 1
        return self._refresh_wizard()

    def action_test_db_connection(self):
        """Test database connection"""
        self.ensure_one()

        try:
            import psycopg2
            conn = psycopg2.connect(
                host=self.db_host,
                port=self.db_port,
                database='postgres',
                user=self.db_user,
                password=self.db_password
            )
            conn.close()

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Test Successful'),
                    'message': _('Database connection is working correctly!'),
                    'type': 'success',
                }
            }

        except Exception as e:
            raise ValidationError(_('Database connection failed: %s') % str(e))

    def action_test_ports(self):
        """Test port availability"""
        self.ensure_one()
        errors = []

        # Test master port
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex((self.master_host, self.master_port))
            sock.close()

            if result != 0:
                errors.append(_('Cannot connect to master instance at %s:%s') % (self.master_host, self.master_port))
        except Exception as e:
            errors.append(_('Master port test failed: %s') % str(e))

        if errors:
            raise ValidationError(_('Port test failed:\n%s') % '\n'.join(errors))
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Port Test Successful'),
                    'message': _('All ports are accessible!'),
                    'type': 'success',
                }
            }

    def action_complete(self):
        """Complete setup and save configuration"""
        self.ensure_one()
        self._validate_step4()

        # Create or update configuration
        config_data = {
            'company_name': self.company_name,
            'company_email': self.company_email,
            'company_logo': self.company_logo,
            'deployment_mode': self.deployment_mode,
            'master_port': self.master_port,
            'master_host': self.master_host,
            'tenant_port_start': self.tenant_port_start,
            'tenant_port_end': self.tenant_port_end,
            'max_tenants': self.max_tenants,
            'main_domain': self.main_domain,
            'use_ssl': self.use_ssl,
            'db_host': self.db_host,
            'db_port': self.db_port,
            'db_user': self.db_user,
            'db_password': self.db_password,
            'enable_trials': self.enable_trials,
            'trial_days': self.trial_days,
            'auto_approve': self.auto_approve,
            'enable_monitoring': self.enable_monitoring,
            'email_from': self.email_from,
            'is_configured': True,
            'setup_complete': True,
            'is_active': True,
        }

        if self.config_id:
            self.config_id.write(config_data)
            config = self.config_id
        else:
            config = self.env['saas.tenant.config'].create(config_data)

        # Create default subscription plans
        config._create_default_plans()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Setup Complete!'),
                'message': _('Your SaaS platform is now configured and ready to use!'),
                'type': 'success',
                'sticky': True,
            }
        }

    def _validate_step1(self):
        """Validate step 1"""
        if not self.company_name:
            raise ValidationError(_('Company Name is required'))
        if not self.company_email:
            raise ValidationError(_('Company Email is required'))

    def _validate_step2(self):
        """Validate step 2"""
        if not self.deployment_mode:
            raise ValidationError(_('Please select a deployment mode'))

        if self.tenant_port_start >= self.tenant_port_end:
            raise ValidationError(_('Tenant Port Start must be less than Tenant Port End'))

        available_ports = self.tenant_port_end - self.tenant_port_start + 1
        if available_ports < self.max_tenants:
            raise ValidationError(_('Port range (%d ports) cannot accommodate maximum tenants (%d)') %
                                (available_ports, self.max_tenants))

        if self.deployment_mode in ['subdomain', 'hybrid'] and not self.main_domain:
            raise ValidationError(_('Main Domain is required for subdomain-based deployment'))

    def _validate_step3(self):
        """Validate step 3"""
        if not self.db_host or not self.db_user:
            raise ValidationError(_('Database Host and User are required'))

        if self.test_connection:
            self.action_test_db_connection()

    def _validate_step4(self):
        """Validate step 4"""
        if self.enable_trials and not self.trial_days:
            raise ValidationError(_('Trial Days must be specified when trials are enabled'))

    def _refresh_wizard(self):
        """Refresh the wizard view"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'SaaS Platform Setup',
            'res_model': 'saas.setup.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context,
        }

    @api.model
    def create(self, vals):
        """Create wizard and set config_id if exists"""
        if 'config_id' not in vals:
            config = self.env['saas.tenant.config'].search([], limit=1)
            if config:
                vals['config_id'] = config.id
        return super(SaaSSetupWizard, self).create(vals)