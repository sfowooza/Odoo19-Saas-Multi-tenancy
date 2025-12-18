from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging
import re

_logger = logging.getLogger(__name__)

class SaasClient(models.Model):
    _name = 'saas.client'
    _description = 'SaaS Client'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'company_name'
    
    # Performance indexes
    _indexes = {
        'state_trial_idx': 'state, is_trial',
        'port_idx': 'port',
        'database_name_idx': 'database_name',
    }

    # Company Information
    company_name = fields.Char(string='Company Name', required=True, index=True, tracking=True)
    subdomain = fields.Char(string='Subdomain', required=True, index=True)
    port = fields.Integer(string='Port', required=True, index=True)
    longpolling_port = fields.Integer(string='Longpolling Port', readonly=True)
    database_name = fields.Char(string='Database Name', required=True, index=True)
    container_name = fields.Char(string='Container Name', readonly=True)
    container_id = fields.Char(string='Container ID', readonly=True)
    admin_name = fields.Char(string='Admin Name', required=True)
    admin_email = fields.Char(string='Admin Email', required=True)
    admin_password = fields.Char(string='Admin Password', required=True)
    phone = fields.Char(string='Phone')
    country_id = fields.Many2one('res.country', string='Country')

    # Subscription
    subscription_id = fields.Many2one('saas.subscription', string='Subscription Plan', required=True, index=True, tracking=True)
    trial_end_date = fields.Date(string='Trial End Date', index=True)
    is_trial = fields.Boolean(string='Is Trial', default=True, index=True)
    trial_days_remaining = fields.Integer(string='Trial Days Remaining', compute='_compute_trial_status', store=False)
    trial_expired = fields.Boolean(string='Trial Expired', compute='_compute_trial_status', store=False)
    upgrade_requested = fields.Boolean(string='Upgrade Requested', default=False, index=True)
    upgrade_plan_id = fields.Many2one('saas.subscription', string='Requested Upgrade Plan')
    upgrade_request_date = fields.Datetime(string='Upgrade Request Date')

    # State
    state = fields.Selection([
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='pending', required=True, index=True, tracking=True)
    
    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True)
    approved_date = fields.Datetime(string='Approved Date', readonly=True)
    rejection_reason = fields.Text(string='Rejection Reason')

    # Metadata
    create_date = fields.Datetime(string='Created Date', readonly=True)
    last_login = fields.Datetime(string='Last Login')
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('port_uniq', 'unique(port)', 'Port must be unique!'),
        ('database_name_uniq', 'unique(database_name)', 'Database name must be unique!'),
        ('subdomain_uniq', 'unique(subdomain)', 'Subdomain must be unique!'),
        ('port_positive', 'CHECK(port > 0)', 'Port must be positive!'),
    ]
    
    @api.constrains('subdomain')
    def _check_subdomain_format(self):
        """Validate subdomain format"""
        for record in self:
            if record.subdomain:
                # Only lowercase letters, numbers, and hyphens
                if not re.match(r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?$', record.subdomain):
                    raise ValidationError(_(
                        'Subdomain must contain only lowercase letters, numbers, and hyphens. '
                        'It must start and end with a letter or number.'
                    ))
                if len(record.subdomain) < 3 or len(record.subdomain) > 63:
                    raise ValidationError(_('Subdomain must be between 3 and 63 characters.'))
    
    @api.constrains('admin_email')
    def _check_admin_email(self):
        """Validate admin email format"""
        for record in self:
            if record.admin_email:
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, record.admin_email):
                    raise ValidationError(_('Please enter a valid email address.'))
    
    @api.constrains('port')
    def _check_port_range(self):
        """Validate port is within acceptable range"""
        for record in self:
            if record.port and (record.port < 1024 or record.port > 65535):
                raise ValidationError(_('Port must be between 1024 and 65535.'))

    @api.depends('trial_end_date', 'is_trial')
    def _compute_trial_status(self):
        """Compute trial days remaining and expiration status"""
        from datetime import date
        for record in self:
            if record.is_trial and record.trial_end_date:
                today = date.today()
                delta = (record.trial_end_date - today).days
                record.trial_days_remaining = delta if delta > 0 else 0
                record.trial_expired = delta <= 0
            else:
                record.trial_days_remaining = 0
                record.trial_expired = False
    
    def action_request_upgrade(self, new_plan_id):
        """Request upgrade to a new plan"""
        self.ensure_one()
        self.write({
            'upgrade_requested': True,
            'upgrade_plan_id': new_plan_id,
            'upgrade_request_date': fields.Datetime.now()
        })
        return True
    
    @api.model
    def check_trial_expiration(self):
        """Cron job to check and suspend expired trials - optimized query"""
        # Use date field directly for better performance
        from datetime import date
        today = date.today()
        
        # Optimized: query expired trials directly without computed field
        expired_clients = self.search([
            ('is_trial', '=', True),
            ('trial_end_date', '<', today),
            ('state', '=', 'active')
        ], limit=100)  # Process in batches for performance
        
        for client in expired_clients:
            _logger.info(f"Trial expired for {client.company_name}")
            client.write({
                'state': 'suspended',
                'notes': f"{client.notes or ''}\n\nTrial expired on {fields.Date.today()}. Please upgrade to continue."
            })
            
            # Stop container
            try:
                import docker
                docker_client = docker.from_env()
                container_name = f"odoo_tenant_{client.subdomain}"
                container = docker_client.containers.get(container_name)
                container.stop()
                _logger.info(f"Suspended container: {container_name}")
            except Exception as e:
                _logger.warning(f"Could not suspend container: {e}")
        
        return True
    
    def action_approve_upgrade(self):
        """Admin approves the upgrade request and installs new modules"""
        import logging
        _logger = logging.getLogger(__name__)
        
        for record in self:
            if record.upgrade_requested and record.upgrade_plan_id:
                old_plan = record.subscription_id
                new_plan = record.upgrade_plan_id
                
                _logger.info(f"Processing upgrade for {record.subdomain}: {old_plan.name} → {new_plan.name}")
                
                # Install additional modules from new plan
                if new_plan.module_list:
                    try:
                        import docker
                        docker_client = docker.from_env()
                        
                        # Stop tenant container
                        container_name = f"odoo_tenant_{record.subdomain}"
                        try:
                            container = docker_client.containers.get(container_name)
                            container.stop()
                            _logger.info(f"Stopped container: {container_name}")
                        except:
                            pass
                        
                        # Install new modules
                        _logger.info(f"Installing modules: {new_plan.module_list}")
                        docker_client.containers.run(
                            'odoo:19',
                            name=f"upgrade_{record.subdomain}",
                            remove=True,
                            environment={'HOST': 'db', 'PORT': '5432', 'USER': 'odoo', 'PASSWORD': 'odoo'},
                            command=f'odoo -d {record.database_name} -i {new_plan.module_list} -u all --stop-after-init --without-demo=all',
                            network='odoo19_odoo-network'
                        )
                        
                        # Restart tenant container
                        try:
                            container = docker_client.containers.get(container_name)
                            container.start()
                            _logger.info(f"Restarted container: {container_name}")
                        except:
                            pass
                        
                    except Exception as e:
                        _logger.error(f"Upgrade error: {e}")
                        record.notes = f"{record.notes or ''}\n\nUpgrade error: {str(e)}"
                        return False
                
                # Update subscription and clear upgrade request
                record.write({
                    'subscription_id': new_plan.id,
                    'is_trial': False,
                    'upgrade_requested': False,
                    'upgrade_plan_id': False,
                    'notes': f"{record.notes or ''}\n\nUpgraded from {old_plan.name} to {new_plan.name} on {fields.Datetime.now()}"
                })
                
                _logger.info(f"Upgrade completed for {record.subdomain}")
        
        return True
    
    @api.model
    def create(self, vals):
        # Handle both single dict and list of dicts
        if isinstance(vals, list):
            vals_list = vals
        else:
            vals_list = [vals]
        
        # Process each record
        for val in vals_list:
            if 'trial_end_date' not in val:
                trial_days = self.env['saas.subscription'].browse(val.get('subscription_id')).trial_days
                val['trial_end_date'] = datetime.now() + timedelta(days=trial_days)

        # Call parent create
        clients = super(SaasClient, self).create(vals)

        # Note: Database and container provisioning is now done in the controller
        # The controller creates the database and Docker container before calling this create method
        # So we skip the _create_client_database call here

        return clients
    
    def _get_next_available_port(self):
        """Get next available port for new tenant instance"""
        base_port = 8100
        max_port = 8999
        
        used_ports = self.sudo().search([('port', '!=', False)]).mapped('port')
        
        for port in range(base_port, max_port + 1):
            if port not in used_ports:
                return port
        
        raise UserError("No available ports! Maximum tenant limit reached.")
    
    def _configure_nginx(self):
        """Configure Nginx reverse proxy for this tenant"""
        self.ensure_one()
        
        try:
            from ..utils.nginx_manager import NginxManager
            
            config = self.env['saas.configuration'].sudo().get_config()
            
            # Only configure Nginx in subdomain mode
            if config.deployment_mode == 'subdomain':
                NginxManager.create_tenant_config(
                    subdomain=self.subdomain,
                    odoo_port=self.port,
                    longpolling_port=self.longpolling_port,
                    main_domain=config.main_domain
                )
                _logger.info(f"✅ Nginx configured for {self.subdomain}.{config.main_domain}")
                return True
            else:
                _logger.info(f"Localhost mode: Skipping Nginx config for port {self.port}")
                return True
                
        except Exception as e:
            _logger.error(f"❌ Nginx configuration failed for {self.subdomain}: {e}")
            raise
    
    def _remove_nginx_config(self):
        """Remove Nginx configuration for this tenant"""
        self.ensure_one()
        
        try:
            from ..utils.nginx_manager import NginxManager
            
            config = self.env['saas.configuration'].sudo().get_config()
            
            if config.deployment_mode == 'subdomain':
                NginxManager.remove_tenant_config(self.subdomain)
                _logger.info(f"✅ Nginx config removed for {self.subdomain}")
            
        except Exception as e:
            _logger.warning(f"Failed to remove Nginx config: {e}")
    
    def action_approve(self):
        """Approve pending tenant and create/start container with Nginx config"""
        from odoo.exceptions import UserError
        
        for record in self:
            if record.state == 'pending':
                # Set longpolling port if not set
                if not record.longpolling_port:
                    record.longpolling_port = record.port + 1000
                
                # Set container name
                if not record.container_name:
                    record.container_name = f"odoo_tenant_{record.subdomain}"
                
                record.write({
                    'state': 'approved',
                    'approved_by': self.env.user.id,
                    'approved_date': fields.Datetime.now()
                })
                
                # Create and start the container now that tenant is approved
                try:
                    import docker
                    docker_client = docker.from_env()
                    container_name = f"odoo_tenant_{record.subdomain}"
                    volume_name = f"odoo_tenant_{record.subdomain}_data"
                    waiting_container_name = f"waiting_{record.subdomain}"
                    
                    # Remove waiting page container if it exists
                    try:
                        waiting_container = docker_client.containers.get(waiting_container_name)
                        _logger.info(f"Removing waiting page container: {waiting_container_name}")
                        waiting_container.stop()
                        waiting_container.remove()
                        _logger.info(f"Waiting page container removed")
                    except docker.errors.NotFound:
                        _logger.info(f"No waiting container found (already removed or never created)")
                    except Exception as e:
                        _logger.warning(f"Error removing waiting container: {e}")
                    
                    # Check if Odoo container already exists
                    try:
                        container = docker_client.containers.get(container_name)
                        _logger.info(f"Container {container_name} already exists, starting...")
                        if container.status != 'running':
                            container.start()
                    except docker.errors.NotFound:
                        # Container doesn't exist, create it
                        _logger.info(f"Creating container {container_name} on port {record.port}...")
                        
                        container = docker_client.containers.run(
                            'odoo:19',
                            name=container_name,
                            detach=True,
                            environment={
                                'HOST': 'db',
                                'PORT': '5432',
                                'USER': 'odoo',
                                'PASSWORD': '248413',  # Use correct password from .env
                            },
                            command=f'odoo --database={record.database_name} --db-filter=^{record.database_name}$ --without-demo=all',
                            ports={'8069/tcp': ('0.0.0.0', record.port)},  # Bind to all interfaces for external access
                            volumes={
                                volume_name: {'bind': '/var/lib/odoo', 'mode': 'rw'}
                            },
                            network='odoo19_odoo-network',
                            labels={
                                'saas.type': 'tenant',
                                'saas.tenant': record.subdomain,
                                'saas.database': record.database_name,
                                'saas.company': record.company_name,
                                'saas.port': str(record.port)
                            },
                            restart_policy={'Name': 'unless-stopped'}
                        )
                        
                        _logger.info(f"Container created and started: {container.id[:12]}")
                        record.container_id = container.id[:12]
                        record.notes = f"{record.notes or ''}\n\nApproved and activated on {fields.Datetime.now()}\nContainer: {container.id[:12]}\nStatus: Running on port {record.port}"
                        
                        # Regenerate nginx map with robust multi-pattern detection
                        try:
                            _logger.info(f"Regenerating nginx map with robust detection...")
                            import subprocess
                            result = subprocess.run(
                                ['python3', '/opt/odoo19/scripts/generate_robust_tenant_map.py'],
                                capture_output=True,
                                text=True,
                                timeout=20
                            )
                            if result.returncode == 0:
                                _logger.info(f"✅ Robust nginx map regenerated: {result.stdout}")
                                record.notes = f"{record.notes}\nNginx: Robust mapping active, found {result.stdout.count('Found:')} containers"
                            else:
                                _logger.warning(f"Robust mapping generation warning: {result.stderr}")
                                record.notes = f"{record.notes}\nNginx: Robust mapping attempted (check logs)"
                        except Exception as nginx_error:
                            _logger.error(f"❌ Robust nginx map generation failed: {nginx_error}", exc_info=True)
                            record.notes = f"{record.notes}\nNginx: Manual robust config may be needed"
                            # Don't fail approval just because nginx failed
                            pass

                    # Generate tenant proxy configurations for reverse proxy
                    try:
                        _logger.info(f"Generating tenant proxy configurations...")
                        result = subprocess.run(
                            ['python3', '/opt/odoo19/scripts/generate_tenant_proxy_configs.py'],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        if result.returncode == 0:
                            _logger.info(f"✅ Tenant proxy configs generated: {result.stdout}")
                            record.notes = f"{record.notes}\nReverse Proxy: {record.subdomain}.avodahconsult.info configured"
                        else:
                            _logger.warning(f"Proxy config generation warning: {result.stderr}")
                    except Exception as proxy_error:
                        _logger.warning(f"Proxy config generation failed: {proxy_error}")

                    # Wait for container to be fully ready and then reset admin password
                    import time
                    _logger.info(f"Waiting for container {container_name} to be ready...")
                    time.sleep(10)  # Give container time to start

                    # Reset admin password to ensure proper authentication
                    try:
                        record._reset_admin_password()
                        record.notes = f"{record.notes}\n✅ Admin password reset for immediate login"
                    except Exception as pwd_error:
                        _logger.warning(f"Password reset failed for {record.subdomain}: {pwd_error}")
                        record.notes = f"{record.notes}\n⚠️ Password reset failed - admin may need to reset manually"

                    record.state = 'active'

                except Exception as e:
                    _logger.error(f"Error creating/starting container for {record.subdomain}: {e}", exc_info=True)
                    record.notes = f"{record.notes or ''}\n\nApproval error: {str(e)}\nPlease contact system administrator."
        
        return True

    def _reset_admin_password(self):
        """Internal method to reset admin password with proper hashing"""
        import psycopg2
        from passlib.context import CryptContext

        try:
            # Hash the password with Odoo's exact parameters
            pwd_context = CryptContext(
                schemes=['pbkdf2_sha512'],
                default__pbkdf2_sha512__rounds=600000,
                deprecated='auto'
            )
            hashed_password = pwd_context.hash(self.admin_password)

            # Connect to tenant database
            db_host = 'db'
            db_port = 5432
            db_user = 'odoo'
            db_password = '248413'

            tenant_conn = psycopg2.connect(
                host=db_host, port=db_port, database=self.database_name,
                user=db_user, password=db_password
            )
            tenant_conn.autocommit = True
            tenant_cursor = tenant_conn.cursor()

            # Find the admin user (could be id=2 or login='admin')
            tenant_cursor.execute(
                "SELECT id, partner_id FROM res_users WHERE login IN ('admin', 'admin@example.com') OR id = 2 LIMIT 1"
            )
            admin_result = tenant_cursor.fetchone()

            if admin_result:
                admin_user_id, admin_partner_id = admin_result

                # Update admin user login and password
                tenant_cursor.execute(
                    "UPDATE res_users SET login=%s, password=%s WHERE id=%s",
                    (self.admin_email, hashed_password, admin_user_id)
                )

                # Update partner information
                tenant_cursor.execute(
                    "UPDATE res_partner SET name=%s, email=%s WHERE id=%s",
                    (self.admin_name, self.admin_email, admin_partner_id)
                )

                _logger.info(f"✅ Admin password reset for {self.subdomain}: {self.admin_email}")
            else:
                _logger.warning(f"⚠️ No admin user found in database {self.database_name}")

            tenant_cursor.close()
            tenant_conn.close()

        except Exception as e:
            _logger.error(f"❌ Failed to reset admin password for {self.subdomain}: {e}")
            raise

    def action_reject(self):
        """Reject pending tenant and stop/remove container"""
        for record in self:
            if record.state == 'pending':
                record.write({'state': 'rejected'})
                
                # Remove Nginx config
                try:
                    record._remove_nginx_config()
                except Exception as e:
                    _logger.warning(f"Failed to remove Nginx config: {e}")
                
                # Stop and remove the container
                try:
                    import docker
                    client = docker.from_env()
                    container_name = f"odoo_tenant_{record.subdomain}"
                    container = client.containers.get(container_name)
                    container.stop()
                    container.remove()
                    record.notes = f"{record.notes}\nRejection: Container and Nginx config removed"
                except Exception as e:
                    record.notes = f"{record.notes}\nRejection note: {str(e)}"
        return True
    
    def action_reset_password(self):
        """Reset tenant admin password to match stored password in saas_client record"""
        from odoo.exceptions import UserError

        for record in self:
            if not record.admin_password:
                raise UserError("No password found for this tenant. Please set a password first.")

            if record.state not in ['approved', 'active']:
                raise UserError("Tenant must be approved before resetting password. Please approve the tenant first.")

            try:
                # Use the internal password reset method
                record._reset_admin_password()

                record.notes = f"{record.notes or ''}\n\n✅ Manual password reset on {fields.Datetime.now()}\nLogin: {record.admin_email}\nPassword: {record.admin_password}"

                _logger.info(f"✅ Manual password reset for tenant {record.subdomain}: {record.admin_email}")

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Password Reset Success',
                        'message': f'Password reset for {record.subdomain}. User can now login with: {record.admin_email}',
                        'type': 'success',
                        'sticky': False,
                    }
                }

            except Exception as e:
                _logger.error(f"❌ Manual password reset failed for {record.subdomain}: {e}", exc_info=True)
                raise UserError(f"Password reset failed: {str(e)}")

        return True
    
    def action_suspend(self):
        """Suspend active tenant (stops container but keeps Nginx config)"""
        for record in self:
            if record.state in ['active', 'approved']:
                record.write({'state': 'suspended'})
                try:
                    import docker
                    client = docker.from_env()
                    container_name = record.container_name or f"odoo_tenant_{record.subdomain}"
                    container = client.containers.get(container_name)
                    container.stop()
                    _logger.info(f"Suspended tenant: {record.subdomain}")
                except Exception as e:
                    _logger.error(f"Suspension error: {e}")
                    record.notes = f"{record.notes}\nSuspension error: {str(e)}"
        return True
    
    def action_activate(self):
        """Activate suspended tenant (restarts container)"""
        for record in self:
            if record.state == 'suspended':
                record.write({'state': 'active'})
                try:
                    import docker
                    client = docker.from_env()
                    container_name = record.container_name or f"odoo_tenant_{record.subdomain}"
                    container = client.containers.get(container_name)
                    container.start()
                    _logger.info(f"Reactivated tenant: {record.subdomain}")
                except Exception as e:
                    _logger.error(f"Activation error: {e}")
                    record.notes = f"{record.notes}\nActivation error: {str(e)}"
        return True
    
    def action_delete_tenant(self):
        """Completely delete tenant - container, database, Nginx config"""
        self.ensure_one()
        
        from odoo.exceptions import UserError
        
        try:
            import docker
            import psycopg2
            from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
            
            docker_client = docker.from_env()
            container_name = self.container_name or f"odoo_tenant_{self.subdomain}"
            
            # Stop and remove container
            try:
                container = docker_client.containers.get(container_name)
                container.stop(timeout=10)
                container.remove()
                _logger.info(f"✅ Removed container: {container_name}")
            except docker.errors.NotFound:
                _logger.warning(f"Container not found: {container_name}")
            
            # Remove Docker volumes
            volume_name = f"odoo_tenant_{self.subdomain}_data"
            try:
                volume = docker_client.volumes.get(volume_name)
                volume.remove()
                _logger.info(f"✅ Removed volume: {volume_name}")
            except docker.errors.NotFound:
                pass
            
            # Remove Nginx config
            self._remove_nginx_config()
            
            # Drop database
            if self.database_name:
                try:
                    conn = psycopg2.connect(
                        host='localhost',
                        port=5432,
                        user='odoo',
                        password='odoo',
                        database='postgres'
                    )
                    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
                    cursor = conn.cursor()
                    
                    # Terminate connections
                    cursor.execute(f"""
                        SELECT pg_terminate_backend(pid) 
                        FROM pg_stat_activity 
                        WHERE datname = '{self.database_name}' AND pid <> pg_backend_pid()
                    """)
                    
                    # Drop database
                    cursor.execute(f'DROP DATABASE IF EXISTS "{self.database_name}"')
                    cursor.close()
                    conn.close()
                    
                    _logger.info(f"✅ Dropped database: {self.database_name}")
                except Exception as db_error:
                    _logger.error(f"Database deletion error: {db_error}")
            
            # Update record
            self.write({
                'state': 'cancelled',
                'notes': f"{self.notes or ''}\n\nTenant deleted on {fields.Datetime.now()}\nAll resources removed."
            })
            
            _logger.info(f"✅ Tenant completely deleted: {self.subdomain}")
            return True
            
        except Exception as e:
            _logger.error(f"❌ Tenant deletion failed: {e}")
            raise UserError(f"Failed to delete tenant: {str(e)}")

    def _create_client_database(self, client):
        """Create a new Odoo database for the client"""
        try:
            # Import necessary modules
            import subprocess
            import psycopg2
            from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

            # Connect to PostgreSQL server (not a specific database)
            conn = psycopg2.connect(
                host='localhost',
                port=5432,
                user='odoo',
                password='odoo'
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()

            # Create the new database
            cursor.execute(f"CREATE DATABASE {client.database_name}")
            cursor.close()
            conn.close()

            # Initialize the new database with Odoo schema
            subprocess.run([
                'odoo',
                '-d', client.database_name,
                '--init=base',
                '--stop-after-init',
                '--db_host=localhost',
                '--db_port=5432',
                '--db_user=odoo',
                '--db_password=odoo'
            ], capture_output=True, check=True)

            # Connect to the new database and create admin user
            new_conn = psycopg2.connect(
                host='localhost',
                port=5432,
                user='odoo',
                password='odoo',
                database=client.database_name
            )
            new_cursor = new_conn.cursor()

            # Update admin user credentials
            new_cursor.execute("""
                UPDATE res_users
                SET login = %s,
                    password = crypt(%s, password),
                    email = %s,
                    name = %s
                WHERE login = 'admin'
            """, (client.admin_email, client.admin_password, client.admin_email, client.admin_name))

            # Update company information
            new_cursor.execute("""
                UPDATE res_company
                SET name = %s
                WHERE id = 1
            """, (client.company_name,))

            new_cursor.close()
            new_conn.close()

            client.write({
                'state': 'active',
                'notes': f'Database "{client.database_name}" created successfully on port {client.port}'
            })

        except Exception as e:
            client.write({
                'state': 'pending',
                'notes': f'Database creation failed: {str(e)}'
            })
            raise

    @api.model
    def check_expired_trials(self):
        """Check and update expired trials"""
        expired_clients = self.search([
            ('is_trial', '=', True),
            ('trial_end_date', '<', fields.Date.today()),
            ('state', '=', 'active')
        ])
        expired_clients.write({'state': 'suspended'})
    
    # ==================
    # MULTI-TENANCY HELPERS
    # ==================
    
    def get_database_size_mb(self):
        """Get database size in MB"""
        self.ensure_one()
        if not self.database_name:
            return 0
        
        try:
            conn = psycopg2.connect(
                host=self.env['ir.config_parameter'].sudo().get_param('db_host', 'localhost'),
                port=int(self.env['ir.config_parameter'].sudo().get_param('db_port', 5432)),
                database='postgres',
                user=self.env['ir.config_parameter'].sudo().get_param('db_user', 'odoo'),
                password=self.env['ir.config_parameter'].sudo().get_param('db_password', 'odoo')
            )
            conn.autocommit = True
            cur = conn.cursor()
            
            cur.execute("SELECT pg_database_size(%s) / (1024 * 1024)", (self.database_name,))
            result = cur.fetchone()
            
            cur.close()
            conn.close()
            
            return round(result[0], 2) if result else 0
        except Exception as e:
            _logger.error(f"Failed to get database size: {e}")
            return 0
    
    def get_tenant_url(self):
        """Get the full URL for accessing this tenant"""
        self.ensure_one()
        config = self.env['saas.configuration'].sudo().get_config()
        
        if config.deployment_mode == 'subdomain':
            protocol = 'https' if config.use_ssl else 'http'
            # For subdomain mode, always show subdomain.domain format
            # For production with nginx: subdomain.yourdomain.com (no port)
            # For local testing: subdomain.localhost:port
            if config.main_domain == 'localhost':
                return f"{protocol}://{self.subdomain}.{config.main_domain}:{self.port}"
            else:
                return f"{protocol}://{self.subdomain}.{config.main_domain}"
        else:
            return f"http://localhost:{self.port}"
    
    def action_open_tenant(self):
        """Open tenant URL in browser"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': self.get_tenant_url(),
            'target': 'new'
        }
    
    def _duplicate_from_template(self, template_db):
        """Fast provisioning by duplicating from template database"""
        self.ensure_one()
        
        try:
            import psycopg2
            from odoo.tools import config
            
            conn = psycopg2.connect(
                host=config.get('db_host', 'localhost'),
                port=config.get('db_port', 5432),
                database='postgres',
                user=config.get('db_user', 'odoo'),
                password=config.get('db_password', 'odoo')
            )
            conn.autocommit = True
            cur = conn.cursor()
            
            # Terminate connections to template
            cur.execute(f"""
                SELECT pg_terminate_backend(pid) 
                FROM pg_stat_activity 
                WHERE datname = '{template_db}' AND pid <> pg_backend_pid()
            """)
            
            # Create database from template (much faster than fresh install)
            cur.execute(f'CREATE DATABASE "{self.database_name}" WITH TEMPLATE "{template_db}"')
            
            cur.close()
            conn.close()
            
            _logger.info(f"Created {self.database_name} from template {template_db}")
            return True
            
        except Exception as e:
            _logger.error(f"Template duplication failed: {e}")
            return False
        return expired_clients