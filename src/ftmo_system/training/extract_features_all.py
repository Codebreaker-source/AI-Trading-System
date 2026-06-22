"""
Feature Extraction — All Dukascopy Symbols, with Frozen-Data Exclusion
========================================================================
Computes the 27 CLEAN signal features (same names/order as
core.feature_history_recorder.FEATURE_27) from each
data/historical_data/{SYMBOL}_M15_dukascopy.csv.

Any symbol whose price history fails the frozen/flat-data validation
(constant price across long stretches, near-zero variance) is EXCLUDED —
no feature/label/model files are produced for it, and it is reported in
the summary so it can stay on rule-based + confluence (ML=ABSTAIN) until
live feature_history accumulates real data.

Output: data/historical_data/features/{SYMBOL}_features.parquet
  columns: timestamp + FEATURE_27 (27 columns)

Run: python training/extract_features_all.py
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

INPUT_DIR = BASE_DIR / "data" / "historical_data"
OUTPUT_DIR = INPUT_DIR / "features"

FAST_EMA, SLOW_EMA = 12, 26
RSI_PERIOD = 14
ATR_PERIOD = 14
BB_PERIOD, BB_STD = 20, 2.0
STOCH_K, STOCH_D = 14, 3
SMA_20, SMA_50 = 20, 50
MOMENTUM_PERIOD = 20
VOLUME_SMA = 20
HTF_MULTIPLIER = 16  # M15 -> H4


# ── Frozen/corrupted data validation ────────────────────────────────────────

def validate_data(df: pd.DataFrame) -> list[str]:
    """Return a list of issues; non-empty means the symbol should be excluded."""
    issues = []
    close = df["close"].values

    price_std = np.std(close)
    price_range = np.max(close) - np.min(close)

    if price_std < 1e-9:
        issues.append(f"price std dev too low: {price_std:.8f}")
    if price_range / max(np.mean(close), 1e-9) < 1e-5:
        issues.append(f"price range too small relative to level: {price_range:.8f}")

    df_temp = df.copy()
    df_temp["month"] = pd.to_datetime(df_temp["timestamp"]).dt.to_period("M")
    monthly = df_temp.groupby("month")["close"].agg(["min", "max"])

    def count_consecutive_same(arr):
        if len(arr) == 0:
            return 0
        max_count = current = 1
        for i in range(1, len(arr)):
            if arr[i] == arr[i - 1]:
                current += 1
                max_count = max(max_count, current)
            else:
                current = 1
        return max_count

    consec_max = count_consecutive_same(monthly["max"].round(6).values)
    consec_min = count_consecutive_same(monthly["min"].round(6).values)

    if consec_max >= 4:
        issues.append(f"FROZEN: {consec_max} consecutive months with same MAX")
    if consec_min >= 4:
        issues.append(f"FROZEN: {consec_min} consecutive months with same MIN")

    return issues


# ── Indicators ───────────────────────────────────────────────────────────────

def calc_ema(data, period):
    return data.ewm(span=period, adjust=False).mean()

def calc_sma(data, period):
    return data.rolling(window=period).mean()

def calc_rsi(data, period):
    delta = data.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calc_atr(df, period):
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def calc_bollinger(data, period, std_dev):
    middle = calc_sma(data, period)
    std = data.rolling(window=period).std()
    return middle + std * std_dev, middle, middle - std * std_dev

def calc_stochastic(df, k_period, d_period):
    low_min = df["low"].rolling(window=k_period).min()
    high_max = df["high"].rolling(window=k_period).max()
    stoch_k = 100 * (df["close"] - low_min) / (high_max - low_min)
    stoch_d = stoch_k.rolling(window=d_period).mean()
    return stoch_k, stoch_d

def calc_sentiment(df):
    range_hl = (df["high"] - df["low"]).replace(0, np.nan)
    bullish = (df["close"] - df["low"]) / range_hl
    bearish = (df["high"] - df["close"]) / range_hl
    net = bullish - bearish
    return bullish.fillna(0.5), bearish.fillna(0.5), net.fillna(0)

def resample_to_htf(df, multiplier):
    df_indexed = df.set_index("timestamp")
    htf = df_indexed.resample(f"{multiplier * 15}min").agg({
        "open": "first", "high": "max", "low": "min",
        "close": "last", "tick_volume": "sum",
    }).dropna()
    return htf.reset_index()


def extract_features(df: pd.DataFrame) -> pd.DataFrame:
    f = pd.DataFrame()
    f["timestamp"] = df["timestamp"]
    f["close"] = df["close"].values
    f["high"] = df["high"].values
    f["low"] = df["low"].values
    f["volume"] = df["tick_volume"].values

    f["sma_20"] = calc_sma(df["close"], SMA_20).values
    f["sma_50"] = calc_sma(df["close"], SMA_50).values
    f["fast_ema"] = calc_ema(df["close"], FAST_EMA).values
    f["slow_ema"] = calc_ema(df["close"], SLOW_EMA).values

    htf = resample_to_htf(df, HTF_MULTIPLIER)
    htf["htf_fast_ema"] = calc_ema(htf["close"], FAST_EMA)
    htf["htf_slow_ema"] = calc_ema(htf["close"], SLOW_EMA)
    htf["htf_trend_direction"] = np.where(htf["htf_fast_ema"] > htf["htf_slow_ema"], 1, -1)

    htf_merge = htf[["timestamp", "htf_fast_ema", "htf_slow_ema", "htf_trend_direction"]]
    df_with_htf = pd.merge_asof(
        df.sort_values("timestamp"), htf_merge.sort_values("timestamp"),
        on="timestamp", direction="backward",
    )
    f["htf_fast_ema"] = df_with_htf["htf_fast_ema"].values
    f["htf_slow_ema"] = df_with_htf["htf_slow_ema"].values
    f["htf_trend_direction"] = df_with_htf["htf_trend_direction"].values

    m15_trend = np.where(f["fast_ema"] > f["slow_ema"], 1, -1)
    f["htf_trend_alignment"] = (m15_trend == f["htf_trend_direction"]).astype(int)

    f["rsi"] = calc_rsi(df["close"], RSI_PERIOD).values
    stoch_k, stoch_d = calc_stochastic(df, STOCH_K, STOCH_D)
    f["stoch_k"] = stoch_k.values
    f["stoch_d"] = stoch_d.values
    f["momentum"] = df["close"].pct_change(periods=MOMENTUM_PERIOD).values

    f["atr"] = calc_atr(df, ATR_PERIOD).values
    bb_u, bb_m, bb_l = calc_bollinger(df["close"], BB_PERIOD, BB_STD)
    f["bb_upper"] = bb_u.values
    f["bb_middle"] = bb_m.values
    f["bb_lower"] = bb_l.values
    f["volatility"] = df["close"].rolling(window=20).std().values

    f["volume_sma"] = calc_sma(df["tick_volume"], VOLUME_SMA).values
    vol_sma = f["volume_sma"].replace(0, np.nan)
    f["volume_ratio"] = (df["tick_volume"].values / vol_sma).fillna(1.0)
    f["price_volume"] = df["close"].values * df["tick_volume"].values

    bullish, bearish, net = calc_sentiment(df)
    f["bullish_sentiment"] = bullish.values
    f["bearish_sentiment"] = bearish.values
    f["net_sentiment"] = net.values

    return f[["timestamp"] + FEATURE_27]


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    excluded = []
    extracted = []

    for path in sorted(INPUT_DIR.glob("*_M15_dukascopy.csv")):
        symbol = path.stem.replace("_M15_dukascopy", "")
        df = pd.read_csv(path)
        if "close" not in df.columns or len(df) < 100:
            excluded.append((symbol, "insufficient rows"))
            continue
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)

        issues = validate_data(df)
        if issues:
            excluded.append((symbol, "; ".join(issues)))
            logger.warning(f"[{symbol}] EXCLUDED — {'; '.join(issues)}")
            continue

        features = extract_features(df)
        before = len(features)
        features = features.dropna().reset_index(drop=True)
        dropped = before - len(features)

        out_path = OUTPUT_DIR / f"{symbol}_features.parquet"
        features.to_parquet(out_path, index=False)
        extracted.append((symbol, len(features), dropped))
        logger.info(f"[{symbol}] {len(features):,} rows ({dropped} warmup dropped) -> {out_path.name}")

    logger.info("=" * 70)
    logger.info(f"Extracted {len(extracted)} symbols, excluded {len(excluded)}")
    if excluded:
        logger.info("Excluded (frozen/invalid data):")
        for symbol, reason in excluded:
            logger.info(f"  {symbol}: {reason}")


if __name__ == "__main__":
    main()
