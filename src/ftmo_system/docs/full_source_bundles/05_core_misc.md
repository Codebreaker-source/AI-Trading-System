# Source Bundle: docs/full_source_bundles/05_core_misc.md


---

## `core/feature_expander.py`

```py
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

```

---

## `core/feature_history_recorder.py`

```py
"""
Feature History Recorder
=========================
Append-only per-symbol log of the raw 27-feature snapshot taken each
trading cycle. Used to build fixed-length feature sequences
(data/feature_sequences/{trade_id}.npy) for sequence models
(LSTM/Transformer/CNN) once a trade's outcome is finalized.

CSV append (not parquet) — matches the rest of the codebase's
file-based logging (unified_trade_logger, EA CSVs) and survives
process restarts without needing an open writer handle.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

FEATURE_27 = [
    "close", "high", "low", "volume",
    "sma_20", "sma_50", "fast_ema", "slow_ema",
    "htf_fast_ema", "htf_slow_ema", "htf_trend_direction", "htf_trend_alignment",
    "rsi", "stoch_k", "stoch_d", "momentum",
    "atr", "bb_upper", "bb_middle", "bb_lower", "volatility",
    "volume_sma", "volume_ratio", "price_volume",
    "bullish_sentiment", "bearish_sentiment", "net_sentiment",
]

HISTORY_COLUMNS = ["timestamp"] + FEATURE_27

SEQUENCE_LENGTH = 50


class FeatureHistoryRecorder:
    """One CSV per symbol under data/feature_history/."""

    def __init__(self, history_dir: str):
        self.history_dir = Path(history_dir)
        self.history_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, symbol: str) -> Path:
        return self.history_dir / f"{symbol}.csv"

    def append(self, symbol: str, base_features: np.ndarray, timestamp: datetime = None):
        """Append one 27-feature snapshot for `symbol`."""
        if base_features is None or len(base_features) != len(FEATURE_27):
            return
        ts = (timestamp or datetime.now(timezone.utc)).isoformat()
        row = {"timestamp": ts}
        row.update({name: float(val) for name, val in zip(FEATURE_27, base_features)})

        path = self._path(symbol)
        try:
            df = pd.DataFrame([row], columns=HISTORY_COLUMNS)
            if not path.exists():
                df.to_csv(path, index=False)
            else:
                df.to_csv(path, mode="a", header=False, index=False)
        except Exception as e:
            logger.error(f"[FEATURE_HISTORY] append failed for {symbol}: {e}")

    def get_sequence(self, symbol: str, before: datetime, length: int = SEQUENCE_LENGTH) -> np.ndarray:
        """
        Return the last `length` feature snapshots strictly before `before`,
        as a (length, 27) array. Returns None if insufficient history.
        """
        path = self._path(symbol)
        if not path.exists():
            return None
        try:
            df = pd.read_csv(path)
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            before_ts = pd.Timestamp(before)
            if before_ts.tzinfo is None:
                before_ts = before_ts.tz_localize(timezone.utc)
            else:
                before_ts = before_ts.tz_convert(timezone.utc)
            df = df[df["timestamp"] < before_ts]
            if len(df) < length:
                return None
            tail = df.tail(length)
            return tail[FEATURE_27].to_numpy(dtype=np.float32)
        except Exception as e:
            logger.error(f"[FEATURE_HISTORY] get_sequence failed for {symbol}: {e}")
            return None

```

---

## `core/exit_logic.py`

```py
"""
Shared Exit Logic
==================
Pure-Python port of the position-management logic in
ea/BridgeEA_FTMO_v1.mq5 (`ManagePositions()`, ~lines 757-867,
"from v2.29-2.31").

This is the single source of truth for break-even, partial-TP,
regime-adaptive trailing, and progressive-trailing behavior. It is
used by:
  - live_trading_system.py (reading EA-confirmed position state — kept
    behavior-preserving)
  - core/trade_outcome_simulator.py (tick replay, to label simulated
    trades exactly as the live EA would manage them)

All functions are pure (no I/O, no MT5 calls) and operate on plain
numbers/strings so they can be unit tested and reused in replay loops.

`direction` is "BUY" or "SELL" throughout.
"""

from dataclasses import dataclass, field
from typing import Optional


# ----------------------------------------------------------------------
# Regime-adaptive trail multiplier
# ----------------------------------------------------------------------

def compute_regime_trail_multiplier(
    atr: float,
    pip: float,
    enable_regime_trailing: bool,
    trail_atr_multiplier: float,
    trail_atr_ranging: float,
    trail_atr_trending: float,
    trail_atr_volatile: float,
    regime_atr_low_threshold: float,
    regime_atr_high_threshold: float,
) -> float:
    """Mirror of the 'Regime-adaptive trail multiplier' block (~lines 780-787)."""
    trail_mult = trail_atr_multiplier
    if enable_regime_trailing and atr > 0 and pip > 0:
        atr_pips = atr / pip
        if atr_pips < regime_atr_low_threshold:
            trail_mult = trail_atr_ranging
        elif atr_pips > regime_atr_high_threshold:
            trail_mult = trail_atr_volatile
        else:
            trail_mult = trail_atr_trending
    return trail_mult


# ----------------------------------------------------------------------
# RR calculation
# ----------------------------------------------------------------------

def compute_rr_now(entry: float, sl: float, current: float, direction: str) -> Optional[float]:
    """Mirror of the rr_now calc (~lines 789-793). Returns None if sl/entry invalid."""
    if sl <= 0 or entry <= 0:
        return None
    risk_dist = abs(entry - sl)
    if risk_dist <= 0:
        return None
    if direction == "BUY":
        profit_dist = current - entry
    else:
        profit_dist = entry - current
    return profit_dist / risk_dist


# ----------------------------------------------------------------------
# Progressive trailing modifier
# ----------------------------------------------------------------------

def compute_progressive_trail_modifier(
    rr_now: float,
    enable_progressive_trail: bool,
    progtrail_tier1_rr: float,
    progtrail_tier2_rr: float,
    progtrail_tier3_rr: float,
    progtrail_mult_tier1: float,
    progtrail_mult_tier2: float,
    progtrail_mult_tier3: float,
) -> float:
    """Mirror of the 'Progressive trailing modifier' block (~lines 796-802)."""
    prog_mod = 1.0
    if enable_progressive_trail:
        if rr_now >= progtrail_tier3_rr:
            prog_mod = progtrail_mult_tier3
        elif rr_now >= progtrail_tier2_rr:
            prog_mod = progtrail_mult_tier2
        elif rr_now >= progtrail_tier1_rr:
            prog_mod = progtrail_mult_tier1
    return prog_mod


# ----------------------------------------------------------------------
# Partial TP
# ----------------------------------------------------------------------

@dataclass
class PartialTPResult:
    triggered: bool
    close_volume: Optional[float] = None
    new_tp: Optional[float] = None
    new_sl: Optional[float] = None  # BE-buffer SL applied alongside partial TP


def check_partial_tp(
    rr_now: float,
    entry: float,
    sl: float,
    direction: str,
    vol: float,
    pip: float,
    already_taken: bool,
    enable_partial_tp: bool,
    partial_tp_trigger_rr: float,
    partial_tp_close_percent: float,
    partial_tp_extend_rr: float,
    be_buffer_pips: float,
    volume_min: float = 0.01,
) -> PartialTPResult:
    """
    Mirror of the 'Partial TP' block (~lines 805-829).

    risk_dist is recomputed from entry/sl (same as rr_now's denominator).
    """
    if not enable_partial_tp or already_taken or rr_now < partial_tp_trigger_rr:
        return PartialTPResult(triggered=False)

    risk_dist = abs(entry - sl)

    close_vol = round(vol * (partial_tp_close_percent / 100.0), 2)
    close_vol = max(close_vol, volume_min)

    if direction == "BUY":
        new_tp = entry + risk_dist * partial_tp_extend_rr
        be_sl = entry + be_buffer_pips * pip
    else:
        new_tp = entry - risk_dist * partial_tp_extend_rr
        be_sl = entry - be_buffer_pips * pip

    return PartialTPResult(
        triggered=True,
        close_volume=close_vol,
        new_tp=new_tp,
        new_sl=be_sl,
    )


# ----------------------------------------------------------------------
# Break-even trigger
# ----------------------------------------------------------------------

def check_breakeven_trigger(
    rr_now: float,
    entry: float,
    sl: float,
    direction: str,
    bid_now: float,
    ask_now: float,
    pip: float,
    enable_breakeven: bool,
    be_trigger_rr: float,
    be_buffer_pips: float,
) -> Optional[float]:
    """
    Mirror of the 'Break-even' block (~lines 836-849).

    Returns the new SL if BE should be applied, else None.
    """
    if not enable_breakeven or rr_now < be_trigger_rr:
        return None

    if direction == "BUY":
        be_sl = entry + be_buffer_pips * pip
        needs = sl < be_sl
        valid_be = be_sl < bid_now
    else:
        be_sl = entry - be_buffer_pips * pip
        needs = sl > be_sl
        valid_be = be_sl > ask_now

    if needs and valid_be:
        return be_sl
    return None


# ----------------------------------------------------------------------
# Trailing stop
# ----------------------------------------------------------------------

def compute_trailing_stop(
    rr_now: float,
    current: float,
    sl: float,
    direction: str,
    bid_now: float,
    ask_now: float,
    eff_trail: float,
    pip: float,
    enable_trailing: bool,
) -> Optional[float]:
    """
    Mirror of the 'Trailing stop' block (~lines 852-865).

    `eff_trail` = atr * trail_mult * prog_mod (computed by the caller via
    compute_regime_trail_multiplier / compute_progressive_trail_modifier).

    Returns the new SL if trailing should be applied, else None.
    """
    if not enable_trailing or rr_now <= 0:
        return None

    if direction == "BUY":
        new_sl = current - eff_trail
        trail_ok = new_sl > sl + pip
        valid_sl = new_sl < bid_now
    else:
        new_sl = current + eff_trail
        trail_ok = (new_sl < sl - pip) and (sl > 0)
        valid_sl = new_sl > ask_now

    if trail_ok and valid_sl:
        return new_sl
    return None


# ----------------------------------------------------------------------
# Convenience: default EA parameter set (from ea/BridgeEA_FTMO_v1.mq5 inputs)
# ----------------------------------------------------------------------

@dataclass
class ExitParams:
    """Default values mirror the EA's input parameters."""
    enable_breakeven: bool = True
    be_trigger_rr: float = 0.25
    be_buffer_pips: float = 2.0

    enable_trailing: bool = True
    trail_atr_multiplier: float = 2.0

    enable_regime_trailing: bool = True
    trail_atr_ranging: float = 1.5
    trail_atr_trending: float = 2.5
    trail_atr_volatile: float = 3.5
    regime_atr_low_threshold: float = 15.0
    regime_atr_high_threshold: float = 40.0

    enable_partial_tp: bool = True
    partial_tp_trigger_rr: float = 2.0
    partial_tp_close_percent: float = 50.0
    partial_tp_extend_rr: float = 3.0

    enable_progressive_trail: bool = True
    progtrail_tier1_rr: float = 1.0
    progtrail_tier2_rr: float = 1.5
    progtrail_tier3_rr: float = 2.0
    progtrail_mult_tier1: float = 0.9
    progtrail_mult_tier2: float = 0.75
    progtrail_mult_tier3: float = 0.5


@dataclass
class PositionState:
    """Mutable state tracked across a tick-replay loop for one simulated trade."""
    entry: float
    sl: float
    tp: float
    direction: str  # "BUY" | "SELL"
    vol: float = 0.01
    partial_tp_taken: bool = False
    mfe_pips: float = 0.0
    mae_pips: float = 0.0


def step_position(
    state: PositionState,
    current: float,
    bid_now: float,
    ask_now: float,
    atr: float,
    pip: float,
    params: ExitParams = field(default_factory=ExitParams),
) -> PositionState:
    """
    Advance `state` by one tick/bar of price `current`.

    Applies, in EA order: regime trail mult -> rr_now -> progressive
    trail modifier -> partial TP -> break-even -> trailing stop.
    Updates MFE/MAE (in pips) along the way. Mutates and returns `state`.

    Caller is responsible for detecting SL/TP hits separately (this
    function only adjusts sl/tp/partial_tp_taken).
    """
    rr_now = compute_rr_now(state.entry, state.sl, current, state.direction)
    if rr_now is None:
        return state

    # MFE/MAE tracking
    if state.direction == "BUY":
        excursion_pips = (current - state.entry) / pip if pip > 0 else 0.0
    else:
        excursion_pips = (state.entry - current) / pip if pip > 0 else 0.0

    if excursion_pips > state.mfe_pips:
        state.mfe_pips = excursion_pips
    if excursion_pips < -state.mae_pips:
        state.mae_pips = -excursion_pips

    trail_mult = compute_regime_trail_multiplier(
        atr, pip,
        params.enable_regime_trailing,
        params.trail_atr_multiplier,
        params.trail_atr_ranging,
        params.trail_atr_trending,
        params.trail_atr_volatile,
        params.regime_atr_low_threshold,
        params.regime_atr_high_threshold,
    )

    prog_mod = compute_progressive_trail_modifier(
        rr_now,
        params.enable_progressive_trail,
        params.progtrail_tier1_rr,
        params.progtrail_tier2_rr,
        params.progtrail_tier3_rr,
        params.progtrail_mult_tier1,
        params.progtrail_mult_tier2,
        params.progtrail_mult_tier3,
    )

    eff_trail = atr * trail_mult * prog_mod

    partial = check_partial_tp(
        rr_now, state.entry, state.sl, state.direction, state.vol, pip,
        state.partial_tp_taken,
        params.enable_partial_tp,
        params.partial_tp_trigger_rr,
        params.partial_tp_close_percent,
        params.partial_tp_extend_rr,
        params.be_buffer_pips,
    )
    if partial.triggered:
        state.partial_tp_taken = True
        state.vol = max(state.vol - partial.close_volume, 0.0)
        state.tp = partial.new_tp
        state.sl = partial.new_sl
        return state  # EA `continue`s after partial TP — skip BE/trail this step

    be_sl = check_breakeven_trigger(
        rr_now, state.entry, state.sl, state.direction, bid_now, ask_now, pip,
        params.enable_breakeven,
        params.be_trigger_rr,
        params.be_buffer_pips,
    )
    if be_sl is not None:
        state.sl = be_sl

    new_sl = compute_trailing_stop(
        rr_now, current, state.sl, state.direction, bid_now, ask_now,
        eff_trail, pip,
        params.enable_trailing,
    )
    if new_sl is not None:
        state.sl = new_sl

    return state

```

---

## `core/symbol_manager.py`

```py
"""
Dynamic symbol discovery for FTMO MT5 account.
Queries all available symbols, filters to tradeable, categorizes,
and identifies which have pretrained XGBoost models.
"""

import os
import json
import logging
from pathlib import Path

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

logger = logging.getLogger(__name__)

PRETRAINED_BASES = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD", "EURGBP"]

SUFFIX_STRIP_PATTERNS = [".i", "_SB", ".r", "_raw", ".a", ".b", ".c", ".m", ".pro"]

CATEGORY_RULES = {
    "major":  ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD", "USDJPY"],
    "metals": ["XAUUSD", "XAGUSD", "XPTUSD", "XPDUSD", "GOLD", "SILVER"],
    "crypto": ["BTC", "ETH", "LTC", "XRP", "BNB"],
    "index":  ["US30", "US500", "NAS100", "UK100", "GER40", "JPN225", "AUS200", "SPX", "NDX", "DAX"],
    "energy": ["XTIUSD", "XBRUSD", "USOIL", "UKOIL", "NGAS"],
}

MAJOR_CURRENCIES = {"USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD"}


def strip_suffix(symbol: str) -> str:
    """Strip known FTMO broker suffixes to get the base symbol name."""
    base = symbol
    for suffix in SUFFIX_STRIP_PATTERNS:
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    return base.upper()


def categorize_symbol(symbol: str) -> str:
    base = strip_suffix(symbol).upper()
    for category, patterns in CATEGORY_RULES.items():
        if any(base.startswith(p) or base == p for p in patterns):
            return category
    if len(base) == 6:
        quote = base[3:]
        base3 = base[:3]
        if base3 in MAJOR_CURRENCIES and quote in MAJOR_CURRENCIES:
            return "major"
        if base3 in MAJOR_CURRENCIES or quote in MAJOR_CURRENCIES:
            return "minor"
        return "exotic"
    return "other"


def find_model_file(base_symbol: str, model_dir: str) -> str | None:
    """Return model filepath if a pretrained XGBoost model exists for this base symbol."""
    candidates = [
        f"{base_symbol}_xgboost_CLEAN27.joblib",
        f"{base_symbol}_xgboost.joblib",
    ]
    for name in candidates:
        path = os.path.join(model_dir, name)
        if os.path.exists(path):
            return path
    return None


class SymbolManager:
    def __init__(self, model_dir: str, config: dict | None = None):
        self.model_dir = model_dir
        self.config = config or {}
        self.all_symbols: list[str] = []
        self.symbols_with_models: list[str] = []
        self.symbols_without_models: list[str] = []
        self.symbol_categories: dict[str, str] = {}
        self.symbol_model_paths: dict[str, str] = {}

    def connect_mt5(self, login: int = 0, password: str = "", server: str = "") -> bool:
        if not MT5_AVAILABLE:
            logger.error("MetaTrader5 package not installed")
            return False
        if not mt5.initialize():
            logger.error(f"MT5 initialize failed: {mt5.last_error()}")
            return False
        if login and password and server:
            if not mt5.login(login, password=password, server=server):
                logger.error(f"MT5 login failed: {mt5.last_error()}")
                mt5.shutdown()
                return False
        logger.info("MT5 connected successfully")
        return True

    def discover(self) -> dict:
        """
        Main entry point. Returns dict with:
          symbols_with_models, symbols_without_models, categories, model_paths
        """
        if MT5_AVAILABLE:
            self._discover_from_mt5()
        else:
            logger.warning("MT5 not available — using model directory to infer symbol list")
            self._discover_from_models_only()

        self._classify_by_model()
        self._log_summary()
        return {
            "all_symbols": self.all_symbols,
            "symbols_with_models": self.symbols_with_models,
            "symbols_without_models": self.symbols_without_models,
            "categories": self.symbol_categories,
            "model_paths": self.symbol_model_paths,
        }

    def _discover_from_mt5(self):
        symbols_info = mt5.symbols_get()
        if not symbols_info:
            logger.warning("mt5.symbols_get() returned nothing — falling back to feature file discovery")
            self._discover_from_models_only()
            return

        tradeable = []
        for s in symbols_info:
            name = s.name
            if not name:
                continue
            if "#" in name:   # skip synthetic/index-only instruments
                continue
            tradeable.append(name)

        self.all_symbols = sorted(tradeable)
        logger.info(f"MT5 returned {len(symbols_info)} symbols; {len(tradeable)} tradeable")

    def _discover_from_models_only(self):
        """
        Fallback when MT5 API is unavailable.
        Scans Common\\Files for existing feature CSVs written by the Bridge EA,
        then falls back to the 8 pretrained bases if none found.
        """
        common_files = r"C:\Users\mt5-admin\AppData\Roaming\MetaQuotes\Terminal\Common\Files"
        import glob, os
        pattern = os.path.join(common_files, "*_features.csv")
        found = []
        for path in glob.glob(pattern):
            name = os.path.basename(path)
            symbol = name.replace("_features.csv", "")
            if symbol:
                found.append(symbol)

        if found:
            self.all_symbols = sorted(found)
            logger.info(f"Discovered {len(found)} symbols from feature CSVs (MT5 API unavailable)")
        else:
            self.all_symbols = list(PRETRAINED_BASES)
            logger.info("No feature CSVs found — using 8 pretrained base symbols")

    def _classify_by_model(self):
        for symbol in self.all_symbols:
            base = strip_suffix(symbol)
            self.symbol_categories[symbol] = categorize_symbol(symbol)
            model_path = find_model_file(base, self.model_dir)
            if model_path:
                self.symbols_with_models.append(symbol)
                self.symbol_model_paths[symbol] = model_path
            else:
                self.symbols_without_models.append(symbol)

    def _log_summary(self):
        total = len(self.all_symbols)
        with_m = len(self.symbols_with_models)
        without_m = len(self.symbols_without_models)
        logger.info(f"Symbol discovery complete: {total} total | {with_m} with ML models | {without_m} rule-based only")
        if self.symbols_with_models:
            logger.info(f"  ML symbols : {self.symbols_with_models}")
        cat_counts = {}
        for cat in self.symbol_categories.values():
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
        logger.info(f"  Categories : {cat_counts}")

    def has_model(self, symbol: str) -> bool:
        return symbol in self.symbol_model_paths

    def get_model_path(self, symbol: str) -> str | None:
        return self.symbol_model_paths.get(symbol)

    def get_base_symbol(self, symbol: str) -> str:
        return strip_suffix(symbol)

    def shutdown_mt5(self):
        if MT5_AVAILABLE:
            mt5.shutdown()


def load_symbol_manager(config_path: str | None = None) -> SymbolManager:
    """Convenience factory: loads config and returns a ready SymbolManager."""
    config = {}
    if config_path and os.path.exists(config_path):
        with open(config_path, "r") as f:
            full = json.load(f)
        config = full.get("symbols", {})
        model_dir = full.get("ml", {}).get("model_dir", "data/models")
    else:
        model_dir = "data/models"

    base_dir = Path(__file__).parent.parent
    model_dir_abs = str(base_dir / model_dir)

    return SymbolManager(model_dir=model_dir_abs, config=config)

```

---

## `core/unified_trade_logger.py`

```py
"""
Unified Trade Logger
=====================
One master CSV capturing every signal from every source with full context.
One row per (symbol, source, signal) — updated when trade executes and closes.

Columns:
  trade_id | timestamp | symbol | signal_source | source_type | action |
  confidence | confluence_score | dimension_votes | danger_score |
  strategy_votes | close | rsi | atr | momentum | volatility |
  would_execute | actually_executed |
  entry_price | sl | tp | lot |
  exit_time | exit_price | outcome | profit_pips | profit_usd
"""

import os
import uuid
import logging
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

COLUMNS = [
    "trade_id", "timestamp", "symbol", "signal_source", "source_type", "action",
    # ML/gate context
    "confidence", "confluence_score", "dimension_votes", "dimension_count",
    "danger_score", "strategy_votes",
    # Key indicators at signal time
    "close", "rsi", "atr", "momentum", "volatility",
    # Execution flags
    "would_execute", "actually_executed",
    # Order details
    "entry_price", "sl", "tp", "lot",
    # Outcome (filled when trade closes)
    "exit_time", "exit_price", "outcome", "profit_pips", "profit_usd",
    # Outcome detail (filled by trade_outcome_simulator)
    "exit_reason", "mfe_pips", "mae_pips", "trade_duration_minutes", "label_quality",
]


def make_trade_id(symbol: str, source: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    sym = symbol.replace(".sim", "").replace(".", "")[:6]
    src = source[:8]
    return f"{ts}_{sym}_{src}"


class UnifiedTradeLogger:
    """
    Append-only logger for all trade signals and outcomes.
    Thread-safe via file append (each write is atomic at OS level).
    """

    def __init__(self, log_path: str):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._pending: dict[str, dict] = {}  # trade_id -> row dict

        if not self.log_path.exists():
            pd.DataFrame(columns=COLUMNS).to_csv(self.log_path, index=False)
            logger.info(f"[UNIFIED LOG] Created: {self.log_path}")

    # ------------------------------------------------------------------
    # Log a new signal (call when signal is generated, before execution)
    # ------------------------------------------------------------------

    def log_signal(
        self,
        trade_id: str,
        symbol: str,
        signal_source: str,
        source_type: str,
        action: str,
        # gate context (optional — only present for XGBoost signals)
        confidence: float = 0.0,
        confluence_score: float = 0.0,
        dimension_votes: str = "",
        dimension_count: int = 0,
        danger_score: float = 0.0,
        strategy_votes: str = "",
        # indicator snapshot
        close: float = 0.0,
        rsi: float = 0.0,
        atr: float = 0.0,
        momentum: float = 0.0,
        volatility: float = 0.0,
        # execution status
        would_execute: bool = True,
        actually_executed: bool = False,
    ) -> str:
        """Write signal row. Returns trade_id."""
        row = {
            "trade_id":          trade_id,
            "timestamp":         datetime.now(timezone.utc).isoformat(),
            "symbol":            symbol,
            "signal_source":     signal_source,
            "source_type":       source_type,
            "action":            action,
            "confidence":        round(confidence, 4),
            "confluence_score":  round(confluence_score, 4),
            "dimension_votes":   dimension_votes,
            "dimension_count":   dimension_count,
            "danger_score":      round(danger_score, 2),
            "strategy_votes":    strategy_votes,
            "close":             round(close, 6),
            "rsi":               round(rsi, 2),
            "atr":               round(atr, 6),
            "momentum":          round(momentum, 6),
            "volatility":        round(volatility, 4),
            "would_execute":     would_execute,
            "actually_executed": actually_executed,
            "entry_price": "", "sl": "", "tp": "", "lot": "",
            "exit_time": "", "exit_price": "", "outcome": "",
            "profit_pips": "", "profit_usd": "",
            "exit_reason": "", "mfe_pips": "", "mae_pips": "",
            "trade_duration_minutes": "", "label_quality": "",
        }
        self._pending[trade_id] = row
        self._append_row(row)
        return trade_id

    # ------------------------------------------------------------------
    # Update when EA confirms execution
    # ------------------------------------------------------------------

    def log_execution(
        self,
        trade_id: str,
        entry_price: float,
        sl: float,
        tp: float,
        lot: float,
    ):
        """Mark signal as actually executed and fill order details."""
        self._update_row(trade_id, {
            "actually_executed": True,
            "entry_price":       round(entry_price, 6),
            "sl":                round(sl, 6),
            "tp":                round(tp, 6),
            "lot":               round(lot, 2),
        })

    # ------------------------------------------------------------------
    # Update when trade closes
    # ------------------------------------------------------------------

    def log_outcome(
        self,
        trade_id: str,
        exit_price: float,
        outcome: str,       # 'TP' | 'SL' | 'BE' | 'PARTIAL_TP' | 'MANUAL' | 'OPEN'
        profit_pips: float,
        profit_usd: float,
        exit_reason: str = "",
        mfe_pips: float = 0.0,
        mae_pips: float = 0.0,
        trade_duration_minutes: float = 0.0,
        label_quality: str = "",   # 'tick' | 'm1_approx'
        exit_time: Optional[datetime] = None,
    ):
        """Fill outcome columns when trade closes (or finalizes a label)."""
        self._update_row(trade_id, {
            "exit_time":   (exit_time or datetime.now(timezone.utc)).isoformat(),
            "exit_price":  round(exit_price, 6),
            "outcome":     outcome,
            "profit_pips": round(profit_pips, 1),
            "profit_usd":  round(profit_usd, 2),
            "exit_reason": exit_reason,
            "mfe_pips":    round(mfe_pips, 1),
            "mae_pips":    round(mae_pips, 1),
            "trade_duration_minutes": round(trade_duration_minutes, 1),
            "label_quality": label_quality,
        })

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _append_row(self, row: dict):
        try:
            df = pd.DataFrame([row], columns=COLUMNS)
            df.to_csv(self.log_path, mode="a", header=False, index=False)
        except Exception as e:
            logger.error(f"[UNIFIED LOG] Append failed: {e}")

    def _update_row(self, trade_id: str, updates: dict):
        """Update an existing row in-place by rewriting the file."""
        try:
            df = pd.read_csv(self.log_path, dtype=str)
            mask = df["trade_id"] == trade_id
            if not mask.any():
                logger.warning(f"[UNIFIED LOG] trade_id {trade_id} not found for update")
                return
            for col, val in updates.items():
                df.loc[mask, col] = str(val)
            df.to_csv(self.log_path, index=False)
        except Exception as e:
            logger.error(f"[UNIFIED LOG] Update failed for {trade_id}: {e}")

    def get_summary(self) -> dict:
        """Quick stats for logging."""
        try:
            df = pd.read_csv(self.log_path)
            total    = len(df)
            executed = df["actually_executed"].astype(str).str.lower().eq("true").sum()
            closed   = df["outcome"].notna().sum()
            return {"total_signals": total, "executed": executed, "closed": closed}
        except Exception:
            return {}

```

---

## `core/trade_outcome_simulator.py`

```py
"""
Tick-Based Outcome Simulator
=============================
Background loop that turns logged signals (data/unified_trades.csv,
actually_executed=True, outcome=='') into fully labeled training rows
by replaying MT5 tick data (fallback: M1 bars) through the same
break-even / partial-TP / regime-trailing logic the live EA uses
(core/exit_logic.py).

Entry/SL/TP are reconstructed the same way live_trading_system.py
computes them at signal time (~live_trading_system.py lines 792-805):
  SL = entry - 1.5*ATR (BUY) / entry + 1.5*ATR (SELL)
  TP = entry + 3.0*ATR (BUY) / entry - 3.0*ATR (SELL)
using the `close` and `atr` columns already captured in unified_trades.csv.

Run via `run_forever()` in a background thread from run_system.py.
"""

import time
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

from core.exit_logic import ExitParams, PositionState, step_position
from core.unified_trade_logger import UnifiedTradeLogger
from core.feature_history_recorder import FeatureHistoryRecorder, SEQUENCE_LENGTH

TICK_TRAJECTORY_LENGTH = 200

logger = logging.getLogger(__name__)

SL_ATR_MULT = 1.5
TP_ATR_MULT = 3.0
MAX_HOLD_HOURS = 48
POLL_SECONDS = 30
MIN_AGE_SECONDS = 60  # don't replay a signal until at least this old


_INDEX_CRYPTO_KEYWORDS = (
    "US500", "US100", "US30", "UK100", "GER", "GER40", "JP225", "AUS200",
    "FRA40", "EU50", "NAS", "SPX", "DJ30",
    "BTC", "ETH", "LTC", "XRP",
    "OIL", "USOIL", "UKOIL", "NGAS",
)


def _pip_value(symbol: str) -> float:
    """
    Approximate 'pip' size in price units, by symbol category.
    Forex majors/minors: 0.0001 (0.01 for JPY pairs).
    Metals (XAU/XAG): 0.01 (1 pip = $0.01).
    Indices/crypto/energy: 1.0 (1 'pip' = 1 point/dollar) — pip-based
    P&L is not meaningful for these, but this avoids wildly inflated
    profit_pips from applying a forex pip size to a $60,000 BTC move.
    """
    s = symbol.upper()
    if any(k in s for k in _INDEX_CRYPTO_KEYWORDS):
        return 1.0
    if "XAU" in s or "XAG" in s:
        return 0.01
    if "JPY" in s:
        return 0.01
    return 0.0001


class TradeOutcomeSimulator:
    def __init__(self, unified_trades_path: str, exit_params: ExitParams = None):
        self.path = Path(unified_trades_path)
        self.unified_logger = UnifiedTradeLogger(str(self.path))
        self.params = exit_params or ExitParams()
        self._stop = False

        data_dir = self.path.parent
        self.feature_history = FeatureHistoryRecorder(str(data_dir / "feature_history"))
        self.sequences_dir = data_dir / "feature_sequences"
        self.sequences_dir.mkdir(parents=True, exist_ok=True)
        self.tick_trajectories_dir = data_dir / "tick_trajectories"
        self.tick_trajectories_dir.mkdir(parents=True, exist_ok=True)

    def stop(self):
        self._stop = True

    def run_forever(self):
        logger.info("[SIM] Trade outcome simulator started")
        while not self._stop:
            try:
                self.process_pending()
            except Exception as e:
                logger.error(f"[SIM] cycle error: {e}")
            time.sleep(POLL_SECONDS)

    # ------------------------------------------------------------------

    def process_pending(self):
        if not self.path.exists():
            return
        try:
            df = pd.read_csv(self.path, dtype=str)
        except Exception as e:
            logger.error(f"[SIM] read failed: {e}")
            return
        if df.empty:
            return

        mask = (
            df["actually_executed"].astype(str).str.lower().eq("true")
            & df["action"].isin(["BUY", "SELL"])
            & df["outcome"].fillna("").eq("")
        )
        pending = df[mask]
        if pending.empty:
            return

        now = datetime.now(timezone.utc)
        for _, row in pending.iterrows():
            try:
                signal_time = pd.to_datetime(row["timestamp"], utc=True).to_pydatetime()
                if (now - signal_time).total_seconds() < MIN_AGE_SECONDS:
                    continue
                self._process_row(row, signal_time, now)
            except Exception as e:
                logger.error(f"[SIM] failed for {row.get('trade_id')}: {e}")

    def _process_row(self, row, signal_time: datetime, now: datetime):
        trade_id = row["trade_id"]
        symbol = row["symbol"]
        action = row["action"]
        close = float(row["close"])
        atr = float(row["atr"])

        if atr <= 0 or close <= 0:
            return

        pip = _pip_value(symbol)
        entry = close
        if action == "BUY":
            sl = entry - atr * SL_ATR_MULT
            tp = entry + atr * TP_ATR_MULT
        else:
            sl = entry + atr * SL_ATR_MULT
            tp = entry - atr * TP_ATR_MULT

        if str(row.get("entry_price", "")).strip() == "":
            self.unified_logger.log_execution(trade_id, entry, sl, tp, lot=0.01)

        path, label_quality = self._get_price_path(symbol, signal_time, now)
        if not path:
            return  # no data yet — try again next poll

        state = PositionState(entry=entry, sl=sl, tp=tp, direction=action, vol=0.01)
        outcome = None
        exit_price = None
        exit_time = None

        for ts, bid, ask in path:
            current = bid if action == "BUY" else ask

            if action == "BUY":
                if current <= state.sl:
                    outcome = "BE" if abs(state.sl - entry) < pip else "SL"
                    exit_price = state.sl
                    exit_time = ts
                    break
                if current >= state.tp:
                    outcome = "PARTIAL_TP" if state.partial_tp_taken else "TP"
                    exit_price = state.tp
                    exit_time = ts
                    break
            else:
                if current >= state.sl:
                    outcome = "BE" if abs(state.sl - entry) < pip else "SL"
                    exit_price = state.sl
                    exit_time = ts
                    break
                if current <= state.tp:
                    outcome = "PARTIAL_TP" if state.partial_tp_taken else "TP"
                    exit_price = state.tp
                    exit_time = ts
                    break

            state = step_position(state, current, bid, ask, atr, pip, self.params)

        if outcome is None:
            if (now - signal_time) > timedelta(hours=MAX_HOLD_HOURS):
                last_ts, last_bid, last_ask = path[-1]
                exit_price = last_bid if action == "BUY" else last_ask
                exit_time = last_ts
                outcome = "MANUAL"
            else:
                return  # still open — re-check next poll

        if action == "BUY":
            profit_pips = (exit_price - entry) / pip
        else:
            profit_pips = (entry - exit_price) / pip
        profit_usd = profit_pips * pip * 100000 * state.vol

        duration_min = (exit_time - signal_time).total_seconds() / 60.0

        self._write_feature_sequence(trade_id, symbol, signal_time)
        self._write_tick_trajectory(trade_id, path, exit_time)

        self.unified_logger.log_outcome(
            trade_id=trade_id,
            exit_price=exit_price,
            outcome=outcome,
            profit_pips=profit_pips,
            profit_usd=profit_usd,
            exit_reason=outcome,
            mfe_pips=state.mfe_pips,
            mae_pips=state.mae_pips,
            trade_duration_minutes=duration_min,
            label_quality=label_quality,
            exit_time=exit_time,
        )
        logger.info(
            f"[SIM] {trade_id} {symbol} {action} -> {outcome} "
            f"({profit_pips:.1f} pips, {label_quality})"
        )

    # ------------------------------------------------------------------

    def _write_feature_sequence(self, trade_id: str, symbol: str, signal_time: datetime):
        seq = self.feature_history.get_sequence(symbol, before=signal_time, length=SEQUENCE_LENGTH)
        if seq is None:
            return
        try:
            np.save(self.sequences_dir / f"{trade_id}.npy", seq)
        except Exception as e:
            logger.error(f"[SIM] feature sequence save failed for {trade_id}: {e}")

    def _write_tick_trajectory(self, trade_id: str, path: list, exit_time: datetime):
        """Sample (timestamp, bid, ask) path up to exit_time down to a fixed length."""
        trimmed = [p for p in path if p[0] <= exit_time]
        if len(trimmed) < 2:
            return
        try:
            arr = np.array([[p[1], p[2]] for p in trimmed], dtype=np.float32)
            if len(arr) > TICK_TRAJECTORY_LENGTH:
                idx = np.linspace(0, len(arr) - 1, TICK_TRAJECTORY_LENGTH).astype(int)
                arr = arr[idx]
            np.save(self.tick_trajectories_dir / f"{trade_id}.npy", arr)
        except Exception as e:
            logger.error(f"[SIM] tick trajectory save failed for {trade_id}: {e}")

    # ------------------------------------------------------------------

    def _get_price_path(self, symbol: str, start: datetime, end: datetime):
        """Return (list of (timestamp, bid, ask), label_quality) or (None, '')."""
        if mt5 is None:
            return None, ""

        ticks = mt5.copy_ticks_range(symbol, start, end, mt5.COPY_TICKS_ALL)
        if ticks is not None and len(ticks) > 0:
            path = []
            for t in ticks:
                bid = float(t["bid"])
                ask = float(t["ask"])
                if bid > 0 and ask > 0:
                    path.append((datetime.fromtimestamp(t["time"], tz=timezone.utc), bid, ask))
            if path:
                return path, "tick"

        rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M1, start, end)
        if rates is not None and len(rates) > 0:
            path = []
            for r in rates:
                ts = datetime.fromtimestamp(r["time"], tz=timezone.utc)
                for price in (r["open"], r["high"], r["low"], r["close"]):
                    p = float(price)
                    path.append((ts, p, p))
            if path:
                return path, "m1_approx"

        return None, ""

```

---

## `core/rule_based_strategies.py`

```py
"""
Rule-Based Trading Strategies V1.0
====================================
9 rule-based strategies covering various market conditions
Uses the 10 critical features from feature importance test

Author: AI Trading System
Version: 1.0
Date: 2025-11-03
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple


class RuleBasedStrategies:
    """
    9 Rule-Based Trading Strategies
    Each strategy returns: 'BUY', 'SELL', or 'HOLD'
    """
    
    def __init__(self):
        """Initialize strategy parameters"""
        
        # Strategy names for reference
        self.strategy_names = [
            'volume_breakout',
            'currency_strength_divergence',
            'volatility_breakout',
            'trend_following',
            'mean_reversion',
            'volatility_contraction',
            'currency_correlation',
            'low_volatility_momentum',
            'high_volatility_reversal'
        ]
        
        # Thresholds (can be tuned based on backtesting)
        self.thresholds = {
            'volume_high': 1.5,      # Volume > 1.5x average = breakout
            'volume_low': 0.5,       # Volume < 0.5x average = low volume
            'strength_strong': 0.6,  # Currency strength > 0.6 = strong
            'strength_weak': 0.4,    # Currency strength < 0.4 = weak
            'volatility_high': 1.5,  # Volatility > 1.5x average = high
            'volatility_low': 0.5,   # Volatility < 0.5x average = low
            'atr_high': 1.2,         # ATR > 1.2x average = high
            'atr_low': 0.8,          # ATR < 0.8x average = low
            'returns_high': 0.02,    # Returns > 2% = strong trend
            'returns_low': 0.005     # Returns < 0.5% = weak trend
        }
    
    def _extract_features(self, features: np.ndarray) -> Dict[str, float]:
        """
        Extract the 10 critical features from feature array
        
        Args:
            features: numpy array of 10 features (in order from feature test)
            
        Returns:
            Dictionary with named features
        """
        if len(features) < 10:
            raise ValueError(f"Expected 10 features, got {len(features)}")
        
        return {
            'volume_sma': features[0],
            'eur_strength': features[1],
            'gbp_strength': features[2],
            'nzd_strength': features[3],
            'usd_strength': features[4],
            'jpy_strength': features[5],
            'volatility': features[6],
            'returns_std': features[7],
            'volatility_confirm': features[8],
            'atr': features[9]
        }
    
    def _get_currency_strength(self, pair: str, features: Dict[str, float]) -> Tuple[float, float]:
        """
        Get base and quote currency strength for a pair
        
        Args:
            pair: Currency pair (e.g., 'EURUSD.sim')
            features: Dictionary of features
            
        Returns:
            (base_strength, quote_strength)
        """
        # Remove .sim suffix if present
        pair_clean = pair.replace('.sim', '')
        
        # Extract base and quote currencies
        base = pair_clean[:3]  # First 3 chars (EUR, GBP, etc.)
        quote = pair_clean[3:6]  # Next 3 chars (USD, JPY, etc.)
        
        # Map to feature names
        strength_map = {
            'EUR': 'eur_strength',
            'GBP': 'gbp_strength',
            'NZD': 'nzd_strength',
            'USD': 'usd_strength',
            'JPY': 'jpy_strength'
        }
        
        base_strength = features.get(strength_map.get(base, ''), 0.5)
        quote_strength = features.get(strength_map.get(quote, ''), 0.5)
        
        return base_strength, quote_strength
    
    # ==================== STRATEGY 1: VOLUME BREAKOUT ====================
    
    def volume_breakout(self, pair: str, features: np.ndarray) -> str:
        """
        Strategy 1: Volume Breakout
        BUY when volume spikes high (breakout potential)
        SELL when volume spikes with weakness
        
        Logic:
        - High volume (>1.5x) + strong base currency = BUY
        - High volume (>1.5x) + weak base currency = SELL
        - Otherwise HOLD
        """
        feat = self._extract_features(features)
        base_strength, quote_strength = self._get_currency_strength(pair, feat)
        
        volume = feat['volume_sma']
        
        # High volume breakout
        if volume > self.thresholds['volume_high']:
            if base_strength > self.thresholds['strength_strong']:
                return 'BUY'
            elif base_strength < self.thresholds['strength_weak']:
                return 'SELL'
        
        return 'HOLD'
    
    # ==================== STRATEGY 2: CURRENCY STRENGTH DIVERGENCE ====================
    
    def currency_strength_divergence(self, pair: str, features: np.ndarray) -> str:
        """
        Strategy 2: Currency Strength Divergence
        BUY when base currency much stronger than quote
        SELL when quote currency much stronger than base
        
        Logic:
        - Base strength > 0.6 AND Quote strength < 0.4 = BUY
        - Base strength < 0.4 AND Quote strength > 0.6 = SELL
        - Otherwise HOLD
        """
        feat = self._extract_features(features)
        base_strength, quote_strength = self._get_currency_strength(pair, feat)
        
        strength_diff = base_strength - quote_strength
        
        # Strong divergence
        if strength_diff > 0.2:  # Base much stronger
            return 'BUY'
        elif strength_diff < -0.2:  # Quote much stronger
            return 'SELL'
        
        return 'HOLD'
    
    # ==================== STRATEGY 3: VOLATILITY BREAKOUT ====================
    
    def volatility_breakout(self, pair: str, features: np.ndarray) -> str:
        """
        Strategy 3: Volatility Breakout
        BUY on volatility expansion with positive momentum
        SELL on volatility expansion with negative momentum
        
        Logic:
        - High volatility + high returns = BUY (trend acceleration)
        - High volatility + negative returns = SELL (breakdown)
        - Otherwise HOLD
        """
        feat = self._extract_features(features)
        
        volatility = feat['volatility']
        returns = feat['returns_std']
        
        # High volatility environment
        if volatility > self.thresholds['volatility_high']:
            if returns > self.thresholds['returns_high']:
                return 'BUY'
            elif returns < -self.thresholds['returns_high']:
                return 'SELL'
        
        return 'HOLD'
    
    # ==================== STRATEGY 4: TREND FOLLOWING ====================
    
    def trend_following(self, pair: str, features: np.ndarray) -> str:
        """
        Strategy 4: Trend Following
        BUY on strong uptrend (high returns + high ATR)
        SELL on strong downtrend (negative returns + high ATR)
        
        Logic:
        - High returns + high ATR = BUY (strong uptrend)
        - Negative returns + high ATR = SELL (strong downtrend)
        - Otherwise HOLD
        """
        feat = self._extract_features(features)
        
        returns = feat['returns_std']
        atr = feat['atr']
        
        # Strong trend conditions
        if atr > self.thresholds['atr_high']:
            if returns > self.thresholds['returns_high']:
                return 'BUY'
            elif returns < -self.thresholds['returns_high']:
                return 'SELL'
        
        return 'HOLD'
    
    # ==================== STRATEGY 5: MEAN REVERSION ====================
    
    def mean_reversion(self, pair: str, features: np.ndarray) -> str:
        """
        Strategy 5: Mean Reversion
        BUY when oversold (low volatility + negative returns)
        SELL when overbought (low volatility + high returns)
        
        Logic:
        - Low volatility + negative returns = BUY (oversold)
        - Low volatility + high returns = SELL (overbought)
        - Otherwise HOLD
        """
        feat = self._extract_features(features)
        
        volatility = feat['volatility']
        returns = feat['returns_std']
        
        # Low volatility environment (ranging)
        if volatility < self.thresholds['volatility_low']:
            if returns < -self.thresholds['returns_low']:
                return 'BUY'  # Oversold
            elif returns > self.thresholds['returns_low']:
                return 'SELL'  # Overbought
        
        return 'HOLD'
    
    # ==================== STRATEGY 6: VOLATILITY CONTRACTION ====================
    
    def volatility_contraction(self, pair: str, features: np.ndarray) -> str:
        """
        Strategy 6: Volatility Contraction
        BUY when volatility contracts with bullish confirmation
        SELL when volatility contracts with bearish confirmation
        
        Logic:
        - Low volatility + volatility_confirm > 1.0 = BUY (coiling for upside)
        - Low volatility + volatility_confirm < -1.0 = SELL (coiling for downside)
        - Otherwise HOLD
        """
        feat = self._extract_features(features)
        
        volatility = feat['volatility']
        vol_confirm = feat['volatility_confirm']
        
        # Volatility contraction
        if volatility < self.thresholds['volatility_low']:
            if vol_confirm > 1.0:
                return 'BUY'
            elif vol_confirm < -1.0:
                return 'SELL'
        
        return 'HOLD'
    
    # ==================== STRATEGY 7: CURRENCY CORRELATION ====================
    
    def currency_correlation(self, pair: str, features: np.ndarray) -> str:
        """
        Strategy 7: Currency Correlation
        BUY when both base and quote align bullish
        SELL when both base and quote align bearish
        
        Logic:
        - Base strong + Quote weak + returns positive = BUY
        - Base weak + Quote strong + returns negative = SELL
        - Otherwise HOLD
        """
        feat = self._extract_features(features)
        base_strength, quote_strength = self._get_currency_strength(pair, feat)
        returns = feat['returns_std']
        
        # All indicators align
        if base_strength > 0.55 and quote_strength < 0.45 and returns > 0:
            return 'BUY'
        elif base_strength < 0.45 and quote_strength > 0.55 and returns < 0:
            return 'SELL'
        
        return 'HOLD'
    
    # ==================== STRATEGY 8: LOW VOLATILITY MOMENTUM ====================
    
    def low_volatility_momentum(self, pair: str, features: np.ndarray) -> str:
        """
        Strategy 8: Low Volatility Momentum
        BUY on quiet accumulation (low vol + volume increase + positive returns)
        SELL on quiet distribution (low vol + volume increase + negative returns)
        
        Logic:
        - Low volatility + high volume + positive returns = BUY
        - Low volatility + high volume + negative returns = SELL
        - Otherwise HOLD
        """
        feat = self._extract_features(features)
        
        volatility = feat['volatility']
        volume = feat['volume_sma']
        returns = feat['returns_std']
        
        # Quiet accumulation/distribution
        if volatility < self.thresholds['volatility_low'] and volume > 1.2:
            if returns > self.thresholds['returns_low']:
                return 'BUY'
            elif returns < -self.thresholds['returns_low']:
                return 'SELL'
        
        return 'HOLD'
    
    # ==================== STRATEGY 9: HIGH VOLATILITY REVERSAL ====================
    
    def high_volatility_reversal(self, pair: str, features: np.ndarray) -> str:
        """
        Strategy 9: High Volatility Reversal
        BUY when volatility spikes but shows bullish reversal signs
        SELL when volatility spikes but shows bearish reversal signs
        
        Logic:
        - High ATR + volatility_confirm positive = BUY (reversal up)
        - High ATR + volatility_confirm negative = SELL (reversal down)
        - Otherwise HOLD
        """
        feat = self._extract_features(features)
        
        atr = feat['atr']
        vol_confirm = feat['volatility_confirm']
        
        # High volatility reversal
        if atr > self.thresholds['atr_high']:
            if vol_confirm > 0.5:
                return 'BUY'
            elif vol_confirm < -0.5:
                return 'SELL'
        
        return 'HOLD'
    
    # ==================== REGIME DETECTION ====================
    
    def detect_regime(self, features: np.ndarray) -> str:
        """
        Detect current market regime based on features
        
        Args:
            features: numpy array of 10 features
            
        Returns:
            str: 'trending', 'ranging', or 'volatile'
        """
        # Extract key features
        volume_sma = features[0]
        volatility = features[6]
        returns_std = features[7]
        atr = features[9]
        
        # High volatility regime (breakouts, rapid moves)
        if volatility > self.thresholds['volatility_high'] or atr > self.thresholds['atr_high']:
            return 'volatile'
        
        # Trending regime (sustained directional movement)
        elif abs(returns_std) > self.thresholds['returns_high'] and volatility > self.thresholds['volatility_low']:
            return 'trending'
        
        # Ranging regime (low volatility, mean-reverting)
        else:
            return 'ranging'
    
    def get_regime_strategies(self, regime: str) -> List[str]:
        """
        Get strategies appropriate for current market regime
        
        Args:
            regime: 'trending', 'ranging', or 'volatile'
            
        Returns:
            List of strategy names for that regime
        """
        regime_map = {
            'trending': [
                'trend_following',
                'currency_strength_divergence', 
                'currency_correlation'
            ],
            'ranging': [
                'mean_reversion',
                'low_volatility_momentum',
                'volatility_contraction'
            ],
            'volatile': [
                'volume_breakout',
                'volatility_breakout',
                'high_volatility_reversal'
            ]
        }
        
        return regime_map.get(regime, [])
    
    def check_strategy_agreement(self, pair: str, features: np.ndarray, 
                                ml_prediction: str) -> Dict[str, any]:
        """
        Check 2-of-3 regime-appropriate strategy agreement
        
        Args:
            pair: Currency pair
            features: Feature array
            ml_prediction: ML model prediction ('BUY', 'SELL', 'HOLD')
            
        Returns:
            dict: {
                'passes': bool,
                'regime': str,
                'relevant_strategies': list,
                'strategy_votes': dict,
                'agreement_count': int,
                'reason': str
            }
        """
        # Get all strategy predictions
        all_predictions = self.predict_all(pair, features)
        
        # Detect current regime
        regime = self.detect_regime(features)
        
        # Get regime-appropriate strategies
        relevant_strategies = self.get_regime_strategies(regime)
        
        # Count votes from relevant strategies only
        regime_votes = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
        strategy_details = {}
        
        for strategy in relevant_strategies:
            if strategy in all_predictions:
                prediction = all_predictions[strategy]
                regime_votes[prediction] += 1
                strategy_details[strategy] = prediction
        
        # Check if ML prediction has 1+ supporting votes
        ml_support_count = regime_votes.get(ml_prediction, 0)
        
        # Result
        if ml_support_count >= 1:
            return {
                'passes': True,
                'regime': regime,
                'relevant_strategies': relevant_strategies,
                'strategy_votes': strategy_details,
                'agreement_count': ml_support_count,
                'reason': f'{ml_support_count} of {len(relevant_strategies)} {regime} strategies agree with ML {ml_prediction}'
            }
        else:
            return {
                'passes': False,
                'regime': regime,
                'relevant_strategies': relevant_strategies,
                'strategy_votes': strategy_details,
                'agreement_count': ml_support_count,
                'reason': f'Only {ml_support_count} of {len(relevant_strategies)} {regime} strategies agree with ML {ml_prediction}'
            }
    
    # ==================== MAIN PREDICTION METHOD ====================
    
    def predict_all(self, pair: str, features: np.ndarray) -> Dict[str, str]:
        """
        Run all 9 strategies and return their predictions
        
        Args:
            pair: Currency pair (e.g., 'EURUSD.sim')
            features: numpy array of 10 features
            
        Returns:
            Dictionary of {strategy_name: prediction}
        """
        predictions = {}
        
        predictions['volume_breakout'] = self.volume_breakout(pair, features)
        predictions['currency_strength_divergence'] = self.currency_strength_divergence(pair, features)
        predictions['volatility_breakout'] = self.volatility_breakout(pair, features)
        predictions['trend_following'] = self.trend_following(pair, features)
        predictions['mean_reversion'] = self.mean_reversion(pair, features)
        predictions['volatility_contraction'] = self.volatility_contraction(pair, features)
        predictions['currency_correlation'] = self.currency_correlation(pair, features)
        predictions['low_volatility_momentum'] = self.low_volatility_momentum(pair, features)
        predictions['high_volatility_reversal'] = self.high_volatility_reversal(pair, features)
        
        return predictions
    
    def get_vote_summary(self, predictions: Dict[str, str]) -> Dict[str, int]:
        """
        Get vote counts from all strategies
        
        Args:
            predictions: Dictionary of {strategy_name: prediction}
            
        Returns:
            Dictionary of {BUY: count, SELL: count, HOLD: count}
        """
        votes = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
        
        for prediction in predictions.values():
            votes[prediction] += 1
        
        return votes


# ==================== QUICK TEST ====================

if __name__ == "__main__":
    """Quick test of all 9 strategies"""
    
    print("="*70)
    print("RULE-BASED STRATEGIES V1.0 - QUICK TEST")
    print("="*70)
    
    # Create strategies
    strategies = RuleBasedStrategies()
    
    # Test with sample features (10 features)
    test_features = np.array([
        1.8,   # volume_sma (high)
        0.65,  # eur_strength (strong)
        0.55,  # gbp_strength (neutral)
        0.45,  # nzd_strength (neutral)
        0.35,  # usd_strength (weak)
        0.50,  # jpy_strength (neutral)
        1.6,   # volatility (high)
        0.025, # returns_std (positive)
        1.2,   # volatility_confirm (positive)
        1.3    # atr (high)
    ])
    
    # Test on EURUSD
    pair = 'EURUSD.sim'
    
    print(f"\n📊 Testing {pair} with sample features:")
    print(f"   Volume: {test_features[0]:.2f} (high)")
    print(f"   EUR Strength: {test_features[1]:.2f} (strong)")
    print(f"   USD Strength: {test_features[4]:.2f} (weak)")
    print(f"   Volatility: {test_features[6]:.2f} (high)")
    print(f"   Returns: {test_features[7]:.3f} (positive)")
    
    # Get predictions
    predictions = strategies.predict_all(pair, test_features)
    
    print(f"\n📈 Strategy Predictions:")
    for strategy, prediction in predictions.items():
        symbol = '✅' if prediction == 'BUY' else ('❌' if prediction == 'SELL' else '⏸️')
        print(f"   {symbol} {strategy:30s} → {prediction}")
    
    # Get vote summary
    votes = strategies.get_vote_summary(predictions)
    print(f"\n📊 Vote Summary:")
    print(f"   BUY:  {votes['BUY']}/9")
    print(f"   SELL: {votes['SELL']}/9")
    print(f"   HOLD: {votes['HOLD']}/9")
    
    # Determine consensus
    max_vote = max(votes.values())
    consensus = [k for k, v in votes.items() if v == max_vote][0]
    
    print(f"\n🎯 Consensus: {consensus} ({max_vote}/9 votes)")
    
    print("\n" + "="*70)
    print("✅ TEST COMPLETE - All 9 strategies operational")
    print("="*70)

```
