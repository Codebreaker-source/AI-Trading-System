"""
H1 Candlestick Pattern Recognition
===================================

Identifies common candlestick patterns on H1 timeframe for confluence scoring.

Patterns Detected:
- Reversal: Hammer, Inverted Hammer, Shooting Star, Hanging Man
- Reversal: Engulfing (Bullish/Bearish), Harami
- Continuation: Doji, Spinning Top, Marubozu
- Multi-candle: Morning/Evening Star, Three White Soldiers, Three Black Crows

Returns a confluence score based on pattern alignment with trade direction.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class PatternType(Enum):
    """Pattern classification"""
    BULLISH_REVERSAL = "bullish_reversal"
    BEARISH_REVERSAL = "bearish_reversal"
    BULLISH_CONTINUATION = "bullish_continuation"
    BEARISH_CONTINUATION = "bearish_continuation"
    NEUTRAL = "neutral"


@dataclass
class CandlePattern:
    """Detected candlestick pattern"""
    name: str
    pattern_type: PatternType
    strength: float  # 0.0 to 1.0
    candles_used: int
    description: str


class CandlestickPatternRecognizer:
    """
    H1 Candlestick Pattern Recognition for confluence scoring.
    
    Uses OHLC data to identify patterns and score them based on
    alignment with the predicted trade direction.
    """
    
    def __init__(self, body_threshold: float = 0.3, wick_threshold: float = 2.0):
        """
        Initialize pattern recognizer.
        
        Args:
            body_threshold: Minimum body/range ratio for "real body" patterns
            wick_threshold: Minimum wick/body ratio for wick-dominant patterns
        """
        self.body_threshold = body_threshold
        self.wick_threshold = wick_threshold
        
        # Pattern weights for scoring (higher = stronger signal)
        self.pattern_weights = {
            # Strong reversal patterns
            'bullish_engulfing': 0.9,
            'bearish_engulfing': 0.9,
            'morning_star': 0.85,
            'evening_star': 0.85,
            'three_white_soldiers': 0.85,
            'three_black_crows': 0.85,
            
            # Medium reversal patterns
            'hammer': 0.7,
            'inverted_hammer': 0.65,
            'shooting_star': 0.7,
            'hanging_man': 0.65,
            'bullish_harami': 0.6,
            'bearish_harami': 0.6,
            
            # Weak/neutral patterns
            'doji': 0.4,
            'spinning_top': 0.35,
            'marubozu_bullish': 0.5,
            'marubozu_bearish': 0.5,
            
            # NEW: Additional single candle patterns
            'dragonfly_doji': 0.7,
            'gravestone_doji': 0.7,
            'long_legged_doji': 0.45,
            'four_price_doji': 0.3,
            'high_wave': 0.4,
            'belt_hold_bullish': 0.65,
            'belt_hold_bearish': 0.65,
            'opening_marubozu_bullish': 0.55,
            'opening_marubozu_bearish': 0.55,
            'closing_marubozu_bullish': 0.55,
            'closing_marubozu_bearish': 0.55,
            'shaven_head': 0.45,
            'shaven_bottom': 0.45,
            
            # NEW: Additional two candle patterns
            'piercing_line': 0.75,
            'dark_cloud_cover': 0.75,
            'tweezer_bottom': 0.7,
            'tweezer_top': 0.7,
            'kicking_bullish': 0.85,
            'kicking_bearish': 0.85,
            'on_neck_line': 0.5,
            'in_neck_line': 0.5,
            'thrusting_line': 0.5,
            'separating_lines_bullish': 0.6,
            'separating_lines_bearish': 0.6,
            'meeting_lines_bullish': 0.65,
            'meeting_lines_bearish': 0.65,
            'homing_pigeon': 0.55,
            'descending_hawk': 0.55,
            'matching_low': 0.6,
            'matching_high': 0.6,
            'doji_star_bullish': 0.65,
            'doji_star_bearish': 0.65,
            
            # NEW: Additional three candle patterns
            'three_inside_up': 0.8,
            'three_inside_down': 0.8,
            'three_outside_up': 0.85,
            'three_outside_down': 0.85,
            'abandoned_baby_bullish': 0.9,
            'abandoned_baby_bearish': 0.9,
            'tri_star_bullish': 0.75,
            'tri_star_bearish': 0.75,
            'three_stars_south': 0.7,
            'three_line_strike_bullish': 0.8,
            'three_line_strike_bearish': 0.8,
            'deliberation': 0.6,
            'advance_block': 0.65,
            'two_crows': 0.7,
            'upside_gap_two_crows': 0.7,
            'unique_three_river_bottom': 0.7,
            'concealing_baby_swallow': 0.75,
            'stick_sandwich': 0.65,
            'ladder_bottom': 0.7,
            'ladder_top': 0.7,
            
            # NEW: Multi-candle continuation patterns
            # Gap patterns
            'rising_window': 0.7,
            'falling_window': 0.7,
            'upside_tasuki_gap': 0.7,
            'downside_tasuki_gap': 0.7,
            'upside_gap_three_methods': 0.7,
            'downside_gap_three_methods': 0.7,
            'side_by_side_white_lines': 0.65,
            'side_by_side_black_lines': 0.65,
            'gapping_play_high': 0.7,
            'gapping_play_low': 0.7,
            # Three methods
            'rising_three_methods': 0.8,
            'falling_three_methods': 0.8,
            'mat_hold_bullish': 0.8,
            'mat_hold_bearish': 0.8,
            'rising_three_methods_extended': 0.75,
            'falling_three_methods_extended': 0.75,
            # Rest/consolidation
            'bullish_rest_after_rally': 0.65,
            'bearish_rest_after_decline': 0.65,
            'high_tight_flag': 0.85,
            'low_tight_flag': 0.85,
            'bullish_pennant': 0.75,
            'bearish_pennant': 0.75,
            'bull_flag': 0.75,
            'bear_flag': 0.75,
            # Thrust
            'bullish_thrust': 0.7,
            'bearish_thrust': 0.7,
            # Breakaway
            'breakaway_bullish': 0.75,
            'breakaway_bearish': 0.75,
            'runaway_gap_bullish': 0.8,
            'runaway_gap_bearish': 0.8,
            'exhaustion_gap_bullish': 0.6,
            'exhaustion_gap_bearish': 0.6,
            # Stalling
            'bullish_stalled': 0.5,
            'bearish_stalled': 0.5,
            'spinning_top_series_bullish': 0.6,
            'spinning_top_series_bearish': 0.6,
            # Inside bar
            'inside_bar_bullish_breakout': 0.7,
            'inside_bar_bearish_breakout': 0.7,
            'multiple_inside_bars_bullish': 0.75,
            'multiple_inside_bars_bearish': 0.75,
            # Squeeze
            'nr4_bullish': 0.7,
            'nr4_bearish': 0.7,
            'nr7_bullish': 0.75,
            'nr7_bearish': 0.75,
            
            # NEW: Sloped/Structure patterns
            # Wedges
            'rising_wedge': 0.75,
            'falling_wedge': 0.75,
            'broadening_wedge_ascending': 0.65,
            'broadening_wedge_descending': 0.65,
            # Channels
            'ascending_channel': 0.7,
            'descending_channel': 0.7,
            'horizontal_channel': 0.5,
            # Triangles
            'ascending_triangle': 0.75,
            'descending_triangle': 0.75,
            'symmetrical_triangle': 0.65,
            'expanding_triangle': 0.55,
            # Flags/Pennants (already have bull_flag, bear_flag)
            'bullish_pennant_structure': 0.75,
            'bearish_pennant_structure': 0.75,
            # Reversal structures
            'head_and_shoulders': 0.85,
            'inverse_head_and_shoulders': 0.85,
            'double_top': 0.8,
            'double_bottom': 0.8,
            'triple_top': 0.85,
            'triple_bottom': 0.85,
            
            # NEW: Rounded/Curved patterns
            'rounding_top': 0.75,
            'rounding_bottom': 0.75,
            'cup_and_handle': 0.8,
            'inverted_cup_and_handle': 0.8,
            'saucer_bottom': 0.7,
            'saucer_top': 0.7,
            
            # NEW: Harmonic patterns
            'gartley_bullish': 0.85,
            'gartley_bearish': 0.85,
            'bat_bullish': 0.8,
            'bat_bearish': 0.8,
            'butterfly_bullish': 0.8,
            'butterfly_bearish': 0.8,
            'crab_bullish': 0.85,
            'crab_bearish': 0.85,
            'shark_bullish': 0.75,
            'shark_bearish': 0.75,
            'cypher_bullish': 0.75,
            'cypher_bearish': 0.75,
            
            # NEW: AB=CD patterns
            'abcd_bullish': 0.7,
            'abcd_bearish': 0.7,
            'abcd_extension_bullish': 0.75,
            'abcd_extension_bearish': 0.75,
            
            # NEW: Three Drives
            'three_drives_bullish': 0.8,
            'three_drives_bearish': 0.8,
            
            # NEW: Elliott Wave patterns
            'impulse_wave_bullish': 0.8,
            'impulse_wave_bearish': 0.8,
            'corrective_abc_bullish': 0.7,
            'corrective_abc_bearish': 0.7,
            'wave_3_extension_bullish': 0.85,
            'wave_3_extension_bearish': 0.85,
            'ending_diagonal_bullish': 0.75,
            'ending_diagonal_bearish': 0.75,
            
            # NEW: Volume-based patterns
            'volume_climax_bullish': 0.75,
            'volume_climax_bearish': 0.75,
            'no_demand': 0.7,
            'no_supply': 0.7,
            'stopping_volume_bullish': 0.7,
            'stopping_volume_bearish': 0.7,
        }
    
    def analyze(
        self,
        h1_candles: List[Dict[str, float]],
        prediction: int
    ) -> Tuple[float, List[CandlePattern]]:
        """
        Analyze H1 candles for patterns and score alignment with prediction.
        
        Args:
            h1_candles: List of H1 candle dicts with 'open', 'high', 'low', 'close'
                       Most recent candle should be LAST in list
            prediction: Trade direction (0=SELL, 1=HOLD, 2=BUY)
        
        Returns:
            Tuple of (score, detected_patterns)
            Score is 0.0-1.0 based on pattern alignment with prediction
        """
        if not h1_candles or len(h1_candles) < 3:
            return 0.5, []  # Neutral if insufficient data
        
        if prediction == 1:  # HOLD
            return 0.5, []
        
        detected_patterns = []
        
        # Single candle patterns (most recent)
        single_patterns = self._detect_single_candle_patterns(h1_candles[-1])
        detected_patterns.extend(single_patterns)
        
        # Two candle patterns (last 2)
        if len(h1_candles) >= 2:
            two_patterns = self._detect_two_candle_patterns(
                h1_candles[-2], h1_candles[-1]
            )
            detected_patterns.extend(two_patterns)
        
        # Three candle patterns (last 3)
        if len(h1_candles) >= 3:
            three_patterns = self._detect_three_candle_patterns(
                h1_candles[-3], h1_candles[-2], h1_candles[-1]
            )
            detected_patterns.extend(three_patterns)
        
        # Multi-candle patterns (4+ candles)
        if len(h1_candles) >= 5:
            multi_patterns = self._detect_multi_candle_patterns(h1_candles)
            detected_patterns.extend(multi_patterns)
        
        # Sloped/Structure patterns (10+ candles for reliable detection)
        if len(h1_candles) >= 10:
            structure_patterns = self._detect_structure_patterns(h1_candles)
            detected_patterns.extend(structure_patterns)
        
        # Harmonic patterns (need sufficient swing points)
        if len(h1_candles) >= 15:
            harmonic_patterns = self._detect_harmonic_patterns(h1_candles)
            detected_patterns.extend(harmonic_patterns)
        
        # Elliott Wave patterns (need 20+ candles for wave structure)
        if len(h1_candles) >= 20:
            elliott_patterns = self._detect_elliott_wave_patterns(h1_candles)
            detected_patterns.extend(elliott_patterns)
        
        # Volume-based patterns (if volume data available)
        if len(h1_candles) >= 5 and 'volume' in h1_candles[-1]:
            volume_patterns = self._detect_volume_patterns(h1_candles)
            detected_patterns.extend(volume_patterns)
        
        # Calculate score based on pattern alignment
        score = self._calculate_alignment_score(detected_patterns, prediction)
        
        return score, detected_patterns
    
    def _get_candle_metrics(self, candle: Dict[str, float]) -> Dict[str, float]:
        """Calculate candle body, wicks, and ratios."""
        o, h, l, c = candle['open'], candle['high'], candle['low'], candle['close']
        
        body = abs(c - o)
        range_hl = h - l if h > l else 0.0001
        upper_wick = h - max(o, c)
        lower_wick = min(o, c) - l
        
        return {
            'open': o,
            'high': h,
            'low': l,
            'close': c,
            'body': body,
            'range': range_hl,
            'upper_wick': upper_wick,
            'lower_wick': lower_wick,
            'body_ratio': body / range_hl,
            'is_bullish': c > o,
            'is_bearish': c < o,
            'midpoint': (h + l) / 2
        }
    

    def _detect_single_candle_patterns(self, candle: Dict[str, float]) -> List[CandlePattern]:
        """Detect single-candle patterns."""
        patterns = []
        m = self._get_candle_metrics(candle)
        
        # Doji - very small body relative to range
        if m['body_ratio'] < 0.1:
            patterns.append(CandlePattern(
                name='doji',
                pattern_type=PatternType.NEUTRAL,
                strength=0.4,
                candles_used=1,
                description="Indecision - small body, potential reversal"
            ))
        
        # Spinning Top - small body with wicks on both sides
        elif m['body_ratio'] < 0.3 and m['upper_wick'] > m['body'] and m['lower_wick'] > m['body']:
            patterns.append(CandlePattern(
                name='spinning_top',
                pattern_type=PatternType.NEUTRAL,
                strength=0.35,
                candles_used=1,
                description="Indecision - balanced buying/selling pressure"
            ))
        
        # Hammer - small body at top, long lower wick (bullish reversal)
        if (m['lower_wick'] >= m['body'] * self.wick_threshold and 
            m['upper_wick'] < m['body'] * 0.5 and
            m['body_ratio'] < 0.4):
            patterns.append(CandlePattern(
                name='hammer',
                pattern_type=PatternType.BULLISH_REVERSAL,
                strength=0.7,
                candles_used=1,
                description="Bullish reversal - buyers rejected lower prices"
            ))
        
        # Inverted Hammer - small body at bottom, long upper wick (bullish reversal after downtrend)
        if (m['upper_wick'] >= m['body'] * self.wick_threshold and 
            m['lower_wick'] < m['body'] * 0.5 and
            m['body_ratio'] < 0.4):
            patterns.append(CandlePattern(
                name='inverted_hammer',
                pattern_type=PatternType.BULLISH_REVERSAL,
                strength=0.65,
                candles_used=1,
                description="Potential bullish reversal - buying interest emerging"
            ))
        
        # Shooting Star - small body at bottom, long upper wick (bearish reversal after uptrend)
        if (m['upper_wick'] >= m['body'] * self.wick_threshold and 
            m['lower_wick'] < m['body'] * 0.5 and
            m['body_ratio'] < 0.4 and
            m['is_bearish']):
            patterns.append(CandlePattern(
                name='shooting_star',
                pattern_type=PatternType.BEARISH_REVERSAL,
                strength=0.7,
                candles_used=1,
                description="Bearish reversal - sellers rejected higher prices"
            ))
        
        # Hanging Man - small body at top, long lower wick (bearish reversal after uptrend)
        if (m['lower_wick'] >= m['body'] * self.wick_threshold and 
            m['upper_wick'] < m['body'] * 0.5 and
            m['body_ratio'] < 0.4 and
            m['is_bearish']):
            patterns.append(CandlePattern(
                name='hanging_man',
                pattern_type=PatternType.BEARISH_REVERSAL,
                strength=0.65,
                candles_used=1,
                description="Potential bearish reversal - selling pressure building"
            ))
        
        # Marubozu - large body with minimal wicks
        if m['body_ratio'] > 0.8:
            if m['is_bullish']:
                patterns.append(CandlePattern(
                    name='marubozu_bullish',
                    pattern_type=PatternType.BULLISH_CONTINUATION,
                    strength=0.5,
                    candles_used=1,
                    description="Strong bullish momentum"
                ))
            else:
                patterns.append(CandlePattern(
                    name='marubozu_bearish',
                    pattern_type=PatternType.BEARISH_CONTINUATION,
                    strength=0.5,
                    candles_used=1,
                    description="Strong bearish momentum"
                ))
        
        # ============ NEW SINGLE CANDLE PATTERNS ============
        
        # Dragonfly Doji - open/close at high, long lower wick (bullish reversal)
        if (m['body_ratio'] < 0.1 and 
            m['lower_wick'] >= m['range'] * 0.6 and
            m['upper_wick'] < m['range'] * 0.1):
            patterns.append(CandlePattern(
                name='dragonfly_doji',
                pattern_type=PatternType.BULLISH_REVERSAL,
                strength=0.7,
                candles_used=1,
                description="Bullish reversal - buyers rejected lower prices, closed at high"
            ))
        
        # Gravestone Doji - open/close at low, long upper wick (bearish reversal)
        if (m['body_ratio'] < 0.1 and 
            m['upper_wick'] >= m['range'] * 0.6 and
            m['lower_wick'] < m['range'] * 0.1):
            patterns.append(CandlePattern(
                name='gravestone_doji',
                pattern_type=PatternType.BEARISH_REVERSAL,
                strength=0.7,
                candles_used=1,
                description="Bearish reversal - sellers rejected higher prices, closed at low"
            ))
        
        # Long-Legged Doji - long wicks both sides, tiny body
        if (m['body_ratio'] < 0.1 and 
            m['upper_wick'] >= m['range'] * 0.3 and
            m['lower_wick'] >= m['range'] * 0.3):
            patterns.append(CandlePattern(
                name='long_legged_doji',
                pattern_type=PatternType.NEUTRAL,
                strength=0.45,
                candles_used=1,
                description="High indecision - extreme volatility, potential reversal"
            ))
        
        # Four Price Doji - open=high=low=close (very rare)
        if m['range'] < 0.00001:  # Essentially no movement
            patterns.append(CandlePattern(
                name='four_price_doji',
                pattern_type=PatternType.NEUTRAL,
                strength=0.3,
                candles_used=1,
                description="No movement - extreme indecision or low liquidity"
            ))
        
        # High Wave - extreme long wicks, small body (more extreme than spinning top)
        if (m['body_ratio'] < 0.2 and 
            m['upper_wick'] >= m['body'] * 3 and
            m['lower_wick'] >= m['body'] * 3):
            patterns.append(CandlePattern(
                name='high_wave',
                pattern_type=PatternType.NEUTRAL,
                strength=0.4,
                candles_used=1,
                description="Extreme indecision - high volatility, trend uncertainty"
            ))
        
        # Belt Hold Bullish (Yorikiri) - opens at low, no lower wick, closes near high
        if (m['is_bullish'] and
            m['lower_wick'] < m['range'] * 0.05 and
            m['body_ratio'] > 0.6):
            patterns.append(CandlePattern(
                name='belt_hold_bullish',
                pattern_type=PatternType.BULLISH_REVERSAL,
                strength=0.65,
                candles_used=1,
                description="Bullish reversal - opened at low, strong buying throughout"
            ))
        
        # Belt Hold Bearish (Yorikiri) - opens at high, no upper wick, closes near low
        if (m['is_bearish'] and
            m['upper_wick'] < m['range'] * 0.05 and
            m['body_ratio'] > 0.6):
            patterns.append(CandlePattern(
                name='belt_hold_bearish',
                pattern_type=PatternType.BEARISH_REVERSAL,
                strength=0.65,
                candles_used=1,
                description="Bearish reversal - opened at high, strong selling throughout"
            ))
        
        # Opening Marubozu Bullish - no lower wick, opens at low
        if (m['is_bullish'] and
            m['lower_wick'] < m['range'] * 0.02 and
            m['upper_wick'] > m['range'] * 0.05 and
            m['body_ratio'] > 0.7):
            patterns.append(CandlePattern(
                name='opening_marubozu_bullish',
                pattern_type=PatternType.BULLISH_CONTINUATION,
                strength=0.55,
                candles_used=1,
                description="Bullish momentum - opened at low, buyers controlled"
            ))
        
        # Opening Marubozu Bearish - no upper wick, opens at high
        if (m['is_bearish'] and
            m['upper_wick'] < m['range'] * 0.02 and
            m['lower_wick'] > m['range'] * 0.05 and
            m['body_ratio'] > 0.7):
            patterns.append(CandlePattern(
                name='opening_marubozu_bearish',
                pattern_type=PatternType.BEARISH_CONTINUATION,
                strength=0.55,
                candles_used=1,
                description="Bearish momentum - opened at high, sellers controlled"
            ))
        
        # Closing Marubozu Bullish - no upper wick, closes at high
        if (m['is_bullish'] and
            m['upper_wick'] < m['range'] * 0.02 and
            m['lower_wick'] > m['range'] * 0.05 and
            m['body_ratio'] > 0.7):
            patterns.append(CandlePattern(
                name='closing_marubozu_bullish',
                pattern_type=PatternType.BULLISH_CONTINUATION,
                strength=0.55,
                candles_used=1,
                description="Bullish momentum - closed at high, buyers in control at close"
            ))
        
        # Closing Marubozu Bearish - no lower wick, closes at low
        if (m['is_bearish'] and
            m['lower_wick'] < m['range'] * 0.02 and
            m['upper_wick'] > m['range'] * 0.05 and
            m['body_ratio'] > 0.7):
            patterns.append(CandlePattern(
                name='closing_marubozu_bearish',
                pattern_type=PatternType.BEARISH_CONTINUATION,
                strength=0.55,
                candles_used=1,
                description="Bearish momentum - closed at low, sellers in control at close"
            ))
        
        # Shaven Head - no upper wick (bullish or bearish)
        if (m['upper_wick'] < m['range'] * 0.02 and
            m['body_ratio'] > 0.5 and m['body_ratio'] < 0.8):
            pattern_type = PatternType.BULLISH_CONTINUATION if m['is_bullish'] else PatternType.BEARISH_CONTINUATION
            patterns.append(CandlePattern(
                name='shaven_head',
                pattern_type=pattern_type,
                strength=0.45,
                candles_used=1,
                description="No upper wick - closed at high of session"
            ))
        
        # Shaven Bottom - no lower wick (bullish or bearish)
        if (m['lower_wick'] < m['range'] * 0.02 and
            m['body_ratio'] > 0.5 and m['body_ratio'] < 0.8):
            pattern_type = PatternType.BULLISH_CONTINUATION if m['is_bullish'] else PatternType.BEARISH_CONTINUATION
            patterns.append(CandlePattern(
                name='shaven_bottom',
                pattern_type=pattern_type,
                strength=0.45,
                candles_used=1,
                description="No lower wick - opened at low of session"
            ))
        
        return patterns
    
    def _detect_two_candle_patterns(
        self, 
        prev: Dict[str, float], 
        curr: Dict[str, float]
    ) -> List[CandlePattern]:
        """Detect two-candle patterns."""
        patterns = []
        m_prev = self._get_candle_metrics(prev)
        m_curr = self._get_candle_metrics(curr)
        
        # Bullish Engulfing - bearish candle followed by larger bullish candle
        if (m_prev['is_bearish'] and m_curr['is_bullish'] and
            m_curr['body'] > m_prev['body'] * 1.2 and
            m_curr['close'] > m_prev['open'] and
            m_curr['open'] < m_prev['close']):
            patterns.append(CandlePattern(
                name='bullish_engulfing',
                pattern_type=PatternType.BULLISH_REVERSAL,
                strength=0.9,
                candles_used=2,
                description="Strong bullish reversal - buyers overwhelmed sellers"
            ))
        
        # Bearish Engulfing - bullish candle followed by larger bearish candle
        if (m_prev['is_bullish'] and m_curr['is_bearish'] and
            m_curr['body'] > m_prev['body'] * 1.2 and
            m_curr['close'] < m_prev['open'] and
            m_curr['open'] > m_prev['close']):
            patterns.append(CandlePattern(
                name='bearish_engulfing',
                pattern_type=PatternType.BEARISH_REVERSAL,
                strength=0.9,
                candles_used=2,
                description="Strong bearish reversal - sellers overwhelmed buyers"
            ))
        
        # Bullish Harami - large bearish candle followed by small bullish candle inside it
        if (m_prev['is_bearish'] and m_curr['is_bullish'] and
            m_prev['body'] > m_curr['body'] * 1.5 and
            m_curr['high'] < m_prev['open'] and
            m_curr['low'] > m_prev['close']):
            patterns.append(CandlePattern(
                name='bullish_harami',
                pattern_type=PatternType.BULLISH_REVERSAL,
                strength=0.6,
                candles_used=2,
                description="Potential bullish reversal - selling momentum fading"
            ))
        
        # Bearish Harami - large bullish candle followed by small bearish candle inside it
        if (m_prev['is_bullish'] and m_curr['is_bearish'] and
            m_prev['body'] > m_curr['body'] * 1.5 and
            m_curr['high'] < m_prev['close'] and
            m_curr['low'] > m_prev['open']):
            patterns.append(CandlePattern(
                name='bearish_harami',
                pattern_type=PatternType.BEARISH_REVERSAL,
                strength=0.6,
                candles_used=2,
                description="Potential bearish reversal - buying momentum fading"
            ))
        
        # ============ NEW TWO CANDLE PATTERNS ============
        
        # Piercing Line - bearish → bullish opens below low, closes >50% into body
        if (m_prev['is_bearish'] and m_curr['is_bullish'] and
            m_curr['open'] < m_prev['low'] and
            m_curr['close'] > m_prev['midpoint'] and
            m_curr['close'] < m_prev['open']):
            patterns.append(CandlePattern(
                name='piercing_line',
                pattern_type=PatternType.BULLISH_REVERSAL,
                strength=0.75,
                candles_used=2,
                description="Bullish reversal - opened below low, recovered >50%"
            ))
        
        # Dark Cloud Cover - bullish → bearish opens above high, closes >50% into body
        if (m_prev['is_bullish'] and m_curr['is_bearish'] and
            m_curr['open'] > m_prev['high'] and
            m_curr['close'] < m_prev['midpoint'] and
            m_curr['close'] > m_prev['open']):
            patterns.append(CandlePattern(
                name='dark_cloud_cover',
                pattern_type=PatternType.BEARISH_REVERSAL,
                strength=0.75,
                candles_used=2,
                description="Bearish reversal - opened above high, sold off >50%"
            ))
        
        # Tweezer Bottom - two candles with matching lows
        low_tolerance = m_prev['range'] * 0.05
        if (abs(m_prev['low'] - m_curr['low']) < low_tolerance and
            m_prev['is_bearish'] and m_curr['is_bullish']):
            patterns.append(CandlePattern(
                name='tweezer_bottom',
                pattern_type=PatternType.BULLISH_REVERSAL,
                strength=0.7,
                candles_used=2,
                description="Bullish reversal - matching lows, support found"
            ))
        
        # Tweezer Top - two candles with matching highs
        high_tolerance = m_prev['range'] * 0.05
        if (abs(m_prev['high'] - m_curr['high']) < high_tolerance and
            m_prev['is_bullish'] and m_curr['is_bearish']):
            patterns.append(CandlePattern(
                name='tweezer_top',
                pattern_type=PatternType.BEARISH_REVERSAL,
                strength=0.7,
                candles_used=2,
                description="Bearish reversal - matching highs, resistance found"
            ))
        
        # Kicking Bullish - bearish marubozu → gap up → bullish marubozu
        if (m_prev['is_bearish'] and m_prev['body_ratio'] > 0.8 and
            m_curr['is_bullish'] and m_curr['body_ratio'] > 0.8 and
            m_curr['open'] > m_prev['open']):  # Gap up
            patterns.append(CandlePattern(
                name='kicking_bullish',
                pattern_type=PatternType.BULLISH_REVERSAL,
                strength=0.85,
                candles_used=2,
                description="Strong bullish reversal - gap up from bearish marubozu"
            ))
        
        # Kicking Bearish - bullish marubozu → gap down → bearish marubozu
        if (m_prev['is_bullish'] and m_prev['body_ratio'] > 0.8 and
            m_curr['is_bearish'] and m_curr['body_ratio'] > 0.8 and
            m_curr['open'] < m_prev['open']):  # Gap down
            patterns.append(CandlePattern(
                name='kicking_bearish',
                pattern_type=PatternType.BEARISH_REVERSAL,
                strength=0.85,
                candles_used=2,
                description="Strong bearish reversal - gap down from bullish marubozu"
            ))
        
        # On-Neck Line - bearish → small bullish closes at prior low
        close_tolerance = m_prev['range'] * 0.05
        if (m_prev['is_bearish'] and m_curr['is_bullish'] and
            m_curr['body'] < m_prev['body'] * 0.5 and
            abs(m_curr['close'] - m_prev['low']) < close_tolerance):
            patterns.append(CandlePattern(
                name='on_neck_line',
                pattern_type=PatternType.BEARISH_CONTINUATION,
                strength=0.5,
                candles_used=2,
                description="Bearish continuation - weak bounce to prior low"
            ))
        
        # In-Neck Line - bearish → small bullish closes slightly into prior body
        if (m_prev['is_bearish'] and m_curr['is_bullish'] and
            m_curr['body'] < m_prev['body'] * 0.5 and
            m_curr['close'] > m_prev['low'] and
            m_curr['close'] < m_prev['close'] + m_prev['body'] * 0.2):
            patterns.append(CandlePattern(
                name='in_neck_line',
                pattern_type=PatternType.BEARISH_CONTINUATION,
                strength=0.5,
                candles_used=2,
                description="Bearish continuation - weak penetration into prior body"
            ))
        
        # Thrusting Line - bearish → bullish closes into body below midpoint
        if (m_prev['is_bearish'] and m_curr['is_bullish'] and
            m_curr['close'] > m_prev['close'] and
            m_curr['close'] < m_prev['midpoint']):
            patterns.append(CandlePattern(
                name='thrusting_line',
                pattern_type=PatternType.BEARISH_CONTINUATION,
                strength=0.5,
                candles_used=2,
                description="Bearish continuation - recovery below midpoint"
            ))
        
        # Separating Lines Bullish - bearish → bullish opens at same open, rallies
        open_tolerance = m_prev['range'] * 0.05
        if (m_prev['is_bearish'] and m_curr['is_bullish'] and
            abs(m_curr['open'] - m_prev['open']) < open_tolerance and
            m_curr['body_ratio'] > 0.6):
            patterns.append(CandlePattern(
                name='separating_lines_bullish',
                pattern_type=PatternType.BULLISH_CONTINUATION,
                strength=0.6,
                candles_used=2,
                description="Bullish continuation - same open level, strong rally"
            ))
        
        # Separating Lines Bearish - bullish → bearish opens at same open, sells off
        if (m_prev['is_bullish'] and m_curr['is_bearish'] and
            abs(m_curr['open'] - m_prev['open']) < open_tolerance and
            m_curr['body_ratio'] > 0.6):
            patterns.append(CandlePattern(
                name='separating_lines_bearish',
                pattern_type=PatternType.BEARISH_CONTINUATION,
                strength=0.6,
                candles_used=2,
                description="Bearish continuation - same open level, strong selloff"
            ))
        
        # Meeting Lines Bullish - bearish → bullish with same close
        if (m_prev['is_bearish'] and m_curr['is_bullish'] and
            abs(m_curr['close'] - m_prev['close']) < close_tolerance and
            m_curr['body_ratio'] > 0.5):
            patterns.append(CandlePattern(
                name='meeting_lines_bullish',
                pattern_type=PatternType.BULLISH_REVERSAL,
                strength=0.65,
                candles_used=2,
                description="Bullish reversal - matching closes, support found"
            ))
        
        # Meeting Lines Bearish - bullish → bearish with same close
        if (m_prev['is_bullish'] and m_curr['is_bearish'] and
            abs(m_curr['close'] - m_prev['close']) < close_tolerance and
            m_curr['body_ratio'] > 0.5):
            patterns.append(CandlePattern(
                name='meeting_lines_bearish',
                pattern_type=PatternType.BEARISH_REVERSAL,
                strength=0.65,
                candles_used=2,
                description="Bearish reversal - matching closes, resistance found"
            ))
        
        # Homing Pigeon - bearish → smaller bearish inside (bullish reversal)
        if (m_prev['is_bearish'] and m_curr['is_bearish'] and
            m_curr['body'] < m_prev['body'] * 0.6 and
            m_curr['high'] < m_prev['high'] and
            m_curr['low'] > m_prev['low']):
            patterns.append(CandlePattern(
                name='homing_pigeon',
                pattern_type=PatternType.BULLISH_REVERSAL,
                strength=0.55,
                candles_used=2,
                description="Bullish reversal - smaller bearish inside, selling fading"
            ))
        
        # Descending Hawk - bullish → smaller bullish inside (bearish reversal)
        if (m_prev['is_bullish'] and m_curr['is_bullish'] and
            m_curr['body'] < m_prev['body'] * 0.6 and
            m_curr['high'] < m_prev['high'] and
            m_curr['low'] > m_prev['low']):
            patterns.append(CandlePattern(
                name='descending_hawk',
                pattern_type=PatternType.BEARISH_REVERSAL,
                strength=0.55,
                candles_used=2,
                description="Bearish reversal - smaller bullish inside, buying fading"
            ))
        
        # Matching Low - two bearish candles with same close (bullish reversal)
        if (m_prev['is_bearish'] and m_curr['is_bearish'] and
            abs(m_curr['close'] - m_prev['close']) < close_tolerance):
            patterns.append(CandlePattern(
                name='matching_low',
                pattern_type=PatternType.BULLISH_REVERSAL,
                strength=0.6,
                candles_used=2,
                description="Bullish reversal - matching closes, double bottom forming"
            ))
        
        # Matching High - two bullish candles with same close (bearish reversal)
        if (m_prev['is_bullish'] and m_curr['is_bullish'] and
            abs(m_curr['close'] - m_prev['close']) < close_tolerance):
            patterns.append(CandlePattern(
                name='matching_high',
                pattern_type=PatternType.BEARISH_REVERSAL,
                strength=0.6,
                candles_used=2,
                description="Bearish reversal - matching closes, double top forming"
            ))
        
        # Doji Star Bullish - bearish → gap down doji
        if (m_prev['is_bearish'] and m_prev['body_ratio'] > 0.5 and
            m_curr['body_ratio'] < 0.1 and
            m_curr['high'] < m_prev['close']):  # Gap down
            patterns.append(CandlePattern(
                name='doji_star_bullish',
                pattern_type=PatternType.BULLISH_REVERSAL,
                strength=0.65,
                candles_used=2,
                description="Bullish reversal - doji after gap down, indecision at bottom"
            ))
        
        # Doji Star Bearish - bullish → gap up doji
        if (m_prev['is_bullish'] and m_prev['body_ratio'] > 0.5 and
            m_curr['body_ratio'] < 0.1 and
            m_curr['low'] > m_prev['close']):  # Gap up
            patterns.append(CandlePattern(
                name='doji_star_bearish',
                pattern_type=PatternType.BEARISH_REVERSAL,
                strength=0.65,
                candles_used=2,
                description="Bearish reversal - doji after gap up, indecision at top"
            ))
        
        return patterns
    

    def _detect_three_candle_patterns(
        self,
        first: Dict[str, float],
        second: Dict[str, float],
        third: Dict[str, float]
    ) -> List[CandlePattern]:
        """Detect three-candle patterns."""
        patterns = []
        m1 = self._get_candle_metrics(first)
        m2 = self._get_candle_metrics(second)
        m3 = self._get_candle_metrics(third)
        
        # Morning Star - bearish, small body (doji/spinning top), bullish
        if (m1['is_bearish'] and m1['body_ratio'] > 0.4 and
            m2['body_ratio'] < 0.3 and
            m3['is_bullish'] and m3['body_ratio'] > 0.4 and
            m3['close'] > m1['midpoint']):
            patterns.append(CandlePattern(
                name='morning_star',
                pattern_type=PatternType.BULLISH_REVERSAL,
                strength=0.85,
                candles_used=3,
                description="Strong bullish reversal - downtrend exhaustion"
            ))
        
        # Evening Star - bullish, small body, bearish
        if (m1['is_bullish'] and m1['body_ratio'] > 0.4 and
            m2['body_ratio'] < 0.3 and
            m3['is_bearish'] and m3['body_ratio'] > 0.4 and
            m3['close'] < m1['midpoint']):
            patterns.append(CandlePattern(
                name='evening_star',
                pattern_type=PatternType.BEARISH_REVERSAL,
                strength=0.85,
                candles_used=3,
                description="Strong bearish reversal - uptrend exhaustion"
            ))
        
        # Three White Soldiers - three consecutive bullish candles with higher closes
        if (m1['is_bullish'] and m2['is_bullish'] and m3['is_bullish'] and
            m2['close'] > m1['close'] and m3['close'] > m2['close'] and
            m1['body_ratio'] > 0.5 and m2['body_ratio'] > 0.5 and m3['body_ratio'] > 0.5):
            patterns.append(CandlePattern(
                name='three_white_soldiers',
                pattern_type=PatternType.BULLISH_CONTINUATION,
                strength=0.85,
                candles_used=3,
                description="Strong bullish continuation - sustained buying"
            ))
        
        # Three Black Crows - three consecutive bearish candles with lower closes
        if (m1['is_bearish'] and m2['is_bearish'] and m3['is_bearish'] and
            m2['close'] < m1['close'] and m3['close'] < m2['close'] and
            m1['body_ratio'] > 0.5 and m2['body_ratio'] > 0.5 and m3['body_ratio'] > 0.5):
            patterns.append(CandlePattern(
                name='three_black_crows',
                pattern_type=PatternType.BEARISH_CONTINUATION,
                strength=0.85,
                candles_used=3,
                description="Strong bearish continuation - sustained selling"
            ))
        
        # ============ NEW THREE CANDLE PATTERNS ============
        
        # Three Inside Up - bearish → bullish harami → bullish confirms
        if (m1['is_bearish'] and m1['body_ratio'] > 0.5 and
            m2['is_bullish'] and m2['body'] < m1['body'] and
            m2['high'] < m1['open'] and m2['low'] > m1['close'] and
            m3['is_bullish'] and m3['close'] > m1['open']):
            patterns.append(CandlePattern(
                name='three_inside_up',
                pattern_type=PatternType.BULLISH_REVERSAL,
                strength=0.8,
                candles_used=3,
                description="Bullish reversal - harami confirmed by third candle"
            ))
        
        # Three Inside Down - bullish → bearish harami → bearish confirms
        if (m1['is_bullish'] and m1['body_ratio'] > 0.5 and
            m2['is_bearish'] and m2['body'] < m1['body'] and
            m2['high'] < m1['close'] and m2['low'] > m1['open'] and
            m3['is_bearish'] and m3['close'] < m1['open']):
            patterns.append(CandlePattern(
                name='three_inside_down',
                pattern_type=PatternType.BEARISH_REVERSAL,
                strength=0.8,
                candles_used=3,
                description="Bearish reversal - harami confirmed by third candle"
            ))
        
        # Three Outside Up - bearish → bullish engulfing → bullish confirms
        if (m1['is_bearish'] and
            m2['is_bullish'] and m2['body'] > m1['body'] * 1.2 and
            m2['close'] > m1['open'] and m2['open'] < m1['close'] and
            m3['is_bullish'] and m3['close'] > m2['close']):
            patterns.append(CandlePattern(
                name='three_outside_up',
                pattern_type=PatternType.BULLISH_REVERSAL,
                strength=0.85,
                candles_used=3,
                description="Strong bullish reversal - engulfing confirmed"
            ))
        
        # Three Outside Down - bullish → bearish engulfing → bearish confirms
        if (m1['is_bullish'] and
            m2['is_bearish'] and m2['body'] > m1['body'] * 1.2 and
            m2['close'] < m1['open'] and m2['open'] > m1['close'] and
            m3['is_bearish'] and m3['close'] < m2['close']):
            patterns.append(CandlePattern(
                name='three_outside_down',
                pattern_type=PatternType.BEARISH_REVERSAL,
                strength=0.85,
                candles_used=3,
                description="Strong bearish reversal - engulfing confirmed"
            ))
        
        # Abandoned Baby Bullish - bearish → gap down doji → gap up bullish
        if (m1['is_bearish'] and m1['body_ratio'] > 0.5 and
            m2['body_ratio'] < 0.1 and
            m2['high'] < m1['low'] and  # Gap down
            m3['is_bullish'] and m3['body_ratio'] > 0.5 and
            m3['low'] > m2['high']):  # Gap up
            patterns.append(CandlePattern(
                name='abandoned_baby_bullish',
                pattern_type=PatternType.BULLISH_REVERSAL,
                strength=0.9,
                candles_used=3,
                description="Strong bullish reversal - isolated doji at bottom"
            ))
        
        # Abandoned Baby Bearish - bullish → gap up doji → gap down bearish
        if (m1['is_bullish'] and m1['body_ratio'] > 0.5 and
            m2['body_ratio'] < 0.1 and
            m2['low'] > m1['high'] and  # Gap up
            m3['is_bearish'] and m3['body_ratio'] > 0.5 and
            m3['high'] < m2['low']):  # Gap down
            patterns.append(CandlePattern(
                name='abandoned_baby_bearish',
                pattern_type=PatternType.BEARISH_REVERSAL,
                strength=0.9,
                candles_used=3,
                description="Strong bearish reversal - isolated doji at top"
            ))
        
        # Tri-Star Bullish - three dojis, middle lower
        if (m1['body_ratio'] < 0.1 and m2['body_ratio'] < 0.1 and m3['body_ratio'] < 0.1 and
            m2['close'] < m1['close'] and m3['close'] > m2['close']):
            patterns.append(CandlePattern(
                name='tri_star_bullish',
                pattern_type=PatternType.BULLISH_REVERSAL,
                strength=0.75,
                candles_used=3,
                description="Bullish reversal - three dojis with middle lowest"
            ))
        
        # Tri-Star Bearish - three dojis, middle higher
        if (m1['body_ratio'] < 0.1 and m2['body_ratio'] < 0.1 and m3['body_ratio'] < 0.1 and
            m2['close'] > m1['close'] and m3['close'] < m2['close']):
            patterns.append(CandlePattern(
                name='tri_star_bearish',
                pattern_type=PatternType.BEARISH_REVERSAL,
                strength=0.75,
                candles_used=3,
                description="Bearish reversal - three dojis with middle highest"
            ))
        
        # Three Stars in the South - three bearish, each smaller with higher low
        if (m1['is_bearish'] and m2['is_bearish'] and m3['is_bearish'] and
            m2['body'] < m1['body'] and m3['body'] < m2['body'] and
            m2['low'] > m1['low'] and m3['low'] > m2['low']):
            patterns.append(CandlePattern(
                name='three_stars_south',
                pattern_type=PatternType.BULLISH_REVERSAL,
                strength=0.7,
                candles_used=3,
                description="Bullish reversal - selling pressure decreasing"
            ))
        
        # Three Line Strike Bullish - three bearish → one bullish engulfs all three
        if (m1['is_bearish'] and m2['is_bearish'] and m3['is_bearish'] and
            m2['close'] < m1['close'] and m3['close'] < m2['close']):
            # Check if a 4th candle would engulf - approximate with m3 metrics
            # This is a 4-candle pattern but we check setup with 3
            patterns.append(CandlePattern(
                name='three_line_strike_bullish',
                pattern_type=PatternType.BULLISH_CONTINUATION,
                strength=0.8,
                candles_used=3,
                description="Bullish continuation setup - watch for engulfing"
            ))
        
        # Three Line Strike Bearish - three bullish → one bearish engulfs all three
        if (m1['is_bullish'] and m2['is_bullish'] and m3['is_bullish'] and
            m2['close'] > m1['close'] and m3['close'] > m2['close']):
            patterns.append(CandlePattern(
                name='three_line_strike_bearish',
                pattern_type=PatternType.BEARISH_CONTINUATION,
                strength=0.8,
                candles_used=3,
                description="Bearish continuation setup - watch for engulfing"
            ))
        
        # Deliberation - two strong bullish → small bullish/spinning top
        if (m1['is_bullish'] and m1['body_ratio'] > 0.6 and
            m2['is_bullish'] and m2['body_ratio'] > 0.6 and
            m2['close'] > m1['close'] and
            m3['is_bullish'] and m3['body_ratio'] < 0.3):
            patterns.append(CandlePattern(
                name='deliberation',
                pattern_type=PatternType.BEARISH_REVERSAL,
                strength=0.6,
                candles_used=3,
                description="Bearish reversal - momentum fading, indecision"
            ))
        
        # Advance Block - three bullish with decreasing bodies and longer upper wicks
        if (m1['is_bullish'] and m2['is_bullish'] and m3['is_bullish'] and
            m2['close'] > m1['close'] and m3['close'] > m2['close'] and
            m2['body'] < m1['body'] and m3['body'] < m2['body'] and
            m2['upper_wick'] > m1['upper_wick'] and m3['upper_wick'] > m2['upper_wick']):
            patterns.append(CandlePattern(
                name='advance_block',
                pattern_type=PatternType.BEARISH_REVERSAL,
                strength=0.65,
                candles_used=3,
                description="Bearish reversal - buying pressure weakening"
            ))
        
        # Two Crows - bullish → gap up small bearish → bearish engulfs
        if (m1['is_bullish'] and m1['body_ratio'] > 0.6 and
            m2['is_bearish'] and m2['open'] > m1['close'] and  # Gap up
            m3['is_bearish'] and m3['body'] > m2['body'] and
            m3['close'] < m2['close']):
            patterns.append(CandlePattern(
                name='two_crows',
                pattern_type=PatternType.BEARISH_REVERSAL,
                strength=0.7,
                candles_used=3,
                description="Bearish reversal - crows signal top"
            ))
        
        # Upside Gap Two Crows - bullish → gap up bearish → bearish engulfs first gap candle
        if (m1['is_bullish'] and m1['body_ratio'] > 0.6 and
            m2['is_bearish'] and m2['open'] > m1['close'] and  # Gap up
            m3['is_bearish'] and
            m3['open'] > m2['open'] and m3['close'] < m2['close'] and
            m3['close'] > m1['close']):  # Still above first candle close
            patterns.append(CandlePattern(
                name='upside_gap_two_crows',
                pattern_type=PatternType.BEARISH_REVERSAL,
                strength=0.7,
                candles_used=3,
                description="Bearish reversal - gap up rejected"
            ))
        
        # Unique Three River Bottom - bearish → bearish harami with long lower wick → small bullish
        if (m1['is_bearish'] and m1['body_ratio'] > 0.5 and
            m2['is_bearish'] and m2['body'] < m1['body'] and
            m2['lower_wick'] > m2['body'] * 2 and
            m3['is_bullish'] and m3['body'] < m2['body'] and
            m3['close'] < m2['close']):
            patterns.append(CandlePattern(
                name='unique_three_river_bottom',
                pattern_type=PatternType.BULLISH_REVERSAL,
                strength=0.7,
                candles_used=3,
                description="Bullish reversal - unique bottom formation"
            ))
        
        # Concealing Baby Swallow - two bearish marubozu → bearish high wave inside → bearish engulfs
        if (m1['is_bearish'] and m1['body_ratio'] > 0.8 and
            m2['is_bearish'] and m2['body_ratio'] > 0.8 and
            m3['is_bearish'] and m3['body_ratio'] < 0.4 and
            m3['upper_wick'] > m3['body'] and m3['lower_wick'] > m3['body']):
            patterns.append(CandlePattern(
                name='concealing_baby_swallow',
                pattern_type=PatternType.BULLISH_REVERSAL,
                strength=0.75,
                candles_used=3,
                description="Bullish reversal - concealed reversal signal"
            ))
        
        # Stick Sandwich - bearish → bullish → bearish with same close as first
        close_tolerance = m1['range'] * 0.05
        if (m1['is_bearish'] and
            m2['is_bullish'] and
            m3['is_bearish'] and
            abs(m3['close'] - m1['close']) < close_tolerance):
            patterns.append(CandlePattern(
                name='stick_sandwich',
                pattern_type=PatternType.BULLISH_REVERSAL,
                strength=0.65,
                candles_used=3,
                description="Bullish reversal - support at matching closes"
            ))
        
        # Ladder Bottom - three bearish → bearish with long upper wick → bullish
        if (m1['is_bearish'] and m2['is_bearish'] and
            m2['close'] < m1['close'] and
            m3['is_bearish'] and m3['upper_wick'] > m3['body'] * 1.5):
            patterns.append(CandlePattern(
                name='ladder_bottom',
                pattern_type=PatternType.BULLISH_REVERSAL,
                strength=0.7,
                candles_used=3,
                description="Bullish reversal - ladder pattern at bottom"
            ))
        
        # Ladder Top - three bullish → bullish with long lower wick → bearish
        if (m1['is_bullish'] and m2['is_bullish'] and
            m2['close'] > m1['close'] and
            m3['is_bullish'] and m3['lower_wick'] > m3['body'] * 1.5):
            patterns.append(CandlePattern(
                name='ladder_top',
                pattern_type=PatternType.BEARISH_REVERSAL,
                strength=0.7,
                candles_used=3,
                description="Bearish reversal - ladder pattern at top"
            ))
        
        return patterns
    
    def _detect_multi_candle_patterns(self, candles: List[Dict[str, float]]) -> List[CandlePattern]:
        """Detect multi-candle patterns (4+ candles)."""
        patterns = []
        
        # Need at least 5 candles for most patterns
        if len(candles) < 5:
            return patterns
        
        # Get metrics for last several candles
        metrics = [self._get_candle_metrics(c) for c in candles[-7:]]
        
        # ============ GAP PATTERNS ============
        
        # Rising Window - gap up that doesn't fill
        if len(metrics) >= 3:
            m1, m2, m3 = metrics[-3], metrics[-2], metrics[-1]
            if (m2['low'] > m1['high'] and  # Gap up between 1 and 2
                m3['low'] > m1['high']):  # Gap still not filled
                patterns.append(CandlePattern(
                    name='rising_window',
                    pattern_type=PatternType.BULLISH_CONTINUATION,
                    strength=0.7,
                    candles_used=3,
                    description="Bullish continuation - gap up holding"
                ))
        
        # Falling Window - gap down that doesn't fill
        if len(metrics) >= 3:
            m1, m2, m3 = metrics[-3], metrics[-2], metrics[-1]
            if (m2['high'] < m1['low'] and  # Gap down between 1 and 2
                m3['high'] < m1['low']):  # Gap still not filled
                patterns.append(CandlePattern(
                    name='falling_window',
                    pattern_type=PatternType.BEARISH_CONTINUATION,
                    strength=0.7,
                    candles_used=3,
                    description="Bearish continuation - gap down holding"
                ))
        
        # Upside Tasuki Gap - bullish → gap up bullish → bearish into gap (doesn't close)
        if len(metrics) >= 3:
            m1, m2, m3 = metrics[-3], metrics[-2], metrics[-1]
            if (m1['is_bullish'] and m2['is_bullish'] and m3['is_bearish'] and
                m2['open'] > m1['close'] and  # Gap up
                m3['open'] > m2['open'] and m3['close'] < m2['close'] and
                m3['close'] > m1['close']):  # Doesn't fill gap
                patterns.append(CandlePattern(
                    name='upside_tasuki_gap',
                    pattern_type=PatternType.BULLISH_CONTINUATION,
                    strength=0.7,
                    candles_used=3,
                    description="Bullish continuation - gap tested but held"
                ))
        
        # Downside Tasuki Gap - bearish → gap down bearish → bullish into gap (doesn't close)
        if len(metrics) >= 3:
            m1, m2, m3 = metrics[-3], metrics[-2], metrics[-1]
            if (m1['is_bearish'] and m2['is_bearish'] and m3['is_bullish'] and
                m2['open'] < m1['close'] and  # Gap down
                m3['open'] < m2['open'] and m3['close'] > m2['close'] and
                m3['close'] < m1['close']):  # Doesn't fill gap
                patterns.append(CandlePattern(
                    name='downside_tasuki_gap',
                    pattern_type=PatternType.BEARISH_CONTINUATION,
                    strength=0.7,
                    candles_used=3,
                    description="Bearish continuation - gap tested but held"
                ))
        
        # Upside Gap Three Methods - two bullish with gap → bearish fills gap → continues up
        if len(metrics) >= 4:
            m1, m2, m3, m4 = metrics[-4], metrics[-3], metrics[-2], metrics[-1]
            if (m1['is_bullish'] and m2['is_bullish'] and
                m2['open'] > m1['close'] and  # Gap up
                m3['is_bearish'] and m3['close'] < m2['open'] and  # Fills gap
                m4['is_bullish'] and m4['close'] > m2['close']):  # Continues up
                patterns.append(CandlePattern(
                    name='upside_gap_three_methods',
                    pattern_type=PatternType.BULLISH_CONTINUATION,
                    strength=0.7,
                    candles_used=4,
                    description="Bullish continuation - gap filled then resumed"
                ))
        
        # Downside Gap Three Methods - two bearish with gap → bullish fills gap → continues down
        if len(metrics) >= 4:
            m1, m2, m3, m4 = metrics[-4], metrics[-3], metrics[-2], metrics[-1]
            if (m1['is_bearish'] and m2['is_bearish'] and
                m2['open'] < m1['close'] and  # Gap down
                m3['is_bullish'] and m3['close'] > m2['open'] and  # Fills gap
                m4['is_bearish'] and m4['close'] < m2['close']):  # Continues down
                patterns.append(CandlePattern(
                    name='downside_gap_three_methods',
                    pattern_type=PatternType.BEARISH_CONTINUATION,
                    strength=0.7,
                    candles_used=4,
                    description="Bearish continuation - gap filled then resumed"
                ))
        
        # Side-by-Side White Lines - bullish → gap up → two similar bullish
        if len(metrics) >= 4:
            m1, m2, m3, m4 = metrics[-4], metrics[-3], metrics[-2], metrics[-1]
            body_tolerance = m2['body'] * 0.3
            if (m1['is_bullish'] and m2['is_bullish'] and m3['is_bullish'] and
                m2['open'] > m1['close'] and  # Gap up
                abs(m2['body'] - m3['body']) < body_tolerance and
                m4['is_bullish']):
                patterns.append(CandlePattern(
                    name='side_by_side_white_lines',
                    pattern_type=PatternType.BULLISH_CONTINUATION,
                    strength=0.65,
                    candles_used=4,
                    description="Bullish continuation - parallel bullish candles"
                ))
        
        # Side-by-Side Black Lines - bearish → gap down → two similar bearish
        if len(metrics) >= 4:
            m1, m2, m3, m4 = metrics[-4], metrics[-3], metrics[-2], metrics[-1]
            body_tolerance = m2['body'] * 0.3
            if (m1['is_bearish'] and m2['is_bearish'] and m3['is_bearish'] and
                m2['open'] < m1['close'] and  # Gap down
                abs(m2['body'] - m3['body']) < body_tolerance and
                m4['is_bearish']):
                patterns.append(CandlePattern(
                    name='side_by_side_black_lines',
                    pattern_type=PatternType.BEARISH_CONTINUATION,
                    strength=0.65,
                    candles_used=4,
                    description="Bearish continuation - parallel bearish candles"
                ))
        
        # Gapping Play High - sideways after gap up → breakout higher
        if len(metrics) >= 5:
            m1, m2, m3, m4, m5 = metrics[-5], metrics[-4], metrics[-3], metrics[-2], metrics[-1]
            if (m2['open'] > m1['high'] and  # Gap up
                m3['body_ratio'] < 0.3 and m4['body_ratio'] < 0.3 and  # Sideways
                m5['is_bullish'] and m5['close'] > max(m3['high'], m4['high'])):  # Breakout
                patterns.append(CandlePattern(
                    name='gapping_play_high',
                    pattern_type=PatternType.BULLISH_CONTINUATION,
                    strength=0.7,
                    candles_used=5,
                    description="Bullish continuation - gap up consolidation breakout"
                ))
        
        # Gapping Play Low - sideways after gap down → breakout lower
        if len(metrics) >= 5:
            m1, m2, m3, m4, m5 = metrics[-5], metrics[-4], metrics[-3], metrics[-2], metrics[-1]
            if (m2['open'] < m1['low'] and  # Gap down
                m3['body_ratio'] < 0.3 and m4['body_ratio'] < 0.3 and  # Sideways
                m5['is_bearish'] and m5['close'] < min(m3['low'], m4['low'])):  # Breakdown
                patterns.append(CandlePattern(
                    name='gapping_play_low',
                    pattern_type=PatternType.BEARISH_CONTINUATION,
                    strength=0.7,
                    candles_used=5,
                    description="Bearish continuation - gap down consolidation breakdown"
                ))
        
        # ============ THREE METHODS PATTERNS ============
        
        # Rising Three Methods - long bullish → 3 small bearish inside → long bullish
        if len(metrics) >= 5:
            m1, m2, m3, m4, m5 = metrics[-5], metrics[-4], metrics[-3], metrics[-2], metrics[-1]
            if (m1['is_bullish'] and m1['body_ratio'] > 0.6 and
                m2['is_bearish'] and m2['body'] < m1['body'] * 0.5 and
                m3['is_bearish'] and m3['body'] < m1['body'] * 0.5 and
                m4['is_bearish'] and m4['body'] < m1['body'] * 0.5 and
                m5['is_bullish'] and m5['body_ratio'] > 0.6 and
                m5['close'] > m1['close'] and
                m2['low'] > m1['low'] and m3['low'] > m1['low'] and m4['low'] > m1['low']):
                patterns.append(CandlePattern(
                    name='rising_three_methods',
                    pattern_type=PatternType.BULLISH_CONTINUATION,
                    strength=0.8,
                    candles_used=5,
                    description="Strong bullish continuation - rest then resume"
                ))
        
        # Falling Three Methods - long bearish → 3 small bullish inside → long bearish
        if len(metrics) >= 5:
            m1, m2, m3, m4, m5 = metrics[-5], metrics[-4], metrics[-3], metrics[-2], metrics[-1]
            if (m1['is_bearish'] and m1['body_ratio'] > 0.6 and
                m2['is_bullish'] and m2['body'] < m1['body'] * 0.5 and
                m3['is_bullish'] and m3['body'] < m1['body'] * 0.5 and
                m4['is_bullish'] and m4['body'] < m1['body'] * 0.5 and
                m5['is_bearish'] and m5['body_ratio'] > 0.6 and
                m5['close'] < m1['close'] and
                m2['high'] < m1['high'] and m3['high'] < m1['high'] and m4['high'] < m1['high']):
                patterns.append(CandlePattern(
                    name='falling_three_methods',
                    pattern_type=PatternType.BEARISH_CONTINUATION,
                    strength=0.8,
                    candles_used=5,
                    description="Strong bearish continuation - rest then resume"
                ))
        
        # Mat Hold Bullish - bullish → gap up → 3 small bearish → bullish above high
        if len(metrics) >= 5:
            m1, m2, m3, m4, m5 = metrics[-5], metrics[-4], metrics[-3], metrics[-2], metrics[-1]
            if (m1['is_bullish'] and m1['body_ratio'] > 0.6 and
                m2['open'] > m1['close'] and  # Gap up
                m2['body_ratio'] < 0.4 and m3['body_ratio'] < 0.4 and m4['body_ratio'] < 0.4 and
                m5['is_bullish'] and m5['close'] > m1['high']):
                patterns.append(CandlePattern(
                    name='mat_hold_bullish',
                    pattern_type=PatternType.BULLISH_CONTINUATION,
                    strength=0.8,
                    candles_used=5,
                    description="Strong bullish continuation - gap up mat hold"
                ))
        
        # Mat Hold Bearish - bearish → gap down → 3 small bullish → bearish below low
        if len(metrics) >= 5:
            m1, m2, m3, m4, m5 = metrics[-5], metrics[-4], metrics[-3], metrics[-2], metrics[-1]
            if (m1['is_bearish'] and m1['body_ratio'] > 0.6 and
                m2['open'] < m1['close'] and  # Gap down
                m2['body_ratio'] < 0.4 and m3['body_ratio'] < 0.4 and m4['body_ratio'] < 0.4 and
                m5['is_bearish'] and m5['close'] < m1['low']):
                patterns.append(CandlePattern(
                    name='mat_hold_bearish',
                    pattern_type=PatternType.BEARISH_CONTINUATION,
                    strength=0.8,
                    candles_used=5,
                    description="Strong bearish continuation - gap down mat hold"
                ))
        
        # Continue with more patterns...
        patterns.extend(self._detect_multi_candle_patterns_part2(candles, metrics))
        
        return patterns
    
    def _detect_multi_candle_patterns_part2(self, candles: List[Dict[str, float]], metrics: List[Dict]) -> List[CandlePattern]:
        """Detect additional multi-candle patterns (Part 2)."""
        patterns = []
        
        # ============ REST/CONSOLIDATION PATTERNS ============
        
        # Bullish Rest After Rally - strong up → 2-4 small body candles → resumes up
        if len(metrics) >= 5:
            m1, m2, m3, m4, m5 = metrics[-5], metrics[-4], metrics[-3], metrics[-2], metrics[-1]
            if (m1['is_bullish'] and m1['body_ratio'] > 0.6 and
                m2['body_ratio'] < 0.3 and m3['body_ratio'] < 0.3 and
                m4['body_ratio'] < 0.3 and
                m5['is_bullish'] and m5['close'] > m1['close']):
                patterns.append(CandlePattern(
                    name='bullish_rest_after_rally',
                    pattern_type=PatternType.BULLISH_CONTINUATION,
                    strength=0.65,
                    candles_used=5,
                    description="Bullish continuation - consolidation then breakout"
                ))
        
        # Bearish Rest After Decline - strong down → 2-4 small body candles → resumes down
        if len(metrics) >= 5:
            m1, m2, m3, m4, m5 = metrics[-5], metrics[-4], metrics[-3], metrics[-2], metrics[-1]
            if (m1['is_bearish'] and m1['body_ratio'] > 0.6 and
                m2['body_ratio'] < 0.3 and m3['body_ratio'] < 0.3 and
                m4['body_ratio'] < 0.3 and
                m5['is_bearish'] and m5['close'] < m1['close']):
                patterns.append(CandlePattern(
                    name='bearish_rest_after_decline',
                    pattern_type=PatternType.BEARISH_CONTINUATION,
                    strength=0.65,
                    candles_used=5,
                    description="Bearish continuation - consolidation then breakdown"
                ))
        
        # Bull Flag - strong up → slight downward channel → breakout
        if len(metrics) >= 6:
            m1 = metrics[-6]
            middle = metrics[-5:-1]
            m_last = metrics[-1]
            # Check for strong initial move
            if m1['is_bullish'] and m1['body_ratio'] > 0.6:
                # Check for slight pullback (lower highs and lower lows)
                highs_descending = all(middle[i]['high'] > middle[i+1]['high'] for i in range(len(middle)-1))
                # Check for breakout
                if highs_descending and m_last['is_bullish'] and m_last['close'] > middle[0]['high']:
                    patterns.append(CandlePattern(
                        name='bull_flag',
                        pattern_type=PatternType.BULLISH_CONTINUATION,
                        strength=0.75,
                        candles_used=6,
                        description="Bullish continuation - flag pattern breakout"
                    ))
        
        # Bear Flag - strong down → slight upward channel → breakdown
        if len(metrics) >= 6:
            m1 = metrics[-6]
            middle = metrics[-5:-1]
            m_last = metrics[-1]
            if m1['is_bearish'] and m1['body_ratio'] > 0.6:
                lows_ascending = all(middle[i]['low'] < middle[i+1]['low'] for i in range(len(middle)-1))
                if lows_ascending and m_last['is_bearish'] and m_last['close'] < middle[0]['low']:
                    patterns.append(CandlePattern(
                        name='bear_flag',
                        pattern_type=PatternType.BEARISH_CONTINUATION,
                        strength=0.75,
                        candles_used=6,
                        description="Bearish continuation - flag pattern breakdown"
                    ))
        
        # ============ THRUST PATTERNS ============
        
        # Bullish Thrust - gap up → brief pullback → new high
        if len(metrics) >= 4:
            m1, m2, m3, m4 = metrics[-4], metrics[-3], metrics[-2], metrics[-1]
            if (m2['open'] > m1['high'] and  # Gap up
                m3['close'] < m2['close'] and  # Pullback
                m4['is_bullish'] and m4['close'] > m2['high']):  # New high
                patterns.append(CandlePattern(
                    name='bullish_thrust',
                    pattern_type=PatternType.BULLISH_CONTINUATION,
                    strength=0.7,
                    candles_used=4,
                    description="Bullish continuation - thrust after gap"
                ))
        
        # Bearish Thrust - gap down → brief bounce → new low
        if len(metrics) >= 4:
            m1, m2, m3, m4 = metrics[-4], metrics[-3], metrics[-2], metrics[-1]
            if (m2['open'] < m1['low'] and  # Gap down
                m3['close'] > m2['close'] and  # Bounce
                m4['is_bearish'] and m4['close'] < m2['low']):  # New low
                patterns.append(CandlePattern(
                    name='bearish_thrust',
                    pattern_type=PatternType.BEARISH_CONTINUATION,
                    strength=0.7,
                    candles_used=4,
                    description="Bearish continuation - thrust after gap"
                ))
        
        # ============ BREAKAWAY PATTERNS ============
        
        # Breakaway Bullish - long bearish → 3 mixed → gap up bullish
        if len(metrics) >= 5:
            m1, m2, m3, m4, m5 = metrics[-5], metrics[-4], metrics[-3], metrics[-2], metrics[-1]
            if (m1['is_bearish'] and m1['body_ratio'] > 0.6 and
                m5['is_bullish'] and m5['open'] > m4['high']):  # Gap up
                patterns.append(CandlePattern(
                    name='breakaway_bullish',
                    pattern_type=PatternType.BULLISH_REVERSAL,
                    strength=0.75,
                    candles_used=5,
                    description="Bullish reversal - breakaway gap after decline"
                ))
        
        # Breakaway Bearish - long bullish → 3 mixed → gap down bearish
        if len(metrics) >= 5:
            m1, m2, m3, m4, m5 = metrics[-5], metrics[-4], metrics[-3], metrics[-2], metrics[-1]
            if (m1['is_bullish'] and m1['body_ratio'] > 0.6 and
                m5['is_bearish'] and m5['open'] < m4['low']):  # Gap down
                patterns.append(CandlePattern(
                    name='breakaway_bearish',
                    pattern_type=PatternType.BEARISH_REVERSAL,
                    strength=0.75,
                    candles_used=5,
                    description="Bearish reversal - breakaway gap after rally"
                ))
        
        # ============ INSIDE BAR PATTERNS ============
        
        # Inside Bar Bullish Breakout - inside bar → breakout above mother bar high
        if len(metrics) >= 3:
            m1, m2, m3 = metrics[-3], metrics[-2], metrics[-1]
            if (m2['high'] < m1['high'] and m2['low'] > m1['low'] and  # Inside bar
                m3['is_bullish'] and m3['close'] > m1['high']):  # Breakout
                patterns.append(CandlePattern(
                    name='inside_bar_bullish_breakout',
                    pattern_type=PatternType.BULLISH_CONTINUATION,
                    strength=0.7,
                    candles_used=3,
                    description="Bullish continuation - inside bar breakout"
                ))
        
        # Inside Bar Bearish Breakout - inside bar → breakout below mother bar low
        if len(metrics) >= 3:
            m1, m2, m3 = metrics[-3], metrics[-2], metrics[-1]
            if (m2['high'] < m1['high'] and m2['low'] > m1['low'] and  # Inside bar
                m3['is_bearish'] and m3['close'] < m1['low']):  # Breakdown
                patterns.append(CandlePattern(
                    name='inside_bar_bearish_breakout',
                    pattern_type=PatternType.BEARISH_CONTINUATION,
                    strength=0.7,
                    candles_used=3,
                    description="Bearish continuation - inside bar breakdown"
                ))
        
        # Multiple Inside Bars Bullish - 2-3 consecutive inside bars → breakout up
        if len(metrics) >= 4:
            m1, m2, m3, m4 = metrics[-4], metrics[-3], metrics[-2], metrics[-1]
            if (m2['high'] < m1['high'] and m2['low'] > m1['low'] and  # First inside
                m3['high'] < m1['high'] and m3['low'] > m1['low'] and  # Second inside
                m4['is_bullish'] and m4['close'] > m1['high']):  # Breakout
                patterns.append(CandlePattern(
                    name='multiple_inside_bars_bullish',
                    pattern_type=PatternType.BULLISH_CONTINUATION,
                    strength=0.75,
                    candles_used=4,
                    description="Bullish continuation - multiple inside bars breakout"
                ))
        
        # Multiple Inside Bars Bearish - 2-3 consecutive inside bars → breakout down
        if len(metrics) >= 4:
            m1, m2, m3, m4 = metrics[-4], metrics[-3], metrics[-2], metrics[-1]
            if (m2['high'] < m1['high'] and m2['low'] > m1['low'] and
                m3['high'] < m1['high'] and m3['low'] > m1['low'] and
                m4['is_bearish'] and m4['close'] < m1['low']):
                patterns.append(CandlePattern(
                    name='multiple_inside_bars_bearish',
                    pattern_type=PatternType.BEARISH_CONTINUATION,
                    strength=0.75,
                    candles_used=4,
                    description="Bearish continuation - multiple inside bars breakdown"
                ))
        
        # ============ SQUEEZE/NR PATTERNS ============
        
        # NR4 Bullish - narrowest range of 4 bars → breakout up
        if len(metrics) >= 5:
            ranges = [m['range'] for m in metrics[-5:-1]]
            current_range = metrics[-2]['range']
            m_last = metrics[-1]
            if current_range < min(ranges) and m_last['is_bullish']:
                patterns.append(CandlePattern(
                    name='nr4_bullish',
                    pattern_type=PatternType.BULLISH_CONTINUATION,
                    strength=0.7,
                    candles_used=5,
                    description="Bullish continuation - NR4 breakout"
                ))
        
        # NR4 Bearish - narrowest range of 4 bars → breakout down
        if len(metrics) >= 5:
            ranges = [m['range'] for m in metrics[-5:-1]]
            current_range = metrics[-2]['range']
            m_last = metrics[-1]
            if current_range < min(ranges) and m_last['is_bearish']:
                patterns.append(CandlePattern(
                    name='nr4_bearish',
                    pattern_type=PatternType.BEARISH_CONTINUATION,
                    strength=0.7,
                    candles_used=5,
                    description="Bearish continuation - NR4 breakdown"
                ))
        
        # NR7 Bullish - narrowest range of 7 bars → breakout up
        if len(metrics) >= 7:
            ranges = [m['range'] for m in metrics[-7:-1]]
            current_range = metrics[-2]['range']
            m_last = metrics[-1]
            if current_range < min(ranges) and m_last['is_bullish']:
                patterns.append(CandlePattern(
                    name='nr7_bullish',
                    pattern_type=PatternType.BULLISH_CONTINUATION,
                    strength=0.75,
                    candles_used=7,
                    description="Bullish continuation - NR7 breakout (stronger squeeze)"
                ))
        
        # NR7 Bearish - narrowest range of 7 bars → breakout down
        if len(metrics) >= 7:
            ranges = [m['range'] for m in metrics[-7:-1]]
            current_range = metrics[-2]['range']
            m_last = metrics[-1]
            if current_range < min(ranges) and m_last['is_bearish']:
                patterns.append(CandlePattern(
                    name='nr7_bearish',
                    pattern_type=PatternType.BEARISH_CONTINUATION,
                    strength=0.75,
                    candles_used=7,
                    description="Bearish continuation - NR7 breakdown (stronger squeeze)"
                ))
        
        # ============ STALLING PATTERNS ============
        
        # Bullish Stalled - three bullish, third small body at highs
        if len(metrics) >= 3:
            m1, m2, m3 = metrics[-3], metrics[-2], metrics[-1]
            if (m1['is_bullish'] and m1['body_ratio'] > 0.5 and
                m2['is_bullish'] and m2['body_ratio'] > 0.5 and
                m3['is_bullish'] and m3['body_ratio'] < 0.3 and
                m3['close'] > m2['close']):
                patterns.append(CandlePattern(
                    name='bullish_stalled',
                    pattern_type=PatternType.NEUTRAL,
                    strength=0.5,
                    candles_used=3,
                    description="Neutral - momentum stalling, watch for reversal"
                ))
        
        # Bearish Stalled - three bearish, third small body at lows
        if len(metrics) >= 3:
            m1, m2, m3 = metrics[-3], metrics[-2], metrics[-1]
            if (m1['is_bearish'] and m1['body_ratio'] > 0.5 and
                m2['is_bearish'] and m2['body_ratio'] > 0.5 and
                m3['is_bearish'] and m3['body_ratio'] < 0.3 and
                m3['close'] < m2['close']):
                patterns.append(CandlePattern(
                    name='bearish_stalled',
                    pattern_type=PatternType.NEUTRAL,
                    strength=0.5,
                    candles_used=3,
                    description="Neutral - momentum stalling, watch for reversal"
                ))
        
        # Spinning Top Series Bullish - multiple spinning tops after up move → breakout
        if len(metrics) >= 4:
            m1, m2, m3, m4 = metrics[-4], metrics[-3], metrics[-2], metrics[-1]
            if (m1['is_bullish'] and m1['body_ratio'] > 0.5 and
                m2['body_ratio'] < 0.3 and m3['body_ratio'] < 0.3 and
                m4['is_bullish'] and m4['close'] > max(m2['high'], m3['high'])):
                patterns.append(CandlePattern(
                    name='spinning_top_series_bullish',
                    pattern_type=PatternType.BULLISH_CONTINUATION,
                    strength=0.6,
                    candles_used=4,
                    description="Bullish continuation - indecision resolved higher"
                ))
        
        # Spinning Top Series Bearish - multiple spinning tops after down move → breakdown
        if len(metrics) >= 4:
            m1, m2, m3, m4 = metrics[-4], metrics[-3], metrics[-2], metrics[-1]
            if (m1['is_bearish'] and m1['body_ratio'] > 0.5 and
                m2['body_ratio'] < 0.3 and m3['body_ratio'] < 0.3 and
                m4['is_bearish'] and m4['close'] < min(m2['low'], m3['low'])):
                patterns.append(CandlePattern(
                    name='spinning_top_series_bearish',
                    pattern_type=PatternType.BEARISH_CONTINUATION,
                    strength=0.6,
                    candles_used=4,
                    description="Bearish continuation - indecision resolved lower"
                ))
        
        return patterns
    
    def _find_swing_points(self, candles: List[Dict[str, float]], lookback: int = 3) -> tuple:
        """Find swing highs and swing lows in candle data."""
        swing_highs = []
        swing_lows = []
        
        for i in range(lookback, len(candles) - lookback):
            # Swing high: higher than lookback candles on both sides
            is_swing_high = True
            is_swing_low = True
            
            for j in range(1, lookback + 1):
                if candles[i]['high'] <= candles[i-j]['high'] or candles[i]['high'] <= candles[i+j]['high']:
                    is_swing_high = False
                if candles[i]['low'] >= candles[i-j]['low'] or candles[i]['low'] >= candles[i+j]['low']:
                    is_swing_low = False
            
            if is_swing_high:
                swing_highs.append((i, candles[i]['high']))
            if is_swing_low:
                swing_lows.append((i, candles[i]['low']))
        
        return swing_highs, swing_lows
    
    def _detect_structure_patterns(self, candles: List[Dict[str, float]]) -> List[CandlePattern]:
        """Detect sloped/structure patterns (wedges, channels, triangles, H&S, etc.)."""
        patterns = []
        
        if len(candles) < 10:
            return patterns
        
        # Find swing points
        swing_highs, swing_lows = self._find_swing_points(candles[-20:] if len(candles) >= 20 else candles)
        
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return patterns
        
        # Get recent swing points for pattern detection
        recent_highs = swing_highs[-3:] if len(swing_highs) >= 3 else swing_highs
        recent_lows = swing_lows[-3:] if len(swing_lows) >= 3 else swing_lows
        
        # ============ WEDGE PATTERNS ============
        
        # Rising Wedge - higher highs + higher lows converging (bearish)
        if len(recent_highs) >= 2 and len(recent_lows) >= 2:
            hh_slope = (recent_highs[-1][1] - recent_highs[0][1]) / max(1, recent_highs[-1][0] - recent_highs[0][0])
            hl_slope = (recent_lows[-1][1] - recent_lows[0][1]) / max(1, recent_lows[-1][0] - recent_lows[0][0])
            
            # Rising wedge: both slopes positive, highs slope < lows slope (converging upward)
            if hh_slope > 0 and hl_slope > 0 and hl_slope > hh_slope:
                patterns.append(CandlePattern(
                    name='rising_wedge',
                    pattern_type=PatternType.BEARISH_REVERSAL,
                    strength=0.75,
                    candles_used=len(candles),
                    description="Bearish reversal - rising wedge, expect breakdown"
                ))
        
        # Falling Wedge - lower highs + lower lows converging (bullish)
        if len(recent_highs) >= 2 and len(recent_lows) >= 2:
            lh_slope = (recent_highs[-1][1] - recent_highs[0][1]) / max(1, recent_highs[-1][0] - recent_highs[0][0])
            ll_slope = (recent_lows[-1][1] - recent_lows[0][1]) / max(1, recent_lows[-1][0] - recent_lows[0][0])
            
            # Falling wedge: both slopes negative, lows slope < highs slope (converging downward)
            if lh_slope < 0 and ll_slope < 0 and lh_slope > ll_slope:
                patterns.append(CandlePattern(
                    name='falling_wedge',
                    pattern_type=PatternType.BULLISH_REVERSAL,
                    strength=0.75,
                    candles_used=len(candles),
                    description="Bullish reversal - falling wedge, expect breakout"
                ))
        
        # Broadening Wedge Ascending - expanding higher highs/higher lows
        if len(recent_highs) >= 2 and len(recent_lows) >= 2:
            hh_slope = (recent_highs[-1][1] - recent_highs[0][1]) / max(1, recent_highs[-1][0] - recent_highs[0][0])
            hl_slope = (recent_lows[-1][1] - recent_lows[0][1]) / max(1, recent_lows[-1][0] - recent_lows[0][0])
            
            if hh_slope > 0 and hl_slope > 0 and hh_slope > hl_slope:
                patterns.append(CandlePattern(
                    name='broadening_wedge_ascending',
                    pattern_type=PatternType.BEARISH_REVERSAL,
                    strength=0.65,
                    candles_used=len(candles),
                    description="Bearish - expanding volatility in uptrend"
                ))
        
        # Broadening Wedge Descending - expanding lower highs/lower lows
        if len(recent_highs) >= 2 and len(recent_lows) >= 2:
            lh_slope = (recent_highs[-1][1] - recent_highs[0][1]) / max(1, recent_highs[-1][0] - recent_highs[0][0])
            ll_slope = (recent_lows[-1][1] - recent_lows[0][1]) / max(1, recent_lows[-1][0] - recent_lows[0][0])
            
            if lh_slope < 0 and ll_slope < 0 and ll_slope < lh_slope:
                patterns.append(CandlePattern(
                    name='broadening_wedge_descending',
                    pattern_type=PatternType.BULLISH_REVERSAL,
                    strength=0.65,
                    candles_used=len(candles),
                    description="Bullish - expanding volatility in downtrend"
                ))
        
        # ============ CHANNEL PATTERNS ============
        
        # Ascending Channel - parallel upward sloping support/resistance
        if len(recent_highs) >= 2 and len(recent_lows) >= 2:
            hh_slope = (recent_highs[-1][1] - recent_highs[0][1]) / max(1, recent_highs[-1][0] - recent_highs[0][0])
            hl_slope = (recent_lows[-1][1] - recent_lows[0][1]) / max(1, recent_lows[-1][0] - recent_lows[0][0])
            
            # Ascending channel: both slopes positive and similar
            if hh_slope > 0 and hl_slope > 0 and abs(hh_slope - hl_slope) < abs(hh_slope) * 0.3:
                patterns.append(CandlePattern(
                    name='ascending_channel',
                    pattern_type=PatternType.BULLISH_CONTINUATION,
                    strength=0.7,
                    candles_used=len(candles),
                    description="Bullish continuation - ascending channel"
                ))
        
        # Descending Channel - parallel downward sloping support/resistance
        if len(recent_highs) >= 2 and len(recent_lows) >= 2:
            lh_slope = (recent_highs[-1][1] - recent_highs[0][1]) / max(1, recent_highs[-1][0] - recent_highs[0][0])
            ll_slope = (recent_lows[-1][1] - recent_lows[0][1]) / max(1, recent_lows[-1][0] - recent_lows[0][0])
            
            if lh_slope < 0 and ll_slope < 0 and abs(lh_slope - ll_slope) < abs(lh_slope) * 0.3:
                patterns.append(CandlePattern(
                    name='descending_channel',
                    pattern_type=PatternType.BEARISH_CONTINUATION,
                    strength=0.7,
                    candles_used=len(candles),
                    description="Bearish continuation - descending channel"
                ))
        
        # Horizontal Channel - flat support/resistance
        if len(recent_highs) >= 2 and len(recent_lows) >= 2:
            avg_high = sum(h[1] for h in recent_highs) / len(recent_highs)
            avg_low = sum(l[1] for l in recent_lows) / len(recent_lows)
            high_range = max(h[1] for h in recent_highs) - min(h[1] for h in recent_highs)
            low_range = max(l[1] for l in recent_lows) - min(l[1] for l in recent_lows)
            
            # Horizontal if range is small relative to channel height
            channel_height = avg_high - avg_low
            if high_range < channel_height * 0.2 and low_range < channel_height * 0.2:
                patterns.append(CandlePattern(
                    name='horizontal_channel',
                    pattern_type=PatternType.NEUTRAL,
                    strength=0.5,
                    candles_used=len(candles),
                    description="Neutral - ranging, wait for breakout"
                ))
        
        # ============ TRIANGLE PATTERNS ============
        
        # Ascending Triangle - flat resistance + rising support
        if len(recent_highs) >= 2 and len(recent_lows) >= 2:
            high_range = max(h[1] for h in recent_highs) - min(h[1] for h in recent_highs)
            avg_high = sum(h[1] for h in recent_highs) / len(recent_highs)
            hl_slope = (recent_lows[-1][1] - recent_lows[0][1]) / max(1, recent_lows[-1][0] - recent_lows[0][0])
            
            if high_range < avg_high * 0.01 and hl_slope > 0:  # Flat highs, rising lows
                patterns.append(CandlePattern(
                    name='ascending_triangle',
                    pattern_type=PatternType.BULLISH_CONTINUATION,
                    strength=0.75,
                    candles_used=len(candles),
                    description="Bullish - ascending triangle, expect breakout"
                ))
        
        # Descending Triangle - flat support + falling resistance
        if len(recent_highs) >= 2 and len(recent_lows) >= 2:
            low_range = max(l[1] for l in recent_lows) - min(l[1] for l in recent_lows)
            avg_low = sum(l[1] for l in recent_lows) / len(recent_lows)
            lh_slope = (recent_highs[-1][1] - recent_highs[0][1]) / max(1, recent_highs[-1][0] - recent_highs[0][0])
            
            if low_range < avg_low * 0.01 and lh_slope < 0:  # Flat lows, falling highs
                patterns.append(CandlePattern(
                    name='descending_triangle',
                    pattern_type=PatternType.BEARISH_CONTINUATION,
                    strength=0.75,
                    candles_used=len(candles),
                    description="Bearish - descending triangle, expect breakdown"
                ))
        
        # Symmetrical Triangle - converging highs and lows
        if len(recent_highs) >= 2 and len(recent_lows) >= 2:
            hh_slope = (recent_highs[-1][1] - recent_highs[0][1]) / max(1, recent_highs[-1][0] - recent_highs[0][0])
            hl_slope = (recent_lows[-1][1] - recent_lows[0][1]) / max(1, recent_lows[-1][0] - recent_lows[0][0])
            
            if hh_slope < 0 and hl_slope > 0:  # Falling highs, rising lows
                patterns.append(CandlePattern(
                    name='symmetrical_triangle',
                    pattern_type=PatternType.NEUTRAL,
                    strength=0.65,
                    candles_used=len(candles),
                    description="Neutral - symmetrical triangle, breakout either way"
                ))
        
        # Expanding Triangle (Megaphone) - diverging highs and lows
        if len(recent_highs) >= 2 and len(recent_lows) >= 2:
            hh_slope = (recent_highs[-1][1] - recent_highs[0][1]) / max(1, recent_highs[-1][0] - recent_highs[0][0])
            ll_slope = (recent_lows[-1][1] - recent_lows[0][1]) / max(1, recent_lows[-1][0] - recent_lows[0][0])
            
            if hh_slope > 0 and ll_slope < 0:  # Rising highs, falling lows
                patterns.append(CandlePattern(
                    name='expanding_triangle',
                    pattern_type=PatternType.NEUTRAL,
                    strength=0.55,
                    candles_used=len(candles),
                    description="Neutral - expanding volatility, high risk"
                ))
        
        # ============ PENNANT PATTERNS (STRUCTURE) ============
        
        # Bullish Pennant Structure - small symmetrical triangle after up move
        if len(candles) >= 15:
            metrics = [self._get_candle_metrics(c) for c in candles[-15:]]
            first_5 = metrics[:5]
            last_10 = metrics[5:]
            
            # Check for strong initial up move
            up_move = sum(1 for m in first_5 if m['is_bullish'])
            if up_move >= 4:
                # Check for converging triangle in last 10
                high_range = max(m['high'] for m in last_10) - min(m['high'] for m in last_10)
                low_range = max(m['low'] for m in last_10) - min(m['low'] for m in last_10)
                avg_range = sum(m['range'] for m in last_10) / 10
                
                if high_range < avg_range * 3 and low_range < avg_range * 3:
                    patterns.append(CandlePattern(
                        name='bullish_pennant_structure',
                        pattern_type=PatternType.BULLISH_CONTINUATION,
                        strength=0.75,
                        candles_used=15,
                        description="Bullish continuation - pennant after rally"
                    ))
        
        # Bearish Pennant Structure - small symmetrical triangle after down move
        if len(candles) >= 15:
            metrics = [self._get_candle_metrics(c) for c in candles[-15:]]
            first_5 = metrics[:5]
            last_10 = metrics[5:]
            
            down_move = sum(1 for m in first_5 if m['is_bearish'])
            if down_move >= 4:
                high_range = max(m['high'] for m in last_10) - min(m['high'] for m in last_10)
                low_range = max(m['low'] for m in last_10) - min(m['low'] for m in last_10)
                avg_range = sum(m['range'] for m in last_10) / 10
                
                if high_range < avg_range * 3 and low_range < avg_range * 3:
                    patterns.append(CandlePattern(
                        name='bearish_pennant_structure',
                        pattern_type=PatternType.BEARISH_CONTINUATION,
                        strength=0.75,
                        candles_used=15,
                        description="Bearish continuation - pennant after decline"
                    ))
        
        # ============ REVERSAL STRUCTURES ============
        
        # Head and Shoulders - left shoulder, head (higher), right shoulder
        if len(swing_highs) >= 3:
            h1, h2, h3 = swing_highs[-3:]
            # Head should be highest, shoulders similar
            if (h2[1] > h1[1] and h2[1] > h3[1] and
                abs(h1[1] - h3[1]) < (h2[1] - min(h1[1], h3[1])) * 0.3):
                patterns.append(CandlePattern(
                    name='head_and_shoulders',
                    pattern_type=PatternType.BEARISH_REVERSAL,
                    strength=0.85,
                    candles_used=len(candles),
                    description="Strong bearish reversal - head and shoulders top"
                ))
        
        # Inverse Head and Shoulders - left shoulder, head (lower), right shoulder
        if len(swing_lows) >= 3:
            l1, l2, l3 = swing_lows[-3:]
            # Head should be lowest, shoulders similar
            if (l2[1] < l1[1] and l2[1] < l3[1] and
                abs(l1[1] - l3[1]) < (max(l1[1], l3[1]) - l2[1]) * 0.3):
                patterns.append(CandlePattern(
                    name='inverse_head_and_shoulders',
                    pattern_type=PatternType.BULLISH_REVERSAL,
                    strength=0.85,
                    candles_used=len(candles),
                    description="Strong bullish reversal - inverse head and shoulders"
                ))
        
        # Double Top - two peaks at similar level
        if len(swing_highs) >= 2:
            h1, h2 = swing_highs[-2:]
            avg_high = (h1[1] + h2[1]) / 2
            if abs(h1[1] - h2[1]) < avg_high * 0.01:  # Within 1%
                patterns.append(CandlePattern(
                    name='double_top',
                    pattern_type=PatternType.BEARISH_REVERSAL,
                    strength=0.8,
                    candles_used=len(candles),
                    description="Bearish reversal - double top resistance"
                ))
        
        # Double Bottom - two troughs at similar level
        if len(swing_lows) >= 2:
            l1, l2 = swing_lows[-2:]
            avg_low = (l1[1] + l2[1]) / 2
            if abs(l1[1] - l2[1]) < avg_low * 0.01:  # Within 1%
                patterns.append(CandlePattern(
                    name='double_bottom',
                    pattern_type=PatternType.BULLISH_REVERSAL,
                    strength=0.8,
                    candles_used=len(candles),
                    description="Bullish reversal - double bottom support"
                ))
        
        # Triple Top - three peaks at similar level
        if len(swing_highs) >= 3:
            h1, h2, h3 = swing_highs[-3:]
            avg_high = (h1[1] + h2[1] + h3[1]) / 3
            if (abs(h1[1] - avg_high) < avg_high * 0.01 and
                abs(h2[1] - avg_high) < avg_high * 0.01 and
                abs(h3[1] - avg_high) < avg_high * 0.01):
                patterns.append(CandlePattern(
                    name='triple_top',
                    pattern_type=PatternType.BEARISH_REVERSAL,
                    strength=0.85,
                    candles_used=len(candles),
                    description="Strong bearish reversal - triple top resistance"
                ))
        
        # Triple Bottom - three troughs at similar level
        if len(swing_lows) >= 3:
            l1, l2, l3 = swing_lows[-3:]
            avg_low = (l1[1] + l2[1] + l3[1]) / 3
            if (abs(l1[1] - avg_low) < avg_low * 0.01 and
                abs(l2[1] - avg_low) < avg_low * 0.01 and
                abs(l3[1] - avg_low) < avg_low * 0.01):
                patterns.append(CandlePattern(
                    name='triple_bottom',
                    pattern_type=PatternType.BULLISH_REVERSAL,
                    strength=0.85,
                    candles_used=len(candles),
                    description="Strong bullish reversal - triple bottom support"
                ))
        
        # ============ ROUNDED/CURVED PATTERNS ============
        
        # Rounding Top - gradual curved top formation
        if len(candles) >= 15:
            prices = [(c['high'] + c['low']) / 2 for c in candles[-15:]]
            # Check for arc shape: rises then falls
            mid_idx = len(prices) // 2
            first_half = prices[:mid_idx]
            second_half = prices[mid_idx:]
            
            # Rising first half, falling second half
            first_rising = sum(1 for i in range(1, len(first_half)) if first_half[i] > first_half[i-1])
            second_falling = sum(1 for i in range(1, len(second_half)) if second_half[i] < second_half[i-1])
            
            if first_rising >= mid_idx * 0.6 and second_falling >= len(second_half) * 0.6:
                # Check for smooth curve (no sharp spikes)
                max_idx = prices.index(max(prices))
                if mid_idx - 2 <= max_idx <= mid_idx + 2:  # Peak near middle
                    patterns.append(CandlePattern(
                        name='rounding_top',
                        pattern_type=PatternType.BEARISH_REVERSAL,
                        strength=0.75,
                        candles_used=15,
                        description="Bearish reversal - gradual rounding top"
                    ))
        
        # Rounding Bottom - gradual curved bottom formation
        if len(candles) >= 15:
            prices = [(c['high'] + c['low']) / 2 for c in candles[-15:]]
            mid_idx = len(prices) // 2
            first_half = prices[:mid_idx]
            second_half = prices[mid_idx:]
            
            # Falling first half, rising second half
            first_falling = sum(1 for i in range(1, len(first_half)) if first_half[i] < first_half[i-1])
            second_rising = sum(1 for i in range(1, len(second_half)) if second_half[i] > second_half[i-1])
            
            if first_falling >= mid_idx * 0.6 and second_rising >= len(second_half) * 0.6:
                min_idx = prices.index(min(prices))
                if mid_idx - 2 <= min_idx <= mid_idx + 2:  # Trough near middle
                    patterns.append(CandlePattern(
                        name='rounding_bottom',
                        pattern_type=PatternType.BULLISH_REVERSAL,
                        strength=0.75,
                        candles_used=15,
                        description="Bullish reversal - gradual rounding bottom"
                    ))
        
        # Cup and Handle - U-shaped bottom + small pullback
        if len(candles) >= 20:
            prices = [(c['high'] + c['low']) / 2 for c in candles[-20:]]
            cup_section = prices[:15]
            handle_section = prices[15:]
            
            # Cup: falling then rising (U-shape)
            cup_mid = len(cup_section) // 2
            cup_first = cup_section[:cup_mid]
            cup_second = cup_section[cup_mid:]
            
            first_falling = sum(1 for i in range(1, len(cup_first)) if cup_first[i] < cup_first[i-1])
            second_rising = sum(1 for i in range(1, len(cup_second)) if cup_second[i] > cup_second[i-1])
            
            # Handle: small pullback (lower than cup rim but higher than cup bottom)
            cup_bottom = min(cup_section)
            cup_rim = max(cup_section[0], cup_section[-1])
            handle_low = min(handle_section)
            
            if (first_falling >= cup_mid * 0.5 and second_rising >= len(cup_second) * 0.5 and
                handle_low > cup_bottom and handle_low < cup_rim):
                patterns.append(CandlePattern(
                    name='cup_and_handle',
                    pattern_type=PatternType.BULLISH_CONTINUATION,
                    strength=0.8,
                    candles_used=20,
                    description="Bullish continuation - cup and handle breakout setup"
                ))
        
        # Inverted Cup and Handle - inverted U-top + small rally
        if len(candles) >= 20:
            prices = [(c['high'] + c['low']) / 2 for c in candles[-20:]]
            cup_section = prices[:15]
            handle_section = prices[15:]
            
            cup_mid = len(cup_section) // 2
            cup_first = cup_section[:cup_mid]
            cup_second = cup_section[cup_mid:]
            
            first_rising = sum(1 for i in range(1, len(cup_first)) if cup_first[i] > cup_first[i-1])
            second_falling = sum(1 for i in range(1, len(cup_second)) if cup_second[i] < cup_second[i-1])
            
            cup_top = max(cup_section)
            cup_rim = min(cup_section[0], cup_section[-1])
            handle_high = max(handle_section)
            
            if (first_rising >= cup_mid * 0.5 and second_falling >= len(cup_second) * 0.5 and
                handle_high < cup_top and handle_high > cup_rim):
                patterns.append(CandlePattern(
                    name='inverted_cup_and_handle',
                    pattern_type=PatternType.BEARISH_CONTINUATION,
                    strength=0.8,
                    candles_used=20,
                    description="Bearish continuation - inverted cup and handle breakdown setup"
                ))
        
        # Saucer Bottom - very gradual U-shape (longer than rounding bottom)
        if len(candles) >= 25:
            prices = [(c['high'] + c['low']) / 2 for c in candles[-25:]]
            mid_idx = len(prices) // 2
            first_half = prices[:mid_idx]
            second_half = prices[mid_idx:]
            
            # Gradual decline then gradual rise
            first_trend = (first_half[-1] - first_half[0]) / len(first_half)
            second_trend = (second_half[-1] - second_half[0]) / len(second_half)
            
            # Both trends should be gradual (small per-bar change)
            avg_range = sum(abs(prices[i] - prices[i-1]) for i in range(1, len(prices))) / len(prices)
            
            if first_trend < 0 and second_trend > 0 and abs(first_trend) < avg_range and abs(second_trend) < avg_range:
                min_idx = prices.index(min(prices))
                if mid_idx - 3 <= min_idx <= mid_idx + 3:
                    patterns.append(CandlePattern(
                        name='saucer_bottom',
                        pattern_type=PatternType.BULLISH_REVERSAL,
                        strength=0.7,
                        candles_used=25,
                        description="Bullish reversal - very gradual saucer bottom"
                    ))
        
        # Saucer Top - very gradual inverted U-shape
        if len(candles) >= 25:
            prices = [(c['high'] + c['low']) / 2 for c in candles[-25:]]
            mid_idx = len(prices) // 2
            first_half = prices[:mid_idx]
            second_half = prices[mid_idx:]
            
            first_trend = (first_half[-1] - first_half[0]) / len(first_half)
            second_trend = (second_half[-1] - second_half[0]) / len(second_half)
            
            avg_range = sum(abs(prices[i] - prices[i-1]) for i in range(1, len(prices))) / len(prices)
            
            if first_trend > 0 and second_trend < 0 and abs(first_trend) < avg_range and abs(second_trend) < avg_range:
                max_idx = prices.index(max(prices))
                if mid_idx - 3 <= max_idx <= mid_idx + 3:
                    patterns.append(CandlePattern(
                        name='saucer_top',
                        pattern_type=PatternType.BEARISH_REVERSAL,
                        strength=0.7,
                        candles_used=25,
                        description="Bearish reversal - very gradual saucer top"
                    ))
        
        return patterns
    
    def _detect_harmonic_patterns(self, candles: List[Dict[str, float]]) -> List[CandlePattern]:
        """Detect harmonic patterns (Gartley, Bat, Butterfly, Crab, Shark, Cypher, AB=CD, Three Drives)."""
        patterns = []
        
        if len(candles) < 15:
            return patterns
        
        # Find swing points for harmonic detection
        swing_highs, swing_lows = self._find_swing_points(candles[-30:] if len(candles) >= 30 else candles, lookback=2)
        
        # Need at least 5 points for XABCD patterns
        all_swings = sorted(swing_highs + swing_lows, key=lambda x: x[0])
        
        if len(all_swings) < 5:
            return patterns
        
        # Get the last 5 swing points for XABCD
        xabcd = all_swings[-5:]
        x_idx, x_price = xabcd[0]
        a_idx, a_price = xabcd[1]
        b_idx, b_price = xabcd[2]
        c_idx, c_price = xabcd[3]
        d_idx, d_price = xabcd[4]
        
        # Calculate Fibonacci ratios
        xa = abs(a_price - x_price)
        ab = abs(b_price - a_price)
        bc = abs(c_price - b_price)
        cd = abs(d_price - c_price)
        xd = abs(d_price - x_price)
        
        # Avoid division by zero
        if xa < 0.00001 or ab < 0.00001 or bc < 0.00001:
            return patterns
        
        ab_xa = ab / xa  # B retracement of XA
        bc_ab = bc / ab  # C retracement of AB
        cd_bc = cd / bc  # D extension of BC
        xd_xa = xd / xa  # D retracement of XA
        
        # Determine if bullish or bearish pattern
        is_bullish = d_price < x_price and d_price < a_price  # D is lowest = bullish reversal
        is_bearish = d_price > x_price and d_price > a_price  # D is highest = bearish reversal
        
        # Tolerance for Fibonacci ratios
        tol = 0.05
        
        # ============ GARTLEY PATTERN ============
        # AB = 0.618 of XA, BC = 0.382-0.886 of AB, CD = 1.27-1.618 of BC, D = 0.786 of XA
        if (0.618 - tol <= ab_xa <= 0.618 + tol and
            0.382 - tol <= bc_ab <= 0.886 + tol and
            1.27 - tol <= cd_bc <= 1.618 + tol and
            0.786 - tol <= xd_xa <= 0.786 + tol):
            if is_bullish:
                patterns.append(CandlePattern(
                    name='gartley_bullish',
                    pattern_type=PatternType.BULLISH_REVERSAL,
                    strength=0.85,
                    candles_used=d_idx - x_idx + 1,
                    description="Bullish Gartley - high probability reversal at D"
                ))
            elif is_bearish:
                patterns.append(CandlePattern(
                    name='gartley_bearish',
                    pattern_type=PatternType.BEARISH_REVERSAL,
                    strength=0.85,
                    candles_used=d_idx - x_idx + 1,
                    description="Bearish Gartley - high probability reversal at D"
                ))
        
        # ============ BAT PATTERN ============
        # AB = 0.382-0.50 of XA, BC = 0.382-0.886 of AB, CD = 1.618-2.618 of BC, D = 0.886 of XA
        if (0.382 - tol <= ab_xa <= 0.50 + tol and
            0.382 - tol <= bc_ab <= 0.886 + tol and
            1.618 - tol <= cd_bc <= 2.618 + tol and
            0.886 - tol <= xd_xa <= 0.886 + tol):
            if is_bullish:
                patterns.append(CandlePattern(
                    name='bat_bullish',
                    pattern_type=PatternType.BULLISH_REVERSAL,
                    strength=0.8,
                    candles_used=d_idx - x_idx + 1,
                    description="Bullish Bat - reversal at 0.886 XA"
                ))
            elif is_bearish:
                patterns.append(CandlePattern(
                    name='bat_bearish',
                    pattern_type=PatternType.BEARISH_REVERSAL,
                    strength=0.8,
                    candles_used=d_idx - x_idx + 1,
                    description="Bearish Bat - reversal at 0.886 XA"
                ))
        
        # ============ BUTTERFLY PATTERN ============
        # AB = 0.786 of XA, BC = 0.382-0.886 of AB, CD = 1.618-2.24 of BC, D = 1.27 of XA
        if (0.786 - tol <= ab_xa <= 0.786 + tol and
            0.382 - tol <= bc_ab <= 0.886 + tol and
            1.618 - tol <= cd_bc <= 2.24 + tol and
            1.27 - tol <= xd_xa <= 1.618 + tol):
            if is_bullish:
                patterns.append(CandlePattern(
                    name='butterfly_bullish',
                    pattern_type=PatternType.BULLISH_REVERSAL,
                    strength=0.8,
                    candles_used=d_idx - x_idx + 1,
                    description="Bullish Butterfly - extended reversal beyond X"
                ))
            elif is_bearish:
                patterns.append(CandlePattern(
                    name='butterfly_bearish',
                    pattern_type=PatternType.BEARISH_REVERSAL,
                    strength=0.8,
                    candles_used=d_idx - x_idx + 1,
                    description="Bearish Butterfly - extended reversal beyond X"
                ))
        
        # ============ CRAB PATTERN ============
        # AB = 0.382-0.618 of XA, BC = 0.382-0.886 of AB, CD = 2.24-3.618 of BC, D = 1.618 of XA
        if (0.382 - tol <= ab_xa <= 0.618 + tol and
            0.382 - tol <= bc_ab <= 0.886 + tol and
            2.24 - tol <= cd_bc <= 3.618 + tol and
            1.618 - tol <= xd_xa <= 1.618 + tol):
            if is_bullish:
                patterns.append(CandlePattern(
                    name='crab_bullish',
                    pattern_type=PatternType.BULLISH_REVERSAL,
                    strength=0.85,
                    candles_used=d_idx - x_idx + 1,
                    description="Bullish Crab - deep extension reversal at 1.618 XA"
                ))
            elif is_bearish:
                patterns.append(CandlePattern(
                    name='crab_bearish',
                    pattern_type=PatternType.BEARISH_REVERSAL,
                    strength=0.85,
                    candles_used=d_idx - x_idx + 1,
                    description="Bearish Crab - deep extension reversal at 1.618 XA"
                ))
        
        # ============ SHARK PATTERN ============
        # AB = 0.382-0.618 of XA, BC = 1.13-1.618 of AB, CD = 1.618-2.24 of BC, D = 0.886-1.13 of XA
        if (0.382 - tol <= ab_xa <= 0.618 + tol and
            1.13 - tol <= bc_ab <= 1.618 + tol and
            1.618 - tol <= cd_bc <= 2.24 + tol and
            0.886 - tol <= xd_xa <= 1.13 + tol):
            if is_bullish:
                patterns.append(CandlePattern(
                    name='shark_bullish',
                    pattern_type=PatternType.BULLISH_REVERSAL,
                    strength=0.75,
                    candles_used=d_idx - x_idx + 1,
                    description="Bullish Shark - aggressive reversal pattern"
                ))
            elif is_bearish:
                patterns.append(CandlePattern(
                    name='shark_bearish',
                    pattern_type=PatternType.BEARISH_REVERSAL,
                    strength=0.75,
                    candles_used=d_idx - x_idx + 1,
                    description="Bearish Shark - aggressive reversal pattern"
                ))
        
        # ============ CYPHER PATTERN ============
        # AB = 0.382-0.618 of XA, BC = 1.13-1.414 of AB, D = 0.786 of XC
        xc = abs(c_price - x_price)
        xd_xc = xd / xc if xc > 0.00001 else 0
        
        if (0.382 - tol <= ab_xa <= 0.618 + tol and
            1.13 - tol <= bc_ab <= 1.414 + tol and
            0.786 - tol <= xd_xc <= 0.786 + tol):
            if is_bullish:
                patterns.append(CandlePattern(
                    name='cypher_bullish',
                    pattern_type=PatternType.BULLISH_REVERSAL,
                    strength=0.75,
                    candles_used=d_idx - x_idx + 1,
                    description="Bullish Cypher - unique structure reversal"
                ))
            elif is_bearish:
                patterns.append(CandlePattern(
                    name='cypher_bearish',
                    pattern_type=PatternType.BEARISH_REVERSAL,
                    strength=0.75,
                    candles_used=d_idx - x_idx + 1,
                    description="Bearish Cypher - unique structure reversal"
                ))
        
        # ============ AB=CD PATTERNS ============
        # Simple: AB = CD (1.0), Extended: CD = 1.27 or 1.618 of AB
        
        # Get last 4 points for ABCD
        if len(all_swings) >= 4:
            abcd = all_swings[-4:]
            a2_idx, a2_price = abcd[0]
            b2_idx, b2_price = abcd[1]
            c2_idx, c2_price = abcd[2]
            d2_idx, d2_price = abcd[3]
            
            ab2 = abs(b2_price - a2_price)
            cd2 = abs(d2_price - c2_price)
            
            if ab2 > 0.00001:
                cd_ab = cd2 / ab2
                
                is_bullish_abcd = d2_price < a2_price  # D lower = bullish
                is_bearish_abcd = d2_price > a2_price  # D higher = bearish
                
                # Standard AB=CD (0.95-1.05 ratio)
                if 0.95 <= cd_ab <= 1.05:
                    if is_bullish_abcd:
                        patterns.append(CandlePattern(
                            name='abcd_bullish',
                            pattern_type=PatternType.BULLISH_REVERSAL,
                            strength=0.7,
                            candles_used=d2_idx - a2_idx + 1,
                            description="Bullish AB=CD - equal leg reversal"
                        ))
                    elif is_bearish_abcd:
                        patterns.append(CandlePattern(
                            name='abcd_bearish',
                            pattern_type=PatternType.BEARISH_REVERSAL,
                            strength=0.7,
                            candles_used=d2_idx - a2_idx + 1,
                            description="Bearish AB=CD - equal leg reversal"
                        ))
                
                # Extended AB=CD (1.27 or 1.618)
                if (1.27 - tol <= cd_ab <= 1.27 + tol) or (1.618 - tol <= cd_ab <= 1.618 + tol):
                    if is_bullish_abcd:
                        patterns.append(CandlePattern(
                            name='abcd_extension_bullish',
                            pattern_type=PatternType.BULLISH_REVERSAL,
                            strength=0.75,
                            candles_used=d2_idx - a2_idx + 1,
                            description="Bullish AB=CD Extension - Fibonacci extended leg"
                        ))
                    elif is_bearish_abcd:
                        patterns.append(CandlePattern(
                            name='abcd_extension_bearish',
                            pattern_type=PatternType.BEARISH_REVERSAL,
                            strength=0.75,
                            candles_used=d2_idx - a2_idx + 1,
                            description="Bearish AB=CD Extension - Fibonacci extended leg"
                        ))
        
        # ============ THREE DRIVES PATTERN ============
        # Three symmetric pushes with Fibonacci extensions
        if len(all_swings) >= 6:
            drives = all_swings[-6:]
            
            # Extract the 3 drive endpoints
            d1_price = drives[1][1]
            d2_price = drives[3][1]
            d3_price = drives[5][1]
            
            # Calculate drive lengths
            drive1 = abs(d1_price - drives[0][1])
            drive2 = abs(d2_price - drives[2][1])
            drive3 = abs(d3_price - drives[4][1])
            
            if drive1 > 0.00001 and drive2 > 0.00001:
                d2_d1 = drive2 / drive1
                d3_d2 = drive3 / drive2
                
                # Drives should be similar (1.27 or 1.618 extensions)
                valid_ratio = lambda r: (1.27 - tol <= r <= 1.27 + tol) or (1.618 - tol <= r <= 1.618 + tol) or (0.9 <= r <= 1.1)
                
                if valid_ratio(d2_d1) and valid_ratio(d3_d2):
                    # Bullish three drives: three lower lows
                    if d1_price < drives[0][1] and d2_price < d1_price and d3_price < d2_price:
                        patterns.append(CandlePattern(
                            name='three_drives_bullish',
                            pattern_type=PatternType.BULLISH_REVERSAL,
                            strength=0.8,
                            candles_used=drives[5][0] - drives[0][0] + 1,
                            description="Bullish Three Drives - exhaustion after 3 pushes down"
                        ))
                    
                    # Bearish three drives: three higher highs
                    if d1_price > drives[0][1] and d2_price > d1_price and d3_price > d2_price:
                        patterns.append(CandlePattern(
                            name='three_drives_bearish',
                            pattern_type=PatternType.BEARISH_REVERSAL,
                            strength=0.8,
                            candles_used=drives[5][0] - drives[0][0] + 1,
                            description="Bearish Three Drives - exhaustion after 3 pushes up"
                        ))
        
        return patterns
    
    def _detect_elliott_wave_patterns(self, candles: List[Dict[str, float]]) -> List[CandlePattern]:
        """Detect Elliott Wave patterns (impulse waves, corrections, diagonals)."""
        patterns = []
        
        if len(candles) < 20:
            return patterns
        
        # Find swing points for wave counting
        swing_highs, swing_lows = self._find_swing_points(candles[-40:] if len(candles) >= 40 else candles, lookback=2)
        
        # Combine and sort all swings
        all_swings = sorted(swing_highs + swing_lows, key=lambda x: x[0])
        
        if len(all_swings) < 5:
            return patterns
        
        # ============ IMPULSE WAVE (5-wave structure) ============
        # Wave 1-2-3-4-5 pattern
        if len(all_swings) >= 6:
            waves = all_swings[-6:]
            w0_price = waves[0][1]
            w1_price = waves[1][1]
            w2_price = waves[2][1]
            w3_price = waves[3][1]
            w4_price = waves[4][1]
            w5_price = waves[5][1]
            
            # Bullish impulse: 1 up, 2 down, 3 up (longest), 4 down, 5 up
            wave1 = w1_price - w0_price
            wave2 = w2_price - w1_price
            wave3 = w3_price - w2_price
            wave4 = w4_price - w3_price
            wave5 = w5_price - w4_price
            
            # Bullish impulse rules
            if (wave1 > 0 and wave2 < 0 and wave3 > 0 and wave4 < 0 and wave5 > 0 and
                abs(wave3) > abs(wave1) and abs(wave3) > abs(wave5) and  # Wave 3 longest
                w2_price > w0_price and  # Wave 2 doesn't retrace below wave 1 start
                w4_price > w1_price):  # Wave 4 doesn't overlap wave 1
                patterns.append(CandlePattern(
                    name='impulse_wave_bullish',
                    pattern_type=PatternType.BULLISH_CONTINUATION,
                    strength=0.8,
                    candles_used=waves[5][0] - waves[0][0] + 1,
                    description="Bullish Elliott Impulse - 5-wave up structure"
                ))
            
            # Bearish impulse rules
            if (wave1 < 0 and wave2 > 0 and wave3 < 0 and wave4 > 0 and wave5 < 0 and
                abs(wave3) > abs(wave1) and abs(wave3) > abs(wave5) and
                w2_price < w0_price and
                w4_price < w1_price):
                patterns.append(CandlePattern(
                    name='impulse_wave_bearish',
                    pattern_type=PatternType.BEARISH_CONTINUATION,
                    strength=0.8,
                    candles_used=waves[5][0] - waves[0][0] + 1,
                    description="Bearish Elliott Impulse - 5-wave down structure"
                ))
            
            # Wave 3 Extension (strongest wave)
            if wave1 > 0 and wave3 > 0:
                if abs(wave3) > abs(wave1) * 1.618:  # Wave 3 is 1.618+ of wave 1
                    patterns.append(CandlePattern(
                        name='wave_3_extension_bullish',
                        pattern_type=PatternType.BULLISH_CONTINUATION,
                        strength=0.85,
                        candles_used=waves[5][0] - waves[0][0] + 1,
                        description="Bullish Wave 3 Extension - powerful momentum"
                    ))
            
            if wave1 < 0 and wave3 < 0:
                if abs(wave3) > abs(wave1) * 1.618:
                    patterns.append(CandlePattern(
                        name='wave_3_extension_bearish',
                        pattern_type=PatternType.BEARISH_CONTINUATION,
                        strength=0.85,
                        candles_used=waves[5][0] - waves[0][0] + 1,
                        description="Bearish Wave 3 Extension - powerful momentum"
                    ))
        
        # ============ CORRECTIVE ABC PATTERN ============
        if len(all_swings) >= 4:
            abc = all_swings[-4:]
            a_start = abc[0][1]
            a_end = abc[1][1]
            b_end = abc[2][1]
            c_end = abc[3][1]
            
            wave_a = a_end - a_start
            wave_b = b_end - a_end
            wave_c = c_end - b_end
            
            # Bullish ABC correction (after bearish impulse, sets up bullish reversal)
            # A down, B up (retraces 38-78% of A), C down (equal to or less than A)
            if (wave_a < 0 and wave_b > 0 and wave_c < 0 and
                0.382 <= abs(wave_b / wave_a) <= 0.786 and
                abs(wave_c) <= abs(wave_a) * 1.2):
                patterns.append(CandlePattern(
                    name='corrective_abc_bullish',
                    pattern_type=PatternType.BULLISH_REVERSAL,
                    strength=0.7,
                    candles_used=abc[3][0] - abc[0][0] + 1,
                    description="Bullish ABC Correction complete - expect reversal up"
                ))
            
            # Bearish ABC correction (after bullish impulse, sets up bearish reversal)
            if (wave_a > 0 and wave_b < 0 and wave_c > 0 and
                0.382 <= abs(wave_b / wave_a) <= 0.786 and
                abs(wave_c) <= abs(wave_a) * 1.2):
                patterns.append(CandlePattern(
                    name='corrective_abc_bearish',
                    pattern_type=PatternType.BEARISH_REVERSAL,
                    strength=0.7,
                    candles_used=abc[3][0] - abc[0][0] + 1,
                    description="Bearish ABC Correction complete - expect reversal down"
                ))
        
        # ============ ENDING DIAGONAL (WEDGE in wave 5) ============
        if len(all_swings) >= 5:
            diag = all_swings[-5:]
            
            # Get high/low bounds
            highs = [s[1] for s in diag if s in swing_highs[-5:]]
            lows = [s[1] for s in diag if s in swing_lows[-5:]]
            
            if len(highs) >= 2 and len(lows) >= 2:
                # Calculate slopes
                high_slope = (highs[-1] - highs[0]) / max(1, len(highs))
                low_slope = (lows[-1] - lows[0]) / max(1, len(lows))
                
                # Ending diagonal bullish: rising wedge at end of downtrend (both slopes up, converging)
                if high_slope > 0 and low_slope > 0 and low_slope > high_slope:
                    recent_trend = candles[-1]['close'] - candles[-10]['close'] if len(candles) >= 10 else 0
                    if recent_trend < 0:  # Was in downtrend
                        patterns.append(CandlePattern(
                            name='ending_diagonal_bullish',
                            pattern_type=PatternType.BULLISH_REVERSAL,
                            strength=0.75,
                            candles_used=diag[4][0] - diag[0][0] + 1,
                            description="Bullish Ending Diagonal - wedge exhaustion, expect reversal up"
                        ))
                
                # Ending diagonal bearish: falling wedge at end of uptrend
                if high_slope < 0 and low_slope < 0 and high_slope > low_slope:
                    recent_trend = candles[-1]['close'] - candles[-10]['close'] if len(candles) >= 10 else 0
                    if recent_trend > 0:  # Was in uptrend
                        patterns.append(CandlePattern(
                            name='ending_diagonal_bearish',
                            pattern_type=PatternType.BEARISH_REVERSAL,
                            strength=0.75,
                            candles_used=diag[4][0] - diag[0][0] + 1,
                            description="Bearish Ending Diagonal - wedge exhaustion, expect reversal down"
                        ))
        
        return patterns
    
    def _detect_volume_patterns(self, candles: List[Dict[str, float]]) -> List[CandlePattern]:
        """Detect volume-based patterns (climax, no demand/supply, stopping volume)."""
        patterns = []
        
        if len(candles) < 5:
            return patterns
        
        # Check if volume data exists
        if 'volume' not in candles[-1]:
            return patterns
        
        # Get recent candles with metrics
        recent = candles[-10:] if len(candles) >= 10 else candles
        metrics = [self._get_candle_metrics(c) for c in recent]
        volumes = [c.get('volume', 0) for c in recent]
        
        # Calculate average volume
        avg_volume = sum(volumes) / len(volumes) if volumes else 1
        
        # ============ VOLUME CLIMAX ============
        # Extremely high volume with reversal candle
        
        last_vol = volumes[-1] if volumes else 0
        last_m = metrics[-1] if metrics else None
        
        if last_m and last_vol > avg_volume * 2:  # 2x average volume
            # Volume Climax Bullish - high volume bearish candle at bottom (selling exhaustion)
            if last_m['is_bearish'] and last_m['lower_wick'] > last_m['body']:
                # Check if at local low
                recent_lows = [m['low'] for m in metrics[-5:]]
                if last_m['low'] <= min(recent_lows):
                    patterns.append(CandlePattern(
                        name='volume_climax_bullish',
                        pattern_type=PatternType.BULLISH_REVERSAL,
                        strength=0.75,
                        candles_used=1,
                        description="Bullish Volume Climax - selling exhaustion, expect reversal"
                    ))
            
            # Volume Climax Bearish - high volume bullish candle at top (buying exhaustion)
            if last_m['is_bullish'] and last_m['upper_wick'] > last_m['body']:
                recent_highs = [m['high'] for m in metrics[-5:]]
                if last_m['high'] >= max(recent_highs):
                    patterns.append(CandlePattern(
                        name='volume_climax_bearish',
                        pattern_type=PatternType.BEARISH_REVERSAL,
                        strength=0.75,
                        candles_used=1,
                        description="Bearish Volume Climax - buying exhaustion, expect reversal"
                    ))
        
        # ============ NO DEMAND / NO SUPPLY ============
        # Low volume on weak up/down bar in trend
        
        if len(metrics) >= 3 and len(volumes) >= 3:
            m1, m2, m3 = metrics[-3], metrics[-2], metrics[-1]
            v1, v2, v3 = volumes[-3], volumes[-2], volumes[-1]
            
            # No Demand - small up bar on low volume in downtrend
            if (m1['is_bearish'] and m2['is_bearish'] and  # Downtrend context
                m3['is_bullish'] and m3['body_ratio'] < 0.4 and  # Small up bar
                v3 < avg_volume * 0.7):  # Low volume
                patterns.append(CandlePattern(
                    name='no_demand',
                    pattern_type=PatternType.BEARISH_CONTINUATION,
                    strength=0.7,
                    candles_used=3,
                    description="No Demand - weak rally attempt, downtrend continues"
                ))
            
            # No Supply - small down bar on low volume in uptrend
            if (m1['is_bullish'] and m2['is_bullish'] and  # Uptrend context
                m3['is_bearish'] and m3['body_ratio'] < 0.4 and  # Small down bar
                v3 < avg_volume * 0.7):  # Low volume
                patterns.append(CandlePattern(
                    name='no_supply',
                    pattern_type=PatternType.BULLISH_CONTINUATION,
                    strength=0.7,
                    candles_used=3,
                    description="No Supply - weak selloff attempt, uptrend continues"
                ))
        
        # ============ STOPPING VOLUME ============
        # High volume bar that stops the trend
        
        if len(metrics) >= 4 and len(volumes) >= 4:
            # Check for downtrend then stopping volume
            if (metrics[-4]['is_bearish'] and metrics[-3]['is_bearish'] and  # Downtrend
                volumes[-2] > avg_volume * 1.5 and  # High volume
                metrics[-2]['lower_wick'] > metrics[-2]['body'] and  # Rejection wick
                metrics[-1]['is_bullish']):  # Confirmation
                patterns.append(CandlePattern(
                    name='stopping_volume_bullish',
                    pattern_type=PatternType.BULLISH_REVERSAL,
                    strength=0.7,
                    candles_used=4,
                    description="Bullish Stopping Volume - high volume halt of downtrend"
                ))
            
            # Check for uptrend then stopping volume
            if (metrics[-4]['is_bullish'] and metrics[-3]['is_bullish'] and  # Uptrend
                volumes[-2] > avg_volume * 1.5 and  # High volume
                metrics[-2]['upper_wick'] > metrics[-2]['body'] and  # Rejection wick
                metrics[-1]['is_bearish']):  # Confirmation
                patterns.append(CandlePattern(
                    name='stopping_volume_bearish',
                    pattern_type=PatternType.BEARISH_REVERSAL,
                    strength=0.7,
                    candles_used=4,
                    description="Bearish Stopping Volume - high volume halt of uptrend"
                ))
        
        return patterns
    
    def _calculate_alignment_score(
        self,
        patterns: List[CandlePattern],
        prediction: int
    ) -> float:
        """
        Calculate score based on pattern alignment with prediction direction.
        
        Args:
            patterns: Detected patterns
            prediction: 0=SELL, 2=BUY
            
        Returns:
            Score 0.0-1.0 where higher = better alignment
        """
        if not patterns:
            return 0.5  # Neutral if no patterns
        
        is_bullish_trade = prediction == 2
        
        aligned_score = 0.0
        conflicting_score = 0.0
        neutral_score = 0.0
        
        for pattern in patterns:
            weight = self.pattern_weights.get(pattern.name, 0.5)
            
            if pattern.pattern_type == PatternType.NEUTRAL:
                neutral_score += weight * 0.5
            elif is_bullish_trade:
                # For BUY trades, bullish patterns help, bearish hurt
                if pattern.pattern_type in [PatternType.BULLISH_REVERSAL, PatternType.BULLISH_CONTINUATION]:
                    aligned_score += weight
                else:
                    conflicting_score += weight
            else:
                # For SELL trades, bearish patterns help, bullish hurt
                if pattern.pattern_type in [PatternType.BEARISH_REVERSAL, PatternType.BEARISH_CONTINUATION]:
                    aligned_score += weight
                else:
                    conflicting_score += weight
        
        total_weight = aligned_score + conflicting_score + neutral_score
        
        if total_weight == 0:
            return 0.5
        
        # Score formula: aligned patterns boost score, conflicting reduce it
        # Base 0.5, add aligned contribution, subtract conflicting
        score = 0.5 + (aligned_score - conflicting_score) / (2 * max(total_weight, 1.0))
        
        return float(np.clip(score, 0.0, 1.0))
    
    def get_pattern_summary(self, patterns: List[CandlePattern]) -> str:
        """Get human-readable summary of detected patterns."""
        if not patterns:
            return "No significant patterns detected"
        
        summaries = []
        for p in patterns:
            summaries.append(f"{p.name} ({p.pattern_type.value}, strength={p.strength:.2f})")
        
        return "; ".join(summaries)


def create_h1_pattern_scorer() -> CandlestickPatternRecognizer:
    """Factory function to create configured pattern recognizer."""
    return CandlestickPatternRecognizer(
        body_threshold=0.3,
        wick_threshold=2.0
    )
