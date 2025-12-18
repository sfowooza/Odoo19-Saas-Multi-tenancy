# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import subprocess
import os
import json
import time

class SaasPortConfig(models.Model):
    _name = 'saas.port.config'
    _description = 'SaaS Port Configuration'
    _rec_name = 'Port Configuration'

    name = fields.Char(string='Configuration Name', required=True, help='Name for this port configuration')

    # Port settings
    odoo_port = fields.Integer(string='Main Odoo Port', required=True,
                            default=7001, help='Main Odoo web interface port')
    odoo_chat_port = fields.Integer(string='Chat/Longpolling Port',
                                   default=7002, help='Odoo chat/longpolling port')
    pgadmin_port = fields.Integer(string='pgAdmin Port',
                              default=5050, help='pgAdmin database interface port')

    # Status
    is_active = fields.Boolean(string='Active', default=True,
                             help='Whether this port configuration is currently active')
    is_default = fields.Boolean(string='Default Configuration', default=False,
                               help='This is the default port configuration')

    # Advanced settings
    ssl_enabled = fields.Boolean(string='Enable SSL/HTTPS', default=False,
                                 help='Enable SSL/HTTPS for secure connections')
    ssl_port = fields.Integer(string='SSL Port', default=443,
                            help='Port for SSL/HTTPS connections')

    # Technical information
    container_status = fields.Selection([
        ('stopped', 'Stopped'),
        ('running', 'Running'),
        ('error', 'Error'),
        ('restarting', 'Restarting'),
    ], string='Container Status', default='stopped', readonly=True)

    last_restart = fields.Datetime(string='Last Restart', readonly=True)
    error_message = fields.Text(string='Error Message', readonly=True)

    @api.model
    def default_get(self, fields_list):
        """Set default values for fields"""
        res = super(SaasPortConfig, self).default_get(fields_list)
        if 'name' in fields_list:
            res['name'] = 'Default Configuration'
        return res

    @api.constrains('odoo_port')
    def _check_odoo_port(self):
        """Validate Odoo port"""
        for record in self:
            if record.odoo_port < 1 or record.odoo_port > 65535:
                raise ValidationError(_('Odoo port must be between 1 and 65535'))

            # Check for port conflicts with other active configurations
            if record.is_active:
                conflicting = self.search([
                    ('id', '!=', record.id),
                    ('is_active', '=', True),
                    ('odoo_port', '=', record.odoo_port)
                ])
                if conflicting:
                    raise ValidationError(_('Odoo port %s is already used by configuration: %s') %
                                        (record.odoo_port, conflicting[0].name))

    @api.constrains('odoo_chat_port')
    def _check_odoo_chat_port(self):
        """Validate Odoo chat port"""
        for record in self:
            if record.odoo_chat_port < 1 or record.odoo_chat_port > 65535:
                raise ValidationError(_('Chat port must be between 1 and 65535'))

    @api.constrains('pgadmin_port')
    def _check_pgadmin_port(self):
        """Validate pgAdmin port"""
        for record in self:
            if record.pgadmin_port < 1 or record.pgadmin_port > 65535:
                raise ValidationError(_('pgAdmin port must be between 1 and 65535'))

    @api.model
    def set_as_default(self):
        """Set this configuration as default"""
        active_configs = self.search([('is_default', '=', True)])
        if active_configs:
            active_configs.write({'is_default': False})
        self.write({'is_default': True})
        return True

    def write(self, vals):
        """Override write to restart services if ports changed"""
        # Check if ports are being changed
        port_fields = ['odoo_port', 'odoo_chat_port', 'pgadmin_port']
        ports_changed = any(field in vals for field in port_fields)

        # Set only one active configuration
        if vals.get('is_active') and not self.is_active:
            # Deactivate other configurations
            self.search([('id', '!=', self.id), ('is_active', '=', True)]) \
                .write({'is_active': False})

        res = super(SaasPortConfig, self).write(vals)

        # If ports changed and this is active, restart services
        if ports_changed and vals.get('is_active', self.is_active):
            try:
                self._update_environment_file()
                self._restart_services()
                self.write({
                    'container_status': 'restarting',
                    'last_restart': fields.Datetime.now(),
                    'error_message': False
                })
            except Exception as e:
                self.write({
                    'container_status': 'error',
                    'error_message': str(e)
                })
                raise ValidationError(_('Failed to apply port configuration: %s') % str(e))

        return res

    def _update_environment_file(self):
        """Update the .env file with current port configuration"""
        env_content = f"""# 🔧 Port Configuration for Odoo 19 SaaS Platform
# Updated by Odoo Admin Interface on {fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

# Main Odoo Web Interface
ODOO_PORT={self.odoo_port}

# Odoo Chat/Longpolling Port (optional)
ODOO_CHAT_PORT={self.odoo_chat_port}

# pgAdmin Database Interface
PGADMIN_PORT={self.pgadmin_port}

# Advanced Configuration (keep defaults)
DB_PORT=5432
DB_HOST=db
"""

        env_file_path = os.path.join(os.getcwd(), '.env')

        try:
            with open(env_file_path, 'w') as f:
                f.write(env_content)
            return True
        except Exception as e:
            raise Exception(f"Failed to write .env file: {str(e)}")

    def _restart_services(self):
        """Restart Docker services with new port configuration"""
        try:
            # Change to the correct directory
            os.chdir(os.getcwd())

            # Stop services
            subprocess.run(['docker-compose', 'down'],
                         check=True, capture_output=True, text=True, timeout=30)

            # Small delay to ensure containers are fully stopped
            time.sleep(2)

            # Start services
            result = subprocess.run(['docker-compose', 'up', '-d'],
                                     check=True, capture_output=True, text=True, timeout=60)

            return True

        except subprocess.TimeoutExpired:
            raise Exception("Services failed to restart within timeout period")
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to restart services: {e.stderr}")
        except Exception as e:
            raise Exception(f"Error during service restart: {str(e)}")

    @api.model
    def check_services_status(self):
        """Check the status of Docker services"""
        try:
            os.chdir(os.getcwd())

            # Check if containers are running
            result = subprocess.run(['docker-compose', 'ps'],
                                     capture_output=True, text=True, timeout=10)

            # Parse output to check if services are running
            if 'Up' in result.stdout and 'odoo19' in result.stdout:
                return 'running'
            else:
                return 'stopped'

        except Exception:
            return 'error'

    @api.model
    def get_active_config(self):
        """Get the currently active port configuration"""
        active_config = self.search([('is_active', '=', True)], limit=1)
        if active_config:
            return active_config[0]
        return None

    def action_test_ports(self):
        """Test if the configured ports are available"""
        self.ensure_one()

        ports_to_test = [self.odoo_port, self.pgadmin_port]
        if self.odoo_chat_port:
            ports_to_test.append(self.odoo_chat_port)

        import socket
        unavailable_ports = []

        for port in ports_to_test:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    result = s.connect_ex(('localhost', port))
                    if result == 0:
                        unavailable_ports.append(port)
            except:
                pass

        if unavailable_ports:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Port Conflict'),
                    'message': _('The following ports are already in use: %s') % ', '.join(map(str, unavailable_ports)),
                    'type': 'warning',
                    'sticky': True,
                }
            }
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Ports Available'),
                    'message': _('All configured ports are available!'),
                    'type': 'success',
                    'sticky': False,
                }
            }

    def action_restart_services(self):
        """Restart services with current configuration"""
        self.ensure_one()

        try:
            self._update_environment_file()
            self._restart_services()
            self.write({
                'container_status': 'restarting',
                'last_restart': fields.Datetime.now(),
                'error_message': False
            })

            # Check status after restart
            time.sleep(5)
            status = self.check_services_status()
            self.write({'container_status': status})

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Services Restarted'),
                    'message': _('Services have been restarted with the new port configuration.'),
                    'type': 'success',
                    'sticky': False,
                }
            }

        except Exception as e:
            self.write({
                'container_status': 'error',
                'error_message': str(e)
            })
            raise ValidationError(_('Failed to restart services: %s') % str(e))

    def action_view_logs(self):
        """View Docker logs"""
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Docker Logs'),
            'res_model': 'saas.docker.logs',
            'view_mode': 'form',
            'view_id': 'saas_signup.view_docker_logs_form',
            'context': {'default_config_id': self.id},
            'target': 'new',
        }