#!/bin/bash
# SSL Certificate Auto-Renewal Script
# Run via cron: 0 0,12 * * * /opt/saas/scripts/renew_ssl.sh

LOG_FILE="/var/log/saas/ssl_renewal.log"
mkdir -p /var/log/saas

echo "$(date): Starting SSL renewal check..." >> $LOG_FILE

# Attempt renewal
certbot renew --quiet --deploy-hook "systemctl reload nginx" >> $LOG_FILE 2>&1

if [ $? -eq 0 ]; then
    echo "$(date): SSL renewal check completed successfully" >> $LOG_FILE
else
    echo "$(date): SSL renewal check failed" >> $LOG_FILE
    # Optional: Send alert email
    # echo "SSL renewal failed" | mail -s "SaaS SSL Alert" admin@yourdomain.com
fi
