"""
Test Model Predictions - Verify Models Work Correctly
=====================================================
"""

import pandas as pd
import pickle
from pathlib import Path
import numpy as np

BASE_DIR = Path(r"C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System")
MODELS_DIR = BASE_DIR / "trained_models_B1_CLEAN"
VAL_FILE = BASE_DIR / "training" / "val_data_24c_10p_offset.csv"

PAIRS = ['EURUSD.sim', 'GBPUSD.sim', 'USDJPY.sim', 'USDCHF.sim',
         'AUDUSD.sim', 'USDCAD.sim', 'NZDUSD.sim']

print("\n" + "="*80)
print("TESTING MODEL PREDICTIONS")
print("="*80)

for pair in PAIRS:
    print(f"\n{pair}:")
    
    # Load XGBoost model
    model_path = MODELS_DIR / f"{pair}_xgboost.pkl"
    if not model_path.exists():
        print(f"  [SKIP] Model not found")
        continue
    
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    
    # Load validation data for this pair
    print(f"  Loading validation data...")
    df_val = pd.read_csv(VAL_FILE)
    df_pair = df_val[df_val['symbol'] == pair]
    
    if len(df_pair) == 0:
        print(f"  [ERROR] No validation data found!")
        continue
    
    # Get features and labels
    feature_cols = [col for col in df_pair.columns if col not in ['timestamp', 'symbol', 'label']]
    X_val = df_pair[feature_cols].values
    y_true = df_pair['label'].values
    
    # Make predictions
    y_pred = model.predict(X_val)
    
    # Calculate prediction distribution
    unique, counts = np.unique(y_pred, return_counts=True)
    pred_dist = dict(zip(unique, counts))
    
    # Calculate true label distribution
    unique_true, counts_true = np.unique(y_true, return_counts=True)
    true_dist = dict(zip(unique_true, counts_true))
    
    print(f"  Samples: {len(df_pair):,}")
    print(f"\n  TRUE Labels:")
    for label in [0, 1, 2]:
        count = true_dist.get(label, 0)
        pct = count / len(y_true) * 100
        label_name = ['SELL', 'HOLD', 'BUY'][label]
        print(f"    {label_name}: {count:,} ({pct:.2f}%)")
    
    print(f"\n  PREDICTED Labels:")
    for label in [0, 1, 2]:
        count = pred_dist.get(label, 0)
        pct = count / len(y_pred) * 100
        label_name = ['SELL', 'HOLD', 'BUY'][label]
        print(f"    {label_name}: {count:,} ({pct:.2f}%)")
    
    # Calculate accuracy
    accuracy = (y_pred == y_true).mean()
    print(f"\n  Accuracy: {accuracy:.4f} ({accuracy*100:.2f}%)")
    
    # Check if predicting variety
    num_unique_preds = len(pred_dist)
    if num_unique_preds == 1:
        print(f"  [WARNING] Only predicting 1 class!")
    elif num_unique_preds == 2:
        print(f"  [OK] Predicting 2 classes")
    else:
        print(f"  [EXCELLENT] Predicting all 3 classes!")

print("\n" + "="*80)
print("VERIFICATION COMPLETE")
print("="*80)
print("\nSummary:")
print("  - If models predict variety (2-3 classes): GOOD")
print("  - If models only predict 1 class (HOLD): BAD - still broken")
print("="*80 + "\n")
