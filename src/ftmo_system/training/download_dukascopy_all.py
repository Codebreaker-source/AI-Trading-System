"""
Dukascopy Historical Data Downloader — All FTMO Symbols
=========================================================
Downloads 3 years of M15 OHLCV data for every FTMO symbol that has a
matching Dukascopy instrument (forex majors/crosses, metals, indices,
crypto, energy). Free institutional-quality data from Dukascopy Bank SA.

Output: data/historical_data/{SYMBOL}_M15_dukascopy.csv
  columns: timestamp, symbol, open, high, low, close, tick_volume

Run: python training/download_dukascopy_all.py
"""

from __future__ import annotations

import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

import dukascopy_python
from dukascopy_python import instruments as I

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "data" / "historical_data"

# Symbol (FTMO name, suffix-stripped) -> Dukascopy instrument constant
SYMBOL_INSTRUMENTS = {
    # 8 majors (already pretrained, included for completeness/refresh)
    "EURUSD": I.INSTRUMENT_FX_MAJORS_EUR_USD,
    "GBPUSD": I.INSTRUMENT_FX_MAJORS_GBP_USD,
    "USDJPY": I.INSTRUMENT_FX_MAJORS_USD_JPY,
    "USDCHF": I.INSTRUMENT_FX_MAJORS_USD_CHF,
    "AUDUSD": I.INSTRUMENT_FX_MAJORS_AUD_USD,
    "USDCAD": I.INSTRUMENT_FX_MAJORS_USD_CAD,
    "NZDUSD": I.INSTRUMENT_FX_MAJORS_NZD_USD,
    "EURGBP": I.INSTRUMENT_FX_CROSSES_EUR_GBP,

    # Forex crosses / exotics
    "AUDCAD": I.INSTRUMENT_FX_CROSSES_AUD_CAD,
    "AUDCHF": I.INSTRUMENT_FX_CROSSES_AUD_CHF,
    "AUDJPY": I.INSTRUMENT_FX_CROSSES_AUD_JPY,
    "AUDNZD": I.INSTRUMENT_FX_CROSSES_AUD_NZD,
    "CADCHF": I.INSTRUMENT_FX_CROSSES_CAD_CHF,
    "CADJPY": I.INSTRUMENT_FX_CROSSES_CAD_JPY,
    "CHFJPY": I.INSTRUMENT_FX_CROSSES_CHF_JPY,
    "EURAUD": I.INSTRUMENT_FX_CROSSES_EUR_AUD,
    "EURCAD": I.INSTRUMENT_FX_CROSSES_EUR_CAD,
    "EURCHF": I.INSTRUMENT_FX_CROSSES_EUR_CHF,
    "EURCZK": I.INSTRUMENT_FX_CROSSES_EUR_CZK,
    "EURHUF": I.INSTRUMENT_FX_CROSSES_EUR_HUF,
    "EURNOK": I.INSTRUMENT_FX_CROSSES_EUR_NOK,
    "EURNZD": I.INSTRUMENT_FX_CROSSES_EUR_NZD,
    "EURPLN": I.INSTRUMENT_FX_CROSSES_EUR_PLN,
    "EURSEK": I.INSTRUMENT_FX_CROSSES_EUR_SEK,
    "GBPAUD": I.INSTRUMENT_FX_CROSSES_GBP_AUD,
    "NZDCAD": I.INSTRUMENT_FX_CROSSES_NZD_CAD,
    "NZDCHF": I.INSTRUMENT_FX_CROSSES_NZD_CHF,
    "USDCNH": I.INSTRUMENT_FX_CROSSES_USD_CNH,
    "USDCZK": I.INSTRUMENT_FX_CROSSES_USD_CZK,
    "USDHUF": I.INSTRUMENT_FX_CROSSES_USD_HUF,
    "USDMXN": I.INSTRUMENT_FX_CROSSES_USD_MXN,
    "USDNOK": I.INSTRUMENT_FX_CROSSES_USD_NOK,
    "USDPLN": I.INSTRUMENT_FX_CROSSES_USD_PLN,
    "USDSEK": I.INSTRUMENT_FX_CROSSES_USD_SEK,
    "USDSGD": I.INSTRUMENT_FX_CROSSES_USD_SGD,
    "USDZAR": I.INSTRUMENT_FX_CROSSES_USD_ZAR,

    # Metals
    "XAUUSD": I.INSTRUMENT_FX_METALS_XAU_USD,
    "XAGUSD": I.INSTRUMENT_FX_METALS_XAG_USD,

    # Indices
    "US100": I.INSTRUMENT_IDX_AMERICA_E_NQ_100,
    "US30": I.INSTRUMENT_IDX_AMERICA_E_D_J_IND,
    "US500": I.INSTRUMENT_IDX_AMERICA_E_SANDP_500,

    # Crypto
    "BTCUSD": I.INSTRUMENT_VCCY_BTC_USD,

    # Energy
    "USOIL": I.INSTRUMENT_CMD_ENERGY_E_LIGHT,
}

END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=3 * 365)


def download_symbol(symbol_name: str, instrument) -> pd.DataFrame | None:
    logger.info(f"[{symbol_name}] downloading...")
    try:
        df = dukascopy_python.fetch(
            instrument=instrument,
            interval=dukascopy_python.INTERVAL_MIN_15,
            offer_side=dukascopy_python.OFFER_SIDE_BID,
            start=START_DATE,
            end=END_DATE,
        )
    except Exception as e:
        logger.error(f"[{symbol_name}] fetch failed: {e}")
        return None

    if df is None or len(df) == 0:
        logger.warning(f"[{symbol_name}] no data returned")
        return None

    df = df.reset_index()
    df = df.rename(columns={"index": "timestamp", "volume": "tick_volume"})
    df["symbol"] = symbol_name
    cols = ["timestamp", "symbol", "open", "high", "low", "close", "tick_volume"]
    df = df[[c for c in cols if c in df.columns]]

    out_path = OUTPUT_DIR / f"{symbol_name}_M15_dukascopy.csv"
    df.to_csv(out_path, index=False)
    return df


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Downloading {len(SYMBOL_INSTRUMENTS)} symbols, {START_DATE.date()} -> {END_DATE.date()}, M15")

    summary = []
    for symbol, instrument in SYMBOL_INSTRUMENTS.items():
        df = download_symbol(symbol, instrument)
        if df is not None:
            span_days = (df["timestamp"].max() - df["timestamp"].min()).days
            summary.append((symbol, len(df), df["timestamp"].min(), df["timestamp"].max(), span_days))
        else:
            summary.append((symbol, 0, None, None, 0))
        time.sleep(1)

    logger.info("=" * 70)
    logger.info(f"{'SYMBOL':<10} {'CANDLES':>10} {'SPAN_DAYS':>10}  RANGE")
    for symbol, n, start, end, days in summary:
        if n == 0:
            logger.info(f"{symbol:<10} {'FAILED':>10}")
        else:
            logger.info(f"{symbol:<10} {n:>10,} {days:>10}  {start} -> {end}")

    ok = sum(1 for _, n, *_ in summary if n > 0)
    logger.info(f"=== Downloaded {ok}/{len(summary)} symbols to {OUTPUT_DIR} ===")


if __name__ == "__main__":
    main()
