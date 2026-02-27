#!/bin/bash
set -e

# Create log directory
mkdir -p /var/log/app

# Set SSH password for admin user
SSH_PASSWORD="${AICP_ADMIN_PASSWORD:-changeme}"
echo "admin:${SSH_PASSWORD}" | chpasswd

# Generate SSH host keys if not present
if [ ! -f /etc/ssh/ssh_host_rsa_key ]; then
    ssh-keygen -A
fi

# Set SSH_ENABLED environment for supervisord
export SSH_ENABLED="${SSH_ENABLED:-true}"

# Ensure data directory permissions
chown -R admin:admin /data/results 2>/dev/null || true

echo "=== AICP Performance Testing Tool ==="
echo "Frontend: http://0.0.0.0:8080"
echo "API:      http://0.0.0.0:8081"
echo "SSH:      Port 22 (user: admin)"
echo "======================================"

exec "$@"
