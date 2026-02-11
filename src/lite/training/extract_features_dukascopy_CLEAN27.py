#!/usr/bin/env python3
"""
Dukascopy Feature Extractor - CLEAN 27 Signal Features Only
============================================================
File: extract_features_dukascopy_CLEAN27.py
Date: 2025-12-03
Version: 2.0 - FIXED (Sparse format, no pair prefix)

FIX APPLIED:
- Creates SPARSE format (symbol column, no pair prefix)
- Columns: timestamp, symbol, close, high, low, volume, rsi, ...
- dropna() now works correctly per pair

27 SIGNAL FEATURES (no pair prefix):
- Price: close, high, low, volume (4)
- Trend: sma_20, sma_50, fast_ema, slow_ema, htf_* (8)
- Momentum: rsi, stoch_k, stoch_d, momentum (4)
- Volatility: atr, bb_upper, bb_middle, bb_lower, volatility (5)
- Volume: volume_sma, volume_ratio, price_volume (3)
- Sentiment: bullish_sentiment, bearish_sentiment, net_sentiment (3)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import gc
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================
BASE_DIR = Path(r"C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System")
INPUT_DIR = BASE_DIR / "historical_data"
OUTPUT_DIR = BASE_DIR / "training"
OUTPUT_FILE = OUTPUT_DIR / "dukascopy_CLEAN27_features.csv"

PAIRS = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD', 'EURGBP']

# Indicator periods
FAST_EMA = 12
SLOW_EMA = 26
RSI_PERIOD = 14
ATR_PERIOD = 14
BB_PERIOD = 20
BB_STD = 2.0
STOCH_K = 14
STOCH_D = 3
SMA_20 = 20
SMA_50 = 50
MOMENTUM_PERIOD = 20
VOLUME_SMA = 20
HTF_MULTIPLIER = 16  # M15 * 16 = H4

# Warmup period (rows to drop due to indicator calculation)
WARMUP_PERIOD = 50  # Max of all indicator periods

print("=" * 70)
print("DUKASCOPY FEATURE EXTRACTOR - CLEAN 27 SIGNAL FEATURES")
print("Version 2.0 - SPARSE FORMAT (Fixed)")
print("=" * 70)
print(f"Input: {INPUT_DIR}")
print(f"Output: {OUTPUT_FILE}")
print(f"Pairs: {PAIRS}")
print(f"Warmup period: {WARMUP_PERIOD} rows per pair")
print("=" * 70)


# ============================================================================
# DATA VALIDATION
# ============================================================================
def validate_data(df, pair):
    """Check for frozen/corrupted price data"""
    issues = []
    
    close_prices = df['close'].values
    
    # Check price variance
    price_std = np.std(close_prices)
    price_range = np.max(close_prices) - np.min(close_prices)
    
    if price_std < 0.0001:
        issues.append(f"Price std dev too low: {price_std:.6f}")
    
    if price_range < 0.001:
        issues.append(f"Price range too small: {price_range:.6f}")
    
    # Check monthly variance (detect frozen data)
    df_temp = df.copy()
    df_temp['month'] = pd.to_datetime(df_temp['timestamp']).dt.to_period('M')
    monthly = df_temp.groupby('month')['close'].agg(['min', 'max'])
    
    monthly_maxes = monthly['max'].round(5).values
    monthly_mins = monthly['min'].round(5).values
    
    def count_consecutive_same(arr):
        max_count = 1
        current = 1
        for i in range(1, len(arr)):
            if arr[i] == arr[i-1]:
                current += 1
                max_count = max(max_count, current)
            else:
                current = 1
        return max_count
    
    consec_max = count_consecutive_same(monthly_maxes)
    consec_min = count_consecutive_same(monthly_mins)
    
    if consec_max >= 4:
        issues.append(f"FROZEN: {consec_max} consecutive months with same MAX")
    if consec_min >= 4:
        issues.append(f"FROZEN: {consec_min} consecutive months with same MIN")
    
    return issues


# ============================================================================
# INDICATOR CALCULATIONS
# ============================================================================
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
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift())
    low_close = abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def calc_bollinger(data, period, std_dev):
    middle = calc_sma(data, period)
    std = data.rolling(window=period).std()
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    return upper, middle, lower

def calc_stochastic(df, k_period, d_period):
    low_min = df['low'].rolling(window=k_period).min()
    high_max = df['high'].rolling(window=k_period).max()
    stoch_k = 100 * (df['close'] - low_min) / (high_max - low_min)
    stoch_d = stoch_k.rolling(window=d_period).mean()
    return stoch_k, stoch_d

def calc_sentiment(df):
    range_hl = df['high'] - df['low']
    range_hl = range_hl.replace(0, np.nan)
    bullish = (df['close'] - df['low']) / range_hl
    bearish = (df['high'] - df['close']) / range_hl
    net = bullish - bearish
    return bullish.fillna(0.5), bearish.fillna(0.5), net.fillna(0)

def resample_to_htf(df, multiplier):
    """Resample M15 to H4 (multiplier=16)"""
    df_indexed = df.set_index('timestamp')
    htf = df_indexed.resample(f'{multiplier * 15}min').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'tick_volume': 'sum'
    }).dropna()
    return htf.reset_index()


# ============================================================================
# FEATURE EXTRACTION - SPARSE FORMAT (NO PAIR PREFIX)
# ============================================================================
def extract_features(df, pair):
    """Extract 27 clean signal features for one pair - SPARSE format"""
    
    features = pd.DataFrame()
    features['timestamp'] = df['timestamp']
    features['symbol'] = pair  # Add symbol column for sparse format
    
    # === PRICE (4) - NO PAIR PREFIX ===
    features['close'] = df['close'].values
    features['high'] = df['high'].values
    features['low'] = df['low'].values
    features['volume'] = df['tick_volume'].values
    
    # === TREND (8) ===
    features['sma_20'] = calc_sma(df['close'], SMA_20).values
    features['sma_50'] = calc_sma(df['close'], SMA_50).values
    features['fast_ema'] = calc_ema(df['close'], FAST_EMA).values
    features['slow_ema'] = calc_ema(df['close'], SLOW_EMA).values
    
    # HTF (H4) features
    htf = resample_to_htf(df, HTF_MULTIPLIER)
    htf['htf_fast_ema'] = calc_ema(htf['close'], FAST_EMA)
    htf['htf_slow_ema'] = calc_ema(htf['close'], SLOW_EMA)
    htf['htf_trend_direction'] = np.where(htf['htf_fast_ema'] > htf['htf_slow_ema'], 1, -1)
    
    # Merge HTF back to M15
    htf_merge = htf[['timestamp', 'htf_fast_ema', 'htf_slow_ema', 'htf_trend_direction']]
    df_with_htf = pd.merge_asof(
        df.sort_values('timestamp'),
        htf_merge.sort_values('timestamp'),
        on='timestamp',
        direction='backward'
    )
    
    features['htf_fast_ema'] = df_with_htf['htf_fast_ema'].values
    features['htf_slow_ema'] = df_with_htf['htf_slow_ema'].values
    features['htf_trend_direction'] = df_with_htf['htf_trend_direction'].values
    
    # HTF alignment (M15 trend matches H4 trend)
    m15_trend = np.where(features['fast_ema'] > features['slow_ema'], 1, -1)
    features['htf_trend_alignment'] = (m15_trend == features['htf_trend_direction']).astype(int)
    
    # === MOMENTUM (4) ===
    features['rsi'] = calc_rsi(df['close'], RSI_PERIOD).values
    stoch_k, stoch_d = calc_stochastic(df, STOCH_K, STOCH_D)
    features['stoch_k'] = stoch_k.values
    features['stoch_d'] = stoch_d.values
    features['momentum'] = df['close'].pct_change(periods=MOMENTUM_PERIOD).values
    
    # === VOLATILITY (5) ===
    features['atr'] = calc_atr(df, ATR_PERIOD).values
    bb_upper, bb_middle, bb_lower = calc_bollinger(df['close'], BB_PERIOD, BB_STD)
    features['bb_upper'] = bb_upper.values
    features['bb_middle'] = bb_middle.values
    features['bb_lower'] = bb_lower.values
    features['volatility'] = df['close'].rolling(window=20).std().values
    
    # === VOLUME (3) ===
    features['volume_sma'] = calc_sma(df['tick_volume'], VOLUME_SMA).values
    vol_sma = features['volume_sma'].replace(0, np.nan)
    features['volume_ratio'] = (df['tick_volume'].values / vol_sma).fillna(1.0)
    features['price_volume'] = df['close'].values * df['tick_volume'].values
    
    # === SENTIMENT (3) ===
    bullish, bearish, net = calc_sentiment(df)
    features['bullish_sentiment'] = bullish.values
    features['bearish_sentiment'] = bearish.values
    features['net_sentiment'] = net.values
    
    return features


# ============================================================================
# MAIN PROCESSING
# ============================================================================
def main():
    all_features = []
    valid_pairs = []
    skipped_pairs = []
    
    for pair in PAIRS:
        print(f"\n[{pair}] Processing...")
        
        # Find input file
        input_file = INPUT_DIR / f"{pair}_M15_dukascopy.csv"
        if not input_file.exists():
            print(f"  [SKIP] File not found: {input_file}")
            skipped_pairs.append(pair)
            continue
        
        # Load data
        print(f"  Loading {input_file.name}...")
        df = pd.read_csv(input_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        print(f"  Loaded {len(df):,} rows")
        print(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        
        # Validate data
        print(f"  Validating data...")
        issues = validate_data(df, pair)
        if issues:
            print(f"  [WARNING] Data issues found:")
            for issue in issues:
                print(f"    - {issue}")
        else:
            print(f"  [OK] Data validation passed")
        
        # Extract features (SPARSE format - no pair prefix)
        print(f"  Extracting 27 features...")
        features = extract_features(df, pair)
        
        # Drop warmup rows (NaN from indicator calculations)
        before_count = len(features)
        features = features.dropna()
        after_count = len(features)
        dropped = before_count - after_count
        print(f"  Dropped {dropped} warmup rows ({after_count:,} remaining)")
        
        # Verify feature count
        feature_cols = [c for c in features.columns if c not in ['timestamp', 'symbol']]
        print(f"  Features: {len(feature_cols)} columns")
        
        all_features.append(features)
        valid_pairs.append(pair)
        
        # Memory cleanup
        del df, features
        gc.collect()
        print(f"  [OK] Complete")
    
    # Combine all pairs (vertical stack - sparse format)
    if not all_features:
        print("\n[ERROR] No data extracted!")
        return
    
    print(f"\nCombining {len(all_features)} pairs (sparse format)...")
    combined = pd.concat(all_features, ignore_index=True)
    
    # Verify no NaN remaining
    nan_count = combined.isna().sum().sum()
    if nan_count > 0:
        print(f"[WARNING] {nan_count} NaN values remaining, filling with 0")
        combined = combined.fillna(0)
    
    # Save
    print(f"\nSaving to {OUTPUT_FILE}...")
    combined.to_csv(OUTPUT_FILE, index=False)
    file_size = OUTPUT_FILE.stat().st_size / 1024 / 1024
    print(f"Saved: {len(combined):,} rows, {file_size:.1f} MB")
    
    # Summary
    print("\n" + "=" * 70)
    print("EXTRACTION COMPLETE")
    print("=" * 70)
    print(f"Valid pairs: {valid_pairs}")
    print(f"Skipped pairs: {skipped_pairs}")
    print(f"Total rows: {len(combined):,}")
    print(f"Columns: {len(combined.columns)}")
    
    # Per-pair counts
    print("\nPer-pair sample counts:")
    for pair in valid_pairs:
        count = len(combined[combined['symbol'] == pair])
        print(f"  {pair}: {count:,}")
    
    print("\nColumn list:")
    print(f"  {list(combined.columns)}")
    
    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print("1. Run labeler: python data_labeler_CLEAN27.py")
    print("2. Train models: python train_xgboost_CLEAN27.py")


if __name__ == "__main__":
    main()
