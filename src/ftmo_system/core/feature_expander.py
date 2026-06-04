"""
Feature Expansion Module - 58 to 105 Features
==============================================

Takes 58 base features from Bridge EA and computes 47 additional features
for confluence scoring and improved model training.

Additional Features:
- Pivot Points (7): PP, S1, S2, S3, R1, R2, R3
- Pivot Distances (5): dist_to_pivot, dist_to_support, dist_to_resistance, pivot_position, pivot_confluence
- Fibonacci Levels (6): fib_0.236, fib_0.382, fib_0.5, fib_0.618, fib_0.786, fib_1.0
- Fib Distances (3): dist_to_nearest_fib, fib_level_strength, at_fib_level
- Psychological Levels (4): dist_to_major_psych, dist_to_minor_psych, psych_confluence, at_psych_level
- MTF Alignment (6): mtf_trend_h1, mtf_momentum_h1, mtf_trend_h4, mtf_rsi_h4, mtf_alignment_score, htf_momentum
- Market Regime (4): market_regime, regime_confidence, regime_transition, regime_duration
- Session Features (4): session_volatility_mult, is_high_liquidity, active_session_count, overlap_intensity
- Momentum Extended (6): momentum_acceleration, momentum_divergence, rsi_divergence, macd_divergence, stoch_divergence, macd_histogram
- Volume Extended (5): volume_trend, volume_breakout, cumulative_delta, volume_climax, volume_spike

Total: 58 base + 50 computed = 108 features

Author: AI Trading System
Version: 1.1
Date: 2025-11-29

CHANGELOG v1.1:
- Fixed swing high/low calculation using historical_data parameter
- Fibonacci levels now calculated from actual N-bar lookback (default 50)
- Removed stateful swing_data tracking (now stateless)
- Added swing_lookback parameter for configurable lookback period
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class ExpandedFeatures:
    """Container for expanded feature set"""
    features: np.ndarray  # Shape: (108,)
    feature_names: List[str]
    base_count: int
    expanded_count: int
    
    def to_dict(self) -> Dict[str, float]:
        return {name: float(self.features[i]) for i, name in enumerate(self.feature_names)}


class FeatureExpander:
    """
    Expands 58 base features to 108 features for training.
    
    Computes pivot points, fibonacci levels, psychological levels,
    and multi-timeframe alignment features.
    
    Args:
        swing_lookback: Number of bars to use for swing high/low detection (default 50)
    """
    
    def __init__(self, swing_lookback: int = 50):
        self.swing_lookback = swing_lookback
        
        # Base feature names (58 from EA)
        self.base_feature_names = [
            'close', 'high', 'low', 'volume', 'sma_20', 'sma_50', 'fast_ema', 'slow_ema',
            'rsi', 'atr', 'bb_upper', 'bb_middle', 'bb_lower', 'stoch_k', 'stoch_d',
            'volume_sma', 'volume_ratio', 'price_volume', 'volatility', 'momentum',
            'trend_confirm', 'momentum_confirm', 'volatility_confirm', 'returns_std',
            'sharpe_approx', 'max_drawdown', 'htf_fast_ema', 'htf_slow_ema',
            'htf_trend_direction', 'htf_trend_alignment', 'bullish_sentiment',
            'bearish_sentiment', 'net_sentiment', 'corr_eurusd', 'corr_gbpusd',
            'corr_usdjpy', 'corr_usdchf', 'corr_audusd', 'corr_usdcad', 'corr_nzdusd',
            'corr_eurgbp', 'avg_correlation', 'usd_strength', 'eur_strength',
            'gbp_strength', 'jpy_strength', 'chf_strength', 'cad_strength',
            'aud_strength', 'nzd_strength', 'htf_confirm', 'price_action_confirm',
            'correlation_confirm', 'ema_confirm', 'rsi_confirm', 'volume_confirm',
            'bb_confirm', 'stoch_confirm'
        ]
        
        # Expanded feature names (50 new)
        self.expanded_feature_names = [
            # Pivot Points (7)
            'pivot_pp', 'pivot_s1', 'pivot_s2', 'pivot_s3', 'pivot_r1', 'pivot_r2', 'pivot_r3',
            # Pivot Distances (5)
            'dist_to_pivot', 'dist_to_nearest_support', 'dist_to_nearest_resistance', 'pivot_position', 'pivot_confluence',
            # Fibonacci Levels (6)
            'fib_0236', 'fib_0382', 'fib_0500', 'fib_0618', 'fib_0786', 'fib_1000',
            # Fib Distances (3)
            'dist_to_nearest_fib', 'fib_level_strength', 'at_fib_level',
            # Psychological Levels (4)
            'dist_to_major_psych', 'dist_to_minor_psych', 'psych_confluence', 'at_psych_level',
            # MTF Alignment Extended (6)
            'mtf_trend_h1', 'mtf_momentum_h1', 'mtf_trend_h4', 'mtf_rsi_h4', 
            'mtf_alignment_score', 'htf_momentum',
            # Market Regime (4)
            'market_regime', 'regime_confidence', 'regime_transition', 'regime_duration',
            # Session Features (4)
            'session_volatility_mult', 'is_high_liquidity_period', 'active_session_count', 'overlap_intensity',
            # Momentum Extended (6)
            'momentum_acceleration', 'momentum_divergence', 'rsi_divergence', 
            'macd_divergence', 'stoch_divergence', 'macd_histogram',
            # Volume Extended (5)
            'volume_trend', 'volume_breakout', 'cumulative_delta', 'volume_climax', 'volume_spike'
        ]
        
        # Combined feature names
        self.all_feature_names = self.base_feature_names + self.expanded_feature_names
        
        # Pip values for distance calculations
        self.pip_values = {
            'EURUSD': 0.0001, 'GBPUSD': 0.0001, 'USDJPY': 0.01, 'USDCHF': 0.0001,
            'AUDUSD': 0.0001, 'USDCAD': 0.0001, 'NZDUSD': 0.0001, 'EURGBP': 0.0001,
        }
    
    def expand(
        self,
        base_features: np.ndarray,
        symbol: str,
        historical_data: Optional[pd.DataFrame] = None
    ) -> ExpandedFeatures:
        """
        Expand 58 base features to 108 features.
        
        Args:
            base_features: numpy array of 58 features from EA
            symbol: Trading symbol (e.g., 'EURUSD.sim')
            historical_data: DataFrame with columns ['high', 'low', 'close'] for swing detection.
                           Should contain at least swing_lookback rows of recent OHLC data.
                           Most recent bar should be LAST row (index -1).
            
        Returns:
            ExpandedFeatures with 108 total features
        """
        if len(base_features) != 58:
            raise ValueError(f"Expected 58 base features, got {len(base_features)}")
        
        # Extract key values from base features
        base_dict = {name: base_features[i] for i, name in enumerate(self.base_feature_names)}
        
        close = base_dict['close']
        high = base_dict['high']
        low = base_dict['low']
        atr = base_dict['atr']
        
        # Get pip value for this symbol
        symbol_clean = symbol.replace('.sim', '')
        pip_value = self.pip_values.get(symbol_clean, 0.0001)
        
        # Compute expanded features (50 total)
        expanded = np.zeros(50, dtype=np.float32)
        
        # === PIVOT POINTS (7) ===
        pivots = self._calculate_pivots(high, low, close)
        expanded[0:7] = pivots
        
        # === PIVOT DISTANCES (5) ===
        pivot_distances = self._calculate_pivot_distances(close, pivots, pip_value)
        expanded[7:12] = pivot_distances
        
        # === FIBONACCI LEVELS (6) - NOW USES HISTORICAL DATA ===
        fib_levels = self._calculate_fib_levels(close, pip_value, historical_data)
        expanded[12:18] = fib_levels
        
        # === FIB DISTANCES (3) ===
        fib_distances = self._calculate_fib_distances(close, fib_levels, pip_value)
        expanded[18:21] = fib_distances
        
        # === PSYCHOLOGICAL LEVELS (4) ===
        psych_features = self._calculate_psych_levels(close, pip_value)
        expanded[21:25] = psych_features
        
        # === MTF ALIGNMENT EXTENDED (6) ===
        mtf_features = self._calculate_mtf_features(base_dict)
        expanded[25:31] = mtf_features
        
        # === MARKET REGIME (4) ===
        regime_features = self._calculate_regime_features(base_dict, atr)
        expanded[31:35] = regime_features
        
        # === SESSION FEATURES (4) ===
        session_features = self._calculate_session_features()
        expanded[35:39] = session_features
        
        # === MOMENTUM EXTENDED (6) ===
        momentum_features = self._calculate_momentum_extended(base_dict)
        expanded[39:45] = momentum_features
        
        # === VOLUME EXTENDED (5) ===
        volume_features = self._calculate_volume_extended(base_dict)
        expanded[45:50] = volume_features
        
        # Combine base + expanded
        all_features = np.concatenate([base_features, expanded])
        
        return ExpandedFeatures(
            features=all_features,
            feature_names=self.all_feature_names,
            base_count=58,
            expanded_count=50
        )
    
    def _calculate_pivots(self, high: float, low: float, close: float) -> np.ndarray:
        """Calculate standard pivot points from previous bar's OHLC"""
        pp = (high + low + close) / 3
        
        s1 = 2 * pp - high
        s2 = pp - (high - low)
        s3 = low - 2 * (high - pp)
        
        r1 = 2 * pp - low
        r2 = pp + (high - low)
        r3 = high + 2 * (pp - low)
        
        return np.array([pp, s1, s2, s3, r1, r2, r3], dtype=np.float32)
    
    def _calculate_pivot_distances(
        self, close: float, pivots: np.ndarray, pip_value: float
    ) -> np.ndarray:
        """Calculate distances to pivot levels in pips"""
        pp, s1, s2, s3, r1, r2, r3 = pivots
        
        dist_to_pivot = (close - pp) / pip_value
        
        # Distance to nearest support
        supports = [s1, s2, s3]
        dist_to_support = min(abs(close - s) for s in supports) / pip_value
        
        # Distance to nearest resistance
        resistances = [r1, r2, r3]
        dist_to_resistance = min(abs(close - r) for r in resistances) / pip_value
        
        # Pivot position (-1 to 1, where -1 = at S3, 1 = at R3)
        range_total = r3 - s3
        if range_total > 0:
            pivot_position = 2 * (close - s3) / range_total - 1
        else:
            pivot_position = 0
        
        # Pivot confluence (count of nearby pivot levels)
        pivot_confluence = 0
        all_levels = [pp, s1, s2, s3, r1, r2, r3]
        for level in all_levels:
            dist_pips = abs(close - level) / pip_value
            if dist_pips <= 20:  # Within 20 pips
                pivot_confluence += 1
        
        return np.array([dist_to_pivot, dist_to_support, dist_to_resistance, pivot_position, pivot_confluence], dtype=np.float32)
    
    def _calculate_fib_levels(
        self, 
        close: float, 
        pip_value: float,
        historical_data: Optional[pd.DataFrame] = None
    ) -> np.ndarray:
        """
        Calculate Fibonacci retracement levels from swing high/low.
        
        Uses historical_data to find the highest high and lowest low
        over the lookback period for proper swing detection.
        
        Args:
            close: Current close price
            pip_value: Pip value for the symbol
            historical_data: DataFrame with 'high' and 'low' columns.
                           Most recent bar should be LAST row.
        
        Returns:
            Array of 6 Fibonacci levels: [0.236, 0.382, 0.500, 0.618, 0.786, 1.000]
        """
        # If no historical data provided, return zeros (can't calculate properly)
        if historical_data is None or len(historical_data) < 2:
            return np.zeros(6, dtype=np.float32)
        
        # Validate required columns
        if 'high' not in historical_data.columns or 'low' not in historical_data.columns:
            return np.zeros(6, dtype=np.float32)
        
        # Use last N bars for swing detection
        lookback = min(self.swing_lookback, len(historical_data))
        recent_data = historical_data.tail(lookback)
        
        # Find swing high and swing low
        swing_high = recent_data['high'].max()
        swing_low = recent_data['low'].min()
        swing_range = swing_high - swing_low
        
        # Need meaningful range (at least 10 pips)
        min_range = pip_value * 10
        if swing_range < min_range:
            return np.zeros(6, dtype=np.float32)
        
        # Determine trend direction to calculate retracements correctly
        # If close is closer to swing_high, we're in uptrend (retrace from high)
        # If close is closer to swing_low, we're in downtrend (retrace from low)
        
        dist_to_high = swing_high - close
        dist_to_low = close - swing_low
        
        if dist_to_high <= dist_to_low:
            # Uptrend - retracement levels from high going down
            fib_0236 = swing_high - swing_range * 0.236
            fib_0382 = swing_high - swing_range * 0.382
            fib_0500 = swing_high - swing_range * 0.500
            fib_0618 = swing_high - swing_range * 0.618
            fib_0786 = swing_high - swing_range * 0.786
            fib_1000 = swing_low
        else:
            # Downtrend - retracement levels from low going up
            fib_0236 = swing_low + swing_range * 0.236
            fib_0382 = swing_low + swing_range * 0.382
            fib_0500 = swing_low + swing_range * 0.500
            fib_0618 = swing_low + swing_range * 0.618
            fib_0786 = swing_low + swing_range * 0.786
            fib_1000 = swing_high
        
        return np.array([fib_0236, fib_0382, fib_0500, fib_0618, fib_0786, fib_1000], dtype=np.float32)
    
    def _calculate_fib_distances(
        self, close: float, fib_levels: np.ndarray, pip_value: float
    ) -> np.ndarray:
        """Calculate distances to Fibonacci levels"""
        if np.all(fib_levels == 0):
            return np.zeros(3, dtype=np.float32)
        
        # Distance to nearest fib level
        distances = [abs(close - level) for level in fib_levels if level > 0]
        dist_to_nearest = min(distances) / pip_value if distances else 0
        
        # Fib level strength (closer = stronger)
        fib_strength = max(0, 1 - dist_to_nearest / 50)  # Within 50 pips = strong
        
        # At fib level flag (within 10 pips)
        at_fib = 1.0 if dist_to_nearest <= 10 else 0.0
        
        return np.array([dist_to_nearest, fib_strength, at_fib], dtype=np.float32)
    
    def _calculate_psych_levels(self, close: float, pip_value: float) -> np.ndarray:
        """Calculate distances to psychological (round number) levels"""
        # Major psychological levels (every 100 pips for non-JPY, every 100 for JPY)
        if pip_value == 0.01:  # JPY pair
            major_round = 1.0
            minor_round = 0.5
        else:
            major_round = 0.01  # 100 pips
            minor_round = 0.005  # 50 pips
        
        # Distance to nearest major level
        nearest_major = round(close / major_round) * major_round
        dist_major = abs(close - nearest_major) / pip_value
        
        # Distance to nearest minor level
        nearest_minor = round(close / minor_round) * minor_round
        dist_minor = abs(close - nearest_minor) / pip_value
        
        # Confluence (multiple levels nearby)
        psych_confluence = 0
        if dist_major <= 20:
            psych_confluence += 1
        if dist_minor <= 10:
            psych_confluence += 1
        
        # At psychological level flag
        at_psych = 1.0 if dist_major <= 10 or dist_minor <= 5 else 0.0
        
        return np.array([dist_major, dist_minor, psych_confluence, at_psych], dtype=np.float32)
    
    def _calculate_mtf_features(self, base_dict: Dict[str, float]) -> np.ndarray:
        """Calculate multi-timeframe alignment features"""
        # Use existing HTF data from base features
        htf_trend = base_dict.get('htf_trend_direction', 0)
        htf_alignment = base_dict.get('htf_trend_alignment', 0)
        
        # Derive MTF features
        mtf_trend_h1 = htf_trend  # Use HTF as proxy for H1
        mtf_momentum_h1 = base_dict.get('momentum', 0) * htf_trend
        
        # H4 approximation (less responsive)
        mtf_trend_h4 = htf_trend * 0.8 + base_dict.get('trend_confirm', 0) * 0.2
        mtf_rsi_h4 = base_dict.get('rsi', 50)
        
        # Alignment score (-3 to 3)
        alignment_score = (
            (1 if htf_trend > 0 else -1) +
            (1 if htf_alignment > 0 else -1) +
            (1 if base_dict.get('ema_confirm', 0) > 0 else -1)
        )
        
        # HTF momentum
        htf_momentum = htf_trend * abs(base_dict.get('momentum', 0))
        
        return np.array([
            mtf_trend_h1, mtf_momentum_h1, mtf_trend_h4, 
            mtf_rsi_h4, alignment_score, htf_momentum
        ], dtype=np.float32)
    
    def _calculate_regime_features(self, base_dict: Dict[str, float], atr: float) -> np.ndarray:
        """Calculate market regime features"""
        volatility = base_dict.get('volatility', 0)
        trend_confirm = base_dict.get('trend_confirm', 0)
        
        # Market regime (0=ranging, 1=trending, 2=volatile)
        if volatility > 0.02:
            regime = 2  # Volatile
        elif trend_confirm > 0.5 and atr > 0:
            regime = 1  # Trending
        else:
            regime = 0  # Ranging
        
        # Regime confidence
        confidence = min(abs(trend_confirm) + volatility * 10, 1.0)
        
        # Transition flag (placeholder - would need history)
        transition = 0
        
        # Duration (placeholder)
        duration = 1
        
        return np.array([regime, confidence, transition, duration], dtype=np.float32)
    
    def _calculate_session_features(self) -> np.ndarray:
        """Calculate trading session features"""
        now = datetime.utcnow()
        hour = now.hour
        
        # Session times (UTC)
        in_london = 8 <= hour < 17
        in_ny = 13 <= hour < 22
        in_tokyo = 0 <= hour < 9
        in_sydney = 22 <= hour or hour < 7
        
        # Session volatility multiplier
        if in_london and in_ny:
            vol_mult = 1.5  # Overlap = highest volatility
        elif in_london or in_ny:
            vol_mult = 1.2
        else:
            vol_mult = 0.8
        
        # High liquidity period
        is_high_liquidity = 1.0 if (in_london or in_ny) else 0.0
        
        # Active session count
        active_count = sum([in_london, in_ny, in_tokyo, in_sydney])
        
        # Overlap intensity
        overlap = 1.0 if (in_london and in_ny) else 0.0
        
        return np.array([vol_mult, is_high_liquidity, active_count, overlap], dtype=np.float32)
    
    def _calculate_momentum_extended(self, base_dict: Dict[str, float]) -> np.ndarray:
        """Calculate extended momentum features"""
        momentum = base_dict.get('momentum', 0)
        rsi = base_dict.get('rsi', 50)
        stoch_k = base_dict.get('stoch_k', 50)
        
        # Momentum acceleration (placeholder - needs history)
        acceleration = momentum * 0.1
        
        # Momentum divergence (placeholder)
        mom_divergence = 0
        
        # RSI divergence (simplified)
        rsi_divergence = (rsi - 50) / 50 * (1 if momentum > 0 else -1)
        
        # MACD divergence (placeholder)
        macd_divergence = 0
        
        # Stochastic divergence
        stoch_divergence = (stoch_k - 50) / 50 * (1 if momentum > 0 else -1)
        
        # MACD histogram (derived from momentum and RSI)
        macd_histogram = momentum * (1 if rsi > 50 else -1) * abs(rsi - 50) / 50
        
        return np.array([
            acceleration, mom_divergence, rsi_divergence,
            macd_divergence, stoch_divergence, macd_histogram
        ], dtype=np.float32)
    
    def _calculate_volume_extended(self, base_dict: Dict[str, float]) -> np.ndarray:
        """Calculate extended volume features"""
        volume_ratio = base_dict.get('volume_ratio', 1.0)
        
        # Volume trend
        volume_trend = 1 if volume_ratio > 1.0 else -1
        
        # Volume breakout
        volume_breakout = 1.0 if volume_ratio > 2.0 else 0.0
        
        # Cumulative delta (placeholder)
        cumulative_delta = 0
        
        # Volume climax
        volume_climax = 1.0 if volume_ratio > 3.0 else 0.0
        
        # Volume spike (significant increase from average)
        volume_spike = 1.0 if volume_ratio > 1.5 else 0.0
        
        return np.array([volume_trend, volume_breakout, cumulative_delta, volume_climax, volume_spike], dtype=np.float32)
    
    def get_feature_names(self) -> List[str]:
        """Return all 108 feature names (58 base + 50 expanded)"""
        return self.all_feature_names.copy()
    
    def get_feature_count(self) -> int:
        """Return total feature count"""
        return len(self.all_feature_names)


# Convenience function
def expand_features(
    base_features: np.ndarray,
    symbol: str,
    historical_data: Optional[pd.DataFrame] = None,
    expander: Optional[FeatureExpander] = None
) -> np.ndarray:
    """
    Quick function to expand 58 features to 108.
    
    Args:
        base_features: 58-feature array
        symbol: Trading symbol
        historical_data: DataFrame with 'high', 'low', 'close' columns for Fib calculation
        expander: Optional pre-created expander (for efficiency)
        
    Returns:
        108-feature array
    """
    if expander is None:
        expander = FeatureExpander()
    
    result = expander.expand(base_features, symbol, historical_data)
    return result.features
