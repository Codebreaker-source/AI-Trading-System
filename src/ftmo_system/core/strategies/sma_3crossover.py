"""
SMA 3-Crossover Strategy
========================
Translation of SMA_3Crossover.mq5

Signal:
  BUY  — Fast(8) crosses above Mid(20) AND Mid > Slow(50)
  SELL — Fast(8) crosses below Mid(20) AND Mid < Slow(50)

Trailing: handled by EA (not replicated here — signal only)
SL: 30 points | TP: 60 points | Lot: 0.01
"""

from typing import Optional
import pandas as pd
from .base_strategy import BaseStrategy


class SMA3CrossoverStrategy(BaseStrategy):

    def __init__(self, fast: int = 8, mid: int = 20, slow: int = 50,
                 sl_points: int = 30, tp_points: int = 60, lot: float = 0.01):
        super().__init__(sl_points=sl_points, tp_points=tp_points, lot=lot)
        self.fast = fast
        self.mid = mid
        self.slow = slow

    @property
    def name(self) -> str:
        return "sma_3crossover"

    def generate_signal(self, symbol: str, ohlcv: pd.DataFrame,
                        point: float = BaseStrategy.DEFAULT_POINT) -> Optional[dict]:
        if len(ohlcv) < self.slow + 2:
            return None

        close = ohlcv["close"]
        fast_ma = self.sma(close, self.fast)
        mid_ma  = self.sma(close, self.mid)
        slow_ma = self.sma(close, self.slow)

        if fast_ma.isna().iloc[-1] or slow_ma.isna().iloc[-1]:
            return None

        indicators = {
            "fast_sma": round(float(fast_ma.iloc[-1]), 6),
            "mid_sma":  round(float(mid_ma.iloc[-1]),  6),
            "slow_sma": round(float(slow_ma.iloc[-1]), 6),
        }

        # BUY: fast crosses above mid AND mid > slow
        if self._cross_up(fast_ma, mid_ma) and float(mid_ma.iloc[-1]) > float(slow_ma.iloc[-1]):
            return self._signal_dict("BUY", indicators)

        # SELL: fast crosses below mid AND mid < slow
        if self._cross_down(fast_ma, mid_ma) and float(mid_ma.iloc[-1]) < float(slow_ma.iloc[-1]):
            return self._signal_dict("SELL", indicators)

        return None
