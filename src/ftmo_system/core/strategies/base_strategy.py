"""
Base class for all EA-translated Python strategies.
Each strategy receives OHLCV history and returns a signal dict.
"""

from abc import ABC, abstractmethod
from typing import Optional
import numpy as np
import pandas as pd


class BaseStrategy(ABC):
    """
    All strategies implement this interface.
    Signal sources are named; the name appears in the unified trade record.
    """

    # Points to price conversion — 5-digit pairs use _Point = 0.00001
    # Passed at runtime from symbol info
    DEFAULT_POINT = 0.00001

    def __init__(self, sl_points: int = 30, tp_points: int = 60, lot: float = 0.01):
        self.sl_points = sl_points
        self.tp_points = tp_points
        self.lot = lot

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique strategy identifier used in unified trade record."""
        ...

    @abstractmethod
    def generate_signal(
        self,
        symbol: str,
        ohlcv: pd.DataFrame,
        point: float = DEFAULT_POINT,
    ) -> Optional[dict]:
        """
        Generate a trading signal.

        Args:
            symbol: e.g. 'EURUSD.sim'
            ohlcv: DataFrame with columns [open, high, low, close, tick_volume]
                   Most recent bar is LAST row. Minimum 55 bars recommended.
            point: Pip/point size for this symbol.

        Returns:
            None if no signal, else:
            {
                'action':     'BUY' | 'SELL',
                'sl_points':  int,
                'tp_points':  int,
                'lot':        float,
                'indicators': dict   # key indicator values for logging
            }
        """
        ...

    # ------------------------------------------------------------------
    # Shared indicator helpers
    # ------------------------------------------------------------------

    @staticmethod
    def ema(series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def sma(series: pd.Series, period: int) -> pd.Series:
        return series.rolling(period).mean()

    @staticmethod
    def dema(series: pd.Series, period: int) -> pd.Series:
        e1 = series.ewm(span=period, adjust=False).mean()
        e2 = e1.ewm(span=period, adjust=False).mean()
        return 2 * e1 - e2

    @staticmethod
    def tema(series: pd.Series, period: int) -> pd.Series:
        e1 = series.ewm(span=period, adjust=False).mean()
        e2 = e1.ewm(span=period, adjust=False).mean()
        e3 = e2.ewm(span=period, adjust=False).mean()
        return 3 * e1 - 3 * e2 + e3

    @staticmethod
    def rsi(series: pd.Series, period: int) -> pd.Series:
        delta = series.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def ama(series: pd.Series, period: int = 10, fast: int = 2, slow: int = 30) -> pd.Series:
        """Kaufman Adaptive Moving Average."""
        fast_sc = 2 / (fast + 1)
        slow_sc = 2 / (slow + 1)
        result = series.copy()
        for i in range(period, len(series)):
            direction = abs(series.iloc[i] - series.iloc[i - period])
            volatility = sum(abs(series.iloc[j] - series.iloc[j - 1]) for j in range(i - period + 1, i + 1))
            er = direction / volatility if volatility != 0 else 0
            sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2
            result.iloc[i] = result.iloc[i - 1] + sc * (series.iloc[i] - result.iloc[i - 1])
        return result

    def _signal_dict(self, action: str, indicators: dict) -> dict:
        return {
            "action":    action,
            "sl_points": self.sl_points,
            "tp_points": self.tp_points,
            "lot":       self.lot,
            "indicators": indicators,
        }

    def _cross_up(self, fast: pd.Series, slow: pd.Series) -> bool:
        """True if fast crossed above slow on the last completed bar."""
        return float(fast.iloc[-2]) < float(slow.iloc[-2]) and float(fast.iloc[-1]) > float(slow.iloc[-1])

    def _cross_down(self, fast: pd.Series, slow: pd.Series) -> bool:
        return float(fast.iloc[-2]) > float(slow.iloc[-2]) and float(fast.iloc[-1]) < float(slow.iloc[-1])

    def _price_cross_up(self, price: pd.Series, line: pd.Series) -> bool:
        return float(price.iloc[-2]) < float(line.iloc[-2]) and float(price.iloc[-1]) > float(line.iloc[-1])

    def _price_cross_down(self, price: pd.Series, line: pd.Series) -> bool:
        return float(price.iloc[-2]) > float(line.iloc[-2]) and float(price.iloc[-1]) < float(line.iloc[-1])
