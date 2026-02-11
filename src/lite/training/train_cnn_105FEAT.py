#!/usr/bin/env python3
"""
Train 8 CNN Models on 105 Features - ALL PROVEN FIXES
======================================================
File: train_cnn_105FEAT.py
Date: 2025-11-29

FIXES APPLIED (from Nov 15-17 chat history):
1. SimpleCNN (MLP architecture) - NOT Conv1D
2. .dropna() before training - removes NaN rows
3. Full batch training (not mini-batch)
4. Class weights (inverse frequency, ~9-15x)
5. Learning rate 0.001
6. Memory-safe chunked loading

Models: 8 CNN (one per currency pair)
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

import torch
import torch.nn as nn
import torch.optim as optim

# ============================================================================
# CONFIGURATION
# ============================================================================
BASE_DIR = Path(r"C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System")
TRAINING_DIR = BASE_DIR / "training"
OUTPUT_DIR = BASE_DIR / "trained_models_105FEAT" / "cnn"

TRAIN_FILE = TRAINING_DIR / "train_data_24c_10p_105FEAT.csv"
VAL_FILE = TRAINING_DIR / "val_data_24c_10p_105FEAT.csv"

SYMBOLS = ['EURUSD.sim', 'GBPUSD.sim', 'USDJPY.sim', 'USDCHF.sim', 
           'AUDUSD.sim', 'USDCAD.sim', 'NZDUSD.sim', 'EURGBP.sim']

MAX_SAMPLES = 50000
CHUNK_SIZE = 25000

# Create output directory
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging
log_file = TRAINING_DIR / f"training_CNN_105FEAT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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
# MODEL DEFINITION - SimpleCNN (MLP Architecture)
# ============================================================================

class SimpleCNN(nn.Module):
    """
    MLP Architecture (NOT Conv1D) - PROVEN TO WORK
    Linear layers with BatchNorm, ReLU, Dropout
    
    This fixed the 3-4% accuracy issue from Conv1D approach.
    """
    def __init__(self, input_dim, hidden_dims=[128, 64, 32], num_classes=3, dropout=0.3):
        super(SimpleCNN, self).__init__()
        layers = []
        prev_dim = input_dim
        
        for hidden_dim in hidden_dims:
            layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.BatchNorm1d(hidden_dim),
                nn.ReLU(),
                nn.Dropout(dropout)
            ])
            prev_dim = hidden_dim
        
        layers.append(nn.Linear(prev_dim, num_classes))
        self.network = nn.Sequential(*layers)
    
    def forward(self, x):
        return self.network(x)


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
    
    # CRITICAL FIX: Drop NaN rows
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

def train_cnn(X_train, y_train, X_val, y_val, symbol, device, num_features):
    """
    Train SimpleCNN (MLP) with class weights - FULL BATCH
    
    Key fixes:
    - Full batch (not mini-batch) - proven to work
    - Class weights for 93% HOLD imbalance
    - Learning rate 0.001
    """
    # Calculate class weights
    classes = np.unique(y_train)
    weights = compute_class_weight('balanced', classes=classes, y=y_train)
    class_weights = torch.FloatTensor(weights).to(device)
    
    logger.info(f"  Class weights: {dict(zip(classes.tolist(), weights.round(2).tolist()))}")
    
    # Convert to tensors
    X_train_t = torch.FloatTensor(X_train).to(device)
    y_train_t = torch.LongTensor(y_train).to(device)
    X_val_t = torch.FloatTensor(X_val).to(device)
    y_val_t = torch.LongTensor(y_val).to(device)
    
    # Model - SimpleCNN (MLP architecture)
    model = SimpleCNN(input_dim=num_features, num_classes=3).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    # Training - FULL BATCH (proven to work)
    logger.info(f"  Training 30 epochs (full batch)...")
    model.train()
    for epoch in range(30):
        optimizer.zero_grad()
        outputs = model(X_train_t)
        loss = criterion(outputs, y_train_t)
        loss.backward()
        optimizer.step()
        
        if epoch % 10 == 0:
            with torch.no_grad():
                preds = outputs.argmax(dim=1)
                unique_preds = np.unique(preds.cpu().numpy())
            logger.info(f"    Epoch {epoch}/30 - Loss: {loss.item():.4f} - Predicting: {sorted(unique_preds.tolist())}")
    
    # Evaluate
    model.eval()
    with torch.no_grad():
        train_preds = model(X_train_t).argmax(dim=1)
        val_preds = model(X_val_t).argmax(dim=1)
        train_acc = (train_preds == y_train_t).float().mean().item()
        val_acc = (val_preds == y_val_t).float().mean().item()
        
        # Check class distribution in predictions
        pred_classes = val_preds.cpu().numpy()
        unique_preds = np.unique(pred_classes)
        logger.info(f"  Final predicting classes: {sorted(unique_preds.tolist())}")
    
    return model, train_acc, val_acc


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("="*80)
    print("TRAINING 8 CNN MODELS - 105 FEATURES (ALL FIXES APPLIED)")
    print("="*80)
    logger.info("="*80)
    logger.info("CNN TRAINING - 105 FEATURES")
    logger.info("="*80)
    logger.info(f"Train file: {TRAIN_FILE}")
    logger.info(f"Val file: {VAL_FILE}")
    logger.info(f"Output: {OUTPUT_DIR}")
    logger.info("Fixes: SimpleCNN (MLP), .dropna(), full batch, class weights")
    logger.info("="*80)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"Device: {device}")
    print(f"Device: {device}")
    
    results = {}
    
    for i, symbol in enumerate(SYMBOLS, 1):
        print(f"\n{'='*80}")
        print(f"[{i}/8] TRAINING CNN: {symbol}")
        print("="*80)
        logger.info(f"\n{'='*80}")
        logger.info(f"[{i}/8] TRAINING CNN: {symbol}")
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
            
            # Train CNN
            model, train_acc, val_acc = train_cnn(
                X_train, y_train, X_val, y_val, symbol, device, num_features
            )
            
            # Save model
            model_path = OUTPUT_DIR / f"{symbol}_cnn.pth"
            torch.save({
                'model_state_dict': model.state_dict(),
                'input_dim': num_features,
                'num_classes': 3,
                'architecture': 'SimpleCNN_MLP'
            }, model_path)
            
            results[symbol] = val_acc
            
            logger.info(f"  Train Acc: {train_acc:.4f}")
            logger.info(f"  Val Acc: {val_acc:.4f}")
            logger.info(f"  Saved: {model_path.name}")
            
            print(f"  ✓ Train: {train_acc:.4f} | Val: {val_acc:.4f}")
            print(f"  ✓ Saved: {model_path.name}")
            
            # Cleanup
            del model, X_train, y_train, X_val, y_val
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
        except Exception as e:
            logger.error(f"Failed to train {symbol}: {e}")
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    # Final summary
    print("\n" + "="*80)
    print("CNN TRAINING COMPLETE")
    print("="*80)
    logger.info("\n" + "="*80)
    logger.info("CNN TRAINING COMPLETE")
    logger.info("="*80)
    
    for symbol, acc in results.items():
        status = "✓" if acc >= 0.85 else "⚠️" if acc >= 0.50 else "❌"
        print(f"  {status} {symbol}: {acc:.4f}")
        logger.info(f"  {symbol}: {acc:.4f}")
    
    avg_acc = np.mean(list(results.values())) if results else 0
    print(f"\n  Average: {avg_acc:.4f}")
    print(f"  Models saved to: {OUTPUT_DIR}")
    logger.info(f"Average accuracy: {avg_acc:.4f}")
    logger.info(f"Models saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
