# File: backtester.py (PHIÊN BẢN CUỐI CÙNG - HOÀN CHỈNH)

import pandas as pd
import logging
import config
from logging_config import setup_logging
from modules import OKXIntegration, TAEngine, RiskManagement

# Thiết lập logging
logger = setup_logging(log_file='logs/backtester.log')

class Backtester:
    def __init__(self, initial_balance, symbol, timeframe):
        logger.info("--- Initializing Backtester ---")
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.symbol = symbol
        self.timeframe = timeframe
        
        self.api = OKXIntegration(config.OKX_API_KEY, config.OKX_SECRET_KEY, config.OKX_PASSPHRASE, is_test=True)
        self.ta_engine = TAEngine()
        
        self.trades = []
        self.in_position = False
        self.position = {}

    def run(self):
        logger.info(f"Starting backtest for {self.symbol} on {self.timeframe} with initial balance ${self.initial_balance:,.2f}")

        # Lấy 1500 cây nến
        klines_data = self.api.get_klines(self.symbol, self.timeframe, total_candles=1500) 
        if not klines_data or 'data' not in klines_data or not klines_data['data']:
            logger.error("Could not fetch historical klines for backtesting.")
            return

        columns = ['ts', 'o', 'h', 'l', 'c', 'vol', 'volCcy', 'volCcyQuote', 'confirm']
        df = pd.DataFrame(klines_data['data'], columns=columns)
        df['ts'] = pd.to_numeric(df['ts'])
        df['ts'] = pd.to_datetime(df['ts'], unit='ms')
        df.set_index('ts', inplace=True)
        df = df.astype(float).sort_index()
        
        df_with_indicators = self.ta_engine.calculate_indicators(df)
        if df_with_indicators.empty:
            logger.error("Failed to calculate indicators.")
            return

        logger.info(f"Loaded and processed {len(df_with_indicators)} candles for backtest.")

        for i in range(1, len(df_with_indicators)):
            current_candle = df_with_indicators.iloc[i]
            
            score = 0
            if current_candle['EMA_12'] > current_candle['EMA_26']:
                score += 6
            else:
                score -= 6
            
            if current_candle['RSI_14'] < 30:
                score += 4
            elif current_candle['RSI_14'] > 70:
                score -= 4

            if not self.in_position:
                if score >= config.ENTRY_THRESHOLD_LONG:
                    entry_price = current_candle['c']
                    risk_manager = RiskManagement(self.balance, config.RISK_PER_TRADE_PERCENT, config.STOP_LOSS_ATR_MULTIPLIER, config.TAKE_PROFIT_ATR_MULTIPLIER)
                    trade_params = risk_manager.get_trade_params(current_candle, 'buy')
                    if not trade_params: continue
                    
                    size = risk_manager.get_position_size(entry_price, trade_params['sl'])

                    if size > 0:
                        self.in_position = True
                        self.position = {
                            'side': 'BUY', 'entry_price': entry_price, 'entry_time': current_candle.name,
                            'size': size, 'sl': trade_params['sl'], 'tp': trade_params['tp'], 'entry_score': score
                        }
                        logger.info(f"Simulating BUY: Time={self.position['entry_time']}, Price={entry_price:.4f}, Size={size:.4f}")

            elif self.in_position:
                exit_price = current_candle['c']
                exit_reason = None
                if self.position['side'] == 'BUY':
                    if exit_price <= self.position['sl']:
                        exit_reason = 'Stop Loss'
                    elif exit_price >= self.position['tp']:
                        exit_reason = 'Take Profit'
                    elif score <= config.ENTRY_THRESHOLD_SHORT:
                        exit_reason = 'Reversal Signal'

                if exit_reason:
                    pnl = (exit_price - self.position['entry_price']) * self.position['size']
                    self.balance += pnl
                    
                    trade_result = {
                        'entry_time': self.position['entry_time'], 'exit_time': current_candle.name,
                        'side': self.position['side'], 'size': self.position['size'],
                        'entry_price': self.position['entry_price'], 'exit_price': exit_price,
                        'pnl': pnl, 'reason': exit_reason, 'balance': self.balance
                    }
                    self.trades.append(trade_result)
                    logger.info(f"Simulating CLOSE: Reason={exit_reason}, Price={exit_price:.4f}, PnL=${pnl:,.2f}, New Balance=${self.balance:,.2f}")

                    self.in_position = False
                    self.position = {}

        logger.info("--- Backtest Finished ---")

    def generate_report(self):
        logger.info("--- Generating Backtest Report ---")
        if not self.trades:
            logger.warning("No trades were executed during the backtest.")
            return

        report_df = pd.DataFrame(self.trades)

        report_df['cumulative_pnl'] = report_df['pnl'].cumsum()
        report_df['equity_curve'] = self.initial_balance + report_df['cumulative_pnl']
        report_df['running_max'] = report_df['equity_curve'].cummax()
        report_df['drawdown'] = report_df['running_max'] - report_df['equity_curve']
        max_drawdown = report_df['drawdown'].max()
        max_drawdown_percent = (max_drawdown / report_df['running_max'].max()) * 100 if report_df['running_max'].max() > 0 else 0
        
        total_trades = len(report_df)
        winning_trades = report_df[report_df['pnl'] > 0]
        losing_trades = report_df[report_df['pnl'] <= 0]
        win_rate = (len(winning_trades) / total_trades) * 100 if total_trades > 0 else 0
        total_pnl = report_df['pnl'].sum()
        profit_factor = abs(winning_trades['pnl'].sum() / losing_trades['pnl'].sum()) if losing_trades['pnl'].sum() != 0 else float('inf')
        avg_win = winning_trades['pnl'].mean() if not winning_trades.empty else 0
        avg_loss = losing_trades['pnl'].mean() if not losing_trades.empty else 0

        print("\n" + "="*50)
        print(" " * 15 + "BACKTEST REPORT")
        print("="*50)
        print(f"Symbol: {self.symbol} | Timeframe: {self.timeframe}")
        print(f"Initial Balance: ${self.initial_balance:,.2f}")
        print(f"Final Balance:   ${self.balance:,.2f}")
        print(f"Total PnL:       ${total_pnl:,.2f} ({total_pnl/self.initial_balance*100:.2f}%)")
        print("-"*50)
        print(f"Total Trades:    {total_trades}")
        print(f"Win Rate:        {win_rate:.2f}%")
        print(f"Profit Factor:   {profit_factor:.2f}")
        print(f"Average Win:     ${avg_win:,.2f}")
        print(f"Average Loss:    ${avg_loss:,.2f}")
        print(f"Max Drawdown:    ${max_drawdown:,.2f} ({max_drawdown_percent:.2f}%)")
        print("="*50 + "\n")

        report_df.to_csv('logs/backtest_trades.csv', index=False)
        logger.info("Backtest trade log saved to logs/backtest_trades.csv")

if __name__ == "__main__":
    backtester = Backtester(
        initial_balance=config.INITIAL_BALANCE, 
        symbol=config.SYMBOL, 
        timeframe=config.TIMEFRAME
    )
    backtester.run()
    backtester.generate_report()