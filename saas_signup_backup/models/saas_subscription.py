from odoo import models, fields, api

class SaasSubscription(models.Model):
    _name = 'saas.subscription'
    _description = 'SaaS Subscription Plans'
    _order = 'sequence'

    name = fields.Char(string='Plan Name', required=True)
    code = fields.Char(string='Plan Code', required=True)
    sequence = fields.Integer(string='Sequence')

    # Pricing
    monthly_price = fields.Float(string='Monthly Price')
    yearly_price = fields.Float(string='Yearly Price')

    # Limits
    max_users = fields.Integer(string='Max Users', default=5, help='Maximum number of users allowed')
    max_storage = fields.Float(string='Max Storage (GB)')
    max_records = fields.Integer(string='Max Records', default=10000, help='Maximum database records')
    storage_limit = fields.Integer(string='Storage Limit (GB)', default=10, help='Storage limit in GB')
    max_databases = fields.Integer(string='Max Databases')

    # Resource Limits (for Docker/Container mode)
    cpu_limit = fields.Float(string='CPU Limit (cores)', default=1.0, 
                             help='Number of CPU cores (e.g., 0.5, 1.0, 2.0)')
    memory_limit_gb = fields.Float(string='Memory Limit (GB)', default=1.0,
                                   help='RAM limit in gigabytes')
    bandwidth_limit_gb = fields.Float(string='Bandwidth Limit (GB/month)', default=50.0,
                                      help='Monthly bandwidth limit')

    # Settings
    trial_days = fields.Integer(string='Trial Days', default=14)
    is_popular = fields.Boolean(string='Popular Plan')
    is_active = fields.Boolean(string='Active', default=True)

    features = fields.Text(string='Features')
    
    # Modules to install for this plan
    module_list = fields.Text(
        string='Modules to Install',
        help='Comma-separated list of technical module names to install for this plan. E.g: mail,hr,point_of_sale,project,sale,hr_expense'
    )

    client_count = fields.Integer(compute='_compute_client_count', string='Active Clients')

    @api.depends('is_active')
    def _compute_client_count(self):
        for plan in self:
            plan.client_count = self.env['saas.client'].search_count([
                ('subscription_id', '=', plan.id),
                ('state', '=', 'active')
            ])