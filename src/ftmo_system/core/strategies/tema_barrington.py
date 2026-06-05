"""
Barrington's TEMA Strategy
===========================
Translation of barrington's sma strategy.mq5

Signal:
  BUY  — Price closes above TEMA(12)  (previous close was below)
  SELL — Price closes below TEMA(12)  (previous close was above)

Trailing: SMA(8) trailing (position management only — not replicated here)
SL: 50 points | TP: 50 points | Lot: 0.01
"""

from typing import Optional
import pandas as pd
from .base_strategy import BaseStrategy


class TEMABarringtonStrategy(BaseStrategy):

    def __init__(self, tema_period: int = 12, trail_period: int = 8,
                 sl_points: int = 50, tp_points: int = 50, lot: float = 0.01):
        super().__init__(sl_points=sl_points, tp_points=tp_points, lot=lot)
        self.tema_period = tema_period
        self.trail_period = trail_period

    @property
    def name(self) -> str:
        return "tema_barrington"

    def generate_signal(self, symbol: str, ohlcv: pd.DataFrame,
                        point: float = BaseStrategy.DEFAULT_POINT) -> Optional[dict]:
        min_bars = self.tema_period * 3 + 2
        if len(ohlcv) < min_bars:
            return None

        close = ohlcv["close"]
        tema_line = self.tema(close, self.tema_period)
        trail_ma  = self.sma(close, self.trail_period)

        if tema_line.isna().iloc[-1]:
            return None

        indicators = {
            "tema":      round(float(tema_line.iloc[-1]), 6),
            "trail_sma": round(float(trail_ma.iloc[-1]),  6),
            "close":     round(float(close.iloc[-1]),      6),
        }

        if self._price_cross_up(close, tema_line):
            return self._signal_dict("BUY", indicators)

        if self._price_cross_down(close, tema_line):
            return self._signal_dict("SELL", indicators)

        return None
