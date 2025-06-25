# openValves 🌧️🌱
**Smart Irrigation System for Raspberry Pi**  
Automated watering system that adjusts based on weather forecasts


[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## ✨ Features
- **Weather-adaptive watering** - Skips watering when rain is forecasted
- **Multi-zone control** - Manages 4 independent watering zones
- **Web dashboard** - Django-based monitoring interface
- **Scheduled execution** - Automatic 6 AM daily runs
- **Raspberry Pi GPIO** - Controls relay modules for valve operation

## 🛠️ Hardware Requirements
- Raspberry Pi (3/4/Zero recommended)
- 4-channel relay module
- Solenoid valves (24VAC)
- Waterproof enclosure
- Power supply for valves
- [Hardware Bill of Materials](https://docs.google.com/spreadsheets/d/14KFi8By2FL1IUUs16bJJF-sFFORRKznYOV_ILq-R138/edit?usp=sharing)

## 🚀 Installation
```bash
# Initial Updates
sudo apt-get update
sudo apt-get -y install git python3-dev python3-pip

# Clone repository
git clone https://github.com/MattShoeman/openValves.git
cd openValves
git checkout DashInterface

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
python3 app.py

✅ Success: Open a web browser and view the private IP address of the raspberry pi.

❌ Debug: Fix it
```

## How to make a daemon service for automatic operation and restart upon reboot
Paste the following (adjust paths if needed):

[Unit]
Description=Smart Irrigation Dashboard
After=network.target

[Service]
User=user
WorkingDirectory=/home/user/openValves
Environment="PATH=/home/user/openValves/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/home/user/openValves/venv/bin/python /home/user/openValves/app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target

Enable the service:

sudo systemctl daemon-reload  
sudo systemctl enable smart_irrigation.service  
sudo systemctl start smart_irrigation.service  

Verify it's running:

sudo systemctl status smart_irrigation.service  

✅ Success: Output shows active (running).

❌ Debug: Check logs with journalctl -u smart_irrigation.service -f.


```
# :bulb: What's Next?
- Hardware shield
- Web dashboard (Django-based monitoring interface)
- Sub-zones for precise control of garden watering beds

