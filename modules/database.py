# modules/database.py
import sqlite3
import logging
from typing import Dict, Any

DB_NAME = 'bot_database.db'
logger = logging.getLogger(__name__)

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        with get_db_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    symbol TEXT NOT NULL, side TEXT NOT NULL, size REAL NOT NULL,
                    entry_price REAL NOT NULL, stop_loss REAL NOT NULL, take_profit REAL NOT NULL,
                    final_score REAL, status TEXT DEFAULT 'OPEN', pnl REAL
                )
            ''')
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.exception(f"Error initializing database: {e}")

def log_trade(trade_data: Dict[str, Any]):
    sql = '''
        INSERT INTO trades (symbol, side, size, entry_price, stop_loss, take_profit, final_score)
        VALUES (:symbol, :side, :size, :entry_price, :stop_loss, :take_profit, :final_score)
    '''
    try:
        with get_db_connection() as conn:
            conn.execute(sql, trade_data)
        logger.info(f"Successfully logged trade for {trade_data['symbol']}")
    except Exception as e:
        logger.exception(f"Error logging trade to database: {e}")