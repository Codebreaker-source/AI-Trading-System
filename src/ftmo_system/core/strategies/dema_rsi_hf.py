"""
High Frequency — DEMA + RSI Strategy
=======================================
Translation of high frequency.mq5

Signal:
  BUY  — Price crosses above DEMA(12) AND RSI(8) < 50 (oversold momentum)
  SELL — Price crosses below DEMA(12) AND RSI(8) > 50 (overbought momentum)

Trailing: Fixed pips (SL trail 30 pts, TP trail 50 pts — EA-managed)
SL: 50 points | TP: 50 points | Lot: 0.01
Sizing: reduces after losses (tracked externally if needed)
"""

from typing import Optional
import pandas as pd
from .base_strategy import BaseStrategy


class DEMARSIHighFreqStrategy(BaseStrategy):

    def __init__(self, dema_period: int = 12, rsi_period: int = 8,
                 sl_points: int = 50, tp_points: int = 50, lot: float = 0.01):
        super().__init__(sl_points=sl_points, tp_points=tp_points, lot=lot)
        self.dema_period = dema_period
        self.rsi_period  = rsi_period

    @property
    def name(self) -> str:
        return "dema_rsi_hf"

    def generate_signal(self, symbol: str, ohlcv: pd.DataFrame,
                        point: float = BaseStrategy.DEFAULT_POINT) -> Optional[dict]:
        min_bars = max(self.dema_period * 2, self.rsi_period) + 3
        if len(ohlcv) < min_bars:
            return None

        close     = ohlcv["close"]
        dema_line = self.dema(close, self.dema_period)
        rsi_line  = self.rsi(close, self.rsi_period)

        if dema_line.isna().iloc[-1] or rsi_line.isna().iloc[-1]:
            return None

        rsi_val  = float(rsi_line.iloc[-1])
        indicators = {
            "dema":  round(float(dema_line.iloc[-1]), 6),
            "rsi":   round(rsi_val, 2),
            "close": round(float(close.iloc[-1]),    6),
        }

        if self._price_cross_up(close, dema_line) and rsi_val < 50:
            return self._signal_dict("BUY", indicators)

        if self._price_cross_down(close, dema_line) and rsi_val > 50:
            return self._signal_dict("SELL", indicators)

        return None
