#!/usr/bin/env python3
"""
Fix USDJPY Transformer - Lower Learning Rate
=============================================
File: fix_usdjpy_transformer.py
Date: 2025-11-29

USDJPY Transformer failed with LR 0.001 (29% accuracy, loss barely decreased)
Fix from Nov 16 chat history: Use LR 0.0001 for USDJPY
"""

import gc
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
OUTPUT_DIR = BASE_DIR / "trained_models_105FEAT" / "transformer"

TRAIN_FILE = TRAINING_DIR / "train_data_24c_10p_105FEAT.csv"
VAL_FILE = TRAINING_DIR / "val_data_24c_10p_105FEAT.csv"

SYMBOL = 'USDJPY.sim'
MAX_SAMPLES = 50000
CHUNK_SIZE = 25000

# THE FIX: Lower learning rate for USDJPY
LEARNING_RATE = 0.0001  # Was 0.001, now 0.0001

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ============================================================================
# MODEL DEFINITION
# ============================================================================

class SimpleTransformer(nn.Module):
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
        x = x.unsqueeze(1)
        x = self.embedding(x)
        x = self.transformer(x)
        x = x.squeeze(1)
        x = self.dropout(x)
        return self.classifier(x)


# ============================================================================
# DATA LOADING
# ============================================================================

def load_symbol_data(csv_file, symbol, max_samples=MAX_SAMPLES):
    chunks = []
    total_loaded = 0
    
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
    
    # Drop NaN
    original_len = len(df)
    df = df.dropna()
    dropped = original_len - len(df)
    if dropped > 0:
        logger.info(f"  Dropped {dropped} NaN rows")
    
    if len(df) > max_samples:
        df = df.sample(n=max_samples, random_state=42)
    
    feature_cols = [c for c in df.columns if c not in ['timestamp', 'symbol', 'label']]
    X = df[feature_cols].values.astype(np.float32)
    y = df['label'].values.astype(np.int64)
    
    return X, y, len(feature_cols)


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("="*80)
    print(f"FIXING USDJPY TRANSFORMER - LR {LEARNING_RATE}")
    print("="*80)
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Device: {device}")
    
    # Load data
    print(f"\nLoading {SYMBOL} training data...")
    X_train, y_train, num_features = load_symbol_data(TRAIN_FILE, SYMBOL)
    print(f"Loading {SYMBOL} validation data...")
    X_val, y_val, _ = load_symbol_data(VAL_FILE, SYMBOL)
    
    print(f"  Train: {len(X_train):,} samples, {num_features} features")
    print(f"  Val: {len(X_val):,} samples")
    
    # Class distribution
    unique, counts = np.unique(y_train, return_counts=True)
    print(f"  Classes: {dict(zip(unique, counts))}")
    
    # Class weights
    classes = np.unique(y_train)
    weights = compute_class_weight('balanced', classes=classes, y=y_train)
    class_weights = torch.FloatTensor(weights).to(device)
    print(f"  Class weights: {dict(zip(classes.tolist(), weights.round(2).tolist()))}")
    
    # Convert to tensors
    X_train_t = torch.FloatTensor(X_train).to(device)
    y_train_t = torch.LongTensor(y_train).to(device)
    X_val_t = torch.FloatTensor(X_val).to(device)
    y_val_t = torch.LongTensor(y_val).to(device)
    
    # Model
    model = SimpleTransformer(input_dim=num_features, num_classes=3).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
    
    # Training - 50 epochs (more epochs for lower LR)
    print(f"\nTraining 50 epochs with LR={LEARNING_RATE}...")
    model.train()
    for epoch in range(50):
        optimizer.zero_grad()
        outputs = model(X_train_t)
        loss = criterion(outputs, y_train_t)
        loss.backward()
        optimizer.step()
        
        if epoch % 10 == 0:
            with torch.no_grad():
                preds = outputs.argmax(dim=1)
                unique_preds = np.unique(preds.cpu().numpy())
            print(f"  Epoch {epoch}/50 - Loss: {loss.item():.4f} - Predicting: {sorted(unique_preds.tolist())}")
    
    # Evaluate
    model.eval()
    with torch.no_grad():
        train_preds = model(X_train_t).argmax(dim=1)
        val_preds = model(X_val_t).argmax(dim=1)
        train_acc = (train_preds == y_train_t).float().mean().item()
        val_acc = (val_preds == y_val_t).float().mean().item()
        
        pred_classes = val_preds.cpu().numpy()
        unique_preds = np.unique(pred_classes)
        print(f"\n  Final predicting classes: {sorted(unique_preds.tolist())}")
    
    print(f"\n  Train Acc: {train_acc:.4f}")
    print(f"  Val Acc: {val_acc:.4f}")
    
    # Save model
    model_path = OUTPUT_DIR / f"{SYMBOL}_transformer.pth"
    torch.save({
        'model_state_dict': model.state_dict(),
        'input_dim': num_features,
        'num_classes': 3,
        'architecture': 'SimpleTransformer',
        'learning_rate': LEARNING_RATE
    }, model_path)
    
    print(f"\n  ✓ Saved: {model_path}")
    
    # Summary
    print("\n" + "="*80)
    if val_acc >= 0.85:
        print(f"✅ SUCCESS! USDJPY Transformer fixed: {val_acc:.4f}")
    elif val_acc >= 0.50:
        print(f"⚠️ PARTIAL: USDJPY Transformer: {val_acc:.4f} (acceptable)")
    else:
        print(f"❌ STILL FAILING: {val_acc:.4f} - may need more epochs or different approach")
    print("="*80)


if __name__ == "__main__":
    main()
