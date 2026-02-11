#!/usr/bin/env python3
"""
LightGBM Training Script - 105 Features
========================================
File: train_lightgbm_105FEAT.py
Date: 2025-11-29

Trains LightGBM models for all 8 currency pairs.
LightGBM uses histogram-based gradient boosting for faster training.

Part of 3-model tree ensemble: XGBoost + LightGBM + CatBoost
"""

import os
import sys
import logging
import warnings
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import joblib
import lightgbm as lgb
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================
BASE_DIR = Path(r"C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System")
TRAINING_DIR = BASE_DIR / "training"
MODEL_DIR = BASE_DIR / "trained_models_105FEAT" / "lightgbm"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# Data files
TRAIN_FILE = TRAINING_DIR / "train_data_24c_10p_105FEAT.csv"
VAL_FILE = TRAINING_DIR / "val_data_24c_10p_105FEAT.csv"

# Symbols to train
SYMBOLS = [
    'EURUSD.sim', 'GBPUSD.sim', 'USDJPY.sim', 'USDCHF.sim',
    'AUDUSD.sim', 'USDCAD.sim', 'NZDUSD.sim', 'EURGBP.sim'
]

# Features to exclude
EXCLUDE_COLS = ['timestamp', 'symbol', 'label']

# LightGBM hyperparameters (similar to XGBoost for fair comparison)
LGBM_PARAMS = {
    'objective': 'multiclass',
    'num_class': 3,
    'boosting_type': 'gbdt',
    'n_estimators': 200,
    'max_depth': 6,
    'num_leaves': 31,  # 2^5 - 1, consistent with max_depth
    'learning_rate': 0.1,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'reg_alpha': 0.1,  # L1 regularization
    'reg_lambda': 1.0,  # L2 regularization
    'min_child_samples': 20,
    'random_state': 42,
    'n_jobs': -1,
    'verbose': -1,
    'force_col_wise': True,  # Faster for smaller datasets
}

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(TRAINING_DIR / 'lightgbm_training.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_data_for_symbol(filepath: Path, symbol: str, max_samples: int = None) -> pd.DataFrame:
    """Load data for a specific symbol using chunked reading"""
    chunks = []
    chunk_size = 50000
    
    for chunk in pd.read_csv(filepath, chunksize=chunk_size):
        symbol_data = chunk[chunk['symbol'] == symbol]
        if len(symbol_data) > 0:
            chunks.append(symbol_data)
    
    if not chunks:
        return pd.DataFrame()
    
    df = pd.concat(chunks, ignore_index=True)
    
    # Sample if too large
    if max_samples and len(df) > max_samples:
        df = df.sample(n=max_samples, random_state=42)
    
    return df


def prepare_features(df: pd.DataFrame) -> tuple:
    """Extract features and labels from dataframe"""
    # Get feature columns
    feature_cols = [c for c in df.columns if c not in EXCLUDE_COLS]
    
    X = df[feature_cols].copy()
    y = df['label'].values
    
    # Handle any NaN/inf values
    X = X.replace([np.inf, -np.inf], np.nan)
    X = X.fillna(0)
    
    return X, y, feature_cols


def compute_class_weights(y: np.ndarray) -> dict:
    """Compute balanced class weights"""
    classes, counts = np.unique(y, return_counts=True)
    total = len(y)
    weights = {}
    for cls, count in zip(classes, counts):
        weights[int(cls)] = total / (len(classes) * count)
    return weights


def train_lightgbm(symbol: str) -> tuple:
    """Train LightGBM model for a single symbol"""
    logger.info(f"Loading {symbol} data...")
    
    # Load training data
    train_df = load_data_for_symbol(TRAIN_FILE, symbol, max_samples=100000)
    if len(train_df) == 0:
        logger.error(f"No training data for {symbol}")
        return None, 0, 0
    
    # Load validation data
    val_df = load_data_for_symbol(VAL_FILE, symbol)
    if len(val_df) == 0:
        logger.error(f"No validation data for {symbol}")
        return None, 0, 0
    
    # Prepare features
    X_train, y_train, feature_cols = prepare_features(train_df)
    X_val, y_val, _ = prepare_features(val_df)
    
    logger.info(f"  Train: {len(X_train):,} samples, {len(feature_cols)} features")
    logger.info(f"  Val: {len(X_val):,} samples")
    
    # Class distribution
    classes, counts = np.unique(y_train, return_counts=True)
    class_dist = dict(zip(classes.astype(int), counts))
    logger.info(f"  Class distribution: {class_dist}")
    
    # NOTE: Removed aggressive class weighting - it was causing model collapse
    # XGBoost works without it, so LightGBM should too
    logger.info(f"  Training without class weights (matching XGBoost approach)")
    
    # Create LightGBM model - no class weighting
    model = lgb.LGBMClassifier(**LGBM_PARAMS)
    
    # Train with early stopping
    model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        eval_metric='multi_logloss',
        callbacks=[
            lgb.early_stopping(stopping_rounds=20, verbose=False),
            lgb.log_evaluation(period=0)  # Suppress iteration output
        ]
    )
    
    # Evaluate
    train_pred = model.predict(X_train)
    val_pred = model.predict(X_val)
    
    train_acc = accuracy_score(y_train, train_pred)
    val_acc = accuracy_score(y_val, val_pred)
    
    # Check which classes are being predicted
    pred_classes = sorted(list(set(val_pred)))
    logger.info(f"  Predicting classes: {pred_classes}")
    
    # Detailed metrics
    logger.info(f"  Train Accuracy: {train_acc:.4f}")
    logger.info(f"  Val Accuracy: {val_acc:.4f}")
    
    # Save model
    model_path = MODEL_DIR / f"{symbol}_lightgbm_105feat.pkl"
    joblib.dump({
        'model': model,
        'feature_cols': feature_cols,
        'train_acc': train_acc,
        'val_acc': val_acc,
        'n_estimators': model.n_estimators_,
        'best_iteration': model.best_iteration_
    }, model_path)
    logger.info(f"  Saved: {model_path.name}")
    
    return model, train_acc, val_acc


def main():
    """Train LightGBM models for all symbols"""
    print("=" * 80)
    print("TRAINING 8 LightGBM MODELS - 105 FEATURES")
    print("=" * 80)
    
    logger.info("=" * 80)
    logger.info("LightGBM TRAINING - 105 FEATURES")
    logger.info("=" * 80)
    logger.info(f"Train file: {TRAIN_FILE}")
    logger.info(f"Val file: {VAL_FILE}")
    logger.info(f"Output: {MODEL_DIR}")
    logger.info(f"Parameters: {LGBM_PARAMS}")
    logger.info("=" * 80)
    
    results = {}
    
    for i, symbol in enumerate(SYMBOLS, 1):
        print(f"\n{'=' * 80}")
        print(f"[{i}/8] TRAINING LightGBM: {symbol}")
        print("=" * 80)
        
        logger.info(f"\n{'=' * 80}")
        logger.info(f"[{i}/8] TRAINING LightGBM: {symbol}")
        logger.info("=" * 80)
        
        try:
            model, train_acc, val_acc = train_lightgbm(symbol)
            
            if model is not None:
                results[symbol] = {
                    'train_acc': train_acc,
                    'val_acc': val_acc,
                    'status': 'OK' if val_acc >= 0.70 else 'WARN' if val_acc >= 0.50 else 'FAIL'
                }
                status = results[symbol]['status']
                print(f"  {status} Train: {train_acc:.4f} | Val: {val_acc:.4f}")
            else:
                results[symbol] = {'train_acc': 0, 'val_acc': 0, 'status': 'ERROR'}
                print(f"  ERROR: Failed to train")
                
        except Exception as e:
            logger.error(f"Error training {symbol}: {e}")
            import traceback
            traceback.print_exc()
            results[symbol] = {'train_acc': 0, 'val_acc': 0, 'status': 'ERROR', 'error': str(e)}
    
    # Summary
    print(f"\n{'=' * 80}")
    print("LightGBM TRAINING COMPLETE")
    print("=" * 80)
    
    logger.info(f"\n{'=' * 80}")
    logger.info("LightGBM TRAINING COMPLETE")
    logger.info("=" * 80)
    
    total_acc = 0
    valid_count = 0
    
    for symbol, res in results.items():
        status = res['status']
        val_acc = res['val_acc']
        
        if status == 'OK':
            print(f"  OK   {symbol}: {val_acc:.4f}")
        elif status == 'WARN':
            print(f"  WARN {symbol}: {val_acc:.4f}")
        elif status == 'FAIL':
            print(f"  FAIL {symbol}: {val_acc:.4f}")
        else:
            print(f"  ERR  {symbol}: {res.get('error', 'Unknown error')}")
        
        logger.info(f"  {symbol}: {val_acc:.4f}")
        
        if status != 'ERROR':
            total_acc += val_acc
            valid_count += 1
    
    if valid_count > 0:
        avg_acc = total_acc / valid_count
        print(f"\n  Average: {avg_acc:.4f}")
        print(f"  Models saved to: {MODEL_DIR}")
        logger.info(f"Average accuracy: {avg_acc:.4f}")
        logger.info(f"Models saved to: {MODEL_DIR}")


if __name__ == "__main__":
    main()
