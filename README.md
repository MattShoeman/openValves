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
# Copy the deploy.sh script from the repo onto a freshly installed raspberry pi.  This was tested with the Raspberry Pi4 using Raspberry Pi OS Lite (Bookworm and 64-bit)
# Suggested copying it into /home/user/  ,where user is the name of the user.  This creates some absolute directory references that would need to be updated if the user is names something else.

# Simple command to update the pi, install apts with apt-get, install python packages with pip, clone the repo, and create systemd services.
bash deploy.sh

✅ Success: Open a web browser and view the private IP address of the raspberry pi.

❌ Debug: Fix it

```
# :bulb: What's Next?
- Hardware shield
- Web dashboard (Django-based monitoring interface)
- Sub-zones for precise control of garden watering beds

