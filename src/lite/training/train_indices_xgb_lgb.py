#!/usr/bin/env python3
"""XGBoost + LightGBM Training for Indices"""
import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from pathlib import Path
from sklearn.metrics import accuracy_score
import joblib
import gc

BASE_DIR = Path(r'C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System')
TRAINING_DIR = BASE_DIR / 'training'
MODEL_DIR = BASE_DIR / 'trained_models_indices'
MODEL_DIR.mkdir(exist_ok=True)

TRAIN_FILE = TRAINING_DIR / 'train_indices_CLEAN27.csv'
VAL_FILE = TRAINING_DIR / 'val_indices_CLEAN27.csv'
TEST_FILE = TRAINING_DIR / 'test_indices_CLEAN27.csv'

INDICES = ['US30', 'US500', 'NAS100']
EXCLUDE_COLS = ['timestamp', 'symbol', 'label']

print('XGBOOST + LIGHTGBM TRAINING - INDICES')
print('='*60)

print('Loading data...')
train = pd.read_csv(TRAIN_FILE)
val = pd.read_csv(VAL_FILE)
test = pd.read_csv(TEST_FILE)
print(f'Train: {len(train):,} | Val: {len(val):,} | Test: {len(test):,}')

feature_cols = [c for c in train.columns if c not in EXCLUDE_COLS]
print(f'Features: {len(feature_cols)}')

results = []

for symbol in INDICES:
    print(f'\n[{symbol}] Training...')
    
    train_sym = train[train['symbol'] == symbol]
    val_sym = val[val['symbol'] == symbol]
    test_sym = test[test['symbol'] == symbol]
    
    if len(train_sym) == 0:
        continue
    
    X_train = train_sym[feature_cols].values
    y_train = train_sym['label'].values
    X_val = val_sym[feature_cols].values
    y_val = val_sym['label'].values
    X_test = test_sym[feature_cols].values
    y_test = test_sym['label'].values
    
    print(f'  Train: {len(X_train):,} | Val: {len(X_val):,} | Test: {len(X_test):,}')
    
    # XGBOOST
    print('  Training XGBoost...')
    xgb_model = xgb.XGBClassifier(
        n_estimators=200, max_depth=6, learning_rate=0.1,
        subsample=0.8, colsample_bytree=0.8,
        objective='multi:softprob', num_class=3,
        eval_metric='mlogloss', random_state=42, n_jobs=-1, verbosity=0
    )
    xgb_model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    
    xgb_pred = xgb_model.predict(X_test)
    xgb_acc = accuracy_score(y_test, xgb_pred)
    print(f'    XGBoost Accuracy: {xgb_acc:.4f}')
    
    xgb_path = MODEL_DIR / f'xgboost_{symbol}.joblib'
    joblib.dump(xgb_model, xgb_path)
    
    # LIGHTGBM
    print('  Training LightGBM...')
    lgb_model = lgb.LGBMClassifier(
        n_estimators=200, max_depth=6, learning_rate=0.1,
        subsample=0.8, colsample_bytree=0.8,
        objective='multiclass', num_class=3,
        random_state=42, n_jobs=-1, verbose=-1
    )
    lgb_model.fit(X_train, y_train, eval_set=[(X_val, y_val)])
    
    lgb_pred = lgb_model.predict(X_test)
    lgb_acc = accuracy_score(y_test, lgb_pred)
    print(f'    LightGBM Accuracy: {lgb_acc:.4f}')
    
    lgb_path = MODEL_DIR / f'lightgbm_{symbol}.joblib'
    joblib.dump(lgb_model, lgb_path)
    
    # ENSEMBLE
    xgb_proba = xgb_model.predict_proba(X_test)
    lgb_proba = lgb_model.predict_proba(X_test)
    ensemble_proba = (xgb_proba + lgb_proba) / 2
    ensemble_pred = np.argmax(ensemble_proba, axis=1)
    ensemble_acc = accuracy_score(y_test, ensemble_pred)
    print(f'    ENSEMBLE Accuracy: {ensemble_acc:.4f}')
    
    results.append((symbol, xgb_acc, lgb_acc, ensemble_acc, len(y_test)))
    
    # Per-class
    print('  Per-class (Ensemble):')
    for lbl, name in [(0,'SELL'), (1,'HOLD'), (2,'BUY')]:
        mask = y_test == lbl
        if mask.sum() > 0:
            acc = (ensemble_pred[mask] == y_test[mask]).mean()
            print(f'    {name}: {acc:.4f} ({mask.sum()} samples)')
    
    del train_sym, val_sym, test_sym
    gc.collect()

print('\n' + '='*60)
print('RESULTS SUMMARY')
print('='*60)
for r in results:
    print(f'{r[0]}: XGB={r[1]:.4f} LGB={r[2]:.4f} ENS={r[3]:.4f}')
print(f'\nModels saved to: {MODEL_DIR}')
