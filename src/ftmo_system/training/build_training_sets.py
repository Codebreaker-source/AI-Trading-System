"""
Per-Symbol Price-Action Training Set Builder
=============================================
Builds ML training data the SAME way the 8 original pretrained XGBoost
models were built (src/lite/training/data_labeler_CLEAN27.py):

  - Forward window = 24 rows (M15 candles -> 6 hours)
  - Label = BUY if forward max gain >= 20 pips (and max loss < 20 pips)
            SELL if forward max loss >= 20 pips (and max gain < 20 pips)
            HOLD otherwise
  - Row i is labeled using rows i+1 .. i+FORWARD_CANDLES (no lookahead
    into row i's own future close)

Labels are derived PURELY from price action in
data/feature_history/{SYMBOL}.csv (Phase 4 recorder) — never from any
signal source's trade outcomes. Every ML model type (XGBoost, LightGBM,
CatBoost, Transformer) trains on this SAME per-symbol label set
independently; diversification comes from differing model architectures,
not differing label sources. Rule-based strategies are not retrained and
never contribute to this data.

Output: data/training_sets/{SYMBOL}_tabular.parquet
  - feat_<name> columns (27 raw features, FEATURE_27 order)
  - label  (0=SELL, 1=HOLD, 2=BUY)
  - weight (always 1.0 — price-action labels have no execution-based weighting)
  - timestamp

Run on a schedule (daily, before retraining) or manually:
    python training/build_training_sets.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.feature_history_recorder import FEATURE_27  # noqa: E402
from core.trade_outcome_simulator import _pip_value  # noqa: E402

logger = logging.getLogger(__name__)

FEATURE_HISTORY_DIR = BASE_DIR / "data" / "feature_history"
TRAINING_SETS_DIR = BASE_DIR / "data" / "training_sets"

FORWARD_CANDLES = 24   # 6 hours on M15 — matches data_labeler_CLEAN27.py
PIP_THRESHOLD = 20     # 20 pips — matches data_labeler_CLEAN27.py

LABEL_SELL, LABEL_HOLD, LABEL_BUY = 0, 1, 2


def label_symbol(close_prices: np.ndarray, threshold: float) -> np.ndarray:
    """Forward-window pip-threshold labeling, identical to data_labeler_CLEAN27.label_pair()."""
    n = len(close_prices)
    labels = np.full(n, LABEL_HOLD, dtype=int)

    for i in range(n - FORWARD_CANDLES):
        current_price = close_prices[i]
        future_prices = close_prices[i + 1: i + 1 + FORWARD_CANDLES]

        max_gain = np.max(future_prices) - current_price
        max_loss = current_price - np.min(future_prices)

        if max_gain >= threshold and max_loss < threshold:
            labels[i] = LABEL_BUY
        elif max_loss >= threshold and max_gain < threshold:
            labels[i] = LABEL_SELL
        # else stays HOLD

    return labels


def _resample_to_m15(df: pd.DataFrame) -> pd.DataFrame:
    """
    feature_history rows are recorded every ~15s (one per main loop cycle),
    not per M15 candle. Resample to M15 bars (last snapshot in each 15-minute
    bucket) so FORWARD_CANDLES=24 actually represents 6 hours, matching the
    original data_labeler_CLEAN27.py methodology.
    """
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.set_index("timestamp").resample("15min").last().dropna().reset_index()
    return df


def build_training_sets(history_dir: Path = FEATURE_HISTORY_DIR,
                         min_rows: int = 50) -> dict:
    """Returns a summary dict: {symbol: n_rows}."""
    if not history_dir.exists():
        logger.warning(f"{history_dir} not found")
        return {}

    summary = {}

    for path in sorted(history_dir.glob("*.csv")):
        symbol = path.stem
        try:
            df = pd.read_csv(path)
        except Exception as e:
            logger.error(f"Failed to read {path}: {e}")
            continue

        if "close" not in df.columns:
            continue

        df = df.sort_values("timestamp").reset_index(drop=True)
        df = _resample_to_m15(df)

        if len(df) <= FORWARD_CANDLES:
            continue

        threshold = PIP_THRESHOLD * _pip_value(symbol)
        labels = label_symbol(df["close"].to_numpy(dtype=np.float64), threshold)

        # Drop the trailing rows that have no full forward window
        usable = df.iloc[: len(df) - FORWARD_CANDLES].copy()
        usable["label"] = labels[: len(usable)]

        if len(usable) < min_rows:
            continue

        feat_cols = {f"feat_{name}": usable[name].astype(np.float32) for name in FEATURE_27}
        out_df = pd.DataFrame(feat_cols)
        out_df["label"] = usable["label"].values.astype(int)
        out_df["weight"] = 1.0
        out_df["timestamp"] = usable["timestamp"].values

        TRAINING_SETS_DIR.mkdir(parents=True, exist_ok=True)
        out_path = TRAINING_SETS_DIR / f"{symbol}_tabular.parquet"
        out_df.to_parquet(out_path, index=False)
        summary[symbol] = len(out_df)

        dist = pd.Series(out_df["label"]).value_counts().sort_index()
        logger.info(
            f"[BUILD] {symbol}: {len(out_df)} rows -> {out_path}  "
            f"SELL={dist.get(0,0)} HOLD={dist.get(1,0)} BUY={dist.get(2,0)}"
        )

    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result = build_training_sets()
    total = sum(result.values())
    logger.info(f"=== Built {len(result)} symbol training set(s), {total} total rows ===")
