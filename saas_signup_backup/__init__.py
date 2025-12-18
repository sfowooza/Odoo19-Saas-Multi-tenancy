from . import models
from . import controllers

def post_init_hook(env):
    """Create default SaaS configuration and launch setup wizard after module installation"""
    # Create default configuration
    env['saas.configuration'].init_default_config()
    
    # Launch setup wizard for first-time configuration
    action = env.ref('saas_signup.action_saas_setup_wizard')
    return action.sudo().read()[0] if action else None