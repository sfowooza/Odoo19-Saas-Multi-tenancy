# -*- coding: utf-8 -*-

from odoo import models, fields, api
import psycopg2
from odoo.tools import config
import logging

_logger = logging.getLogger(__name__)


class SaaSDashboard(models.Model):
    _name = 'saas.dashboard'
    _description = 'SaaS Monitoring Dashboard'
    _auto = False  # No database table needed
    
    @api.model
    def get_dashboard_data(self):
        """Get comprehensive dashboard metrics"""
        return {
            'tenants': self._get_tenant_stats(),
            'resources': self._get_resource_usage(),
            'recent_signups': self._get_recent_signups(),
            'revenue': self._get_revenue_stats(),
            'alerts': self._get_system_alerts(),
            'database_sizes': self._get_database_sizes(),
        }
    
    def _get_tenant_stats(self):
        """Get tenant statistics"""
        Client = self.env['saas.client']
        
        total = Client.search_count([])
        active = Client.search_count([('state', '=', 'active')])
        suspended = Client.search_count([('state', '=', 'suspended')])
        pending = Client.search_count([('state', '=', 'pending')])
        provisioning = Client.search_count([('state', '=', 'provisioning')])
        
        # Tenants by plan
        self.env.cr.execute("""
            SELECT 
                COALESCE(s.name, 'No Plan') as plan_name,
                COUNT(c.id) as count
            FROM saas_client c
            LEFT JOIN saas_subscription s ON c.plan_id = s.id
            WHERE c.state = 'active'
            GROUP BY s.name
            ORDER BY count DESC
        """)
        by_plan = self.env.cr.dictfetchall()
        
        return {
            'total': total,
            'active': active,
            'suspended': suspended,
            'pending': pending,
            'provisioning': provisioning,
            'by_plan': by_plan
        }
    
    def _get_resource_usage(self):
        """Get system resource usage"""
        try:
            import psutil
            
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_percent': round(cpu_percent, 1),
                'cpu_count': psutil.cpu_count(),
                'memory_total_gb': round(memory.total / (1024**3), 2),
                'memory_used_gb': round(memory.used / (1024**3), 2),
                'memory_percent': round(memory.percent, 1),
                'disk_total_gb': round(disk.total / (1024**3), 2),
                'disk_used_gb': round(disk.used / (1024**3), 2),
                'disk_percent': round(disk.percent, 1),
            }
        except ImportError:
            _logger.warning('psutil not installed - system metrics unavailable')
            return {
                'error': 'psutil not installed',
                'message': 'Run: pip install psutil'
            }
    
    def _get_recent_signups(self, limit=10):
        """Get recent tenant signups"""
        clients = self.env['saas.client'].search([
            ('create_date', '!=', False)
        ], order='create_date desc', limit=limit)
        
        return [{
            'id': c.id,
            'name': c.name,
            'subdomain': c.subdomain,
            'plan': c.plan_id.name if c.plan_id else 'N/A',
            'port': c.port if c.port else 'N/A',
            'date': c.create_date.strftime('%Y-%m-%d %H:%M') if c.create_date else '',
            'state': c.state
        } for c in clients]
    
    def _get_revenue_stats(self):
        """Calculate revenue statistics"""
        self.env.cr.execute("""
            SELECT 
                COALESCE(SUM(s.monthly_price), 0) as mrr,
                COALESCE(SUM(s.yearly_price), 0) as arr,
                COUNT(c.id) as paying_customers
            FROM saas_client c
            JOIN saas_subscription s ON c.plan_id = s.id
            WHERE c.state = 'active' AND s.monthly_price > 0
        """)
        result = self.env.cr.fetchone()
        
        mrr = result[0] if result else 0
        arr_total = result[1] if result else 0
        paying = result[2] if result else 0
        
        return {
            'mrr': round(mrr, 2),
            'arr': round(arr_total, 2),
            'arr_from_monthly': round(mrr * 12, 2),
            'paying_customers': paying,
            'free_customers': self.env['saas.client'].search_count([
                ('state', '=', 'active'),
                ('plan_id.monthly_price', '=', 0)
            ])
        }
    
    def _get_system_alerts(self):
        """Get system alerts and warnings"""
        alerts = []
        
        # Resource alerts
        try:
            import psutil
            
            cpu = psutil.cpu_percent()
            if cpu > 80:
                alerts.append({
                    'type': 'warning',
                    'icon': 'fa-exclamation-triangle',
                    'message': f'High CPU usage: {cpu}%'
                })
            
            memory = psutil.virtual_memory().percent
            if memory > 85:
                alerts.append({
                    'type': 'warning',
                    'icon': 'fa-exclamation-triangle',
                    'message': f'High memory usage: {memory}%'
                })
            
            disk = psutil.disk_usage('/').percent
            if disk > 90:
                alerts.append({
                    'type': 'danger',
                    'icon': 'fa-exclamation-circle',
                    'message': f'Critical: Disk space at {disk}%'
                })
        except ImportError:
            pass
        
        # Pending tenants
        pending = self.env['saas.client'].search_count([('state', '=', 'pending')])
        if pending > 0:
            alerts.append({
                'type': 'info',
                'icon': 'fa-clock-o',
                'message': f'{pending} tenant(s) awaiting approval'
            })
        
        # Expiring subscriptions
        expiring = self.env['saas.client'].search_count([
            ('state', '=', 'active'),
            ('trial_end_date', '!=', False),
            ('trial_end_date', '<=', fields.Date.add(fields.Date.today(), days=7))
        ])
        if expiring > 0:
            alerts.append({
                'type': 'warning',
                'icon': 'fa-calendar',
                'message': f'{expiring} trial(s) expiring within 7 days'
            })
        
        # Failed provisions
        failed = self.env['saas.client'].search_count([
            ('state', '=', 'draft'),
            ('create_date', '<', fields.Datetime.subtract(fields.Datetime.now(), hours=24))
        ])
        if failed > 0:
            alerts.append({
                'type': 'danger',
                'icon': 'fa-times-circle',
                'message': f'{failed} signup(s) not provisioned after 24h'
            })
        
        return alerts
    
    def _get_database_sizes(self):
        """Get sizes of tenant databases"""
        try:
            conn = psycopg2.connect(
                host=config.get('db_host', 'localhost'),
                port=config.get('db_port', 5432),
                database='postgres',
                user=config.get('db_user', 'odoo'),
                password=config.get('db_password', 'odoo')
            )
            conn.autocommit = True
            cur = conn.cursor()
            
            # Get all SaaS databases
            cur.execute("""
                SELECT 
                    datname as database,
                    pg_size_pretty(pg_database_size(datname)) as size,
                    pg_database_size(datname) as size_bytes
                FROM pg_database 
                WHERE datname LIKE 'saas_%' OR datname LIKE 'db_%'
                ORDER BY pg_database_size(datname) DESC
                LIMIT 20
            """)
            
            results = cur.fetchall()
            cur.close()
            conn.close()
            
            return [{
                'database': r[0],
                'size': r[1],
                'size_bytes': r[2],
                'size_mb': round(r[2] / (1024 * 1024), 2)
            } for r in results]
            
        except Exception as e:
            _logger.error(f"Failed to get database sizes: {e}")
            return []
