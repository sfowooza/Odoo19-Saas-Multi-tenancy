from odoo import http
from odoo.http import request
import re


class SaasSignupController(http.Controller):
    
    @http.route('/saas/signup', type='http', auth='public', website=True, sitemap=False)
    def saas_signup(self, **kw):
        """Display the SaaS signup form"""
        # Get subscription plans
        plans = request.env['saas.subscription'].sudo().search([
            ('is_active', '=', True)
        ], order='sequence')
        
        # Get countries for dropdown
        countries = request.env['res.country'].sudo().search([])
        
        values = {
            'plans': plans,
            'countries': countries,
            'error': kw.get('error'),
            'success': kw.get('success'),
        }
        
        return request.render('saas_signup.signup_form', values)
    
    @http.route('/saas/signup/submit', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def saas_signup_submit(self, **post):
        """Process the signup form submission"""
        error = {}
        
        # Validate required fields
        required_fields = ['company_name', 'subdomain', 'admin_email', 'admin_name', 'plan_id']
        for field in required_fields:
            if not post.get(field):
                error[field] = 'This field is required'
        
        # Validate subdomain format
        subdomain = post.get('subdomain', '')
        if subdomain:
            if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$', subdomain):
                error['subdomain'] = 'Subdomain must contain only lowercase letters, numbers, and hyphens'
            
            # Check if subdomain already exists
            existing = request.env['saas.client'].sudo().search([
                ('subdomain', '=', subdomain)
            ], limit=1)
            if existing:
                error['subdomain'] = 'This subdomain is already taken'
        
        # Validate email
        email = post.get('admin_email', '')
        if email and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            error['email'] = 'Please enter a valid email address'
        
        if error:
            # Return to form with errors
            return request.redirect('/saas/signup?' + '&'.join([f'error_{k}={v}' for k, v in error.items()]))
        
        # Create the SaaS client
        try:
            plan = request.env['saas.subscription'].sudo().browse(int(post.get('plan_id')))
            
            client_vals = {
                'company_name': post.get('company_name'),
                'subdomain': subdomain,
                'admin_email': email,
                'admin_name': post.get('admin_name'),
                'phone': post.get('phone', ''),
                'country_id': int(post.get('country_id')) if post.get('country_id') else False,
                'subscription_id': plan.id,
                'is_trial': True,
                'state': 'pending',
            }
            
            client = request.env['saas.client'].sudo().create(client_vals)
            
            # Send welcome email (if mail template exists)
            template = request.env.ref('saas_signup.mail_template_welcome', raise_if_not_found=False)
            if template:
                template.sudo().send_mail(client.id, force_send=True)
            
            return request.redirect(f'/saas/signup/success?client_id={client.id}')
            
        except Exception as e:
            return request.redirect('/saas/signup?error=An error occurred. Please try again.')
    
    @http.route('/saas/signup/success', type='http', auth='public', website=True)
    def saas_signup_success(self, client_id=None, **kw):
        """Display success page after signup"""
        client = None
        if client_id:
            client = request.env['saas.client'].sudo().browse(int(client_id))
        
        values = {
            'client': client,
        }
        
        return request.render('saas_signup.signup_success', values)
    
    @http.route('/saas/check-subdomain', type='json', auth='public', methods=['POST'])
    def check_subdomain(self, subdomain):
        """AJAX endpoint to check subdomain availability"""
        if not subdomain:
            return {'available': False, 'message': 'Subdomain is required'}
        
        # Validate format
        if not re.match(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$', subdomain):
            return {
                'available': False,
                'message': 'Must contain only lowercase letters, numbers, and hyphens'
            }
        
        # Check availability
        existing = request.env['saas.client'].sudo().search([
            ('subdomain', '=', subdomain)
        ], limit=1)
        
        if existing:
            return {'available': False, 'message': 'This subdomain is already taken'}
        
        return {'available': True, 'message': 'Subdomain is available!'}
    
    @http.route('/saas/pricing', type='http', auth='public', website=True)
    def saas_pricing(self, **kw):
        """Display pricing page"""
        plans = request.env['saas.subscription'].sudo().search([
            ('is_active', '=', True)
        ], order='sequence')
        
        values = {
            'plans': plans,
        }
        
        return request.render('saas_signup.pricing_page', values)
