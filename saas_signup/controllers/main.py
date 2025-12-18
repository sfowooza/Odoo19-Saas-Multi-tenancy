from odoo import http
from odoo.http import request
import docker
import psycopg2
from psycopg2 import sql
import logging
import re

_logger = logging.getLogger(__name__)

class SaasSignupController(http.Controller):

    @http.route('/saas/features', type='http', auth='public', website=True)
    def saas_features(self, **kw):
        """Display SaaS features page"""
        return request.render('saas_signup.features_page', {})

    @http.route('/saas/pricing', type='http', auth='public', website=True)
    def saas_pricing(self, **kw):
        """Display SaaS pricing page"""
        plans = request.env['saas.subscription'].sudo().search([
            ('is_active', '=', True)
        ], order='sequence')
        return request.render('saas_signup.pricing_page', {'plans': plans})

    @http.route('/saas/signup', type='http', auth='public', website=True)
    def saas_signup(self, **kw):
        """Display the SaaS signup form"""
        plans = request.env['saas.subscription'].sudo().search([
            ('is_active', '=', True)
        ], order='sequence')

        countries = request.env['res.country'].sudo().search([])
        config = request.env['saas.configuration'].sudo().get_config()

        values = {
            'plans': plans,
            'countries': countries,
            'config': config,
            'error': kw.get('error'),
            'success': kw.get('success'),
        }

        return request.render('saas_signup.signup_form', values)

    @http.route('/saas/signup/submit', type='http', auth='public', website=True, methods=['POST'], csrf=False)
    def saas_signup_submit(self, **post):
        """Process the signup form submission and provision tenant container"""
        error = {}
        
        # Get SaaS configuration
        config = request.env['saas.configuration'].sudo().get_config()

        # Validate company name
        company_name = post.get('company_name', '').strip()
        if not company_name:
            error['company'] = 'Company name is required'

        # Get or generate subdomain
        subdomain = post.get('subdomain', '').strip()
        if not subdomain:
            # Auto-generate from company name if not provided
            subdomain = re.sub(r'[^a-z0-9]', '', company_name.lower())
        else:
            # Clean user input
            subdomain = re.sub(r'[^a-z0-9]', '', subdomain.lower())
        
        if not subdomain:
            subdomain = 'tenant'

        # Validate email
        email = post.get('admin_email', '').strip()
        if not email:
            error['email'] = 'Email is required'
        elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            error['email'] = 'Please enter a valid email address'

        # Check if subdomain already exists
        existing = request.env['saas.client'].sudo().search([
            ('subdomain', '=', subdomain)
        ], limit=1)
        if existing:
            error['subdomain'] = f'A tenant with name "{company_name}" already exists. Please choose a different name.'

        # Validate plan
        if not post.get('plan_id'):
            error['plan'] = 'Please select a subscription plan'

        if error:
            error_msg = '. '.join([f"{k}: {v}" for k, v in error.items()])
            return request.redirect(f'/saas/signup?error={error_msg}')

        # Create the SaaS client record immediately
        try:
            plan = request.env['saas.subscription'].sudo().browse(int(post.get('plan_id')))
            admin_name = post.get('admin_name', 'Admin')

            # Generate random password if not provided
            import random
            import string
            admin_password = post.get('admin_password', '').strip()
            if not admin_password:
                admin_password = ''.join(
                    random.choices(string.ascii_letters + string.digits + '!@#$%^&*', k=12)
                )

            # Get port based on deployment mode
            _logger.info(f"Creating tenant record: {subdomain} (mode: {config.deployment_mode})")
            
            # Always assign unique tenant ports (nginx routes subdomains to these ports)
            port = config.starting_port or 8001
            docker_client = docker.from_env()
            used_ports = [8080, 9069]  # Reserved ports
            
            # Get existing tenant ports
            existing_clients = request.env['saas.client'].sudo().search([])
            for existing in existing_clients:
                if existing.port:
                    used_ports.append(existing.port)
            
            containers = docker_client.containers.list(
                all=True,
                filters={"label": "saas.type=tenant"}
            )
            for container in containers:
                port_label = container.labels.get('saas.port')
                if port_label:
                    used_ports.append(int(port_label))
            
            while port in used_ports:
                port += 1
            
            db_name = f'saas_{subdomain}'
            
            # Create client record immediately - provisioning will happen in background
            client_vals = {
                'company_name': company_name,
                'subdomain': subdomain,
                'database_name': db_name,
                'port': port,
                'admin_name': admin_name,
                'admin_email': email,
                'admin_password': admin_password,
                'phone': post.get('phone', ''),
                'country_id': int(post.get('country_id')) if post.get('country_id') else False,
                'subscription_id': plan.id,
                'state': 'pending',
                'is_trial': True,
            }
            
            client = request.env['saas.client'].sudo().create(client_vals)
            _logger.info(f"Client record created: {client.id}, starting background provisioning...")
            
            # Get modules to install from plan
            plan_modules = plan.module_list or 'base'
            _logger.info(f"Plan modules: {plan_modules}")
            
            # Start background thread to provision tenant
            import threading
            def provision_tenant():
                """Background provisioning - runs asynchronously"""
                try:
                    _logger.info(f"[Background] Starting provisioning for {subdomain}")
                    
                    # Database configuration - get from Odoo config
                    from odoo.tools import config as odoo_config
                    db_host = odoo_config.get('db_host', 'db')
                    db_port = int(odoo_config.get('db_port', 5432))
                    db_user = odoo_config.get('db_user', 'odoo')
                    db_password = odoo_config.get('db_password', '248413')  # Use correct password
                    
                    # Create database
                    _logger.info(f"[Background] Creating database: {db_name}")
                    conn = psycopg2.connect(
                        host=db_host,
                        port=db_port,
                        database="postgres",
                        user=db_user,
                        password=db_password
                    )
                    conn.autocommit = True
                    cursor = conn.cursor()
                    
                    cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
                    if not cursor.fetchone():
                        cursor.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))
                    
                    cursor.close()
                    conn.close()
                    
                    # Initialize database with plan-specific modules
                    _logger.info(f"[Background] Installing plan modules: {plan_modules}...")
                    
                    # Install modules with proper initialization
                    try:
                        init_container = docker_client.containers.run(
                            'odoo:19',
                            name=f"init_{subdomain}",
                            remove=True,
                            environment={
                                'HOST': db_host, 
                                'PORT': str(db_port), 
                                'USER': db_user, 
                                'PASSWORD': db_password
                            },
                            command=f'odoo -d {db_name} -i {plan_modules} --stop-after-init --without-demo=all --load-language=en_US',
                            network='odoo19_odoo-network',
                            stdout=True,
                            stderr=True
                        )
                        _logger.info(f"[Background] Module installation completed")
                    except Exception as init_error:
                        _logger.error(f"[Background] Module installation failed: {init_error}")
                        raise
                    
                    # Create admin user
                    _logger.info(f"[Background] Creating admin user...")
                    from passlib.context import CryptContext
                    pwd_context = CryptContext(schemes=['pbkdf2_sha512'], deprecated='auto')
                    hashed_password = pwd_context.hash(admin_password)
                    
                    tenant_conn = psycopg2.connect(
                        host=db_host, port=db_port, database=db_name,
                        user=db_user, password=db_password
                    )
                    tenant_conn.autocommit = True
                    tenant_cursor = tenant_conn.cursor()
                    
                    # Find admin user (don't use hardcoded ID as modules may create additional users)
                    tenant_cursor.execute(
                        "SELECT id, partner_id FROM res_users WHERE login='admin' LIMIT 1"
                    )
                    admin_result = tenant_cursor.fetchone()
                    
                    if admin_result:
                        admin_user_id, admin_partner_id = admin_result
                        _logger.info(f"[Background] Found admin user ID: {admin_user_id}, updating credentials...")
                        
                        # Update admin user credentials
                        tenant_cursor.execute(
                            "UPDATE res_users SET login=%s, password=%s WHERE id=%s",
                            (email, hashed_password, admin_user_id)
                        )
                        
                        # Update partner name and email
                        tenant_cursor.execute(
                            "UPDATE res_partner SET name=%s, email=%s WHERE id=%s",
                            (admin_name, email, admin_partner_id)
                        )
                        
                        _logger.info(f"[Background] ✅ Admin credentials updated: login={email}")
                    else:
                        _logger.error(f"[Background] ❌ Admin user not found in tenant database!")
                    
                    # Verify modules were installed
                    _logger.info(f"[Background] Verifying module installation...")
                    plan_module_list = [m.strip() for m in plan_modules.split(',')]
                    plan_module_names = ','.join([f"'{m}'" for m in plan_module_list])
                    
                    tenant_cursor.execute(
                        f"SELECT name, state FROM ir_module_module WHERE name IN ({plan_module_names})"
                    )
                    installed_modules = tenant_cursor.fetchall()
                    installed_count = sum(1 for _, state in installed_modules if state == 'installed')
                    _logger.info(f"[Background] Installed {installed_count}/{len(plan_module_list)} plan modules")
                    
                    # Hide non-plan modules from Apps menu
                    _logger.info(f"[Background] Hiding non-plan modules...")
                    tenant_cursor.execute(
                        f"UPDATE ir_module_module SET state='uninstallable' "
                        f"WHERE state='uninstalled' AND name NOT IN ({plan_module_names})"
                    )
                    _logger.info(f"[Background] Tenant ready with all plan modules installed")
                    
                    tenant_cursor.close()
                    tenant_conn.close()
                    
                    # Create volume for future use
                    _logger.info(f"[Background] Creating volume for future container...")
                    volume_name = f"odoo_tenant_{subdomain}_data"
                    try:
                        docker_client.volumes.create(name=volume_name)
                        _logger.info(f"[Background] Volume created: {volume_name}")
                    except Exception as vol_error:
                        _logger.warning(f"[Background] Volume creation warning: {vol_error}")
                    
                    # Create temporary nginx container showing "waiting" page
                    _logger.info(f"[Background] Creating waiting page container on port {port}...")
                    waiting_container_name = f"waiting_{subdomain}"
                    
                    # Create simple nginx config
                    nginx_html = '''<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Account Pending Approval</title><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}.container{max-width:600px;background:white;border-radius:20px;box-shadow:0 20px 60px rgba(0,0,0,0.3);padding:50px;text-align:center;animation:fadeIn 0.5s ease-in}@keyframes fadeIn{from{opacity:0;transform:translateY(-20px)}to{opacity:1;transform:translateY(0)}}.icon{font-size:80px;margin-bottom:20px;animation:pulse 2s infinite}@keyframes pulse{0%,100%{transform:scale(1)}50%{transform:scale(1.1)}}h1{color:#333;font-size:32px;margin-bottom:15px}.status{display:inline-block;background:#FEF3C7;color:#92400E;padding:10px 25px;border-radius:25px;font-weight:bold;margin:20px 0;border:2px solid #F59E0B}p{color:#666;font-size:18px;line-height:1.6;margin:20px 0}.info-box{background:#F3F4F6;border-left:4px solid #667eea;padding:20px;margin:30px 0;text-align:left;border-radius:5px}.info-box h3{color:#667eea;margin-bottom:15px;font-size:18px}.info-box ul{list-style:none;padding:0}.info-box li{padding:8px 0;color:#555}.info-box li:before{content:"✓ ";color:#10B981;font-weight:bold;margin-right:8px}.footer{margin-top:30px;padding-top:20px;border-top:1px solid #E5E7EB;color:#999;font-size:14px}.refresh-notice{background:#DBEAFE;color:#1E40AF;padding:15px;border-radius:10px;margin-top:20px;font-size:14px}</style></head><body><div class="container"><div class="icon">⏳</div><h1>Account Pending Approval</h1><div class="status">⚠️ Awaiting Admin Approval</div><p>Thank you for signing up! Your Odoo ERP instance is being prepared.</p><div class="info-box"><h3>📋 What's Happening?</h3><ul><li>Your account has been created</li><li>Database has been prepared</li><li>Awaiting administrator approval</li><li>Your instance will activate automatically once approved</li></ul></div><p><strong>Approval Time:</strong> Usually within 24 hours</p><div class="refresh-notice"><strong>💡 Tip:</strong> Once approved, simply refresh this page. The Odoo login will appear automatically.</div><div class="footer"><p>Odoo ERP SaaS Platform</p><p>Need help? Contact your administrator</p></div></div><script>setTimeout(function(){location.reload()},60000);</script></body></html>'''
                    
                    try:
                        # Create temporary nginx container showing waiting page
                        waiting_container = docker_client.containers.run(
                            'nginx:alpine',
                            name=waiting_container_name,
                            detach=True,
                            command=[
                                'sh', '-c',
                                f'echo \'{nginx_html}\' > /usr/share/nginx/html/index.html && nginx -g "daemon off;"'
                            ],
                            ports={'80/tcp': port},
                            network='odoo19_odoo-network',
                            labels={
                                'saas.type': 'waiting',
                                'saas.tenant': subdomain,
                                'saas.port': str(port)
                            },
                            restart_policy={'Name': 'unless-stopped'}
                        )
                        _logger.info(f"[Background] Waiting page container started: {waiting_container.id[:12]}")
                    except Exception as nginx_error:
                        _logger.warning(f"[Background] Could not create waiting container: {nginx_error}")
                    
                    _logger.info(f"[Background] Database and credentials ready for {subdomain}")
                    _logger.info(f"[Background] Waiting page active, Odoo will start after approval")
                    
                except Exception as e:
                    _logger.error(f"[Background] Provisioning failed for {subdomain}: {e}", exc_info=True)
                    # Update client record with error status
                    try:
                        with request.env.cr.savepoint():
                            request.env['saas.client'].sudo().search([
                                ('subdomain', '=', subdomain)
                            ]).write({
                                'notes': f"Provisioning error: {str(e)}\n\nPlease contact support."
                            })
                            request.env.cr.commit()
                    except:
                        pass
            
            # Start background provisioning
            try:
                thread = threading.Thread(target=provision_tenant, daemon=True)
                thread.start()
                _logger.info(f"Background provisioning thread started for {subdomain}")
            except Exception as thread_error:
                _logger.error(f"Failed to start background thread: {thread_error}", exc_info=True)
                # Continue anyway - client is created

            # Auto-approve for localhost mode after database is ready
            config = request.env['saas.configuration'].sudo().get_config()
            if config.deployment_mode == 'localhost':
                def auto_approve_tenant():
                    """Auto-approve tenant after database is ready"""
                    import time
                    max_retries = 30  # Wait up to 30 seconds
                    for i in range(max_retries):
                        time.sleep(1)
                        try:
                            # Check if database exists
                            conn = psycopg2.connect(
                                host='db', port=5432, database='postgres',
                                user='odoo', password='248413'
                            )
                            cursor = conn.cursor()
                            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
                            if cursor.fetchone():
                                cursor.close()
                                conn.close()
                                
                                # Check if admin user exists
                                tenant_conn = psycopg2.connect(
                                    host='db', port=5432, database=db_name,
                                    user='odoo', password='248413'
                                )
                                tenant_cursor = tenant_conn.cursor()
                                tenant_cursor.execute("SELECT 1 FROM res_users WHERE login = %s", (email,))
                                if tenant_cursor.fetchone():
                                    tenant_cursor.close()
                                    tenant_conn.close()
                                    
                                    # Database and user ready, approve tenant
                                    with request.env.cr.savepoint():
                                        client_to_approve = request.env['saas.client'].sudo().browse(client.id)
                                        client_to_approve.action_approve()
                                        request.env.cr.commit()
                                    _logger.info(f"✅ Auto-approved tenant {subdomain} for localhost mode")
                                    return
                                tenant_cursor.close()
                                tenant_conn.close()
                            else:
                                cursor.close()
                                conn.close()
                        except Exception as e:
                            if i == max_retries - 1:
                                _logger.warning(f"Auto-approval timeout for {subdomain}: {e}")
                            continue
                
                # Start auto-approval in separate thread
                import threading
                auto_thread = threading.Thread(target=auto_approve_tenant, daemon=True)
                auto_thread.start()
                _logger.info(f"Started auto-approval thread for {subdomain}")

            # Use werkzeug redirect with 303 See Other for POST-redirect-GET pattern
            from werkzeug.utils import redirect
            return redirect(f'/saas/signup/success?client_id={client.id}', code=303)

        except docker.errors.APIError as e:
            error_msg = f'Docker error: {str(e)}'
            _logger.error(error_msg, exc_info=True)
            # Still redirect to success page if client was created
            if 'client' in locals() and client:
                _logger.warning(f"Docker error but client created, redirecting to success for {client.id}")
                from werkzeug.utils import redirect
                return redirect(f'/saas/signup/success?client_id={client.id}', code=303)
            return request.redirect(f'/saas/signup?error=System error. Please contact support.')
        except psycopg2.Error as e:
            error_msg = f'Database error: {str(e)}'
            _logger.error(error_msg, exc_info=True)
            # Still redirect to success page if client was created
            if 'client' in locals() and client:
                _logger.warning(f"Database error but client created, redirecting to success for {client.id}")
                from werkzeug.utils import redirect
                return redirect(f'/saas/signup/success?client_id={client.id}', code=303)
            return request.redirect(f'/saas/signup?error=System error. Please contact support.')
        except Exception as e:
            error_msg = f'Signup failed: {str(e)}'
            _logger.error(error_msg, exc_info=True)
            # Still redirect to success page if client was created
            if 'client' in locals() and client:
                _logger.warning(f"General error but client created, redirecting to success for {client.id}")
                from werkzeug.utils import redirect
                return redirect(f'/saas/signup/success?client_id={client.id}', code=303)
            return request.redirect(f'/saas/signup?error=An error occurred. Please try again.')

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

    @http.route('/saas/check-subdomain', type='json', auth='public', methods=['POST'])
    def check_subdomain(self, subdomain):
        """AJAX endpoint to check subdomain availability"""
        if not subdomain:
            return {'available': False, 'message': 'Subdomain is required'}
        
        # Clean subdomain
        subdomain = re.sub(r'[^a-z0-9]', '', subdomain.lower())
        
        if not subdomain or len(subdomain) < 3:
            return {'available': False, 'message': 'Subdomain must be at least 3 characters'}
        
        # Check if subdomain already exists
        existing = request.env['saas.client'].sudo().search([
            ('subdomain', '=', subdomain)
        ], limit=1)
        
        if existing:
            return {'available': False, 'message': f'Subdomain "{subdomain}" is already taken'}
        
        return {'available': True, 'message': 'Subdomain is available', 'subdomain': subdomain}

    @http.route('/saas/check-port', type='jsonrpc', auth='public', methods=['POST'])
    def check_port(self, port):
        """AJAX endpoint to check port availability"""
        if not port:
            return {'available': False, 'message': 'Port is required'}

        try:
            port = int(port)
            if port < 8081 or port > 65535:
                return {'available': False, 'message': 'Port must be between 8081 and 65535'}

            # Check availability
            existing = request.env['saas.client'].sudo().search([
                ('port', '=', port)
            ], limit=1)

            if existing:
                return {'available': False, 'message': f'Port {port} is already taken'}

            return {'available': True, 'message': f'Port {port} is available!'}

        except ValueError:
            return {'available': False, 'message': 'Port must be a valid number'}
