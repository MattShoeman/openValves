import dash
from dash import dcc, html, Input, Output, State, dash_table, callback_context
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import logging
from gpio_controller import ValveController
from scheduler import IrrigationScheduler
from weather import get_weather_forecast
from config import VALVE_NAMES

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Initialize system components
valve_controller = ValveController()
irrigation_scheduler = IrrigationScheduler(valve_controller, get_weather_forecast)

# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Smart Irrigation Dashboard"

# ====================== LAYOUT COMPONENTS ======================
# (Same layout as original, but reference valve_controller instead of global variables)

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
    [State("duration-input", "value")]
)
def update_system(interval, emergency_clicks, *args):
    """Handle all system updates in one callback"""
    ctx = callback_context
    duration = args[-1] or 15  # Default duration
    
    if ctx.triggered:
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if trigger_id == 'emergency-stop':
            valve_controller.emergency_stop()
            message = dbc.Alert("Emergency stop activated! All valves turned off.", color="danger")
        
        elif trigger_id.startswith('btn-'):
            valve_idx = int(trigger_id.split('-')[1])
            current_state = valve_controller.valve_states[valve_idx]
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

# (Other callbacks remain similar but reference the new components)

if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=8050, debug=False)
    except KeyboardInterrupt:
        pass
    finally:
        valve_controller.cleanup()
        irrigation_scheduler.shutdown()