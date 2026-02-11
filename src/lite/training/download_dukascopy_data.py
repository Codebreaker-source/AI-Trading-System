#!/usr/bin/env python3
"""
Download Historical Forex Data from Dukascopy Bank SA
======================================================
Downloads 3 years of M15 OHLCV data for all 8 currency pairs.
Dukascopy provides FREE, high-quality institutional data.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import time

import dukascopy_python
from dukascopy_python.instruments import (
    INSTRUMENT_FX_MAJORS_EUR_USD,
    INSTRUMENT_FX_MAJORS_GBP_USD,
    INSTRUMENT_FX_MAJORS_USD_JPY,
    INSTRUMENT_FX_MAJORS_USD_CHF,
    INSTRUMENT_FX_MAJORS_AUD_USD,
    INSTRUMENT_FX_MAJORS_USD_CAD,
    INSTRUMENT_FX_MAJORS_NZD_USD,
    INSTRUMENT_FX_CROSSES_EUR_GBP,
)

# ============================================================================
# CONFIGURATION
# ============================================================================
BASE_DIR = Path(r"C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System")
OUTPUT_DIR = BASE_DIR / "historical_data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Symbols mapping (our naming -> Dukascopy instrument)
SYMBOLS = {
    'EURUSD': INSTRUMENT_FX_MAJORS_EUR_USD,
    'GBPUSD': INSTRUMENT_FX_MAJORS_GBP_USD,
    'USDJPY': INSTRUMENT_FX_MAJORS_USD_JPY,
    'USDCHF': INSTRUMENT_FX_MAJORS_USD_CHF,
    'AUDUSD': INSTRUMENT_FX_MAJORS_AUD_USD,
    'USDCAD': INSTRUMENT_FX_MAJORS_USD_CAD,
    'NZDUSD': INSTRUMENT_FX_MAJORS_NZD_USD,
    'EURGBP': INSTRUMENT_FX_CROSSES_EUR_GBP,
}

# Date range - 3 years of data
END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=3*365)  # 3 years back

print("=" * 70)
print("DUKASCOPY HISTORICAL DATA DOWNLOADER")
print("=" * 70)
print(f"Output directory: {OUTPUT_DIR}")
print(f"Date range: {START_DATE.strftime('%Y-%m-%d')} to {END_DATE.strftime('%Y-%m-%d')}")
print(f"Timeframe: M15")
print(f"Symbols: {list(SYMBOLS.keys())}")
print("=" * 70)


def download_symbol(symbol_name, instrument):
    """Download M15 data for a single symbol"""
    print(f"\n[{symbol_name}] Downloading...")
    
    try:
        # Fetch data from Dukascopy using correct API
        df = dukascopy_python.fetch(
            instrument=instrument,
            interval=dukascopy_python.INTERVAL_MIN_15,
            offer_side=dukascopy_python.OFFER_SIDE_BID,
            start=START_DATE,
            end=END_DATE,
        )
        
        if df is None or len(df) == 0:
            print(f"  WARNING: No data returned for {symbol_name}")
            return None
        
        print(f"  Downloaded {len(df):,} candles")
        
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
        df['symbol'] = symbol_name
        
        # Reorder columns
        cols = ['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'tick_volume']
        available_cols = [c for c in cols if c in df.columns]
        df = df[available_cols]
        
        # Save to CSV
        output_file = OUTPUT_DIR / f"{symbol_name}_M15_dukascopy.csv"
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
    """Download all symbols"""
    all_data = {}
    
    for symbol_name, instrument in SYMBOLS.items():
        df = download_symbol(symbol_name, instrument)
        if df is not None:
            all_data[symbol_name] = df
        
        # Small delay to be nice to Dukascopy servers
        time.sleep(2)
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "=" * 70)
    print("DOWNLOAD SUMMARY")
    print("=" * 70)
    
    total_candles = 0
    for symbol, df in all_data.items():
        candles = len(df)
        total_candles += candles
        days = candles * 15 / 60 / 24  # Convert M15 candles to days
        print(f"  {symbol}: {candles:,} candles (~{days:.0f} days)")
    
    print("-" * 70)
    print(f"  TOTAL: {total_candles:,} candles across {len(all_data)} symbols")
    print(f"  Files saved to: {OUTPUT_DIR}")
    
    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print("""
1. Run feature extraction on downloaded data
2. Label the data
3. Split into train/val/test
4. Retrain all models (XGBoost, LightGBM, CatBoost)
""")


if __name__ == "__main__":
    main()
