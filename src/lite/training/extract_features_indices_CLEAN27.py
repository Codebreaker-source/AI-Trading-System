#!/usr/bin/env python3
"""
Index Feature Extractor - CLEAN 27 Signal Features
====================================================
Extracts 27 signal features for US30, US500, NAS100
"""

import pandas as pd
import numpy as np
from pathlib import Path
import gc
import warnings
warnings.filterwarnings('ignore')

BASE_DIR = Path(r"C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System")
INPUT_DIR = BASE_DIR / "historical_data"
OUTPUT_DIR = BASE_DIR / "training"
OUTPUT_FILE = OUTPUT_DIR / "indices_CLEAN27_features.csv"

INDICES = [
    ('US30', 'US30_M15_dukascopy.csv', 'M15', 16),
    ('US500', 'US500_M15_dukascopy.csv', 'M15', 16),
    ('NAS100', 'NAS100_H1_yfinance.csv', 'H1', 4),
]

FAST_EMA, SLOW_EMA = 12, 26
RSI_PERIOD, ATR_PERIOD = 14, 14
BB_PERIOD, BB_STD = 20, 2.0
STOCH_K, STOCH_D = 14, 3
SMA_20, SMA_50 = 20, 50
MOMENTUM_PERIOD, VOLUME_SMA = 20, 20

print("=" * 70)
print("INDEX FEATURE EXTRACTOR - CLEAN 27 SIGNAL FEATURES")
print("=" * 70)

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
    return middle + (std * std_dev), middle, middle - (std * std_dev)

def calc_stochastic(df, k_period, d_period):
    low_min = df['low'].rolling(window=k_period).min()
    high_max = df['high'].rolling(window=k_period).max()
    stoch_k = 100 * (df['close'] - low_min) / (high_max - low_min)
    return stoch_k, stoch_k.rolling(window=d_period).mean()

def calc_sentiment(df):
    range_hl = (df['high'] - df['low']).replace(0, np.nan)
    bullish = ((df['close'] - df['low']) / range_hl).fillna(0.5)
    bearish = ((df['high'] - df['close']) / range_hl).fillna(0.5)
    return bullish, bearish, (bullish - bearish).fillna(0)

def resample_to_htf(df, timeframe, multiplier):
    df_idx = df.set_index('timestamp')
    htf_min = multiplier * (15 if timeframe == 'M15' else 60)
    htf = df_idx.resample(f'{htf_min}min').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 
        'close': 'last', 'tick_volume': 'sum'
    }).dropna()
    return htf.reset_index()

def extract_features(df, symbol, timeframe, htf_mult):
    features = pd.DataFrame()
    features['timestamp'] = df['timestamp']
    features['symbol'] = symbol
    
    features['close'] = df['close'].values
    features['high'] = df['high'].values
    features['low'] = df['low'].values
    features['volume'] = df['tick_volume'].values
    
    features['sma_20'] = calc_sma(df['close'], SMA_20).values
    features['sma_50'] = calc_sma(df['close'], SMA_50).values
    features['fast_ema'] = calc_ema(df['close'], FAST_EMA).values
    features['slow_ema'] = calc_ema(df['close'], SLOW_EMA).values
    
    htf = resample_to_htf(df, timeframe, htf_mult)
    htf['htf_fast_ema'] = calc_ema(htf['close'], FAST_EMA)
    htf['htf_slow_ema'] = calc_ema(htf['close'], SLOW_EMA)
    htf['htf_trend_direction'] = np.where(htf['htf_fast_ema'] > htf['htf_slow_ema'], 1, -1)
    
    df_htf = pd.merge_asof(df.sort_values('timestamp'),
        htf[['timestamp','htf_fast_ema','htf_slow_ema','htf_trend_direction']].sort_values('timestamp'),
        on='timestamp', direction='backward')
    
    features['htf_fast_ema'] = df_htf['htf_fast_ema'].values
    features['htf_slow_ema'] = df_htf['htf_slow_ema'].values
    features['htf_trend_direction'] = df_htf['htf_trend_direction'].values
    m15_trend = np.where(features['fast_ema'] > features['slow_ema'], 1, -1)
    features['htf_trend_alignment'] = (m15_trend == features['htf_trend_direction']).astype(int)
    
    features['rsi'] = calc_rsi(df['close'], RSI_PERIOD).values
    stoch_k, stoch_d = calc_stochastic(df, STOCH_K, STOCH_D)
    features['stoch_k'] = stoch_k.values
    features['stoch_d'] = stoch_d.values
    features['momentum'] = df['close'].pct_change(periods=MOMENTUM_PERIOD).values
    
    features['atr'] = calc_atr(df, ATR_PERIOD).values
    bb_up, bb_mid, bb_low = calc_bollinger(df['close'], BB_PERIOD, BB_STD)
    features['bb_upper'] = bb_up.values
    features['bb_middle'] = bb_mid.values
    features['bb_lower'] = bb_low.values
    features['volatility'] = df['close'].rolling(window=20).std().values
    
    features['volume_sma'] = calc_sma(df['tick_volume'], VOLUME_SMA).values
    vol_sma = features['volume_sma'].replace(0, np.nan)
    features['volume_ratio'] = (df['tick_volume'].values / vol_sma).fillna(1.0)
    features['price_volume'] = df['close'].values * df['tick_volume'].values
    
    bull, bear, net = calc_sentiment(df)
    features['bullish_sentiment'] = bull.values
    features['bearish_sentiment'] = bear.values
    features['net_sentiment'] = net.values
    
    return features

def main():
    all_features = []
    
    for symbol, filename, timeframe, htf_mult in INDICES:
        print(f"\n[{symbol}] Processing ({timeframe})...")
        
        input_file = INPUT_DIR / filename
        if not input_file.exists():
            print(f"  [SKIP] Not found: {input_file}")
            continue
        
        df = pd.read_csv(input_file)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        if 'tick_volume' not in df.columns:
            df['tick_volume'] = df.get('volume', 0)
        
        print(f"  Loaded {len(df):,} rows ({df['timestamp'].min()} to {df['timestamp'].max()})")
        
        features = extract_features(df, symbol, timeframe, htf_mult)
        before = len(features)
        features = features.dropna()
        print(f"  Extracted 27 features, {len(features):,} rows (dropped {before-len(features)} warmup)")
        
        all_features.append(features)
        del df, features
        gc.collect()
    
    combined = pd.concat(all_features, ignore_index=True).fillna(0)
    combined.to_csv(OUTPUT_FILE, index=False)
    
    print(f"\n{'='*70}")
    print(f"SAVED: {OUTPUT_FILE.name}")
    print(f"Total: {len(combined):,} rows, {OUTPUT_FILE.stat().st_size/1024/1024:.1f} MB")
    for sym in combined['symbol'].unique():
        print(f"  {sym}: {len(combined[combined['symbol']==sym]):,}")
    print(f"Columns ({len(combined.columns)}): {list(combined.columns)}")

if __name__ == "__main__":
    main()
