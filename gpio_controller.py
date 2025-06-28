import RPi.GPIO as GPIO
import threading
from threading import Lock
from datetime import datetime
import time
import logging
from config import VALVE_NAMES, VALVE_PINS, RELAY_ACTIVE, GARDEN_MASTER_PIN
from database import log_watering_event, get_watering_history

class ValveController:
    def __init__(self):
        self.valve_states = [False] * len(VALVE_NAMES)
        self._setup_gpio()
        self.timers = {}
        # Removed the watering_history list since we're using SQLite now
        self.history_lock = Lock()  # Keep lock for thread safety with timers

    def _setup_gpio(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for pin in VALVE_PINS:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.HIGH if RELAY_ACTIVE == GPIO.LOW else GPIO.LOW)
        # Add master valve setup
        GPIO.setup(GARDEN_MASTER_PIN, GPIO.OUT)
        GPIO.output(GARDEN_MASTER_PIN, GPIO.HIGH if RELAY_ACTIVE == GPIO.LOW else GPIO.LOW)

    def control_valve(self, valve_idx, state, duration=10, weather="Normal"):
        try:
            pin = VALVE_PINS[valve_idx]
            zone_name = VALVE_NAMES[valve_idx]
            
            if state:
                # For ALL garden zones (names starting with "Garden-"), activate master valve first
                if zone_name.startswith("Garden-"):
                    GPIO.output(GARDEN_MASTER_PIN, RELAY_ACTIVE)
                    time.sleep(0.5)  # Small delay for master valve to activate
                
                # Cancel existing timer if any
                if valve_idx in self.timers:
                    self.timers[valve_idx].cancel()
                
                # Rest of the ON logic remains the same...
                GPIO.output(pin, RELAY_ACTIVE)
                self.valve_states[valve_idx] = True
                
                log_watering_event(
                    zone=zone_name,
                    duration=duration,
                    weather=weather
                )
                
                timer = threading.Timer(duration * 60, lambda: self.control_valve(valve_idx, False))
                timer.start()
                self.timers[valve_idx] = timer
                
                logging.info(f"Valve {zone_name} ON for {duration} minutes")
            else:
                # Turn valve OFF
                GPIO.output(pin, GPIO.HIGH if RELAY_ACTIVE == GPIO.LOW else GPIO.LOW)
                self.valve_states[valve_idx] = False
                
                # For garden zones, check if any others are active before turning off master
                if zone_name.startswith("Garden-"):
                    garden_active = any(self.valve_states[i] for i, name in enumerate(VALVE_NAMES) 
                                   if name.startswith("Garden-"))
                    if not garden_active:
                        GPIO.output(GARDEN_MASTER_PIN, GPIO.HIGH if RELAY_ACTIVE == GPIO.LOW else GPIO.LOW)
                
                # Cancel timer if exists
                if valve_idx in self.timers:
                    self.timers[valve_idx].cancel()
                    del self.timers[valve_idx]
                
                logging.info(f"Valve {zone_name} OFF")
        except Exception as e:
            logging.error(f"Error controlling valve {VALVE_NAMES[valve_idx]}: {str(e)}")
            raise

    def get_valve_states(self):
        return [GPIO.input(pin) == RELAY_ACTIVE for pin in VALVE_PINS]

    def get_watering_history(self):
        """Get watering history from database"""
        try:
            return get_watering_history()
        except Exception as e:
            logging.error(f"Error getting watering history: {str(e)}")
            return []

    def emergency_stop(self):
        for i in range(len(VALVE_NAMES)):
            self.control_valve(i, False)

    def cleanup(self):
        self.emergency_stop()
        GPIO.cleanup()
