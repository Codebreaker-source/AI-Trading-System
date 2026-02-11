#!/usr/bin/env python3
"""
Fast Ensemble Test - Batch Predictions
=======================================
Tests XGBoost + LightGBM + CatBoost ensemble using batch predictions.
"""

import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from sklearn.metrics import accuracy_score
from collections import Counter

# Configuration
BASE_DIR = Path(r"C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System")
MODEL_DIR = BASE_DIR / "trained_models_105FEAT"
VAL_FILE = BASE_DIR / "training" / "val_data_24c_10p_105FEAT.csv"

SYMBOLS = [
    'EURUSD.sim', 'GBPUSD.sim', 'USDJPY.sim', 'USDCHF.sim',
    'AUDUSD.sim', 'USDCAD.sim', 'NZDUSD.sim', 'EURGBP.sim'
]

EXCLUDE_COLS = ['timestamp', 'symbol', 'label']
LABELS = ['SELL', 'HOLD', 'BUY']


def load_val_data(symbol: str) -> tuple:
    """Load validation data for a symbol"""
    chunks = []
    for chunk in pd.read_csv(VAL_FILE, chunksize=50000):
        symbol_data = chunk[chunk['symbol'] == symbol]
        if len(symbol_data) > 0:
            chunks.append(symbol_data)
    
    if not chunks:
        return None, None
    
    df = pd.concat(chunks, ignore_index=True)
    
    feature_cols = [c for c in df.columns if c not in EXCLUDE_COLS]
    X = df[feature_cols].values.astype(np.float64)
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    y = df['label'].values
    
    return X, y


def load_model(model_type: str, symbol: str):
    """Load a model"""
    if model_type == 'xgboost':
        path = MODEL_DIR / f"{symbol}_xgboost_105feat.pkl"
    elif model_type == 'lightgbm':
        path = MODEL_DIR / "lightgbm" / f"{symbol}_lightgbm_105feat.pkl"
    elif model_type == 'catboost':
        path = MODEL_DIR / "catboost" / f"{symbol}_catboost_105feat.pkl"
    else:
        return None
    
    if not path.exists():
        return None
    
    data = joblib.load(path)
    return data['model'] if isinstance(data, dict) else data


def ensemble_vote(preds_list: list) -> np.ndarray:
    """Majority vote ensemble"""
    # Ensure all predictions are 1D arrays of same length
    preds_list = [np.array(p).flatten().astype(int) for p in preds_list]
    
    # Stack predictions: (n_models, n_samples)
    stacked = np.vstack(preds_list)
    
    # Vote for each sample
    n_samples = stacked.shape[1]
    final_preds = np.zeros(n_samples, dtype=int)
    
    for i in range(n_samples):
        votes = stacked[:, i]
        # Most common vote
        final_preds[i] = Counter(votes).most_common(1)[0][0]
    
    return final_preds


def main():
    print("=" * 70)
    print("FAST ENSEMBLE TEST - BATCH PREDICTIONS")
    print("=" * 70)
    
    results = {model: {} for model in ['xgboost', 'lightgbm', 'catboost', 'ensemble']}
    
    for symbol in SYMBOLS:
        print(f"\n[{symbol}]")
        
        # Load data
        X, y = load_val_data(symbol)
        if X is None:
            print(f"   No data")
            continue
        
        print(f"   Samples: {len(X)}")
        
        # Get predictions from each model
        all_preds = []
        
        for model_type in ['xgboost', 'lightgbm', 'catboost']:
            model = load_model(model_type, symbol)
            if model is None:
                print(f"   {model_type}: NOT FOUND")
                continue
            
            y_pred = model.predict(X)
            # Flatten if needed (CatBoost returns 2D)
            if hasattr(y_pred, 'flatten'):
                y_pred = y_pred.flatten()
            y_pred = np.array(y_pred).astype(int)
            
            acc = accuracy_score(y, y_pred)
            results[model_type][symbol] = acc
            all_preds.append(y_pred)
            print(f"   {model_type:10s}: {acc:.2%}")
        
        # Ensemble vote
        if len(all_preds) >= 2:
            y_ensemble = ensemble_vote(all_preds)
            ens_acc = accuracy_score(y, y_ensemble)
            results['ensemble'][symbol] = ens_acc
            
            # Count agreements
            agree_mask = np.all(np.array(all_preds) == all_preds[0], axis=0)
            unanimous = np.mean(agree_mask)
            
            print(f"   {'ENSEMBLE':10s}: {ens_acc:.2%} (unanimous: {unanimous:.1%})")
    
    # Summary table
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print("=" * 70)
    
    print(f"\n{'Pair':<12} {'XGBoost':>10} {'LightGBM':>10} {'CatBoost':>10} {'ENSEMBLE':>10}")
    print("-" * 54)
    
    for symbol in SYMBOLS:
        xgb = results['xgboost'].get(symbol, 0)
        lgb = results['lightgbm'].get(symbol, 0)
        cat = results['catboost'].get(symbol, 0)
        ens = results['ensemble'].get(symbol, 0)
        
        print(f"{symbol:<12} {xgb:>9.2%} {lgb:>10.2%} {cat:>10.2%} {ens:>10.2%}")
    
    print("-" * 54)
    
    # Averages
    avg_xgb = np.mean(list(results['xgboost'].values())) if results['xgboost'] else 0
    avg_lgb = np.mean(list(results['lightgbm'].values())) if results['lightgbm'] else 0
    avg_cat = np.mean(list(results['catboost'].values())) if results['catboost'] else 0
    avg_ens = np.mean(list(results['ensemble'].values())) if results['ensemble'] else 0
    
    print(f"{'AVERAGE':<12} {avg_xgb:>9.2%} {avg_lgb:>10.2%} {avg_cat:>10.2%} {avg_ens:>10.2%}")
    
    # Conclusion
    print(f"\n{'=' * 70}")
    print("CONCLUSION")
    print("=" * 70)
    
    best_single = max(avg_xgb, avg_lgb, avg_cat)
    best_name = 'LightGBM' if avg_lgb == best_single else 'XGBoost' if avg_xgb == best_single else 'CatBoost'
    improvement = avg_ens - best_single
    
    print(f"\n   Best single model: {best_name} ({best_single:.2%})")
    print(f"   Ensemble accuracy: {avg_ens:.2%}")
    
    if improvement > 0:
        print(f"   Improvement: +{improvement:.2%}")
    elif improvement < 0:
        print(f"   Difference: {improvement:.2%}")
    else:
        print(f"   Matches best single model")
    
    print(f"\n   READY FOR PRODUCTION: {'YES' if avg_ens >= 0.85 else 'ACCEPTABLE' if avg_ens >= 0.80 else 'NEEDS WORK'}")


if __name__ == "__main__":
    main()
