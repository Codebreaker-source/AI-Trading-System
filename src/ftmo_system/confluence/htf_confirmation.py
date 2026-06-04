"""
H1/H4 Trend Confirmation Filter
================================

Validates trade signals against higher timeframe trend direction.
Acts as a filter to ensure trades align with the broader market structure.

Confirmation Criteria:
- H1 EMA alignment (fast > slow for bullish, fast < slow for bearish)
- H4 EMA alignment (same logic)
- Price position relative to H1/H4 EMAs
- Trend momentum (ADX-based strength)
- Cross-timeframe agreement

Returns a confluence score based on HTF alignment with trade direction.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class TrendDirection(Enum):
    """Trend classification"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class TrendStrength(Enum):
    """Trend strength classification"""
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    NONE = "none"


@dataclass
class TimeframeTrend:
    """Trend state for a single timeframe"""
    timeframe: str
    direction: TrendDirection
    strength: TrendStrength
    ema_alignment: bool  # fast EMA > slow EMA for bullish
    price_above_ema: bool  # price above slow EMA
    momentum_score: float  # 0.0 to 1.0
    
    def __str__(self) -> str:
        return f"{self.timeframe}: {self.direction.value} ({self.strength.value})"


@dataclass
class HTFConfirmationResult:
    """Result from HTF trend confirmation analysis"""
    score: float  # 0.0 to 1.0
    h1_trend: TimeframeTrend
    h4_trend: TimeframeTrend
    alignment_level: str  # "full", "partial", "none", "conflicting"
    recommendation: str
    
    def __str__(self) -> str:
        return f"HTF Score: {self.score:.2f} ({self.alignment_level}) - {self.recommendation}"


class HTFTrendConfirmation:
    """
    H1/H4 Trend Confirmation for confluence scoring.
    
    Analyzes higher timeframe trends to confirm or reject trade signals.
    Provides a score based on alignment with the predicted trade direction.
    """
    
    def __init__(
        self,
        h1_weight: float = 0.4,
        h4_weight: float = 0.6,
        strong_adx_threshold: float = 25.0,
        weak_adx_threshold: float = 15.0
    ):
        """
        Initialize HTF trend confirmation.
        
        Args:
            h1_weight: Weight for H1 timeframe (default 0.4)
            h4_weight: Weight for H4 timeframe (default 0.6 - more important)
            strong_adx_threshold: ADX above this = strong trend
            weak_adx_threshold: ADX below this = weak/no trend
        """
        self.h1_weight = h1_weight
        self.h4_weight = h4_weight
        self.strong_adx = strong_adx_threshold
        self.weak_adx = weak_adx_threshold
        
        # Normalize weights
        total = self.h1_weight + self.h4_weight
        self.h1_weight /= total
        self.h4_weight /= total
    
    def analyze(
        self,
        features: Dict[str, float],
        prediction: int,
        h1_data: Optional[Dict[str, float]] = None,
        h4_data: Optional[Dict[str, float]] = None
    ) -> HTFConfirmationResult:
        """
        Analyze H1/H4 trend alignment with prediction.
        
        Args:
            features: Base features dict (may contain HTF features)
            prediction: Trade direction (0=SELL, 1=HOLD, 2=BUY)
            h1_data: Optional H1-specific data dict
            h4_data: Optional H4-specific data dict
            
        Returns:
            HTFConfirmationResult with score and breakdown
        """
        if prediction == 1:  # HOLD
            return HTFConfirmationResult(
                score=0.5,
                h1_trend=self._create_neutral_trend("H1"),
                h4_trend=self._create_neutral_trend("H4"),
                alignment_level="neutral",
                recommendation="HOLD prediction - HTF confirmation not applicable"
            )
        
        is_bullish_trade = prediction == 2
        
        # Analyze H1 trend
        h1_trend = self._analyze_timeframe(
            "H1", features, h1_data, is_bullish_trade
        )
        
        # Analyze H4 trend
        h4_trend = self._analyze_timeframe(
            "H4", features, h4_data, is_bullish_trade
        )
        
        # Calculate alignment and score
        score, alignment_level = self._calculate_alignment_score(
            h1_trend, h4_trend, is_bullish_trade
        )
        
        # Generate recommendation
        recommendation = self._generate_recommendation(
            score, alignment_level, is_bullish_trade
        )
        
        return HTFConfirmationResult(
            score=score,
            h1_trend=h1_trend,
            h4_trend=h4_trend,
            alignment_level=alignment_level,
            recommendation=recommendation
        )
    
    def _analyze_timeframe(
        self,
        timeframe: str,
        features: Dict[str, float],
        tf_data: Optional[Dict[str, float]],
        is_bullish_trade: bool
    ) -> TimeframeTrend:
        """Analyze trend for a specific timeframe."""
        
        # Get relevant features based on timeframe
        if timeframe == "H1":
            prefix = "h1_" if tf_data else ""
            data = tf_data or features
            
            # Try to get H1-specific features
            fast_ema = data.get(f'{prefix}fast_ema', data.get('mtf_trend_h1', 0))
            slow_ema = data.get(f'{prefix}slow_ema', 0)
            trend_dir = data.get(f'{prefix}trend_direction', data.get('mtf_trend_h1', 0))
            momentum = data.get(f'{prefix}momentum', data.get('mtf_momentum_h1', 0))
            adx = data.get(f'{prefix}adx', data.get('adx', 20))
            close = data.get('close', data.get(f'{prefix}close', 0))
            
        else:  # H4
            prefix = "h4_" if tf_data else ""
            data = tf_data or features
            
            fast_ema = data.get(f'{prefix}fast_ema', data.get('htf_fast_ema', 0))
            slow_ema = data.get(f'{prefix}slow_ema', data.get('htf_slow_ema', 0))
            trend_dir = data.get(f'{prefix}trend_direction', data.get('htf_trend_direction', 0))
            momentum = data.get(f'{prefix}momentum', data.get('mtf_rsi_h4', 50))
            adx = data.get(f'{prefix}adx', data.get('adx', 20))
            close = data.get('close', data.get(f'{prefix}close', 0))
        
        # Determine EMA alignment
        if fast_ema != 0 and slow_ema != 0:
            ema_alignment = fast_ema > slow_ema
        elif trend_dir != 0:
            ema_alignment = trend_dir > 0
        else:
            ema_alignment = None  # Unknown
        
        # Determine price position relative to slow EMA
        if close != 0 and slow_ema != 0:
            price_above_ema = close > slow_ema
        elif trend_dir != 0:
            price_above_ema = trend_dir > 0
        else:
            price_above_ema = None
        
        # Determine trend direction
        if ema_alignment is True and price_above_ema is True:
            direction = TrendDirection.BULLISH
        elif ema_alignment is False and price_above_ema is False:
            direction = TrendDirection.BEARISH
        elif ema_alignment is not None:
            # Mixed signals
            direction = TrendDirection.BULLISH if ema_alignment else TrendDirection.BEARISH
        else:
            direction = TrendDirection.NEUTRAL
        
        # Determine trend strength based on ADX
        if adx >= self.strong_adx:
            strength = TrendStrength.STRONG
        elif adx >= self.weak_adx:
            strength = TrendStrength.MODERATE
        elif adx > 0:
            strength = TrendStrength.WEAK
        else:
            strength = TrendStrength.NONE
        
        # Calculate momentum score (0-1)
        if isinstance(momentum, (int, float)):
            # Normalize momentum to 0-1
            if momentum > 50:
                momentum_score = min((momentum - 50) / 50, 1.0)
            else:
                momentum_score = max((50 - momentum) / 50, 0.0) if momentum < 50 else 0.5
        else:
            momentum_score = 0.5
        
        return TimeframeTrend(
            timeframe=timeframe,
            direction=direction,
            strength=strength,
            ema_alignment=ema_alignment if ema_alignment is not None else False,
            price_above_ema=price_above_ema if price_above_ema is not None else False,
            momentum_score=momentum_score
        )
    

    def _calculate_alignment_score(
        self,
        h1_trend: TimeframeTrend,
        h4_trend: TimeframeTrend,
        is_bullish_trade: bool
    ) -> Tuple[float, str]:
        """
        Calculate alignment score based on HTF trends.
        
        Returns:
            Tuple of (score, alignment_level)
        """
        h1_score = self._score_trend_alignment(h1_trend, is_bullish_trade)
        h4_score = self._score_trend_alignment(h4_trend, is_bullish_trade)
        
        # Weighted combination
        combined_score = (h1_score * self.h1_weight) + (h4_score * self.h4_weight)
        
        # Determine alignment level
        if h1_score >= 0.7 and h4_score >= 0.7:
            alignment_level = "full"
        elif h1_score >= 0.5 and h4_score >= 0.5:
            alignment_level = "partial"
        elif (h1_score < 0.3 and h4_score > 0.7) or (h1_score > 0.7 and h4_score < 0.3):
            alignment_level = "conflicting"
        elif h1_score < 0.4 and h4_score < 0.4:
            alignment_level = "opposing"
        else:
            alignment_level = "mixed"
        
        return float(np.clip(combined_score, 0.0, 1.0)), alignment_level
    
    def _score_trend_alignment(
        self,
        trend: TimeframeTrend,
        is_bullish_trade: bool
    ) -> float:
        """Score how well a timeframe trend aligns with trade direction."""
        
        score = 0.0
        
        # Direction alignment (most important)
        if trend.direction == TrendDirection.NEUTRAL:
            direction_score = 0.5
        elif is_bullish_trade:
            direction_score = 1.0 if trend.direction == TrendDirection.BULLISH else 0.0
        else:
            direction_score = 1.0 if trend.direction == TrendDirection.BEARISH else 0.0
        
        # Strength multiplier
        strength_mult = {
            TrendStrength.STRONG: 1.0,
            TrendStrength.MODERATE: 0.8,
            TrendStrength.WEAK: 0.6,
            TrendStrength.NONE: 0.4
        }.get(trend.strength, 0.5)
        
        # EMA alignment bonus
        ema_bonus = 0.0
        if is_bullish_trade and trend.ema_alignment:
            ema_bonus = 0.1
        elif not is_bullish_trade and not trend.ema_alignment:
            ema_bonus = 0.1
        
        # Price position bonus
        price_bonus = 0.0
        if is_bullish_trade and trend.price_above_ema:
            price_bonus = 0.1
        elif not is_bullish_trade and not trend.price_above_ema:
            price_bonus = 0.1
        
        # Momentum alignment
        momentum_bonus = 0.0
        if is_bullish_trade and trend.momentum_score > 0.6:
            momentum_bonus = 0.1
        elif not is_bullish_trade and trend.momentum_score < 0.4:
            momentum_bonus = 0.1
        
        # Calculate final score
        score = direction_score * strength_mult + ema_bonus + price_bonus + momentum_bonus
        
        return float(np.clip(score, 0.0, 1.0))
    
    def _generate_recommendation(
        self,
        score: float,
        alignment_level: str,
        is_bullish_trade: bool
    ) -> str:
        """Generate human-readable recommendation."""
        
        direction = "BUY" if is_bullish_trade else "SELL"
        
        if alignment_level == "full":
            return f"STRONG {direction} - Full HTF alignment confirmed"
        elif alignment_level == "partial":
            return f"MODERATE {direction} - Partial HTF alignment"
        elif alignment_level == "conflicting":
            return f"CAUTION {direction} - H1/H4 trends conflicting"
        elif alignment_level == "opposing":
            return f"WEAK {direction} - HTF trends oppose trade direction"
        else:
            return f"MIXED {direction} - HTF signals unclear"
    
    def _create_neutral_trend(self, timeframe: str) -> TimeframeTrend:
        """Create a neutral trend for HOLD predictions."""
        return TimeframeTrend(
            timeframe=timeframe,
            direction=TrendDirection.NEUTRAL,
            strength=TrendStrength.NONE,
            ema_alignment=False,
            price_above_ema=False,
            momentum_score=0.5
        )
    
    def get_score_from_features(
        self,
        features: Dict[str, float],
        prediction: int
    ) -> float:
        """
        Quick score calculation using just base features.
        
        This is a convenience method for integration with confluence scorer.
        """
        result = self.analyze(features, prediction)
        return result.score


def create_htf_confirmation() -> HTFTrendConfirmation:
    """Factory function to create configured HTF confirmation."""
    return HTFTrendConfirmation(
        h1_weight=0.4,
        h4_weight=0.6,
        strong_adx_threshold=25.0,
        weak_adx_threshold=15.0
    )
