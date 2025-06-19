from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import pytz
import time
import logging
import json
from pathlib import Path
from config import SCHEDULE_FILE, DEFAULT_SCHEDULE, HOT_WEATHER_EXTRA, VALVE_NAMES

class IrrigationScheduler:
    def __init__(self, valve_controller, weather_provider):
        self.valve_controller = valve_controller
        self.weather_provider = weather_provider
        self.scheduler = BackgroundScheduler(daemon=True)
        logging.info("Starting scheduler service...")  # Add this line
        self.scheduler.start()
        self.schedule_daily_watering()

    def load_schedule(self):
        """Load schedule from JSON file"""
        try:
            with open(SCHEDULE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading schedule: {str(e)}")
            return DEFAULT_SCHEDULE

    def run_scheduled_watering(self):
        """Improved sequential watering with clean transitions"""
        try:
            logging.info("Starting scheduled watering sequence")
            weather = self.weather_provider()
            schedules = self.load_schedule()
            
            today = datetime.now().strftime("%A")
            day_schedule = schedules['weekly'].get(today, {})
            
            # Apply weather adjustments
            adjusted_schedule = {
                zone: int(duration * HOT_WEATHER_EXTRA) 
                if weather['next_high_temp'] > 85 else duration
                for zone, duration in day_schedule.items()
            }
            
            # Water each zone sequentially with proper delays
            for zone_idx, zone_name in enumerate(VALVE_NAMES):
                if zone_name in adjusted_schedule and adjusted_schedule[zone_name] > 0:
                    duration = adjusted_schedule[zone_name]
                    weather_cond = "Hot" if weather['next_high_temp'] > 85 else "Normal"
                    
                    # Clean activation
                    self.valve_controller.control_valve(
                        zone_idx,
                        True,
                        duration,
                        weather_cond
                    )
                    
                    # Wait for duration plus buffer
                    time.sleep(duration * 60 + 2)  # Additional 2 second buffer
                    
                    # Explicit clean deactivation
                    self.valve_controller.control_valve(zone_idx, False)
                    
                    # Inter-zone delay
                    time.sleep(5)  # 5 second delay between zones
                    
            logging.info("Completed watering sequence")
            
        except Exception as e:
            logging.error(f"Watering sequence error: {str(e)}")
            self.valve_controller.emergency_stop()

    def schedule_daily_watering(self):
        """Schedule the daily watering job at 6 AM"""
        trigger = CronTrigger(hour=6, minute=0, timezone=pytz.timezone('America/Los_Angeles'))
        self.scheduler.add_job(
            self.run_scheduled_watering,
            trigger=trigger,
            name="daily_watering"
        )
        logging.info("Scheduled daily watering at 6:00 AM")

    def shutdown(self):
        self.scheduler.shutdown()