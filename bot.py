import threading
import time
import pandas as pd
import pandas_ta as ta
from decimal import Decimal, ROUND_DOWN
import logging

# --- Import các module của dự án ---
from modules.api_integration import OKXManager
from modules.ta_engine import TAEngine
from modules.risk_management import RiskManager
from modules.notification_manager import NotificationManager
from modules.database import DatabaseManager
from logging_config import configure_logging
import config

# --- Cấu hình logging và lấy logger cho module này ---
configure_logging()
logger = logging.getLogger(__name__)

class TradingBot:
    """
    Bot giao dịch phiên bản 2.1 - Tối ưu hóa xử lý song song.
    """
    
    def __init__(self):
        """Khởi tạo tất cả các thành phần cần thiết cho bot."""
        logger.info("Đang khởi tạo TradingBot (v2.1 - Parallel)...")
        self.managers = {
            'api': OKXManager(),
            'ta': TAEngine(),
            'risk': RiskManager(),
            'notify': NotificationManager()
        }
        self.symbols = config.SYMBOLS
        self.states = self._initialize_states()

        # BƯỚC 1: Tạo một "ổ khóa" để bảo vệ self.states khi nhiều thread cùng truy cập
        self.state_lock = threading.Lock()

        logger.info("TradingBot đã khởi tạo thành công các managers và lock.")

    def _initialize_states(self):
        states = {}
        for symbol in self.symbols:
            states[symbol] = {"in_position": False, "side": None, "entry_price": 0.0, "position_size": 0.0, "initial_stop_loss": 0.0, "trailing_stop_loss": 0.0}
        return states
    
    def _reset_symbol_state(self, state):
        state.update({"in_position": False, "side": None, "entry_price": 0.0, "position_size": 0.0, "initial_stop_loss": 0.0, "trailing_stop_loss": 0.0})
        return state

    def _get_usdt_balance(self):
        try:
            balance_details = self.managers['api'].get_account_balance()
            if balance_details:
                for currency in balance_details:
                    if currency.get('ccy') == 'USDT':
                        return float(currency.get('eq', 0))
            logger.warning("Không tìm thấy số dư USDT.")
            return None
        except Exception as e:
            logger.error(f"Không thể lấy số dư USDT: {e}", exc_info=True)
            return None

    def _synchronize_states(self):
        logger.info("===== BẮT ĐẦU ĐỒNG BỘ HÓA TRẠNG THÁI VỚI SÀN =====")
        for symbol in self.symbols:
            position_data = self.managers['api'].get_position(symbol)
            if position_data and float(position_data.get('pos', 0)) > 0:
                side = position_data.get('posSide')
                entry_price = float(position_data.get('avgPx'))
                pos_size = float(position_data.get('pos'))
                self.states[symbol].update({"in_position": True, "side": side, "entry_price": entry_price, "position_size": pos_size})
                logger.warning(f"[{symbol}] PHÁT HIỆN VỊ THẾ CÓ SẴN. Đồng bộ: Side={side}, Entry={entry_price}, Size={pos_size}")
                klines = self.managers['api'].get_klines(symbol, config.ENTRY_TIMEFRAMES[0], limit=200)
                if klines is not None and not klines.empty:
                    data = self.managers['ta'].calculate_all_indicators(klines)
                    current_atr = data.iloc[-1][config.ATR_COL]
                    if not pd.isna(current_atr):
                        recalculated_sl = self.managers['risk'].calculate_stop_loss(entry_price, current_atr, side)
                        self.states[symbol]['initial_stop_loss'] = recalculated_sl
                        self.states[symbol]['trailing_stop_loss'] = recalculated_sl
                        logger.warning(f"[{symbol}] SL không xác định. Tạm tính lại SL/TSL tại: {recalculated_sl:.4f}")
            else:
                logger.info(f"[{symbol}] Không có vị thế mở.")
        logger.info("===== KẾT THÚC ĐỒNG BỘ HÓA TRẠNG THÁI =====")

    def _handle_no_position(self, state, symbol, all_data, account_balance):
        """Xử lý logic vào lệnh dựa trên tín hiệu hội tụ."""
        trend_data = all_data['trend']
        entry_data_1m = all_data['entry']['1m']
        entry_data_5m = all_data['entry']['5m']

        if any(df.empty for df in [trend_data, entry_data_1m, entry_data_5m]):
            return
        
        price = entry_data_1m.iloc[-1]['close']
        trend_ma = trend_data.iloc[-1][config.TREND_MA_COL]
        rsi_1m = entry_data_1m.iloc[-1][config.RSI_COL]
        prev_rsi_1m = entry_data_1m.iloc[-2][config.RSI_COL]
        rsi_5m = entry_data_5m.iloc[-1][config.RSI_COL]
        
        is_uptrend = price > trend_ma
        is_pullback_long = rsi_5m < config.RSI_PULLBACK
        is_trigger_long = prev_rsi_1m < config.RSI_OVERSOLD and rsi_1m >= config.RSI_OVERSOLD
        
        side, posSide, order_side = None, None, None
        if is_uptrend and is_pullback_long and is_trigger_long:
            side, posSide, order_side = 'long', 'long', 'buy'
            logger.info(f"[{symbol}] Điều kiện LONG hội tụ: Trend Up, 5m Pullback (RSI={rsi_5m:.2f}), 1m Trigger (RSI={rsi_1m:.2f})")

        is_downtrend = price < trend_ma
        is_pullback_short = rsi_5m > config.RSI_PULLBACK_SELL
        is_trigger_short = prev_rsi_1m > config.RSI_OVERBOUGHT and rsi_1m <= config.RSI_OVERBOUGHT

        if is_downtrend and is_pullback_short and is_trigger_short:
            side, posSide, order_side = 'short', 'short', 'sell'
            logger.info(f"[{symbol}] Điều kiện SHORT hội tụ: Trend Down, 5m Pullback (RSI={rsi_5m:.2f}), 1m Trigger (RSI={rsi_1m:.2f})")
        
        if not side: return

        entry_price = price
        atr = entry_data_1m.iloc[-1][config.ATR_COL]
        if pd.isna(atr): return

        initial_sl = self.managers['risk'].calculate_stop_loss(entry_price, atr, side)
        contract_value = config.CONTRACT_VALUES.get(symbol)
        if not contract_value:
            logger.error(f"[{symbol}] Không tìm thấy CONTRACT_VALUE. Bỏ qua.")
            return

        size_contracts = self.managers['risk'].calculate_position_size(account_balance, entry_price, initial_sl, contract_value)
        if size_contracts <= 0: return

        size_str = str(Decimal(size_contracts).quantize(Decimal('0.0001'), rounding=ROUND_DOWN))
        order = self.managers['api'].place_order(instId=symbol, tdMode='cross', side=order_side, posSide=posSide, ordType=config.ORDER_TYPE, sz=size_str)
        
        if order and order.get('sCode') == '0':
            # BƯỚC 4: Dùng khóa để bảo vệ dữ liệu khi ghi
            with self.state_lock:
                state.update({"in_position": True, "side": side, "entry_price": entry_price, "position_size": float(size_str), "initial_stop_loss": initial_sl, "trailing_stop_loss": initial_sl})
            
            msg = f"✅ **ENTER {side.upper()}**\nSymbol: `{symbol}`\nPrice: `{entry_price:.4f}`\nInitial SL: `{initial_sl:.4f}`"
            self.managers['notify'].send_message(msg)
            logger.info(f"[{symbol}] Lệnh {side.upper()} đặt thành công.")

    def _handle_in_position(self, state, symbol, data_1m):
        """Xử lý logic quản lý và thoát lệnh, dùng khung 1m."""
        if data_1m.empty: return

        current_candle = data_1m.iloc[-1]
        atr = current_candle[config.ATR_COL]
        if not pd.isna(atr):
            # Cập nhật TSL không thay đổi state, chỉ trả về giá trị mới nên không cần khóa
            new_tsl = self.managers['risk'].update_trailing_stop(state["trailing_stop_loss"], current_candle['high'], current_candle['low'], atr, state['side'])
            if new_tsl != state["trailing_stop_loss"]:
                # Chỉ khi có sự thay đổi thực sự mới cần khóa để ghi
                with self.state_lock:
                    state["trailing_stop_loss"] = new_tsl
                logger.info(f"[{symbol}] TSL cho {state['side']} di chuyển đến {new_tsl:.4f}")

        close_reason, exit_price = None, 0
        if state['side'] == 'long' and current_candle['low'] <= state["trailing_stop_loss"]:
            close_reason, exit_price = 'TRAILING STOP', state["trailing_stop_loss"]
        elif state['side'] == 'short' and current_candle['high'] >= state["trailing_stop_loss"]:
            close_reason, exit_price = 'TRAILING STOP', state["trailing_stop_loss"]
        
        if not close_reason: return

        logger.warning(f"[{symbol}] TÍN HIỆU ĐÓNG LỆNH! Lý do: {close_reason}. Thực hiện đóng...")
        position_info = self.managers['api'].get_position(symbol)

        if position_info and float(position_info.get('pos', 0)) > 0:
            size_to_close = position_info['pos']
            close_side = 'sell' if state['side'] == 'long' else 'buy'
            close_order = self.managers['api'].place_order(instId=symbol, tdMode='cross', side=close_side, posSide=state['side'], ordType=config.ORDER_TYPE, sz=size_to_close)
            
            if close_order and close_order.get('sCode') == '0':
                pnl_multiplier = 1 if state['side'] == 'long' else -1
                contract_value = config.CONTRACT_VALUES.get(symbol, 0)
                pnl = (exit_price - state['entry_price']) * pnl_multiplier * float(size_to_close) * contract_value
                trade_data = {"symbol": symbol, "side": state['side'], "entry_price": state['entry_price'], "exit_price": exit_price, "stop_loss": state['initial_stop_loss'], "take_profit": 0, "pnl": pnl, "exit_reason": close_reason}
                
                with DatabaseManager() as db:
                    db.log_trade(trade_data)
                
                msg = f"⛔️ **CLOSED {state['side'].upper()}**\nSymbol: `{symbol}`\nExit Price: `{exit_price:.4f}`\nPnL (ước tính): `~${pnl:.2f}`"
                self.managers['notify'].send_message(msg)
                
                # BƯỚC 4: Dùng khóa để bảo vệ dữ liệu khi reset
                with self.state_lock:
                    self._reset_symbol_state(state)
                logger.info(f"[{symbol}] Lệnh đóng thành công. Reset trạng thái.")
        else:
            logger.warning(f"[{symbol}] Muốn đóng lệnh nhưng không tìm thấy vị thế trên sàn. Reset.")
            # BƯỚC 4: Dùng khóa để bảo vệ dữ liệu khi reset
            with self.state_lock:
                self._reset_symbol_state(state)

    def _process_single_symbol(self, symbol, account_balance):
        """Thực hiện toàn bộ chu trình xử lý cho một symbol duy nhất."""
        # Lấy bản sao của state để thread làm việc, tránh thay đổi trực tiếp
        with self.state_lock:
            state = self.states[symbol].copy()

        logger.debug(f"Đang xử lý [{symbol}]. Trạng thái: In Position = {state['in_position']}")
        
        try:
            trend_klines = self.managers['api'].get_klines(symbol, config.TREND_TIMEFRAME, limit=200)
            entry_klines_1m = self.managers['api'].get_klines(symbol, config.ENTRY_TIMEFRAMES[0], limit=200)
            entry_klines_5m = self.managers['api'].get_klines(symbol, config.ENTRY_TIMEFRAMES[1], limit=200)

            all_data = {}
            all_data['trend'] = self.managers['ta'].calculate_all_indicators(trend_klines) if trend_klines is not None and not trend_klines.empty else pd.DataFrame()
            if not all_data['trend'].empty:
                all_data['trend'][config.TREND_MA_COL] = ta.ema(all_data['trend']['close'], length=config.TREND_MA_PERIOD)

            all_data['entry'] = {
                '1m': self.managers['ta'].calculate_all_indicators(entry_klines_1m) if entry_klines_1m is not None and not entry_klines_1m.empty else pd.DataFrame(),
                '5m': self.managers['ta'].calculate_all_indicators(entry_klines_5m) if entry_klines_5m is not None and not entry_klines_5m.empty else pd.DataFrame()
            }
            
            if not state['in_position']:
                self._handle_no_position(state, symbol, all_data, account_balance)
            else:
                self._handle_in_position(state, symbol, all_data['entry']['1m'])
        except Exception as e:
            logger.error(f"Lỗi không mong muốn khi xử lý symbol [{symbol}]: {e}", exc_info=True)

    def run(self):
        """Hàm chính điều phối toàn bộ hoạt động của bot."""
        logger.info("================ BOT V2.1 LIVE STARTING (Parallel Concordance) ================")
        self.managers['notify'].send_message(f"🚀 **Bot v2.1 (Parallel) Started!** 🚀\nStrategy: Signal Concordance")
        self._synchronize_states()

        while True:
            try:
                logger.info("--- Bắt đầu chu kỳ kiểm tra mới ---")
                account_balance = self._get_usdt_balance()
                if account_balance is None or account_balance <= 0:
                    time.sleep(60); continue
                logger.info(f"Vốn chủ sở hữu hiện tại: ${account_balance:,.2f}")
                
                # BƯỚC 3: Xử lý song song
                threads = []
                for symbol in self.symbols:
                    # Tạo một thread mới cho mỗi symbol
                    thread = threading.Thread(
                        target=self._process_single_symbol, 
                        args=(symbol, account_balance)
                    )
                    threads.append(thread)
                    thread.start() # Bắt đầu chạy thread

                # Đợi cho tất cả các thread xử lý xong
                for thread in threads:
                    thread.join()

                logger.info(f"--- Chu kỳ hoàn tất. Chờ {config.CYCLE_DELAY_SECONDS} giây ---")
                time.sleep(config.CYCLE_DELAY_SECONDS)

            except KeyboardInterrupt:
                self.managers['notify'].send_message("Bot đã nhận lệnh dừng. Đang tắt...")
                logger.info("Bot đã nhận lệnh dừng. Đang tắt...")
                break
            except Exception as e:
                error_message = f"LỖI NGHIÊM TRỌNG: {e}"
                logger.error(error_message, exc_info=True)
                self.managers['notify'].send_message(f"🔥 **CRITICAL ERROR** 🔥\n`{error_message}`\nBot tạm dừng 60 giây.")
                time.sleep(60)

if __name__ == "__main__":
    bot = TradingBot()
    bot.run()
