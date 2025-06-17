from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
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
        """Run the scheduled watering for today with sequential zone activation"""
        try:
            logging.info("Running scheduled watering")
            weather = self.weather_provider()
            schedules = self.load_schedule()
            
            today = datetime.now().strftime("%A")
            day_schedule = schedules['weekly'].get(today, {})
            
            # Apply weather adjustments
            for zone, duration in day_schedule.items():
                if weather['next_high_temp'] > 85:
                    day_schedule[zone] = int(duration * HOT_WEATHER_EXTRA)
            
            # Water each zone sequentially
            for zone_idx, zone_name in enumerate(VALVE_NAMES):
                if zone_name in day_schedule and day_schedule[zone_name] > 0:
                    duration = day_schedule[zone_name]
                    weather_condition = "Hot" if weather['next_high_temp'] > 85 else "Normal"
                    
                    logging.info(f"Starting {zone_name} for {duration} minutes")
                    self.valve_controller.control_valve(
                        zone_idx, 
                        True, 
                        duration,
                        weather_condition
                    )
                    
                    # Wait for this zone to complete
                    time.sleep(duration * 60 + 5)  # Convert minutes to seconds + buffer
                    
                    # Safety check
                    self.valve_controller.control_valve(zone_idx, False)
                    logging.info(f"Completed watering {zone_name}")
            
        except Exception as e:
            logging.error(f"Error in scheduled watering: {str(e)}")

    def schedule_daily_watering(self):
        """Schedule the daily watering job at 6 AM"""
        trigger = CronTrigger(hour=6, minute=0)
        self.scheduler.add_job(
            self.run_scheduled_watering,
            trigger=trigger,
            name="daily_watering"
        )
        logging.info("Scheduled daily watering at 6:00 AM")

    def shutdown(self):
        self.scheduler.shutdown()