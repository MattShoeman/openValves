import RPi.GPIO as GPIO
from pathlib import Path
import json

# Hardware Configuration
VALVE_NAMES = ["Lawn-Patio", "Lawn-Fig", "Lawn-Apple", "Garden-Berries", "Garden-Flowers", "Garden-Beds", "Garden-Tomatoes"]
VALVE_PINS = [4, 17, 27, 25, 24, 23, 22]  # BCM numbering
GARDEN_MASTER_PIN = 18 
RELAY_ACTIVE = GPIO.LOW

# Water Usage Configuration
WATER_FLOW_RATES = {
    "Lawn-Fig": 3,             # gallons per minute
    "Lawn-Patio": 3,           # gallons per minute
    "Lawn-Apple": 3,           # gallons per minute
    "Garden-Berries": 1,  # gallons per minute
    "Garden-Flowers": 1,  # gallons per minute
    "Garden-Beds": 1,     # gallons per minute
    "Garden-Tomatoes": 1  # gallons per minute
}

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

WATER_RATES = {
    # Consolidated Fixed Costs (monthly) - Breakdown:
    "fixed_total": (
        22.57    # WATER BASE RATE - Basic water service charge
        + 23.35  # WASTEWATER BASE RATE - Sewer service charge
        + 11.20  # STORMWATER - Storm drainage system maintenance
        + 11.16  # STREET MAINTENANCE FEE - Road maintenance and repairs
        + 2.30   # SIDEWALK MAINTENANCE FEE - Sidewalk upkeep
        + 3.89   # TRANSIT OPERATIONS FEE - Public transportation funding
        + 1.15   # URBAN FORESTRY FEE - Tree planting and maintenance
        + 16.30  # POLICE PUBLIC SERVICE FEE - Police department funding
        + 17.34  # FIRE PUBLIC SERVICE FEE - Fire department funding
        + 0.96   # LOW-INCOME ASSISTANCE FEE - Utility assistance programs
    ),  # Total fixed monthly charges: $110.22
    
    # Variable Water Rates (per hcf - hundred cubic feet)
    "water_rate": 2.48,       # Level 1 base water rate per hcf
    "water_surcharge": 0.52,  # Additional water infrastructure surcharge per hcf
    "wastewater_rate": 3.72,  # Wastewater treatment charge per hcf
    
    # Tier Threshold
    "tier_threshold": 7,      # Units before conservation pricing kicks in (7 hcf)
    "tiered_rate": 2.86,      # Conservation rate after threshold (Level 2 rate)
    
    # Constants
    "gallons_per_hcf": 748,   # 1 hcf = 748 gallons (standard water measurement)
    "usage_period_days": 30   # Default billing period for calculations
}

# Ensure schedule file exists
if not Path(SCHEDULE_FILE).exists():
    with open(SCHEDULE_FILE, 'w') as f:
        json.dump(DEFAULT_SCHEDULE, f, indent=2)
