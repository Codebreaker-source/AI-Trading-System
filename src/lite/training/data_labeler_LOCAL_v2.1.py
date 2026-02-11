#!/usr/bin/env python3
"""
Data Labeler LOCAL Version 2.1 - MULTI-CONFIG WITH CLI ARGS
============================================================
ENHANCEMENTS FROM v2.0:
- Command-line argument support for different labeling configs
- Custom output filename based on parameters
- Memory-safe chunked processing (5GB RAM compatible)
- Backward compatible (no args = use config file)

NEW FEATURES:
- --lookforward_candles: Override config value (e.g., 24, 48)
- --profit_threshold_pips: Override config value (e.g., 10, 15, 20)
- --chunk_size: Memory control (default 50000)

Usage Examples:
    # Use config file settings:
    python data_labeler_LOCAL_v2.1.py accumulated_features_m5_chunked.csv
    
    # Custom settings for different timeframes:
    python data_labeler_LOCAL_v2.1.py accumulated_features_m5_chunked.csv \
        --lookforward_candles 48 --profit_threshold_pips 15
    
    python data_labeler_LOCAL_v2.1.py accumulated_features_m5_chunked.csv \
        --lookforward_candles 24 --profit_threshold_pips 10

Author: AI Trading System
Date: 2025-10-24
Version: 2.1
"""

import os
import sys
import json
import logging
import argparse
import pandas as pd
import numpy as np
import gc

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class DataLabelerLocalV21:
    """Labels training data with configurable parameters - MEMORY SAFE"""
    
    def __init__(self, config_path='../config/trading_config.json', local_file=None, 
                 chunk_size=25000, lookforward_candles=None, profit_threshold_pips=None):
        """
        Initialize labeler with configuration
        
        Args:
            config_path: Path to trading config file
            local_file: Input CSV file path
            chunk_size: Rows per chunk for memory-safe processing
            lookforward_candles: Override config value (optional)
            profit_threshold_pips: Override config value (optional)
        """
        
        logging.info("="*60)
        logging.info("DATA LABELER LOCAL v2.1 - MULTI-CONFIG")
        logging.info("="*60)
        
        # Chunk size for memory-efficient processing
        self.chunk_size = chunk_size
        logging.info(f"Chunk size: {chunk_size:,} rows per chunk (5GB RAM safe - reduced from 50K)")
        
        # Load configuration
        if not os.path.exists(config_path):
            # Try relative path from training directory
            alt_config_path = 'config/trading_config.json'
            if os.path.exists(alt_config_path):
                config_path = alt_config_path
            else:
                raise FileNotFoundError(f"Config file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        # Set local file
        self.local_file = local_file
        if not local_file:
            raise ValueError("Must provide local file path as argument")
        
        if not os.path.exists(local_file):
            raise FileNotFoundError(f"File not found: {local_file}")
        
        # Labeling parameters - use CLI args if provided, else config
        labeling_config = self.config['labeling_strategy']
        
        if lookforward_candles is not None:
            self.forward_window = lookforward_candles
            logging.info(f"Using CLI argument: lookforward_candles={lookforward_candles}")
        else:
            self.forward_window = labeling_config['forward_window_candles']
            logging.info(f"Using config file: lookforward_candles={self.forward_window}")
        
        if profit_threshold_pips is not None:
            self.profit_threshold = profit_threshold_pips
            self.loss_threshold = profit_threshold_pips
            logging.info(f"Using CLI argument: profit_threshold_pips={profit_threshold_pips}")
        else:
            self.profit_threshold = labeling_config['profit_threshold_pips']
            self.loss_threshold = labeling_config['loss_threshold_pips']
            logging.info(f"Using config file: profit_threshold_pips={self.profit_threshold}")
        
        # All possible symbols in the dataset
        self.all_symbols = ['EURUSD.sim', 'GBPUSD.sim', 'USDJPY.sim', 'AUDUSD.sim', 
                           'USDCAD.sim', 'NZDUSD.sim', 'USDCHF.sim', 'EURGBP.sim']
        
        logging.info("")
        logging.info(f"Input file: {local_file}")
        logging.info(f"Forward window: {self.forward_window} candles")
        logging.info(f"Profit threshold: {self.profit_threshold} pips")
        logging.info(f"Loss threshold: {self.loss_threshold} pips")
    
    def calculate_pip_value(self, symbol):
        """Calculate pip value for a symbol"""
        # JPY pairs: 1 pip = 0.01
        # Other pairs: 1 pip = 0.0001
        if 'JPY' in symbol:
            return 0.01
        else:
            return 0.0001
    
    def label_sample(self, current_price, future_prices, symbol):
        """
        Label a single sample based on forward price movement
        
        Args:
            current_price: Current close price
            future_prices: Array of future close prices
            symbol: Trading symbol
        
        Returns:
            str: 'BUY', 'SELL', or 'HOLD'
        """
        if len(future_prices) == 0:
            return 'HOLD'
        
        pip_value = self.calculate_pip_value(symbol)
        
        # Calculate price changes in pips
        price_changes = (future_prices - current_price) / pip_value
        
        max_gain = np.max(price_changes)
        max_loss = np.min(price_changes)
        
        # Labeling logic
        if max_gain >= self.profit_threshold and abs(max_loss) < self.loss_threshold:
            return 'BUY'
        elif abs(max_loss) >= self.loss_threshold and max_gain < self.profit_threshold:
            return 'SELL'
        else:
            return 'HOLD'
    
    def generate_output_filename(self):
        """Generate output filename based on parameters"""
        input_basename = os.path.basename(self.local_file)
        base = input_basename.replace('.csv', '')
        
        # Create descriptive suffix
        suffix = f"_labeled_{self.forward_window}c_{self.profit_threshold}p.csv"
        
        return base + suffix
    
    def run(self):
        """Main execution flow - Dense format processing"""
        try:
            output_file = self.generate_output_filename()
            
            logging.info("")
            logging.info("="*60)
            logging.info("DENSE FORMAT LABELING (MEMORY-SAFE)")
            logging.info("="*60)
            logging.info(f"Output file: {output_file}")
            logging.info("")
            
            # Read and process in chunks
            chunk_iterator = pd.read_csv(self.local_file, chunksize=self.chunk_size)
            
            first_output = True
            total_input_rows = 0
            total_output_samples = 0
            chunk_num = 0
            
            for chunk_df in chunk_iterator:
                chunk_num += 1
                chunk_size = len(chunk_df)
                total_input_rows += chunk_size
                
                logging.info(f"\nProcessing chunk {chunk_num} ({chunk_size:,} rows)...")
                
                # Expand dense format to one row per pair
                output_rows = []
                
                for idx, row in chunk_df.iterrows():
                    for symbol in self.all_symbols:
                        pair_data = {'timestamp': row['timestamp'], 'symbol': symbol}
                        
                        # Extract all features for this pair
                        for col in chunk_df.columns:
                            if col.startswith(symbol):
                                clean_col = col.replace(f'{symbol}_', '')
                                pair_data[clean_col] = row[col]
                        
                        # Validate this pair's data
                        close_col = f'{symbol}_close'
                        high_col = f'{symbol}_high'
                        low_col = f'{symbol}_low'
                        
                        is_valid = True
                        
                        if close_col not in row.index or pd.isna(row[close_col]) or row[close_col] <= 0:
                            is_valid = False
                        elif high_col not in row.index or pd.isna(row[high_col]) or row[high_col] <= 0:
                            is_valid = False
                        elif low_col not in row.index or pd.isna(row[low_col]) or row[low_col] <= 0:
                            is_valid = False
                        elif not (row[low_col] <= row[close_col] <= row[high_col]):
                            is_valid = False
                        
                        if is_valid:
                            output_rows.append(pair_data)
                
                logging.info(f"  Extracted {len(output_rows):,} valid samples")
                
                # Convert to dataframe
                chunk_output = pd.DataFrame(output_rows)
                chunk_output = chunk_output.sort_values(['symbol', 'timestamp']).reset_index(drop=True)
                chunk_output['label'] = 'HOLD'
                
                # Label each pair in this chunk
                logging.info("  Labeling samples...")
                labeled_count = 0
                
                for symbol in self.all_symbols:
                    symbol_mask = chunk_output['symbol'] == symbol
                    symbol_df = chunk_output[symbol_mask]
                    symbol_indices = symbol_df.index.tolist()
                    
                    if len(symbol_indices) == 0:
                        continue
                    
                    for i, idx in enumerate(symbol_indices):
                        if i >= len(symbol_indices) - self.forward_window:
                            continue
                        
                        current_price = chunk_output.loc[idx, 'close']
                        future_indices = symbol_indices[i+1:i+1+self.forward_window]
                        
                        if len(future_indices) >= self.forward_window:
                            future_prices = chunk_output.loc[future_indices, 'close'].values
                            label = self.label_sample(current_price, future_prices, symbol)
                            chunk_output.loc[idx, 'label'] = label
                            labeled_count += 1
                
                logging.info(f"  Labeled {labeled_count:,} samples")
                
                # Write to output file
                if first_output:
                    chunk_output.to_csv(output_file, index=False, mode='w')
                    first_output = False
                else:
                    chunk_output.to_csv(output_file, index=False, mode='a', header=False)
                
                total_output_samples += len(chunk_output)
                
                # Force garbage collection to free memory
                del chunk_df, chunk_output, output_rows
                gc.collect()
                
                logging.info(f"  Cumulative: {total_output_samples:,} samples")
            
            logging.info("")
            logging.info("="*60)
            logging.info("DATA LABELING COMPLETE!")
            logging.info("="*60)
            logging.info(f"Output file: {output_file}")
            logging.info(f"Total samples: {total_output_samples:,}")
            
            # Calculate final statistics
            logging.info("")
            logging.info("Calculating final statistics...")
            
            # Read in chunks to avoid memory issues
            hold_count = 0
            buy_count = 0
            sell_count = 0
            total_count = 0
            
            for stats_chunk in pd.read_csv(output_file, chunksize=50000):
                label_counts = stats_chunk['label'].value_counts()
                hold_count += label_counts.get('HOLD', 0)
                buy_count += label_counts.get('BUY', 0)
                sell_count += label_counts.get('SELL', 0)
                total_count += len(stats_chunk)
            
            logging.info("")
            logging.info("Label Distribution:")
            logging.info(f"  HOLD: {hold_count:,} ({hold_count/total_count*100:.1f}%)")
            logging.info(f"  BUY:  {buy_count:,} ({buy_count/total_count*100:.1f}%)")
            logging.info(f"  SELL: {sell_count:,} ({sell_count/total_count*100:.1f}%)")
            
            file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
            logging.info(f"\nOutput file size: {file_size_mb:.1f} MB")
            
            logging.info("")
            logging.info("="*60)
            
            return True
            
        except Exception as e:
            logging.error(f"Error during labeling: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Parse arguments and run labeler"""
    parser = argparse.ArgumentParser(
        description='Label trading data with configurable timeframes and thresholds'
    )
    
    parser.add_argument(
        'input_file',
        help='Input CSV file path'
    )
    
    parser.add_argument(
        '--lookforward_candles',
        type=int,
        default=None,
        help='Number of candles to look forward (e.g., 24, 48). Overrides config file.'
    )
    
    parser.add_argument(
        '--profit_threshold_pips',
        type=int,
        default=None,
        help='Pip threshold for BUY/SELL labels (e.g., 10, 15, 20). Overrides config file.'
    )
    
    parser.add_argument(
        '--chunk_size',
        type=int,
        default=25000,
        help='Rows per chunk for memory-safe processing (default: 25000)'
    )
    
    args = parser.parse_args()
    
    # Create labeler with arguments
    labeler = DataLabelerLocalV21(
        local_file=args.input_file,
        chunk_size=args.chunk_size,
        lookforward_candles=args.lookforward_candles,
        profit_threshold_pips=args.profit_threshold_pips
    )
    
    success = labeler.run()
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
