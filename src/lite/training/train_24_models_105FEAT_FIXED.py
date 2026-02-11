#!/usr/bin/env python3
"""
Train 24 Models on 105 Features - ALL PROVEN FIXES APPLIED
===========================================================
File: train_24_models_105FEAT_FIXED.py
Date: 2025-11-29

FIXES APPLIED (from Nov 15-17 chat history):
1. SimpleCNN (MLP architecture) - NOT Conv1D
2. .dropna() before training - removes NaN rows
3. Full batch training for neural networks
4. Class weights (inverse frequency, ~9-15x)
5. Learning rate 0.001
6. Memory-safe chunked loading
7. 102 features (105 - timestamp - symbol - label)

Models: 8 XGBoost + 8 Transformer + 8 CNN = 24 total
"""

import os
import sys
import gc
import pickle
import logging
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np
from sklearn.utils.class_weight import compute_class_weight
import xgboost as xgb

import torch
import torch.nn as nn
import torch.optim as optim

# ============================================================================
# CONFIGURATION
# ============================================================================
BASE_DIR = Path(r"C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System")
TRAINING_DIR = BASE_DIR / "training"
OUTPUT_DIR = BASE_DIR / "trained_models_105FEAT"

TRAIN_FILE = TRAINING_DIR / "train_data_24c_10p_105FEAT.csv"
VAL_FILE = TRAINING_DIR / "val_data_24c_10p_105FEAT.csv"
TEST_FILE = TRAINING_DIR / "test_data_24c_10p_105FEAT.csv"

SYMBOLS = ['EURUSD.sim', 'GBPUSD.sim', 'USDJPY.sim', 'USDCHF.sim', 
           'AUDUSD.sim', 'USDCAD.sim', 'NZDUSD.sim', 'EURGBP.sim']

MAX_SAMPLES = 50000  # Memory safety
CHUNK_SIZE = 25000

# Create output directories
OUTPUT_DIR.mkdir(exist_ok=True)
(OUTPUT_DIR / "xgboost").mkdir(exist_ok=True)
(OUTPUT_DIR / "transformer").mkdir(exist_ok=True)
(OUTPUT_DIR / "cnn").mkdir(exist_ok=True)

# Setup logging
log_file = TRAINING_DIR / f"training_105FEAT_FIXED_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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
# MODEL DEFINITIONS
# ============================================================================

class SimpleCNN(nn.Module):
    """
    MLP Architecture (NOT Conv1D) - PROVEN TO WORK
    Linear layers with BatchNorm, ReLU, Dropout
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


class SimpleTransformer(nn.Module):
    """
    Simple Transformer for tabular data
    Embedding + Self-Attention + Classification head
    """
    def __init__(self, input_dim, d_model=64, nhead=4, num_layers=2, num_classes=3, dropout=0.1):
        super(SimpleTransformer, self).__init__()
        self.embedding = nn.Linear(input_dim, d_model)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, 
            nhead=nhead, 
            dim_feedforward=128,
            dropout=dropout,
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.classifier = nn.Linear(d_model, num_classes)
        self.dropout = nn.Dropout(dropout)
    
    def forward(self, x):
        # x: [batch, features] -> [batch, 1, features]
        x = x.unsqueeze(1)
        x = self.embedding(x)
        x = self.transformer(x)
        x = x.squeeze(1)  # [batch, d_model]
        x = self.dropout(x)
        return self.classifier(x)


# ============================================================================
# DATA LOADING (CHUNKED + DROPNA)
# ============================================================================

def load_symbol_data(csv_file, symbol, max_samples=MAX_SAMPLES):
    """Load data for a specific symbol with chunked reading and NaN removal"""
    chunks = []
    total_loaded = 0
    
    for chunk in pd.read_csv(csv_file, chunksize=CHUNK_SIZE):
        symbol_data = chunk[chunk['symbol'] == symbol]
        if len(symbol_data) > 0:
            chunks.append(symbol_data)
            total_loaded += len(symbol_data)
            if total_loaded >= max_samples * 2:  # Load extra for dropna
                break
    
    if not chunks:
        return None, None
    
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
    
    # Get feature columns (exclude timestamp, symbol, label)
    feature_cols = [c for c in df.columns if c not in ['timestamp', 'symbol', 'label']]
    
    X = df[feature_cols].values.astype(np.float32)
    y = df['label'].values.astype(np.int64)
    
    return X, y


# ============================================================================
# TRAINING FUNCTIONS
# ============================================================================

def train_xgboost(X_train, y_train, X_val, y_val, symbol):
    """Train XGBoost with class weights"""
    # Calculate class weights
    classes = np.unique(y_train)
    weights = compute_class_weight('balanced', classes=classes, y=y_train)
    
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
    train_acc = (model.predict(X_train) == y_train).mean()
    val_acc = (model.predict(X_val) == y_val).mean()
    
    return model, train_acc, val_acc


def train_transformer(X_train, y_train, X_val, y_val, symbol, device, num_features):
    """Train Transformer with class weights - FULL BATCH"""
    # Class weights
    classes = np.unique(y_train)
    weights = compute_class_weight('balanced', classes=classes, y=y_train)
    class_weights = torch.FloatTensor(weights).to(device)
    
    # Convert to tensors
    X_train_t = torch.FloatTensor(X_train).to(device)
    y_train_t = torch.LongTensor(y_train).to(device)
    X_val_t = torch.FloatTensor(X_val).to(device)
    y_val_t = torch.LongTensor(y_val).to(device)
    
    # Model
    model = SimpleTransformer(input_dim=num_features, num_classes=3).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    # Training - FULL BATCH
    model.train()
    for epoch in range(30):
        optimizer.zero_grad()
        outputs = model(X_train_t)
        loss = criterion(outputs, y_train_t)
        loss.backward()
        optimizer.step()
        
        if epoch % 10 == 0:
            logger.info(f"    Epoch {epoch}/30 - Loss: {loss.item():.4f}")
    
    # Evaluate
    model.eval()
    with torch.no_grad():
        train_preds = model(X_train_t).argmax(dim=1)
        val_preds = model(X_val_t).argmax(dim=1)
        train_acc = (train_preds == y_train_t).float().mean().item()
        val_acc = (val_preds == y_val_t).float().mean().item()
        
        # Check class distribution
        pred_classes = val_preds.cpu().numpy()
        unique_preds = np.unique(pred_classes)
        logger.info(f"    Predicting classes: {sorted(unique_preds.tolist())}")
    
    return model, train_acc, val_acc


def train_cnn(X_train, y_train, X_val, y_val, symbol, device, num_features):
    """Train SimpleCNN (MLP) with class weights - FULL BATCH"""
    # Class weights
    classes = np.unique(y_train)
    weights = compute_class_weight('balanced', classes=classes, y=y_train)
    class_weights = torch.FloatTensor(weights).to(device)
    
    # Convert to tensors
    X_train_t = torch.FloatTensor(X_train).to(device)
    y_train_t = torch.LongTensor(y_train).to(device)
    X_val_t = torch.FloatTensor(X_val).to(device)
    y_val_t = torch.LongTensor(y_val).to(device)
    
    # Model - SimpleCNN (MLP architecture)
    model = SimpleCNN(input_dim=num_features, num_classes=3).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    
    # Training - FULL BATCH
    model.train()
    for epoch in range(30):
        optimizer.zero_grad()
        outputs = model(X_train_t)
        loss = criterion(outputs, y_train_t)
        loss.backward()
        optimizer.step()
        
        if epoch % 10 == 0:
            logger.info(f"    Epoch {epoch}/30 - Loss: {loss.item():.4f}")
    
    # Evaluate
    model.eval()
    with torch.no_grad():
        train_preds = model(X_train_t).argmax(dim=1)
        val_preds = model(X_val_t).argmax(dim=1)
        train_acc = (train_preds == y_train_t).float().mean().item()
        val_acc = (val_preds == y_val_t).float().mean().item()
        
        # Check class distribution
        pred_classes = val_preds.cpu().numpy()
        unique_preds = np.unique(pred_classes)
        logger.info(f"    Predicting classes: {sorted(unique_preds.tolist())}")
    
    return model, train_acc, val_acc


# ============================================================================
# MAIN TRAINING LOOP
# ============================================================================

def main():
    logger.info("="*80)
    logger.info("TRAINING 24 MODELS - 105 FEATURES (ALL FIXES APPLIED)")
    logger.info("="*80)
    logger.info(f"Train file: {TRAIN_FILE}")
    logger.info(f"Val file: {VAL_FILE}")
    logger.info(f"Output: {OUTPUT_DIR}")
    logger.info("="*80)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"Device: {device}")
    
    results = {}
    
    for i, symbol in enumerate(SYMBOLS, 1):
        logger.info(f"\n{'='*80}")
        logger.info(f"TRAINING {i}/8: {symbol}")
        logger.info("="*80)
        
        try:
            # Load training data
            logger.info(f"Loading {symbol} training data...")
            X_train, y_train = load_symbol_data(TRAIN_FILE, symbol)
            if X_train is None:
                logger.error(f"No data for {symbol}")
                continue
            
            # Load validation data
            logger.info(f"Loading {symbol} validation data...")
            X_val, y_val = load_symbol_data(VAL_FILE, symbol)
            if X_val is None:
                logger.error(f"No validation data for {symbol}")
                continue
            
            num_features = X_train.shape[1]
            logger.info(f"  Train: {len(X_train):,} samples, {num_features} features")
            logger.info(f"  Val: {len(X_val):,} samples")
            
            # Class distribution
            unique, counts = np.unique(y_train, return_counts=True)
            logger.info(f"  Class distribution: {dict(zip(unique, counts))}")
            
            results[symbol] = {}
            
            # ========== XGBoost ==========
            logger.info(f"\n  Training XGBoost for {symbol}...")
            xgb_model, xgb_train, xgb_val = train_xgboost(X_train, y_train, X_val, y_val, symbol)
            
            xgb_path = OUTPUT_DIR / "xgboost" / f"{symbol}_xgboost.pkl"
            with open(xgb_path, 'wb') as f:
                pickle.dump(xgb_model, f)
            
            logger.info(f"  [XGB] Train: {xgb_train:.4f}, Val: {xgb_val:.4f}")
            logger.info(f"  [OK] Saved: {xgb_path.name}")
            results[symbol]['xgboost'] = xgb_val
            
            del xgb_model
            gc.collect()
            
            # ========== Transformer ==========
            logger.info(f"\n  Training Transformer for {symbol}...")
            trans_model, trans_train, trans_val = train_transformer(
                X_train, y_train, X_val, y_val, symbol, device, num_features
            )
            
            trans_path = OUTPUT_DIR / "transformer" / f"{symbol}_transformer.pth"
            torch.save({
                'model_state_dict': trans_model.state_dict(),
                'input_dim': num_features,
                'num_classes': 3
            }, trans_path)
            
            logger.info(f"  [TRF] Train: {trans_train:.4f}, Val: {trans_val:.4f}")
            logger.info(f"  [OK] Saved: {trans_path.name}")
            results[symbol]['transformer'] = trans_val
            
            del trans_model
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            # ========== CNN (SimpleCNN/MLP) ==========
            logger.info(f"\n  Training CNN (SimpleCNN) for {symbol}...")
            cnn_model, cnn_train, cnn_val = train_cnn(
                X_train, y_train, X_val, y_val, symbol, device, num_features
            )
            
            cnn_path = OUTPUT_DIR / "cnn" / f"{symbol}_cnn.pth"
            torch.save({
                'model_state_dict': cnn_model.state_dict(),
                'input_dim': num_features,
                'num_classes': 3
            }, cnn_path)
            
            logger.info(f"  [CNN] Train: {cnn_train:.4f}, Val: {cnn_val:.4f}")
            logger.info(f"  [OK] Saved: {cnn_path.name}")
            results[symbol]['cnn'] = cnn_val
            
            del cnn_model, X_train, y_train, X_val, y_val
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            logger.info(f"\n  {symbol} COMPLETE:")
            logger.info(f"    XGBoost:     {results[symbol]['xgboost']:.4f}")
            logger.info(f"    Transformer: {results[symbol]['transformer']:.4f}")
            logger.info(f"    CNN:         {results[symbol]['cnn']:.4f}")
            
        except Exception as e:
            logger.error(f"Failed to train {symbol}: {e}")
            import traceback
            traceback.print_exc()
    
    # Final summary
    logger.info("\n" + "="*80)
    logger.info("TRAINING COMPLETE - SUMMARY")
    logger.info("="*80)
    
    for symbol, accs in results.items():
        logger.info(f"{symbol}:")
        logger.info(f"  XGB: {accs.get('xgboost', 0):.4f}")
        logger.info(f"  TRF: {accs.get('transformer', 0):.4f}")
        logger.info(f"  CNN: {accs.get('cnn', 0):.4f}")
    
    logger.info("\n" + "="*80)
    logger.info(f"ALL 24 MODELS SAVED TO: {OUTPUT_DIR}")
    logger.info("="*80)


if __name__ == "__main__":
    main()
