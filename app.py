import dash
from dash import dcc, html, Input, Output, State, dash_table, callback_context
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import logging
import threading
from threading import Lock
import RPi.GPIO as GPIO
from pathlib import Path
import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Initialize GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Valve configuration
VALVE_NAMES = ["Patio", "Flowers", "Fig", "Apple"]
VALVE_PINS = [17, 18, 27, 22]  # BCM numbering
RELAY_ACTIVE = GPIO.LOW  # Change to GPIO.HIGH if your relays activate on HIGH

# Weather thresholds
HOT_WEATHER_EXTRA = 1.5  # Multiplier for watering when >85°F

# Initialize all valves to OFF state
for pin in VALVE_PINS:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.HIGH if RELAY_ACTIVE == GPIO.LOW else GPIO.LOW)

# Track system state
valve_states = [False] * len(VALVE_NAMES)
watering_history = []
history_lock = Lock()
weather_data = {
    'next_high_temp': 75,
    'forecast_data': []
}

SCHEDULE_FILE = "schedules.json"
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

# Initialize scheduler
scheduler = BackgroundScheduler(daemon=True)
scheduler.start()

# Utility functions
def load_schedule():
    """Load schedule from JSON file"""
    try:
        with open(SCHEDULE_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error loading schedule: {str(e)}")
        return DEFAULT_SCHEDULE

def control_valve(valve_idx, state, duration_min=10):
    """Control a single valve with safety checks and timed shutoff"""
    try:
        pin = VALVE_PINS[valve_idx]
        if state:
            # Cancel any existing timer for this valve
            if hasattr(control_valve, f"timer_{valve_idx}"):
                old_timer = getattr(control_valve, f"timer_{valve_idx}")
                if old_timer and old_timer.is_alive():
                    old_timer.cancel()
            
            # Turn valve ON
            GPIO.output(pin, RELAY_ACTIVE)
            valve_states[valve_idx] = True
            
            # Log watering event
            with history_lock:
                weather_condition = "Hot" if weather_data['next_high_temp'] > 85 else "Normal"
                watering_history.append({
                    'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'zone': VALVE_NAMES[valve_idx],
                    'duration': duration_min,
                    'weather': weather_condition
                })
            
            # Start timer to turn off
            timer = threading.Timer(duration_min * 60, lambda: control_valve(valve_idx, False))
            timer.start()
            setattr(control_valve, f"timer_{valve_idx}", timer)
            
            logging.info(f"Valve {VALVE_NAMES[valve_idx]} ON for {duration_min} minutes")
        else:
            # Turn valve OFF
            GPIO.output(pin, GPIO.HIGH if RELAY_ACTIVE == GPIO.LOW else GPIO.LOW)
            valve_states[valve_idx] = False
            
            # Cancel any running timer
            if hasattr(control_valve, f"timer_{valve_idx}"):
                timer = getattr(control_valve, f"timer_{valve_idx}")
                if timer and timer.is_alive():
                    timer.cancel()
            
            logging.info(f"Valve {VALVE_NAMES[valve_idx]} OFF")
    except Exception as e:
        logging.error(f"Error controlling valve {VALVE_NAMES[valve_idx]}: {str(e)}")

def run_scheduled_watering():
    """Run the scheduled watering for today with sequential zone activation"""
    try:
        logging.info("Running scheduled watering")
        weather = get_weather_forecast()
        schedules = load_schedule()
        
        today = datetime.now().strftime("%A")
        day_schedule = schedules['weekly'].get(today, {})
        
        # Apply weather adjustments
        for zone, duration in day_schedule.items():
            if weather['next_high_temp'] > 85:
                day_schedule[zone] = int(duration * HOT_WEATHER_EXTRA)
        
        # Water each zone sequentially with proper waiting
        for zone_idx, zone_name in enumerate(VALVE_NAMES):
            if zone_name in day_schedule and day_schedule[zone_name] > 0:
                duration = day_schedule[zone_name]
                logging.info(f"Starting {zone_name} for {duration} minutes")
                
                # Turn on the current zone
                control_valve(zone_idx, True, duration)
                
                # Wait for this zone to complete (duration + small buffer)
                time.sleep(duration * 60 + 5)  # Convert minutes to seconds and add 5s buffer
                
                # Ensure the valve is off before proceeding (safety check)
                control_valve(zone_idx, False)
                logging.info(f"Completed watering {zone_name}")
                
    except Exception as e:
        logging.error(f"Error in scheduled watering: {str(e)}")

def schedule_daily_watering():
    """Schedule the daily watering job at 6 AM"""
    trigger = CronTrigger(hour=6, minute=0)
    scheduler.add_job(
        run_scheduled_watering,
        trigger=trigger,
        name="daily_watering"
    )
    logging.info("Scheduled daily watering at 6:00 AM")

# Initialize the daily watering schedule
schedule_daily_watering()

# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Smart Irrigation Dashboard"

# ====================== LAYOUT COMPONENTS ======================
controls_card = dbc.Card([
    dbc.CardHeader("Manual Valve Control", className="bg-primary text-white"),
    dbc.CardBody([
        html.Div([
            dbc.Button(
                f"{name}",
                id=f"btn-{i}",
                color="danger" if valve_states[i] else "primary",
                className="m-1",
                style={"width": "100px"}
            ) for i, name in enumerate(VALVE_NAMES)
        ], className="d-flex flex-wrap"),
        dbc.InputGroup([
            dbc.Input(
                id="duration-input",
                type="number",
                placeholder="Minutes",
                min=1,
                max=120,
                value=15
            ),
            dbc.InputGroupText("mins")
        ], className="my-3"),
        dbc.Row([
            dbc.Col(dbc.Button("Run All Zones", id="run-all-btn", color="success", className="w-100")),
            dbc.Col(dbc.Button("Emergency Stop", id="emergency-stop", color="danger", className="w-100"))
        ])
    ])
])

status_card = dbc.Card([
    dbc.CardHeader("System Status", className="bg-info text-white"),
    dbc.CardBody([
        html.Div(id="valve-status-indicators"),
        html.Hr(),
        html.Div(id="last-watering-info"),
        html.Hr(),
        html.Div(id="system-messages")
    ])
])

weather_card = dbc.Card([
    dbc.CardHeader("Weather Forecast", className="bg-warning text-dark"),
    dbc.CardBody([
        dcc.Interval(id="weather-update", interval=3600000),
        html.Div(id="weather-summary"),
        dcc.Graph(
            id="forecast-graph",
            config={
                'displayModeBar': False,
                'staticPlot': True,      
                'scrollZoom': False,
                'doubleClick': False,
            }
        ),
        dbc.Button("Update Now", id="update-weather", color="info", className="mt-2")
    ])
])

schedule_card = dbc.Card([
    dbc.CardHeader("Watering Schedule", className="bg-success text-white"),
    dbc.CardBody([
        dash_table.DataTable(
            id='schedule-editor',
            columns=[
                {'name': 'Zone', 'id': 'zone', 'editable': False},
                *[{'name': day, 'id': f'{day.lower()}_duration', 'editable': True, 'type': 'numeric'} 
                  for day in ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 
                             'Thursday', 'Friday', 'Saturday']]
            ],
            data=[{'zone': name} for name in VALVE_NAMES],
            editable=True,
            style_cell={
                'textAlign': 'center',
                'minWidth': '80px',
                'width': '80px',
                'maxWidth': '80px'
            },
            style_header={
                'fontWeight': 'bold',
                'textAlign': 'center'
            },
            style_table={'overflowX': 'auto'},
            style_data_conditional=[
                {
                    'if': {'column_id': 'zone'},
                    'textAlign': 'left',
                    'minWidth': '100px',
                    'width': '100px',
                    'maxWidth': '100px'
                }
            ]
        ),
        dbc.Button("Save Schedule", 
                 id="save-schedule", 
                 color="primary", 
                 className="mt-3"),
        html.Div(id='schedule-save-status')
    ])
])

history_card = dbc.Card([
    dbc.CardHeader("Watering History", className="bg-secondary text-white"),
    dbc.CardBody([
        dash_table.DataTable(
            id='history-table',
            columns=[
                {'name': 'Time', 'id': 'time'},
                {'name': 'Zone', 'id': 'zone'},
                {'name': 'Duration (min)', 'id': 'duration'},
                {'name': 'Weather', 'id': 'weather'}
            ],
            page_size=10,
            style_table={'overflowX': 'auto'},
            filter_action='native'
        )
    ])
])

app.layout = dbc.Container([
    html.H1("Smart Irrigation Control System", className="text-center my-4"),
    dbc.Row([
        dbc.Col(controls_card, md=4),
        dbc.Col(status_card, md=4),
        dbc.Col(weather_card, md=4)
    ], className="mb-4"),
    dbc.Row([
        dbc.Col(schedule_card, md=6),
        dbc.Col(history_card, md=6)
    ]),
    dcc.Interval(id="status-update", interval=10000),  # Update status every 10 sec
    dcc.Store(id="weather-store"),
    dcc.Store(id="system-store")
], fluid=True)

# ====================== GPIO FUNCTIONS ======================
def valve_timer(valve_idx, duration_min):
    """Thread function to turn off valve after duration"""
    time.sleep(duration_min * 60)
    control_valve(valve_idx, False)
    logging.info(f"Valve {VALVE_NAMES[valve_idx]} auto-off after {duration_min} minutes")

def control_valve(valve_idx, state, duration_min=10):
    """Control a single valve with safety checks and timed shutoff"""
    try:
        pin = VALVE_PINS[valve_idx]
        if state:
            # Cancel any existing timer for this valve
            if hasattr(control_valve, f"timer_{valve_idx}"):
                old_timer = getattr(control_valve, f"timer_{valve_idx}")
                if old_timer and old_timer.is_alive():
                    old_timer.cancel()
            
            # Turn valve ON
            GPIO.output(pin, RELAY_ACTIVE)
            valve_states[valve_idx] = True
            
            # Log watering event
            with history_lock:
                weather_condition = "Hot" if weather_data['next_high_temp'] > 85 else "Normal"
                
                watering_history.append({
                    'time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'zone': VALVE_NAMES[valve_idx],
                    'duration': duration_min,
                    'weather': weather_condition
                })
            
            # Start timer to turn off
            timer = threading.Timer(duration_min * 60, lambda: control_valve(valve_idx, False))
            timer.start()
            setattr(control_valve, f"timer_{valve_idx}", timer)
            
            logging.info(f"Valve {VALVE_NAMES[valve_idx]} ON for {duration_min} minutes")
        else:
            # Turn valve OFF
            GPIO.output(pin, GPIO.HIGH if RELAY_ACTIVE == GPIO.LOW else GPIO.LOW)
            valve_states[valve_idx] = False
            
            # Cancel any running timer
            if hasattr(control_valve, f"timer_{valve_idx}"):
                timer = getattr(control_valve, f"timer_{valve_idx}")
                if timer and timer.is_alive():
                    timer.cancel()
            
            logging.info(f"Valve {VALVE_NAMES[valve_idx]} OFF")
    except Exception as e:
        logging.error(f"Error controlling valve {VALVE_NAMES[valve_idx]}: {str(e)}")
        raise

# ====================== WEATHER FUNCTIONS ======================
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

# ====================== CALLBACKS ======================
@app.callback(
    [Output("valve-status-indicators", "children"),
     Output("last-watering-info", "children"),
     Output("system-messages", "children"),
     *[Output(f"btn-{i}", "color") for i in range(len(VALVE_NAMES))]],
    [Input("status-update", "n_intervals"),
     Input("emergency-stop", "n_clicks"),
     *[Input(f"btn-{i}", "n_clicks") for i in range(len(VALVE_NAMES))],
     Input("run-all-btn", "n_clicks"),
     Input("update-weather", "n_clicks")],
    [State("duration-input", "value"),
     State("weather-store", "data")]
)
def update_system(interval, emergency_clicks, *args):
    """Handle all system updates in one callback"""
    ctx = callback_context
    duration = args[-2] or 15  # Default duration
    weather = args[-1] or weather_data
    
    # Check which input triggered the callback
    if ctx.triggered:
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        # Emergency stop takes priority
        if trigger_id == 'emergency-stop':
            for i in range(len(VALVE_NAMES)):
                control_valve(i, False)  # This will cancel any running timers
            message = dbc.Alert("Emergency stop activated! All valves turned off.", color="danger")
        
        # Individual valve control
        elif trigger_id.startswith('btn-'):
            valve_idx = int(trigger_id.split('-')[1])
            control_valve(valve_idx, not valve_states[valve_idx], 
                        duration if not valve_states[valve_idx] else 0)
            message = None
        
        # Run all zones
        elif trigger_id == 'run-all-btn':
            for i in range(len(VALVE_NAMES)):
                control_valve(i, True, duration)
                time.sleep(1)  # Brief delay between valves
            message = dbc.Alert(f"Watering all zones for {duration} minutes", color="success")
        
        # Weather update
        elif trigger_id == 'update-weather':
            message = dbc.Alert("Updating weather data...", color="info")
        else:
            message = None
    else:
        message = None
    
    # Update status indicators
    indicators = []
    for i, name in enumerate(VALVE_NAMES):
        current_state = GPIO.input(VALVE_PINS[i]) == RELAY_ACTIVE
        valve_states[i] = current_state
        color = "danger" if current_state else "primary"
        text = "ACTIVE" if current_state else "INACTIVE"
        indicators.append(
            dbc.Alert(f"{name}: {text}", color=color, className="p-2 m-1")
        )
    
    # Last watering info
    last_watering = "No watering history yet"
    with history_lock:
        if watering_history:
            last = watering_history[-1]
            last_watering = [
                html.H5("Last Watering:"),
                html.P(f"{last['zone']} for {last['duration']} minutes"),
                html.Small(f"at {last['time']} ({last['weather']})")
            ]
    
    # Button colors
    button_colors = ["danger" if valve_states[i] else "primary" 
                    for i in range(len(VALVE_NAMES))]
    
    return indicators, last_watering, message, *button_colors

@app.callback(
    [Output("weather-summary", "children"),
     Output("forecast-graph", "figure"),
     Output("weather-store", "data")],
    [Input("weather-update", "n_intervals"),
     Input("update-weather", "n_clicks")]
)
def update_weather(interval, update_click):
    """Update weather data and display"""
    try:
        weather = get_weather_forecast()
        
        # Update global weather data
        global weather_data
        weather_data = weather
        
        # Create summary display
        summary = [
            html.H4(f"Current: {weather.get('current_temp', 'N/A')}°F"),
            html.Hr(),
            html.H5(f"Next High: {weather.get('next_high_temp', 75)}°F")
        ]
        
        # Create forecast graph
        fig = go.Figure()
        forecast_data = weather.get('forecast_data', [])
        
        if forecast_data:
            highs = [f for f in forecast_data if f.get('is_high')]
            if highs:
                fig.add_trace(go.Bar(
                    x=[f['period'] for f in highs],
                    y=[f['temp_value'] for f in highs],
                    text=[f['description'] for f in highs],
                    marker_color='indianred',
                    name='High Temp'
                ))
            
            fig.update_layout(
                title="Weather Forecast",
                yaxis_title="Temperature (°F)",
                xaxis_title="Day",
                hovermode="x unified",
                dragmode=False,
                xaxis=dict(fixedrange=True),
                yaxis=dict(fixedrange=True)
            )
        else:
            fig.update_layout(
                title="No Forecast Data Available",
                annotations=[dict(text="Check connection", showarrow=False)],
                dragmode=False,
                xaxis=dict(fixedrange=True),
                yaxis=dict(fixedrange=True)
            )
        
        return summary, fig, weather
    
    except Exception as e:
        logging.error(f"Weather update failed: {str(e)}")
        error_msg = [
            html.H4("Weather Data Unavailable"),
            html.P("Please check your internet connection")
        ]
        error_fig = go.Figure()
        error_fig.update_layout(
            title="Weather Data Error",
            annotations=[dict(text="Update failed", showarrow=False)],
            dragmode=False,
            xaxis=dict(fixedrange=True),
            yaxis=dict(fixedrange=True)
        )
        return error_msg, error_fig, weather_data

@app.callback(
    Output("history-table", "data"),
    Input("status-update", "n_intervals")
)
def update_history_table(n):
    with history_lock:
        return watering_history

@app.callback(
    Output('weekly-schedule-editor', 'data'),
    [Input('day-selector', 'value')],
    [State('weekly-schedule-editor', 'data')]
)
def update_weekly_editor(selected_day, current_data):
    schedules = load_schedule()
    day_schedule = schedules['weekly'].get(selected_day, {})
    return [{'zone': name, 'duration': day_schedule.get(name, 10)} for name in VALVE_NAMES]

@app.callback(
    Output('schedule-editor', 'data'),
    Input('schedule-editor', 'data_timestamp'),
    State('schedule-editor', 'data')
)
def initialize_schedule_editor(timestamp, current_data):
    if current_data and any(day in current_data[0] for day in ['sunday_duration', 'monday_duration']):
        return current_data
        
    schedules = load_schedule()
    schedule_data = []
    
    for zone in VALVE_NAMES:
        zone_data = {'zone': zone}
        for day in ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 
                   'Thursday', 'Friday', 'Saturday']:
            zone_data[f'{day.lower()}_duration'] = schedules['weekly'].get(day, {}).get(zone, 10)
        schedule_data.append(zone_data)
    
    return schedule_data

@app.callback(
    Output('schedule-save-status', 'children'),
    Input('save-schedule', 'n_clicks'),
    State('schedule-editor', 'data')
)
def save_schedule(n_clicks, table_data):
    if not n_clicks:
        return None
    
    try:
        with open(SCHEDULE_FILE, 'r') as f:
            schedules = json.load(f)
        
        # Reconstruct weekly schedule from table data
        weekly_schedule = {}
        for day in ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 
                   'Thursday', 'Friday', 'Saturday']:
            day_key = f'{day.lower()}_duration'
            weekly_schedule[day] = {}
            for row in table_data:
                weekly_schedule[day][row['zone']] = max(0, int(row.get(day_key, 10)))
        
        schedules['weekly'] = weekly_schedule
        
        with open(SCHEDULE_FILE, 'w') as f:
            json.dump(schedules, f, indent=2)
        
        return dbc.Alert("Schedule saved successfully!", color="success", duration=3000)
    except Exception as e:
        return dbc.Alert(f"Error saving schedule: {str(e)}", color="danger")

def cleanup():
    """Clean up resources on exit"""
    logging.info("Cleaning up resources")
    scheduler.shutdown()
    for pin in VALVE_PINS:
        GPIO.output(pin, GPIO.HIGH if RELAY_ACTIVE == GPIO.LOW else GPIO.LOW)
    GPIO.cleanup()

if __name__ == '__main__':
    try:
        # Initial weather update
        weather_data = get_weather_forecast()
        
        # Start the server
        app.run(host='0.0.0.0', port=8050, debug=False)
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()