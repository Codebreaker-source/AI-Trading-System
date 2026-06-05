"""
TV SuperTrend — DEMA Strategy
================================
Translation of tv sssupertrend.mq5

Signal:
  BUY  — Price crosses above DEMA(12)
  SELL — Price crosses below DEMA(12)

Trailing: Fixed pips (SL trail 30 pts, TP trail 50 pts — EA-managed)
SL: 50 points | TP: 50 points | Lot: 0.01
"""

from typing import Optional
import pandas as pd
from .base_strategy import BaseStrategy


class DEMASuperTrendStrategy(BaseStrategy):

    def __init__(self, dema_period: int = 12,
                 sl_points: int = 50, tp_points: int = 50, lot: float = 0.01):
        super().__init__(sl_points=sl_points, tp_points=tp_points, lot=lot)
        self.dema_period = dema_period

    @property
    def name(self) -> str:
        return "dema_supertrend"

    def generate_signal(self, symbol: str, ohlcv: pd.DataFrame,
                        point: float = BaseStrategy.DEFAULT_POINT) -> Optional[dict]:
        min_bars = self.dema_period * 2 + 2
        if len(ohlcv) < min_bars:
            return None

        close     = ohlcv["close"]
        dema_line = self.dema(close, self.dema_period)

        if dema_line.isna().iloc[-1]:
            return None

        indicators = {
            "dema":  round(float(dema_line.iloc[-1]), 6),
            "close": round(float(close.iloc[-1]),    6),
        }

        if self._price_cross_up(close, dema_line):
            return self._signal_dict("BUY", indicators)

        if self._price_cross_down(close, dema_line):
            return self._signal_dict("SELL", indicators)

        return None
