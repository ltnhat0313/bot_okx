# -*- coding: utf-8 -*-
"""
File cấu hình trung tâm cho toàn bộ bot.
Tất cả các tham số quan trọng, API keys, và cài đặt chiến lược được định nghĩa tại đây.
"""

import os
from dotenv import load_dotenv

# Tải các biến môi trường từ file .env vào chương trình
load_dotenv()


# ==============================================================================
# 1. CÀI ĐẶT API VÀ KẾT NỐI
# ==============================================================================
IS_DEMO_MODE = os.getenv("OKX_DEMO_MODE", "1") == "1"
OKX_API_KEY = os.getenv("OKX_API_KEY")
OKX_SECRET_KEY = os.getenv("OKX_SECRET_KEY")
OKX_PASSPHRASE = os.getenv("OKX_PASSPHRASE")
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")


# ==============================================================================
# 2. CÀI ĐẶT HOẠT ĐỘNG CỦA BOT
# ==============================================================================
SYMBOLS = ['BTC-USDT-SWAP', 'ETH-USDT-SWAP','SOL-USDT-SWAP']
CYCLE_DELAY_SECONDS = 5


# ==============================================================================
# 3. THAM SỐ CỐT LÕI CỦA CHIẾN LƯỢC
# ==============================================================================
# --- Quản lý rủi ro (Risk Management) ---
RISK_PER_TRADE = 0.1
STOP_LOSS_MULTIPLIER = 2.0
TAKE_PROFIT_MULTIPLIER = 3.0

# --- Phân tích kỹ thuật (Technical Analysis) ---
TREND_TIMEFRAME = '4H'
ENTRY_TIMEFRAMES = ['1m', '5m']

# Các tham số cho chỉ báo
RSI_PERIOD = 14
ATR_PERIOD = 14
TREND_MA_PERIOD = 50

# Các ngưỡng RSI để vào lệnh
RSI_OVERSOLD = 30                      # Ngưỡng quá bán (dùng cho lệnh Long)
RSI_OVERBOUGHT = 70                    # Ngưỡng quá mua (dùng cho lệnh Short)
RSI_PULLBACK = 60                      # Ngưỡng pullback cho lệnh Long
RSI_PULLBACK_SELL = 40                 # Ngưỡng pullback cho lệnh Short

# Tên các cột dữ liệu sau khi được tính toán
TREND_MA_COL = f'EMA_{TREND_MA_PERIOD}'
RSI_COL = f'RSI_{RSI_PERIOD}'
ATR_COL = f'ATRr_{ATR_PERIOD}'


# ==============================================================================
# 4. ĐƯỜNG DẪN DỮ LIỆU VÀ LOGGING
# ==============================================================================
DATABASE_PATH = "data/trades.db"
LOG_FILE_PATH = "logs/bot_activity.log"
LOG_LEVEL = "INFO"
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 5


# ==============================================================================
# 5. CÀI ĐẶT CHO BACKTESTING
# ==============================================================================
BACKTEST_SYMBOL = 'BTCUSDT'
BACKTEST_TIMEFRAME = '1m'
START_DATE_FOR_DOWNLOAD = "1 Jan, 2024"
