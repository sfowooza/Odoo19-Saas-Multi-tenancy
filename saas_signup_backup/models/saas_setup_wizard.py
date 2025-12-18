# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class SaaSSetupWizard(models.TransientModel):
    _name = 'saas.setup.wizard'
    _description = 'SaaS Platform Setup Wizard'
    
    deployment_mode = fields.Selection([
        ('localhost', 'Localhost / Self-Hosted (Development)'),
        ('subdomain', 'Cloud / Subdomain (Production)')
    ], string='Deployment Mode', required=True, default='localhost',
       help='Choose how tenants will be accessed')
    
    main_domain = fields.Char(
        string='Main Domain',
        help='Your main domain (e.g., yourdomain.com). Required for subdomain mode.'
    )
    
    use_ssl = fields.Boolean(
        string='Use SSL (HTTPS)',
        default=False,
        help='Enable if you have SSL certificates configured'
    )
    
    starting_port = fields.Integer(
        string='Starting Port',
        default=8001,
        help='First port number for localhost tenants (e.g., 8001, 8002, 8003...)'
    )
    
    detected_domain = fields.Char(
        string='Detected Domain',
        compute='_compute_detected_domain',
        help='Auto-detected domain from current request'
    )
    
    @api.depends('deployment_mode')
    def _compute_detected_domain(self):
        """Auto-detect domain from HTTP request"""
        for wizard in self:
            try:
                if self.env.context.get('http_request'):
                    request = self.env.context['http_request']
                    host = request.httprequest.host
                    # Remove port if present
                    domain = host.split(':')[0]
                    wizard.detected_domain = domain
                else:
                    wizard.detected_domain = 'localhost'
            except:
                wizard.detected_domain = 'localhost'
    
    @api.onchange('deployment_mode')
    def _onchange_deployment_mode(self):
        """Set defaults based on deployment mode"""
        if self.deployment_mode == 'localhost':
            self.use_ssl = False
            self.main_domain = 'localhost'
        elif self.deployment_mode == 'subdomain':
            self.use_ssl = True
            if self.detected_domain and self.detected_domain != 'localhost':
                self.main_domain = self.detected_domain
    
    def action_configure(self):
        """Apply configuration and create initial setup"""
        self.ensure_one()
        
        # Validate subdomain mode
        if self.deployment_mode == 'subdomain' and not self.main_domain:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Configuration Error',
                    'message': 'Please enter your main domain for subdomain deployment.',
                    'type': 'warning',
                    'sticky': False,
                }
            }
        
        # Deactivate all existing configurations
        existing_configs = self.env['saas.configuration'].sudo().search([])
        if existing_configs:
            existing_configs.write({'active': False})
            _logger.info(f"Deactivated {len(existing_configs)} existing configuration(s)")
        
        # Create new active configuration
        config = self.env['saas.configuration'].sudo().create({
            'deployment_mode': self.deployment_mode,
            'main_domain': self.main_domain or 'localhost',
            'use_ssl': self.use_ssl,
            'starting_port': self.starting_port,
            'active': True,
        })
        
        _logger.info(f"✅ SaaS Platform configured: {self.deployment_mode} mode on {self.main_domain} (ID: {config.id})")
        
        # Show success notification
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Setup Complete!',
                'message': f'SaaS Platform configured for {self.deployment_mode} deployment on {self.main_domain}.',
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.act_window_close',
                },
            }
        }
    
    def action_skip(self):
        """Skip wizard and use defaults"""
        self.ensure_one()
        return {'type': 'ir.actions.act_window_close'}
