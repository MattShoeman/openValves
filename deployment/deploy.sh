#!/bin/bash

# Enable error checking and logging
set -e
exec > >(tee -a /var/log/irrigation-deploy.log) 2>&1
echo "=== Irrigation System Deployment Starting at $(date) ==="

# ==============================================
# DEPENDENCY INSTALLATION
# ==============================================

echo "Updating package lists..."
sudo apt-get update || { echo "ERROR: Failed to update package lists"; exit 1; }

echo "Installing system dependencies..."
sudo apt-get install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    git \
    chromium-chromedriver \
    || { echo "ERROR: Failed to install dependencies"; exit 1; }

# ==============================================
# REPOSITORY SETUP
# ==============================================

echo "Setting up repository..."
IRRIGATION_DIR="/home/user/openValves"
if [ ! -d "$IRRIGATION_DIR" ]; then
    echo "Cloning repository..."
    git clone https://github.com/MattShoeman/openValves.git "$IRRIGATION_DIR" \
        || { echo "ERROR: Failed to clone repository"; exit 1; }
    cd "$IRRIGATION_DIR"
    git checkout DashInterface || { echo "WARNING: Failed to checkout DashInterface branch"; }
else
    echo "Repository already exists at $IRRIGATION_DIR"
    cd "$IRRIGATION_DIR"
    git pull || { echo "WARNING: Failed to pull latest changes"; }
fi

# ==============================================
# PYTHON ENVIRONMENT SETUP
# ==============================================

echo "Creating Python virtual environment..."
python3 -m venv "$IRRIGATION_DIR/venv" \
    || { echo "ERROR: Failed to create virtual environment"; exit 1; }

echo "Installing Python dependencies..."
source "$IRRIGATION_DIR/venv/bin/activate"
pip install --upgrade pip \
    || { echo "ERROR: Failed to upgrade pip"; exit 1; }

pip install -r "$IRRIGATION_DIR/requirements.txt" \
    || { echo "ERROR: Failed to install Python requirements"; exit 1; }

# ==============================================
# SYSTEMD SERVICE SETUP WITH DEBUGGING
# ==============================================

echo "Configuring irrigation service..."
SERVICE_FILE="/etc/systemd/system/irrigation.service"
sudo tee "$SERVICE_FILE" > /dev/null <<EOF
[Unit]
Description=Smart Irrigation System
After=network.target
StartLimitIntervalSec=500
StartLimitBurst=5

[Service]
User=user
WorkingDirectory=$IRRIGATION_DIR
Environment="PATH=$IRRIGATION_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="DISPLAY=:0"
Environment="XAUTHORITY=/home/user/.Xauthority"
ExecStart=$IRRIGATION_DIR/venv/bin/python $IRRIGATION_DIR/app.py
Restart=always
RestartSec=10s

[Install]
WantedBy=multi-user.target
EOF

echo "Reloading systemd..."
sudo systemctl daemon-reload || { echo "ERROR: Failed to reload systemd"; exit 1; }

echo "Enabling service..."
sudo systemctl enable irrigation.service || { echo "ERROR: Failed to enable service"; exit 1; }

echo "Starting service..."
sudo systemctl start irrigation.service || { echo "ERROR: Failed to start service"; exit 1; }

# ==============================================
# SERVICE VERIFICATION
# ==============================================

echo "Checking service status..."
sleep 3  # Give the service time to start
SERVICE_STATUS=$(systemctl is-active irrigation.service)

if [ "$SERVICE_STATUS" != "active" ]; then
    echo "WARNING: Service is not running. Checking logs..."
    journalctl -u irrigation.service -b --no-pager | tail -20
    echo "Attempting to manually start the application for debugging..."
    cd "$IRRIGATION_DIR"
    $IRRIGATION_DIR/venv/bin/python app.py || { echo "ERROR: Manual start failed"; exit 1; }
else
    echo "Service is running successfully!"
fi

# ==============================================
# FIREWALL CONFIGURATION (OPTIONAL)
# ==============================================

echo "Configuring firewall..."
if command -v ufw &> /dev/null; then
    sudo ufw allow 8050/tcp || echo "WARNING: Failed to configure firewall"
else
    echo "ufw not installed, skipping firewall configuration"
fi

# ==============================================
# FINAL OUTPUT
# ==============================================

echo "=== Deployment Complete at $(date) ==="
echo "System information:"
echo "Hostname: $(hostname)"
echo "IP Addresses: $(hostname -I)"
echo "Service status: $(systemctl is-active irrigation.service)"
echo "Access the system at:"
echo "http://$(hostname -I | cut -d' ' -f1):8050"
echo "or http://openValves.local:8050"

echo "Debugging tips:"
echo "1. View service logs: journalctl -u irrigation.service -f"
echo "2. Test manually: cd $IRRIGATION_DIR && venv/bin/python app.py"
echo "3. Check network: ping $(hostname -I | cut -d' ' -f1)"

exit 0
