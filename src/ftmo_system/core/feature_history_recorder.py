"""
Feature History Recorder
=========================
Append-only per-symbol log of the raw 27-feature snapshot taken each
trading cycle. Used to build fixed-length feature sequences
(data/feature_sequences/{trade_id}.npy) for sequence models
(LSTM/Transformer/CNN) once a trade's outcome is finalized.

CSV append (not parquet) — matches the rest of the codebase's
file-based logging (unified_trade_logger, EA CSVs) and survives
process restarts without needing an open writer handle.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

FEATURE_27 = [
    "close", "high", "low", "volume",
    "sma_20", "sma_50", "fast_ema", "slow_ema",
    "htf_fast_ema", "htf_slow_ema", "htf_trend_direction", "htf_trend_alignment",
    "rsi", "stoch_k", "stoch_d", "momentum",
    "atr", "bb_upper", "bb_middle", "bb_lower", "volatility",
    "volume_sma", "volume_ratio", "price_volume",
    "bullish_sentiment", "bearish_sentiment", "net_sentiment",
]

HISTORY_COLUMNS = ["timestamp"] + FEATURE_27

SEQUENCE_LENGTH = 50


class FeatureHistoryRecorder:
    """One CSV per symbol under data/feature_history/."""

    def __init__(self, history_dir: str):
        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, symbol: str) -> Path:
        return self.history_dir / f"{symbol}.csv"

    def append(self, symbol: str, base_features: np.ndarray, timestamp: datetime = None):
        """Append one 27-feature snapshot for `symbol`."""
        if base_features is None or len(base_features) != len(FEATURE_27):
            return
        ts = (timestamp or datetime.now(timezone.utc)).isoformat()
        row = {"timestamp": ts}
        row.update({name: float(val) for name, val in zip(FEATURE_27, base_features)})

        path = self._path(symbol)
        try:
            df = pd.DataFrame([row], columns=HISTORY_COLUMNS)
            if not path.exists():
                df.to_csv(path, index=False)
            else:
                df.to_csv(path, mode="a", header=False, index=False)
        except Exception as e:
            logger.error(f"[FEATURE_HISTORY] append failed for {symbol}: {e}")

    def get_sequence(self, symbol: str, before: datetime, length: int = SEQUENCE_LENGTH) -> np.ndarray:
        """
        Return the last `length` feature snapshots strictly before `before`,
        as a (length, 27) array. Returns None if insufficient history.
        """
        path = self._path(symbol)
        if not path.exists():
            return None
        try:
            df = pd.read_csv(path)
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            before_ts = pd.Timestamp(before)
            if before_ts.tzinfo is None:
                before_ts = before_ts.tz_localize(timezone.utc)
            else:
                before_ts = before_ts.tz_convert(timezone.utc)
            df = df[df["timestamp"] < before_ts]
            if len(df) < length:
                return None
            tail = df.tail(length)
            return tail[FEATURE_27].to_numpy(dtype=np.float32)
        except Exception as e:
            logger.error(f"[FEATURE_HISTORY] get_sequence failed for {symbol}: {e}")
            return None
