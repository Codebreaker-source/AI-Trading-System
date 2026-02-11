#!/usr/bin/env python3
"""
Neural Network Training Pipeline - FIXED v4.0 (WEIGHTED SAMPLING)
Fixes Transformer & CNN 3.55% accuracy issue with Weighted Random Sampling

CRITICAL FIXES:
1. Focal Loss (gamma=3.0) for extreme class imbalance (15x weights + focusing)
2. Weighted Random Sampling - FORCES BALANCED BATCHES (NUCLEAR OPTION)
3. Better learning rate (0.001 vs 0.0001)
4. Gradient clipping for stability
5. Early stopping (patience=5)
6. Correct 102-feature support
7. Per-pair training with .sim suffix
8. Memory-optimized chunked loading

Expected Results:
- Before: 3.55% accuracy (predicts HOLD 100%)
- After: 60-75% accuracy (learns BUY/SELL patterns)

Why Weighted Sampling:
- v2.0 Weighted Loss failed (91% accuracy)
- v3.0 Focal Loss failed (91% accuracy)
- v4.0 Forces every batch to have ~equal SELL/HOLD/BUY
- Model CANNOT learn "predict HOLD" strategy anymore

Author: AI Trading System
Version: 4.0 (Weighted Random Sampling)
Date: 2025-11-23
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

# AGGRESSIVE MEMORY CLEANUP AT START
gc.collect()
if torch.cuda.is_available():
    torch.cuda.empty_cache()

print("\n" + "="*80)
print("NEURAL NETWORK TRAINING - FIXED v4.0 (WEIGHTED SAMPLING)")
print("Fixing 3.55% Accuracy with FORCED BALANCED BATCHES")
print("="*80)

# ==================== DEVICE SETUP ====================

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"\n✓ Using device: {device}")
if torch.cuda.is_available():
    print(f"✓ GPU: {torch.cuda.get_device_name(0)}")
    print(f"✓ GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
else:
    print("✓ Using CPU (training will be slower)")

# ==================== FOCAL LOSS ====================

class FocalLoss(nn.Module):
    """
    Focal Loss for extreme class imbalance
    
    Formula: FL(pt) = -α(1 - pt)^γ * log(pt)
    
    Args:
        alpha: Class weights (tensor of shape [num_classes])
        gamma: Focusing parameter (0-5, higher = more focus on hard examples)
               gamma=0 → same as CrossEntropyLoss
               gamma=2 → standard (moderate focus)
               gamma=3 → high focus on hard examples (recommended for extreme imbalance)
        
    How it works:
        - Easy correct predictions (high pt): Loss ≈ 0 (barely counts)
        - Hard wrong predictions (low pt): Loss >> regular loss (big penalty)
        - Forces model to focus on minority classes (BUY/SELL)
    """
    
    def __init__(self, alpha=None, gamma=2.0):
        super(FocalLoss, self).__init__()
        self.alpha = alpha
        self.gamma = gamma
        
    def forward(self, inputs, targets):
        """
        Args:
            inputs: Predictions from model (logits, before softmax) [batch_size, num_classes]
            targets: Ground truth labels [batch_size]
        
        Returns:
            Focal loss value
        """
        # Get probabilities
        ce_loss = nn.functional.cross_entropy(inputs, targets, reduction='none', weight=self.alpha)
        pt = torch.exp(-ce_loss)  # pt = probability of correct class
        
        # Apply focal term: (1 - pt)^gamma
        focal_loss = ((1 - pt) ** self.gamma) * ce_loss
        
        return focal_loss.mean()


print("✓ Focal Loss initialized (gamma=3.0 for extreme imbalance)")
print("✓ Weighted Random Sampling ready (forces balanced batches)")

# ==================== MODEL ARCHITECTURES ====================

class TransformerModel(nn.Module):
    """Transformer model for sequence learning"""
    
    def __init__(self, input_dim, d_model=128, nhead=8, num_layers=2, num_classes=3):
        super(TransformerModel, self).__init__()
        self.input_projection = nn.Linear(input_dim, d_model)
        self.positional_encoding = nn.Parameter(torch.zeros(1, 100, d_model))
        encoder_layer = nn.TransformerEncoderLayer(d_model=d_model, nhead=nhead, batch_first=True)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.classifier = nn.Linear(d_model, num_classes)
        self.dropout = nn.Dropout(0.1)
        
    def forward(self, x):
        # If 2D, add sequence dimension
        if len(x.shape) == 2:
            x = x.unsqueeze(1)  # (batch, 1, features)
        
        # Project input to model dimension
        x = self.input_projection(x)
        
        # Add positional encoding
        seq_len = x.size(1)
        x = x + self.positional_encoding[:, :seq_len, :]
        
        # Transformer encoding
        x = self.transformer(x)
        
        # Take the mean across sequence dimension
        x = x.mean(dim=1)
        
        # Classify
        x = self.dropout(x)
        x = self.classifier(x)
        
        return x


class CNNModel(nn.Module):
    """Simplified 1D CNN - FAST on CPU"""
    
    def __init__(self, input_dim, num_classes=3):
        super(CNNModel, self).__init__()
        
        # Simple 1D convolutions (no 2D reshape needed)
        self.conv1 = nn.Conv1d(1, 32, kernel_size=5, padding=2)
        self.conv2 = nn.Conv1d(32, 64, kernel_size=3, padding=1)
        self.pool = nn.MaxPool1d(2)
        self.dropout = nn.Dropout(0.3)
        
        # After 2 pools: input_dim -> input_dim/4
        fc_input = 64 * (input_dim // 4)
        self.fc1 = nn.Linear(fc_input, 128)
        self.fc2 = nn.Linear(128, num_classes)
        
    def forward(self, x):
        # x shape: (batch, features) -> (batch, 1, features)
        x = x.unsqueeze(1)
        
        x = self.pool(torch.relu(self.conv1(x)))
        x = self.pool(torch.relu(self.conv2(x)))
        x = self.dropout(x)
        
        x = x.view(x.size(0), -1)
        x = torch.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.fc2(x)
        
        return x


# ==================== MODEL TRAINER ====================

class ModelTrainer:
    """Trains Transformer and CNN models for a specific currency pair"""
    
    def __init__(self, pair_name):
        self.pair = pair_name
        self.models = {}
        self.scalers = {}
        self.feature_columns = None
        self.device = device
        
        # CRITICAL FIX: Focal Loss for extreme class imbalance
        # Class weights: [SELL, HOLD, BUY] = [15.0, 1.0, 15.0]
        # Gamma: 3.0 (high focus on hard examples)
        # This forces model to learn minority classes by making HOLD predictions almost worthless
        self.class_weights = torch.tensor([15.0, 1.0, 15.0]).to(device)
        self.gamma = 3.0  # High focusing parameter for extreme imbalance
        
        print(f"\n{'='*80}")
        print(f"INITIALIZING TRAINER FOR {pair_name}")
        print(f"{'='*80}")
        print(f"✓ Device: {self.device}")
        print(f"✓ Class weights: SELL={self.class_weights[0]:.1f}x, HOLD={self.class_weights[1]:.1f}x, BUY={self.class_weights[2]:.1f}x")
        print(f"✓ Focal Loss gamma: {self.gamma} (extreme imbalance mode)")
        
    def prepare_data(self, df):
        """Prepare features and labels"""
        
        print(f"\n[{self.pair}] Preparing data...")
        
        # Get labels
        y = df['label'].values
        
        # Get features (everything except timestamp, symbol, label)
        feature_cols = [col for col in df.columns if col not in ['timestamp', 'symbol', 'label']]
        self.feature_columns = feature_cols
        X = df[feature_cols].values
        
        # Handle NaN values
        X = np.nan_to_num(X, nan=0.0, posinf=1e6, neginf=-1e6)
        
        print(f"✓ Features: {X.shape[1]} columns")
        print(f"✓ Samples: {X.shape[0]:,}")
        
        # Show class distribution
        unique, counts = np.unique(y, return_counts=True)
        print(f"\nClass Distribution:")
        label_names = ['SELL', 'HOLD', 'BUY']
        for label, count in zip(unique, counts):
            pct = count / len(y) * 100
            name = label_names[int(label)] if int(label) < 3 else f"Class {int(label)}"
            print(f"  {int(label)} ({name}): {count:,} ({pct:.2f}%)")
        
        # Split data (stratified to maintain class balance)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Normalize features
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X_train)
        X_test = scaler.transform(X_test)
        
        self.scalers['standard'] = scaler
        
        print(f"\n✓ Train set: {X_train.shape[0]:,} samples")
        print(f"✓ Test set: {X_test.shape[0]:,} samples")
        
        return X_train, X_test, y_train, y_test
    
    def train_transformer(self, X_train, X_test, y_train, y_test):
        """Train Transformer model with weighted loss"""
        print(f"\n{'='*80}")
        print(f"[{self.pair}] TRAINING TRANSFORMER")
        print(f"{'='*80}")
        
        # Convert to tensors
        X_train_t = torch.FloatTensor(X_train).to(self.device)
        X_test_t = torch.FloatTensor(X_test).to(self.device)
        y_train_t = torch.LongTensor(y_train).to(self.device)
        y_test_t = torch.LongTensor(y_test).to(self.device)
        
        # Create model
        input_dim = X_train.shape[1]
        model = TransformerModel(
            input_dim=input_dim,
            d_model=128,
            nhead=8,
            num_layers=2,
            num_classes=3
        ).to(self.device)
        
        print(f"✓ Model created: input_dim={input_dim}")
        print(f"✓ Total parameters: {sum(p.numel() for p in model.parameters()):,}")
        
        # CRITICAL FIX: Focal Loss instead of Weighted CrossEntropyLoss
        criterion = FocalLoss(alpha=self.class_weights, gamma=self.gamma)
        print(f"✓ Using Focal Loss (alpha=[15,1,15], gamma={self.gamma})")
        
        # CRITICAL FIX: Better learning rate (0.001 vs 0.0001)
        optimizer = optim.Adam(model.parameters(), lr=0.001)
        
        # CRITICAL FIX: Learning rate scheduler
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', factor=0.5, patience=3
        )
        
        # NUCLEAR FIX: Weighted Random Sampler for Transformer
        # Forces balanced batches (equal SELL/HOLD/BUY per batch)
        # This prevents model from learning "predict HOLD 100%" strategy
        class_counts = torch.bincount(y_train_t)
        class_weights_sampling = 1.0 / class_counts.float()
        sample_weights = class_weights_sampling[y_train_t]
        sampler = WeightedRandomSampler(
            weights=sample_weights,
            num_samples=len(sample_weights),
            replacement=True
        )
        
        print(f"✓ Weighted sampling enabled:")
        print(f"  - SELL weight: {class_weights_sampling[0]:.6f}")
        print(f"  - HOLD weight: {class_weights_sampling[1]:.6f}")
        print(f"  - BUY weight:  {class_weights_sampling[2]:.6f}")
        print(f"  → Each batch will have ~equal SELL/HOLD/BUY samples")
        
        # Create data loaders with weighted sampler
        train_dataset = TensorDataset(X_train_t, y_train_t)
        train_loader = DataLoader(train_dataset, batch_size=32, sampler=sampler)
        
        # Training loop with early stopping
        best_val_loss = float('inf')
        best_model_state = model.state_dict()  # Initialize with current model
        patience_counter = 0
        patience = 5  # CRITICAL FIX: Better early stopping (was 8)
        
        print(f"\n✓ Starting training (max 50 epochs, patience={patience})...")
        
        for epoch in range(50):
            model.train()
            total_loss = 0
            correct = 0
            total = 0
            
            for batch_X, batch_y in train_loader:
                optimizer.zero_grad()
                outputs = model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                
                # CRITICAL FIX: Gradient clipping
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                
                optimizer.step()
                
                total_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                total += batch_y.size(0)
                correct += (predicted == batch_y).sum().item()
            
            train_loss = total_loss / len(train_loader)
            train_acc = correct / total
            
            # Validation
            model.eval()
            with torch.no_grad():
                val_outputs = model(X_test_t)
                val_loss = criterion(val_outputs, y_test_t).item()
                _, val_pred = torch.max(val_outputs, 1)
                val_acc = (val_pred == y_test_t).float().mean().item()
            
            # Learning rate scheduling
            scheduler.step(val_loss)
            
            # Print progress
            if (epoch + 1) % 5 == 0 or epoch == 0:
                print(f"Epoch {epoch+1:2d}/50 | Train Loss: {train_loss:.4f} | Train Acc: {train_acc:.4f} | Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.4f}")
            
            # Early stopping check
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                # Save best model
                best_model_state = model.state_dict()
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    print(f"✓ Early stopping at epoch {epoch+1}")
                    break
        
        # Load best model
        print(f"[DEBUG] Loading best model state...")
        model.load_state_dict(best_model_state)
        print(f"[DEBUG] Best model loaded successfully")
        
        # Final evaluation
        print(f"[DEBUG] Starting final evaluation...")
        model.eval()
        
        # Batched evaluation to prevent memory crash
        batch_size = 1000
        train_preds = []
        test_preds = []
        
        with torch.no_grad():
            # Evaluate training set in batches
            for i in range(0, len(X_train_t), batch_size):
                batch = X_train_t[i:i+batch_size]
                outputs = model(batch)
                _, preds = torch.max(outputs, 1)
                train_preds.append(preds)
            train_pred = torch.cat(train_preds)
            
            # Evaluate test set in batches
            for i in range(0, len(X_test_t), batch_size):
                batch = X_test_t[i:i+batch_size]
                outputs = model(batch)
                _, preds = torch.max(outputs, 1)
                test_preds.append(preds)
            test_pred = torch.cat(test_preds)
            
            train_acc = (train_pred == y_train_t).float().mean().item()
            test_acc = (test_pred == y_test_t).float().mean().item()
            
            # Prediction distribution
            train_dist = torch.bincount(train_pred, minlength=3)
            test_dist = torch.bincount(test_pred, minlength=3)
        
        print(f"[DEBUG] Final evaluation complete. Printing results...")
        print(f"\n{'='*80}")
        print(f"[{self.pair}] TRANSFORMER RESULTS")
        print(f"{'='*80}")
        print(f"✓ Train Accuracy: {train_acc:.4f}")
        print(f"✓ Test Accuracy:  {test_acc:.4f}")
        print(f"\nPrediction Distribution (Test Set):")
        for i, count in enumerate(test_dist):
            pct = count.item() / len(y_test_t) * 100
            name = ['SELL', 'HOLD', 'BUY'][i]
            print(f"  {i} ({name}): {count.item():,} ({pct:.2f}%)")
        
        self.models['transformer'] = model
        return model
    
    def train_cnn(self, X_train, X_test, y_train, y_test):
        """Train CNN model with weighted loss"""
        print(f"\n{'='*80}")
        print(f"[{self.pair}] TRAINING CNN")
        print(f"{'='*80}")
        
        # Convert to tensors
        X_train_t = torch.FloatTensor(X_train).to(self.device)
        X_test_t = torch.FloatTensor(X_test).to(self.device)
        y_train_t = torch.LongTensor(y_train).to(self.device)
        y_test_t = torch.LongTensor(y_test).to(self.device)
        
        # Create model
        input_dim = X_train.shape[1]
        model = CNNModel(
            input_dim=input_dim,
            num_classes=3
        ).to(self.device)
        
        print(f"✓ Model created: input_dim={input_dim}")
        print(f"✓ Total parameters: {sum(p.numel() for p in model.parameters()):,}")
        
        # CRITICAL FIX: Focal Loss instead of Weighted CrossEntropyLoss
        criterion = FocalLoss(alpha=self.class_weights, gamma=self.gamma)
        print(f"✓ Using Focal Loss (alpha=[15,1,15], gamma={self.gamma})")
        
        # CRITICAL FIX: Better learning rate
        optimizer = optim.Adam(model.parameters(), lr=0.001)
        
        # CRITICAL FIX: Learning rate scheduler
        scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', factor=0.5, patience=3
        )
        
        # NUCLEAR FIX: Weighted Random Sampler for CNN
        # Forces balanced batches (equal SELL/HOLD/BUY per batch)
        # This prevents model from learning "predict HOLD 100%" strategy
        class_counts = torch.bincount(y_train_t)
        class_weights_sampling = 1.0 / class_counts.float()
        sample_weights = class_weights_sampling[y_train_t]
        sampler = WeightedRandomSampler(
            weights=sample_weights,
            num_samples=len(sample_weights),
            replacement=True
        )
        
        print(f"✓ Weighted sampling enabled:")
        print(f"  - SELL weight: {class_weights_sampling[0]:.6f}")
        print(f"  - HOLD weight: {class_weights_sampling[1]:.6f}")
        print(f"  - BUY weight:  {class_weights_sampling[2]:.6f}")
        print(f"  → Each batch will have ~equal SELL/HOLD/BUY samples")
        
        # Create data loaders with weighted sampler
        train_dataset = TensorDataset(X_train_t, y_train_t)
        train_loader = DataLoader(train_dataset, batch_size=64, sampler=sampler)
        
        # Training loop with early stopping
        best_val_loss = float('inf')
        best_model_state = model.state_dict()  # Initialize with current model
        patience_counter = 0
        patience = 5
        
        print(f"\n✓ Starting CNN training (max 20 epochs, patience={patience})...")
        print(f"[DEBUG-CNN] Starting epoch loop...")
        sys.stdout.flush()
        
        for epoch in range(20):
            if epoch == 0:
                print(f"[DEBUG-CNN] Epoch 0 starting...", flush=True)
            model.train()
            total_loss = 0
            correct = 0
            total = 0
            
            for batch_X, batch_y in train_loader:
                if epoch == 0 and total == 0:
                    print(f"[DEBUG-CNN] First batch shape: {batch_X.shape}", flush=True)
                optimizer.zero_grad()
                outputs = model(batch_X)
                if epoch == 0 and total == 0:
                    print(f"[DEBUG-CNN] First batch output shape: {outputs.shape}")
                loss = criterion(outputs, batch_y)
                if epoch == 0 and total == 0:
                    print(f"[DEBUG-CNN] Loss calculated: {loss.item():.4f}")
                loss.backward()
                if epoch == 0 and total == 0:
                    print(f"[DEBUG-CNN] Backward pass done")
                
                # Gradient clipping
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                
                optimizer.step()
                if epoch == 0 and total == 0:
                    print(f"[DEBUG-CNN] First batch COMPLETE!")
                
                total_loss += loss.item()
                _, predicted = torch.max(outputs.data, 1)
                total += batch_y.size(0)
                correct += (predicted == batch_y).sum().item()
                
                # Show progress every 500 batches
                batch_num = total // 64
                if batch_num % 500 == 0 and batch_num > 0:
                    print(f"  [CNN] Epoch {epoch+1} batch {batch_num}...", flush=True)
            
            print(f"[DEBUG-CNN] Epoch {epoch+1} batch loop complete", flush=True)
            train_loss = total_loss / len(train_loader)
            train_acc = correct / total
            
            # Validation (batched to prevent memory crash)
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
            
            # Learning rate scheduling
            scheduler.step(val_loss)
            
            # Print progress
            if (epoch + 1) % 5 == 0 or epoch == 0:
                print(f"Epoch {epoch+1:2d}/20 | Train Loss: {train_loss:.4f} | Train Acc: {train_acc:.4f} | Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.4f}", flush=True)
            
            # Early stopping check
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                best_model_state = model.state_dict()
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    print(f"✓ CNN Early stopping at epoch {epoch+1}", flush=True)
                    break
        
        print(f"[DEBUG-CNN] Training loop finished", flush=True)
        # Load best model
        print(f"[DEBUG] Loading best model state...")
        model.load_state_dict(best_model_state)
        print(f"[DEBUG] Best model loaded successfully")
        
        # Final evaluation
        print(f"[DEBUG] Starting final evaluation...")
        model.eval()
        
        # Batched evaluation to prevent memory crash
        batch_size = 1000
        train_preds = []
        test_preds = []
        
        with torch.no_grad():
            # Evaluate training set in batches
            for i in range(0, len(X_train_t), batch_size):
                batch = X_train_t[i:i+batch_size]
                outputs = model(batch)
                _, preds = torch.max(outputs, 1)
                train_preds.append(preds)
            train_pred = torch.cat(train_preds)
            
            # Evaluate test set in batches
            for i in range(0, len(X_test_t), batch_size):
                batch = X_test_t[i:i+batch_size]
                outputs = model(batch)
                _, preds = torch.max(outputs, 1)
                test_preds.append(preds)
            test_pred = torch.cat(test_preds)
            
            train_acc = (train_pred == y_train_t).float().mean().item()
            test_acc = (test_pred == y_test_t).float().mean().item()
            
            # Prediction distribution
            train_dist = torch.bincount(train_pred, minlength=3)
            test_dist = torch.bincount(test_pred, minlength=3)
        
        print(f"[DEBUG] Final evaluation complete. Printing results...")
        print(f"\n{'='*80}")
        print(f"[{self.pair}] CNN RESULTS")
        print(f"{'='*80}")
        print(f"✓ Train Accuracy: {train_acc:.4f}")
        print(f"✓ Test Accuracy:  {test_acc:.4f}")
        print(f"\nPrediction Distribution (Test Set):")
        for i, count in enumerate(test_dist):
            pct = count.item() / len(y_test_t) * 100
            name = ['SELL', 'HOLD', 'BUY'][i]
            print(f"  {i} ({name}): {count.item():,} ({pct:.2f}%)")
        
        self.models['cnn'] = model
        return model
    
    def save_single_model(self, model_type):
        """Save a single model immediately after training"""
        model_dir = f"C:/Users/mt5-admin/Documents/TradingSystem/AzureDeploy/Phase4_LITE_System/trained_models_B1_CLEAN/{self.pair}"
        os.makedirs(model_dir, exist_ok=True)
        
        if model_type == 'transformer':
            torch.save(self.models['transformer'].state_dict(), f"{model_dir}/transformer.pth")
            print(f"✓ SAVED: {model_dir}/transformer.pth")
            # Also save scaler with transformer
            with open(f"{model_dir}/scaler.pkl", 'wb') as f:
                pickle.dump(self.scalers['standard'], f)
            print(f"✓ SAVED: {model_dir}/scaler.pkl")
        elif model_type == 'cnn':
            torch.save(self.models['cnn'].state_dict(), f"{model_dir}/cnn.pth")
            print(f"✓ SAVED: {model_dir}/cnn.pth")
            # Save metadata after CNN (all models done)
            metadata = {
                'pair': self.pair,
                'feature_columns': self.feature_columns,
                'training_date': datetime.now().isoformat(),
                'models': ['transformer', 'cnn'],
                'class_weights': self.class_weights.cpu().tolist(),
                'input_dim': len(self.feature_columns)
            }
            with open(f"{model_dir}/metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)
            print(f"✓ SAVED: {model_dir}/metadata.json")
    
    def save_models(self):
        """Save all trained models"""
        model_dir = f"C:/Users/mt5-admin/Documents/TradingSystem/AzureDeploy/Phase4_LITE_System/trained_models_B1_CLEAN/{self.pair}"
        os.makedirs(model_dir, exist_ok=True)
        
        print(f"\n{'='*80}")
        print(f"[{self.pair}] SAVING MODELS")
        print(f"{'='*80}")
        
        # Save Transformer
        torch.save(self.models['transformer'].state_dict(), f"{model_dir}/transformer.pth")
        print(f"✓ Saved: {model_dir}/transformer.pth")
        
        # Save CNN
        torch.save(self.models['cnn'].state_dict(), f"{model_dir}/cnn.pth")
        print(f"✓ Saved: {model_dir}/cnn.pth")
        
        # Save scaler
        with open(f"{model_dir}/scaler.pkl", 'wb') as f:
            pickle.dump(self.scalers['standard'], f)
        print(f"✓ Saved: {model_dir}/scaler.pkl")
        
        # Save metadata
        metadata = {
            'pair': self.pair,
            'feature_columns': self.feature_columns,
            'training_date': datetime.now().isoformat(),
            'models': ['transformer', 'cnn'],
            'class_weights': self.class_weights.cpu().tolist(),
            'input_dim': len(self.feature_columns)
        }
        with open(f"{model_dir}/metadata.json", 'w') as f:
            json.dump(metadata, f, indent=2)
        print(f"✓ Saved: {model_dir}/metadata.json")


# ==================== MAIN TRAINING FUNCTION ====================

def train_all_pairs():
    """Train Transformer and CNN models for all currency pairs"""
    
    # Currency pairs (with .sim suffix for OANDA demo)
    pairs = ['EURUSD.sim', 'GBPUSD.sim', 'USDJPY.sim', 'USDCHF.sim', 
             'AUDUSD.sim', 'USDCAD.sim', 'NZDUSD.sim', 'EURGBP.sim']
    
    # Load data
    data_file = 'C:/Users/mt5-admin/Documents/TradingSystem/AzureDeploy/Phase4_LITE_System/training/train_data_24c_10p_105FEAT.csv'
    
    print(f"\n{'='*80}")
    print(f"LOADING TRAINING DATA (MEMORY-OPTIMIZED)")
    print(f"{'='*80}")
    print(f"File: {data_file}")
    print(f"Strategy: Load one pair at a time to minimize RAM usage")
    
    # Train models for each pair (load data separately for each pair)
    results = {}
    
    for i, pair in enumerate(pairs, 1):
        print(f"\n\n{'#'*80}")
        print(f"# TRAINING PAIR {i}/{len(pairs)}: {pair}")
        print(f"{'#'*80}")
        
        # MEMORY FIX: Load only this pair's data in chunks
        print(f"\n[{pair}] Loading data for this pair only...")
        pair_data_chunks = []
        chunk_size = 100000  # Load 100k rows at a time
        
        for chunk in pd.read_csv(data_file, chunksize=chunk_size):
            # Filter for this pair only
            pair_chunk = chunk[chunk['symbol'] == pair]
            if len(pair_chunk) > 0:
                pair_data_chunks.append(pair_chunk)
            del chunk  # Free memory immediately
            gc.collect()
        
        # Combine chunks for this pair
        if len(pair_data_chunks) == 0:
            print(f"⚠ WARNING: No data found for {pair}, skipping...")
            continue
        
        pair_data = pd.concat(pair_data_chunks, ignore_index=True)
        del pair_data_chunks  # Free memory
        gc.collect()
        
        print(f"✓ Loaded: {len(pair_data):,} samples for {pair}")
        
        # Show label distribution for this pair
        print(f"\nLabel Distribution for {pair}:")
        for label, count in pair_data['label'].value_counts().sort_index().items():
            pct = count / len(pair_data) * 100
            name = ['SELL', 'HOLD', 'BUY'][int(label)] if int(label) < 3 else f"Class {int(label)}"
            print(f"  {int(label)} ({name}): {count:,} ({pct:.2f}%)")
        
        # Create trainer
        trainer = ModelTrainer(pair)
        
        # Prepare data
        X_train, X_test, y_train, y_test = trainer.prepare_data(pair_data)
        
        # Check if Transformer already exists
        transformer_path = f"C:/Users/mt5-admin/Documents/TradingSystem/AzureDeploy/Phase4_LITE_System/trained_models_B1_CLEAN/{pair}/transformer.pth"
        if os.path.exists(transformer_path):
            print(f"\n✓ Transformer already trained for {pair}, skipping...")
        else:
            # Train Transformer
            transformer = trainer.train_transformer(X_train, X_test, y_train, y_test)
            # SAVE TRANSFORMER IMMEDIATELY
            trainer.save_single_model('transformer')
            gc.collect()
        
        # Check if CNN already exists
        cnn_path = f"C:/Users/mt5-admin/Documents/TradingSystem/AzureDeploy/Phase4_LITE_System/trained_models_B1_CLEAN/{pair}/cnn.pth"
        if os.path.exists(cnn_path):
            print(f"\n✓ CNN already trained for {pair}, skipping...")
        else:
            # Train CNN
            cnn = trainer.train_cnn(X_train, X_test, y_train, y_test)
            # Save CNN
            trainer.save_single_model('cnn')
        
        # Collect results
        results[pair] = {
            'transformer_acc': trainer.models['transformer'],
            'cnn_acc': trainer.models['cnn'],
            'samples': len(pair_data)
        }
        
        # Clean up memory
        del trainer
        del pair_data
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        print(f"\n✓ {pair} training complete!")
    
    # Final summary
    print(f"\n\n{'='*80}")
    print(f"TRAINING COMPLETE - ALL PAIRS")
    print(f"{'='*80}")
    print(f"✓ Trained {len(results)} pairs")
    print(f"✓ Models per pair: 2 (Transformer + CNN)")
    print(f"✓ Total models trained: {len(results) * 2}")
    print(f"\n✓ All models saved to: trained_models_B1_CLEAN/")
    print(f"\n{'='*80}")
    print(f"READY FOR DEPLOYMENT")
    print(f"{'='*80}")


if __name__ == "__main__":
    train_all_pairs()
