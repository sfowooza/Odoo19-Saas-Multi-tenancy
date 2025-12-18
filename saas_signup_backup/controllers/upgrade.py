# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class SaasUpgradeController(http.Controller):

    @http.route('/saas/upgrade', type='http', auth='public', website=True)
    def upgrade_page(self, **kw):
        """Show upgrade plans page"""
        # Get all active plans
        plans = request.env['saas.subscription'].sudo().search([
            ('is_active', '=', True)
        ], order='sequence')
        
        # Get client info if subdomain provided
        subdomain = kw.get('subdomain')
        client = None
        if subdomain:
            client = request.env['saas.client'].sudo().search([
                ('subdomain', '=', subdomain)
            ], limit=1)
        
        values = {
            'plans': plans,
            'client': client,
            'subdomain': subdomain,
        }
        
        return request.render('saas_signup.upgrade_page', values)
    
    @http.route('/saas/upgrade/request', type='http', auth='public', website=True, methods=['POST'], csrf=False)
    def upgrade_request(self, **post):
        """Process upgrade request from tenant"""
        subdomain = post.get('subdomain')
        new_plan_id = int(post.get('plan_id'))
        
        if not subdomain or not new_plan_id:
            return request.redirect('/saas/upgrade?error=missing_data')
        
        # Find client
        client = request.env['saas.client'].sudo().search([
            ('subdomain', '=', subdomain)
        ], limit=1)
        
        if not client:
            return request.redirect('/saas/upgrade?error=client_not_found')
        
        # Request upgrade
        try:
            client.action_request_upgrade(new_plan_id)
            _logger.info(f"Upgrade request: {client.company_name} → Plan {new_plan_id}")
            return request.redirect(f'/saas/upgrade/success?subdomain={subdomain}')
        except Exception as e:
            _logger.error(f"Upgrade request error: {e}")
            return request.redirect(f'/saas/upgrade?subdomain={subdomain}&error=request_failed')
    
    @http.route('/saas/upgrade/success', type='http', auth='public', website=True)
    def upgrade_success(self, **kw):
        """Show upgrade request success page"""
        subdomain = kw.get('subdomain')
        client = None
        if subdomain:
            client = request.env['saas.client'].sudo().search([
                ('subdomain', '=', subdomain)
            ], limit=1)
        
        values = {
            'client': client,
            'subdomain': subdomain,
        }
        
        return request.render('saas_signup.upgrade_success_page', values)
