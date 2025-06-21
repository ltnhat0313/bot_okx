# File: modules/risk_management.py (PHIÊN BẢN HOÀN THIỆN)

import logging
import math
import pandas as pd # <-- THÊM DÒNG IMPORT CÒN THIẾU

logger = logging.getLogger(__name__)

class RiskManagement:
    def __init__(self, balance: float, risk_per_trade_percent: float, stop_loss_atr_multiplier: float, take_profit_atr_multiplier: float):
        self.balance = balance
        self.risk_per_trade_percent = risk_per_trade_percent
        self.stop_loss_atr_multiplier = stop_loss_atr_multiplier
        self.take_profit_atr_multiplier = take_profit_atr_multiplier
        self.logger = logging.getLogger(__name__)

    def get_trade_params(self, latest_candle: pd.Series, side: str) -> dict:
        """
        Tính toán các tham số giao dịch (Stop Loss và Take Profit) cho một lệnh.
        :param latest_candle: Cây nến hiện tại để tính toán ATR và giá vào lệnh.
        :param side: Phía vào lệnh ('buy' hoặc 'sell')
        :return: Dictionary chứa các tham số như entry, sl, tp. Hoặc dict rỗng nếu lỗi.
        """
        # Sử dụng .get() để an toàn hơn, tránh lỗi KeyError nếu cột không tồn tại
        atr = latest_candle.get('ATRr_14', 0)
        entry_price = latest_candle.get('c')

        if entry_price is None:
            self.logger.warning("Could not find close price ('c') in candle data.")
            return {}

        # Kiểm tra giá trị ATR hợp lệ
        if atr is None or atr == 0 or pd.isna(atr):
            self.logger.warning(f"ATR value is invalid ({atr}). Cannot calculate SL/TP.")
            return {}

        # Tính toán Stop Loss và Take Profit
        if side == 'buy':
            stop_loss = entry_price - (atr * self.stop_loss_atr_multiplier)
            take_profit = entry_price + (atr * self.take_profit_atr_multiplier)
        elif side == 'sell':
            stop_loss = entry_price + (atr * self.stop_loss_atr_multiplier)
            take_profit = entry_price - (atr * self.tp_multiplier)
        else:
            self.logger.warning(f"Invalid side '{side}' provided. Cannot calculate SL/TP.")
            return {}
        
        return {
            'entry': entry_price,
            'sl': stop_loss,
            'tp': take_profit
        }

    def get_position_size(self, entry_price: float, stop_loss_price: float, lot_size: float) -> float:
        """
        Tính toán khối lượng giao dịch dựa trên % rủi ro và làm tròn xuống theo lot_size.
        :param entry_price: Giá vào lệnh (entry price)
        :param stop_loss_price: Giá stop loss
        :param lot_size: Số lot nhỏ nhất của sàn giao dịch
        :return: Khối lượng giao dịch tối ưu
        """
        risk_amount = self.balance * (self.risk_per_trade_percent / 100)
        price_diff = abs(entry_price - stop_loss_price)
        
        if price_diff == 0:
            self.logger.warning("Price difference is zero, cannot calculate position size.")
            return 0
        
        raw_size = risk_amount / price_diff

        if lot_size > 0:
            # Làm tròn xuống bội số gần nhất của lot_size
            adjusted_size = math.floor(raw_size / lot_size) * lot_size
            self.logger.info(f"Risk Calc: Balance=${self.balance:,.2f}, Risk=${risk_amount:,.2f}, Raw Size={raw_size:.4f}, Adjusted Size={adjusted_size:.4f}, Lot Size={lot_size}")
            return adjusted_size
        
        self.logger.warning("Lot size is zero, cannot calculate position size.")
        return 0