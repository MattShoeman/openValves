#!/usr/bin/env python3

import RPi.GPIO as GPIO
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import logging

def setup_logging():
    """Configure logging for the script"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

# Relay GPIO Pins (BCM numbering)
RELAY_PINS = [17, 18, 27, 22]  # Update these to match your wiring
ZONE_NAMES = ["Patio", "Flowers", "Fig", "Apple"]

# Weather thresholds (adjust based on your needs)
RAIN_THRESHOLD = 0.1  # Inches of rain to skip watering
HOT_WEATHER_EXTRA = 1.5  # Multiplier for watering when >85°F

def setup_relays():
    GPIO.setmode(GPIO.BCM)
    for pin in RELAY_PINS:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.HIGH)  # Relays OFF initially

def water_zone(zone_idx, duration_min):
    print(f"Watering {ZONE_NAMES[zone_idx]} for {duration_min} minutes")
    GPIO.output(RELAY_PINS[zone_idx], GPIO.LOW)  # Relay ON
    time.sleep(duration_min * 60)
    GPIO.output(RELAY_PINS[zone_idx], GPIO.HIGH)  # Relay OFF

def get_weather_forecast():
    """Get comprehensive weather updates from weather.gov"""
    setup_logging()
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.binary_location = '/usr/bin/chromium-browser'
    service = Service('/usr/bin/chromedriver')
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        # Navigate to the forecast page
        url = "https://forecast.weather.gov/MapClick.php?lat=44.591248&lon=-123.272118"
        driver.get(url)
        logging.info(f"Accessing weather data from: {url}")

        # Wait for critical elements to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "seven-day-forecast-body")))

        # Get current conditions
        current_temp = driver.find_element(
            By.CLASS_NAME, "myforecast-current-lrg").text
        print(f"Current temp: {current_temp}")

        # Get extended forecast
        forecast_items = driver.find_elements(
            By.CSS_SELECTOR, "#seven-day-forecast-list li.forecast-tombstone")

        # DEBUG: Print raw HTML of each forecast item
        #print(f"\nFound {len(forecast_items)} forecast items:")
        #for i, item in enumerate(forecast_items, 1):
        #    print(f"\n--- Item {i} ---")
        #    print(item.get_attribute('outerHTML'))  # This prints the full HTML element
        #    print("----------------")

        forecast_data = []
        for item in forecast_items:
            try:
                temp_element = item.find_element(By.CLASS_NAME, "temp")
                period = item.find_element(By.CLASS_NAME, "period-name").text
                temp = temp_element.text
                desc = item.find_element(By.CLASS_NAME, "short-desc").text
                
                #print(f"Found forecast: {period} - {temp} - {desc}")  # Debug print
                
                forecast_data.append({
                    'period': period,
                    'temperature': temp,
                    'is_high': 'High' in temp,
                    'description': desc
                })
            except NoSuchElementException as e:
                logging.warning(f"Missing element in forecast item: {str(e)}")
                continue

        # Check for precipitation
        detailed_forecast = driver.find_element(
            By.ID, "detailed-forecast-body").text.lower()
        rain_expected = any(word in detailed_forecast 
                          for word in ["rain", "shower", "precip"])

        # Find next high temp with fallback
        next_high = next((f for f in forecast_data if f['is_high']), None)
        next_high_temp = float(next_high['temperature'].split()[1].replace('°F', '')) if next_high else 75

        return {
            'next_high_temp': next_high_temp,
            'rain_expected': rain_expected,
            'forecast_data': forecast_data  # Include full forecast data for debugging
        }

    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        return {
            'next_high_temp': 75,
            'rain_expected': False,
            'forecast_data': [],
            'error': str(e)
        }
    finally:
        driver.quit()

def calculate_watering_schedule(weather):
    """Determine watering duration for each zone based on weather"""
    #"Patio", "Flowers", "Fig", "Apple"]
    base_times = [10, 20, 10, 20]  # Base minutes per zone
    
    # Adjust for weather conditions
    if weather['rain_expected']:
        print("Rain expected - reducing watering time")
        return [t * 0.5 for t in base_times]  # Reduce by 50%
    
    if weather['next_high_temp'] > 85:
        print(f"Hot weather forecast ({weather['next_high_temp']}°F) - increasing watering time")
        return [t * HOT_WEATHER_EXTRA for t in base_times]
    
    return base_times

def main():
    setup_relays()
    
    try:
        print("Checking weather forecast...")
        weather = get_weather_forecast()
        print(f"Next forecasted high: {weather['next_high_temp']}°F")
        print(f"Rain expected: {'Yes' if weather['rain_expected'] else 'No'}")
        
        schedule = calculate_watering_schedule(weather)
        
        # Water each zone sequentially
        for zone, duration in enumerate(schedule):
            if duration > 0:  # Skip zones with 0 duration
                water_zone(zone, duration)
                time.sleep(15)  # Short break between zones
        
        print("Watering complete!")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    # Run at 6 AM daily (use cron job for scheduling)
    if 5 <= datetime.now().hour < 10:  # Only run between 5-10 AM
        main()
    else:
        print("Not the right time for watering (6-10 AM only)")
