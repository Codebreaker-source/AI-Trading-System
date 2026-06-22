"""
Labeling — All Dukascopy Symbols (Price-Action, Same Methodology as the
Original 8 Pretrained Models)
=========================================================================
Reads data/historical_data/features/{SYMBOL}_features.parquet (M15 bars,
27 CLEAN features), applies the proven 24-candle / 20-pip forward-window
labeling (SELL=0, HOLD=1, BUY=2), and writes per-symbol stratified
train/val/test splits.

Threshold is category-aware via _pip_value() (forex 0.0001, JPY 0.01,
metals 0.01, indices/crypto/energy 1.0) — same helper used by the live
build_training_sets.py, so all symbols use one consistent, already-reviewed
methodology. Symbols whose resulting label distribution is degenerate
(>95% one class, or any class at 0%) are flagged in the summary but still
produce a model — diversification across model types means a skewed XGBoost
label set is not fatal (e.g. EURGBP was already heavily skewed historically).

Output: data/historical_data/splits/{SYMBOL}_{train,val,test}.parquet
  columns: feat_<name> (27) + label + weight

Run: python training/label_dukascopy_all.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.feature_history_recorder import FEATURE_27  # noqa: E402
from core.trade_outcome_simulator import _pip_value  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

FEATURES_DIR = BASE_DIR / "data" / "historical_data" / "features"
SPLITS_DIR = BASE_DIR / "data" / "historical_data" / "splits"

FORWARD_CANDLES = 24   # 6 hours on M15
PIP_THRESHOLD = 20

LABEL_SELL, LABEL_HOLD, LABEL_BUY = 0, 1, 2

TRAIN_RATIO, VAL_RATIO, TEST_RATIO = 0.70, 0.15, 0.15
DEGENERATE_PCT = 0.95


def label_symbol(close_prices: np.ndarray, threshold: float) -> np.ndarray:
    n = len(close_prices)
    labels = np.full(n, LABEL_HOLD, dtype=int)

    for i in range(n - FORWARD_CANDLES):
        current = close_prices[i]
        future = close_prices[i + 1: i + 1 + FORWARD_CANDLES]
        max_gain = np.max(future) - current
        max_loss = current - np.min(future)

        if max_gain >= threshold and max_loss < threshold:
            labels[i] = LABEL_BUY
        elif max_loss >= threshold and max_gain < threshold:
            labels[i] = LABEL_SELL

    return labels


def main():
    SPLITS_DIR.mkdir(parents=True, exist_ok=True)

    summary = []

    for path in sorted(FEATURES_DIR.glob("*_features.parquet")):
        symbol = path.stem.replace("_features", "")
        df = pd.read_parquet(path)
        df = df.sort_values("timestamp").reset_index(drop=True)

        if len(df) <= FORWARD_CANDLES:
            logger.warning(f"[{symbol}] too few rows ({len(df)}) — skipping")
            continue

        threshold = PIP_THRESHOLD * _pip_value(symbol)
        labels = label_symbol(df["close"].to_numpy(dtype=np.float64), threshold)

        usable = df.iloc[: len(df) - FORWARD_CANDLES].copy()
        usable["label"] = labels[: len(usable)]

        feat_cols = {f"feat_{name}": usable[name].astype(np.float32) for name in FEATURE_27}
        out_df = pd.DataFrame(feat_cols)
        out_df["label"] = usable["label"].values.astype(int)
        out_df["weight"] = 1.0

        dist = out_df["label"].value_counts(normalize=True).reindex([0, 1, 2], fill_value=0.0)
        counts = out_df["label"].value_counts().reindex([0, 1, 2], fill_value=0)
        degenerate = (dist.max() > DEGENERATE_PCT) or (dist.min() == 0.0)

        # Stratified 70/15/15 split
        try:
            train_df, temp_df = train_test_split(
                out_df, test_size=(VAL_RATIO + TEST_RATIO),
                stratify=out_df["label"], random_state=42, shuffle=True,
            )
            val_ratio_of_temp = TEST_RATIO / (VAL_RATIO + TEST_RATIO)
            val_df, test_df = train_test_split(
                temp_df, test_size=val_ratio_of_temp,
                stratify=temp_df["label"], random_state=42, shuffle=True,
            )
        except ValueError:
            train_df, temp_df = train_test_split(
                out_df, test_size=(VAL_RATIO + TEST_RATIO), random_state=42, shuffle=True,
            )
            val_df, test_df = train_test_split(temp_df, test_size=0.5, random_state=42, shuffle=True)

        train_df.to_parquet(SPLITS_DIR / f"{symbol}_train.parquet", index=False)
        val_df.to_parquet(SPLITS_DIR / f"{symbol}_val.parquet", index=False)
        test_df.to_parquet(SPLITS_DIR / f"{symbol}_test.parquet", index=False)

        summary.append((symbol, len(out_df), counts[0], counts[1], counts[2], degenerate))

        flag = "  [DEGENERATE]" if degenerate else ""
        logger.info(
            f"[{symbol}] n={len(out_df):,}  SELL={counts[0]} ({dist[0]:.1%})  "
            f"HOLD={counts[1]} ({dist[1]:.1%})  BUY={counts[2]} ({dist[2]:.1%}){flag}"
        )

    logger.info("=" * 70)
    n_degenerate = sum(1 for *_, d in summary if d)
    logger.info(f"=== Labeled {len(summary)} symbols, {n_degenerate} with degenerate distributions ===")
    if n_degenerate:
        logger.info("Degenerate symbols (review threshold/category mapping later):")
        for symbol, n, sell, hold, buy, d in summary:
            if d:
                logger.info(f"  {symbol}: n={n} SELL={sell} HOLD={hold} BUY={buy}")


if __name__ == "__main__":
    main()
