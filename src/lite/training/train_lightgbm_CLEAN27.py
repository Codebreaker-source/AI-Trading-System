#!/usr/bin/env python3
"""
LightGBM Training Script - CLEAN27 Features - M15 Timeframe
============================================================
File: train_lightgbm_CLEAN27.py
Date: 2025-12-03

PREVENTION CHECKLIST APPLIED:
[x] NO class weights - standard loss only
[x] Correct label mapping: SELL=0, HOLD=1, BUY=2
[x] Memory safe: train one pair at a time, gc.collect()
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
from pathlib import Path
from sklearn.metrics import accuracy_score, confusion_matrix
import joblib
import gc
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================
BASE_DIR = Path(r"C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System")
TRAINING_DIR = BASE_DIR / "training"
MODEL_DIR = BASE_DIR / "trained_models_CLEAN27"

TRAIN_FILE = TRAINING_DIR / "train_CLEAN27.csv"
VAL_FILE = TRAINING_DIR / "val_CLEAN27.csv"

PAIRS = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD', 'EURGBP']
EXCLUDE_COLS = ['timestamp', 'symbol', 'label']

# LightGBM parameters (no class weights!)
LGB_PARAMS = {
    'n_estimators': 200,
    'max_depth': 6,
    'learning_rate': 0.1,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'objective': 'multiclass',
    'num_class': 3,
    'metric': 'multi_logloss',
    'random_state': 42,
    'n_jobs': -1,
    'verbose': -1
    # NO class_weight - causes issues!
}

print("=" * 70)
print("LIGHTGBM TRAINING - CLEAN27 FEATURES - M15 TIMEFRAME")
print("=" * 70)
MODEL_DIR.mkdir(exist_ok=True)


def load_data():
    print("\nLoading data...")
    train_df = pd.read_csv(TRAIN_FILE)
    val_df = pd.read_csv(VAL_FILE)
    print(f"  Train: {len(train_df):,}, Val: {len(val_df):,}")
    return train_df, val_df


def train_pair(pair, train_df, val_df):
    print(f"\n[{pair}] Training LightGBM...")
    
    train_pair = train_df[train_df['symbol'] == pair].copy()
    val_pair = val_df[val_df['symbol'] == pair].copy()
    
    if len(train_pair) == 0:
        print(f"  [SKIP] No data")
        return None
    
    feature_cols = [c for c in train_pair.columns if c not in EXCLUDE_COLS]
    
    X_train = train_pair[feature_cols].values
    y_train = train_pair['label'].values
    X_val = val_pair[feature_cols].values
    y_val = val_pair['label'].values
    
    print(f"  Samples: train={len(X_train):,}, val={len(X_val):,}")
    
    # Train
    model = lgb.LGBMClassifier(**LGB_PARAMS)
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)])
    
    # Evaluate
    y_pred = model.predict(X_val)
    accuracy = accuracy_score(y_val, y_pred)
    unique_preds = len(np.unique(y_pred))
    
    print(f"  Accuracy: {accuracy:.1%}, Unique preds: {unique_preds}")
    
    # Save
    model_path = MODEL_DIR / f"{pair}_lightgbm.joblib"
    joblib.dump(model, model_path)
    print(f"  Saved: {model_path.name}")
    
    return {'pair': pair, 'accuracy': accuracy, 'unique_predictions': unique_preds}


def main():
    train_df, val_df = load_data()
    
    results = []
    for pair in PAIRS:
        result = train_pair(pair, train_df, val_df)
        if result:
            results.append(result)
        gc.collect()
    
    # Summary
    print("\n" + "=" * 70)
    print("LIGHTGBM TRAINING COMPLETE")
    print("=" * 70)
    for r in results:
        print(f"  {r['pair']}: {r['accuracy']:.1%} (preds: {r['unique_predictions']})")
    
    avg_acc = np.mean([r['accuracy'] for r in results])
    print(f"\n  Average: {avg_acc:.1%}")
    print(f"  Models saved to: {MODEL_DIR}")


if __name__ == "__main__":
    main()
