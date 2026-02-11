#!/usr/bin/env python3
"""
Train 8 TabM Models on 105 Features - SOTA Tabular Architecture
================================================================
File: train_tabm_105FEAT.py
Date: 2025-11-29

TabM (ICLR 2025) - State-of-the-art for tabular deep learning
Key innovations:
1. Parameter-efficient batch ensembling 
2. Smooth decision boundaries (complements XGBoost's rectangular splits)
3. Built-in regularization through weight sharing

FIXES APPLIED:
1. Focal Loss for class imbalance (80/10/10 HOLD/BUY/SELL)
2. WeightedRandomSampler for balanced batches
3. Early stopping with patience=16
4. .dropna() before training
5. Memory-safe chunked loading

Reference: https://arxiv.org/abs/2410.24210
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
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset, WeightedRandomSampler

# ============================================================================
# CONFIGURATION
# ============================================================================
BASE_DIR = Path(r"C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System")
TRAINING_DIR = BASE_DIR / "training"
OUTPUT_DIR = BASE_DIR / "trained_models_105FEAT" / "tabm"

TRAIN_FILE = TRAINING_DIR / "train_data_24c_10p_105FEAT.csv"
VAL_FILE = TRAINING_DIR / "val_data_24c_10p_105FEAT.csv"

SYMBOLS = ['EURUSD.sim', 'GBPUSD.sim', 'USDJPY.sim', 'USDCHF.sim', 
           'AUDUSD.sim', 'USDCAD.sim', 'NZDUSD.sim', 'EURGBP.sim']

# Training parameters
MAX_SAMPLES = 50000
CHUNK_SIZE = 25000
BATCH_SIZE = 256
EPOCHS = 100
PATIENCE = 16  # TabM default
LEARNING_RATE = 1e-3
WEIGHT_DECAY = 0.01

# TabM architecture
HIDDEN_DIM = 256
N_LAYERS = 3
DROPOUT = 0.2
N_ENSEMBLES = 4  # Number of implicit ensemble members

# Create output directory
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging
log_file = TRAINING_DIR / f"training_TabM_105FEAT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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
# FOCAL LOSS - Handles Class Imbalance
# ============================================================================

class FocalLoss(nn.Module):
    """
    Focal Loss for handling severe class imbalance (80/10/10)
    Down-weights easy examples, focuses on hard-to-classify samples
    
    FL(p_t) = -alpha_t * (1 - p_t)^gamma * log(p_t)
    
    gamma=2.0: Standard focusing parameter
    alpha: Inverse class frequency weights
    """
    def __init__(self, alpha=None, gamma=2.0, reduction='mean'):
        super(FocalLoss, self).__init__()
        self.gamma = gamma
        self.alpha = alpha  # Will be set per-batch based on class weights
        self.reduction = reduction
    
    def forward(self, inputs, targets):
        ce_loss = F.cross_entropy(inputs, targets, reduction='none')
        pt = torch.exp(-ce_loss)  # Probability of correct class
        
        focal_weight = (1 - pt) ** self.gamma
        
        if self.alpha is not None:
            alpha_t = self.alpha.to(inputs.device)[targets]
            focal_loss = alpha_t * focal_weight * ce_loss
        else:
            focal_loss = focal_weight * ce_loss
        
        if self.reduction == 'mean':
            return focal_loss.mean()
        elif self.reduction == 'sum':
            return focal_loss.sum()
        return focal_loss


# ============================================================================
# TabM ARCHITECTURE - Batch Ensembling MLP
# ============================================================================

class TabMLayer(nn.Module):
    """
    Single TabM layer with batch ensembling
    
    Key insight: Multiple ensemble members share most parameters,
    differing only in low-rank perturbations (r, s factors)
    """
    def __init__(self, in_features, out_features, n_ensembles=4, dropout=0.2):
        super(TabMLayer, self).__init__()
        self.n_ensembles = n_ensembles
        
        # Shared weight matrix
        self.weight = nn.Parameter(torch.empty(out_features, in_features))
        self.bias = nn.Parameter(torch.zeros(out_features))
        
        # Per-ensemble scaling factors (batch ensembling trick)
        # r_i, s_i create ensemble diversity with minimal extra parameters
        self.r = nn.Parameter(torch.ones(n_ensembles, in_features))
        self.s = nn.Parameter(torch.ones(n_ensembles, out_features))
        
        # Normalization and regularization
        self.norm = nn.LayerNorm(out_features)
        self.dropout = nn.Dropout(dropout)
        
        # Initialize weights
        nn.init.kaiming_normal_(self.weight, mode='fan_out', nonlinearity='relu')
        nn.init.normal_(self.r, mean=1.0, std=0.1)
        nn.init.normal_(self.s, mean=1.0, std=0.1)
    
    def forward(self, x, ensemble_idx=None):
        """
        Forward pass with optional ensemble selection
        During training: randomly select ensemble member
        During inference: average all ensemble outputs
        """
        batch_size = x.shape[0]
        
        if self.training:
            # Randomly select ensemble member per sample
            if ensemble_idx is None:
                ensemble_idx = torch.randint(0, self.n_ensembles, (batch_size,), device=x.device)
            
            # Apply per-ensemble scaling: y = s * (W @ (r * x)) + b
            r_selected = self.r[ensemble_idx]  # [batch, in_features]
            s_selected = self.s[ensemble_idx]  # [batch, out_features]
            
            x_scaled = x * r_selected
            out = F.linear(x_scaled, self.weight, self.bias)
            out = out * s_selected
        else:
            # Inference: average over all ensembles
            outputs = []
            for i in range(self.n_ensembles):
                x_scaled = x * self.r[i:i+1]
                out = F.linear(x_scaled, self.weight, self.bias)
                out = out * self.s[i:i+1]
                outputs.append(out)
            out = torch.stack(outputs, dim=0).mean(dim=0)
        
        out = self.norm(out)
        out = F.relu(out)
        out = self.dropout(out)
        
        return out


class TabM(nn.Module):
    """
    TabM: Tabular Model with Parameter-Efficient Ensembling
    
    Architecture:
    - Input projection layer
    - N TabM layers with batch ensembling
    - Output classification head
    
    Key advantages over SimpleMLP:
    1. Implicit ensemble (multiple predictors, single forward pass)
    2. Better generalization through ensemble diversity
    3. Smooth decision boundaries that complement XGBoost
    """
    def __init__(self, input_dim, hidden_dim=256, n_layers=3, num_classes=3, 
                 n_ensembles=4, dropout=0.2):
        super(TabM, self).__init__()
        
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.n_layers = n_layers
        self.n_ensembles = n_ensembles
        
        # Input projection
        self.input_proj = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout)
        )
        
        # TabM layers with batch ensembling
        self.layers = nn.ModuleList([
            TabMLayer(hidden_dim, hidden_dim, n_ensembles, dropout)
            for _ in range(n_layers)
        ])
        
        # Output head
        self.output_head = nn.Linear(hidden_dim, num_classes)
    
    def forward(self, x):
        # Input projection
        x = self.input_proj(x)
        
        # TabM layers
        for layer in self.layers:
            x = layer(x) + x  # Residual connection
        
        # Classification output
        return self.output_head(x)



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
    
    # CRITICAL: Drop NaN rows
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

def train_tabm(X_train, y_train, X_val, y_val, symbol, device, num_features):
    """
    Train TabM with:
    - Focal Loss for class imbalance
    - WeightedRandomSampler for balanced batches
    - Early stopping with patience=16
    """
    
    # Compute class weights for Focal Loss
    classes = np.unique(y_train)
    class_weights = compute_class_weight('balanced', classes=classes, y=y_train)
    class_weights_dict = {int(c): w for c, w in zip(classes, class_weights)}
    logger.info(f"  Class weights: {class_weights_dict}")
    
    # Create alpha tensor for Focal Loss (inverse frequency)
    alpha = torch.tensor([class_weights_dict.get(i, 1.0) for i in range(3)], dtype=torch.float32)
    
    # Setup WeightedRandomSampler for balanced batches
    sample_weights = torch.tensor([class_weights_dict[int(y)] for y in y_train], dtype=torch.float32)
    sampler = WeightedRandomSampler(sample_weights, len(sample_weights), replacement=True)
    
    # Create data loaders
    X_train_t = torch.tensor(X_train, dtype=torch.float32)
    y_train_t = torch.tensor(y_train, dtype=torch.long)
    X_val_t = torch.tensor(X_val, dtype=torch.float32)
    y_val_t = torch.tensor(y_val, dtype=torch.long)
    
    train_dataset = TensorDataset(X_train_t, y_train_t)
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, sampler=sampler)
    val_loader = DataLoader(TensorDataset(X_val_t, y_val_t), batch_size=BATCH_SIZE*2, shuffle=False)
    
    # Initialize model
    model = TabM(
        input_dim=num_features,
        hidden_dim=HIDDEN_DIM,
        n_layers=N_LAYERS,
        num_classes=3,
        n_ensembles=N_ENSEMBLES,
        dropout=DROPOUT
    ).to(device)
    
    # Focal Loss with class weights
    criterion = FocalLoss(alpha=alpha, gamma=2.0)
    optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    
    # Learning rate scheduler
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=5)
    
    # Early stopping
    best_val_acc = 0.0
    best_model_state = None
    patience_counter = 0
    
    logger.info(f"  Training {EPOCHS} epochs (early stopping patience={PATIENCE})...")
    
    for epoch in range(EPOCHS):
        # Training
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0
        
        for X_batch, y_batch in train_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            
            optimizer.zero_grad()
            outputs = model(X_batch)
            loss = criterion(outputs, y_batch)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            _, predicted = outputs.max(1)
            train_total += y_batch.size(0)
            train_correct += predicted.eq(y_batch).sum().item()
        
        train_acc = train_correct / train_total
        
        # Validation
        model.eval()
        val_correct = 0
        val_total = 0
        predictions_set = set()
        
        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                outputs = model(X_batch)
                _, predicted = outputs.max(1)
                val_total += y_batch.size(0)
                val_correct += predicted.eq(y_batch).sum().item()
                predictions_set.update(predicted.cpu().numpy().tolist())
        
        val_acc = val_correct / val_total
        scheduler.step(val_acc)
        
        # Logging
        if epoch % 10 == 0 or epoch == EPOCHS - 1:
            logger.info(f"    Epoch {epoch}/{EPOCHS} - Train: {train_acc:.4f}, Val: {val_acc:.4f} - Predicting: {sorted(predictions_set)}")
        
        # Early stopping check
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_model_state = model.state_dict().copy()
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= PATIENCE:
                logger.info(f"    Early stopping at epoch {epoch} (patience={PATIENCE})")
                break
    
    # Load best model
    if best_model_state is not None:
        model.load_state_dict(best_model_state)
    
    # Final evaluation
    model.eval()
    with torch.no_grad():
        # Train accuracy
        train_outputs = model(X_train_t.to(device))
        _, train_preds = train_outputs.max(1)
        final_train_acc = (train_preds.cpu() == y_train_t).float().mean().item()
        
        # Val accuracy
        val_outputs = model(X_val_t.to(device))
        _, val_preds = val_outputs.max(1)
        final_val_acc = (val_preds.cpu() == y_val_t).float().mean().item()
        
        # Check predicted classes
        final_preds_set = sorted(set(val_preds.cpu().numpy().tolist()))
    
    logger.info(f"  Final predicting classes: {final_preds_set}")
    logger.info(f"  Train Acc: {final_train_acc:.4f}")
    logger.info(f"  Val Acc: {final_val_acc:.4f}")
    
    return model, final_train_acc, final_val_acc



# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    print("=" * 80)
    print("TRAINING 8 TabM MODELS - 105 FEATURES (SOTA TABULAR ARCHITECTURE)")
    print("=" * 80)
    
    logger.info("=" * 80)
    logger.info("TabM TRAINING - 105 FEATURES")
    logger.info("=" * 80)
    logger.info(f"Train file: {TRAIN_FILE}")
    logger.info(f"Val file: {VAL_FILE}")
    logger.info(f"Output: {OUTPUT_DIR}")
    logger.info(f"Architecture: hidden_dim={HIDDEN_DIM}, n_layers={N_LAYERS}, n_ensembles={N_ENSEMBLES}")
    logger.info(f"Training: batch_size={BATCH_SIZE}, lr={LEARNING_RATE}, patience={PATIENCE}")
    logger.info(f"Fixes: Focal Loss, WeightedRandomSampler, Early Stopping, .dropna()")
    logger.info("=" * 80)
    
    # Device setup
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"Device: {device}")
    print(f"Device: {device}")
    
    results = {}
    
    for i, symbol in enumerate(SYMBOLS):
        print(f"\n{'='*80}")
        print(f"[{i+1}/8] TRAINING TabM: {symbol}")
        print("=" * 80)
        
        logger.info(f"\n{'='*80}")
        logger.info(f"[{i+1}/8] TRAINING TabM: {symbol}")
        logger.info("=" * 80)
        
        try:
            # Load training data
            X_train, y_train, num_features = load_symbol_data(TRAIN_FILE, symbol)
            if X_train is None:
                logger.error(f"  No training data for {symbol}")
                results[symbol] = {'train_acc': None, 'val_acc': None, 'status': 'NO DATA'}
                continue
            
            # Load validation data
            X_val, y_val, _ = load_symbol_data(VAL_FILE, symbol)
            if X_val is None:
                logger.error(f"  No validation data for {symbol}")
                results[symbol] = {'train_acc': None, 'val_acc': None, 'status': 'NO DATA'}
                continue
            
            logger.info(f"  Train: {len(X_train):,} samples, {num_features} features")
            logger.info(f"  Val: {len(X_val):,} samples")
            print(f"  Train: {len(X_train):,} | Val: {len(X_val):,} | Features: {num_features}")
            
            # Class distribution
            unique, counts = np.unique(y_train, return_counts=True)
            class_dist = dict(zip(unique.astype(int), counts.astype(int)))
            logger.info(f"  Class distribution: {class_dist}")
            print(f"  Classes: {class_dist}")
            
            # Train model
            model, train_acc, val_acc = train_tabm(
                X_train, y_train, X_val, y_val, symbol, device, num_features
            )
            
            # Save model
            model_path = OUTPUT_DIR / f"{symbol}_tabm.pth"
            torch.save({
                'model_state_dict': model.state_dict(),
                'num_features': num_features,
                'hidden_dim': HIDDEN_DIM,
                'n_layers': N_LAYERS,
                'n_ensembles': N_ENSEMBLES,
                'dropout': DROPOUT,
                'train_acc': train_acc,
                'val_acc': val_acc,
                'symbol': symbol
            }, model_path)
            logger.info(f"  Saved: {model_path.name}")
            
            results[symbol] = {
                'train_acc': train_acc,
                'val_acc': val_acc,
                'status': 'SUCCESS'
            }
            
            # Print status
            status_icon = "OK" if val_acc >= 0.70 else ("WARN" if val_acc >= 0.50 else "FAIL")
            print(f"  {status_icon} Train: {train_acc:.4f} | Val: {val_acc:.4f}")
            print(f"  Saved: {model_path.name}")
            
        except Exception as e:
            logger.error(f"  Error training {symbol}: {e}")
            import traceback
            traceback.print_exc()
            results[symbol] = {'train_acc': None, 'val_acc': None, 'status': f'ERROR: {e}'}
        
        # Clear memory
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    print(f"\n{'='*80}")
    print("TabM TRAINING COMPLETE")
    print("=" * 80)
    
    logger.info(f"\n{'='*80}")
    logger.info("TabM TRAINING COMPLETE")
    logger.info("=" * 80)
    
    val_accs = []
    for symbol, res in results.items():
        if res['val_acc'] is not None:
            val_accs.append(res['val_acc'])
            status = "OK" if res['val_acc'] >= 0.70 else ("WARN" if res['val_acc'] >= 0.50 else "FAIL")
            print(f"  {status} {symbol}: {res['val_acc']:.4f}")
            logger.info(f"  {symbol}: {res['val_acc']:.4f}")
        else:
            print(f"  FAIL {symbol}: {res['status']}")
            logger.info(f"  {symbol}: {res['status']}")
    
    if val_accs:
        avg_acc = np.mean(val_accs)
        print(f"\n  Average: {avg_acc:.4f}")
        print(f"  Models saved to: {OUTPUT_DIR}")
        logger.info(f"Average accuracy: {avg_acc:.4f}")
        logger.info(f"Models saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
