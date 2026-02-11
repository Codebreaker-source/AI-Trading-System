#!/usr/bin/env python3
"""
Train 8 XGBoost Models on 105 Features
=======================================
File: train_xgboost_105FEAT.py
Date: 2025-11-29

XGBoost is the most reliable model type.
Uses class weights via sample_weight for imbalanced data.

Models: 8 XGBoost (one per currency pair)
"""

import os
import gc
import pickle
import logging
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np
from sklearn.utils.class_weight import compute_class_weight
import xgboost as xgb

# ============================================================================
# CONFIGURATION
# ============================================================================
BASE_DIR = Path(r"C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System")
TRAINING_DIR = BASE_DIR / "training"
OUTPUT_DIR = BASE_DIR / "trained_models_105FEAT" / "xgboost"

TRAIN_FILE = TRAINING_DIR / "train_data_24c_10p_105FEAT.csv"
VAL_FILE = TRAINING_DIR / "val_data_24c_10p_105FEAT.csv"

SYMBOLS = ['EURUSD.sim', 'GBPUSD.sim', 'USDJPY.sim', 'USDCHF.sim', 
           'AUDUSD.sim', 'USDCAD.sim', 'NZDUSD.sim', 'EURGBP.sim']

MAX_SAMPLES = 50000
CHUNK_SIZE = 25000

# Create output directory
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging
log_file = TRAINING_DIR / f"training_XGBOOST_105FEAT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# DATA LOADING (CHUNKED + DROPNA)
# ============================================================================

def load_symbol_data(csv_file, symbol, max_samples=MAX_SAMPLES):
    """Load data for a specific symbol with chunked reading and NaN removal"""
    chunks = []
    total_loaded = 0
    
    logger.info(f"  Loading {symbol} in chunks...")
    
    for chunk in pd.read_csv(csv_file, chunksize=CHUNK_SIZE):
        symbol_data = chunk[chunk['symbol'] == symbol]
        if len(symbol_data) > 0:
            chunks.append(symbol_data)
            total_loaded += len(symbol_data)
            if total_loaded >= max_samples * 2:
                break
    
    if not chunks:
        return None, None, None
    
    df = pd.concat(chunks, ignore_index=True)
    del chunks
    gc.collect()
    
    # Drop NaN rows
    original_len = len(df)
    df = df.dropna()
    dropped = original_len - len(df)
    if dropped > 0:
        logger.info(f"  Dropped {dropped} NaN rows ({dropped/original_len*100:.1f}%)")
    
    # Sample if too large
    if len(df) > max_samples:
        df = df.sample(n=max_samples, random_state=42)
        logger.info(f"  Sampled {len(df):,} rows")
    
    # Get feature columns (exclude timestamp, symbol, label)
    feature_cols = [c for c in df.columns if c not in ['timestamp', 'symbol', 'label']]
    
    X = df[feature_cols].values.astype(np.float32)
    y = df['label'].values.astype(np.int64)
    
    return X, y, len(feature_cols)


# ============================================================================
# TRAINING FUNCTION
# ============================================================================

def train_xgboost(X_train, y_train, X_val, y_val, symbol):
    """Train XGBoost with class weights"""
    # Calculate class weights
    classes = np.unique(y_train)
    weights = compute_class_weight('balanced', classes=classes, y=y_train)
    
    logger.info(f"  Class weights: {dict(zip(classes.tolist(), weights.round(2).tolist()))}")
    
    # Sample weights
    sample_weights = np.ones(len(y_train))
    for i, cls in enumerate(classes):
        sample_weights[y_train == cls] = weights[i]
    
    # XGBoost parameters
    params = {
        'objective': 'multi:softprob',
        'num_class': 3,
        'max_depth': 6,
        'learning_rate': 0.1,
        'n_estimators': 200,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'random_state': 42,
        'verbosity': 0
    }
    
    model = xgb.XGBClassifier(**params)
    model.fit(X_train, y_train, sample_weight=sample_weights,
              eval_set=[(X_val, y_val)], verbose=False)
    
    # Evaluate
    train_preds = model.predict(X_train)
    val_preds = model.predict(X_val)
    
    train_acc = (train_preds == y_train).mean()
    val_acc = (val_preds == y_val).mean()
    
    # Check class distribution in predictions
    unique_preds = np.unique(val_preds)
    logger.info(f"  Predicting classes: {sorted(unique_preds.tolist())}")
    
    return model, train_acc, val_acc


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("="*80)
    print("TRAINING 8 XGBOOST MODELS - 105 FEATURES")
    print("="*80)
    logger.info("="*80)
    logger.info("XGBOOST TRAINING - 105 FEATURES")
    logger.info("="*80)
    logger.info(f"Train file: {TRAIN_FILE}")
    logger.info(f"Val file: {VAL_FILE}")
    logger.info(f"Output: {OUTPUT_DIR}")
    logger.info("="*80)
    
    results = {}
    
    for i, symbol in enumerate(SYMBOLS, 1):
        print(f"\n{'='*80}")
        print(f"[{i}/8] TRAINING XGBOOST: {symbol}")
        print("="*80)
        logger.info(f"\n{'='*80}")
        logger.info(f"[{i}/8] TRAINING XGBOOST: {symbol}")
        logger.info("="*80)
        
        try:
            # Load training data
            X_train, y_train, num_features = load_symbol_data(TRAIN_FILE, symbol)
            if X_train is None:
                logger.error(f"No training data for {symbol}")
                print(f"  ERROR: No training data for {symbol}")
                continue
            
            # Load validation data
            X_val, y_val, _ = load_symbol_data(VAL_FILE, symbol)
            if X_val is None:
                logger.error(f"No validation data for {symbol}")
                print(f"  ERROR: No validation data for {symbol}")
                continue
            
            logger.info(f"  Train: {len(X_train):,} samples, {num_features} features")
            logger.info(f"  Val: {len(X_val):,} samples")
            print(f"  Train: {len(X_train):,} | Val: {len(X_val):,} | Features: {num_features}")
            
            # Class distribution
            unique, counts = np.unique(y_train, return_counts=True)
            dist = {int(k): int(v) for k, v in zip(unique, counts)}
            logger.info(f"  Class distribution: {dist}")
            print(f"  Classes: {dist}")
            
            # Train XGBoost
            model, train_acc, val_acc = train_xgboost(X_train, y_train, X_val, y_val, symbol)
            
            # Save model
            model_path = OUTPUT_DIR / f"{symbol}_xgboost.pkl"
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)
            
            results[symbol] = val_acc
            
            logger.info(f"  Train Acc: {train_acc:.4f}")
            logger.info(f"  Val Acc: {val_acc:.4f}")
            logger.info(f"  Saved: {model_path.name}")
            
            print(f"  ✓ Train: {train_acc:.4f} | Val: {val_acc:.4f}")
            print(f"  ✓ Saved: {model_path.name}")
            
            # Cleanup
            del model, X_train, y_train, X_val, y_val
            gc.collect()
            
        except Exception as e:
            logger.error(f"Failed to train {symbol}: {e}")
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    # Final summary
    print("\n" + "="*80)
    print("XGBOOST TRAINING COMPLETE")
    print("="*80)
    logger.info("\n" + "="*80)
    logger.info("XGBOOST TRAINING COMPLETE")
    logger.info("="*80)
    
    for symbol, acc in results.items():
        status = "✓" if acc >= 0.90 else "⚠️" if acc >= 0.80 else "❌"
        print(f"  {status} {symbol}: {acc:.4f}")
        logger.info(f"  {symbol}: {acc:.4f}")
    
    avg_acc = np.mean(list(results.values())) if results else 0
    print(f"\n  Average: {avg_acc:.4f}")
    print(f"  Models saved to: {OUTPUT_DIR}")
    logger.info(f"Average accuracy: {avg_acc:.4f}")
    logger.info(f"Models saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
