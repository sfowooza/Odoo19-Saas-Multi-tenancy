#!/bin/bash
echo "🚀 Installing SaaS module directly..."

# Change to the correct directory
cd /home/avodahdevops/Desktop/Odoo_Projects/Odoo19-Saas-Multi-tenancy

# Execute Odoo command to install the module
docker-compose exec odoo19 odoo -c /etc/odoo/odoo.conf -i saas_signup --stop-after-init

if [ $? -eq 0 ]; then
    echo "✅ SaaS module installation completed"
else
    echo "❌ SaaS module installation failed"
fi
