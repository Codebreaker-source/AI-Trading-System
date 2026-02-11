#!/usr/bin/env python3
"""
XGBoost Training Script - CLEAN27 Features - M15 Timeframe
===========================================================
File: train_xgboost_CLEAN27.py
Date: 2025-12-03

PREVENTION CHECKLIST APPLIED:
[x] NO class weights - standard loss only (tree models work fine without)
[x] NO focal loss - causes model collapse
[x] Correct label mapping: SELL=0, HOLD=1, BUY=2
[x] Memory safe: train one pair at a time, gc.collect()
[x] Save models per pair to trained_models_CLEAN27/

TRAINING APPROACH:
- Use XGBoost with default parameters first
- Train one model per pair (8 models total)
- Validate on held-out validation set
- Save best model per pair
"""

import pandas as pd
import numpy as np
import xgboost as xgb
from pathlib import Path
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
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
TEST_FILE = TRAINING_DIR / "test_CLEAN27.csv"

PAIRS = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD', 'EURGBP']

# Features to use (exclude metadata columns)
EXCLUDE_COLS = ['timestamp', 'symbol', 'label']

# XGBoost parameters (conservative defaults - no class weights!)
XGB_PARAMS = {
    'n_estimators': 200,
    'max_depth': 6,
    'learning_rate': 0.1,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'objective': 'multi:softprob',
    'num_class': 3,
    'eval_metric': 'mlogloss',
    'random_state': 42,
    'n_jobs': -1,
    'verbosity': 1
    # NO scale_pos_weight - causes issues!
}

print("=" * 70)
print("XGBOOST TRAINING - CLEAN27 FEATURES - M15 TIMEFRAME")
print("=" * 70)
print(f"Train file: {TRAIN_FILE}")
print(f"Val file: {VAL_FILE}")
print(f"Model output: {MODEL_DIR}")
print(f"Pairs: {PAIRS}")
print("=" * 70)

# Create model directory
MODEL_DIR.mkdir(exist_ok=True)


# ============================================================================
# LOAD DATA
# ============================================================================
def load_data():
    """Load train and validation data"""
    print("\nLoading training data...")
    train_df = pd.read_csv(TRAIN_FILE)
    print(f"  Train: {len(train_df):,} rows")
    
    print("Loading validation data...")
    val_df = pd.read_csv(VAL_FILE)
    print(f"  Val: {len(val_df):,} rows")
    
    return train_df, val_df


# ============================================================================
# TRAIN MODEL FOR ONE PAIR
# ============================================================================
def train_pair(pair, train_df, val_df):
    """Train XGBoost model for one pair"""
    
    print(f"\n{'='*50}")
    print(f"[{pair}] Training XGBoost...")
    print(f"{'='*50}")
    
    # Filter data for this pair
    train_pair = train_df[train_df['symbol'] == pair].copy()
    val_pair = val_df[val_df['symbol'] == pair].copy()
    
    if len(train_pair) == 0:
        print(f"  [SKIP] No training data for {pair}")
        return None
    
    if len(val_pair) == 0:
        print(f"  [WARNING] No validation data for {pair}")
    
    print(f"  Train samples: {len(train_pair):,}")
    print(f"  Val samples: {len(val_pair):,}")
    
    # Get feature columns
    feature_cols = [c for c in train_pair.columns if c not in EXCLUDE_COLS]
    print(f"  Features: {len(feature_cols)}")
    
    # Prepare data
    X_train = train_pair[feature_cols].values
    y_train = train_pair['label'].values
    X_val = val_pair[feature_cols].values
    y_val = val_pair['label'].values
    
    # Check label distribution
    train_labels = pd.Series(y_train).value_counts().sort_index()
    print(f"  Train label distribution:")
    for label, count in train_labels.items():
        pct = count / len(y_train) * 100
        label_name = ['SELL', 'HOLD', 'BUY'][int(label)]
        print(f"    {label_name} ({label}): {count:,} ({pct:.1f}%)")
    
    # Train model
    print(f"  Training...")
    model = xgb.XGBClassifier(**XGB_PARAMS)
    
    # Fit with early stopping
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=False
    )
    
    # Evaluate on validation set
    print(f"  Evaluating...")
    y_pred = model.predict(X_val)
    accuracy = accuracy_score(y_val, y_pred)
    
    print(f"  Validation Accuracy: {accuracy:.4f} ({accuracy*100:.1f}%)")
    
    # Per-class accuracy
    print(f"  Per-class results:")
    for label in [0, 1, 2]:
        label_name = ['SELL', 'HOLD', 'BUY'][label]
        mask = y_val == label
        if mask.sum() > 0:
            class_acc = (y_pred[mask] == y_val[mask]).mean()
            print(f"    {label_name}: {class_acc:.1%}")
    
    # Confusion matrix
    cm = confusion_matrix(y_val, y_pred)
    print(f"  Confusion Matrix:")
    print(f"           Pred SELL  Pred HOLD  Pred BUY")
    print(f"    SELL:  {cm[0,0]:>8}   {cm[0,1]:>8}   {cm[0,2]:>8}")
    print(f"    HOLD:  {cm[1,0]:>8}   {cm[1,1]:>8}   {cm[1,2]:>8}")
    print(f"    BUY:   {cm[2,0]:>8}   {cm[2,1]:>8}   {cm[2,2]:>8}")
    
    # Check for lazy prediction (all same class)
    unique_preds = len(np.unique(y_pred))
    if unique_preds < 3:
        print(f"  [WARNING] Model only predicts {unique_preds} classes!")
    
    # Save model
    model_path = MODEL_DIR / f"{pair}_xgboost.joblib"
    joblib.dump(model, model_path)
    print(f"  Saved: {model_path.name}")
    
    # Save feature list
    features_path = MODEL_DIR / f"{pair}_features.txt"
    with open(features_path, 'w') as f:
        f.write('\n'.join(feature_cols))
    
    return {
        'pair': pair,
        'accuracy': accuracy,
        'train_samples': len(train_pair),
        'val_samples': len(val_pair),
        'unique_predictions': unique_preds
    }


# ============================================================================
# MAIN
# ============================================================================
def main():
    # Load data
    train_df, val_df = load_data()
    
    # Train each pair
    results = []
    for pair in PAIRS:
        result = train_pair(pair, train_df, val_df)
        if result:
            results.append(result)
        
        # Memory cleanup
        gc.collect()
    
    # Summary
    print("\n" + "=" * 70)
    print("TRAINING COMPLETE - SUMMARY")
    print("=" * 70)
    
    print(f"\n{'Pair':<12} {'Accuracy':>10} {'Train':>10} {'Val':>10} {'Preds':>8}")
    print("-" * 55)
    for r in results:
        print(f"{r['pair']:<12} {r['accuracy']:>9.1%} {r['train_samples']:>10,} {r['val_samples']:>10,} {r['unique_predictions']:>8}")
    
    # Average accuracy
    avg_acc = np.mean([r['accuracy'] for r in results])
    print("-" * 55)
    print(f"{'AVERAGE':<12} {avg_acc:>9.1%}")
    
    # Check for issues
    lazy_models = [r['pair'] for r in results if r['unique_predictions'] < 3]
    if lazy_models:
        print(f"\n[WARNING] These models predict fewer than 3 classes: {lazy_models}")
    
    print(f"\nModels saved to: {MODEL_DIR}")
    
    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print("1. Train LightGBM: python train_lightgbm_CLEAN27.py")
    print("2. Train CatBoost: python train_catboost_CLEAN27.py")
    print("3. Create ensemble predictor")
    print("4. Deploy to live system")


if __name__ == "__main__":
    main()
