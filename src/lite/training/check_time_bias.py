#!/usr/bin/env python3
"""Check for time-period bias in index data"""
import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR = Path(r'C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System')
df = pd.read_csv(BASE_DIR / 'training' / 'indices_CLEAN27_features.csv')
df['timestamp'] = pd.to_datetime(df['timestamp'])

print('='*70)
print('TIME-PERIOD BIAS ANALYSIS - INDEX DATA')
print('='*70)

for symbol in ['US30', 'US500', 'NAS100']:
    print()
    print('[' + symbol + ']')
    sym_df = df[df['symbol'] == symbol].sort_values('timestamp')
    
    if len(sym_df) == 0:
        continue
    
    # Overall trend
    first_price = sym_df['close'].iloc[0]
    last_price = sym_df['close'].iloc[-1]
    total_change = ((last_price - first_price) / first_price) * 100
    
    start_date = sym_df['timestamp'].min().date()
    end_date = sym_df['timestamp'].max().date()
    
    print('  Period:', start_date, 'to', end_date)
    print('  First price:', round(first_price, 2))
    print('  Last price:', round(last_price, 2))
    print('  Total change:', str(round(total_change, 1)) + '%')
    
    if total_change > 10:
        print('  >>> STRONG BULLISH BIAS (indices went UP significantly)')
    elif total_change > 5:
        print('  >>> BULLISH BIAS')
    elif total_change < -10:
        print('  >>> STRONG BEARISH BIAS (indices went DOWN significantly)')
    elif total_change < -5:
        print('  >>> BEARISH BIAS')
    else:
        print('  >>> NEUTRAL/RANGING')

# Now check label distribution in train vs test
print()
print('='*70)
print('LABEL DISTRIBUTION BY SPLIT')
print('='*70)

train = pd.read_csv(BASE_DIR / 'training' / 'train_indices_CLEAN27.csv')
val = pd.read_csv(BASE_DIR / 'training' / 'val_indices_CLEAN27.csv')
test = pd.read_csv(BASE_DIR / 'training' / 'test_indices_CLEAN27.csv')

for name, data in [('TRAIN', train), ('VAL', val), ('TEST', test)]:
    print()
    print(name + ':')
    for symbol in ['US30', 'US500', 'NAS100']:
        sym_data = data[data['symbol'] == symbol]
        if len(sym_data) == 0:
            continue
        sell = (sym_data['label'] == 0).sum()
        hold = (sym_data['label'] == 1).sum()
        buy = (sym_data['label'] == 2).sum()
        total = len(sym_data)
        sell_pct = round(sell/total*100, 1)
        hold_pct = round(hold/total*100, 1)
        buy_pct = round(buy/total*100, 1)
        print('  ' + symbol + ': SELL=' + str(sell_pct) + '% HOLD=' + str(hold_pct) + '% BUY=' + str(buy_pct) + '%')

# Check if test period has different market regime
print()
print('='*70)
print('TRAIN vs TEST MARKET REGIME')
print('='*70)

train['timestamp'] = pd.to_datetime(train['timestamp'])
test['timestamp'] = pd.to_datetime(test['timestamp'])

for symbol in ['US30', 'US500', 'NAS100']:
    print()
    print('[' + symbol + ']')
    
    train_sym = train[train['symbol'] == symbol].sort_values('timestamp')
    test_sym = test[test['symbol'] == symbol].sort_values('timestamp')
    
    if len(train_sym) == 0 or len(test_sym) == 0:
        continue
    
    # Train period
    train_start = train_sym['close'].iloc[0]
    train_end = train_sym['close'].iloc[-1]
    train_change = ((train_end - train_start) / train_start) * 100
    
    # Test period
    test_start = test_sym['close'].iloc[0]
    test_end = test_sym['close'].iloc[-1]
    test_change = ((test_end - test_start) / test_start) * 100
    
    print('  TRAIN: ' + str(train_sym['timestamp'].min().date()) + ' to ' + str(train_sym['timestamp'].max().date()))
    print('         Price: ' + str(round(train_start,2)) + ' -> ' + str(round(train_end,2)) + ' (' + str(round(train_change,1)) + '%)')
    
    print('  TEST:  ' + str(test_sym['timestamp'].min().date()) + ' to ' + str(test_sym['timestamp'].max().date()))
    print('         Price: ' + str(round(test_start,2)) + ' -> ' + str(round(test_end,2)) + ' (' + str(round(test_change,1)) + '%)')
    
    if train_change > 0 and test_change < 0:
        print('  >>> REGIME CHANGE: Train=BULL, Test=BEAR')
    elif train_change < 0 and test_change > 0:
        print('  >>> REGIME CHANGE: Train=BEAR, Test=BULL')
    else:
        print('  >>> Same regime')

print()
print('='*70)
print('CONCLUSION')
print('='*70)
