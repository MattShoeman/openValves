import RPi.GPIO as GPIO
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    
    driver = webdriver.Chrome(options=options)
    try:
        driver.get("https://forecast.weather.gov/MapClick.php?lat=44.591248&lon=-123.272118")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "seven-day-forecast-body")))

        # Get forecasted high temperatures
        forecast_items = driver.find_elements(
            By.CSS_SELECTOR, "#seven-day-forecast-list .forecast-tombstone")
        
        # Find the next high temperature in the forecast
        next_high_temp = None
        for item in forecast_items:
            temp_element = item.find_element(By.CLASS_NAME, "temp")
            temp_text = temp_element.text
            if 'High' in temp_text:
                next_high_temp = float(temp_text.split()[1].replace('°F', ''))
                break
        
        # Check for precipitation in detailed forecast
        detailed_forecast = driver.find_element(
            By.ID, "detailed-forecast-body").text.lower()
        rain_today = any(word in detailed_forecast 
                        for word in ["rain", "shower", "precip"])
        
        if next_high_temp is None:
            print("Warning: No high temperature found in forecast")
            next_high_temp = 75  # Default temperature if none found
        
        return {
            'next_high_temp': next_high_temp,
            'rain_expected': rain_today
        }
    finally:
        driver.quit()

def calculate_watering_schedule(weather):
    """Determine watering duration for each zone based on weather"""
    base_times = [15, 45, 15, 25]  # Base minutes per zone
    
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
                time.sleep(60)  # Short break between zones
        
        print("Watering complete!")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    # Run at 6 AM daily (use cron job for scheduling)
    main()
    #if 6 <= datetime.now().hour < 10:  # Only run between 6-10 AM
    #    main()
    #else:
    #    print("Not the right time for watering (6-10 AM only)")