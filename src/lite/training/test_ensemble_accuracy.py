#!/usr/bin/env python3
"""
Test Tree-Based Ensemble on Validation Data
============================================
Evaluates XGBoost + LightGBM + CatBoost ensemble performance.
"""

import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from ensemble_predictor_v3_treebased import EnsemblePredictorV3

# Configuration
BASE_DIR = Path(r"C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System")
VAL_FILE = BASE_DIR / "training" / "val_data_24c_10p_105FEAT.csv"

SYMBOLS = [
    'EURUSD.sim', 'GBPUSD.sim', 'USDJPY.sim', 'USDCHF.sim',
    'AUDUSD.sim', 'USDCAD.sim', 'NZDUSD.sim', 'EURGBP.sim'
]

EXCLUDE_COLS = ['timestamp', 'symbol', 'label']
LABELS = ['SELL', 'HOLD', 'BUY']


def load_val_data(symbol: str, max_samples: int = None) -> tuple:
    """Load validation data for a symbol"""
    chunks = []
    for chunk in pd.read_csv(VAL_FILE, chunksize=50000):
        symbol_data = chunk[chunk['symbol'] == symbol]
        if len(symbol_data) > 0:
            chunks.append(symbol_data)
    
    if not chunks:
        return None, None
    
    df = pd.concat(chunks, ignore_index=True)
    
    if max_samples and len(df) > max_samples:
        df = df.sample(n=max_samples, random_state=42)
    
    feature_cols = [c for c in df.columns if c not in EXCLUDE_COLS]
    X = df[feature_cols].values
    y = df['label'].values
    
    return X, y


def test_single_model(model_type: str, model_dir: Path, symbol: str, X: np.ndarray, y: np.ndarray) -> dict:
    """Test a single model type"""
    if model_type == 'xgboost':
        model_path = model_dir / f"{symbol}_xgboost_105feat.pkl"
    elif model_type == 'lightgbm':
        model_path = model_dir / "lightgbm" / f"{symbol}_lightgbm_105feat.pkl"
    elif model_type == 'catboost':
        model_path = model_dir / "catboost" / f"{symbol}_catboost_105feat.pkl"
    else:
        return None
    
    if not model_path.exists():
        return None
    
    try:
        data = joblib.load(model_path)
        model = data['model'] if isinstance(data, dict) else data
        
        y_pred = model.predict(X)
        acc = accuracy_score(y, y_pred)
        
        return {
            'accuracy': acc,
            'predictions': y_pred
        }
    except Exception as e:
        print(f"   Error loading {model_type}: {e}")
        return None


def test_ensemble(predictor: EnsemblePredictorV3, symbol: str, X: np.ndarray, y: np.ndarray) -> dict:
    """Test ensemble predictions"""
    y_pred = []
    y_conf = []
    agreements = []
    
    for i in range(len(X)):
        result = predictor.predict_pair(X[i], symbol)
        if result:
            y_pred.append(result['prediction'])
            y_conf.append(result['confidence'])
            agreements.append(result['unanimous'])
        else:
            y_pred.append(1)  # Default to HOLD
            y_conf.append(0.0)
            agreements.append(False)
    
    y_pred = np.array(y_pred)
    
    acc = accuracy_score(y, y_pred)
    unanimous_rate = np.mean(agreements)
    avg_conf = np.mean(y_conf)
    
    return {
        'accuracy': acc,
        'predictions': y_pred,
        'unanimous_rate': unanimous_rate,
        'avg_confidence': avg_conf
    }


def main():
    print("=" * 70)
    print("TREE-BASED ENSEMBLE TEST ON VALIDATION DATA")
    print("=" * 70)
    
    model_dir = BASE_DIR / "trained_models_105FEAT"
    predictor = EnsemblePredictorV3(str(model_dir))
    
    results = {
        'xgboost': {},
        'lightgbm': {},
        'catboost': {},
        'ensemble': {}
    }
    
    for symbol in SYMBOLS:
        print(f"\n{'=' * 70}")
        print(f"TESTING: {symbol}")
        print("=" * 70)
        
        # Load data
        X, y = load_val_data(symbol)
        if X is None:
            print(f"   No data for {symbol}")
            continue
        
        print(f"   Samples: {len(X)}")
        
        # Test individual models
        for model_type in ['xgboost', 'lightgbm', 'catboost']:
            result = test_single_model(model_type, model_dir, symbol, X, y)
            if result:
                results[model_type][symbol] = result['accuracy']
                print(f"   {model_type.upper():10s}: {result['accuracy']:.2%}")
        
        # Test ensemble
        print(f"   Testing ensemble (this may take a moment)...")
        ens_result = test_ensemble(predictor, symbol, X, y)
        results['ensemble'][symbol] = ens_result['accuracy']
        print(f"   {'ENSEMBLE':10s}: {ens_result['accuracy']:.2%} (unanimous: {ens_result['unanimous_rate']:.1%}, conf: {ens_result['avg_confidence']:.2%})")
    
    # Summary
    print(f"\n{'=' * 70}")
    print("SUMMARY - VALIDATION ACCURACY")
    print("=" * 70)
    
    print(f"\n{'Pair':<12} {'XGBoost':>10} {'LightGBM':>10} {'CatBoost':>10} {'ENSEMBLE':>10}")
    print("-" * 54)
    
    for symbol in SYMBOLS:
        xgb = results['xgboost'].get(symbol, 0)
        lgb = results['lightgbm'].get(symbol, 0)
        cat = results['catboost'].get(symbol, 0)
        ens = results['ensemble'].get(symbol, 0)
        
        # Mark best
        best = max(xgb, lgb, cat, ens)
        
        xgb_str = f"{xgb:.2%}" + ("*" if xgb == best else "")
        lgb_str = f"{lgb:.2%}" + ("*" if lgb == best else "")
        cat_str = f"{cat:.2%}" + ("*" if cat == best else "")
        ens_str = f"{ens:.2%}" + ("*" if ens == best else "")
        
        print(f"{symbol:<12} {xgb_str:>10} {lgb_str:>10} {cat_str:>10} {ens_str:>10}")
    
    print("-" * 54)
    
    # Averages
    avg_xgb = np.mean(list(results['xgboost'].values())) if results['xgboost'] else 0
    avg_lgb = np.mean(list(results['lightgbm'].values())) if results['lightgbm'] else 0
    avg_cat = np.mean(list(results['catboost'].values())) if results['catboost'] else 0
    avg_ens = np.mean(list(results['ensemble'].values())) if results['ensemble'] else 0
    
    print(f"{'AVERAGE':<12} {avg_xgb:>9.2%} {avg_lgb:>10.2%} {avg_cat:>10.2%} {avg_ens:>10.2%}")
    
    print(f"\n{'=' * 70}")
    print("CONCLUSION")
    print("=" * 70)
    
    best_single = max(avg_xgb, avg_lgb, avg_cat)
    improvement = avg_ens - best_single
    
    if improvement > 0:
        print(f"   Ensemble IMPROVES over best single model by {improvement:.2%}")
    elif improvement == 0:
        print(f"   Ensemble MATCHES best single model")
    else:
        print(f"   Ensemble UNDERPERFORMS best single model by {-improvement:.2%}")
    
    print(f"\n   Best single model: {'LightGBM' if avg_lgb == best_single else 'XGBoost' if avg_xgb == best_single else 'CatBoost'} ({best_single:.2%})")
    print(f"   Ensemble accuracy: {avg_ens:.2%}")


if __name__ == "__main__":
    main()
