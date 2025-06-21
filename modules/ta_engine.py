import pandas as pd
import pandas_ta as ta
import logging
from typing import Tuple, Optional, Dict, Any

logger = logging.getLogger(__name__)

class TAEngine:
    def __init__(self):
        self.rsi_period = 14
        self.ema_short_period = 12
        self.ema_long_period = 26
        self.atr_period = 14

    def calculate_indicators(self, klines_df: pd.DataFrame) -> pd.DataFrame:
        """
        Tính toán và thêm các chỉ báo vào DataFrame.
        Chỉ định rõ các cột 'h', 'l', 'c' cho pandas-ta.
        """
        if klines_df.empty:
            return klines_df

        # Tính các chỉ báo kỹ thuật
        klines_df.ta.rsi(length=self.rsi_period, close='c', append=True)
        klines_df.ta.ema(length=self.ema_short_period, close='c', append=True)
        klines_df.ta.ema(length=self.ema_long_period, close='c', append=True)
        klines_df.ta.atr(length=self.atr_period, high='h', low='l', close='c', append=True)
        
        return klines_df

    def calculate_technical_score(self, klines_data: Dict[str, Any]) -> Tuple[float, Optional[pd.DataFrame]]:
        if not klines_data or 'data' not in klines_data or not klines_data['data']:
            logger.warning("No klines data to analyze.")
            return 0.0, None

        # Định nghĩa các cột của dữ liệu lịch sử
        columns = ['ts', 'o', 'h', 'l', 'c', 'vol', 'volCcy', 'volCcyQuote', 'confirm']
        df = pd.DataFrame(klines_data['data'], columns=columns)
        
        # Chuyển đổi thời gian từ milliseconds sang datetime
        df['ts'] = pd.to_numeric(df['ts'])
        df['ts'] = pd.to_datetime(df['ts'], unit='ms')
        
        df.set_index('ts', inplace=True)
        df = df.astype(float).sort_index()

        # Tính toán các chỉ báo kỹ thuật (RSI, EMA, ATR)
        df = self.calculate_indicators(df)
        if df.empty or len(df) < self.ema_long_period:
            logger.warning("Not enough data to calculate indicators.")
            return 0.0, None

        latest = df.iloc[-1]
        score = 0.0

        # Tính điểm cho chiến lược giao dịch (RSI, EMA)
        if latest['EMA_12'] > latest['EMA_26']:
            score += 6
        else:
            score -= 6
        
        if latest['RSI_14'] < 30:
            score += 4
        elif latest['RSI_14'] > 70:
            score -= 4

        logger.info(f"TA Score Calculated: {score:.2f} (RSI: {latest['RSI_14']:.2f}, EMA_12: {latest['EMA_12']:.2f})")
        return score, df
