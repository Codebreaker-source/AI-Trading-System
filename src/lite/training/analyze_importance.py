import pandas as pd
import numpy as np
import joblib
from pathlib import Path

BASE_DIR = Path(r'C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System')
MODEL_DIR = BASE_DIR / 'trained_models_indices'
TRAINING_DIR = BASE_DIR / 'training'

train = pd.read_csv(TRAINING_DIR / 'train_indices_CLEAN27.csv', nrows=1)
EXCLUDE_COLS = ['timestamp', 'symbol', 'label']
feature_cols = [c for c in train.columns if c not in EXCLUDE_COLS]

print('='*70)
print('FEATURE IMPORTANCE ANALYSIS - INDEX MODELS')
print('='*70)
print('Features:', len(feature_cols))

all_xgb = {}
all_lgb = {}

for symbol in ['US30', 'US500', 'NAS100']:
    print()
    print('[' + symbol + ']')
    print('-'*50)
    
    xgb_path = MODEL_DIR / ('xgboost_' + symbol + '.joblib')
    lgb_path = MODEL_DIR / ('lightgbm_' + symbol + '.joblib')
    
    if xgb_path.exists():
        xgb = joblib.load(xgb_path)
        imp = xgb.feature_importances_
        df = pd.DataFrame({'f': feature_cols, 'i': imp}).sort_values('i', ascending=False)
        print('XGBoost Top 10:')
        for _, r in df.head(10).iterrows():
            stars = '*' * int(r['i'] * 100)
            print('  ' + r['f'].ljust(22) + str(round(r['i'], 4)) + ' ' + stars)
        for f, i in zip(feature_cols, imp):
            if f not in all_xgb:
                all_xgb[f] = []
            all_xgb[f].append(i)
    
    if lgb_path.exists():
        lgb = joblib.load(lgb_path)
        imp = lgb.feature_importances_ / lgb.feature_importances_.sum()
        df = pd.DataFrame({'f': feature_cols, 'i': imp}).sort_values('i', ascending=False)
        print()
        print('LightGBM Top 10:')
        for _, r in df.head(10).iterrows():
            stars = '*' * int(r['i'] * 100)
            print('  ' + r['f'].ljust(22) + str(round(r['i'], 4)) + ' ' + stars)
        for f, i in zip(feature_cols, imp):
            if f not in all_lgb:
                all_lgb[f] = []
            all_lgb[f].append(i)

print()
print('='*70)
print('AVERAGE IMPORTANCE - ALL MODELS')
print('='*70)
print()

avg = {}
for f in feature_cols:
    xgb_avg = np.mean(all_xgb.get(f, [0]))
    lgb_avg = np.mean(all_lgb.get(f, [0]))
    avg[f] = (xgb_avg + lgb_avg) / 2

sorted_avg = sorted(avg.items(), key=lambda x: -x[1])
for i, (f, v) in enumerate(sorted_avg, 1):
    stars = '*' * int(v * 150)
    pct = round(v * 100, 2)
    print(str(i).rjust(3) + '. ' + f.ljust(22) + str(round(v, 4)) + ' (' + str(pct) + '%) ' + stars)

print()
print('='*70)
print('BY CATEGORY')
print('='*70)
print()

cats = {
    'Price': ['close', 'high', 'low', 'volume'],
    'Trend-MA': ['sma_20', 'sma_50', 'fast_ema', 'slow_ema'],
    'HTF Trend': ['htf_fast_ema', 'htf_slow_ema', 'htf_trend_direction', 'htf_trend_alignment'],
    'Momentum': ['rsi', 'stoch_k', 'stoch_d', 'momentum'],
    'Volatility': ['atr', 'bb_upper', 'bb_middle', 'bb_lower', 'volatility'],
    'Volume': ['volume_sma', 'volume_ratio', 'price_volume'],
    'Sentiment': ['bullish_sentiment', 'bearish_sentiment', 'net_sentiment']
}

cat_sums = []
for c, fs in cats.items():
    v = sum(avg.get(f, 0) for f in fs)
    cat_sums.append((c, v))

cat_sums.sort(key=lambda x: -x[1])
for c, v in cat_sums:
    stars = '*' * int(v * 150)
    pct = round(v * 100, 1)
    print('  ' + c.ljust(12) + ': ' + str(round(v, 4)) + ' (' + str(pct) + '%) ' + stars)
