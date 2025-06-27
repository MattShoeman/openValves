#!/bin/bash

# Enable error checking and logging
set -e
exec > >(tee -a /var/log/irrigation-deploy.log) 2>&1
echo "=== Irrigation System Deployment Starting at $(date) ==="

# ==============================================
# SD CARD OPTIMIZATIONS (NEW)
# ==============================================

echo "Configuring SD card optimizations..."

# 1. Move logs to RAM (tmpfs)
echo "Setting up RAM disk for logs..."
sudo mkdir -p /var/log/irrigation
sudo chown $(whoami):$(whoami) /var/log/irrigation
if ! grep -q "irrigation_logs" /etc/fstab; then
    echo "tmpfs    /var/log/irrigation    tmpfs    defaults,noatime,nosuid,size=10m    0    0" | sudo tee -a /etc/fstab
fi
sudo mount /var/log/irrigation || true

# 2. Disable atime updates system-wide
echo "Disabling atime updates..."
sudo sed -i 's/defaults/defaults,noatime/g' /etc/fstab
sudo mount -o remount /

# 3. Install log2ram for system logs (better than manual tmpfs)
echo "Installing log2ram for system logs..."
if ! command -v log2ram &> /dev/null; then
    curl -Lo log2ram.tar.gz https://github.com/azlux/log2ram/archive/master.tar.gz
    tar xf log2ram.tar.gz
    cd log2ram-master
    chmod +x install.sh
    sudo ./install.sh
    cd ..
    rm -rf log2ram-master log2ram.tar.gz
    sudo systemctl restart log2ram
fi

# 4. Reduce swappiness
echo "Reducing swap usage..."
if ! grep -q "vm.swappiness" /etc/sysctl.conf; then
    echo "vm.swappiness=5" | sudo tee -a /etc/sysctl.conf
    sudo sysctl -p
fi

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
    sqlite3 \
    || { echo "ERROR: Failed to install dependencies"; exit 1; }

# ==============================================
# REPOSITORY SETUP
# ==============================================

echo "Setting up repository..."
IRRIGATION_DIR="/home/$(whoami)/openValves"
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
# DATABASE OPTIMIZATIONS (NEW)
# ==============================================

echo "Configuring database optimizations..."
DB_FILE="$IRRIGATION_DIR/irrigation.db"

# Enable WAL mode and other SQLite optimizations
if [ -f "$DB_FILE" ]; then
    echo "Optimizing existing database..."
    sqlite3 "$DB_FILE" "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA cache_size=-4000;"
else
    echo "Creating new optimized database..."
    touch "$DB_FILE"
    sqlite3 "$DB_FILE" "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA cache_size=-4000;"
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
User=$(whoami)
WorkingDirectory=$IRRIGATION_DIR
Environment="PATH=$IRRIGATION_DIR/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="DISPLAY=:0"
Environment="XAUTHORITY=/home/$(whoami)/.Xauthority"
ExecStart=$IRRIGATION_DIR/venv/bin/python $IRRIGATION_DIR/app.py
Restart=always
RestartSec=10s
# Log to RAM disk
StandardOutput=file:/var/log/irrigation/service.log
StandardError=file:/var/log/irrigation/error.log

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
# FINAL OUTPUT
# ==============================================

echo "=== Deployment Complete at $(date) ==="
echo "System information:"
echo "Hostname: $(hostname)"
echo "IP Addresses: $(hostname -I)"
echo "Service status: $(systemctl is-active irrigation.service)"
echo "SD Card optimizations applied:"
echo "1. Logs moved to RAM (tmpfs)"
echo "2. WAL mode enabled for SQLite"
echo "3. noatime enabled system-wide"
echo "4. Reduced swappiness (vm.swappiness=5)"
echo ""
echo "Access the system at:"
echo "http://$(hostname -I | cut -d' ' -f1):8050"

exit 0
