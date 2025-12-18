# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class SaasConfiguration(models.Model):
    _name = 'saas.configuration'
    _description = 'SaaS Configuration'
    _rec_name = 'deployment_mode'

    deployment_mode = fields.Selection([
        ('localhost', 'Localhost/Self-Hosted (Docker Ports)'),
        ('subdomain', 'Subdomain/Cloud (Subdomain Routing)')
    ], string='Deployment Mode', required=True, default='localhost',
       help="Localhost: Tenants run on different ports (8001, 8002, etc.)\n"
            "Subdomain: Tenants run on subdomains (tenant1.yourdomain.com)")
    
    main_domain = fields.Char(string='Main Domain', 
                               help='Your main domain (e.g., avodahsystems.com). Auto-detected on install.')
    
    base_url = fields.Char(string='Base URL', compute='_compute_base_url', store=True,
                           help='Full base URL for the SaaS platform')
    
    starting_port = fields.Integer(string='Starting Port', default=8001,
                                   help='Starting port for localhost deployments')
    
    use_ssl = fields.Boolean(string='Use SSL/HTTPS', default=False,
                            help='Enable if using HTTPS for subdomain deployments')
    
    nginx_config_path = fields.Char(string='Nginx Config Path',
                                    default='/etc/nginx/sites-enabled/',
                                    help='Path where nginx config files should be created')
    
    docker_network = fields.Char(string='Docker Network', 
                                 default='odoo19_odoo-network',
                                 help='Docker network name for tenant containers')
    
    active = fields.Boolean(string='Active', default=True)
    
    _sql_constraints = [
        ('single_config', 'CHECK(id = 1)', 'Only one configuration record is allowed!'),
    ]
    
    @api.depends('deployment_mode', 'main_domain', 'use_ssl')
    def _compute_base_url(self):
        for record in self:
            if record.deployment_mode == 'subdomain' and record.main_domain:
                protocol = 'https' if record.use_ssl else 'http'
                record.base_url = f"{protocol}://{record.main_domain}"
            else:
                record.base_url = 'http://localhost'
    
    @api.model
    def get_config(self):
        """Get or create the SaaS configuration - prioritize active configs"""
        # First try to get active configuration
        config = self.search([('active', '=', True)], limit=1)
        if not config:
            # If no active config, try any config
            config = self.search([], limit=1)
        if not config:
            # Create default if none exists
            config = self.create({
                'deployment_mode': 'subdomain',
                'main_domain': 'avodahconsult.info',
                'starting_port': 8001,
                'use_ssl': False,
            })
            _logger.info(f"Created SaaS configuration: Mode={config.deployment_mode}, Domain={config.main_domain}")
        return config
    
    @api.model
    def init_default_config(self):
        """Initialize default configuration on module install"""
        if not self.search_count([]):
            _logger.info('Initializing default SaaS configuration...')
            # Auto-detect if we're on a remote server or localhost
            import socket
            try:
                hostname = socket.gethostname()
                ip_address = socket.gethostbyname(hostname)
                # If we have a real IP (not localhost), use it
                if ip_address and ip_address not in ['127.0.0.1', '::1']:
                    main_domain = ip_address
                else:
                    main_domain = 'localhost'
            except:
                main_domain = 'localhost'
            
            config = self.create({
                'deployment_mode': 'localhost',
                'main_domain': main_domain,
                'starting_port': 8001,
                'use_ssl': False,
            })
            _logger.info(f'SaaS Configuration created: Mode={config.deployment_mode}, Domain={config.main_domain}')
            return config
        return self.search([], limit=1)
    
    def generate_tenant_url(self, subdomain, port=None):
        """Generate tenant URL based on deployment mode"""
        self.ensure_one()
        
        if self.deployment_mode == 'subdomain':
            protocol = 'https' if self.use_ssl else 'http'
            return f"{protocol}://{subdomain}.{self.main_domain}"
        else:
            # Localhost/IP mode - support both localhost and IP addresses
            import socket
            # Try to get the server's IP address
            try:
                # Get hostname
                hostname = socket.gethostname()
                # Get IP address
                ip_address = socket.gethostbyname(hostname)
                # Check if it's a real IP (not localhost)
                if ip_address and ip_address != '127.0.0.1' and self.main_domain not in ['localhost', '127.0.0.1']:
                    # Use the configured domain/IP
                    base_host = self.main_domain
                else:
                    base_host = 'localhost'
            except:
                base_host = self.main_domain or 'localhost'
            return f"http://{base_host}:{port}"
    
    def get_next_available_port(self):
        """Get next available port for localhost deployment"""
        self.ensure_one()
        
        if self.deployment_mode != 'localhost':
            return None
        
        # Get highest port from existing clients
        Client = self.env['saas.client']
        last_client = Client.search([], order='port desc', limit=1)
        
        if last_client and last_client.port:
            return last_client.port + 1
        else:
            return self.starting_port
