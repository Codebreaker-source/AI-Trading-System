#!/usr/bin/env python3
"""
Train 24 Balanced Ensemble Models
=================================
File: train_balanced_ensemble.py
Date: 2025-12-01

FIXES THE CLASS IMBALANCE PROBLEM:
- Original: 11% SELL, 79% HOLD, 10% BUY  
- Balanced: 33% SELL, 33% HOLD, 33% BUY (via undersampling)

Models: 8 XGBoost + 8 LightGBM + 8 CatBoost = 24 total
Memory: Optimized for 5-8GB RAM
"""

import os
import gc
import pickle
import joblib
import logging
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier

# ============================================================================
# CONFIGURATION
# ============================================================================
BASE_DIR = Path(r"C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System")
TRAINING_DIR = BASE_DIR / "training"

# Output to new directory to preserve old models
OUTPUT_DIR = BASE_DIR / "trained_models_BALANCED"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TRAIN_FILE = TRAINING_DIR / "train_data_24c_10p_105FEAT.csv"
VAL_FILE = TRAINING_DIR / "val_data_24c_10p_105FEAT.csv"

SYMBOLS = ['EURUSD.sim', 'GBPUSD.sim', 'USDJPY.sim', 'USDCHF.sim', 
           'AUDUSD.sim', 'USDCAD.sim', 'NZDUSD.sim', 'EURGBP.sim']

# Samples per class after balancing (reduced for memory)
SAMPLES_PER_CLASS = 5000  # Will have ~15k total samples per symbol

# Setup logging
log_file = TRAINING_DIR / f"training_BALANCED_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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
# DATA LOADING WITH BALANCED UNDERSAMPLING
# ============================================================================

def load_balanced_data(csv_file, symbol, samples_per_class=SAMPLES_PER_CLASS):
    """
    Load data with balanced classes via undersampling.
    Ensures equal representation of SELL, HOLD, BUY.
    """
    logger.info(f"  Loading {symbol} data...")
    
    # Read all data for this symbol
    chunks = []
    for chunk in pd.read_csv(csv_file, chunksize=50000):
        symbol_data = chunk[chunk['symbol'] == symbol]
        if len(symbol_data) > 0:
            chunks.append(symbol_data)
    
    if not chunks:
        logger.warning(f"  No data found for {symbol}")
        return None, None, None
    
    df = pd.concat(chunks, ignore_index=True)
    del chunks
    gc.collect()
    
    # Drop NaN
    df = df.dropna()
    logger.info(f"  Total samples: {len(df):,}")
    
    # Get class distribution
    class_counts = df['label'].value_counts().sort_index()
    logger.info(f"  Original distribution: {class_counts.to_dict()}")
    
    # Find minimum class count
    min_count = class_counts.min()
    target_samples = min(samples_per_class, min_count)
    
    logger.info(f"  Balancing to {target_samples} samples per class...")
    
    # Undersample each class
    balanced_dfs = []
    for label in [0, 1, 2]:  # SELL, HOLD, BUY
        class_df = df[df['label'] == label]
        if len(class_df) >= target_samples:
            sampled = class_df.sample(n=target_samples, random_state=42)
        else:
            sampled = class_df  # Keep all if less than target
        balanced_dfs.append(sampled)
    
    df_balanced = pd.concat(balanced_dfs, ignore_index=True)
    df_balanced = df_balanced.sample(frac=1, random_state=42)  # Shuffle
    
    # Get final distribution
    final_counts = df_balanced['label'].value_counts().sort_index()
    logger.info(f"  Balanced distribution: {final_counts.to_dict()}")
    
    # Extract features
    feature_cols = [c for c in df_balanced.columns if c not in ['timestamp', 'symbol', 'label']]
    
    X = df_balanced[feature_cols].values.astype(np.float32)
    y = df_balanced['label'].values.astype(np.int64)
    
    del df, df_balanced
    gc.collect()
    
    return X, y, feature_cols



# ============================================================================
# MODEL TRAINING FUNCTIONS
# ============================================================================

def train_xgboost(X_train, y_train, X_val, y_val, symbol):
    """Train XGBoost classifier"""
    params = {
        'objective': 'multi:softprob',
        'num_class': 3,
        'max_depth': 6,
        'learning_rate': 0.1,
        'n_estimators': 200,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'random_state': 42,
        'verbosity': 0,
        'tree_method': 'hist',  # Memory efficient
    }
    
    model = xgb.XGBClassifier(**params)
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    
    return model


def train_lightgbm(X_train, y_train, X_val, y_val, symbol):
    """Train LightGBM classifier"""
    params = {
        'objective': 'multiclass',
        'num_class': 3,
        'max_depth': 6,
        'learning_rate': 0.1,
        'n_estimators': 200,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'random_state': 42,
        'verbose': -1,
        'force_col_wise': True,  # Memory efficient
    }
    
    model = lgb.LGBMClassifier(**params)
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)])
    
    return model


def train_catboost(X_train, y_train, X_val, y_val, symbol):
    """Train CatBoost classifier"""
    model = CatBoostClassifier(
        iterations=200,
        depth=6,
        learning_rate=0.1,
        loss_function='MultiClass',
        random_seed=42,
        verbose=False,
        task_type='CPU',
    )
    
    model.fit(X_train, y_train, eval_set=(X_val, y_val), verbose=False)
    
    return model


def evaluate_model(model, X_val, y_val, model_name):
    """Evaluate model and return metrics"""
    preds = model.predict(X_val)
    
    # Handle different prediction formats
    if hasattr(preds, '__len__') and len(preds.shape) > 1:
        preds = preds.argmax(axis=1)
    
    accuracy = (preds == y_val).mean()
    
    # Class-wise accuracy
    class_acc = {}
    for cls in [0, 1, 2]:
        mask = y_val == cls
        if mask.sum() > 0:
            class_acc[cls] = (preds[mask] == y_val[mask]).mean()
        else:
            class_acc[cls] = 0.0
    
    # Prediction distribution
    pred_dist = {}
    for cls in [0, 1, 2]:
        pred_dist[cls] = (preds == cls).sum()
    
    logger.info(f"    {model_name}: Acc={accuracy:.1%} | SELL={class_acc[0]:.1%} HOLD={class_acc[1]:.1%} BUY={class_acc[2]:.1%}")
    logger.info(f"    {model_name} preds: SELL={pred_dist[0]} HOLD={pred_dist[1]} BUY={pred_dist[2]}")
    
    return accuracy, class_acc, pred_dist



# ============================================================================
# SAVE MODELS
# ============================================================================

def save_model(model, symbol, model_type, feature_cols, output_dir):
    """Save model with feature columns"""
    # Create subdirectory for model type
    model_dir = output_dir / model_type
    model_dir.mkdir(parents=True, exist_ok=True)
    
    # Save as dict with model and feature_cols
    save_data = {
        'model': model,
        'feature_cols': feature_cols,
        'symbol': symbol,
        'model_type': model_type,
        'balanced': True,
    }
    
    filename = f"{symbol}_{model_type}_balanced.pkl"
    filepath = model_dir / filename
    
    joblib.dump(save_data, filepath)
    logger.info(f"    Saved: {filepath}")


# ============================================================================
# MAIN TRAINING LOOP
# ============================================================================

def main():
    print("=" * 80)
    print("TRAINING 24 BALANCED ENSEMBLE MODELS")
    print("=" * 80)
    print("Using UNDERSAMPLING to balance classes: 33% SELL, 33% HOLD, 33% BUY")
    print("=" * 80)
    
    logger.info("=" * 80)
    logger.info("BALANCED ENSEMBLE TRAINING")
    logger.info("=" * 80)
    
    all_results = {}
    
    for i, symbol in enumerate(SYMBOLS, 1):
        print(f"\n{'=' * 80}")
        print(f"[{i}/8] TRAINING: {symbol}")
        print("=" * 80)
        
        logger.info(f"\n[{i}/8] TRAINING: {symbol}")
        
        # Load balanced training data
        X_train, y_train, feature_cols = load_balanced_data(TRAIN_FILE, symbol)
        
        if X_train is None:
            logger.warning(f"  Skipping {symbol} - no data")
            continue
        
        # Load validation data (keep imbalanced for realistic evaluation)
        logger.info(f"  Loading validation data...")
        val_chunks = []
        for chunk in pd.read_csv(VAL_FILE, chunksize=50000):
            symbol_data = chunk[chunk['symbol'] == symbol]
            if len(symbol_data) > 0:
                val_chunks.append(symbol_data)
        
        if not val_chunks:
            logger.warning(f"  No validation data for {symbol}")
            continue
        
        val_df = pd.concat(val_chunks, ignore_index=True).dropna()
        X_val = val_df[feature_cols].values.astype(np.float32)
        y_val = val_df['label'].values.astype(np.int64)
        
        logger.info(f"  Train: {len(X_train):,} | Val: {len(X_val):,}")
        logger.info(f"  Val distribution: {dict(zip(*np.unique(y_val, return_counts=True)))}")
        
        symbol_results = {}
        
        # Train XGBoost
        print(f"\n  Training XGBoost...")
        logger.info(f"  Training XGBoost...")
        xgb_model = train_xgboost(X_train, y_train, X_val, y_val, symbol)
        acc, class_acc, pred_dist = evaluate_model(xgb_model, X_val, y_val, "XGBoost")
        save_model(xgb_model, symbol, 'xgboost', feature_cols, OUTPUT_DIR)
        symbol_results['xgboost'] = {'accuracy': acc, 'class_acc': class_acc, 'pred_dist': pred_dist}
        del xgb_model
        gc.collect()
        
        # Train LightGBM
        print(f"  Training LightGBM...")
        logger.info(f"  Training LightGBM...")
        lgb_model = train_lightgbm(X_train, y_train, X_val, y_val, symbol)
        acc, class_acc, pred_dist = evaluate_model(lgb_model, X_val, y_val, "LightGBM")
        save_model(lgb_model, symbol, 'lightgbm', feature_cols, OUTPUT_DIR)
        symbol_results['lightgbm'] = {'accuracy': acc, 'class_acc': class_acc, 'pred_dist': pred_dist}
        del lgb_model
        gc.collect()
        
        # Train CatBoost
        print(f"  Training CatBoost...")
        logger.info(f"  Training CatBoost...")
        cb_model = train_catboost(X_train, y_train, X_val, y_val, symbol)
        acc, class_acc, pred_dist = evaluate_model(cb_model, X_val, y_val, "CatBoost")
        save_model(cb_model, symbol, 'catboost', feature_cols, OUTPUT_DIR)
        symbol_results['catboost'] = {'accuracy': acc, 'class_acc': class_acc, 'pred_dist': pred_dist}
        del cb_model
        gc.collect()
        
        all_results[symbol] = symbol_results
        
        # Cleanup
        del X_train, y_train, X_val, y_val, val_df
        gc.collect()
        
        print(f"  ✅ {symbol} complete!")
    
    # Print summary
    print("\n" + "=" * 80)
    print("TRAINING COMPLETE - SUMMARY")
    print("=" * 80)
    
    logger.info("\n" + "=" * 80)
    logger.info("TRAINING COMPLETE - SUMMARY")
    logger.info("=" * 80)
    
    for symbol, results in all_results.items():
        print(f"\n{symbol}:")
        logger.info(f"\n{symbol}:")
        for model_type, metrics in results.items():
            acc = metrics['accuracy']
            sell_preds = metrics['pred_dist'][0]
            hold_preds = metrics['pred_dist'][1]
            buy_preds = metrics['pred_dist'][2]
            print(f"  {model_type:12}: Acc={acc:.1%} | Preds: SELL={sell_preds}, HOLD={hold_preds}, BUY={buy_preds}")
            logger.info(f"  {model_type:12}: Acc={acc:.1%} | Preds: SELL={sell_preds}, HOLD={hold_preds}, BUY={buy_preds}")
    
    print(f"\n✅ All 24 models saved to: {OUTPUT_DIR}")
    logger.info(f"\n✅ All 24 models saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
