import dash
from dash import dcc, html, Input, Output, State, dash_table, callback_context
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import logging
import time
import json
from datetime import datetime
from gpio_controller import ValveController
from scheduler import IrrigationScheduler
from weather import get_weather_forecast
from config import VALVE_NAMES
from database import init_db


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Initialize system components
valve_controller = ValveController()
irrigation_scheduler = IrrigationScheduler(valve_controller, get_weather_forecast)
init_db()

# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Smart Irrigation Dashboard"

# ====================== CARD COMPONENTS ======================

# 1. Schedule Card (Upper Left)
schedule_card = dbc.Card([
    dbc.CardHeader("Watering Schedule", className="bg-success text-white fs-5"),
    dbc.CardBody([
        dash_table.DataTable(
            id='schedule-editor',
            columns=[
                {'name': 'Zone', 'id': 'zone', 'editable': False},
                *[{'name': day[:3], 'id': f'{day.lower()}_duration', 'editable': True, 'type': 'numeric'} 
                  for day in ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 
                             'Thursday', 'Friday', 'Saturday']]
            ],
            data=[{'zone': name} for name in VALVE_NAMES],
            editable=True,
            style_cell={
                'textAlign': 'center',
                'minWidth': '60px',
                'width': '60px',
                'maxWidth': '60px',
                'padding': '5px'
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
                    'minWidth': '80px',
                    'width': '80px',
                    'maxWidth': '80px'
                }
            ]
        ),
        html.Div(id='schedule-save-status', className="mt-2"),
        dbc.ButtonGroup([
            dbc.Button("Save Schedule", id="save-schedule", color="primary", className="mt-2"),
            dbc.Button("Run Today", id="run-today", color="success", className="mt-2")
        ], className="w-100")
    ])
], className="shadow-sm")

# 2. Controls Card (Upper Middle)
controls_card = dbc.Card([
    dbc.CardHeader("Manual Control", className="bg-primary text-white"),
    dbc.CardBody([
        html.Div([
            dbc.Button(
                f"{name}",
                id=f"btn-{i}",
                color="danger" if valve_controller.get_valve_states()[i] else "primary",
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
            dbc.Col(dbc.Button("Run All", id="run-all-btn", color="success", className="w-100")),
            dbc.Col(dbc.Button("Emergency Stop", id="emergency-stop", color="danger", className="w-100"))
        ])
    ])
], className="h-100")

# 3. Status Card (Upper Right)
status_card = dbc.Card([
    dbc.CardHeader("System Status", className="bg-info text-white"),
    dbc.CardBody([
        html.Div(id="valve-status-indicators"),
        dbc.Progress(id="watering-progress", striped=True, animated=True, className="my-2"),
        html.Div(id="last-watering-info", className="mt-3"),
        html.Div(id="system-messages")
    ])
], className="h-100")

# 4. Weather Card (Lower Left)
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
            },
            className="mt-2"
        ),
        dbc.Button("Update Now", id="update-weather", color="info", className="mt-2 w-100")
    ])
])

# 5. History Card (Lower Right)
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
            filter_action='native',
            style_cell={
                'fontSize': '12px',
                'padding': '5px'
            }
        )
    ])
])

# ====================== LAYOUT ======================
app.layout = dbc.Container([
    html.H1("Smart Irrigation Control System", className="text-center my-4"),
    
    # Top Row
    dbc.Row([
        dbc.Col(schedule_card, md=5),
        dbc.Col(controls_card, md=3),
        dbc.Col(status_card, md=4)
    ], className="mb-4 g-3"),
    
    # Bottom Row
    dbc.Row([
        dbc.Col(weather_card, md=6, className="mb-3"),
        dbc.Col(history_card, md=6, className="mb-3")
    ], className="g-3"),
    
    # Hidden Components
    dcc.Interval(id="status-update", interval=10000),
    dcc.Store(id="weather-store"),
    dcc.Store(id="system-store")
], fluid=True, className="py-3")

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
     Input("run-today", "n_clicks"),
     Input("update-weather", "n_clicks")],
    [State("duration-input", "value")]
)
def update_system(interval, emergency_clicks, *args):
    ctx = callback_context
    duration = args[-1] or 15
    
    if ctx.triggered:
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if trigger_id == 'emergency-stop':
            valve_controller.emergency_stop()
            message = dbc.Alert("Emergency stop activated! All valves turned off.", color="danger")
        
        elif trigger_id == 'run-today':
            irrigation_scheduler.run_scheduled_watering()
            message = dbc.Alert("Running today's watering schedule", color="success")
        
        elif trigger_id.startswith('btn-'):
            valve_idx = int(trigger_id.split('-')[1])
            current_state = valve_controller.get_valve_states()[valve_idx]
            valve_controller.control_valve(
                valve_idx, 
                not current_state, 
                duration if not current_state else 0
            )
            message = None
        
        elif trigger_id == 'run-all-btn':
            for i in range(len(VALVE_NAMES)):
                valve_controller.control_valve(i, True, duration)
                time.sleep(1)
            message = dbc.Alert(f"Watering all zones for {duration} minutes", color="success")
        
        elif trigger_id == 'update-weather':
            message = dbc.Alert("Updating weather data...", color="info")
        else:
            message = None
    else:
        message = None
    
    # Update status indicators
    indicators = []
    current_states = valve_controller.get_valve_states()
    for i, name in enumerate(VALVE_NAMES):
        color = "danger" if current_states[i] else "primary"
        text = "ACTIVE" if current_states[i] else "INACTIVE"
        indicators.append(
            dbc.Alert(f"{name}: {text}", color=color, className="p-2 m-1")
        )
    
    # Last watering info
    history = valve_controller.get_watering_history()
    last_watering = "No watering history yet"
    if history:
        last = history[-1]
        last_watering = [
            html.H5("Last Watering:"),
            html.P(f"{last['zone']} for {last['duration']} minutes"),
            html.Small(f"at {last['time']} ({last['weather']})")
        ]
    
    # Button colors
    button_colors = ["danger" if state else "primary" for state in current_states]
    
    return indicators, last_watering, message, *button_colors

@app.callback(
    [Output("weather-summary", "children"),
     Output("forecast-graph", "figure"),
     Output("weather-store", "data")],
    [Input("weather-update", "n_intervals"),
     Input("update-weather", "n_clicks")]
)
def update_weather(interval, update_click):
    try:
        weather = get_weather_forecast()
        
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
                hovermode="x unified"
            )
        
        return summary, fig, weather
    
    except Exception as e:
        logging.error(f"Weather update failed: {str(e)}")
        error_msg = html.Div([
            html.H4("Weather Data Unavailable"),
            html.P("Please check your internet connection")
        ])
        error_fig = go.Figure()
        return error_msg, error_fig, None

@app.callback(
    Output('schedule-editor', 'data'),
    Input('schedule-editor', 'data_timestamp'),
    State('schedule-editor', 'data')
)
def initialize_schedule_editor(timestamp, current_data):
    if current_data and any(day in current_data[0] for day in ['sunday_duration', 'monday_duration']):
        return current_data
        
    schedules = irrigation_scheduler.load_schedule()
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
        schedules = irrigation_scheduler.load_schedule()
        
        # Reconstruct weekly schedule
        weekly_schedule = {}
        for day in ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 
                   'Thursday', 'Friday', 'Saturday']:
            day_key = f'{day.lower()}_duration'
            weekly_schedule[day] = {}
            for row in table_data:
                weekly_schedule[day][row['zone']] = max(0, int(row.get(day_key, 10)))
        
        schedules['weekly'] = weekly_schedule
        
        with open('schedules.json', 'w') as f:
            json.dump(schedules, f, indent=2)
        
        return dbc.Alert("Schedule saved successfully!", color="success", duration=3000)
    except Exception as e:
        return dbc.Alert(f"Error saving schedule: {str(e)}", color="danger")

@app.callback(
    Output("history-table", "data"),
    Input("status-update", "n_intervals")
)
def update_history_table(n):
    return valve_controller.get_watering_history()

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=8050, debug=False)
    except KeyboardInterrupt:
        pass
    finally:
        valve_controller.cleanup()
        irrigation_scheduler.shutdown()
