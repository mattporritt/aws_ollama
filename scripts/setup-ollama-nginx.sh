#!/bin/bash

# ==============================================================================
#
# This file is part of aws_ollama.
#
# aws_ollama is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# aws_ollama is distributed WITHOUT ANY WARRANTY:
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software. If not, see <http://www.gnu.org/licenses/>.
# ==============================================================================

# ==============================================================================
#
# @author Matthew Porritt
# @copyright  2024 onwards Matthew Porritt (matt.porritt@moodle.com)
# @license    http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
# ==============================================================================

# Accept SUBDOMAIN and HOSTED_ZONE as arguments
SUBDOMAIN=$1
HOSTED_ZONE=$2
BASIC_AUTH_USER=$3
BASIC_AUTH_PASS=$4

# Ensure the arguments are provided
if [ -z "$SUBDOMAIN" ] || [ -z "$HOSTED_ZONE" ] || [ -z "$BASIC_AUTH_USER" ] || [ -z "$BASIC_AUTH_PASS" ]; then
    echo "Usage: $0 SUBDOMAIN HOSTED_ZONE BASIC_AUTH_USER BASIC_AUTH_PASS"
    exit 1
fi

# Update system and install necessary packages
echo "Starting step system update" >> /var/log/user-data.log
apt update -y
apt install -y nginx apache2-utils

# Install Ollama
echo "Starting step install Ollama" >> /var/log/user-data.log
curl -fsSL https://ollama.com/install.sh | sh

# Install cerbot
echo "Starting step Install Certbot" >> /var/log/user-data.log
apt remove -y certbot
apt install -y python3 python3-venv libaugeas0 python3-certbot-nginx
python3 -m venv /opt/certbot/
/opt/certbot/bin/pip install --upgrade pip
/opt/certbot/bin/pip install certbot
rm -f /usr/bin/certbot
ln -s /opt/certbot/bin/certbot /usr/bin/certbot

# Stop Nginx to free up port 80
echo "Starting step stop Nginx" >> /var/log/user-data.log
systemctl stop nginx

# Set up SSL certificates using Certbot
echo "Starting step creating certificate" >> /var/log/user-data.log
certbot certonly --standalone --non-interactive --agree-tos --email admin@${HOSTED_ZONE} -d ${SUBDOMAIN}.${HOSTED_ZONE}

# Configure Nginx as a reverse proxy for Ollama
echo "Starting step configure Nginx" >> /var/log/user-data.log
cat <<EOF > /etc/nginx/sites-available/ollama
server {
    listen 80;
    server_name ${SUBDOMAIN}.${HOSTED_ZONE};

    # Redirect HTTP to HTTPS
    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name ${SUBDOMAIN}.${HOSTED_ZONE};

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/${SUBDOMAIN}.${HOSTED_ZONE}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${SUBDOMAIN}.${HOSTED_ZONE}/privkey.pem;

    # Basic Authentication
    auth_basic "Restricted Content";
    auth_basic_user_file /etc/nginx/.htpasswd;

    location / {
        proxy_pass http://localhost:11434;  # Replace with Ollama's port
        proxy_set_header Host localhost:11434;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable the Nginx configuration
echo "Starting step copy nginx configuration" >> /var/log/user-data.log
ln -s /etc/nginx/sites-available/ollama /etc/nginx/sites-enabled/
rm /etc/nginx/sites-enabled/default

# Create a user for basic authentication (replace 'admin' with your preferred username)
echo "Starting step create basic auth" >> /var/log/user-data.log
htpasswd -cb /etc/nginx/.htpasswd ${BASIC_AUTH_USER} ${BASIC_AUTH_PASS}

# Restart Nginx to apply changes
echo "Starting step restart nginx" >> /var/log/user-data.log
systemctl restart nginx

# Output Ollama status (optional)
echo "Starting step restart olama" >> /var/log/user-data.log
systemctl restart ollama
systemctl status ollama

# Install Ollama models
echo "Starting step install models" >> /var/log/user-data.log
ollama pull mistral
ollama pull llama3.1:8b
