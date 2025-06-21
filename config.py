# File: config.py

import os
from typing import Dict
from dotenv import load_dotenv

load_dotenv()

# --- Cấu hình API ---
OKX_API_KEY: str = os.getenv('OKX_API_KEY')
OKX_SECRET_KEY: str = os.getenv('OKX_SECRET_KEY')
OKX_PASSPHRASE: str = os.getenv('OKX_PASSPHRASE')

# --- Cấu hình Giao dịch ---
OKX_TRADING_ENVIRONMENT: str = 'TEST'
SYMBOL: str = 'DOGE-USDT-SWAP'
TIMEFRAME: str = '15m'
LEVERAGE: int = 10  # Đòn bẩy mong muốn

# --- Cấu hình Chiến lược ---
ENTRY_THRESHOLD_LONG: float = 6.0
ENTRY_THRESHOLD_SHORT: float = -7.0

# --- Cấu hình Quản lý Rủi ro ---
RISK_PER_TRADE_PERCENT: float = 0.01  # Rủi ro 0.01% vốn cho mỗi lệnh (để test)
STOP_LOSS_ATR_MULTIPLIER: float = 1.2
TAKE_PROFIT_ATR_MULTIPLIER: float = 2.5

# === Vốn khởi điểm cho backtest ===
INITIAL_BALANCE = 1000.0