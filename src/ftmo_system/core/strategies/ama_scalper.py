"""
MA Scalper 2 — Kaufman AMA Strategy
=====================================
Translation of mascalper2.mq5

Signal:
  BUY  — Price crosses above AMA(10, fast=2, slow=30)
  SELL — Price crosses below AMA(10, fast=2, slow=30)

Trailing: SMA(12) trailing
SL: 50 points | TP: 50 points | Lot: 0.01
"""

from typing import Optional
import pandas as pd
from .base_strategy import BaseStrategy


class AMAScalperStrategy(BaseStrategy):

    def __init__(self, period: int = 10, fast: int = 2, slow: int = 30,
                 trail_period: int = 12,
                 sl_points: int = 50, tp_points: int = 50, lot: float = 0.01):
        super().__init__(sl_points=sl_points, tp_points=tp_points, lot=lot)
        self.period     = period
        self.fast       = fast
        self.slow       = slow
        self.trail_period = trail_period

    @property
    def name(self) -> str:
        return "ama_scalper"

    def generate_signal(self, symbol: str, ohlcv: pd.DataFrame,
                        point: float = BaseStrategy.DEFAULT_POINT) -> Optional[dict]:
        if len(ohlcv) < self.period + self.slow + 2:
            return None

        close    = ohlcv["close"]
        ama_line = self.ama(close, self.period, self.fast, self.slow)
        trail_ma = self.sma(close, self.trail_period)

        if ama_line.isna().iloc[-1]:
            return None

        indicators = {
            "ama":       round(float(ama_line.iloc[-1]), 6),
            "trail_sma": round(float(trail_ma.iloc[-1]), 6),
            "close":     round(float(close.iloc[-1]),    6),
        }

        if self._price_cross_up(close, ama_line):
            return self._signal_dict("BUY", indicators)

        if self._price_cross_down(close, ama_line):
            return self._signal_dict("SELL", indicators)

        return None
