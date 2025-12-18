"""
Nginx Manager Utility for SaaS Multi-Tenancy
Dynamically creates and manages Nginx configurations for tenant subdomains
"""

import os
import subprocess
import logging
import docker

_logger = logging.getLogger(__name__)

# Import Odoo environment for accessing SaaS config
try:
    from odoo import api, environment
    from .models.saas_config import SaasConfiguration
except ImportError:
    # Fallback for non-Odoo usage
    SaasConfiguration = None


class NginxManager:
    """Utility class to manage Nginx configurations for SaaS tenants"""
    
    # Auto-detect nginx configuration paths
    SYSTEM_NGINX_AVAILABLE = "/etc/nginx/sites-available"
    SYSTEM_NGINX_ENABLED = "/etc/nginx/sites-enabled"
    DOCKER_NGINX_CONF_DIR = "/etc/nginx/conf.d"
    
    @classmethod
    def _detect_nginx_type(cls):
        """Detect if using system nginx or docker nginx"""
        # Check for our project's docker nginx config directory first
        project_docker_dir = "/home/avodahdevops/Desktop/Odoo_Projects/Odoo19/nginx/conf.d"
        if os.path.exists(project_docker_dir):
            return 'docker'
        elif os.path.exists(cls.DOCKER_NGINX_CONF_DIR):
            return 'docker'
        elif os.path.exists(cls.SYSTEM_NGINX_ENABLED):
            return 'system'
        else:
            # Fallback: assume docker for SaaS platform
            return 'docker'
    
    @classmethod
    def _get_saas_config(cls):
        """Get SaaS configuration for nginx path"""
        if SaasConfiguration is None:
            return None

        try:
            # Try to get current Odoo environment
            with environment.manage():
                config = SaasConfiguration.search([('active', '=', True)], limit=1)
                if config:
                    return config[0]
        except Exception as e:
            _logger.warning(f"Could not access SaaS config: {e}")

        return None

    @classmethod
    def _get_config_dir(cls):
        """Get appropriate nginx config directory"""
        # First try to get from SaaS configuration
        saas_config = cls._get_saas_config()
        if saas_config and saas_config.nginx_config_path:
            return saas_config.nginx_config_path

        # Fallback to detection logic
        nginx_type = cls._detect_nginx_type()
        if nginx_type == 'system':
            return cls.SYSTEM_NGINX_ENABLED
        else:
            # Use our project's nginx config directory
            return "/home/avodahdevops/Desktop/Odoo_Projects/Odoo19/nginx/conf.d"
    
    @classmethod
    def create_tenant_config(cls, subdomain, odoo_port, longpolling_port=None, main_domain='avodahconsult.info'):
        """
        Create Nginx config for a tenant
        
        Args:
            subdomain: Tenant subdomain (e.g., 'acme')
            odoo_port: Main Odoo HTTP port (e.g., 8101)
            longpolling_port: Longpolling port (defaults to odoo_port + 1000)
            main_domain: Main domain for subdomains (e.g., 'avodahconsult.info')
        
        Returns:
            bool: True if successful
        """
        if not longpolling_port:
            longpolling_port = odoo_port + 1000
        
        nginx_type = cls._detect_nginx_type()
        config_content = cls._generate_config(subdomain, odoo_port, longpolling_port, main_domain, nginx_type)
        
        config_dir = cls._get_config_dir()
        config_file = f"{config_dir}/{subdomain}.conf"
        
        try:
            # Write config
            with open(config_file, 'w') as f:
                f.write(config_content)
            
            _logger.info(f"✅ Nginx config written to {config_file}")
            
            # Test and reload Nginx container
            cls._test_and_reload()
            
            _logger.info(f"✅ Nginx config created for {subdomain}.{main_domain} → port {odoo_port}")
            return True
            
        except Exception as e:
            _logger.error(f"❌ Failed to create Nginx config for {subdomain}: {e}")
            # Cleanup on failure
            if os.path.exists(config_file):
                os.remove(config_file)
            raise
    
    @classmethod
    def remove_tenant_config(cls, subdomain):
        """
        Remove Nginx config for a tenant
        
        Args:
            subdomain: Tenant subdomain
        
        Returns:
            bool: True if successful
        """
        config_dir = cls._get_config_dir()
        # Try both naming conventions
        config_files = [
            f"{config_dir}/{subdomain}.conf",
            f"{config_dir}/{subdomain}.*.conf"
        ]
        
        try:
            removed = False
            import glob
            for pattern in config_files:
                for config_file in glob.glob(pattern):
                    if os.path.exists(config_file):
                        os.remove(config_file)
                        removed = True
                        _logger.info(f"✅ Removed config: {config_file}")
            
            if removed:
                cls._reload()
                _logger.info(f"✅ Nginx config removed for {subdomain}")
            return removed
            
        except Exception as e:
            _logger.error(f"❌ Failed to remove Nginx config for {subdomain}: {e}")
            return False
    
    @classmethod
    def update_tenant_config(cls, subdomain, odoo_port, longpolling_port=None):
        """
        Update existing tenant config (remove and recreate)
        
        Args:
            subdomain: Tenant subdomain
            odoo_port: New Odoo port
            longpolling_port: New longpolling port
        
        Returns:
            bool: True if successful
        """
        cls.remove_tenant_config(subdomain)
        return cls.create_tenant_config(subdomain, odoo_port, longpolling_port)
    
    @classmethod
    def _get_container_ip(cls, container_name):
        """Get the IP address of a Docker container on the odoo-network"""
        try:
            client = docker.from_env()
            container = client.containers.get(container_name)
            container.reload()  # Refresh container info

            # Get the network settings for odoo19_odoo-network
            networks = container.attrs.get('NetworkSettings', {}).get('Networks', {})
            for network_name, network_info in networks.items():
                if 'odoo-network' in network_name:
                    ip_address = network_info.get('IPAddress')
                    if ip_address:
                        _logger.info(f"🔍 Found IP for {container_name}: {ip_address} on {network_name}")
                        return ip_address

            _logger.warning(f"⚠️ Could not find odoo-network IP for {container_name}")
            return None

        except Exception as e:
            _logger.error(f"❌ Failed to get IP for {container_name}: {e}")
            return None

    @classmethod
    def _get_backend_host(cls, subdomain, odoo_port):
        """Get the best backend host for a tenant"""
        # Each tenant has their own external port mapping
        # Use host.docker.internal to access the host-mapped ports
        nginx_type = cls._detect_nginx_type()

        if nginx_type == 'system':
            # For system nginx, use localhost
            backend_host = '127.0.0.1'
        else:
            # For docker nginx, use host.docker.internal
            backend_host = 'host.docker.internal'

        return f"{backend_host}:{odoo_port}", f"{backend_host}:{odoo_port + 1000}"

    @classmethod
    def _generate_config(cls, subdomain, odoo_port, longpolling_port, main_domain='avodahconsult.info', nginx_type='system'):
        """Generate Nginx config content for system or docker nginx"""

        # Get the best backend hosts for this tenant
        odoo_backend, chat_backend = cls._get_backend_host(subdomain, odoo_port)

        return f"""# ==============================================
# SaaS Tenant Configuration
# ==============================================
# Tenant: {subdomain}
# Odoo Port: {odoo_port}
# Longpolling Port: {longpolling_port}
# Auto-generated by Avodah SaaS Platform
# ==============================================

upstream odoo_{subdomain} {{
    server {odoo_backend};
}}

upstream odoochat_{subdomain} {{
    server {chat_backend};
}}

# HTTP Server (no SSL for now)
server {{
    listen 80;
    server_name {subdomain}.{main_domain};
    
    # Security headers
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Proxy settings
    proxy_read_timeout 720s;
    proxy_connect_timeout 720s;
    proxy_send_timeout 720s;
    proxy_buffers 16 64k;
    proxy_buffer_size 128k;
    proxy_http_version 1.1;
    proxy_set_header Connection "";
    
    # Client upload size
    client_max_body_size 100M;
    client_body_buffer_size 128k;
    
    # Logging
    access_log /var/log/nginx/{subdomain}.access.log;
    error_log /var/log/nginx/{subdomain}.error.log warn;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss application/rss+xml font/truetype font/opentype application/vnd.ms-fontobject image/svg+xml;
    
    # Longpolling endpoint
    location /longpolling {{
        proxy_pass http://odoochat_{subdomain};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
    }}
    
    # Main Odoo application
    location / {{
        proxy_pass http://odoo_{subdomain};
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
        proxy_redirect off;
        
    }}
    
    # Static files caching
    location ~* /web/static/ {{
        proxy_pass http://odoo_{subdomain};
        proxy_cache_valid 200 90m;
        proxy_buffering on;
        expires 864000;
        add_header Cache-Control "public, immutable";
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $host;
    }}
    
    # Image caching
    location ~* \.(jpg|jpeg|png|gif|ico|svg|webp)$ {{
        proxy_pass http://odoo_{subdomain};
        expires 30d;
        add_header Cache-Control "public, immutable";
    }}
}}
"""
    
    @classmethod
    def _test_and_reload(cls):
        """Test Nginx config and reload - works for both system and docker nginx"""
        nginx_type = cls._detect_nginx_type()
        
        try:
            if nginx_type == 'system':
                # System nginx - use systemctl
                test_result = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
                if test_result.returncode != 0:
                    raise Exception(f"Nginx config test failed: {test_result.stderr}")
                
                reload_result = subprocess.run(['systemctl', 'reload', 'nginx'], capture_output=True, text=True)
                if reload_result.returncode == 0:
                    _logger.info("✅ System Nginx reloaded successfully")
                else:
                    _logger.warning(f"Nginx reload warning: {reload_result.stderr}")
            else:
                # Docker nginx
                import docker
                client = docker.from_env()
                
                nginx_containers = [c for c in client.containers.list() if 'nginx' in c.name.lower()]
                if not nginx_containers:
                    _logger.warning("No nginx container found, skipping reload")
                    return
                
                nginx_container = nginx_containers[0]
                
                result = nginx_container.exec_run('nginx -t')
                if result.exit_code != 0:
                    raise Exception(f"Nginx config test failed: {result.output.decode()}")
                
                reload_result = nginx_container.exec_run('nginx -s reload')
                if reload_result.exit_code == 0:
                    _logger.info("✅ Docker Nginx reloaded successfully")
                else:
                    _logger.warning(f"Nginx reload warning: {reload_result.output.decode()}")
                    
        except Exception as e:
            _logger.error(f"Failed to reload nginx: {e}")
            raise
    
    @classmethod
    def _reload(cls):
        """Reload Nginx to apply changes"""
        cls._test_and_reload()
    
    @classmethod
    def test_config(cls):
        """Test if current Nginx configuration is valid"""
        result = subprocess.run(
            ['nginx', '-t'], 
            capture_output=True, 
            text=True
        )
        return result.returncode == 0
    
    @classmethod
    def list_tenant_configs(cls):
        """List all SaaS tenant configurations"""
        configs = []
        config_dir = cls._get_config_dir()
        
        if not os.path.exists(config_dir):
            return configs
        
        for filename in os.listdir(config_dir):
            if filename.endswith('.conf') and filename not in ['default.conf', 'nginx.conf', 'default']:
                # Extract subdomain from filename
                subdomain = filename.split('.')[0]
                configs.append(subdomain)
        
        return configs
