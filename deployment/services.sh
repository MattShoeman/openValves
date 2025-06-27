#!/bin/bash

# ==============================================
# SYSTEMD SERVICE SETUP
# ==============================================

echo "Configuring irrigation service..."
sudo cat > /etc/systemd/system/irrigation.service <<EOF
[Unit]
Description=Smart Irrigation System
After=network.target

[Service]
User=user
WorkingDirectory=/home/user/openValves
Environment="PATH=/home/user/openValves/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/home/user/openValves/venv/bin/python /home/user/openValves/app.py
Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable irrigation.service
sudo systemctl start irrigation.service

# ==============================================
# FINAL CHECKS
# ==============================================

echo "=== Deployment Complete ==="
echo "System information:"
echo "Hostname: $(hostname)"
echo "IP Addresses: $(hostname -I)"
echo "System should be accessible at:"
echo "http://$(hostname -I | cut -d' ' -f1)"
echo "or http://openValves.local"

exit 0
