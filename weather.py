from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
import logging

def get_weather_forecast():
    """Get comprehensive weather updates from weather.gov"""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.binary_location = '/usr/bin/chromium-browser'
    service = Service('/usr/bin/chromedriver')
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        # Navigate to forecast page
        url = "https://forecast.weather.gov/MapClick.php?lat=44.591248&lon=-123.272118"
        driver.get(url)
        logging.info(f"Accessing weather data from: {url}")

        # Wait for elements to load
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "seven-day-forecast-body")))

        # Get current conditions
        current_temp = driver.find_element(
            By.CLASS_NAME, "myforecast-current-lrg").text.replace('°F', '')

        # Process extended forecast
        forecast_items = driver.find_elements(
            By.CSS_SELECTOR, "#seven-day-forecast-list li.forecast-tombstone")

        processed_forecast = []
        for item in forecast_items:
            try:
                period = item.find_element(By.CLASS_NAME, "period-name").text
                temp = item.find_element(By.CLASS_NAME, "temp").text
                desc = item.find_element(By.CLASS_NAME, "short-desc").text
                
                # Extract high temp if available
                is_high = 'High' in temp
                temp_value = int(temp.split()[1].replace('°F', '')) if is_high else None
                
                processed_forecast.append({
                    'period': period,
                    'temperature': temp,
                    'temp_value': temp_value,
                    'is_high': is_high,
                    'description': desc
                })
            except NoSuchElementException:
                continue

        # Find next high temperature
        next_high = next((f for f in processed_forecast if f['is_high']), None)
        next_high_temp = next_high['temp_value'] if next_high else 75

        return {
            'current_temp': current_temp,
            'next_high_temp': next_high_temp,
            'forecast_data': processed_forecast
        }

    except Exception as e:
        logging.error(f"Weather scraping error: {str(e)}")
        return {
            'current_temp': 'N/A',
            'next_high_temp': 75,
            'forecast_data': [],
            'error': str(e)
        }
    finally:
        driver.quit()