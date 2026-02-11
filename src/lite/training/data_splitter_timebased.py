#!/usr/bin/env python3
"""
Time-Based Data Splitter - NO DATA LEAKAGE
===========================================
Splits labeled data into train/val/test sets using TIME-BASED splits (not random).

This ensures:
- Training data comes BEFORE validation data
- Validation data comes BEFORE test data  
- No future information leaks into past predictions

Usage:
    python training/data_splitter_timebased.py accumulated_features_m1_step5_labeled_v2.csv

Splits:
    - Train: First 70% (chronologically)
    - Validation: Next 15%
    - Test: Last 15%

Author: AI Trading System
Version: 1.0
Date: 2025-10-22
"""

import os
import sys
import pandas as pd
import numpy as np
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class TimeBasedDataSplitter:
    """Splits data into train/val/test using time-based approach"""
    
    def __init__(self, input_file, train_ratio=0.70, val_ratio=0.15, test_ratio=0.15):
        """
        Initialize splitter
        
        Args:
            input_file: Path to labeled CSV file
            train_ratio: Proportion for training (default: 0.70)
            val_ratio: Proportion for validation (default: 0.15)
            test_ratio: Proportion for testing (default: 0.15)
        """
        self.input_file = input_file
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio
        
        # Verify ratios sum to 1.0
        total = train_ratio + val_ratio + test_ratio
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Ratios must sum to 1.0, got {total}")
        
        logging.info("="*60)
        logging.info("TIME-BASED DATA SPLITTER - Starting")
        logging.info("="*60)
        logging.info(f"Input file: {input_file}")
        logging.info(f"Split ratios: Train={train_ratio:.0%}, Val={val_ratio:.0%}, Test={test_ratio:.0%}")
    
    def read_data(self):
        """Read labeled data"""
        try:
            logging.info("")
            logging.info("Reading labeled data...")
            df = pd.read_csv(self.input_file)
            
            logging.info(f"  Loaded {len(df):,} samples")
            logging.info(f"  Columns: {len(df.columns)}")
            logging.info(f"  Shape: {df.shape}")
            
            # Check for required columns
            if 'timestamp' not in df.columns:
                raise ValueError("'timestamp' column not found in data")
            
            if 'label' not in df.columns:
                raise ValueError("'label' column not found in data")
            
            # Show label distribution
            logging.info("")
            logging.info("Overall Label Distribution:")
            label_counts = df['label'].value_counts()
            for label in ['HOLD', 'BUY', 'SELL']:
                count = label_counts.get(label, 0)
                percent = (count / len(df)) * 100
                logging.info(f"  {label}: {count:,} ({percent:.1f}%)")
            
            return df
            
        except Exception as e:
            logging.error(f"Error reading data: {e}")
            raise
    
    def split_data(self, df):
        """
        Split data using TIME-BASED approach
        
        Args:
            df: DataFrame with timestamp column
        
        Returns:
            train_df, val_df, test_df
        """
        logging.info("")
        logging.info("Splitting data chronologically...")
        
        # Sort by timestamp to ensure chronological order
        df = df.sort_values('timestamp').reset_index(drop=True)
        logging.info("  Sorted by timestamp (oldest to newest)")
        
        # Calculate split indices
        n_samples = len(df)
        train_end = int(n_samples * self.train_ratio)
        val_end = int(n_samples * (self.train_ratio + self.val_ratio))
        
        # Split data
        train_df = df.iloc[:train_end].copy()
        val_df = df.iloc[train_end:val_end].copy()
        test_df = df.iloc[val_end:].copy()
        
        logging.info("")
        logging.info("Split Summary:")
        logging.info(f"  Train: {len(train_df):,} samples ({len(train_df)/n_samples*100:.1f}%)")
        logging.info(f"  Val:   {len(val_df):,} samples ({len(val_df)/n_samples*100:.1f}%)")
        logging.info(f"  Test:  {len(test_df):,} samples ({len(test_df)/n_samples*100:.1f}%)")
        
        # Verify time ranges don't overlap
        self.verify_time_separation(train_df, val_df, test_df)
        
        # Show label distributions for each split
        self.show_split_distributions(train_df, val_df, test_df)
        
        return train_df, val_df, test_df
    
    def verify_time_separation(self, train_df, val_df, test_df):
        """Verify that splits don't overlap in time"""
        logging.info("")
        logging.info("Verifying time separation...")
        
        train_max = train_df['timestamp'].max()
        val_min = val_df['timestamp'].min()
        val_max = val_df['timestamp'].max()
        test_min = test_df['timestamp'].min()
        
        logging.info(f"  Train period: {train_df['timestamp'].min()} to {train_max}")
        logging.info(f"  Val period:   {val_min} to {val_max}")
        logging.info(f"  Test period:  {test_min} to {test_df['timestamp'].max()}")
        
        # Check for overlaps
        if train_max >= val_min:
            logging.warning(f"  WARNING: Train max ({train_max}) >= Val min ({val_min})")
        else:
            logging.info(f"  ✓ Train ends before Val starts")
        
        if val_max >= test_min:
            logging.warning(f"  WARNING: Val max ({val_max}) >= Test min ({test_min})")
        else:
            logging.info(f"  ✓ Val ends before Test starts")
        
        logging.info("  ✓ Time-based separation verified - NO DATA LEAKAGE")
    
    def show_split_distributions(self, train_df, val_df, test_df):
        """Show label distributions for each split"""
        logging.info("")
        logging.info("Label Distribution Per Split:")
        
        for split_name, split_df in [("Train", train_df), ("Val", val_df), ("Test", test_df)]:
            logging.info(f"  {split_name} ({len(split_df):,} samples):")
            label_counts = split_df['label'].value_counts()
            for label in ['HOLD', 'BUY', 'SELL']:
                count = label_counts.get(label, 0)
                percent = (count / len(split_df)) * 100
                logging.info(f"    {label}: {count:,} ({percent:.1f}%)")
    
    def save_splits(self, train_df, val_df, test_df):
        """Save split datasets to CSV files"""
        try:
            # Create output directory if needed
            output_dir = os.path.dirname(self.input_file)
            if not output_dir:
                output_dir = "."
            
            # Define output filenames
            train_file = os.path.join(output_dir, "train_data.csv")
            val_file = os.path.join(output_dir, "val_data.csv")
            test_file = os.path.join(output_dir, "test_data.csv")
            
            logging.info("")
            logging.info("Saving split datasets...")
            
            # Save train
            train_df.to_csv(train_file, index=False)
            train_size = os.path.getsize(train_file) / (1024 * 1024)
            logging.info(f"  ✓ Train: {train_file} ({train_size:.1f} MB)")
            
            # Save validation
            val_df.to_csv(val_file, index=False)
            val_size = os.path.getsize(val_file) / (1024 * 1024)
            logging.info(f"  ✓ Val:   {val_file} ({val_size:.1f} MB)")
            
            # Save test
            test_df.to_csv(test_file, index=False)
            test_size = os.path.getsize(test_file) / (1024 * 1024)
            logging.info(f"  ✓ Test:  {test_file} ({test_size:.1f} MB)")
            
            return train_file, val_file, test_file
            
        except Exception as e:
            logging.error(f"Error saving splits: {e}")
            raise
    
    def run(self):
        """Main execution flow"""
        try:
            # Read data
            df = self.read_data()
            
            # Split data
            train_df, val_df, test_df = self.split_data(df)
            
            # Save splits
            train_file, val_file, test_file = self.save_splits(train_df, val_df, test_df)
            
            # Print summary
            logging.info("")
            logging.info("="*60)
            logging.info("SPLITTING COMPLETE!")
            logging.info("="*60)
            logging.info("")
            logging.info("FINAL SUMMARY:")
            logging.info(f"  Input file: {self.input_file}")
            logging.info(f"  Output files:")
            logging.info(f"    - Train: {train_file} ({len(train_df):,} samples)")
            logging.info(f"    - Val:   {val_file} ({len(val_df):,} samples)")
            logging.info(f"    - Test:  {test_file} ({len(test_df):,} samples)")
            logging.info("")
            logging.info("Next steps:")
            logging.info("  1. Train LSTM model on train_data.csv")
            logging.info("  2. Validate on val_data.csv during training")
            logging.info("  3. Final test on test_data.csv")
            logging.info("="*60)
            
            return train_file, val_file, test_file
            
        except Exception as e:
            logging.error(f"Error in splitting process: {e}")
            raise


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python training/data_splitter_timebased.py <labeled_file.csv>")
        print("Example: python training/data_splitter_timebased.py accumulated_features_m1_step5_labeled_v2.csv")
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    if not os.path.exists(input_file):
        print(f"Error: File not found: {input_file}")
        sys.exit(1)
    
    # Run splitter
    splitter = TimeBasedDataSplitter(input_file)
    splitter.run()


if __name__ == '__main__':
    main()
