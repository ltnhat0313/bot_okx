# File: bot.py

import time, logging, config
from logging_config import setup_logging
from modules import (OKXIntegration, TAEngine, RiskManagement, log_trade)

logger = setup_logging()

class TradingBot:
    def __init__(self):
        logger.info("Initializing Trading Bot (Live/Paper Mode)...")
        self.is_test = config.OKX_TRADING_ENVIRONMENT == 'TEST'
        self.api = OKXIntegration(config.OKX_API_KEY, config.OKX_SECRET_KEY, config.OKX_PASSPHRASE, self.is_test)
        self.ta_engine = TAEngine()
        self.in_position = False
        self.current_position = {}
        logger.info(f"Bot initialized in {'TEST' if self.is_test else 'REAL'} environment.")

    def run_cycle(self):
        logger.info(f"--- Running new cycle for {config.SYMBOL} ---")
        klines = self.api.get_klines(config.SYMBOL, config.TIMEFRAME, total_candles=100)
        if not klines or not klines.get('data'):
            logger.warning("Could not fetch klines.")
            return

        ta_score, df = self.ta_engine.calculate_technical_score(klines)
        if df is None or df.empty:
            logger.warning("Could not calculate technical score.")
            return
        
        latest_candle = df.iloc[-1]
        if not self.in_position:
            self.check_for_entry(ta_score, latest_candle)
        else:
            self.manage_open_position(latest_candle)

    def check_for_entry(self, score, candle):
        logger.info(f"Checking for entry signal. Current TA Score: {score:.2f}")
        if score >= config.ENTRY_THRESHOLD_LONG:
            logger.info(f"ENTRY SIGNAL DETECTED! Attempting to place a BUY order.")
            
            # Bước 1: Tự động thiết lập đòn bẩy
            logger.info(f"Setting leverage to {config.LEVERAGE}x for {config.SYMBOL}...")
            leverage_result = self.api.set_leverage(config.SYMBOL, config.LEVERAGE)
            if not leverage_result:
                logger.error("Failed to set leverage. Aborting trade.")
                return

            instrument_details = self.api.get_instrument_details(config.SYMBOL)
            if not instrument_details: return
            lot_size = float(instrument_details.get('lotSz', '0'))
            if lot_size <= 0: return

            balance = self.api.get_account_balance('USDT')
            if balance is None or balance <= 0: return
            
            risk_manager = RiskManagement(balance, config.RISK_PER_TRADE_PERCENT, config.STOP_LOSS_ATR_MULTIPLIER, config.TAKE_PROFIT_ATR_MULTIPLIER)
            trade_params = risk_manager.get_trade_params(candle, 'buy')
            if not trade_params: return

            size = risk_manager.get_position_size(trade_params['entry'], trade_params['sl'], lot_size)
            if size <= 0: return

            precision = 0
            if '.' in str(lot_size):
                precision = len(str(lot_size).split('.')[1])
            formatted_size = f"{size:.{precision}f}"
            
            logger.info(f"Final formatted size to be placed: {formatted_size}")
            result = self.api.place_order(config.SYMBOL, 'buy', 'market', formatted_size)
            
            if result and result.get('code') == '0' and result.get('data') and result['data'][0].get('sCode') == '0':
                logger.info(f"TRADE PLACED SUCCESSFULLY: BUY {formatted_size} {config.SYMBOL}")
                self.in_position = True
                self.current_position = trade_params
                self.current_position['size'] = float(formatted_size)
                self.current_position['lot_size'] = lot_size
                log_trade({**self.current_position, 'symbol': config.SYMBOL, 'side': 'BUY', 'final_score': score})
            else:
                logger.error(f"Failed to place trade. API Response: {result}")

    def manage_open_position(self, candle):
        current_price = candle['c']
        logger.info(f"Managing open position. Current Price={current_price:.4f}, SL={self.current_position.get('sl', 0):.4f}, TP={self.current_position.get('tp', 0):.4f}")

        exit_reason = None
        if current_price <= self.current_position.get('sl', float('inf')):
            exit_reason = 'Stop Loss'
        elif current_price >= self.current_position.get('tp', 0):
            exit_reason = 'Take Profit'
        
        if exit_reason:
            logger.info(f"EXIT SIGNAL DETECTED ({exit_reason})! Attempting to close position.")
            size_to_close = self.current_position.get('size', 0)
            lot_size = self.current_position.get('lot_size', 0.01)
            if size_to_close > 0:
                precision = 0
                if '.' in str(lot_size):
                    precision = len(str(lot_size).split('.')[1])
                formatted_size_to_close = f"{size_to_close:.{precision}f}"
                result = self.api.place_order(config.SYMBOL, 'sell', 'market', formatted_size_to_close)

                if result and result.get('code') == '0' and result.get('data') and result['data'][0].get('sCode') == '0':
                    logger.info(f"POSITION CLOSED SUCCESSFULLY.")
                    self.in_position = False
                    self.current_position = {}
                else:
                    logger.error(f"Failed to close position. API Response: {result}")
            else:
                logger.warning("Position size is zero, cannot close. Resetting state.")
                self.in_position = False
                self.current_position = {}

    def start(self):
        """Vòng lặp chính của bot."""
        while True:
            try:
                self.run_cycle()
                sleep_seconds = {'1m': 60, '5m': 300, '15m': 900, '1h': 3600}.get(config.TIMEFRAME, 900)
                logger.info(f"Cycle finished. Waiting for {sleep_seconds} seconds...")
                time.sleep(sleep_seconds)
            except KeyboardInterrupt:
                logger.info("Bot stopped by user.")
                break
            except Exception as e:
                logger.exception("An unexpected error occurred in the main loop!")
                time.sleep(60)

if __name__ == "__main__":
    bot = TradingBot()
    bot.start()