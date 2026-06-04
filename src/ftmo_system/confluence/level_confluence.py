"""
Level Confluence - Fib/Pivot/Psych Level Detection for Scaling
================================================================

Detects confluence of technical levels for scaling decisions:
- Fibonacci levels (0.382, 0.5, 0.618, 1.0, 1.272, 1.618)
- Pivot points (S1, S2, S3, PP, R1, R2, R3)
- Psychological levels (round numbers like 1.1000, 1.0950)

Scale IN: When price pulls back to support levels with high confluence
Scale OUT: When price reaches resistance levels with high confluence

All scaling = Add/Remove 0.01 lot positions
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum


class LevelType(Enum):
    FIBONACCI = "FIBONACCI"
    PIVOT = "PIVOT"
    PSYCHOLOGICAL = "PSYCHOLOGICAL"


class ScalingAction(Enum):
    SCALE_IN = "SCALE_IN"
    SCALE_OUT = "SCALE_OUT"
    HOLD = "HOLD"


@dataclass
class TechnicalLevel:
    """A single technical level"""
    level_type: LevelType
    price: float
    name: str
    strength: float  # 0-1, how significant this level is
    
    def __str__(self) -> str:
        return f"{self.level_type.value}: {self.name} @ {self.price:.5f} (strength: {self.strength:.0%})"


@dataclass
class ScalingSignal:
    """Signal for scaling in or out"""
    action: ScalingAction
    confluence_score: int  # Number of factors aligning (0-4+)
    levels_hit: List[TechnicalLevel]
    reason: str
    confidence: float
    
    def __str__(self) -> str:
        if self.action == ScalingAction.HOLD:
            return f"HOLD - No scaling signal (confluence: {self.confluence_score})"
        return f"{self.action.value} - {self.reason} (confluence: {self.confluence_score}, confidence: {self.confidence:.0%})"


class LevelConfluence:
    """
    Detects confluence of Fibonacci, Pivot, and Psychological levels.
    
    Used for scaling in (add 0.01 lots) and scaling out (close 0.01 lots).
    
    Scale IN signals: Price at support with multiple confirmations
    Scale OUT signals: Price at resistance with multiple confirmations
    """
    
    def __init__(
        self,
        fib_tolerance_pips: float = 10.0,
        pivot_tolerance_pips: float = 15.0,
        psych_tolerance_pips: float = 10.0,
        min_confluence_for_scale: int = 2,
        pip_values: Optional[Dict[str, float]] = None
    ):
        """
        Initialize level confluence detector.
        
        Args:
            fib_tolerance_pips: Max distance from Fib level to count as "at level"
            pivot_tolerance_pips: Max distance from Pivot level
            psych_tolerance_pips: Max distance from Psychological level
            min_confluence_for_scale: Minimum levels needed for scale signal
            pip_values: Pip values per symbol
        """
        self.fib_tolerance_pips = fib_tolerance_pips
        self.pivot_tolerance_pips = pivot_tolerance_pips
        self.psych_tolerance_pips = psych_tolerance_pips
        self.min_confluence_for_scale = min_confluence_for_scale
        
        self.pip_values = pip_values or {
            'EURUSD': 0.0001, 'GBPUSD': 0.0001, 'USDJPY': 0.01, 'USDCHF': 0.0001,
            'AUDUSD': 0.0001, 'USDCAD': 0.0001, 'NZDUSD': 0.0001, 'EURGBP': 0.0001,
            'EURUSD.sim': 0.0001, 'GBPUSD.sim': 0.0001, 'USDJPY.sim': 0.01, 'USDCHF.sim': 0.0001,
            'AUDUSD.sim': 0.0001, 'USDCAD.sim': 0.0001, 'NZDUSD.sim': 0.0001, 'EURGBP.sim': 0.0001,
        }
        
        self.fib_levels = {
            'retracement': [0.236, 0.382, 0.5, 0.618, 0.786],
            'extension': [1.0, 1.272, 1.618, 2.0, 2.618]
        }
        
        # Quarter-level scaling configuration (v5.1 - R:R Based)
        self.quarter_tolerance_pips = 5.0  # How close to quarter level to trigger
        # Note: R:R gating (min 2.0) is passed as parameter to check_quarter_scaleout()
    
    def _get_quarter_levels(
        self,
        symbol: str,
        current_price: float,
        entry_price: float,
        direction: str
    ) -> List[TechnicalLevel]:
        """
        Calculate quarter levels from nearest major level.
        
        Quarter-Level Scaling (v3.2):
        - Major levels: Round numbers (150.00 for JPY, 1.0500 for others)
        - Quarters: .25, .50, .75, 1.00 increments
        - For LONG: scale out at quarters ABOVE entry
        - For SHORT: scale out at quarters BELOW entry
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            entry_price: Position entry price
            direction: 'BUY' or 'SELL'
            
        Returns:
            List of quarter TechnicalLevel objects in profit direction
        """
        levels = []
        is_jpy = 'JPY' in symbol.upper()
        is_long = direction.upper() == 'BUY'
        
        # Determine major level increment and quarter size
        if is_jpy:
            major_increment = 1.0      # 150.00, 151.00, etc.
            quarter_size = 0.25        # 0.25 = 25 pips for JPY
        else:
            major_increment = 0.0100   # 1.0500, 1.0600, etc.
            quarter_size = 0.0025      # 0.0025 = 25 pips for 4-digit
        
        # Find the nearest major level below current price
        major_below = (current_price // major_increment) * major_increment
        
        # Generate quarter levels for current and next major level
        quarter_prices = []
        for major in [major_below, major_below + major_increment]:
            for q in [0.25, 0.50, 0.75, 1.00]:
                quarter_price = major + (q * major_increment)
                quarter_prices.append((quarter_price, f"Q{int(q*100)}@{major:.4f}"))
        
        # Filter: only keep levels in profit direction
        for price, name in quarter_prices:
            if is_long:
                # For LONG: scale out at levels ABOVE entry price
                if price > entry_price:
                    levels.append(TechnicalLevel(
                        level_type=LevelType.PSYCHOLOGICAL,
                        price=price,
                        name=name,
                        strength=0.9  # High strength for quarter levels
                    ))
            else:
                # For SHORT: scale out at levels BELOW entry price
                if price < entry_price:
                    levels.append(TechnicalLevel(
                        level_type=LevelType.PSYCHOLOGICAL,
                        price=price,
                        name=name,
                        strength=0.9
                    ))
        
        # Sort by distance from current price (nearest first)
        if is_long:
            levels.sort(key=lambda l: l.price)  # Ascending for longs
        else:
            levels.sort(key=lambda l: -l.price)  # Descending for shorts
        
        return levels[:4]  # Return up to 4 quarter levels
    
    def check_quarter_scaleout(
        self,
        symbol: str,
        current_price: float,
        entry_price: float,
        sl_price: float,
        direction: str,
        min_rr_for_scaleout: float = 2.0
    ) -> Optional[ScalingSignal]:
        """
        Check if price has hit a quarter level for scale-out.
        
        v5.1 UPDATE: R:R-Based Scaling
        - Scale-out ONLY when R:R >= 2.0 (configurable)
        - Quarter levels are the WHERE, R:R is the WHEN
        - Leaves runner position for 3:1+ potential
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            entry_price: Position entry price
            sl_price: Stop loss price (required for R:R calculation)
            direction: 'BUY' or 'SELL'
            min_rr_for_scaleout: Minimum R:R ratio required (default 2.0)
            
        Returns:
            ScalingSignal if at quarter level AND R:R >= min, None otherwise
        """
        is_long = direction.upper() == 'BUY'
        pip_value = self._get_pip_value(symbol)
        
        # Calculate risk (distance to SL)
        if is_long:
            risk_pips = (entry_price - sl_price) / pip_value
            profit_pips = (current_price - entry_price) / pip_value
        else:
            risk_pips = (sl_price - entry_price) / pip_value
            profit_pips = (entry_price - current_price) / pip_value
        
        # Safety check - need valid risk
        if risk_pips <= 0:
            return None  # Invalid SL or already at BE
        
        # Calculate current R:R
        current_rr = profit_pips / risk_pips
        
        # CRITICAL: Only scale out if R:R >= minimum (default 2.0)
        if current_rr < min_rr_for_scaleout:
            return None  # R:R too low - let trade run!
        
        # Get quarter levels
        quarter_levels = self._get_quarter_levels(symbol, current_price, entry_price, direction)
        
        # Check if we're near any quarter level
        tolerance = self.quarter_tolerance_pips * pip_value
        
        for level in quarter_levels:
            distance = abs(current_price - level.price)
            if distance <= tolerance:
                return ScalingSignal(
                    action=ScalingAction.SCALE_OUT,
                    confluence_score=3,  # Quarter levels are high priority
                    levels_hit=[level],
                    reason=f"Quarter {level.name} @ {level.price:.5f} | R:R={current_rr:.1f}:1",
                    confidence=0.85
                )
        
        return None
    
    def check_for_scaling(
        self,
        symbol: str,
        current_price: float,
        direction: str,
        features: Dict[str, float],
        swing_high: Optional[float] = None,
        swing_low: Optional[float] = None
    ) -> ScalingSignal:
        """
        Check if current price warrants scaling in or out.
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            direction: Position direction ('BUY' or 'SELL')
            features: Feature dict with pivot/psych info
            swing_high: Recent swing high for Fib calculation
            swing_low: Recent swing low for Fib calculation
            
        Returns:
            ScalingSignal with action recommendation
        """
        is_long = direction.upper() == 'BUY'
        
        support_levels = self._find_support_levels(
            symbol, current_price, features, swing_high, swing_low
        )
        resistance_levels = self._find_resistance_levels(
            symbol, current_price, features, swing_high, swing_low
        )
        
        if is_long:
            scale_in_levels = [l for l in support_levels if self._is_near_level(symbol, current_price, l.price)]
            scale_out_levels = [l for l in resistance_levels if self._is_near_level(symbol, current_price, l.price)]
        else:
            scale_in_levels = [l for l in resistance_levels if self._is_near_level(symbol, current_price, l.price)]
            scale_out_levels = [l for l in support_levels if self._is_near_level(symbol, current_price, l.price)]
        
        scale_in_confluence = len(scale_in_levels)
        scale_out_confluence = len(scale_out_levels)
        
        htf_aligned = self._check_htf_alignment(features, is_long)
        if htf_aligned and scale_in_confluence > 0:
            scale_in_confluence += 1
        
        if scale_out_confluence >= self.min_confluence_for_scale and scale_out_confluence >= scale_in_confluence:
            confidence = min(scale_out_confluence / 4, 1.0)
            level_names = [l.name for l in scale_out_levels]
            return ScalingSignal(
                action=ScalingAction.SCALE_OUT,
                confluence_score=scale_out_confluence,
                levels_hit=scale_out_levels,
                reason=f"Price at {'resistance' if is_long else 'support'}: {', '.join(level_names)}",
                confidence=confidence
            )
        
        if scale_in_confluence >= self.min_confluence_for_scale:
            confidence = min(scale_in_confluence / 4, 1.0)
            level_names = [l.name for l in scale_in_levels]
            return ScalingSignal(
                action=ScalingAction.SCALE_IN,
                confluence_score=scale_in_confluence,
                levels_hit=scale_in_levels,
                reason=f"Price at {'support' if is_long else 'resistance'}: {', '.join(level_names)}",
                confidence=confidence
            )
        
        return ScalingSignal(
            action=ScalingAction.HOLD,
            confluence_score=max(scale_in_confluence, scale_out_confluence),
            levels_hit=[],
            reason="Insufficient level confluence for scaling",
            confidence=0.0
        )
    
    def _find_support_levels(
        self,
        symbol: str,
        current_price: float,
        features: Dict[str, float],
        swing_high: Optional[float],
        swing_low: Optional[float]
    ) -> List[TechnicalLevel]:
        """Find all support levels near current price."""
        levels = []
        
        pivot_s1 = features.get('dist_to_nearest_support', 0)
        if pivot_s1 > 0:
            s1_price = current_price - (pivot_s1 * self._get_pip_value(symbol))
            levels.append(TechnicalLevel(
                level_type=LevelType.PIVOT,
                price=s1_price,
                name="Pivot S1",
                strength=0.8
            ))
        
        pivot_position = features.get('pivot_position', 0)
        if pivot_position < 0:
            pp = current_price - (abs(pivot_position) * self._get_pip_value(symbol) * 10)
            levels.append(TechnicalLevel(
                level_type=LevelType.PIVOT,
                price=pp,
                name="Pivot PP",
                strength=0.9
            ))
        
        if swing_high and swing_low and swing_high > swing_low:
            for fib_ratio in self.fib_levels['retracement']:
                fib_price = swing_high - (swing_high - swing_low) * fib_ratio
                if fib_price < current_price:
                    levels.append(TechnicalLevel(
                        level_type=LevelType.FIBONACCI,
                        price=fib_price,
                        name=f"Fib {fib_ratio}",
                        strength=0.9 if fib_ratio in [0.382, 0.5, 0.618] else 0.6
                    ))
        
        psych_levels = self._find_psychological_levels(symbol, current_price, is_support=True)
        levels.extend(psych_levels)
        
        return levels
    
    def _find_resistance_levels(
        self,
        symbol: str,
        current_price: float,
        features: Dict[str, float],
        swing_high: Optional[float],
        swing_low: Optional[float]
    ) -> List[TechnicalLevel]:
        """Find all resistance levels near current price."""
        levels = []
        
        pivot_r1 = features.get('dist_to_nearest_resistance', 0)
        if pivot_r1 > 0:
            r1_price = current_price + (pivot_r1 * self._get_pip_value(symbol))
            levels.append(TechnicalLevel(
                level_type=LevelType.PIVOT,
                price=r1_price,
                name="Pivot R1",
                strength=0.8
            ))
        
        if swing_high and swing_low and swing_high > swing_low:
            swing_range = swing_high - swing_low
            for ext_ratio in self.fib_levels['extension']:
                ext_price = swing_low + swing_range * ext_ratio
                if ext_price > current_price:
                    levels.append(TechnicalLevel(
                        level_type=LevelType.FIBONACCI,
                        price=ext_price,
                        name=f"Fib Ext {ext_ratio}",
                        strength=0.85 if ext_ratio in [1.0, 1.618] else 0.6
                    ))
        
        psych_levels = self._find_psychological_levels(symbol, current_price, is_support=False)
        levels.extend(psych_levels)
        
        return levels
    
    def _find_psychological_levels(
        self,
        symbol: str,
        current_price: float,
        is_support: bool
    ) -> List[TechnicalLevel]:
        """Find nearby psychological (round number) levels."""
        levels = []
        pip_value = self._get_pip_value(symbol)
        
        if pip_value == 0.01:
            major_round = 1.0
            minor_round = 0.5
        else:
            major_round = 0.01
            minor_round = 0.005
        
        major_level = round(current_price / major_round) * major_round
        
        if is_support:
            if major_level < current_price:
                levels.append(TechnicalLevel(
                    level_type=LevelType.PSYCHOLOGICAL,
                    price=major_level,
                    name=f"Psych {major_level:.4f}",
                    strength=0.9
                ))
            minor_level = round(current_price / minor_round) * minor_round
            if minor_level < current_price and minor_level != major_level:
                levels.append(TechnicalLevel(
                    level_type=LevelType.PSYCHOLOGICAL,
                    price=minor_level,
                    name=f"Psych Minor {minor_level:.4f}",
                    strength=0.6
                ))
        else:
            if major_level > current_price:
                levels.append(TechnicalLevel(
                    level_type=LevelType.PSYCHOLOGICAL,
                    price=major_level,
                    name=f"Psych {major_level:.4f}",
                    strength=0.9
                ))
            minor_level = round(current_price / minor_round) * minor_round
            if minor_level > current_price and minor_level != major_level:
                levels.append(TechnicalLevel(
                    level_type=LevelType.PSYCHOLOGICAL,
                    price=minor_level,
                    name=f"Psych Minor {minor_level:.4f}",
                    strength=0.6
                ))
        
        return levels
    
    def _is_near_level(self, symbol: str, current_price: float, level_price: float) -> bool:
        """Check if current price is within tolerance of a level."""
        pip_value = self._get_pip_value(symbol)
        distance_pips = abs(current_price - level_price) / pip_value
        
        return distance_pips <= max(
            self.fib_tolerance_pips,
            self.pivot_tolerance_pips,
            self.psych_tolerance_pips
        )
    
    def _check_htf_alignment(self, features: Dict[str, float], is_long: bool) -> bool:
        """Check if higher timeframe trend aligns with position direction."""
        htf_trend = features.get('htf_trend_direction', 0)
        
        if is_long:
            return htf_trend > 0
        else:
            return htf_trend < 0
    
    def _get_pip_value(self, symbol: str) -> float:
        """Get pip value for symbol."""
        symbol_clean = symbol.replace('.sim', '')
        return self.pip_values.get(symbol, self.pip_values.get(symbol_clean, 0.0001))
    
    def get_level_summary(
        self,
        symbol: str,
        current_price: float,
        features: Dict[str, float],
        swing_high: Optional[float] = None,
        swing_low: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Get summary of all nearby levels for a symbol.
        
        Useful for display and analysis.
        """
        support = self._find_support_levels(symbol, current_price, features, swing_high, swing_low)
        resistance = self._find_resistance_levels(symbol, current_price, features, swing_high, swing_low)
        
        nearby_support = [l for l in support if self._is_near_level(symbol, current_price, l.price)]
        nearby_resistance = [l for l in resistance if self._is_near_level(symbol, current_price, l.price)]
        
        return {
            'symbol': symbol,
            'current_price': current_price,
            'support_levels': [
                {'name': l.name, 'price': l.price, 'strength': l.strength, 'type': l.level_type.value}
                for l in support
            ],
            'resistance_levels': [
                {'name': l.name, 'price': l.price, 'strength': l.strength, 'type': l.level_type.value}
                for l in resistance
            ],
            'nearby_support_count': len(nearby_support),
            'nearby_resistance_count': len(nearby_resistance),
            'total_confluence': len(nearby_support) + len(nearby_resistance)
        }
    
    def calculate_level_based_sl_tp(
        self,
        symbol: str,
        entry_price: float,
        direction: str,
        features: Dict[str, float],
        atr_pips: float,
        swing_high: Optional[float] = None,
        swing_low: Optional[float] = None,
        min_rr_ratio: float = 2.0,
        sl_buffer_pips: float = 5.0,
        tp_buffer_pips: float = 5.0
    ) -> Dict[str, Any]:
        """
        Calculate level-based SL and TP with R:R validation.
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            direction: 'BUY' or 'SELL'
            features: Feature dict with pivot/support/resistance info
            atr_pips: Current ATR in pips (used as SL floor)
            swing_high: Recent swing high for Fib calculation
            swing_low: Recent swing low for Fib calculation
            min_rr_ratio: Minimum R:R ratio to accept trade (default 1.5)
            sl_buffer_pips: Pips beyond level for SL (default 5)
            tp_buffer_pips: Pips before level for TP (default 5)
            
        Returns:
            Dict with sl_price, tp_price, rr_ratio, valid, reason, levels_used
        """
        pip_value = self._get_pip_value(symbol)
        is_long = direction.upper() == 'BUY'
        
        # Get all support and resistance levels
        support_levels = self._find_support_levels(
            symbol, entry_price, features, swing_high, swing_low
        )
        resistance_levels = self._find_resistance_levels(
            symbol, entry_price, features, swing_high, swing_low
        )
        
        # For BUY: SL below support, TP at resistance
        # For SELL: SL above resistance, TP at support
        if is_long:
            sl_levels = [l for l in support_levels if l.price < entry_price]
            tp_levels = [l for l in resistance_levels if l.price > entry_price]
        else:
            sl_levels = [l for l in resistance_levels if l.price > entry_price]
            tp_levels = [l for l in support_levels if l.price < entry_price]
        
        # Sort by distance to entry
        sl_levels.sort(key=lambda l: abs(l.price - entry_price))
        tp_levels.sort(key=lambda l: abs(l.price - entry_price))
        
        # Find nearest SL level
        sl_price = None
        sl_level_used = None
        if sl_levels:
            nearest_sl_level = sl_levels[0]
            if is_long:
                sl_price = nearest_sl_level.price - (sl_buffer_pips * pip_value)
            else:
                sl_price = nearest_sl_level.price + (sl_buffer_pips * pip_value)
            sl_level_used = nearest_sl_level
        
        # Calculate SL distance in pips
        if sl_price:
            sl_distance_pips = abs(entry_price - sl_price) / pip_value
        else:
            sl_distance_pips = 0
        
        # Apply ATR floor - SL should never be tighter than 1 ATR
        atr_floor = atr_pips * pip_value
        if sl_price is None or sl_distance_pips < atr_pips:
            # Use ATR-based SL as floor
            if is_long:
                sl_price = entry_price - atr_floor
            else:
                sl_price = entry_price + atr_floor
            sl_distance_pips = atr_pips
            sl_level_used = TechnicalLevel(
                level_type=LevelType.PIVOT,
                price=sl_price,
                name="ATR Floor",
                strength=0.5
            )
        
        # Find nearest TP level
        tp_price = None
        tp_level_used = None
        if tp_levels:
            nearest_tp_level = tp_levels[0]
            if is_long:
                tp_price = nearest_tp_level.price - (tp_buffer_pips * pip_value)
            else:
                tp_price = nearest_tp_level.price + (tp_buffer_pips * pip_value)
            tp_level_used = nearest_tp_level
        
        # If no TP level found, use 2:1 R:R as fallback
        if tp_price is None:
            if is_long:
                tp_price = entry_price + (sl_distance_pips * 2.0 * pip_value)
            else:
                tp_price = entry_price - (sl_distance_pips * 2.0 * pip_value)
            tp_level_used = TechnicalLevel(
                level_type=LevelType.PIVOT,
                price=tp_price,
                name="2:1 R:R Fallback",
                strength=0.5
            )
        
        # Calculate R:R ratio
        tp_distance_pips = abs(tp_price - entry_price) / pip_value
        rr_ratio = tp_distance_pips / sl_distance_pips if sl_distance_pips > 0 else 0
        
        # Validate R:R
        valid = rr_ratio >= min_rr_ratio
        
        if not valid:
            reason = f"R:R {rr_ratio:.2f} below minimum {min_rr_ratio}"
        else:
            reason = f"R:R {rr_ratio:.2f} - SL: {sl_level_used.name}, TP: {tp_level_used.name}"
        
        return {
            'sl_price': round(sl_price, 5),
            'tp_price': round(tp_price, 5),
            'sl_distance_pips': round(sl_distance_pips, 1),
            'tp_distance_pips': round(tp_distance_pips, 1),
            'rr_ratio': round(rr_ratio, 2),
            'valid': valid,
            'reason': reason,
            'sl_level': sl_level_used.name if sl_level_used else 'None',
            'tp_level': tp_level_used.name if tp_level_used else 'None',
            'direction': direction
        }
