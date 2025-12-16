# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import json


class SaaSTenantController(http.Controller):

    @http.route('/saas/tenant', type='http', auth='user', website=True)
    def tenant_portal(self, **kwargs):
        """Tenant portal for existing tenants"""
        return request.render('saas_custom_tenant.tenant_portal')

    @http.route('/saas/signup', type='http', auth='public', website=True)
    def signup_form(self, **kwargs):
        """Public signup form for new tenants"""
        plans = request.env['saas.subscription.plan'].sudo().search([
            ('is_active', '=', True)
        ], order='sequence')

        config = request.env['saas.tenant.config'].sudo().get_current_config()

        return request.render('saas_custom_tenant.signup_form', {
            'plans': plans,
            'config': config,
            'error': kwargs.get('error'),
            'success': kwargs.get('success'),
        })

    @http.route('/saas/signup/submit', type='http', auth='public', website=True, methods=['POST'], csrf=False)
    def signup_submit(self, **post):
        """Process signup form submission"""
        try:
            # Validate required fields
            if not post.get('company_name'):
                return request.redirect('/saas/signup?error=Company name is required')

            if not post.get('admin_email'):
                return request.redirect('/saas/signup?error=Email is required')

            if not post.get('plan_id'):
                return request.redirect('/saas/signup?error=Please select a subscription plan')

            # Create tenant record
            tenant = request.env['saas.tenant.instance'].sudo().create({
                'company_name': post.get('company_name'),
                'admin_email': post.get('admin_email'),
                'admin_name': post.get('admin_name', 'Administrator'),
                'admin_password': post.get('admin_password', ''),
                'phone': post.get('phone'),
                'subscription_plan_id': int(post.get('plan_id')),
                'state': 'pending',
                'is_trial': True,
            })

            return request.redirect(f'/saas/signup/success?tenant_id={tenant.id}')

        except Exception as e:
            return request.redirect(f'/saas/signup?error=Signup failed: {str(e)}')

    @http.route('/saas/signup/success', type='http', auth='public', website=True)
    def signup_success(self, tenant_id=None, **kwargs):
        """Success page after signup"""
        tenant = None
        if tenant_id:
            tenant = request.env['saas.tenant.instance'].sudo().browse(int(tenant_id))

        return request.render('saas_custom_tenant.signup_success', {
            'tenant': tenant,
        })

    @http.route('/saas/check-subdomain', type='json', auth='public', methods=['POST'])
    def check_subdomain(self, subdomain):
        """Check if subdomain is available"""
        if not subdomain:
            return {'available': False, 'message': 'Subdomain is required'}

        try:
            existing = request.env['saas.tenant.instance'].sudo().search([
                ('subdomain', '=', subdomain)
            ], limit=1)

            if existing:
                return {'available': False, 'message': 'Subdomain is already taken'}

            return {'available': True, 'message': 'Subdomain is available!'}

        except Exception as e:
            return {'available': False, 'message': f'Error checking subdomain: {str(e)}'}

    @http.route('/saas/api/tenant/status', type='json', auth='user', methods=['POST'])
    def tenant_status(self, tenant_id=None):
        """API endpoint to check tenant status"""
        if not tenant_id:
            return {'error': 'Tenant ID is required'}

        try:
            tenant = request.env['saas.tenant.instance'].browse(int(tenant_id))
            if not tenant.exists() or tenant.create_uid.id != request.env.user.id:
                return {'error': 'Tenant not found or access denied'}

            return {
                'id': tenant.id,
                'state': tenant.state,
                'url': tenant.url,
                'login_url': tenant.login_url,
                'is_active': tenant.state == 'active',
            }

        except Exception as e:
            return {'error': f'Error checking tenant status: {str(e)}'}