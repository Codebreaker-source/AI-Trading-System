"""
CNN-ONLY Training Script
Trains just CNN models - skips Transformer completely
"""

import pandas as pd
import numpy as np
import sys
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader, WeightedRandomSampler
import pickle
import json
import os
from datetime import datetime
import gc

# Aggressive cleanup
gc.collect()

print("\n" + "="*80)
print("CNN-ONLY TRAINING")
print("="*80)

device = torch.device('cpu')
print(f"✓ Using CPU")


# ==================== FOCAL LOSS ====================

class FocalLoss(nn.Module):
    def __init__(self, alpha=None, gamma=2.0):
        super(FocalLoss, self).__init__()
        self.alpha = alpha
        self.gamma = gamma
        
    def forward(self, inputs, targets):
        ce_loss = nn.CrossEntropyLoss(weight=self.alpha, reduction='none')(inputs, targets)
        pt = torch.exp(-ce_loss)
        focal_loss = ((1 - pt) ** self.gamma) * ce_loss
        return focal_loss.mean()

# ==================== SIMPLE 1D CNN ====================

class CNNModel(nn.Module):
    """Simple 1D CNN - fast on CPU"""
    
    def __init__(self, input_dim, num_classes=3):
        super(CNNModel, self).__init__()
        
        self.conv1 = nn.Conv1d(1, 32, kernel_size=5, padding=2)
        self.conv2 = nn.Conv1d(32, 64, kernel_size=3, padding=1)
        self.pool = nn.MaxPool1d(2)
        self.dropout = nn.Dropout(0.3)
        
        fc_input = 64 * (input_dim // 4)
        self.fc1 = nn.Linear(fc_input, 128)
        self.fc2 = nn.Linear(128, num_classes)
        
    def forward(self, x):
        x = x.unsqueeze(1)
        x = self.pool(torch.relu(self.conv1(x)))
        x = self.pool(torch.relu(self.conv2(x)))
        x = self.dropout(x)
        x = x.view(x.size(0), -1)
        x = torch.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.fc2(x)
        return x

# ==================== TRAIN CNN ====================

def train_cnn_for_pair(pair):
    print(f"\n{'#'*80}")
    print(f"# TRAINING CNN FOR: {pair}")
    print(f"{'#'*80}")
    
    # Load data for this pair only
    data_file = 'C:/Users/mt5-admin/Documents/TradingSystem/AzureDeploy/Phase4_LITE_System/training/train_data_24c_10p_105FEAT.csv'
    
    print(f"Loading {pair} data...")
    pair_data_chunks = []
    for chunk in pd.read_csv(data_file, chunksize=100000):
        pair_chunk = chunk[chunk['symbol'] == pair]
        if len(pair_chunk) > 0:
            pair_data_chunks.append(pair_chunk)
        del chunk
        gc.collect()
    
    if len(pair_data_chunks) == 0:
        print(f"⚠ No data for {pair}")
        return
    
    pair_data = pd.concat(pair_data_chunks, ignore_index=True)
    del pair_data_chunks
    gc.collect()
    
    print(f"✓ Loaded: {len(pair_data):,} samples")
    
    # Prepare features
    exclude_cols = ['symbol', 'timestamp', 'label', 'actual_pips_change']
    feature_columns = [c for c in pair_data.columns if c not in exclude_cols]
    
    X = pair_data[feature_columns].values
    y = pair_data['label'].values.astype(int)
    
    # Scale
    scaler = StandardScaler()
    X = scaler.fit_transform(X)
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    print(f"✓ Train: {len(X_train):,} | Test: {len(X_test):,}")
    
    del pair_data
    gc.collect()

    
    # Convert to tensors
    X_train_t = torch.FloatTensor(X_train)
    X_test_t = torch.FloatTensor(X_test)
    y_train_t = torch.LongTensor(y_train)
    y_test_t = torch.LongTensor(y_test)
    
    # Create model
    model = CNNModel(input_dim=len(feature_columns))
    print(f"✓ CNN params: {sum(p.numel() for p in model.parameters()):,}")
    
    # Class weights and focal loss
    class_weights = torch.FloatTensor([15.0, 1.0, 15.0])
    criterion = FocalLoss(alpha=class_weights, gamma=3.0)
    optimizer = optim.Adam(model.parameters(), lr=0.001)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=3, factor=0.5)
    
    # Weighted sampler
    class_counts = torch.bincount(y_train_t)
    class_weights_sampling = 1.0 / class_counts.float()
    sample_weights = class_weights_sampling[y_train_t]
    sampler = WeightedRandomSampler(sample_weights, len(sample_weights), replacement=True)
    
    train_dataset = TensorDataset(X_train_t, y_train_t)
    train_loader = DataLoader(train_dataset, batch_size=64, sampler=sampler)
    
    # Training
    best_val_loss = float('inf')
    best_model_state = model.state_dict()
    patience_counter = 0
    
    print(f"✓ Starting training (20 epochs)...")
    
    for epoch in range(20):
        model.train()
        total_loss = 0
        correct = 0
        total = 0
        
        for batch_X, batch_y in train_loader:
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            
            total_loss += loss.item()
            _, predicted = torch.max(outputs, 1)
            total += batch_y.size(0)
            correct += (predicted == batch_y).sum().item()
        
        train_loss = total_loss / len(train_loader)
        train_acc = correct / total
        
        # Validation (batched)
        model.eval()
        val_preds = []
        val_losses = []
        with torch.no_grad():
            for i in range(0, len(X_test_t), 1000):
                batch = X_test_t[i:i+1000]
                batch_y = y_test_t[i:i+1000]
                outputs = model(batch)
                val_losses.append(criterion(outputs, batch_y).item())
                _, preds = torch.max(outputs, 1)
                val_preds.append(preds)
        val_pred = torch.cat(val_preds)
        val_loss = sum(val_losses) / len(val_losses)
        val_acc = (val_pred == y_test_t).float().mean().item()
        
        scheduler.step(val_loss)
        
        if (epoch + 1) % 5 == 0 or epoch == 0:
            print(f"Epoch {epoch+1:2d}/20 | Loss: {train_loss:.4f} | Acc: {train_acc:.4f} | Val: {val_acc:.4f}", flush=True)
        
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            best_model_state = model.state_dict()
        else:
            patience_counter += 1
            if patience_counter >= 5:
                print(f"✓ Early stopping at epoch {epoch+1}")
                break
    
    # Load best and evaluate
    model.load_state_dict(best_model_state)
    model.eval()

    
    # Final eval
    test_preds = []
    with torch.no_grad():
        for i in range(0, len(X_test_t), 1000):
            outputs = model(X_test_t[i:i+1000])
            _, preds = torch.max(outputs, 1)
            test_preds.append(preds)
    test_pred = torch.cat(test_preds)
    test_acc = (test_pred == y_test_t).float().mean().item()
    test_dist = torch.bincount(test_pred, minlength=3)
    
    print(f"\n{'='*60}")
    print(f"[{pair}] CNN RESULTS")
    print(f"{'='*60}")
    print(f"✓ Test Accuracy: {test_acc:.4f}")
    print(f"\nPrediction Distribution:")
    for i, count in enumerate(test_dist):
        pct = count.item() / len(y_test_t) * 100
        name = ['SELL', 'HOLD', 'BUY'][i]
        print(f"  {name}: {count.item():,} ({pct:.2f}%)")
    
    # Save
    save_dir = f"C:/Users/mt5-admin/Documents/TradingSystem/AzureDeploy/Phase4_LITE_System/trained_models_B1_CLEAN/{pair}"
    os.makedirs(save_dir, exist_ok=True)
    
    torch.save(model.state_dict(), f"{save_dir}/cnn.pth")
    print(f"✓ SAVED: {save_dir}/cnn.pth")
    
    with open(f"{save_dir}/scaler.pkl", 'wb') as f:
        pickle.dump(scaler, f)
    print(f"✓ SAVED: {save_dir}/scaler.pkl")
    
    # Cleanup
    del model, X_train_t, X_test_t, y_train_t, y_test_t
    gc.collect()
    
    return test_acc

# ==================== MAIN ====================

if __name__ == "__main__":
    # Just train EURUSD CNN first
    train_cnn_for_pair('EURUSD.sim')
    
    print("\n" + "="*80)
    print("CNN TRAINING COMPLETE")
    print("="*80)
