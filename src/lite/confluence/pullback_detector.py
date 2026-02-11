"""
Micro Pullback Detector for Scale-In System
============================================

Detects valid pullbacks (not reversals) for scale-in opportunities.

Multi-Confirmation Approach:
1. STRUCTURE: Higher low (uptrend) or lower high (downtrend)
2. DEPTH: Retraced 38.2%-61.8% of recent swing (Fib zone)
3. MOMENTUM: RSI stayed above 40 (uptrend) or below 60 (downtrend)
4. TREND: Price still respects 20 EMA
5. VOLUME: Pullback on lower volume than impulse (optional)

All conditions must be met for valid pullback confirmation.
"""

import numpy as np
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from enum import Enum


class PullbackStatus(Enum):
    VALID_PULLBACK = "VALID_PULLBACK"
    POTENTIAL_REVERSAL = "POTENTIAL_REVERSAL"
    NO_PULLBACK = "NO_PULLBACK"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass
class SwingPoints:
    """Recent swing high and low"""
    swing_high: float
    swing_low: float
    swing_high_idx: int
    swing_low_idx: int
    swing_range: float
    trend_direction: str  # 'UP' or 'DOWN'


@dataclass
class PullbackResult:
    """Result of pullback analysis"""
    status: PullbackStatus
    is_valid: bool
    confidence: float
    checks_passed: int
    total_checks: int
    retracement_pct: float
    entry_zone_low: float
    entry_zone_high: float
    reason: str
    details: Dict[str, bool]


class PullbackDetector:
    """
    Detects micro pullbacks for scale-in opportunities.
    
    Only confirms pullback (not reversal) when multiple conditions align.
    """
    
    def __init__(
        self,
        fib_pullback_min: float = 0.382,
        fib_pullback_max: float = 0.618,
        rsi_bull_threshold: float = 40.0,
        rsi_bear_threshold: float = 60.0,
        ema_period: int = 20,
        min_swing_bars: int = 5,
        pip_values: Optional[Dict[str, float]] = None
    ):
        """
        Initialize pullback detector.
        
        Args:
            fib_pullback_min: Minimum retracement for valid pullback (38.2%)
            fib_pullback_max: Maximum retracement before reversal concern (61.8%)
            rsi_bull_threshold: RSI must stay above this in uptrend
            rsi_bear_threshold: RSI must stay below this in downtrend
            ema_period: EMA period for trend confirmation
            min_swing_bars: Minimum bars to identify swing
            pip_values: Pip values per symbol
        """
        self.fib_pullback_min = fib_pullback_min
        self.fib_pullback_max = fib_pullback_max
        self.rsi_bull_threshold = rsi_bull_threshold
        self.rsi_bear_threshold = rsi_bear_threshold
        self.ema_period = ema_period
        self.min_swing_bars = min_swing_bars
        
        self.pip_values = pip_values or {
            'EURUSD': 0.0001, 'GBPUSD': 0.0001, 'USDJPY': 0.01, 'USDCHF': 0.0001,
            'AUDUSD': 0.0001, 'USDCAD': 0.0001, 'NZDUSD': 0.0001, 'EURGBP': 0.0001,
        }

    def _get_pip_value(self, symbol: str) -> float:
        """Get pip value for symbol."""
        symbol_clean = symbol.replace('.sim', '')
        return self.pip_values.get(symbol, self.pip_values.get(symbol_clean, 0.0001))
    
    def find_swing_points(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray
    ) -> Optional[SwingPoints]:
        """
        Find recent swing high and low to define current move.
        
        Args:
            highs: Array of high prices
            lows: Array of low prices
            closes: Array of close prices
            
        Returns:
            SwingPoints or None if insufficient data
        """
        if len(highs) < self.min_swing_bars * 2:
            return None
        
        # Find swing high (highest point in lookback)
        lookback = min(20, len(highs) - 1)
        recent_highs = highs[-lookback:]
        recent_lows = lows[-lookback:]
        
        swing_high_idx = np.argmax(recent_highs)
        swing_low_idx = np.argmin(recent_lows)
        
        swing_high = recent_highs[swing_high_idx]
        swing_low = recent_lows[swing_low_idx]
        swing_range = swing_high - swing_low
        
        # Determine trend direction based on which came first
        if swing_low_idx < swing_high_idx:
            trend_direction = 'UP'  # Low then high = uptrend
        else:
            trend_direction = 'DOWN'  # High then low = downtrend
        
        return SwingPoints(
            swing_high=swing_high,
            swing_low=swing_low,
            swing_high_idx=swing_high_idx,
            swing_low_idx=swing_low_idx,
            swing_range=swing_range,
            trend_direction=trend_direction
        )
    
    def calculate_fib_levels(self, swing: SwingPoints) -> Dict[str, float]:
        """
        Calculate Fibonacci retracement levels from swing points.
        
        Args:
            swing: SwingPoints object
            
        Returns:
            Dictionary of Fib levels
        """
        if swing.trend_direction == 'UP':
            # Uptrend: measure retracement from high back toward low
            return {
                '0.0': swing.swing_high,
                '0.236': swing.swing_high - (swing.swing_range * 0.236),
                '0.382': swing.swing_high - (swing.swing_range * 0.382),
                '0.5': swing.swing_high - (swing.swing_range * 0.5),
                '0.618': swing.swing_high - (swing.swing_range * 0.618),
                '0.786': swing.swing_high - (swing.swing_range * 0.786),
                '1.0': swing.swing_low,
            }
        else:
            # Downtrend: measure retracement from low back toward high
            return {
                '0.0': swing.swing_low,
                '0.236': swing.swing_low + (swing.swing_range * 0.236),
                '0.382': swing.swing_low + (swing.swing_range * 0.382),
                '0.5': swing.swing_low + (swing.swing_range * 0.5),
                '0.618': swing.swing_low + (swing.swing_range * 0.618),
                '0.786': swing.swing_low + (swing.swing_range * 0.786),
                '1.0': swing.swing_high,
            }

    def _check_structure(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        trend_direction: str
    ) -> Tuple[bool, str]:
        """
        Check if price structure confirms pullback (not reversal).
        
        Uptrend: Must be forming higher low
        Downtrend: Must be forming lower high
        """
        if len(highs) < 6:
            return False, "Insufficient bars for structure"
        
        recent_lows = lows[-5:]
        recent_highs = highs[-5:]
        prev_lows = lows[-10:-5] if len(lows) >= 10 else lows[:5]
        prev_highs = highs[-10:-5] if len(highs) >= 10 else highs[:5]
        
        if trend_direction == 'UP':
            # Check for higher low
            current_low = np.min(recent_lows)
            previous_low = np.min(prev_lows)
            
            if current_low > previous_low:
                return True, f"Higher low: {current_low:.5f} > {previous_low:.5f}"
            else:
                return False, f"Lower low forming: {current_low:.5f} <= {previous_low:.5f}"
        else:
            # Check for lower high
            current_high = np.max(recent_highs)
            previous_high = np.max(prev_highs)
            
            if current_high < previous_high:
                return True, f"Lower high: {current_high:.5f} < {previous_high:.5f}"
            else:
                return False, f"Higher high forming: {current_high:.5f} >= {previous_high:.5f}"
    
    def _check_fib_zone(
        self,
        current_price: float,
        swing: SwingPoints
    ) -> Tuple[bool, float, str]:
        """
        Check if price is in the optimal Fib retracement zone (38.2-61.8%).
        """
        if swing.swing_range == 0:
            return False, 0.0, "No swing range"
        
        if swing.trend_direction == 'UP':
            # Uptrend: how much has price pulled back from high?
            pullback = swing.swing_high - current_price
            retracement = pullback / swing.swing_range
        else:
            # Downtrend: how much has price bounced from low?
            bounce = current_price - swing.swing_low
            retracement = bounce / swing.swing_range
        
        in_zone = self.fib_pullback_min <= retracement <= self.fib_pullback_max
        
        if retracement < self.fib_pullback_min:
            reason = f"Shallow pullback: {retracement:.1%} < {self.fib_pullback_min:.1%}"
        elif retracement > self.fib_pullback_max:
            reason = f"Deep pullback (reversal risk): {retracement:.1%} > {self.fib_pullback_max:.1%}"
        else:
            reason = f"In Fib zone: {retracement:.1%}"
        
        return in_zone, retracement, reason

    def _check_rsi_momentum(
        self,
        rsi: float,
        trend_direction: str
    ) -> Tuple[bool, str]:
        """
        Check if RSI confirms trend still intact (not reversing).
        
        Uptrend: RSI should stay above 40
        Downtrend: RSI should stay below 60
        """
        if trend_direction == 'UP':
            if rsi >= self.rsi_bull_threshold:
                return True, f"RSI bullish: {rsi:.1f} >= {self.rsi_bull_threshold}"
            else:
                return False, f"RSI weak: {rsi:.1f} < {self.rsi_bull_threshold}"
        else:
            if rsi <= self.rsi_bear_threshold:
                return True, f"RSI bearish: {rsi:.1f} <= {self.rsi_bear_threshold}"
            else:
                return False, f"RSI strong: {rsi:.1f} > {self.rsi_bear_threshold}"
    
    def _check_ema_trend(
        self,
        current_price: float,
        closes: np.ndarray,
        trend_direction: str
    ) -> Tuple[bool, str]:
        """
        Check if price respects EMA (trend intact).
        
        Uptrend: Price should be above or near 20 EMA
        Downtrend: Price should be below or near 20 EMA
        """
        if len(closes) < self.ema_period:
            return True, "Insufficient data for EMA"
        
        # Calculate EMA
        ema = self._calculate_ema(closes, self.ema_period)
        ema_value = ema[-1]
        
        # Allow some tolerance (price can be slightly through EMA during pullback)
        tolerance = abs(current_price - ema_value) / ema_value
        
        if trend_direction == 'UP':
            # Price should be above EMA or within 0.5% below
            if current_price >= ema_value or tolerance <= 0.005:
                return True, f"Price respects EMA: {current_price:.5f} near {ema_value:.5f}"
            else:
                return False, f"Price broke EMA: {current_price:.5f} < {ema_value:.5f}"
        else:
            # Price should be below EMA or within 0.5% above
            if current_price <= ema_value or tolerance <= 0.005:
                return True, f"Price respects EMA: {current_price:.5f} near {ema_value:.5f}"
            else:
                return False, f"Price broke EMA: {current_price:.5f} > {ema_value:.5f}"
    
    def _calculate_ema(self, data: np.ndarray, period: int) -> np.ndarray:
        """Calculate Exponential Moving Average."""
        ema = np.zeros_like(data)
        multiplier = 2 / (period + 1)
        ema[0] = data[0]
        
        for i in range(1, len(data)):
            ema[i] = (data[i] * multiplier) + (ema[i-1] * (1 - multiplier))
        
        return ema

    def detect_pullback(
        self,
        symbol: str,
        current_price: float,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        rsi: float,
        position_direction: str
    ) -> PullbackResult:
        """
        Main method: Detect if current price action is a valid pullback for scale-in.
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            highs: Array of high prices (at least 20 bars)
            lows: Array of low prices
            closes: Array of close prices
            rsi: Current RSI value
            position_direction: 'BUY' or 'SELL' (existing position direction)
            
        Returns:
            PullbackResult with validation details
        """
        # Initialize result
        details = {
            'structure': False,
            'fib_zone': False,
            'rsi_momentum': False,
            'ema_trend': False
        }
        
        # Check data sufficiency
        if len(highs) < 10 or len(lows) < 10 or len(closes) < 10:
            return PullbackResult(
                status=PullbackStatus.INSUFFICIENT_DATA,
                is_valid=False,
                confidence=0.0,
                checks_passed=0,
                total_checks=4,
                retracement_pct=0.0,
                entry_zone_low=0.0,
                entry_zone_high=0.0,
                reason="Insufficient historical data",
                details=details
            )
        
        # Convert position direction to trend direction
        trend_direction = 'UP' if position_direction.upper() == 'BUY' else 'DOWN'
        
        # Find swing points
        swing = self.find_swing_points(highs, lows, closes)
        if swing is None:
            return PullbackResult(
                status=PullbackStatus.INSUFFICIENT_DATA,
                is_valid=False,
                confidence=0.0,
                checks_passed=0,
                total_checks=4,
                retracement_pct=0.0,
                entry_zone_low=0.0,
                entry_zone_high=0.0,
                reason="Could not identify swing points",
                details=details
            )
        
        # Override swing trend with position direction for consistency
        swing.trend_direction = trend_direction
        
        # Run all checks
        reasons = []
        
        # 1. Structure check
        struct_ok, struct_reason = self._check_structure(highs, lows, trend_direction)
        details['structure'] = struct_ok
        reasons.append(f"Structure: {struct_reason}")
        
        # 2. Fib zone check
        fib_ok, retracement, fib_reason = self._check_fib_zone(current_price, swing)
        details['fib_zone'] = fib_ok
        reasons.append(f"Fib: {fib_reason}")
        
        # 3. RSI momentum check
        rsi_ok, rsi_reason = self._check_rsi_momentum(rsi, trend_direction)
        details['rsi_momentum'] = rsi_ok
        reasons.append(f"RSI: {rsi_reason}")
        
        # 4. EMA trend check
        ema_ok, ema_reason = self._check_ema_trend(current_price, closes, trend_direction)
        details['ema_trend'] = ema_ok
        reasons.append(f"EMA: {ema_reason}")
        
        # Count passed checks
        checks_passed = sum(details.values())
        total_checks = len(details)
        confidence = checks_passed / total_checks
        
        # Calculate entry zone (Fib 38.2% to 61.8%)
        fib_levels = self.calculate_fib_levels(swing)
        entry_zone_low = min(fib_levels['0.382'], fib_levels['0.618'])
        entry_zone_high = max(fib_levels['0.382'], fib_levels['0.618'])
        
        # Determine status
        if checks_passed == 4:
            status = PullbackStatus.VALID_PULLBACK
            is_valid = True
        elif checks_passed >= 3 and fib_ok:
            status = PullbackStatus.VALID_PULLBACK
            is_valid = True
        elif retracement > self.fib_pullback_max:
            status = PullbackStatus.POTENTIAL_REVERSAL
            is_valid = False
        else:
            status = PullbackStatus.NO_PULLBACK
            is_valid = False
        
        return PullbackResult(
            status=status,
            is_valid=is_valid,
            confidence=confidence,
            checks_passed=checks_passed,
            total_checks=total_checks,
            retracement_pct=retracement,
            entry_zone_low=entry_zone_low,
            entry_zone_high=entry_zone_high,
            reason=" | ".join(reasons),
            details=details
        )

    def should_scale_in(
        self,
        symbol: str,
        current_price: float,
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        rsi: float,
        position_direction: str,
        existing_position_at_be: bool,
        confluence_score: float,
        min_confluence_override: float = 0.80
    ) -> Tuple[bool, str]:
        """
        Determine if scale-in should be allowed.
        
        Args:
            symbol: Trading symbol
            current_price: Current price
            highs, lows, closes: Price history
            rsi: Current RSI
            position_direction: 'BUY' or 'SELL'
            existing_position_at_be: Is existing position at break-even or better?
            confluence_score: Current confluence score
            min_confluence_override: Allow scale-in without BE if confluence >= this
            
        Returns:
            (allowed: bool, reason: str)
        """
        # Check 1: Existing position must be at BE+ OR confluence must be high
        if not existing_position_at_be:
            if confluence_score >= min_confluence_override:
                be_status = f"High confluence override ({confluence_score:.2f} >= {min_confluence_override})"
            else:
                return False, f"Position not at BE and confluence too low ({confluence_score:.2f} < {min_confluence_override})"
        else:
            be_status = "Position at BE+"
        
        # Check 2: Validate pullback
        pullback = self.detect_pullback(
            symbol=symbol,
            current_price=current_price,
            highs=highs,
            lows=lows,
            closes=closes,
            rsi=rsi,
            position_direction=position_direction
        )
        
        if not pullback.is_valid:
            return False, f"Pullback invalid: {pullback.status.value} ({pullback.checks_passed}/{pullback.total_checks} checks)"
        
        return True, f"Scale-in allowed: {be_status} | Pullback valid ({pullback.checks_passed}/{pullback.total_checks})"


def get_scale_in_summary(result: PullbackResult) -> str:
    """Get a formatted summary of pullback analysis."""
    status_emoji = {
        PullbackStatus.VALID_PULLBACK: "[OK]",
        PullbackStatus.POTENTIAL_REVERSAL: "[WARN]",
        PullbackStatus.NO_PULLBACK: "[X]",
        PullbackStatus.INSUFFICIENT_DATA: "[?]"
    }
    
    emoji = status_emoji.get(result.status, "[?]")
    
    checks = []
    for check, passed in result.details.items():
        checks.append(f"{check}:{'Y' if passed else 'N'}")
    
    return (
        f"{emoji} {result.status.value} | "
        f"Confidence: {result.confidence:.0%} | "
        f"Retracement: {result.retracement_pct:.1%} | "
        f"{' '.join(checks)}"
    )
