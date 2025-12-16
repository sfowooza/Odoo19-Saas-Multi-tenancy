# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SubscriptionPlan(models.Model):
    _name = 'saas.subscription.plan'
    _description = 'SaaS Subscription Plan'
    _order = 'sequence, price'

    name = fields.Char(string='Plan Name', required=True, help='Name of the subscription plan')
    description = fields.Text(string='Description', help='Detailed description of the plan')
    code = fields.Char(string='Plan Code', help='Unique code for the plan')

    # Pricing
    price = fields.Float(string='Price', required=True, help='Monthly price for this plan')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    billing_cycle = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly')
    ], string='Billing Cycle', default='monthly', required=True)

    # Limits and Resources
    max_users = fields.Integer(string='Maximum Users', default=10, help='Maximum number of users allowed')
    storage_gb = fields.Integer(string='Storage (GB)', default=10, help='Storage limit in gigabytes')
    cpu_limit = fields.Float(string='CPU Limit', default=1.0, help='CPU limit for this plan')
    memory_limit = fields.Char(string='Memory Limit', default='1g', help='Memory limit (e.g., 1g, 2g)')

    # Trial Settings
    trial_days = fields.Integer(string='Trial Days', default=14, help='Number of trial days for this plan')
    enable_trial = fields.Boolean(string='Enable Trial', default=True, help='Whether trial is available')

    # Features
    module_ids = fields.Many2many('ir.module.module', string='Included Modules', help='Odoo modules included in this plan')
    features = fields.Text(string='Features', help='List of features included in this plan')

    # Display and Status
    sequence = fields.Integer(string='Sequence', default=10, help='Display order')
    is_active = fields.Boolean(string='Active', default=True, help='Whether this plan is currently available')
    is_popular = fields.Boolean(string='Popular', default=False, help='Mark as popular plan')
    color = fields.Char(string='Color', help='Background color for plan card')

    # Statistics
    tenant_count = fields.Integer(string='Active Tenants', compute='_compute_tenant_count', help='Number of active tenants on this plan')

    @api.depends('is_active')
    def _compute_tenant_count(self):
        """Count active tenants for each plan"""
        for plan in self:
            plan.tenant_count = self.env['saas.tenant.instance'].search_count([
                ('subscription_plan_id', '=', plan.id),
                ('state', '=', 'active')
            ])

    @api.constrains('price')
    def _check_price(self):
        """Validate price is positive"""
        for plan in self:
            if plan.price < 0:
                raise ValidationError(_('Price cannot be negative'))

    @api.constrains('max_users', 'storage_gb', 'trial_days')
    def _check_limits(self):
        """Validate limits are reasonable"""
        for plan in self:
            if plan.max_users <= 0:
                raise ValidationError(_('Maximum users must be positive'))
            if plan.storage_gb <= 0:
                raise ValidationError(_('Storage must be positive'))
            if plan.trial_days < 0:
                raise ValidationError(_('Trial days cannot be negative'))

    def action_view_tenants(self):
        """View tenants on this plan"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tenants on %s') % self.name,
            'res_model': 'saas.tenant.instance',
            'view_mode': 'tree,form',
            'domain': [('subscription_plan_id', '=', self.id)],
            'context': {'default_subscription_plan_id': self.id}
        }