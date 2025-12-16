# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging
import docker
import psycopg2
from passlib.context import CryptContext
import threading
import time

_logger = logging.getLogger(__name__)


class TenantInstance(models.Model):
    _name = 'saas.tenant.instance'
    _description = 'SaaS Tenant Instance'
    _order = 'create_date desc'
    _rec_name = 'company_name'

    # Tenant Information
    company_name = fields.Char(string='Company Name', required=True,
                              help='Tenant company name')
    subdomain = fields.Char(string='Subdomain', required=True,
                           help='Unique subdomain for the tenant')
    database_name = fields.Char(string='Database Name', required=True,
                              help='Name of the tenant database')
    admin_name = fields.Char(string='Admin Name', required=True,
                           help='Name of the tenant administrator')
    admin_email = fields.Char(string='Admin Email', required=True,
                            help='Email of the tenant administrator')
    admin_password = fields.Char(string='Admin Password', required=True,
                                help='Password for the tenant administrator (encrypted)')
    phone = fields.Char(string='Phone', help='Contact phone number')

    # Access Information
    port = fields.Integer(string='Port', help='Port number for tenant access')
    url = fields.Char(string='Access URL', compute='_compute_url', store=True,
                     help='URL to access the tenant instance')
    login_url = fields.Char(string='Login URL', compute='_compute_login_url', store=True,
                           help='Direct login URL for the tenant')

    # Plan and Subscription
    subscription_plan_id = fields.Many2one('saas.subscription.plan', string='Subscription Plan',
                                          required=True, help='Subscription plan for this tenant')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('provisioning', 'Provisioning'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('cancelled', 'Cancelled'),
        ('error', 'Error')
    ], string='Status', default='draft', required=True, help='Current status of the tenant')

    # Trial Information
    is_trial = fields.Boolean(string='Is Trial', default=True,
                             help='Whether this is a trial tenant')
    trial_end_date = fields.Date(string='Trial End Date',
                                help='Date when the trial period ends')
    subscription_start_date = fields.Date(string='Subscription Start Date',
                                          help='Date when the subscription starts')
    subscription_end_date = fields.Date(string='Subscription End Date',
                                        help='Date when the subscription ends')

    # Resource Limits
    max_users = fields.Integer(string='Maximum Users', default=10,
                              help='Maximum number of users allowed')
    storage_limit_gb = fields.Integer(string='Storage Limit (GB)', default=10,
                                     help='Storage limit in gigabytes')
    cpu_limit = fields.Float(string='CPU Limit', default=1.0,
                           help='CPU limit for this tenant')
    memory_limit = fields.Char(string='Memory Limit', default='1g',
                              help='Memory limit for this tenant')

    # Container Information
    container_id = fields.Char(string='Container ID', readonly=True,
                              help='Docker container ID')
    container_name = fields.Char(string='Container Name', readonly=True,
                                 help='Docker container name')
    volume_name = fields.Char(string='Volume Name', readonly=True,
                             help='Docker volume name for data persistence')

    # Partner and User Information
    partner_id = fields.Many2one('res.partner', string='Customer',
                                help='Customer partner record')
    user_ids = fields.One2many('res.users', 'tenant_id', string='Users',
                              help='Users associated with this tenant')

    # Monitoring and Usage
    last_access_date = fields.Datetime(string='Last Access Date', readonly=True,
                                      help='Last time the tenant accessed their instance')
    active_users_count = fields.Integer(string='Active Users Count', readonly=True,
                                       help='Number of currently active users')
    storage_used_gb = fields.Float(string='Storage Used (GB)', readonly=True,
                                   help='Current storage usage in GB')

    # System Fields
    notes = fields.Text(string='Notes', help='Additional notes about this tenant')
    error_message = fields.Text(string='Error Message', readonly=True,
                               help='Error message if provisioning failed')
    provisioning_log = fields.Text(string='Provisioning Log', readonly=True,
                                  help='Log of the provisioning process')

    # Computed Fields
    days_until_expiry = fields.Integer(string='Days Until Expiry', compute='_compute_expiry_info')
    is_expired = fields.Boolean(string='Is Expired', compute='_compute_expiry_info')
    storage_usage_percent = fields.Float(string='Storage Usage (%)', compute='_compute_storage_usage')

    @api.depends('deployment_mode', 'subdomain', 'port')
    def _compute_url(self):
        """Compute tenant access URL"""
        config = self.env['saas.tenant.config'].get_current_config()
        for record in self:
            record.url = config.generate_tenant_url(record.subdomain, record.port)

    @api.depends('url')
    def _compute_login_url(self):
        """Compute direct login URL"""
        for record in self:
            if record.url:
                record.login_url = f"{record.url}/web/login"
            else:
                record.login_url = ''

    @api.depends('trial_end_date', 'subscription_end_date', 'state')
    def _compute_expiry_info(self):
        """Compute expiry information"""
        today = fields.Date.today()
        for record in self:
            if record.state == 'cancelled':
                record.is_expired = True
                record.days_until_expiry = 0
                continue

            end_date = record.subscription_end_date or record.trial_end_date
            if end_date:
                delta = end_date - today
                record.days_until_expiry = delta.days
                record.is_expired = delta.days < 0
            else:
                record.days_until_expiry = False
                record.is_expired = False

    @api.depends('storage_used_gb', 'storage_limit_gb')
    def _compute_storage_usage(self):
        """Compute storage usage percentage"""
        for record in self:
            if record.storage_limit_gb > 0:
                record.storage_usage_percent = (record.storage_used_gb / record.storage_limit_gb) * 100
            else:
                record.storage_usage_percent = 0

    @api.model
    def create(self, vals):
        """Create tenant with validation"""
        # Ensure subdomain is unique
        if 'subdomain' in vals:
            existing = self.search([('subdomain', '=', vals['subdomain'])])
            if existing:
                raise ValidationError(_('Subdomain "%s" is already taken. Please choose another.') % vals['subdomain'])

        # Generate subdomain from company name if not provided
        if not vals.get('subdomain') and vals.get('company_name'):
            vals['subdomain'] = self._generate_subdomain(vals['company_name'])

        # Generate database name if not provided
        if not vals.get('database_name'):
            vals['database_name'] = f"saas_{vals.get('subdomain', 'unknown')}"

        # Generate admin password if not provided
        if not vals.get('admin_password'):
            vals['admin_password'] = self._generate_password()

        # Get plan defaults
        if vals.get('subscription_plan_id'):
            plan = self.env['saas.subscription.plan'].browse(vals['subscription_plan_id'])
            vals.update({
                'max_users': plan.max_users,
                'storage_limit_gb': plan.storage_gb,
                'cpu_limit': plan.cpu_limit,
                'memory_limit': plan.memory_limit,
            })

        tenant = super(TenantInstance, self).create(vals)

        # Set trial dates if it's a trial
        if tenant.is_trial:
            tenant._setup_trial_dates()

        return tenant

    def _generate_subdomain(self, company_name):
        """Generate a unique subdomain from company name"""
        import re
        # Remove special characters and convert to lowercase
        subdomain = re.sub(r'[^a-z0-9]', '', company_name.lower())

        # Ensure it's not empty
        if not subdomain:
            subdomain = 'tenant'

        # Ensure uniqueness
        base_subdomain = subdomain
        counter = 1
        while self.search([('subdomain', '=', subdomain)]):
            subdomain = f"{base_subdomain}{counter}"
            counter += 1

        return subdomain

    def _generate_password(self, length=12):
        """Generate a random password"""
        import random
        import string
        chars = string.ascii_letters + string.digits + '!@#$%^&*'
        password = ''.join(random.choices(chars, k=length))
        return password

    def _setup_trial_dates(self):
        """Setup trial dates based on configuration"""
        config = self.env['saas.tenant.config'].get_current_config()
        today = fields.Date.today()
        self.trial_end_date = today + timedelta(days=config.trial_days)

    def action_approve(self):
        """Approve tenant and start provisioning"""
        for record in self:
            if record.state != 'pending':
                raise UserError(_('Only pending tenants can be approved'))

            record.state = 'approved'
            record.action_start_provisioning()

    def action_reject(self, reason=''):
        """Reject tenant request"""
        for record in self:
            if record.state not in ['pending', 'approved']:
                raise UserError(_('Only pending or approved tenants can be rejected'))

            record.state = 'cancelled'
            if reason:
                record.notes = f"Rejected: {reason}\n\n{record.notes or ''}"

    def action_start_provisioning(self):
        """Start background provisioning process"""
        for record in self:
            if record.state != 'approved':
                raise UserError(_('Only approved tenants can be provisioned'))

            record.state = 'provisioning'

            # Start background provisioning
            thread = threading.Thread(target=record._provision_tenant, daemon=True)
            thread.start()

    def _provision_tenant(self):
        """Background tenant provisioning"""
        self.ensure_one()

        try:
            _logger.info(f"Starting provisioning for tenant: {self.subdomain}")

            config = self.env['saas.tenant.config'].get_current_config()

            # Step 1: Create database
            self._create_database(config)

            # Step 2: Initialize database
            self._initialize_database(config)

            # Step 3: Create admin user
            self._create_admin_user(config)

            # Step 4: Create Docker volume
            self._create_docker_volume(config)

            # Step 5: Create Docker container
            self._create_docker_container(config)

            # Step 6: Activate tenant
            self.state = 'active'
            self.subscription_start_date = fields.Date.today()

            _logger.info(f"Successfully provisioned tenant: {self.subdomain}")

        except Exception as e:
            _logger.error(f"Provisioning failed for {self.subdomain}: {e}", exc_info=True)
            self.state = 'error'
            self.error_message = str(e)
            self.provisioning_log = f"Provisioning failed: {str(e)}"

    def _create_database(self, config):
        """Create tenant database"""
        _logger.info(f"Creating database: {self.database_name}")

        conn = psycopg2.connect(
            host=config.db_host,
            port=config.db_port,
            database="postgres",
            user=config.db_user,
            password=config.db_password
        )
        conn.autocommit = True
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (self.database_name,))
        if not cursor.fetchone():
            cursor.execute(f'CREATE DATABASE "{self.database_name}"')

        cursor.close()
        conn.close()

    def _initialize_database(self, config):
        """Initialize database with Odoo structure"""
        _logger.info(f"Initializing database: {self.database_name}")

        # Use Docker to initialize database
        import docker
        client = docker.from_env()

        client.containers.run(
            config.docker_image,
            name=f"init_{self.subdomain}",
            remove=True,
            environment={
                'HOST': config.db_host,
                'PORT': str(config.db_port),
                'USER': config.db_user,
                'PASSWORD': config.db_password
            },
            command=f'odoo -d {self.database_name} -i base --stop-after-init --without-demo=all',
            network=config.docker_network
        )

    def _create_admin_user(self, config):
        """Create admin user with custom credentials"""
        _logger.info(f"Creating admin user for: {self.database_name}")

        pwd_context = CryptContext(schemes=['pbkdf2_sha512'], deprecated='auto')
        hashed_password = pwd_context.hash(self.admin_password)

        conn = psycopg2.connect(
            host=config.db_host,
            port=config.db_port,
            database=self.database_name,
            user=config.db_user,
            password=config.db_password
        )
        conn.autocommit = True
        cursor = conn.cursor()

        # Update admin user
        cursor.execute("""
            UPDATE res_users
            SET login = %s, password = %s
            WHERE id = 2
        """, (self.admin_email, hashed_password))

        # Update partner
        cursor.execute("""
            UPDATE res_partner
            SET name = %s, email = %s
            WHERE id = 3
        """, (self.admin_name, self.admin_email))

        cursor.close()
        conn.close()

    def _create_docker_volume(self, config):
        """Create Docker volume for data persistence"""
        _logger.info(f"Creating volume for: {self.subdomain}")

        import docker
        client = docker.from_env()

        self.volume_name = f"saas_{self.subdomain}_data"
        try:
            volume = client.volumes.create(name=self.volume_name)
            _logger.info(f"Created volume: {self.volume_name}")
        except Exception as e:
            _logger.warning(f"Volume creation warning: {e}")

    def _create_docker_container(self, config):
        """Create Docker container for the tenant"""
        _logger.info(f"Creating container for: {self.subdomain}")

        import docker
        client = docker.from_env()

        # Get next available port
        if config.deployment_mode in ['localhost', 'hybrid']:
            self.port = config.get_next_available_port()
            if not self.port:
                raise Exception("No available ports for tenant deployment")

        # Container configuration
        container_config = {
            'image': config.docker_image,
            'name': f"saas_{self.subdomain}",
            'detach': True,
            'environment': {
                'HOST': config.db_host,
                'PORT': str(config.db_port),
                'USER': config.db_user,
                'PASSWORD': config.db_password,
                'DATABASE': self.database_name
            },
            'volumes': {self.volume_name: {'bind': '/var/lib/odoo', 'mode': 'rw'}},
            'network': config.docker_network,
            'restart_policy': {'Name': 'unless-stopped'},
            'mem_limit': self.memory_limit,
        }

        # Add port mapping if using localhost mode
        if self.port:
            container_config['ports'] = {'8069/tcp': self.port}

        container = client.containers.run(**container_config)

        self.container_id = container.id[:12]
        self.container_name = container.name

        _logger.info(f"Created container: {self.container_name}")

    def action_suspend(self):
        """Suspend tenant"""
        self.ensure_one()

        if self.state != 'active':
            raise UserError(_('Only active tenants can be suspended'))

        # Stop Docker container
        if self.container_id:
            try:
                import docker
                client = docker.from_env()
                container = client.containers.get(self.container_id)
                container.stop()
                _logger.info(f"Suspended container for {self.subdomain}")
            except Exception as e:
                _logger.error(f"Error suspending container for {self.subdomain}: {e}")

        self.state = 'suspended'

    def action_activate(self):
        """Activate suspended tenant"""
        self.ensure_one()

        if self.state != 'suspended':
            raise UserError(_('Only suspended tenants can be activated'))

        # Start Docker container
        if self.container_id:
            try:
                import docker
                client = docker.from_env()
                container = client.containers.get(self.container_id)
                container.start()
                _logger.info(f"Activated container for {self.subdomain}")
            except Exception as e:
                _logger.error(f"Error activating container for {self.subdomain}: {e}")

        self.state = 'active'

    def action_cancel(self, reason=''):
        """Cancel tenant subscription"""
        self.ensure_one()

        # Stop and remove container
        if self.container_id:
            try:
                import docker
                client = docker.from_env()
                container = client.containers.get(self.container_id)
                container.stop()
                container.remove()
                _logger.info(f"Removed container for {self.subdomain}")
            except Exception as e:
                _logger.error(f"Error removing container for {self.subdomain}: {e}")

        self.state = 'cancelled'
        if reason:
            self.notes = f"Cancelled: {reason}\n\n{self.notes or ''}"

    def action_access_tenant(self):
        """Open tenant instance in new window"""
        self.ensure_one()

        if self.state != 'active':
            raise UserError(_('Tenant must be active to access'))

        return {
            'type': 'ir.actions.act_url',
            'url': self.login_url,
            'target': 'new',
        }

    def action_send_credentials(self):
        """Send login credentials to tenant"""
        self.ensure_one()

        template = self.env.ref('saas_custom_tenant.email_template_tenant_credentials', False)
        if not template:
            raise UserError(_('Email template not found'))

        template.send_mail(
            self.id,
            force_send=True,
            email_values={
                'email_to': self.admin_email,
                'email_from': self.env.user.company_id.email,
            }
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Credentials Sent'),
                'message': _('Login credentials have been sent to %s') % self.admin_email,
                'type': 'success',
            }
        }