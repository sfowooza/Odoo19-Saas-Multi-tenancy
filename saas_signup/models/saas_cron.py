# -*- coding: utf-8 -*-

from odoo import models, api, fields
import logging
import psycopg2
from odoo.tools import config

_logger = logging.getLogger(__name__)


class SaaSCron(models.Model):
    _name = 'saas.cron'
    _description = 'SaaS Scheduled Tasks'
    
    @api.model
    def monitor_resource_limits(self):
        """Monitor tenant resource usage and enforce limits"""
        _logger.info('Running resource limit monitoring...')
        
        clients = self.env['saas.client'].search([
            ('state', '=', 'active'),
            ('database_name', '!=', False)
        ])
        
        for client in clients:
            try:
                # Check database size
                db_size_mb = self._get_database_size(client.database_name)
                plan_limit_mb = (client.plan_id.storage_limit or 10) * 1024
                
                # Update stored value
                client.storage_used_mb = db_size_mb
                
                # 90% warning
                if db_size_mb > plan_limit_mb * 0.9:
                    client.message_post(
                        body=f"⚠️ Storage Warning: {db_size_mb:.1f}MB / {plan_limit_mb}MB used ({db_size_mb/plan_limit_mb*100:.1f}%)"
                    )
                    self._send_limit_notification(client, 'storage', db_size_mb, plan_limit_mb)
                
                # Over limit - suspend
                if db_size_mb > plan_limit_mb:
                    _logger.warning(f"Tenant {client.subdomain} exceeded storage limit")
                    client.message_post(
                        body=f"🚫 Storage limit exceeded. Tenant suspended."
                    )
                    client.action_suspend()
                
                # Check user count
                if client.database_name:
                    user_count = self._get_user_count(client.database_name)
                    if user_count > client.max_users:
                        client.message_post(
                            body=f"⚠️ User limit exceeded: {user_count} / {client.max_users} users"
                        )
                
            except Exception as e:
                _logger.error(f"Error monitoring {client.subdomain}: {e}")
    
    @api.model
    def check_trial_expirations(self):
        """Check and handle trial expirations"""
        _logger.info('Checking trial expirations...')
        
        # Expiring in 3 days
        expiring_soon = self.env['saas.client'].search([
            ('state', '=', 'active'),
            ('trial_end_date', '!=', False),
            ('trial_end_date', '<=', fields.Date.add(fields.Date.today(), days=3)),
            ('trial_end_date', '>', fields.Date.today())
        ])
        
        for client in expiring_soon:
            days_left = (client.trial_end_date - fields.Date.today()).days
            client.message_post(
                body=f"⏰ Trial expiring in {days_left} day(s)"
            )
            self._send_trial_reminder(client, days_left)
        
        # Expired today
        expired = self.env['saas.client'].search([
            ('state', '=', 'active'),
            ('trial_end_date', '=', fields.Date.today())
        ])
        
        for client in expired:
            _logger.info(f"Trial expired for {client.subdomain}")
            client.action_suspend()
            client.message_post(body="🚫 Trial expired - account suspended")
            self._send_trial_expired(client)
    
    @api.model
    def cleanup_old_tenants(self):
        """Clean up cancelled tenants after grace period"""
        _logger.info('Cleaning up old cancelled tenants...')
        
        grace_days = 30
        cutoff_date = fields.Datetime.subtract(fields.Datetime.now(), days=grace_days)
        
        old_cancelled = self.env['saas.client'].search([
            ('state', '=', 'cancelled'),
            ('write_date', '<', cutoff_date)
        ])
        
        for client in old_cancelled:
            try:
                _logger.info(f"Cleaning up {client.subdomain}")
                if client.database_name:
                    self._delete_database(client.database_name)
                client.database_name = False
                client.message_post(body="🗑️ Tenant data deleted after grace period")
            except Exception as e:
                _logger.error(f"Cleanup failed for {client.subdomain}: {e}")
    
    def _get_database_size(self, database_name):
        """Get database size in MB"""
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
            
            cur.execute("""
                SELECT pg_database_size(%s) / (1024 * 1024)
            """, (database_name,))
            
            result = cur.fetchone()
            cur.close()
            conn.close()
            
            return result[0] if result else 0
        except Exception as e:
            _logger.error(f"Failed to get DB size: {e}")
            return 0
    
    def _get_user_count(self, database_name):
        """Get active user count in tenant database"""
        try:
            conn = psycopg2.connect(
                host=config.get('db_host', 'localhost'),
                port=config.get('db_port', 5432),
                database=database_name,
                user=config.get('db_user', 'odoo'),
                password=config.get('db_password', 'odoo')
            )
            cur = conn.cursor()
            
            cur.execute("""
                SELECT COUNT(*) FROM res_users 
                WHERE active = true AND id > 2
            """)
            
            result = cur.fetchone()
            cur.close()
            conn.close()
            
            return result[0] if result else 0
        except Exception as e:
            _logger.error(f"Failed to get user count: {e}")
            return 0
    
    def _delete_database(self, database_name):
        """Delete a database"""
        try:
            from odoo.service import db as db_service
            master_pwd = config.get('admin_passwd', 'admin')
            db_service.exp_drop(master_pwd, database_name)
            _logger.info(f"Deleted database: {database_name}")
        except Exception as e:
            _logger.error(f"Failed to delete database {database_name}: {e}")
    
    def _send_limit_notification(self, client, resource_type, current, limit):
        """Send resource limit notification email"""
        try:
            template = self.env.ref('saas_signup.email_template_resource_limit', raise_if_not_found=False)
            if template:
                template.with_context(
                    resource_type=resource_type,
                    current_value=current,
                    limit_value=limit
                ).send_mail(client.id, force_send=True)
                _logger.info(f"Sent resource limit notification to {client.admin_email}")
        except Exception as e:
            _logger.error(f"Failed to send resource limit notification: {e}")
    
    def _send_trial_reminder(self, client, days_left):
        """Send trial expiration reminder"""
        try:
            template = self.env.ref('saas_signup.email_template_trial_reminder', raise_if_not_found=False)
            if template:
                template.with_context(days_remaining=days_left).send_mail(client.id, force_send=True)
                _logger.info(f"Sent trial reminder to {client.admin_email} ({days_left} days left)")
        except Exception as e:
            _logger.error(f"Failed to send trial reminder: {e}")
    
    def _send_trial_expired(self, client):
        """Send trial expired notification"""
        try:
            template = self.env.ref('saas_signup.email_template_trial_expired', raise_if_not_found=False)
            if template:
                template.send_mail(client.id, force_send=True)
                _logger.info(f"Sent trial expired notification to {client.admin_email}")
        except Exception as e:
            _logger.error(f"Failed to send trial expired notification: {e}")
