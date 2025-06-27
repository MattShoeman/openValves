import sqlite3
from datetime import datetime
import logging
import os
from config import WATER_FLOW_RATES, WATER_RATES, HOT_WEATHER_EXTRA


DB_FILE = "irrigation.db"

def init_db():
    """Initialize the database with required tables"""
    # Check if database exists to avoid unnecessary table recreation
    db_exists = os.path.exists(DB_FILE)
    
    with sqlite3.connect(DB_FILE) as conn:
        c = conn.cursor()
        
        # Check if table exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='watering_history'")
        table_exists = c.fetchone()
        
        if not table_exists:
            # Create fresh table with correct schema
            c.execute("""
            CREATE TABLE watering_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT NOT NULL,
                zone TEXT NOT NULL,
                duration INTEGER NOT NULL,
                weather TEXT NOT NULL
            )
            """)
            conn.commit()
            logging.info("Created new watering_history table")
        elif not db_exists:
            # Database was just created but table exists (shouldn't happen)
            logging.warning("Database file was missing but table exists - recreating")
            c.execute("DROP TABLE IF EXISTS watering_history")
            init_db()  # Recursively recreate

def log_watering_event(zone: str, duration: int, weather: str):
    """Log a watering event to the database"""
    try:
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(DB_FILE) as conn:
            c = conn.cursor()
            
            # Verify table structure
            c.execute("PRAGMA table_info(watering_history)")
            columns = [col[1] for col in c.fetchall()]
            required_columns = {'time', 'zone', 'duration', 'weather'}
            
            if not required_columns.issubset(columns):
                logging.error("Database schema mismatch - recreating table")
                c.execute("DROP TABLE IF EXISTS watering_history")
                conn.commit()
                init_db()
                
            c.execute(
                "INSERT INTO watering_history (time, zone, duration, weather) VALUES (?, ?, ?, ?)",
                (time_str, zone, duration, weather)
            )
            conn.commit()
    except Exception as e:
        logging.error(f"Error logging watering event: {str(e)}")
        raise

def get_watering_history(limit: int = 100):
    """Retrieve watering history from database"""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            # Verify table exists
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='watering_history'")
            if not c.fetchone():
                init_db()
                return []
                
            c.execute("""
            SELECT time, zone, duration, weather
            FROM watering_history
            ORDER BY time DESC
            LIMIT ?
            """, (limit,))
            return [dict(row) for row in c.fetchall()]
    except Exception as e:
        logging.error(f"Error getting watering history: {str(e)}")
        return []

def calculate_water_usage(days=30):
    """Calculate water usage with simplified rates"""
    try:
        # Use default period if not specified
        if days is None:
            days = WATER_RATES["usage_period_days"]
            
        with sqlite3.connect(DB_FILE) as conn:
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            
            # Get watering history for the period
            c.execute("""
                SELECT zone, duration, time 
                FROM watering_history 
                WHERE date(time) >= date('now', ?)
                ORDER BY time
            """, (f"-{days} days",))
            
            history = [dict(row) for row in c.fetchall()]
            
            # Calculate total gallons per zone
            zone_usage = {}
            total_gallons = 0
            for event in history:
                zone = event['zone']
                duration = event['duration']
                flow_rate = WATER_FLOW_RATES.get(zone, 1)  # Default to 1 if zone not found
                gallons = duration * flow_rate
                total_gallons += gallons
                if zone not in zone_usage:
                    zone_usage[zone] = 0
                zone_usage[zone] += gallons
            
            # Convert gallons to hcf (hundred cubic feet)
            total_hcf = total_gallons / WATER_RATES["gallons_per_hcf"]
            
            # Calculate water charges
            if total_hcf <= WATER_RATES["tier_threshold"]:
                water_charges = total_hcf * (WATER_RATES["water_rate"] + WATER_RATES["water_surcharge"])
            else:
                water_charges = (WATER_RATES["tier_threshold"] * (WATER_RATES["water_rate"] + WATER_RATES["water_surcharge"]) +
                               (total_hcf - WATER_RATES["tier_threshold"]) * (WATER_RATES["tiered_rate"] + WATER_RATES["water_surcharge"]))
            
            # Calculate wastewater charges
            wastewater_charges = total_hcf * WATER_RATES["wastewater_rate"]
            
            # Calculate prorated fixed charges
            prorate_factor = days / 30
            fixed_charges = WATER_RATES["fixed_total"] * prorate_factor
            
            # Calculate total cost
            total_cost = fixed_charges + water_charges + wastewater_charges
            
            return {
                'total_gallons': total_gallons,
                'total_hcf': total_hcf,
                'total_cost': round(total_cost, 2),
                'cost_breakdown': {
                    'fixed_charges': fixed_charges,
                    'water_charges': water_charges,
                    'wastewater_charges': wastewater_charges
                },
                'zone_usage': zone_usage,
                'history': history,
                'calculation_period_days': days
            }
            
    except Exception as e:
        logging.error(f"Error calculating water usage: {str(e)}")
        return None

def project_water_usage(days=30):
    """Project water usage based on current schedule"""
    try:
        from scheduler import IrrigationScheduler
        from datetime import datetime, timedelta
        
        # Load current schedule
        schedules = IrrigationScheduler.load_schedule(None)
        
        # Calculate total gallons from schedule
        total_gallons = 0
        zone_usage = {zone: 0 for zone in WATER_FLOW_RATES.keys()}
        
        # Calculate for each day in projection period
        for day_offset in range(days):
            current_date = datetime.now() + timedelta(days=day_offset)
            day_of_week = current_date.strftime("%A")
            day_schedule = schedules['weekly'].get(day_of_week, {})
            
            # Apply weather adjustment if hot weather is expected
            weather_factor = HOT_WEATHER_EXTRA if day_offset < 7 else 1.0
            
            for zone, duration in day_schedule.items():
                if zone in WATER_FLOW_RATES:
                    gallons = duration * WATER_FLOW_RATES[zone] * weather_factor
                    total_gallons += gallons
                    zone_usage[zone] += gallons
        
        # Convert gallons to hcf
        total_hcf = total_gallons / WATER_RATES["gallons_per_hcf"]
        
        # Calculate costs
        prorate_factor = days / 30
        fixed_charges = WATER_RATES["fixed_total"] * prorate_factor
        
        # Water charges
        if total_hcf <= WATER_RATES["tier_threshold"]:
            water_charges = total_hcf * (WATER_RATES["water_rate"] + WATER_RATES["water_surcharge"])
        else:
            water_charges = (WATER_RATES["tier_threshold"] * (WATER_RATES["water_rate"] + WATER_RATES["water_surcharge"]) +
                           (total_hcf - WATER_RATES["tier_threshold"]) * (WATER_RATES["tiered_rate"] + WATER_RATES["water_surcharge"]))
        
        # Wastewater charges
        wastewater_charges = total_hcf * WATER_RATES["wastewater_rate"]
        
        total_cost = fixed_charges + water_charges + wastewater_charges
        
        return {
            'total_gallons': total_gallons,
            'total_hcf': total_hcf,
            'total_cost': round(total_cost, 2),
            'cost_breakdown': {
                'fixed_charges': fixed_charges,
                'water_charges': water_charges,
                'wastewater_charges': wastewater_charges
            },
            'zone_usage': {k: v for k, v in zone_usage.items() if v > 0},
            'calculation_period_days': days
        }
        
    except Exception as e:
        logging.error(f"Error projecting water usage: {str(e)}")
        return None


# Initialize database on import
init_db()
