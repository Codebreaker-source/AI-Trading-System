"""
HA-MAMA — SMA Price Cross Strategy
=====================================
Translation of HA-MAMA.mq5

Signal:
  BUY  — Price closes above SMA(12)  (previous close was below)
  SELL — Price closes below SMA(12)  (previous close was above)

Trailing: SMA(12) trailing
SL: 50 points | TP: 50 points | Lot: 0.01
"""

from typing import Optional
import pandas as pd
from .base_strategy import BaseStrategy


class SMAPriceCrossStrategy(BaseStrategy):

    def __init__(self, period: int = 12,
                 sl_points: int = 50, tp_points: int = 50, lot: float = 0.01):
        super().__init__(sl_points=sl_points, tp_points=tp_points, lot=lot)
        self.period = period

    @property
    def name(self) -> str:
        return "sma_price_cross"

    def generate_signal(self, symbol: str, ohlcv: pd.DataFrame,
                        point: float = BaseStrategy.DEFAULT_POINT) -> Optional[dict]:
        if len(ohlcv) < self.period + 2:
            return None

        close   = ohlcv["close"]
        sma_line = self.sma(close, self.period)

        if sma_line.isna().iloc[-1]:
            return None

        indicators = {
            "sma":   round(float(sma_line.iloc[-1]), 6),
            "close": round(float(close.iloc[-1]),    6),
        }

        if self._price_cross_up(close, sma_line):
            return self._signal_dict("BUY", indicators)

        if self._price_cross_down(close, sma_line):
            return self._signal_dict("SELL", indicators)

        return None
