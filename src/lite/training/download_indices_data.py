#!/usr/bin/env python3
"""
Download Historical Index Data for Asset Expansion
===================================================
Downloads 3 years of data for US indices:
- USA30 (Dow Jones) - Dukascopy M15
- USA500 (S&P 500) - Dukascopy M15  
- NAS100 (NASDAQ 100) - yfinance H1 (Dukascopy doesn't have it)
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import time
import warnings
warnings.filterwarnings('ignore')

import dukascopy_python
import yfinance as yf

# ============================================================================
# CONFIGURATION
# ============================================================================
BASE_DIR = Path(r"C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System")
OUTPUT_DIR = BASE_DIR / "historical_data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Date range - 3 years of data
END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=3*365)  # 3 years back

print("=" * 70)
print("INDEX HISTORICAL DATA DOWNLOADER")
print("=" * 70)
print(f"Output directory: {OUTPUT_DIR}")
print(f"Date range: {START_DATE.strftime('%Y-%m-%d')} to {END_DATE.strftime('%Y-%m-%d')}")
print("=" * 70)


def download_dukascopy_index(symbol_name, dukascopy_symbol, output_name):
    """Download M15 data from Dukascopy for an index"""
    print(f"\n{'='*70}")
    print(f"[{symbol_name}] Downloading from Dukascopy...")
    print(f"  Dukascopy symbol: {dukascopy_symbol}")
    print(f"  Timeframe: M15")
    print(f"{'='*70}")
    
    try:
        # Download in chunks to avoid timeout (1 year at a time)
        all_data = []
        
        chunk_start = START_DATE
        chunk_size = timedelta(days=365)  # 1 year chunks
        chunk_num = 0
        
        while chunk_start < END_DATE:
            chunk_num += 1
            chunk_end = min(chunk_start + chunk_size, END_DATE)
            
            print(f"  Chunk {chunk_num}: {chunk_start.strftime('%Y-%m-%d')} to {chunk_end.strftime('%Y-%m-%d')}...")
            
            df = dukascopy_python.fetch(
                instrument=dukascopy_symbol,
                interval=dukascopy_python.INTERVAL_MIN_15,
                offer_side=dukascopy_python.OFFER_SIDE_BID,
                start=chunk_start,
                end=chunk_end,
            )
            
            if df is not None and len(df) > 0:
                print(f"    Downloaded {len(df):,} candles")
                all_data.append(df)
            else:
                print(f"    WARNING: No data for this chunk")
            
            chunk_start = chunk_end
            time.sleep(2)  # Be nice to Dukascopy servers
        
        if not all_data:
            print(f"  ERROR: No data downloaded for {symbol_name}")
            return None
        
        # Combine all chunks
        df = pd.concat(all_data)
        df = df.sort_index()
        df = df[~df.index.duplicated(keep='first')]  # Remove duplicates
        
        print(f"\n  Total: {len(df):,} candles")
        
        # Reset index to get timestamp as column
        df = df.reset_index()
        
        # Rename columns to match our format
        df = df.rename(columns={
            'index': 'timestamp',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'tick_volume'
        })
        
        # Add symbol column
        df['symbol'] = output_name
        
        # Reorder columns
        cols = ['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'tick_volume']
        available_cols = [c for c in cols if c in df.columns]
        df = df[available_cols]
        
        # Save to CSV
        output_file = OUTPUT_DIR / f"{output_name}_M15_dukascopy.csv"
        df.to_csv(output_file, index=False)
        
        # Print stats
        print(f"  Period: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print(f"  Saved: {output_file.name} ({output_file.stat().st_size / 1024 / 1024:.1f} MB)")
        
        return df
        
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


def download_yfinance_index(symbol_name, yf_symbol, output_name):
    """Download H1 data from yfinance for an index"""
    print(f"\n{'='*70}")
    print(f"[{symbol_name}] Downloading from yfinance...")
    print(f"  yfinance symbol: {yf_symbol}")
    print(f"  Timeframe: H1 (max available ~2 years)")
    print(f"{'='*70}")
    
    try:
        # yfinance only provides ~730 days of hourly data
        df = yf.download(
            yf_symbol,
            period='max',
            interval='1h',
            progress=True
        )
        
        if df is None or len(df) == 0:
            print(f"  ERROR: No data returned for {symbol_name}")
            return None
        
        print(f"\n  Downloaded {len(df):,} candles")
        
        # Reset index
        df = df.reset_index()
        
        # Handle multi-level columns from yfinance
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] if col[1] == '' else col[0] for col in df.columns]
        
        # Rename columns to match our format
        df = df.rename(columns={
            'Datetime': 'timestamp',
            'Date': 'timestamp',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'tick_volume'
        })
        
        # Add symbol column
        df['symbol'] = output_name
        
        # Reorder columns
        cols = ['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'tick_volume']
        available_cols = [c for c in cols if c in df.columns]
        df = df[available_cols]
        
        # Save to CSV
        output_file = OUTPUT_DIR / f"{output_name}_H1_yfinance.csv"
        df.to_csv(output_file, index=False)
        
        # Print stats
        print(f"  Period: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print(f"  Saved: {output_file.name} ({output_file.stat().st_size / 1024 / 1024:.1f} MB)")
        
        return df
        
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Download all index data"""
    all_data = {}
    
    # ========================================================================
    # DUKASCOPY DOWNLOADS (M15)
    # ========================================================================
    
    # USA30 (Dow Jones)
    df = download_dukascopy_index(
        symbol_name="US30 (Dow Jones)",
        dukascopy_symbol="USA30.IDX/USD",
        output_name="US30"
    )
    if df is not None:
        all_data['US30'] = df
    
    time.sleep(3)
    
    # USA500 (S&P 500)
    df = download_dukascopy_index(
        symbol_name="US500 (S&P 500)",
        dukascopy_symbol="USA500.IDX/USD",
        output_name="US500"
    )
    if df is not None:
        all_data['US500'] = df
    
    time.sleep(3)
    
    # ========================================================================
    # YFINANCE DOWNLOAD (H1)
    # ========================================================================
    
    # NAS100 (NASDAQ 100)
    df = download_yfinance_index(
        symbol_name="NAS100 (NASDAQ 100)",
        yf_symbol="^NDX",
        output_name="NAS100"
    )
    if df is not None:
        all_data['NAS100'] = df
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "=" * 70)
    print("DOWNLOAD SUMMARY")
    print("=" * 70)
    
    for symbol, df in all_data.items():
        candles = len(df)
        first_date = df['timestamp'].min()
        last_date = df['timestamp'].max()
        print(f"  {symbol}: {candles:,} candles ({first_date} to {last_date})")
    
    print("-" * 70)
    print(f"  Files saved to: {OUTPUT_DIR}")
    
    print("\n" + "=" * 70)
    print("DATA SOURCES")
    print("=" * 70)
    print("  US30:   Dukascopy M15 (3 years)")
    print("  US500:  Dukascopy M15 (3 years)")
    print("  NAS100: yfinance H1 (~2 years)")
    
    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print("""
1. Run feature extraction on downloaded data
2. Label the data for training
3. Split into train/val/test
4. Train models for each index (XGBoost, LightGBM)
5. Integrate into live trading system
""")
    
    return all_data


if __name__ == "__main__":
    main()
