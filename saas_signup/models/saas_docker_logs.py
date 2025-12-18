# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import subprocess
import threading
import time

class SaasDockerLogs(models.Model):
    _name = 'saas.docker.logs'
    _description = 'Docker Service Logs'
    _order = 'create_date desc'

    config_id = fields.Many2one('saas.port.config', string='Port Configuration')
    service_name = fields.Char(string='Service Name', required=True)
    log_content = fields.Text(string='Log Content', readonly=True)
    create_date = fields.Datetime(string='Created', default=fields.Datetime.now)
    auto_refresh = fields.Boolean(string='Auto Refresh', default=True)

    @api.model
    def get_recent_logs(self, service_name=None, lines=100):
        """Get recent logs from Docker service"""
        try:
            # Build docker-compose command
            cmd = ['docker-compose', 'logs', '--tail', str(lines)]
            if service_name:
                cmd.append(service_name)

            # Run command and capture output
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                return result.stdout
            else:
                return f"Error getting logs: {result.stderr}"

        except Exception as e:
            return f"Error: {str(e)}"

    def refresh_logs(self):
        """Refresh logs from Docker"""
        if self.auto_refresh:
            # Get recent logs based on service name
            service = self.service_name or 'odoo19'
            self.log_content = self.get_recent_logs(service, lines=200)
            return True
        return False

    def action_refresh(self):
        """Refresh logs button action"""
        self.refresh_logs()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }