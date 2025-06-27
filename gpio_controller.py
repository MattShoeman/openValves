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
            if state:
                # For garden subzones (indices 1-4), activate master valve first
                if 1 <= valve_idx <= 4:
                    GPIO.output(GARDEN_MASTER_PIN, RELAY_ACTIVE)
                    time.sleep(0.5)  # Small delay for master valve to activate
            
                # Cancel existing timer if any
                if valve_idx in self.timers:
                    self.timers[valve_idx].cancel()
            
                # Turn valve ON
                GPIO.output(pin, RELAY_ACTIVE)
                self.valve_states[valve_idx] = True
            
                # Log watering event to database
                log_watering_event(
                    zone=VALVE_NAMES[valve_idx],
                    duration=duration,
                    weather=weather
                )
            
                # Start shutoff timer
                timer = threading.Timer(duration * 60, lambda: self.control_valve(valve_idx, False))
                timer.start()
                self.timers[valve_idx] = timer
            
                logging.info(f"Valve {VALVE_NAMES[valve_idx]} ON for {duration} minutes")
            else:
                # Turn valve OFF
                GPIO.output(pin, GPIO.HIGH if RELAY_ACTIVE == GPIO.LOW else GPIO.LOW)
                self.valve_states[valve_idx] = False
            
                # For garden subzones, turn off master valve if no other subzones are active
                if 1 <= valve_idx <= 4:
                    garden_active = any(self.valve_states[1:5])  # Check indices 1-4
                    if not garden_active:
                        GPIO.output(GARDEN_MASTER_PIN, GPIO.HIGH if RELAY_ACTIVE == GPIO.LOW else GPIO.LOW)
            
                # Cancel timer if exists
                if valve_idx in self.timers:
                    self.timers[valve_idx].cancel()
                    del self.timers[valve_idx]
            
                logging.info(f"Valve {VALVE_NAMES[valve_idx]} OFF")
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
