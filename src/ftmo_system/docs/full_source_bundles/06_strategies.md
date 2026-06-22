# Source Bundle: docs/full_source_bundles/06_strategies.md


---

## `core/strategies/__init__.py`

```py
from .base_strategy import BaseStrategy
from .sma_3crossover import SMA3CrossoverStrategy
from .tema_barrington import TEMABarringtonStrategy
from .ama_scalper import AMAScalperStrategy
from .sma_price_cross import SMAPriceCrossStrategy
from .dema_rsi_hf import DEMARSIHighFreqStrategy
from .dema_supertrend import DEMASuperTrendStrategy

__all__ = [
    "BaseStrategy",
    "SMA3CrossoverStrategy",
    "TEMABarringtonStrategy",
    "AMAScalperStrategy",
    "SMAPriceCrossStrategy",
    "DEMARSIHighFreqStrategy",
    "DEMASuperTrendStrategy",
]

```

---

## `core/strategies/base_strategy.py`

```py
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

```

---

## `core/strategies/sma_3crossover.py`

```py
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

```

---

## `core/strategies/sma_price_cross.py`

```py
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

```

---

## `core/strategies/tema_barrington.py`

```py
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

```

---

## `core/strategies/ama_scalper.py`

```py
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

```

---

## `core/strategies/dema_rsi_hf.py`

```py
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

```

---

## `core/strategies/dema_supertrend.py`

```py
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

```
