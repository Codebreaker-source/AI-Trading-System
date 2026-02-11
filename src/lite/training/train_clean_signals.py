#!/usr/bin/env python3
"""
Train Ensemble Models with CLEAN Signal Features Only
======================================================
File: train_clean_signals.py
Date: 2025-12-01

FIXES:
- Uses ONLY 27 signal features (removes 31 noise features)
- Balanced undersampling (33/33/33)
- XGBoost + LightGBM + CatBoost (all 3 models)

Signal Features (27):
- Price: close, high, low, volume
- Trend: sma_20, sma_50, fast_ema, slow_ema, htf_*
- Momentum: rsi, stoch_k, stoch_d, momentum
- Volatility: atr, bb_*, volatility
- Volume: volume_sma, volume_ratio, price_volume
- Sentiment: bullish/bearish/net_sentiment

REMOVED (31 noise features):
- Risk: returns_std, sharpe_approx, max_drawdown
- Correlations: corr_* (8), avg_correlation
- Currency strength: *_strength (8)
- Derived flags: *_confirm (11)
"""

import os
import gc
import joblib
import logging
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier

# ============================================================================
# CONFIGURATION
# ============================================================================
BASE_DIR = Path(r"C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System")
TRAINING_DIR = BASE_DIR / "training"
OUTPUT_DIR = BASE_DIR / "trained_models_CLEAN27"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TRAIN_FILE = TRAINING_DIR / "train_data_24c_10p_105FEAT.csv"
VAL_FILE = TRAINING_DIR / "val_data_24c_10p_105FEAT.csv"

SYMBOLS = ['EURUSD.sim', 'GBPUSD.sim', 'USDJPY.sim', 'USDCHF.sim', 
           'AUDUSD.sim', 'USDCAD.sim', 'NZDUSD.sim', 'EURGBP.sim']

# ONLY 27 SIGNAL FEATURES - No noise!
SIGNAL_FEATURES = [
    # Price (4)
    'close', 'high', 'low', 'volume',
    # Trend (8)
    'sma_20', 'sma_50', 'fast_ema', 'slow_ema',
    'htf_fast_ema', 'htf_slow_ema', 'htf_trend_direction', 'htf_trend_alignment',
    # Momentum (4)
    'rsi', 'stoch_k', 'stoch_d', 'momentum',
    # Volatility (5)
    'atr', 'bb_upper', 'bb_middle', 'bb_lower', 'volatility',
    # Volume (3)
    'volume_sma', 'volume_ratio', 'price_volume',
    # Sentiment (3)
    'bullish_sentiment', 'bearish_sentiment', 'net_sentiment',
]

SAMPLES_PER_CLASS = 5000

# Setup logging
log_file = TRAINING_DIR / f"training_CLEAN27_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# DATA LOADING - CLEAN FEATURES ONLY
# ============================================================================

def load_balanced_data(csv_file, symbol, samples_per_class=SAMPLES_PER_CLASS):
    """Load data with ONLY signal features, balanced classes"""
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
    
    # Verify we have the signal features
    available_features = [f for f in SIGNAL_FEATURES if f in df.columns]
    missing_features = [f for f in SIGNAL_FEATURES if f not in df.columns]
    
    if missing_features:
        logger.warning(f"  Missing features: {missing_features}")
    
    logger.info(f"  Using {len(available_features)} signal features (removed {58 - len(available_features)} noise features)")
    
    # Get class distribution
    class_counts = df['label'].value_counts().sort_index()
    logger.info(f"  Original: SELL={class_counts.get(0,0)}, HOLD={class_counts.get(1,0)}, BUY={class_counts.get(2,0)}")
    
    # Balance classes
    min_count = class_counts.min()
    target_samples = min(samples_per_class, min_count)
    
    balanced_dfs = []
    for label in [0, 1, 2]:
        class_df = df[df['label'] == label]
        if len(class_df) >= target_samples:
            sampled = class_df.sample(n=target_samples, random_state=42)
        else:
            sampled = class_df
        balanced_dfs.append(sampled)
    
    df_balanced = pd.concat(balanced_dfs, ignore_index=True)
    df_balanced = df_balanced.sample(frac=1, random_state=42)  # Shuffle
    
    logger.info(f"  Balanced: {len(df_balanced):,} samples (5k per class)")
    
    # Extract ONLY signal features
    X = df_balanced[available_features].values.astype(np.float32)
    y = df_balanced['label'].values.astype(np.int64)
    
    del df, df_balanced
    gc.collect()
    
    return X, y, available_features


# ============================================================================
# MODEL TRAINING
# ============================================================================

def train_xgboost(X_train, y_train, X_val, y_val):
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
        'tree_method': 'hist',
    }
    
    model = xgb.XGBClassifier(**params)
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    return model


def train_lightgbm(X_train, y_train, X_val, y_val):
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
        'force_col_wise': True,
    }
    
    model = lgb.LGBMClassifier(**params)
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)])
    return model


def train_catboost(X_train, y_train, X_val, y_val):
    """Train CatBoost classifier with proper parameters"""
    model = CatBoostClassifier(
        iterations=200,
        depth=6,
        learning_rate=0.1,
        loss_function='MultiClass',
        random_seed=42,
        verbose=False,
        task_type='CPU',
        # Additional params to prevent degenerate solutions
        l2_leaf_reg=3.0,
        border_count=254,
        auto_class_weights='Balanced',  # Help with class balance
    )
    
    model.fit(X_train, y_train, eval_set=(X_val, y_val), verbose=False)
    return model


def evaluate_model(model, X_val, y_val, model_name):
    """Evaluate and return metrics"""
    preds = model.predict(X_val)
    
    accuracy = (preds == y_val).mean()
    
    # Per-class metrics
    results = {'accuracy': accuracy, 'class_acc': {}, 'pred_dist': {}}
    
    for cls in [0, 1, 2]:
        mask = y_val == cls
        if mask.sum() > 0:
            results['class_acc'][cls] = (preds[mask] == y_val[mask]).mean()
        else:
            results['class_acc'][cls] = 0.0
        results['pred_dist'][cls] = (preds == cls).sum()
    
    sell_acc = results['class_acc'][0] * 100
    hold_acc = results['class_acc'][1] * 100
    buy_acc = results['class_acc'][2] * 100
    
    logger.info(f"    {model_name}: Acc={accuracy:.1%} | SELL={sell_acc:.1f}% HOLD={hold_acc:.1f}% BUY={buy_acc:.1f}%")
    logger.info(f"    Preds: SELL={results['pred_dist'][0]}, HOLD={results['pred_dist'][1]}, BUY={results['pred_dist'][2]}")
    
    return results


def save_model(model, symbol, model_type, feature_cols):
    """Save model with feature list"""
    model_dir = OUTPUT_DIR / model_type
    model_dir.mkdir(parents=True, exist_ok=True)
    
    save_data = {
        'model': model,
        'feature_cols': feature_cols,
        'symbol': symbol,
        'model_type': model_type,
        'features_used': 'CLEAN_27_SIGNALS',
    }
    
    filepath = model_dir / f"{symbol}_{model_type}_clean27.pkl"
    joblib.dump(save_data, filepath)
    logger.info(f"    Saved: {filepath.name}")



# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 80)
    print("TRAINING WITH CLEAN 27 SIGNAL FEATURES")
    print("=" * 80)
    print("Removed 31 noise features (correlations, strength, derived flags)")
    print("=" * 80)
    
    logger.info("=" * 80)
    logger.info("CLEAN 27 SIGNAL FEATURES TRAINING")
    logger.info(f"Features: {SIGNAL_FEATURES}")
    logger.info("=" * 80)
    
    all_results = {}
    
    for i, symbol in enumerate(SYMBOLS, 1):
        print(f"\n[{i}/8] TRAINING: {symbol}")
        print("-" * 50)
        logger.info(f"\n[{i}/8] TRAINING: {symbol}")
        
        # Load balanced training data with clean features
        X_train, y_train, feature_cols = load_balanced_data(TRAIN_FILE, symbol)
        
        if X_train is None:
            continue
        
        # Load validation data
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
        
        val_dist = val_df['label'].value_counts().sort_index()
        logger.info(f"  Val: {len(X_val):,} samples | SELL={val_dist.get(0,0)}, HOLD={val_dist.get(1,0)}, BUY={val_dist.get(2,0)}")
        
        symbol_results = {}
        
        # Train XGBoost
        print(f"  Training XGBoost (27 features)...")
        logger.info(f"  Training XGBoost...")
        xgb_model = train_xgboost(X_train, y_train, X_val, y_val)
        results = evaluate_model(xgb_model, X_val, y_val, "XGBoost")
        save_model(xgb_model, symbol, 'xgboost', feature_cols)
        symbol_results['xgboost'] = results
        del xgb_model
        gc.collect()
        
        # Train LightGBM
        print(f"  Training LightGBM (27 features)...")
        logger.info(f"  Training LightGBM...")
        lgb_model = train_lightgbm(X_train, y_train, X_val, y_val)
        results = evaluate_model(lgb_model, X_val, y_val, "LightGBM")
        save_model(lgb_model, symbol, 'lightgbm', feature_cols)
        symbol_results['lightgbm'] = results
        del lgb_model
        gc.collect()
        
        # Train CatBoost
        print(f"  Training CatBoost (27 features)...")
        logger.info(f"  Training CatBoost...")
        cb_model = train_catboost(X_train, y_train, X_val, y_val)
        results = evaluate_model(cb_model, X_val, y_val, "CatBoost")
        save_model(cb_model, symbol, 'catboost', feature_cols)
        symbol_results['catboost'] = results
        del cb_model
        gc.collect()
        
        all_results[symbol] = symbol_results
        
        del X_train, y_train, X_val, y_val, val_df
        gc.collect()
        
        print(f"  Done!")
    
    # Summary
    print("\n" + "=" * 80)
    print("TRAINING COMPLETE - SUMMARY")
    print("=" * 80)
    
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)
    
    print(f"\n{'Symbol':<15} {'Model':<12} {'Acc':>8} {'SELL':>8} {'HOLD':>8} {'BUY':>8}")
    print("-" * 65)
    
    for symbol, results in all_results.items():
        for model_type, metrics in results.items():
            acc = metrics['accuracy'] * 100
            sell = metrics['pred_dist'][0]
            hold = metrics['pred_dist'][1]
            buy = metrics['pred_dist'][2]
            print(f"{symbol:<15} {model_type:<12} {acc:>7.1f}% {sell:>8} {hold:>8} {buy:>8}")
    
    print(f"\nModels saved to: {OUTPUT_DIR}")
    print("=" * 80)
    
    logger.info(f"\nModels saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
