"""
Convert String Labels to Numeric Format for Training - FIXED VERSION
====================================================================
Converts labeler output (string labels) to proper numeric labels

CRITICAL MAPPING (CORRECTED):
    0 = SELL
    1 = HOLD
    2 = BUY

Usage: python training/convert_labels_to_numeric_FIXED.py training/train_data_24c_10p.csv
"""

import pandas as pd
import sys
import os
from datetime import datetime

# CRITICAL FIX: Correct label mapping
LABEL_MAPPING = {
    'SELL': 0,
    'HOLD': 1,
    'BUY': 2
}

def convert_labels(input_file):
    """Convert string labels to numeric format with CORRECT mapping"""
    print(f"\n{'='*80}")
    print(f"LABEL CONVERTER - String to Numeric (FIXED VERSION)")
    print(f"{'='*80}")
    print(f"Input file: {input_file}")
    
    if not os.path.exists(input_file):
        print(f"ERROR: File not found: {input_file}")
        return False
    
    print(f"\nReading data...")
    df = pd.read_csv(input_file)
    total_samples = len(df)
    print(f"Total samples: {total_samples:,}")
    
    # Check if labels are already numeric
    if df['label'].dtype in ['int64', 'int32', 'float64']:
        print("\nLabels are already numeric!")
        print(f"Current distribution:")
        for value, count in df['label'].value_counts().sort_index().items():
            if int(value) < 3:
                label_name = ['SELL', 'HOLD', 'BUY'][int(value)]
            else:
                label_name = 'UNKNOWN'
            pct = count/total_samples*100
            print(f"  {int(value)} ({label_name}): {count:,} ({pct:.2f}%)")
        return True
    
    # Show current distribution (strings)
    print(f"\nCurrent label distribution (STRING):")
    for label, count in df['label'].value_counts().items():
        pct = count/total_samples*100
        print(f"  {label}: {count:,} ({pct:.2f}%)")
    
    # Convert to numeric
    print(f"\n{'='*80}")
    print(f"Converting labels using CORRECTED mapping:")
    print(f"{'='*80}")
    for string_label, numeric_value in LABEL_MAPPING.items():
        print(f"  '{string_label}' -> {numeric_value}")
    print(f"{'='*80}\n")
    
    df['label'] = df['label'].map(LABEL_MAPPING)
    
    # Check for unmapped labels
    if df['label'].isna().any():
        unmapped_count = df['label'].isna().sum()
        print(f"WARNING: {unmapped_count} labels could not be mapped!")
        return False
    
    # Show new distribution (numeric)
    print(f"New label distribution (NUMERIC - CORRECTED):")
    for value, count in df['label'].value_counts().sort_index().items():
        label_name = ['SELL', 'HOLD', 'BUY'][int(value)]
        pct = count/total_samples*100
        print(f"  {int(value)} ({label_name}): {count:,} ({pct:.2f}%)")
    
    # Create output filename
    base_name = os.path.basename(input_file)
    dir_name = os.path.dirname(input_file)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(dir_name, base_name.replace('.csv', f'_FIXED_{timestamp}.csv'))
    
    print(f"\nSaving converted file...")
    df.to_csv(output_file, index=False)
    
    input_size = os.path.getsize(input_file) / (1024**2)
    output_size = os.path.getsize(output_file) / (1024**2)
    
    print(f"Saved: {output_file}")
    print(f"Input size:  {input_size:.2f} MB")
    print(f"Output size: {output_size:.2f} MB")
    
    print(f"\n{'='*80}")
    print(f"CONVERSION COMPLETE!")
    print(f"{'='*80}")
    
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python convert_labels_to_numeric_FIXED.py <input_file.csv>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    success = convert_labels(input_file)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
