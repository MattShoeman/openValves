import RPi.GPIO as GPIO
from pathlib import Path
import json

# Hardware Configuration
VALVE_NAMES = ["Patio", "Flowers", "Fig", "Apple"]
VALVE_PINS = [17, 18, 27, 22]  # BCM numbering
RELAY_ACTIVE = GPIO.LOW

# System Settings
SCHEDULE_FILE = "schedules.json"
HOT_WEATHER_EXTRA = 1.5  # Multiplier for watering when >85°F

# Default Schedule
DEFAULT_SCHEDULE = {
    "weekly": {
        "Sunday": {"Patio": 30, "Flowers": 15, "Fig": 20, "Apple": 25},
        "Monday": {"Patio": 20, "Flowers": 20, "Fig": 15, "Apple": 20},
        "Tuesday": {"Patio": 20, "Flowers": 15, "Fig": 20, "Apple": 25},
        "Wednesday": {"Patio": 25, "Flowers": 20, "Fig": 15, "Apple": 20},
        "Thursday": {"Patio": 20, "Flowers": 15, "Fig": 20, "Apple": 25},
        "Friday": {"Patio": 30, "Flowers": 20, "Fig": 15, "Apple": 20},
        "Saturday": {"Patio": 40, "Flowers": 25, "Fig": 30, "Apple": 40}
    },
    "special": {}
}

# Ensure schedule file exists
if not Path(SCHEDULE_FILE).exists():
    with open(SCHEDULE_FILE, 'w') as f:
        json.dump(DEFAULT_SCHEDULE, f, indent=2)