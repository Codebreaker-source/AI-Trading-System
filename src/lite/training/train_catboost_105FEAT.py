#!/usr/bin/env python3
"""
CatBoost Training Script - 105 Features
========================================
File: train_catboost_105FEAT.py
Date: 2025-11-29

Trains CatBoost models for all 8 currency pairs.
CatBoost uses ordered boosting and handles class imbalance well.

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
from catboost import CatBoostClassifier, Pool
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================
BASE_DIR = Path(r"C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System")
TRAINING_DIR = BASE_DIR / "training"
MODEL_DIR = BASE_DIR / "trained_models_105FEAT" / "catboost"
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

# CatBoost hyperparameters (similar to XGBoost for fair comparison)
CATBOOST_PARAMS = {
    'iterations': 200,
    'depth': 6,
    'learning_rate': 0.1,
    'loss_function': 'MultiClass',
    'eval_metric': 'Accuracy',
    'random_seed': 42,
    'l2_leaf_reg': 3.0,  # L2 regularization
    'bootstrap_type': 'Bernoulli',
    'subsample': 0.8,
    'rsm': 0.8,  # Random subspace method (like colsample_bytree)
    # NOTE: Removed auto_class_weights='Balanced' - it was causing model collapse
    'verbose': False,
    'allow_writing_files': False,
    'thread_count': -1,
}

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(TRAINING_DIR / 'catboost_training.log'),
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


def train_catboost(symbol: str) -> tuple:
    """Train CatBoost model for a single symbol"""
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
    
    # Create CatBoost pools (native data format)
    train_pool = Pool(X_train, y_train, feature_names=feature_cols)
    val_pool = Pool(X_val, y_val, feature_names=feature_cols)
    
    # Create CatBoost model
    model = CatBoostClassifier(**CATBOOST_PARAMS)
    
    # Train with early stopping
    model.fit(
        train_pool,
        eval_set=val_pool,
        early_stopping_rounds=20,
        verbose=False
    )
    
    # Evaluate
    train_pred = model.predict(X_train).flatten()
    val_pred = model.predict(X_val).flatten()
    
    train_acc = accuracy_score(y_train, train_pred)
    val_acc = accuracy_score(y_val, val_pred)
    
    # Check which classes are being predicted
    pred_classes = sorted(list(set(val_pred.astype(int))))
    logger.info(f"  Predicting classes: {pred_classes}")
    
    # Detailed metrics
    logger.info(f"  Train Accuracy: {train_acc:.4f}")
    logger.info(f"  Val Accuracy: {val_acc:.4f}")
    logger.info(f"  Best iteration: {model.best_iteration_}")
    
    # Save model
    model_path = MODEL_DIR / f"{symbol}_catboost_105feat.pkl"
    joblib.dump({
        'model': model,
        'feature_cols': feature_cols,
        'train_acc': train_acc,
        'val_acc': val_acc,
        'best_iteration': model.best_iteration_
    }, model_path)
    logger.info(f"  Saved: {model_path.name}")
    
    # Also save native CatBoost format
    native_path = MODEL_DIR / f"{symbol}_catboost_105feat.cbm"
    model.save_model(str(native_path))
    
    return model, train_acc, val_acc


def main():
    """Train CatBoost models for all symbols"""
    print("=" * 80)
    print("TRAINING 8 CatBoost MODELS - 105 FEATURES")
    print("=" * 80)
    
    logger.info("=" * 80)
    logger.info("CatBoost TRAINING - 105 FEATURES")
    logger.info("=" * 80)
    logger.info(f"Train file: {TRAIN_FILE}")
    logger.info(f"Val file: {VAL_FILE}")
    logger.info(f"Output: {MODEL_DIR}")
    logger.info(f"Parameters: {CATBOOST_PARAMS}")
    logger.info("=" * 80)
    
    results = {}
    
    for i, symbol in enumerate(SYMBOLS, 1):
        print(f"\n{'=' * 80}")
        print(f"[{i}/8] TRAINING CatBoost: {symbol}")
        print("=" * 80)
        
        logger.info(f"\n{'=' * 80}")
        logger.info(f"[{i}/8] TRAINING CatBoost: {symbol}")
        logger.info("=" * 80)
        
        try:
            model, train_acc, val_acc = train_catboost(symbol)
            
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
    print("CatBoost TRAINING COMPLETE")
    print("=" * 80)
    
    logger.info(f"\n{'=' * 80}")
    logger.info("CatBoost TRAINING COMPLETE")
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
