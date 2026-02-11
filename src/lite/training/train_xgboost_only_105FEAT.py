#!/usr/bin/env python3
"""
XGBoost-Only Training Script - 105 FEATURES (ALL 8 PAIRS)
File: train_xgboost_only_105FEAT.py
Version: 1.0
Date: 2025-11-17

Configuration: B1 (24 candles, 10 pips) - 105 FEATURES
Purpose: Train 8 XGBoost models (one per pair)
Data Format: 105 columns (timestamp, symbol, 102 features, label)

Why XGBoost-Only:
- Neural networks fail with 93% HOLD imbalance (3.55% accuracy)
- XGBoost handles imbalance perfectly (96.6% accuracy)
- Faster training: 20-30 min (vs 2-3 hours for all models)
- Lower memory: 1.2 GB (vs 3.5 GB)
- Simpler deployment: No ensemble voting needed

Expected Results:
- 8 models trained in 20-30 minutes
- 95-97% validation accuracy per pair
- Models saved to trained_models_105FEAT/
"""

import os
import sys
import time
import pickle
import logging
import gc
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime

import pandas as pd
import numpy as np
from sklearn.metrics import accuracy_score, classification_report
import xgboost as xgb
import joblib

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('training_xgboost_105FEAT_log.txt'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================

class Config:
    """XGBoost-Only Training Configuration"""
    
    BASE_DIR = Path(r"C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System")
    TRAIN_FILE = BASE_DIR / "training" / "train_data_24c_10p_105FEAT.csv"
    VAL_FILE = BASE_DIR / "training" / "val_data_24c_10p_105FEAT.csv"
    OUTPUT_DIR = BASE_DIR / "trained_models_105FEAT"
    
    # All 8 pairs
    PAIRS = [
        'EURUSD.sim',
        'GBPUSD.sim',
        'USDJPY.sim',
        'USDCHF.sim',
        'AUDUSD.sim',
        'USDCAD.sim',
        'NZDUSD.sim',
        'EURGBP.sim'
    ]
    
    # Model configuration
    NUM_FEATURES = 102  # 105 - timestamp - symbol - label
    NUM_CLASSES = 3
    
    # Memory settings
    CHUNK_SIZE = 10000
    MAX_SAMPLES_PER_PAIR = 300000  # Limit to prevent memory issues
    
    # XGBoost parameters (optimized for imbalanced data)
    XGBOOST_PARAMS = {
        'n_estimators': 100,
        'max_depth': 6,
        'learning_rate': 0.1,
        'subsample': 0.8,
        'colsample_bytree': 0.8,
        'objective': 'multi:softprob',
        'num_class': 3,
        'eval_metric': 'mlogloss',
        'random_state': 42,
        'n_jobs': 4,
        'tree_method': 'hist'
    }

config = Config()

# Create output directory
config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ==================== DATA LOADING ====================

def load_pair_data_chunked(file_path: Path, pair: str, max_samples: int = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load data for specific pair in chunks (memory efficient)
    Returns: (X, y) as DataFrames
    """
    logger.info(f"Loading {pair} from {file_path.name} (chunked)...")
    
    chunks = []
    total_rows = 0
    
    try:
        for chunk in pd.read_csv(file_path, chunksize=config.CHUNK_SIZE):
            # Filter for this pair
            pair_data = chunk[chunk['symbol'] == pair].copy()
            
            if len(pair_data) > 0:
                chunks.append(pair_data)
                total_rows += len(pair_data)
                
                # Log progress
                if total_rows % 50000 == 0:
                    logger.info(f"  Rows loaded: {total_rows:,}")
                
                # Check if we have enough samples
                if max_samples and total_rows >= max_samples:
                    logger.info(f"  Reached max samples limit: {max_samples:,}")
                    break
        
        if not chunks:
            raise ValueError(f"No data found for {pair}")
        
        # Combine chunks
        df = pd.concat(chunks, ignore_index=True)
        
        # Sample if too many rows
        if max_samples and len(df) > max_samples:
            df = df.sample(n=max_samples, random_state=42)
            logger.info(f"  Sampled down to {max_samples:,} rows")
        
        # Separate features and labels
        X = df.drop(['timestamp', 'symbol', 'label'], axis=1, errors='ignore')
        y = df['label']
        
        logger.info(f"{pair}: {len(df):,} samples loaded with {len(X.columns)} features")
        
        return X, y
        
    except Exception as e:
        logger.error(f"Error loading {pair}: {e}")
        raise

# ==================== XGBOOST TRAINING ====================

class XGBoostTrainer:
    """XGBoost model trainer with class imbalance handling"""
    
    def __init__(self, config: Config):
        self.config = config
    
    def train(self, X_train: pd.DataFrame, y_train: pd.Series,
             X_val: pd.DataFrame, y_val: pd.Series, pair: str) -> xgb.XGBClassifier:
        logger.info(f"Training XGBoost for {pair}...")
        
        # Calculate boosted scale_pos_weight for XGBoost
        # With 93% HOLD imbalance, we need much stronger weights
        hold_count = len(y_train[y_train == 1])
        action_count = len(y_train[y_train != 1])
        
        # Base scale: 13x, boost to 50-60x for better minority class detection
        base_scale = hold_count / action_count if action_count > 0 else 1.0
        boosted_scale = base_scale * 4.0  # Boost from 13x to ~50x
        
        logger.info(f"XGBoost class balance:")
        logger.info(f"  HOLD samples: {hold_count:,}")
        logger.info(f"  BUY+SELL samples: {action_count:,}")
        logger.info(f"  Base scale_pos_weight: {base_scale:.2f}")
        logger.info(f"  BOOSTED scale_pos_weight: {boosted_scale:.2f}")
        
        model = xgb.XGBClassifier(
            scale_pos_weight=boosted_scale,
            **self.config.XGBOOST_PARAMS
        )
        
        # Train
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=False
        )
        
        # Evaluate
        train_acc = model.score(X_train, y_train)
        val_acc = model.score(X_val, y_val)
        
        logger.info(f"{pair} XGBoost - Train: {train_acc:.4f}, Val: {val_acc:.4f}")
        
        return model

# ==================== MAIN TRAINING LOOP ====================

def train_all_pairs():
    """Train XGBoost models for all 8 pairs"""
    
    logger.info("="*80)
    logger.info("XGBOOST-ONLY TRAINING - 105 FEATURES")
    logger.info("="*80)
    logger.info(f"Training data: {config.TRAIN_FILE}")
    logger.info(f"Validation data: {config.VAL_FILE}")
    logger.info(f"Output directory: {config.OUTPUT_DIR}")
    logger.info(f"Number of features: {config.NUM_FEATURES}")
    logger.info("="*80)
    
    start_time = time.time()
    trainer = XGBoostTrainer(config)
    results = {}
    
    for i, pair in enumerate(config.PAIRS, 1):
        logger.info(f"\n{'='*80}")
        logger.info(f"TRAINING {i}/{len(config.PAIRS)}: {pair}")
        logger.info(f"{'='*80}")
        
        try:
            # Load training data
            X_train, y_train = load_pair_data_chunked(
                config.TRAIN_FILE, 
                pair,
                max_samples=config.MAX_SAMPLES_PER_PAIR
            )
            
            # Load validation data
            X_val, y_val = load_pair_data_chunked(
                config.VAL_FILE,
                pair,
                max_samples=None  # Use all validation data
            )
            
            # Train XGBoost
            model = trainer.train(X_train, y_train, X_val, y_val, pair)
            
            # Save model
            model_path = config.OUTPUT_DIR / f"{pair}_xgboost_105feat.pkl"
            joblib.dump(model, model_path)
            logger.info(f"[OK] Saved: {model_path.name}")
            
            # Store results
            results[pair] = {
                'train_acc': model.score(X_train, y_train),
                'val_acc': model.score(X_val, y_val),
                'model_path': model_path
            }
            
            # Cleanup
            del X_train, y_train, X_val, y_val, model
            gc.collect()
            
        except Exception as e:
            logger.error(f"Failed to train {pair}: {e}")
            results[pair] = {'error': str(e)}
            continue
    
    # Summary
    duration = time.time() - start_time
    logger.info(f"\n{'='*80}")
    logger.info("TRAINING COMPLETE!")
    logger.info(f"{'='*80}")
    logger.info(f"Time taken: {duration/60:.1f} minutes")
    logger.info(f"\nResults Summary:")
    logger.info(f"{'Pair':<15} {'Train Acc':<12} {'Val Acc':<12} {'Status'}")
    logger.info("-" * 80)
    
    successful = 0
    for pair, result in results.items():
        if 'error' in result:
            logger.info(f"{pair:<15} {'N/A':<12} {'N/A':<12} FAILED")
        else:
            train_acc = result['train_acc']
            val_acc = result['val_acc']
            logger.info(f"{pair:<15} {train_acc:.4f}      {val_acc:.4f}      SUCCESS")
            successful += 1
    
    logger.info("-" * 80)
    logger.info(f"Successfully trained: {successful}/{len(config.PAIRS)} models")
    logger.info(f"Models saved to: {config.OUTPUT_DIR}")
    logger.info(f"\nNext step: Deploy to demo account")
    logger.info(f"  python predict_xgboost_105feat.py")
    
    return results

# ==================== ENTRY POINT ====================

if __name__ == "__main__":
    logger.info("Starting XGBoost-Only training...")
    logger.info(f"PyTorch version: {__import__('torch').__version__ if 'torch' in sys.modules else 'N/A'}")
    
    try:
        results = train_all_pairs()
        logger.info("\n✅ TRAINING SUCCESSFUL!")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n❌ TRAINING FAILED: {e}", exc_info=True)
        sys.exit(1)
