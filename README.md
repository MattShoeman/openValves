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

## 🚀 Installation
```bash
# Clone repository
git clone https://github.com/MattShoeman/openValves.git
cd openValves

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up cron job for automatic execution
(crontab -l 2>/dev/null; echo "0 6 * * Mon $(pwd)/run_irrigation.sh") | crontab -

```
# :bulb: What's Next?
- Design a hardware shield
- Switch the Webcrawling from www.weather.gov to https://openweathermap.org
- Watering lawn grass in Oregon requires 1" of water per week.  Sprinklers output 3 gallons per minute.  A 90 degree sprinkler should run for about an hour each week, to get deep penetration. Add some of these computations into the web interface to help determine proper duration and frequency of water.
- Web dashboard (Comparing Dash and Django monitoring interfaces)
- Use the interface to save a schedule as a JSON file.  The Cron will run the control script at 6 AM.
- Sub-zones for precise control of garden watering beds

