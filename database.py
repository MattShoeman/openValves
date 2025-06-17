import sqlite3
from datetime import datetime
import logging
import os

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

# Initialize database on import
init_db()