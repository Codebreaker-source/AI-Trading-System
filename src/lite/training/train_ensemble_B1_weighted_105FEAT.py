#!/usr/bin/env python3
"""
B1 Ensemble Training Script with Class Weighting - 105 FEATURES
File: train_ensemble_B1_weighted_105FEAT.py
Version: 2.0
Date: 2025-11-17

Configuration: B1 (24 candles, 10 pips lookback)
Purpose: Train 24 ensemble models with class weighting - ENHANCED WITH 105 FEATURES
Data Format: 105 columns (timestamp, symbol, 102 features, label)
Memory Strategy: Load per-pair only, sequential training, aggressive cleanup
CLASS WEIGHTING: XGBoost uses scale_pos_weight, Neural nets use weighted CrossEntropyLoss

NEW IN V2.0:
- 102 features (was 58)
- MACD + EMA features
- Multi-timeframe confirmation (H1/H4)
- Meta-labeling (position sizing)
- HMM regime detection
- Economic calendar features
"""

import os
import sys
import time
import pickle
import logging
import gc
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

import pandas as pd
import numpy as np
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import LabelEncoder
from sklearn.utils.class_weight import compute_class_weight
import xgboost as xgb

# PyTorch imports
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('training_B1_105FEAT_log.txt'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== CLASS WEIGHTING UTILITIES ====================

def calculate_class_weights(y_train: np.ndarray) -> Tuple[Dict[int, float], np.ndarray]:
    """
    Calculate balanced class weights for imbalanced data
    
    Args:
        y_train: Training labels (numeric: 0=SELL, 1=HOLD, 2=BUY)
    
    Returns:
        class_weights_dict: Dictionary {class: weight}
        class_weights_array: Array of weights for each class
    """
    classes = np.unique(y_train)
    weights = compute_class_weight('balanced', classes=classes, y=y_train)
    
    # Convert to dictionary format
    class_weights_dict = {int(c): float(w) for c, w in zip(classes, weights)}
    
    logger.info(f"\n{'='*60}")
    logger.info(f"CLASS WEIGHTS (to handle imbalance):")
    for cls, weight in class_weights_dict.items():
        label_name = ['SELL', 'HOLD', 'BUY'][cls]
        count = len(y_train[y_train == cls])
        pct = count / len(y_train) * 100
        logger.info(f"  Class {cls} ({label_name:4s}): {weight:5.2f}x importance ({count:,} samples, {pct:.2f}%)")
    logger.info(f"{'='*60}\n")
    
    return class_weights_dict, weights

# ==================== CONFIGURATION ====================

class Config:
    """B1 Training configuration (24 candles, 10 pips) - 105 FEATURES"""
    
    # Paths - UPDATED FOR 105-FEATURE DATASETS
    BASE_DIR = Path(r"C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System")
    TRAIN_FILE = BASE_DIR / "training" / "train_data_24c_10p_105FEAT.csv"
    VAL_FILE = BASE_DIR / "training" / "val_data_24c_10p_105FEAT.csv"
    TEST_FILE = BASE_DIR / "training" / "test_data_24c_10p_105FEAT.csv"
    MODEL_DIR = BASE_DIR / "trained_models_B1_105FEAT"
    
    # Currency pairs
    PAIRS = [
        'EURUSD.sim', 'GBPUSD.sim', 'USDJPY.sim', 'USDCHF.sim',
        'AUDUSD.sim', 'USDCAD.sim', 'NZDUSD.sim', 'EURGBP.sim'
    ]
    
    # Model configuration - UPDATED FOR 105 FEATURES
    NUM_FEATURES = 102  # Was 58, now 102
    SEQUENCE_LENGTH = 20
    NUM_CLASSES = 3
    
    # MEMORY SETTINGS - CRITICAL
    CHUNK_SIZE = 5000
    BATCH_SIZE = 64
    MAX_SAMPLES_PER_PAIR = 300000
    
    # XGBoost (memory efficient) - No changes needed, auto-detects features
    XGBOOST_PARAMS = {
        'n_estimators': 100,
        'max_depth': 5,
        'learning_rate': 0.1,
        'subsample': 0.7,
        'colsample_bytree': 0.7,
        'objective': 'multi:softprob',
        'num_class': 3,
        'eval_metric': 'mlogloss',
        'random_state': 42,
        'n_jobs': 4,
        'tree_method': 'hist'
    }
    
    # Transformer (memory efficient)
    TRANSFORMER_PARAMS = {
        'embedding_dim': 32,
        'num_heads': 2,
        'num_layers': 1,
        'ff_dim': 64,
        'dropout': 0.1,
        'learning_rate': 0.001,
        'batch_size': 64,
        'epochs': 30,
        'patience': 5
    }
    
    # CNN (memory efficient)
    CNN_PARAMS = {
        'filters': [32, 64],
        'kernel_size': 3,
        'pool_size': 2,
        'dense_units': 64,
        'dropout': 0.2,
        'learning_rate': 0.001,
        'batch_size': 64,
        'epochs': 30,
        'patience': 5
    }

# ==================== MEMORY-EFFICIENT DATA LOADING ====================

class ChunkedDataLoader:
    """Load data in chunks to avoid memory crashes"""
    
    def __init__(self, config: Config):
        self.config = config
        
    def load_pair_data_chunked(self, file_path: Path, pair: str) -> Tuple[np.ndarray, np.ndarray]:
        """
        Load data for one pair only, in chunks
        NOTE: Labels are already numeric (0=SELL, 1=HOLD, 2=BUY)
        """
        logger.info(f"Loading {pair} from {file_path.name} (chunked)...")
        
        X_list = []
        y_list = []
        total_rows = 0
        
        # Read in chunks
        for chunk in pd.read_csv(file_path, chunksize=self.config.CHUNK_SIZE):
            # Filter for this pair only
            pair_chunk = chunk[chunk['symbol'] == pair]
            
            if len(pair_chunk) == 0:
                continue
            
            # Extract features
            feature_cols = [col for col in pair_chunk.columns 
                           if col not in ['timestamp', 'symbol', 'label']]
            
            X_chunk = pair_chunk[feature_cols].values
            y_chunk = pair_chunk['label'].values  # Already numeric!
            
            X_list.append(X_chunk)
            y_list.append(y_chunk)
            total_rows += len(pair_chunk)
            
            # Memory limit check
            if total_rows >= self.config.MAX_SAMPLES_PER_PAIR:
                logger.warning(f"Reached max samples limit ({self.config.MAX_SAMPLES_PER_PAIR})")
                break
            
            # Clear chunk from memory
            del chunk, pair_chunk, X_chunk, y_chunk
            gc.collect()
        
        # Combine all chunks
        if len(X_list) == 0:
            raise ValueError(f"No data found for {pair}")
        
        X = np.vstack(X_list)
        y = np.concatenate(y_list)
        
        logger.info(f"{pair}: {len(X):,} samples loaded with {X.shape[1]} features")
        
        # Clean up
        del X_list, y_list
        gc.collect()
        
        return X, y
    
    def create_sequences_chunked(self, X: np.ndarray, y: np.ndarray, 
                                  seq_length: int) -> Tuple[np.ndarray, np.ndarray]:
        """Create sequences in chunks to save memory"""
        logger.info(f"Creating sequences (length={seq_length})...")
        
        n_sequences = len(X) - seq_length
        X_seq = np.zeros((n_sequences, seq_length, X.shape[1]), dtype=np.float32)
        y_seq = np.zeros(n_sequences, dtype=np.int64)
        
        chunk_size = 10000
        for i in range(0, n_sequences, chunk_size):
            end_idx = min(i + chunk_size, n_sequences)
            
            for j in range(i, end_idx):
                X_seq[j] = X[j:j+seq_length]
                y_seq[j] = y[j+seq_length]
            
            if (i // chunk_size) % 10 == 0:
                logger.info(f"  Sequences created: {i:,}/{n_sequences:,}")
        
        logger.info(f"Total sequences: {len(X_seq):,}")
        return X_seq, y_seq

# ==================== PYTORCH MODELS ====================

class TransformerModel(nn.Module):
    """Lightweight Transformer - UPDATED FOR 102 FEATURES"""
    
    def __init__(self, input_dim: int, embedding_dim: int, num_heads: int,
                 num_layers: int, ff_dim: int, num_classes: int, dropout: float = 0.1):
        super().__init__()
        
        self.embedding = nn.Linear(input_dim, embedding_dim)
        
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embedding_dim,
            nhead=num_heads,
            dim_feedforward=ff_dim,
            dropout=dropout,
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        self.fc = nn.Linear(embedding_dim, num_classes)
        self.dropout = nn.Dropout(dropout)
        
    def forward(self, x):
        x = self.embedding(x)
        x = self.transformer(x)
        x = x.mean(dim=1)
        x = self.dropout(x)
        x = self.fc(x)
        return x

class CNNModel(nn.Module):
    """Lightweight 1D CNN - UPDATED FOR 102 FEATURES"""
    
    def __init__(self, input_dim: int, filters: List[int], kernel_size: int,
                 pool_size: int, dense_units: int, num_classes: int, dropout: float = 0.2):
        super().__init__()
        
        layers = []
        in_channels = input_dim
        
        for out_channels in filters:
            layers.extend([
                nn.Conv1d(in_channels, out_channels, kernel_size, padding=kernel_size//2),
                nn.ReLU(),
                nn.MaxPool1d(pool_size)
            ])
            in_channels = out_channels
        
        self.conv_layers = nn.Sequential(*layers)
        self.adaptive_pool = nn.AdaptiveAvgPool1d(1)
        self.fc1 = nn.Linear(filters[-1], dense_units)
        self.dropout = nn.Dropout(dropout)
        self.fc2 = nn.Linear(dense_units, num_classes)
        
    def forward(self, x):
        x = x.transpose(1, 2)
        x = self.conv_layers(x)
        x = self.adaptive_pool(x).squeeze(-1)
        x = torch.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.fc2(x)
        return x

class SequenceDataset(Dataset):
    """PyTorch dataset"""
    
    def __init__(self, X, y):
        self.X = torch.FloatTensor(X)
        self.y = torch.LongTensor(y)
    
    def __len__(self):
        return len(self.y)
    
    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

# ==================== TRAINERS WITH CLASS WEIGHTING ====================

class XGBoostTrainer:
    """Train XGBoost with class weighting"""
    
    def __init__(self, config: Config):
        self.config = config
    
    def train(self, X_train: np.ndarray, y_train: np.ndarray,
             X_val: np.ndarray, y_val: np.ndarray, pair: str) -> xgb.XGBClassifier:
        """Train XGBoost with class weighting"""
        logger.info(f"Training XGBoost for {pair}...")
        
        # Calculate scale_pos_weight for XGBoost
        hold_count = len(y_train[y_train == 1])
        action_count = len(y_train[y_train != 1])
        scale_pos_weight = hold_count / action_count if action_count > 0 else 1.0
        
        logger.info(f"XGBoost class balance:")
        logger.info(f"  HOLD samples: {hold_count:,}")
        logger.info(f"  BUY+SELL samples: {action_count:,}")
        logger.info(f"  scale_pos_weight: {scale_pos_weight:.2f}")
        
        model = xgb.XGBClassifier(
            scale_pos_weight=scale_pos_weight,
            **self.config.XGBOOST_PARAMS
        )
        
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=False
        )
        
        train_pred = model.predict(X_train)
        val_pred = model.predict(X_val)
        
        train_acc = accuracy_score(y_train, train_pred)
        val_acc = accuracy_score(y_val, val_pred)
        
        logger.info(f"{pair} XGBoost - Train: {train_acc:.4f}, Val: {val_acc:.4f}")
        
        return model

class TransformerTrainer:
    """Train Transformer with class weighting"""
    
    def __init__(self, config: Config):
        self.config = config
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        logger.info(f"Device: {self.device}")
    
    def train(self, X_train: np.ndarray, y_train: np.ndarray,
             X_val: np.ndarray, y_val: np.ndarray, pair: str) -> nn.Module:
        """Train Transformer with class weighting"""
        logger.info(f"Training Transformer for {pair}...")
        
        train_dataset = SequenceDataset(X_train, y_train)
        val_dataset = SequenceDataset(X_val, y_val)
        
        train_loader = DataLoader(train_dataset, batch_size=self.config.TRANSFORMER_PARAMS['batch_size'],
                                 shuffle=True, num_workers=0)
        val_loader = DataLoader(val_dataset, batch_size=self.config.TRANSFORMER_PARAMS['batch_size'],
                               num_workers=0)
        
        model = TransformerModel(
            input_dim=self.config.NUM_FEATURES,  # Now 102 instead of 58
            embedding_dim=self.config.TRANSFORMER_PARAMS['embedding_dim'],
            num_heads=self.config.TRANSFORMER_PARAMS['num_heads'],
            num_layers=self.config.TRANSFORMER_PARAMS['num_layers'],
            ff_dim=self.config.TRANSFORMER_PARAMS['ff_dim'],
            num_classes=self.config.NUM_CLASSES,
            dropout=self.config.TRANSFORMER_PARAMS['dropout']
        ).to(self.device)
        
        # Calculate class weights
        _, class_weights_array = calculate_class_weights(y_train)
        class_weights_tensor = torch.FloatTensor(class_weights_array).to(self.device)
        
        criterion = nn.CrossEntropyLoss(weight=class_weights_tensor)
        optimizer = optim.Adam(model.parameters(), lr=self.config.TRANSFORMER_PARAMS['learning_rate'])
        
        best_val_acc = 0
        patience_counter = 0
        
        for epoch in range(self.config.TRANSFORMER_PARAMS['epochs']):
            model.train()
            train_correct = 0
            train_total = 0
            
            for X_batch, y_batch in train_loader:
                X_batch = X_batch.to(self.device)
                y_batch = y_batch.to(self.device)
                
                optimizer.zero_grad()
                outputs = model(X_batch)
                loss = criterion(outputs, y_batch)
                loss.backward()
                optimizer.step()
                
                _, predicted = outputs.max(1)
                train_total += y_batch.size(0)
                train_correct += predicted.eq(y_batch).sum().item()
                
                del X_batch, y_batch, outputs, loss
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            
            train_acc = train_correct / train_total
            
            model.eval()
            val_correct = 0
            val_total = 0
            
            with torch.no_grad():
                for X_batch, y_batch in val_loader:
                    X_batch = X_batch.to(self.device)
                    y_batch = y_batch.to(self.device)
                    
                    outputs = model(X_batch)
                    _, predicted = outputs.max(1)
                    val_total += y_batch.size(0)
                    val_correct += predicted.eq(y_batch).sum().item()
                    
                    del X_batch, y_batch, outputs
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
            
            val_acc = val_correct / val_total
            
            if (epoch + 1) % 5 == 0 or epoch == 0:
                logger.info(f"  Epoch {epoch+1}: Train={train_acc:.4f}, Val={val_acc:.4f}")
            
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= self.config.TRANSFORMER_PARAMS['patience']:
                    logger.info(f"  Early stop at epoch {epoch+1}")
                    break
        
        logger.info(f"{pair} Transformer - Best Val: {best_val_acc:.4f}")
        
        return model.cpu()

class CNNTrainer:
    """Train CNN with class weighting"""
    
    def __init__(self, config: Config):
        self.config = config
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    def train(self, X_train: np.ndarray, y_train: np.ndarray,
             X_val: np.ndarray, y_val: np.ndarray, pair: str) -> nn.Module:
        """Train CNN with class weighting"""
        logger.info(f"Training CNN for {pair}...")
        
        train_dataset = SequenceDataset(X_train, y_train)
        val_dataset = SequenceDataset(X_val, y_val)
        
        train_loader = DataLoader(train_dataset, batch_size=self.config.CNN_PARAMS['batch_size'],
                                 shuffle=True, num_workers=0)
        val_loader = DataLoader(val_dataset, batch_size=self.config.CNN_PARAMS['batch_size'],
                               num_workers=0)
        
        model = CNNModel(
            input_dim=self.config.NUM_FEATURES,  # Now 102 instead of 58
            filters=self.config.CNN_PARAMS['filters'],
            kernel_size=self.config.CNN_PARAMS['kernel_size'],
            pool_size=self.config.CNN_PARAMS['pool_size'],
            dense_units=self.config.CNN_PARAMS['dense_units'],
            num_classes=self.config.NUM_CLASSES,
            dropout=self.config.CNN_PARAMS['dropout']
        ).to(self.device)
        
        # Calculate class weights
        _, class_weights_array = calculate_class_weights(y_train)
        class_weights_tensor = torch.FloatTensor(class_weights_array).to(self.device)
        
        criterion = nn.CrossEntropyLoss(weight=class_weights_tensor)
        optimizer = optim.Adam(model.parameters(), lr=self.config.CNN_PARAMS['learning_rate'])
        
        best_val_acc = 0
        patience_counter = 0
        
        for epoch in range(self.config.CNN_PARAMS['epochs']):
            model.train()
            train_correct = 0
            train_total = 0
            
            for X_batch, y_batch in train_loader:
                X_batch = X_batch.to(self.device)
                y_batch = y_batch.to(self.device)
                
                optimizer.zero_grad()
                outputs = model(X_batch)
                loss = criterion(outputs, y_batch)
                loss.backward()
                optimizer.step()
                
                _, predicted = outputs.max(1)
                train_total += y_batch.size(0)
                train_correct += predicted.eq(y_batch).sum().item()
                
                del X_batch, y_batch, outputs, loss
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            
            train_acc = train_correct / train_total
            
            model.eval()
            val_correct = 0
            val_total = 0
            
            with torch.no_grad():
                for X_batch, y_batch in val_loader:
                    X_batch = X_batch.to(self.device)
                    y_batch = y_batch.to(self.device)
                    
                    outputs = model(X_batch)
                    _, predicted = outputs.max(1)
                    val_total += y_batch.size(0)
                    val_correct += predicted.eq(y_batch).sum().item()
                    
                    del X_batch, y_batch, outputs
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
            
            val_acc = val_correct / val_total
            
            if (epoch + 1) % 5 == 0 or epoch == 0:
                logger.info(f"  Epoch {epoch+1}: Train={train_acc:.4f}, Val={val_acc:.4f}")
            
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= self.config.CNN_PARAMS['patience']:
                    logger.info(f"  Early stop at epoch {epoch+1}")
                    break
        
        logger.info(f"{pair} CNN - Best Val: {best_val_acc:.4f}")
        
        return model.cpu()

# ==================== MAIN ORCHESTRATOR ====================

class EnsembleTrainer:
    """Sequential training with memory management"""
    
    def __init__(self, config: Config):
        self.config = config
        self.data_loader = ChunkedDataLoader(config)
        self.config.MODEL_DIR.mkdir(parents=True, exist_ok=True)
    
    def train_all_models(self):
        """Train all 24 models SEQUENTIALLY"""
        logger.info("="*80)
        logger.info("B1 ENSEMBLE TRAINING - 24 MODELS WITH 105 FEATURES")
        logger.info("Configuration: 24 candles, 10 pips, 102 features")
        logger.info("="*80)
        
        start_time = time.time()
        results = {}
        
        for pair_idx, pair in enumerate(self.config.PAIRS, 1):
            logger.info(f"\n{'='*80}")
            logger.info(f"PAIR {pair_idx}/8: {pair}")
            logger.info(f"{'='*80}")
            
            pair_start = time.time()
            
            try:
                # Load data
                logger.info("Loading data...")
                X_train, y_train = self.data_loader.load_pair_data_chunked(
                    self.config.TRAIN_FILE, pair
                )
                X_val, y_val = self.data_loader.load_pair_data_chunked(
                    self.config.VAL_FILE, pair
                )
                
                # Train XGBoost
                logger.info(f"\n[1/3] XGBoost for {pair}")
                xgb_trainer = XGBoostTrainer(self.config)
                xgb_model = xgb_trainer.train(X_train, y_train, X_val, y_val, pair)
                
                xgb_path = self.config.MODEL_DIR / f"{pair}_xgboost.pkl"
                with open(xgb_path, 'wb') as f:
                    pickle.dump(xgb_model, f)
                logger.info(f"[OK] Saved: {xgb_path.name}")
                
                del xgb_trainer, xgb_model
                gc.collect()
                
                # Train Transformer
                logger.info(f"\n[2/3] Transformer for {pair}")
                X_train_seq, y_train_seq = self.data_loader.create_sequences_chunked(
                    X_train, y_train, self.config.SEQUENCE_LENGTH
                )
                X_val_seq, y_val_seq = self.data_loader.create_sequences_chunked(
                    X_val, y_val, self.config.SEQUENCE_LENGTH
                )
                
                transformer_trainer = TransformerTrainer(self.config)
                transformer_model = transformer_trainer.train(
                    X_train_seq, y_train_seq, X_val_seq, y_val_seq, pair
                )
                
                transformer_path = self.config.MODEL_DIR / f"{pair}_transformer.pkl"
                torch.save(transformer_model.state_dict(), transformer_path)
                logger.info(f"[OK] Saved: {transformer_path.name}")
                
                del transformer_trainer, transformer_model
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
                # Train CNN
                logger.info(f"\n[3/3] CNN for {pair}")
                cnn_trainer = CNNTrainer(self.config)
                cnn_model = cnn_trainer.train(
                    X_train_seq, y_train_seq, X_val_seq, y_val_seq, pair
                )
                
                cnn_path = self.config.MODEL_DIR / f"{pair}_cnn.pkl"
                torch.save(cnn_model.state_dict(), cnn_path)
                logger.info(f"[OK] Saved: {cnn_path.name}")
                
                del cnn_trainer, cnn_model
                del X_train_seq, y_train_seq, X_val_seq, y_val_seq
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                
                del X_train, y_train, X_val, y_val
                gc.collect()
                
                pair_time = time.time() - pair_start
                logger.info(f"\n[OK] {pair} COMPLETE in {pair_time/60:.1f} min")
                results[pair] = "SUCCESS"
                
            except Exception as e:
                logger.error(f"[X] ERROR training {pair}: {e}", exc_info=True)
                results[pair] = f"FAILED: {str(e)}"
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
        
        # Final summary
        total_time = time.time() - start_time
        logger.info("\n" + "="*80)
        logger.info("B1 TRAINING COMPLETE - 105 FEATURES")
        logger.info("="*80)
        logger.info(f"Total time: {total_time/3600:.2f} hours")
        logger.info("\nResults:")
        success_count = 0
        for pair, status in results.items():
            symbol = "[OK]" if status == "SUCCESS" else "[X]"
            logger.info(f"  {symbol} {pair}: {status}")
            if status == "SUCCESS":
                success_count += 1
        
        model_files = list(self.config.MODEL_DIR.glob("*.pkl"))
        logger.info(f"\nModels saved: {len(model_files)}/24")
        logger.info(f"Success rate: {success_count}/8 pairs")
        
        return results

# ==================== MAIN ====================

def main():
    """Main entry point"""
    try:
        config = Config()
        
        logger.info("="*80)
        logger.info("B1 ENSEMBLE TRAINING SCRIPT - 105 FEATURES")
        logger.info("Configuration: 24 candles, 10 pips, 102 features")
        logger.info("="*80)
        logger.info(f"Training data: {config.TRAIN_FILE}")
        logger.info(f"Validation data: {config.VAL_FILE}")
        logger.info(f"Output directory: {config.MODEL_DIR}")
        logger.info(f"Number of features: {config.NUM_FEATURES}")
        logger.info(f"PyTorch version: {torch.__version__}")
        logger.info(f"CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            logger.info(f"CUDA device: {torch.cuda.get_device_name(0)}")
        
        trainer = EnsembleTrainer(config)
        trainer.train_all_models()
        
    except KeyboardInterrupt:
        logger.info("\n\nTraining interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\nFatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
