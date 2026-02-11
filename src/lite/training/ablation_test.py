#!/usr/bin/env python3
"""
ABLATION TESTING - Feature Selection for Index Models
======================================================
Tests each candidate feature individually to measure impact on BUY accuracy.
"""
import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from pathlib import Path
from sklearn.metrics import accuracy_score
import joblib
import gc
from datetime import datetime

BASE_DIR = Path(r'C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System')
TRAINING_DIR = BASE_DIR / 'training'
HIST_DIR = BASE_DIR / 'historical_data'

# Point thresholds (same as before)
POINT_THRESHOLDS = {'US30': 60, 'US500': 9, 'NAS100': 150}
FORWARD_CANDLES = {'US30': 24, 'US500': 24, 'NAS100': 6}

print('='*70)
print('ABLATION TESTING - FEATURE SELECTION')
print('Started:', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
print('='*70)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def calc_sma(data, period):
    return data.rolling(window=period, min_periods=1).mean()

def calc_ema(data, period):
    return data.ewm(span=period, adjust=False).mean()

def label_data(df, symbol):
    """Label using point thresholds"""
    close = df['close'].values
    threshold = POINT_THRESHOLDS[symbol]
    fwd = FORWARD_CANDLES[symbol]
    labels = []
    n = len(close)
    for i in range(n):
        if i + fwd >= n:
            labels.append(1)
            continue
        current = close[i]
        future = close[i+1:i+1+fwd]
        max_gain = np.max(future) - current
        max_loss = current - np.min(future)
        if max_gain >= threshold and max_loss < threshold:
            labels.append(2)  # BUY
        elif max_loss >= threshold and max_gain < threshold:
            labels.append(0)  # SELL
        else:
            labels.append(1)  # HOLD
    return np.array(labels)

def train_and_evaluate(train_df, val_df, test_df, feature_cols, symbol):
    """Train XGB+LGB and return per-class accuracy"""
    X_train = train_df[feature_cols].values
    y_train = train_df['label'].values
    X_val = val_df[feature_cols].values
    y_val = val_df['label'].values
    X_test = test_df[feature_cols].values
    y_test = test_df['label'].values
    
    # XGBoost
    xgb_model = xgb.XGBClassifier(
        n_estimators=200, max_depth=6, learning_rate=0.1,
        subsample=0.8, colsample_bytree=0.8,
        objective='multi:softprob', num_class=3,
        random_state=42, n_jobs=-1, verbosity=0
    )
    xgb_model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    
    # LightGBM
    lgb_model = lgb.LGBMClassifier(
        n_estimators=200, max_depth=6, learning_rate=0.1,
        subsample=0.8, colsample_bytree=0.8,
        objective='multiclass', num_class=3,
        random_state=42, n_jobs=-1, verbose=-1
    )
    lgb_model.fit(X_train, y_train, eval_set=[(X_val, y_val)])
    
    # Ensemble prediction
    xgb_proba = xgb_model.predict_proba(X_test)
    lgb_proba = lgb_model.predict_proba(X_test)
    ensemble_proba = (xgb_proba + lgb_proba) / 2
    ensemble_pred = np.argmax(ensemble_proba, axis=1)
    
    # Per-class accuracy
    results = {'overall': accuracy_score(y_test, ensemble_pred)}
    for lbl, name in [(0, 'SELL'), (1, 'HOLD'), (2, 'BUY')]:
        mask = y_test == lbl
        if mask.sum() > 0:
            results[name] = (ensemble_pred[mask] == y_test[mask]).mean()
        else:
            results[name] = 0.0
    
    return results

# =============================================================================
# LOAD BASE DATA
# =============================================================================
print('\nLoading base feature data...')
base_df = pd.read_csv(TRAINING_DIR / 'indices_CLEAN27_features.csv')
base_df['timestamp'] = pd.to_datetime(base_df['timestamp'])
print(f'Loaded {len(base_df):,} rows')

BASE_FEATURES = [c for c in base_df.columns if c not in ['timestamp', 'symbol']]
print(f'Base features: {len(BASE_FEATURES)}')

# =============================================================================
# BASELINE TEST (27 features)
# =============================================================================
print('\n' + '='*70)
print('TEST 0: BASELINE (27 features)')
print('='*70)

baseline_results = {}

for symbol in ['US30', 'US500', 'NAS100']:
    sym_df = base_df[base_df['symbol'] == symbol].copy().sort_values('timestamp').reset_index(drop=True)
    sym_df['label'] = label_data(sym_df, symbol)
    
    n = len(sym_df)
    train_end = int(n * 0.70)
    val_end = train_end + int(n * 0.15)
    
    train = sym_df.iloc[:train_end]
    val = sym_df.iloc[train_end:val_end]
    test = sym_df.iloc[val_end:]
    
    feature_cols = [c for c in BASE_FEATURES if c != 'label']
    results = train_and_evaluate(train, val, test, feature_cols, symbol)
    baseline_results[symbol] = results
    
    print(f'{symbol}: Overall={results["overall"]:.4f} SELL={results["SELL"]:.4f} HOLD={results["HOLD"]:.4f} BUY={results["BUY"]:.4f}')

# Average
avg_buy = np.mean([r['BUY'] for r in baseline_results.values()])
avg_sell = np.mean([r['SELL'] for r in baseline_results.values()])
print(f'\nBASELINE AVG: BUY={avg_buy:.4f} SELL={avg_sell:.4f}')

# =============================================================================
# CANDIDATE FEATURE TESTS
# =============================================================================

def add_feature_and_test(feature_name, feature_func, description):
    """Add a feature and test its impact"""
    print(f'\n{"="*70}')
    print(f'TEST: +{feature_name}')
    print(f'Description: {description}')
    print('='*70)
    
    results_dict = {}
    
    for symbol in ['US30', 'US500', 'NAS100']:
        sym_df = base_df[base_df['symbol'] == symbol].copy().sort_values('timestamp').reset_index(drop=True)
        
        # Add new feature
        sym_df[feature_name] = feature_func(sym_df)
        sym_df['label'] = label_data(sym_df, symbol)
        
        # Drop NaN from new feature
        sym_df = sym_df.dropna().reset_index(drop=True)
        
        n = len(sym_df)
        train_end = int(n * 0.70)
        val_end = train_end + int(n * 0.15)
        
        train = sym_df.iloc[:train_end]
        val = sym_df.iloc[train_end:val_end]
        test = sym_df.iloc[val_end:]
        
        feature_cols = [c for c in sym_df.columns if c not in ['timestamp', 'symbol', 'label']]
        results = train_and_evaluate(train, val, test, feature_cols, symbol)
        results_dict[symbol] = results
        
        # Compare to baseline
        buy_diff = results['BUY'] - baseline_results[symbol]['BUY']
        sell_diff = results['SELL'] - baseline_results[symbol]['SELL']
        
        buy_indicator = '++' if buy_diff > 0.05 else '+' if buy_diff > 0.01 else '--' if buy_diff < -0.05 else '-' if buy_diff < -0.01 else '='
        
        print(f'{symbol}: BUY={results["BUY"]:.4f} ({buy_diff:+.4f}) {buy_indicator}  SELL={results["SELL"]:.4f} ({sell_diff:+.4f})')
    
    avg_buy = np.mean([r['BUY'] for r in results_dict.values()])
    avg_sell = np.mean([r['SELL'] for r in results_dict.values()])
    buy_improvement = avg_buy - np.mean([r['BUY'] for r in baseline_results.values()])
    
    print(f'\nAVG: BUY={avg_buy:.4f} ({buy_improvement:+.4f}) SELL={avg_sell:.4f}')
    
    return {
        'feature': feature_name,
        'avg_buy': avg_buy,
        'buy_improvement': buy_improvement,
        'avg_sell': avg_sell,
        'results': results_dict
    }

# =============================================================================
# RUN ABLATION TESTS
# =============================================================================

all_results = []

# Test 1: SMA 100
result = add_feature_and_test(
    'sma_100',
    lambda df: calc_sma(df['close'], 100),
    'Simple Moving Average 100 periods'
)
all_results.append(result)
gc.collect()

# Test 2: SMA 200
result = add_feature_and_test(
    'sma_200',
    lambda df: calc_sma(df['close'], 200),
    'Simple Moving Average 200 periods'
)
all_results.append(result)
gc.collect()

# Test 3: Price vs SMA200 (normalized)
def price_vs_sma200(df):
    sma200 = calc_sma(df['close'], 200)
    return (df['close'] - sma200) / df['atr']

result = add_feature_and_test(
    'price_vs_sma200',
    price_vs_sma200,
    'Distance from SMA200 normalized by ATR'
)
all_results.append(result)
gc.collect()

# Test 4: Daily trend direction (using 96 M15 bars = 1 day)
def daily_trend_direction(df):
    daily_fast = calc_ema(df['close'], 96)   # ~1 day
    daily_slow = calc_ema(df['close'], 192)  # ~2 days
    return np.where(daily_fast > daily_slow, 1, -1)

result = add_feature_and_test(
    'daily_trend_direction',
    daily_trend_direction,
    'Daily timeframe trend direction (EMA 96 vs 192 on M15)'
)
all_results.append(result)
gc.collect()

# Test 5: Weekly trend direction (using 480 M15 bars = 5 days)
def weekly_trend_direction(df):
    weekly_fast = calc_ema(df['close'], 480)   # ~5 days
    weekly_slow = calc_ema(df['close'], 960)   # ~10 days
    return np.where(weekly_fast > weekly_slow, 1, -1)

result = add_feature_and_test(
    'weekly_trend_direction',
    weekly_trend_direction,
    'Weekly timeframe trend direction (EMA 480 vs 960 on M15)'
)
all_results.append(result)
gc.collect()

# Test 6: Trend slope (rate of change of SMA50)
def trend_slope(df):
    sma50 = calc_sma(df['close'], 50)
    return sma50.pct_change(periods=20) * 100  # % change over 20 periods

result = add_feature_and_test(
    'trend_slope',
    trend_slope,
    'Rate of change of SMA50 over 20 periods'
)
all_results.append(result)
gc.collect()

# Test 7: Price position in range (0-1)
def price_position_range(df):
    high_52 = df['high'].rolling(window=52*4).max()  # ~52 periods worth
    low_52 = df['low'].rolling(window=52*4).min()
    return (df['close'] - low_52) / (high_52 - low_52 + 0.0001)

result = add_feature_and_test(
    'price_position_52',
    price_position_range,
    'Price position within 52-period high-low range (0=low, 1=high)'
)
all_results.append(result)
gc.collect()

# =============================================================================
# FINAL SUMMARY
# =============================================================================
print('\n' + '='*70)
print('ABLATION TEST SUMMARY')
print('='*70)
print(f'\nBaseline BUY accuracy: {np.mean([r["BUY"] for r in baseline_results.values()]):.4f}')
print(f'Baseline SELL accuracy: {np.mean([r["SELL"] for r in baseline_results.values()]):.4f}')
print('\nFeature Impact on BUY Accuracy:')
print('-'*50)

# Sort by BUY improvement
all_results.sort(key=lambda x: x['buy_improvement'], reverse=True)

for r in all_results:
    indicator = '***' if r['buy_improvement'] > 0.05 else '**' if r['buy_improvement'] > 0.02 else '*' if r['buy_improvement'] > 0 else ''
    print(f"  {r['feature']:<22}: {r['buy_improvement']:+.4f} ({r['avg_buy']:.4f}) {indicator}")

print('\n' + '='*70)
print('RECOMMENDATIONS')
print('='*70)
winners = [r for r in all_results if r['buy_improvement'] > 0.01]
if winners:
    print('Features that improved BUY accuracy by >1%:')
    for r in winners:
        print(f"  + {r['feature']}: +{r['buy_improvement']*100:.1f}%")
else:
    print('No single feature improved BUY accuracy significantly.')
    print('May need to try combinations or different approach.')

print('\nCompleted:', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
