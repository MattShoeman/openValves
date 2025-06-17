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
- Solenoid valves (12V or 24V)  
- Waterproof enclosure  
- Power supply for valves
- [![Bill of Materials](https://docs.google.com/spreadsheets/d/14KFi8By2FL1IUUs16bJJF-sFFORRKznYOV_ILq-R138/edit?usp=sharing)]

## 🚀 Installation  
```bash  
# Clone repository  
git clone https://github.com/MattShoeman/openValves.git  
cd openValves
```


# Create virtual environment  
python3 -m venv venv  
source venv/bin/activate  

# Install dependencies  
pip install -r requirements.txt  

## 🔌 Autostart Setup (Recommended)

Run the dashboard automatically on boot using systemd:

    Create a service file:
```bash
sudo nano /etc/systemd/system/smart_irrigation.service  
```

Paste the following (adjust paths if needed):
```ini
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
```

Enable the service:
```bash
sudo systemctl daemon-reload  
sudo systemctl enable smart_irrigation.service  
sudo systemctl start smart_irrigation.service  
```

Verify it's running:
```bash

sudo systemctl status smart_irrigation.service  
```
    ✅ Success: Output shows active (running).

    ❌ Debug: Check logs with journalctl -u smart_irrigation.service -f.
