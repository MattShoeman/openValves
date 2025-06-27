#!/bin/bash

# ==============================================
# SYSTEMD SERVICE SETUP
# ==============================================

echo "Configuring irrigation service..."
sudo cp ~/openValves/deployment/irrigation.service /etc/systemd/system/irrigation.service

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
