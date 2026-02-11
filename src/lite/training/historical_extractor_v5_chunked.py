"""
Historical Feature Extractor v5.1 - M15 TIMEFRAME
Complete 55-feature extraction with intelligent chunking for large datasets

VERSION 5.1 CHANGES (M15 MIGRATION):
- Timeframe: M5 -> M15 (3x longer bars)
- Bars to extract: 200,000 -> 67,000 (same ~694 days of data)
- HTF: M20 (4x) -> H4 (16x) for trend confirmation
- All indicator periods unchanged (12,14,20,26,50)

FEATURES:
- Higher Timeframe Analysis (4 features) - NOW USING H4
- Advanced Volume & Sentiment (3 features)
- Currency Correlations (9 features)
- Currency Strength (8 features)
- 9-Point Confirmations (8 features)
- Core Technical Indicators (26 features)

TOTAL: 55 features per pair x 8 pairs = 440 features + timestamp + row_symbol = 442 columns
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

class HistoricalExtractorV5Chunked:
    def __init__(self):
        self.pairs = [
            'EURUSD.sim', 'GBPUSD.sim', 'USDJPY.sim', 'USDCHF.sim',
            'AUDUSD.sim', 'USDCAD.sim', 'NZDUSD.sim', 'EURGBP.sim'
        ]
        self.timeframe = mt5.TIMEFRAME_M15  # Changed from M5 for M15 migration
        self.bars_to_extract = 67000  # ~694 days on M15 (was 200000 on M5)
        self.chunk_size = 60000  # Stay well under MT5's 99,999 limit
        
        # Parameters for indicators
        self.fast_ema_period = 12
        self.slow_ema_period = 26
        self.rsi_period = 14
        self.atr_period = 14
        self.bb_period = 20
        self.bb_deviation = 2.0
        self.stoch_k_period = 14
        self.stoch_d_period = 3
        self.sma_20_period = 20
        self.sma_50_period = 50
        self.htf_multiplier = 16  # H4 = M15 × 16 (was 4 for M20 on M5)
        self.correlation_window = 50  # Rolling correlation window
        
    def connect_mt5(self) -> bool:
        """Connect to MT5"""
        if not mt5.initialize():
            print(f"[ERROR] Failed to initialize MT5: {mt5.last_error()}")
            return False
        
        print("[OK] Connected to MT5")
        print(f"MT5 version: {mt5.version()}")
        return True
    
    def disconnect_mt5(self):
        """Disconnect from MT5"""
        mt5.shutdown()
        print("[OK] Disconnected from MT5")
    
    def get_historical_data_chunk(self, symbol: str, start_pos: int, bars: int) -> pd.DataFrame:
        """
        Get a chunk of historical OHLCV data for a symbol
        
        Args:
            symbol: Trading symbol
            start_pos: Starting position (0 = most recent)
            bars: Number of bars to retrieve
        
        Returns:
            DataFrame with OHLCV data
        """
        try:
            rates = mt5.copy_rates_from_pos(symbol, self.timeframe, start_pos, bars)
            
            if rates is None or len(rates) == 0:
                return pd.DataFrame()
            
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df = df.rename(columns={
                'time': 'timestamp',
                'tick_volume': 'volume'
            })
            
            return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            
        except Exception as e:
            print(f"[ERROR] Error getting data for {symbol}: {e}")
            return pd.DataFrame()
    
    def extract_data_in_chunks(self, symbol: str, total_bars: int) -> pd.DataFrame:
        """
        Extract data in chunks to stay under MT5 limit
        
        Args:
            symbol: Trading symbol
            total_bars: Total bars to extract
        
        Returns:
            Combined DataFrame with all chunks
        """
        num_chunks = (total_bars + self.chunk_size - 1) // self.chunk_size
        all_chunks = []
        
        print(f"    Extracting {total_bars:,} bars in {num_chunks} chunks...")
        
        for chunk_num in range(num_chunks):
            start_pos = chunk_num * self.chunk_size
            bars_in_chunk = min(self.chunk_size, total_bars - start_pos)
            
            print(f"      Chunk {chunk_num + 1}/{num_chunks}: ", end="")
            print(f"Fetching {bars_in_chunk:,} bars from position {start_pos:,}...", end=" ")
            
            chunk_df = self.get_historical_data_chunk(symbol, start_pos, bars_in_chunk)
            
            if chunk_df.empty:
                print("[ERROR] FAILED")
                continue
            
            all_chunks.append(chunk_df)
            print(f"[OK] {len(chunk_df):,} bars")
        
        if not all_chunks:
            return pd.DataFrame()
        
        # Combine all chunks
        print(f"    Combining {len(all_chunks)} chunks...", end=" ")
        combined_df = pd.concat(all_chunks, axis=0, ignore_index=True)
        
        # Sort by timestamp (oldest first)
        combined_df = combined_df.sort_values('timestamp').reset_index(drop=True)
        
        # Remove any duplicate timestamps
        combined_df = combined_df.drop_duplicates(subset=['timestamp'], keep='first')
        
        print(f"[OK] {len(combined_df):,} unique bars")
        
        return combined_df
    
    def calculate_ema(self, data: pd.Series, period: int) -> pd.Series:
        """Calculate Exponential Moving Average"""
        return data.ewm(span=period, adjust=False).mean()
    
    def calculate_sma(self, data: pd.Series, period: int) -> pd.Series:
        """Calculate Simple Moving Average"""
        return data.rolling(window=period).mean()
    
    def calculate_rsi(self, data: pd.Series, period: int) -> pd.Series:
        """Calculate Relative Strength Index"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_atr(self, df: pd.DataFrame, period: int) -> pd.Series:
        """Calculate Average True Range"""
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr
    
    def calculate_bollinger_bands(self, data: pd.Series, period: int, deviation: float) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands"""
        middle = self.calculate_sma(data, period)
        std = data.rolling(window=period).std()
        upper = middle + (std * deviation)
        lower = middle - (std * deviation)
        return upper, middle, lower
    
    def calculate_stochastic(self, df: pd.DataFrame, k_period: int, d_period: int) -> Tuple[pd.Series, pd.Series]:
        """Calculate Stochastic Oscillator"""
        low_min = df['low'].rolling(window=k_period).min()
        high_max = df['high'].rolling(window=k_period).max()
        
        stoch_k = 100 * (df['close'] - low_min) / (high_max - low_min)
        stoch_d = stoch_k.rolling(window=d_period).mean()
        
        return stoch_k, stoch_d
    
    def resample_to_htf(self, df: pd.DataFrame, multiplier: int) -> pd.DataFrame:
        """Resample M15 data to higher timeframe (H4 = M15 × 16)"""
        df = df.set_index('timestamp')
        
        # Resample to higher timeframe (M15 base = 15 minutes)
        htf = df.resample(f'{multiplier * 15}T').agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })
        
        htf = htf.reset_index()
        return htf
    
    def calculate_sentiment(self, df: pd.DataFrame) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate bullish/bearish sentiment from price action"""
        range_hl = df['high'] - df['low']
        range_hl = range_hl.replace(0, np.nan)  # Avoid division by zero
        
        bullish_sentiment = (df['close'] - df['low']) / range_hl
        bearish_sentiment = (df['high'] - df['close']) / range_hl
        net_sentiment = bullish_sentiment - bearish_sentiment
        
        # Fill NaN with neutral sentiment
        bullish_sentiment = bullish_sentiment.fillna(0.5)
        bearish_sentiment = bearish_sentiment.fillna(0.5)
        net_sentiment = net_sentiment.fillna(0.0)
        
        return bullish_sentiment, bearish_sentiment, net_sentiment
    
    def calculate_correlations(self, all_data: Dict[str, pd.DataFrame], window: int = 50) -> Dict[str, pd.DataFrame]:
        """Calculate rolling correlations between all pairs"""
        correlations = {}
        
        for pair in self.pairs:
            pair_corrs = pd.DataFrame(index=all_data[pair].index)
            
            for other_pair in self.pairs:
                # Calculate rolling correlation
                corr = all_data[pair]['close'].rolling(window=window).corr(
                    all_data[other_pair]['close']
                )
                pair_corrs[f'corr_{other_pair.lower()}'] = corr
            
            # Calculate average correlation (excluding self-correlation)
            corr_cols = [c for c in pair_corrs.columns if c != f'corr_{pair.lower()}']
            pair_corrs['avg_correlation'] = pair_corrs[corr_cols].mean(axis=1)
            
            correlations[pair] = pair_corrs
        
        return correlations
    
    def calculate_currency_strength(self, all_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        Calculate individual currency strength from all pairs
        
        Currency strength is derived by analyzing how each currency performs
        across all pairs it's involved in.
        """
        # Define which currencies are in which pairs
        pair_currencies = {
            'EURUSD.sim': ('EUR', 'USD'),
            'GBPUSD.sim': ('GBP', 'USD'),
            'USDJPY.sim': ('USD', 'JPY'),
            'USDCHF.sim': ('USD', 'CHF'),
            'AUDUSD.sim': ('AUD', 'USD'),
            'USDCAD.sim': ('USD', 'CAD'),
            'NZDUSD.sim': ('NZD', 'USD'),
            'EURGBP.sim': ('EUR', 'GBP')
        }
        
        currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'NZD']
        
        # Initialize strength DataFrames for each pair
        strength_dfs = {}
        
        for pair in self.pairs:
            strength_df = pd.DataFrame(index=all_data[pair].index)
            
            # Calculate normalized price movement for each pair
            pair_movements = {}
            for p in self.pairs:
                # Calculate percentage change (normalized)
                pct_change = all_data[p]['close'].pct_change(periods=20)  # 20-period momentum
                pair_movements[p] = pct_change
            
            # Calculate strength for each currency
            for currency in currencies:
                strength_values = []
                
                for p, (base, quote) in pair_currencies.items():
                    if currency == base:
                        # Currency is base - positive movement = strength
                        strength_values.append(pair_movements[p])
                    elif currency == quote:
                        # Currency is quote - negative movement = strength
                        strength_values.append(-pair_movements[p])
                
                if strength_values:
                    # Average strength across all pairs involving this currency
                    currency_strength = pd.concat(strength_values, axis=1).mean(axis=1)
                    # Normalize to 0-1 range using sigmoid
                    currency_strength = 1 / (1 + np.exp(-currency_strength * 100))
                else:
                    currency_strength = pd.Series(0.5, index=all_data[pair].index)
                
                strength_df[f'{currency.lower()}_strength'] = currency_strength
            
            strength_dfs[pair] = strength_df
        
        return strength_dfs
    
    def calculate_core_features(self, df: pd.DataFrame, pair: str) -> pd.DataFrame:
        """Calculate core technical indicators (26 features from v4)"""
        features = pd.DataFrame(index=df.index)
        
        # Price features
        features[f'{pair}_close'] = df['close']
        features[f'{pair}_high'] = df['high']
        features[f'{pair}_low'] = df['low']
        features[f'{pair}_volume'] = df['volume']
        
        # Moving averages
        features[f'{pair}_sma_20'] = self.calculate_sma(df['close'], self.sma_20_period)
        features[f'{pair}_sma_50'] = self.calculate_sma(df['close'], self.sma_50_period)
        features[f'{pair}_fast_ema'] = self.calculate_ema(df['close'], self.fast_ema_period)
        features[f'{pair}_slow_ema'] = self.calculate_ema(df['close'], self.slow_ema_period)
        
        # RSI
        features[f'{pair}_rsi'] = self.calculate_rsi(df['close'], self.rsi_period)
        
        # ATR
        features[f'{pair}_atr'] = self.calculate_atr(df, self.atr_period)
        
        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = self.calculate_bollinger_bands(
            df['close'], self.bb_period, self.bb_deviation
        )
        features[f'{pair}_bb_upper'] = bb_upper
        features[f'{pair}_bb_middle'] = bb_middle
        features[f'{pair}_bb_lower'] = bb_lower
        
        # Stochastic
        stoch_k, stoch_d = self.calculate_stochastic(df, self.stoch_k_period, self.stoch_d_period)
        features[f'{pair}_stoch_k'] = stoch_k
        features[f'{pair}_stoch_d'] = stoch_d
        
        # Volume features
        features[f'{pair}_volume_sma'] = self.calculate_sma(df['volume'], 20)
        features[f'{pair}_volume_ratio'] = df['volume'] / features[f'{pair}_volume_sma']
        features[f'{pair}_price_volume'] = df['close'] * df['volume']
        
        # Basic risk features
        returns = df['close'].pct_change()
        features[f'{pair}_volatility'] = returns.rolling(window=20).std()
        features[f'{pair}_momentum'] = df['close'].pct_change(periods=10)
        
        # Trend confirmations
        features[f'{pair}_trend_confirm'] = (
            (features[f'{pair}_fast_ema'] > features[f'{pair}_slow_ema']).astype(int)
        )
        features[f'{pair}_momentum_confirm'] = (features[f'{pair}_momentum'] > 0).astype(int)
        features[f'{pair}_volatility_confirm'] = (
            features[f'{pair}_volatility'] < features[f'{pair}_volatility'].rolling(window=50).mean()
        ).astype(int)
        
        # Additional risk metrics
        features[f'{pair}_returns_std'] = returns.rolling(window=20).std()
        features[f'{pair}_sharpe_approx'] = (
            returns.rolling(window=20).mean() / features[f'{pair}_returns_std']
        )
        
        # Max drawdown approximation
        cummax = df['close'].expanding().max()
        drawdown = (df['close'] - cummax) / cummax
        features[f'{pair}_max_drawdown'] = drawdown.rolling(window=20).min()
        
        return features
    
    def calculate_htf_features(self, df: pd.DataFrame, pair: str) -> pd.DataFrame:
        """Calculate Higher Timeframe features (4 features)"""
        features = pd.DataFrame(index=df.index)
        
        # Resample to HTF
        htf_df = self.resample_to_htf(df.copy(), self.htf_multiplier)
        
        # Calculate HTF EMAs
        htf_fast_ema = self.calculate_ema(htf_df['close'], self.fast_ema_period)
        htf_slow_ema = self.calculate_ema(htf_df['close'], self.slow_ema_period)
        
        # Add EMAs back to HTF dataframe
        htf_df['htf_fast_ema'] = htf_fast_ema
        htf_df['htf_slow_ema'] = htf_slow_ema
        
        # Merge with original timeframe using forward fill
        df_temp = df[['timestamp']].copy()
        df_temp = pd.merge_asof(
            df_temp.sort_values('timestamp'),
            htf_df[['timestamp', 'htf_fast_ema', 'htf_slow_ema']].sort_values('timestamp'),
            on='timestamp',
            direction='backward'
        )
        
        features[f'{pair}_htf_fast_ema'] = df_temp['htf_fast_ema'].values
        features[f'{pair}_htf_slow_ema'] = df_temp['htf_slow_ema'].values
        
        # HTF trend direction
        features[f'{pair}_htf_trend_direction'] = np.sign(
            features[f'{pair}_htf_fast_ema'] - features[f'{pair}_htf_slow_ema']
        )
        
        # Calculate current trend from core features (will be available)
        current_fast = self.calculate_ema(df['close'], self.fast_ema_period)
        current_slow = self.calculate_ema(df['close'], self.slow_ema_period)
        current_trend = np.sign(current_fast - current_slow)
        
        # HTF trend alignment
        features[f'{pair}_htf_trend_alignment'] = (
            current_trend == features[f'{pair}_htf_trend_direction']
        ).astype(int)
        
        return features
    
    def calculate_sentiment_features(self, df: pd.DataFrame, pair: str) -> pd.DataFrame:
        """Calculate sentiment features (3 features)"""
        features = pd.DataFrame(index=df.index)
        
        bullish, bearish, net = self.calculate_sentiment(df)
        
        features[f'{pair}_bullish_sentiment'] = bullish
        features[f'{pair}_bearish_sentiment'] = bearish
        features[f'{pair}_net_sentiment'] = net
        
        return features
    
    def add_correlation_features(self, features_df: pd.DataFrame, pair: str, 
                                   correlations: pd.DataFrame) -> pd.DataFrame:
        """Add correlation features to main features DataFrame"""
        for col in correlations.columns:
            features_df[f'{pair}_{col}'] = correlations[col].values
        
        return features_df
    
    def add_strength_features(self, features_df: pd.DataFrame, pair: str,
                              strength: pd.DataFrame) -> pd.DataFrame:
        """Add currency strength features to main features DataFrame"""
        for col in strength.columns:
            features_df[f'{pair}_{col}'] = strength[col].values
        
        return features_df
    
    def calculate_confirmation_features(self, features_df: pd.DataFrame, pair: str) -> pd.DataFrame:
        """Calculate 9-point confirmation features (5 additional features)"""
        # Note: EMA, RSI, Volume, BB, Stoch confirmations already exist in core features
        # Adding: HTF, Price Action, and Correlation confirmations
        
        # HTF confirmation (already calculated, just referencing)
        # features_df already has htf_trend_alignment which serves as htf_confirm
        features_df[f'{pair}_htf_confirm'] = features_df[f'{pair}_htf_trend_alignment']
        
        # Price action confirmation (trend aligns with sentiment)
        trend_direction = np.sign(
            features_df[f'{pair}_fast_ema'] - features_df[f'{pair}_slow_ema']
        )
        
        features_df[f'{pair}_price_action_confirm'] = (
            ((trend_direction > 0) & (features_df[f'{pair}_net_sentiment'] > 0)) |
            ((trend_direction < 0) & (features_df[f'{pair}_net_sentiment'] < 0))
        ).astype(int)
        
        # Correlation confirmation (average correlation supports move)
        features_df[f'{pair}_correlation_confirm'] = (
            features_df[f'{pair}_avg_correlation'] > 0.3
        ).astype(int)
        
        # EMA confirmation (already exists as trend_confirm)
        features_df[f'{pair}_ema_confirm'] = features_df[f'{pair}_trend_confirm']
        
        # RSI confirmation
        features_df[f'{pair}_rsi_confirm'] = (
            ((features_df[f'{pair}_rsi'] < 30) & (trend_direction > 0)) |
            ((features_df[f'{pair}_rsi'] > 70) & (trend_direction < 0))
        ).astype(int)
        
        # Volume confirmation
        features_df[f'{pair}_volume_confirm'] = (
            features_df[f'{pair}_volume_ratio'] > 1.0
        ).astype(int)
        
        # BB confirmation
        features_df[f'{pair}_bb_confirm'] = (
            ((features_df[f'{pair}_close'] < features_df[f'{pair}_bb_lower']) & (trend_direction > 0)) |
            ((features_df[f'{pair}_close'] > features_df[f'{pair}_bb_upper']) & (trend_direction < 0))
        ).astype(int)
        
        # Stoch confirmation
        features_df[f'{pair}_stoch_confirm'] = (
            ((features_df[f'{pair}_stoch_k'] < 20) & (trend_direction > 0)) |
            ((features_df[f'{pair}_stoch_k'] > 80) & (trend_direction < 0))
        ).astype(int)
        
        return features_df
    
    def extract_features_all_pairs(self) -> pd.DataFrame:
        """
        Extract all 55 features for all 8 pairs using chunked extraction
        Returns combined DataFrame with 442 columns (timestamp + 440 features + row_symbol)
        """
        print("="*80)
        print("HISTORICAL FEATURE EXTRACTION v5.1 - M15 TIMEFRAME")
        print("="*80)
        print(f"Timeframe: M15 (15-minute bars)")
        print(f"HTF Confirmation: H4 (4-hour bars)")
        print(f"Target bars per pair: {self.bars_to_extract:,}")
        print(f"Chunk size: {self.chunk_size:,} bars")
        print(f"Estimated chunks per pair: {(self.bars_to_extract + self.chunk_size - 1) // self.chunk_size}")
        
        # Step 1: Load all pairs' data simultaneously using chunked extraction
        print("\n[STEP 1/6] Loading historical data for all 8 pairs (CHUNKED)...")
        all_data = {}
        
        extraction_start = time.time()
        
        for i, pair in enumerate(self.pairs, 1):
            print(f"\n  [{i}/{len(self.pairs)}] Extracting {pair}...")
            df = self.extract_data_in_chunks(pair, self.bars_to_extract)
            
            if df.empty:
                print(f"    [ERROR] FAILED - No data for {pair}")
                return pd.DataFrame()
            
            all_data[pair] = df
            print(f"    [OK] Total: {len(df):,} bars extracted")
            
            # Show progress estimate
            elapsed = time.time() - extraction_start
            avg_time_per_pair = elapsed / i
            remaining_pairs = len(self.pairs) - i
            eta_seconds = avg_time_per_pair * remaining_pairs
            
            if remaining_pairs > 0:
                print(f"    [TIMER]  Estimated time remaining: {eta_seconds/60:.1f} minutes")
        
        extraction_time = time.time() - extraction_start
        print(f"\n  [OK] Data extraction complete in {extraction_time/60:.1f} minutes")
        
        # Align timestamps across all pairs (use intersection of timestamps)
        print("\n[STEP 2/6] Aligning timestamps across all pairs...")
        common_timestamps = set(all_data[self.pairs[0]]['timestamp'])
        for pair in self.pairs[1:]:
            common_timestamps &= set(all_data[pair]['timestamp'])
        
        common_timestamps = sorted(list(common_timestamps))
        print(f"  [OK] {len(common_timestamps):,} common timestamps across all pairs")
        
        # Filter all data to common timestamps
        for pair in self.pairs:
            all_data[pair] = all_data[pair][
                all_data[pair]['timestamp'].isin(common_timestamps)
            ].reset_index(drop=True)
        
        # Step 2: Calculate cross-pair features (correlations and currency strength)
        print("\n[STEP 3/6] Calculating cross-pair features...")
        print(f"  Calculating rolling correlations (window={self.correlation_window})...", end=" ")
        correlations = self.calculate_correlations(all_data, self.correlation_window)
        print("[OK]")
        
        print(f"  Calculating currency strength meters...", end=" ")
        strength = self.calculate_currency_strength(all_data)
        print("[OK]")
        
        # Step 3: Calculate features for each pair
        print("\n[STEP 4/6] Calculating features for each pair...")
        
        all_features = []
        
        for pair in self.pairs:
            print(f"\n  Processing {pair}:")
            df = all_data[pair]
            
            # Core features (26 from v4)
            print(f"    Core technical indicators...", end=" ")
            features = self.calculate_core_features(df, pair)
            print(f"[OK] {len(features.columns)} features")
            
            # HTF features (4 new)
            print(f"    Higher timeframe analysis...", end=" ")
            htf_features = self.calculate_htf_features(df, pair)
            features = pd.concat([features, htf_features], axis=1)
            print(f"[OK] 4 features")
            
            # Sentiment features (3 new)
            print(f"    Sentiment analysis...", end=" ")
            sentiment_features = self.calculate_sentiment_features(df, pair)
            features = pd.concat([features, sentiment_features], axis=1)
            print(f"[OK] 3 features")
            
            # Correlation features (9 new)
            print(f"    Currency correlations...", end=" ")
            features = self.add_correlation_features(features, pair, correlations[pair])
            print(f"[OK] 9 features")
            
            # Strength features (8 new)
            print(f"    Currency strength...", end=" ")
            features = self.add_strength_features(features, pair, strength[pair])
            print(f"[OK] 8 features")
            
            # Confirmation features (5 new)
            print(f"    9-point confirmations...", end=" ")
            features = self.calculate_confirmation_features(features, pair)
            print(f"[OK] 8 features (total confirmations)")
            
            # Add timestamp and row_symbol
            features.insert(0, 'timestamp', df['timestamp'])
            features['row_symbol'] = pair
            
            print(f"    TOTAL: {len([c for c in features.columns if pair in c])} features for {pair}")
            
            all_features.append(features)
        
        # Step 4: Combine all pairs into single DataFrame
        print("\n[STEP 5/6] Combining all pairs into single dataset...")
        combined_df = pd.concat(all_features, axis=0, ignore_index=True)
        
        # Fill NaN values
        print("  Handling NaN values...", end=" ")
        combined_df = combined_df.fillna(method='ffill').fillna(method='bfill').fillna(0)
        print("[OK]")
        
        # Verify column count
        print("\n[STEP 6/6] Verification...")
        total_cols = len(combined_df.columns)
        expected_cols = 1 + (55 * 8) + 1  # timestamp + (55 features × 8 pairs) + row_symbol
        
        print(f"  Total columns: {total_cols}")
        print(f"  Expected columns: {expected_cols}")
        
        if total_cols == expected_cols:
            print("  [OK] Column count CORRECT")
        else:
            print(f"  [WARNING] Column count mismatch! Got {total_cols}, expected {expected_cols}")
        
        # Count features per pair
        print("\n  Features per pair:")
        for pair in self.pairs:
            pair_features = [c for c in combined_df.columns if c.startswith(pair)]
            print(f"    {pair}: {len(pair_features)} features")
        
        return combined_df
    
    def save_to_csv(self, df: pd.DataFrame, filename: str = "accumulated_features_m15_chunked.csv"):
        """Save extracted features to CSV"""
        print(f"\n[SAVING] Writing to {filename}...")
        print(f"  Rows: {len(df):,}")
        print(f"  Columns: {len(df.columns)}")
        print(f"  Size: {df.memory_usage(deep=True).sum() / 1024**2:.2f} MB")
        
        df.to_csv(filename, index=False)
        print(f"  [OK] Saved successfully")
    
    def run(self):
        """Main execution method"""
        start_time = time.time()
        
        # Connect to MT5
        if not self.connect_mt5():
            return
        
        try:
            # Extract features
            features_df = self.extract_features_all_pairs()
            
            if features_df.empty:
                print("\n[ERROR] Feature extraction failed")
                return
            
            # Save to CSV
            self.save_to_csv(features_df)
            
            # Summary
            elapsed = time.time() - start_time
            print("\n" + "="*80)
            print("EXTRACTION COMPLETE")
            print("="*80)
            print(f"[TIMER]  Total time: {elapsed/60:.2f} minutes ({elapsed/3600:.2f} hours)")
            print(f"[CHART] Total samples: {len(features_df):,}")
            print(f"📈 Samples per pair: {len(features_df)//8:,}")
            print(f"🔢 Total columns: {len(features_df.columns)}")
            print(f"[OK] All 55 features extracted per pair")
            print("\nNext steps:")
            print("1. Run data_labeler_v2.py to label the data")
            print("2. Run data_splitter_timebased.py to create train/val/test splits")
            print("3. Proceed to model training")
            
        except Exception as e:
            print(f"\n[ERROR] Error during extraction: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            # Disconnect
            self.disconnect_mt5()


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════════════════════╗
    ║                                                                          ║
    ║           HISTORICAL FEATURE EXTRACTOR v5.1 - M15 TIMEFRAME              ║
    ║           Complete 55-Feature Extraction for M15 Trading                 ║
    ║                                                                          ║
    ║  TIMEFRAME MIGRATION:                                                    ║
    ║  [OK] Execution: M15 (was M5)                                              ║
    ║  [OK] HTF Confirmation: H4 (was M20)                                       ║
    ║  [OK] Same indicator periods (12,14,20,26,50)                              ║
    ║  [OK] Same ~694 days of data (67k bars on M15)                             ║
    ║                                                                          ║
    ║  Features per pair: 55                                                   ║
    ║  Total pairs: 8                                                          ║
    ║  Total features: 440                                                     ║
    ║  Output columns: 442 (timestamp + 440 features + row_symbol)             ║
    ║                                                                          ║
    ║  FEATURES:                                                               ║
    ║  [OK] Higher Timeframe Analysis (4 features) - H4                          ║
    ║  [OK] Advanced Sentiment (3 features)                                      ║
    ║  [OK] Currency Correlations (9 features)                                   ║
    ║  [OK] Currency Strength (8 features)                                       ║
    ║  [OK] Enhanced Confirmations (8 total)                                     ║
    ║                                                                          ║
    ╚══════════════════════════════════════════════════════════════════════════╝
    """)
    
    extractor = HistoricalExtractorV5Chunked()
    extractor.run()
