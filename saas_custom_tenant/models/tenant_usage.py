# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class TenantUsage(models.Model):
    _name = 'saas.tenant.usage'
    _description = 'SaaS Tenant Usage Statistics'
    _order = 'date desc'

    tenant_id = fields.Many2one('saas.tenant.instance', string='Tenant', required=True, ondelete='cascade')
    date = fields.Date(string='Date', required=True, default=fields.Date.today)

    # User Statistics
    active_users = fields.Integer(string='Active Users', help='Number of active users on this date')
    total_users = fields.Integer(string='Total Users', help='Total number of users')
    new_users = fields.Integer(string='New Users', help='Number of new users created on this date')

    # Resource Usage
    storage_used_gb = fields.Float(string='Storage Used (GB)', digits=(6, 2))
    cpu_usage_percent = fields.Float(string='CPU Usage (%)', digits=(5, 2))
    memory_usage_mb = fields.Float(string='Memory Usage (MB)', digits=(10, 2))

    # Activity Statistics
    page_views = fields.Integer(string='Page Views', help='Number of page views on this date')
    api_calls = fields.Integer(string='API Calls', help='Number of API calls on this date')

    # Performance Metrics
    response_time_ms = fields.Float(string='Average Response Time (ms)', digits=(8, 2))
    uptime_hours = fields.Float(string='Uptime (Hours)', digits=(6, 2))
    error_count = fields.Integer(string='Error Count', help='Number of errors on this date')

    @api.model
    def create_daily_usage(self):
        """Create daily usage records for all active tenants"""
        today = fields.Date.today()
        tenants = self.env['saas.tenant.instance'].search([('state', '=', 'active')])

        for tenant in tenants:
            existing = self.search([
                ('tenant_id', '=', tenant.id),
                ('date', '=', today)
            ])

            if not existing:
                self.create({
                    'tenant_id': tenant.id,
                    'date': today,
                    # These would be populated by monitoring system
                    'active_users': 1,
                    'total_users': 1,
                    'storage_used_gb': 0.1,
                    'uptime_hours': 24.0,
                })