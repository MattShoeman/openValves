#!/bin/bash

echo "Installing irrigation system dependencies..."
sudo apt-get update
sudo apt-get install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    git \
    chromium-chromedriver \
    || { echo "ERROR: Failed to install dependencies"; exit 1; }

echo "Cloning repository..."
IRRIGATION_DIR="/home/user/openValves"
if [ ! -d "$IRRIGATION_DIR" ]; then
    git clone https://github.com/MattShoeman/openValves.git "$IRRIGATION_DIR" \
        || { echo "ERROR: Failed to clone repository"; exit 1; }
    git checkout DashInterface
fi

echo "Setting up Python environment..."
python3 -m venv "$IRRIGATION_DIR/venv" \
    || { echo "ERROR: Failed to create virtual environment"; exit 1; }

source "$IRRIGATION_DIR/venv/bin/activate"
pip install --upgrade pip \
    || { echo "ERROR: Failed to upgrade pip"; exit 1; }

pip install -r "$IRRIGATION_DIR/requirements.txt" \
    || { echo "ERROR: Failed to install Python requirements"; exit 1; }

# ==============================================
# SYSTEMD SERVICE SETUP
# ==============================================

echo "Configuring irrigation service..."
sudo touch /etc/systemd/system/irrigation.service
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
