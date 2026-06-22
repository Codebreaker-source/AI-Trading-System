# Source Bundle: docs/full_source_bundles/02_confluence.md


---

## `confluence/__init__.py`

```py
"""
Confluence Scoring System for AI Trading
=========================================

This module provides multi-factor confluence scoring for trade entry,
scaling in, and scaling out decisions.

Components:
- ConfluenceScorer: Main 8-factor weighted scoring
- HardFilters: Binary pass/fail gates (ATR, News, Session)
- RegimeDetector: ADX-based trending/ranging detection
- RiskManager: Portfolio risk tracking (2% max across all positions)
- LevelConfluence: Fib/Pivot/Psych level detection for scaling
- CandlestickPatternRecognizer: H1 candlestick pattern recognition
- HTFTrendConfirmation: H1/H4 trend confirmation filter

8 Confluence Factors:
1. MTF Trend Alignment (15%)
2. Support/Resistance Proximity (12%)
3. Momentum Confirmation (10%)
4. Volume Profile (6%)
5. Volatility Regime (6%)
6. Strategy Consensus (13%)
7. H1 Candlestick Patterns (18%)
8. H1/H4 Trend Confirmation (20%) [NEW]

Position Sizing:
- ALL trades are 0.01 lots - no exceptions
- Scale IN = Add 0.01 lot position at key support levels
- Scale OUT = Close 0.01 lot position at key resistance levels

Risk Limits:
- Max total portfolio risk: 2% of account ($200 on $10K)
- Each 0.01 lot position has calculated risk based on stop distance

Label Format:
- 0 = SELL
- 1 = HOLD
- 2 = BUY
"""

from .hard_filters import HardFilters, FilterResult, passes_hard_filters
from .confluence_scorer import ConfluenceScorer, ConfluenceResult
from .regime_detector import RegimeDetector, RegimeState
from .risk_manager import RiskManager, PositionRisk, PortfolioRisk
from .level_confluence import LevelConfluence, ScalingSignal, LevelType
from .candlestick_patterns import CandlestickPatternRecognizer, CandlePattern, PatternType, create_h1_pattern_scorer
from .htf_confirmation import HTFTrendConfirmation, HTFConfirmationResult, TrendDirection, TrendStrength, create_htf_confirmation
from .pullback_detector import PullbackDetector, PullbackResult, PullbackStatus, SwingPoints, get_scale_in_summary

__all__ = [
    'HardFilters',
    'FilterResult',
    'passes_hard_filters',
    'ConfluenceScorer',
    'ConfluenceResult',
    'RegimeDetector',
    'RegimeState',
    'RiskManager',
    'PositionRisk',
    'PortfolioRisk',
    'LevelConfluence',
    'ScalingSignal',
    'LevelType',
    'CandlestickPatternRecognizer',
    'CandlePattern',
    'PatternType',
    'create_h1_pattern_scorer',
    'HTFTrendConfirmation',
    'HTFConfirmationResult',
    'TrendDirection',
    'TrendStrength',
    'create_htf_confirmation',
    'PullbackDetector',
    'PullbackResult',
    'PullbackStatus',
    'SwingPoints',
    'get_scale_in_summary'
]

__version__ = '1.3.0'

```

---

## `confluence/confluence_scorer.py`

```py
"""
Confluence Scorer - Main 7-Factor Weighted Scoring
===================================================

Calculates confluence score from multiple technical factors:
- Multi-timeframe Trend Alignment: 19%
- Support/Resistance Proximity: 15%
- Momentum Confirmation: 12%
- Volume Profile: 8%
- Volatility Regime: 8%
- Strategy Consensus: 16%
- H1 Candlestick Patterns: 22%

NOTE: H1/H4 Trend Confirmation moved to hard_filters.py as a GATE (v2.2)
- Counter-trend trades are now BLOCKED entirely before reaching confluence scoring

Score Range: 0.0 to 1.0
- >= 0.70 AND 3+ factors passing: High confluence (take trade)
- >= 0.50 AND 2+ factors passing: Medium confluence (take trade with caution)
- < 0.50 OR insufficient factors: Low confluence (skip trade)

MINIMUM FACTOR REQUIREMENT (v2.0):
- A factor "passes" if its score >= 0.5 (factor_pass_threshold)
- HIGH confluence requires min_passing_factors (default: 3)
- MEDIUM confluence requires min_passing_factors - 1 (default: 2)
- This prevents high scores from 1-2 dominant factors while others fail
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

# Import candlestick pattern recognizer
from .candlestick_patterns import CandlestickPatternRecognizer, create_h1_pattern_scorer
# NOTE: HTF trend confirmation now in hard_filters.py as a gate (not weighted factor)


class ConfluenceLevel(Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class ConfluenceResult:
    """Result from confluence scoring"""
    score: float
    level: ConfluenceLevel
    factor_scores: Dict[str, float]
    factor_contributions: Dict[str, float]
    recommendation: str
    passing_factor_count: int = 0  # Count of factors scoring >= threshold
    total_factor_count: int = 7    # Total factors evaluated (was 8, HTF now a gate)
    
    def __str__(self) -> str:
        return f"Confluence: {self.score:.2f} ({self.level.value}) [{self.passing_factor_count}/{self.total_factor_count} factors] - {self.recommendation}"


class ConfluenceScorer:
    """
    Main confluence scoring system using 7 weighted factors.
    
    All factors are normalized to [0, 1] before weighting.
    Final score is weighted sum normalized to [0, 1].
    
    NOTE: HTF trend confirmation is now a hard gate in hard_filters.py,
    not a weighted factor here.
    """
    
    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        high_threshold: float = 0.70,
        medium_threshold: float = 0.50,
        min_passing_factors: int = 3,
        factor_pass_threshold: float = 0.5
    ):
        # 7-factor weights (must sum to 1.0)
        # NOTE: HTF confirmation moved to hard_filters.py as a gate
        self.weights = weights or {
            'mtf_trend': 0.19,
            'support_resistance': 0.15,
            'momentum': 0.12,
            'volume': 0.08,
            'volatility': 0.08,
            'strategy_consensus': 0.16,
            'candlestick_patterns': 0.22
        }
        
        total_weight = sum(self.weights.values())
        if abs(total_weight - 1.0) > 0.001:
            self.weights = {k: v / total_weight for k, v in self.weights.items()}
        
        self.high_threshold = high_threshold
        self.medium_threshold = medium_threshold
        
        # NEW: Minimum factor count requirements
        self.min_passing_factors = min_passing_factors  # For HIGH confluence
        self.factor_pass_threshold = factor_pass_threshold  # Score >= this = "passing"
        
        # Initialize candlestick pattern recognizer
        self.pattern_recognizer = create_h1_pattern_scorer()
        
        self.normalization_params = {
            'rsi': {'min': 0, 'max': 100},
            'macd_histogram': {'min': -0.01, 'max': 0.01},
            'volume_ratio': {'min': 0.5, 'max': 3.0},
            'atr_percentile': {'min': 0, 'max': 100},
        }
    
    def calculate(
        self,
        features: Dict[str, float],
        prediction: int,
        regime: Optional[str] = None,
        strategy_data: Optional[Dict[str, Any]] = None,
        h1_candles: Optional[List[Dict[str, float]]] = None
    ) -> ConfluenceResult:
        """
        Calculate confluence score for a potential trade.
        
        Args:
            features: Dict of 58+ technical features
            prediction: Model prediction (0=SELL, 1=HOLD, 2=BUY)
            regime: Optional regime override ('trending', 'ranging')
            strategy_data: Optional strategy voting data
            h1_candles: Optional list of H1 OHLC candles for pattern recognition
            
        Returns:
            ConfluenceResult with score, level, and breakdown
        """
        factor_scores = {}
        
        factor_scores['mtf_trend'] = self._score_mtf_trend(features, prediction)
        factor_scores['support_resistance'] = self._score_support_resistance(features, prediction)
        factor_scores['momentum'] = self._score_momentum(features, prediction)
        factor_scores['volume'] = self._score_volume(features)
        factor_scores['volatility'] = self._score_volatility(features)
        
        # Factor 6: Strategy consensus
        if 'strategy_consensus' in self.weights:
            factor_scores['strategy_consensus'] = self._score_strategy_consensus(
                prediction, strategy_data, regime
            )
        
        # Factor 7: H1 Candlestick Patterns
        if 'candlestick_patterns' in self.weights:
            factor_scores['candlestick_patterns'] = self._score_candlestick_patterns(
                prediction, h1_candles
            )
        
        # NOTE: HTF confirmation is now a hard gate in hard_filters.py (not scored here)
        
        adjusted_weights = self._adjust_weights_for_regime(regime) if regime else self.weights
        
        factor_contributions = {}
        total_score = 0.0
        
        for factor, score in factor_scores.items():
            weight = adjusted_weights.get(factor, 0.0)
            contribution = score * weight
            factor_contributions[factor] = contribution
            total_score += contribution
        
        total_score = np.clip(total_score, 0.0, 1.0)
        
        # NEW: Count factors that pass the threshold
        passing_factors = sum(1 for score in factor_scores.values() if score >= self.factor_pass_threshold)
        total_factors = len(factor_scores)
        
        # NEW: Level determination now requires BOTH score threshold AND minimum passing factors
        if total_score >= self.high_threshold and passing_factors >= self.min_passing_factors:
            level = ConfluenceLevel.HIGH
            recommendation = f"TAKE TRADE - High confluence ({passing_factors}/{total_factors} factors passing)"
        elif total_score >= self.medium_threshold and passing_factors >= (self.min_passing_factors - 1):
            level = ConfluenceLevel.MEDIUM
            recommendation = f"TAKE TRADE WITH CAUTION - Medium confluence ({passing_factors}/{total_factors} factors)"
        else:
            level = ConfluenceLevel.LOW
            # Provide specific reason for rejection
            if total_score >= self.medium_threshold:
                recommendation = f"SKIP TRADE - Score OK but only {passing_factors}/{total_factors} factors passing (need {self.min_passing_factors - 1}+)"
            else:
                recommendation = f"SKIP TRADE - Insufficient confluence ({passing_factors}/{total_factors} factors, score {total_score:.2f})"
        
        return ConfluenceResult(
            score=float(total_score),
            level=level,
            factor_scores=factor_scores,
            factor_contributions=factor_contributions,
            recommendation=recommendation,
            passing_factor_count=passing_factors,
            total_factor_count=total_factors
        )
    
    def _score_mtf_trend(self, features: Dict[str, float], prediction: int) -> float:
        """
        Score multi-timeframe trend alignment (30% weight).
        
        Checks if H1, H4, and daily trends align with prediction direction.
        """
        if prediction == 1:  # HOLD
            return 0.5
        
        is_bullish = prediction == 2
        score = 0.0
        factors_checked = 0
        
        # H1 trend alignment
        mtf_trend_h1 = features.get('mtf_trend_h1', 0)
        if mtf_trend_h1 != 0:
            if (is_bullish and mtf_trend_h1 > 0) or (not is_bullish and mtf_trend_h1 < 0):
                score += 1.0
            factors_checked += 1
        
        # H4 trend alignment
        mtf_trend_h4 = features.get('mtf_trend_h4', 0)
        if mtf_trend_h4 != 0:
            if (is_bullish and mtf_trend_h4 > 0) or (not is_bullish and mtf_trend_h4 < 0):
                score += 1.0
            factors_checked += 1
        
        # HTF trend alignment
        htf_trend_alignment = features.get('htf_trend_alignment', 0)
        if htf_trend_alignment != 0:
            if (is_bullish and htf_trend_alignment > 0) or (not is_bullish and htf_trend_alignment < 0):
                score += 1.0
            factors_checked += 1
        
        # HTF trend direction
        htf_trend_direction = features.get('htf_trend_direction', 0)
        if htf_trend_direction != 0:
            if (is_bullish and htf_trend_direction > 0) or (not is_bullish and htf_trend_direction < 0):
                score += 1.0
            factors_checked += 1
        
        if factors_checked == 0:
            return 0.5
        
        return score / factors_checked
    
    def _score_support_resistance(self, features: Dict[str, float], prediction: int) -> float:
        """
        Score support/resistance proximity (25% weight).
        
        For BUY: Want price near support levels
        For SELL: Want price near resistance levels
        """
        if prediction == 1:  # HOLD
            return 0.5
        
        is_bullish = prediction == 2
        score = 0.0
        factors_checked = 0
        
        # Distance to nearest support (lower = better for BUY)
        dist_support = features.get('dist_to_nearest_support', 100)
        if dist_support < 100:
            support_score = max(0, 1 - (dist_support / 50))  # Within 50 pips = good
            if is_bullish:
                score += support_score
            else:
                score += (1 - support_score)  # For SELL, away from support is good
            factors_checked += 1
        
        # Distance to nearest resistance (lower = better for SELL)
        dist_resistance = features.get('dist_to_nearest_resistance', 100)
        if dist_resistance < 100:
            resistance_score = max(0, 1 - (dist_resistance / 50))
            if not is_bullish:
                score += resistance_score
            else:
                score += (1 - resistance_score)  # For BUY, away from resistance is good
            factors_checked += 1
        
        # Pivot confluence
        pivot_confluence = features.get('pivot_confluence', 0)
        if pivot_confluence > 0:
            score += min(pivot_confluence / 3, 1.0)  # Normalize 0-3 to 0-1
            factors_checked += 1
        
        # Psychological level proximity
        dist_psych = features.get('dist_to_major_psych', 100)
        if dist_psych < 100:
            psych_score = max(0, 1 - (dist_psych / 30))  # Within 30 pips = good
            score += psych_score
            factors_checked += 1
        
        if factors_checked == 0:
            return 0.5
        
        return score / factors_checked
    
    def _score_momentum(self, features: Dict[str, float], prediction: int) -> float:
        """
        Score momentum confirmation (20% weight).
        
        Uses RSI, MACD, and momentum indicators.
        """
        if prediction == 1:  # HOLD
            return 0.5
        
        is_bullish = prediction == 2
        score = 0.0
        factors_checked = 0
        
        # RSI alignment
        rsi = features.get('rsi', 50)
        if is_bullish:
            if rsi < 30:
                score += 1.0  # Oversold = good for buy
            elif rsi < 50:
                score += 0.7
            elif rsi < 70:
                score += 0.4
            else:
                score += 0.1  # Overbought = bad for buy
        else:
            if rsi > 70:
                score += 1.0  # Overbought = good for sell
            elif rsi > 50:
                score += 0.7
            elif rsi > 30:
                score += 0.4
            else:
                score += 0.1  # Oversold = bad for sell
        factors_checked += 1
        
        # MACD histogram
        macd_hist = features.get('macd_histogram', 0)
        if macd_hist != 0:
            if (is_bullish and macd_hist > 0) or (not is_bullish and macd_hist < 0):
                score += 1.0
            else:
                score += 0.2
            factors_checked += 1
        
        # Momentum indicator
        momentum = features.get('momentum', 0)
        if momentum != 0:
            if (is_bullish and momentum > 0) or (not is_bullish and momentum < 0):
                score += 1.0
            else:
                score += 0.2
            factors_checked += 1
        
        # Momentum confirm flag
        momentum_confirm = features.get('momentum_confirm', 0)
        if momentum_confirm > 0:
            score += 1.0
            factors_checked += 1
        
        if factors_checked == 0:
            return 0.5
        
        return score / factors_checked
    
    def _score_volume(self, features: Dict[str, float]) -> float:
        """
        Score volume profile (15% weight).
        
        Higher volume = more conviction in move.
        """
        score = 0.0
        factors_checked = 0
        
        # Volume ratio (current vs average)
        volume_ratio = features.get('volume_ratio', 1.0)
        if volume_ratio > 0:
            if volume_ratio >= 2.0:
                score += 1.0  # 2x+ average = strong
            elif volume_ratio >= 1.5:
                score += 0.8
            elif volume_ratio >= 1.0:
                score += 0.5
            else:
                score += 0.2  # Below average = weak
            factors_checked += 1
        
        # Volume spike
        volume_spike = features.get('volume_spike', 0)
        if volume_spike > 0:
            score += 1.0
            factors_checked += 1
        
        # Volume confirm
        volume_confirm = features.get('volume_confirm', 0)
        if volume_confirm > 0:
            score += 1.0
            factors_checked += 1
        
        if factors_checked == 0:
            return 0.5
        
        return score / factors_checked
    
    def _score_volatility(self, features: Dict[str, float]) -> float:
        """
        Score volatility regime (10% weight).
        
        Moderate volatility is ideal - not too quiet, not too wild.
        """
        score = 0.0
        factors_checked = 0
        
        # ATR-based volatility
        atr = features.get('atr', 0)
        volatility = features.get('volatility', 0)
        
        # Volatility confirm (pre-calculated ideal range indicator)
        volatility_confirm = features.get('volatility_confirm', 0)
        if volatility_confirm > 0:
            score += 1.0
            factors_checked += 1
        
        # Session volatility multiplier (higher during active sessions)
        session_mult = features.get('session_volatility_mult', 1.0)
        if session_mult >= 1.0:
            score += min(session_mult / 1.5, 1.0)
            factors_checked += 1
        
        # High liquidity period
        high_liquidity = features.get('is_high_liquidity_period', 0)
        if high_liquidity > 0:
            score += 1.0
            factors_checked += 1
        
        if factors_checked == 0:
            return 0.5
        
        return score / factors_checked
    
    def _score_strategy_consensus(
        self,
        prediction: int,
        strategy_data: Optional[Dict[str, Any]],
        regime: Optional[str] = None
    ) -> float:
        """
        Score strategy consensus alignment (20% weight).
        
        Only counts votes from strategies appropriate for the detected regime.
        
        Regime-Strategy Mapping:
        - TRENDING: trend_following, currency_strength_divergence, currency_correlation
        - RANGING: mean_reversion, low_volatility_momentum, volatility_contraction
        - VOLATILE: volume_breakout, volatility_breakout, high_volatility_reversal
        """
        if strategy_data is None:
            return 0.5  # Neutral if no strategy data
        
        if prediction == 1:  # HOLD
            return 0.5
        
        # Define regime-appropriate strategies
        regime_strategies = {
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
        
        # Get individual strategy predictions
        strategy_predictions = strategy_data.get('predictions', {})
        
        # If no individual predictions, fall back to total votes
        if not strategy_predictions:
            # Use total votes but apply regime filter if possible
            votes = strategy_data.get('votes', {})
            buy_votes = votes.get('BUY', strategy_data.get('buy_votes', 0))
            sell_votes = votes.get('SELL', strategy_data.get('sell_votes', 0))
            hold_votes = votes.get('HOLD', strategy_data.get('hold_votes', 0))
            total_votes = buy_votes + sell_votes + hold_votes
            
            if total_votes == 0:
                return 0.5
            
            is_bullish = prediction == 2
            if is_bullish:
                agreement_ratio = buy_votes / total_votes
            else:
                agreement_ratio = sell_votes / total_votes
            
            return float(np.clip(agreement_ratio, 0.0, 1.0))
        
        # Filter strategies by regime
        if regime and regime.lower() in regime_strategies:
            relevant_strategies = regime_strategies[regime.lower()]
        else:
            # If no regime or transitional, use all strategies
            relevant_strategies = list(strategy_predictions.keys())
        
        # Count votes from regime-appropriate strategies only
        buy_votes = 0
        sell_votes = 0
        hold_votes = 0
        
        for strategy_name, vote in strategy_predictions.items():
            # Check if strategy is relevant for current regime
            if strategy_name not in relevant_strategies:
                continue
            
            # Handle both string and integer vote formats
            if vote == 2 or vote == 'BUY':
                buy_votes += 1
            elif vote == 0 or vote == 'SELL':
                sell_votes += 1
            else:  # 1, 'HOLD', or anything else
                hold_votes += 1
        
        total_votes = buy_votes + sell_votes + hold_votes
        
        if total_votes == 0:
            return 0.5  # Neutral if no relevant strategies
        
        # Check agreement with prediction
        is_bullish = prediction == 2
        
        if is_bullish:
            agreement_ratio = buy_votes / total_votes
            disagreement_ratio = sell_votes / total_votes
        else:
            agreement_ratio = sell_votes / total_votes
            disagreement_ratio = buy_votes / total_votes
        
        # Score based on agreement among regime-appropriate strategies
        # With only 3 strategies per regime:
        # 3/3 agree = 1.0 (excellent)
        # 2/3 agree = 0.67 (good)
        # 1/3 agree = 0.33 (weak)
        # 0/3 agree = 0.0 (bad)
        
        score = agreement_ratio
        
        # Bonus for unanimous agreement
        if agreement_ratio >= 0.99:
            score = 1.0
        elif agreement_ratio >= 0.66:
            score = 0.7 + (agreement_ratio - 0.66) * 0.9
        
        # Penalty for strong disagreement
        if disagreement_ratio >= 0.66:
            score *= 0.3
        
        return float(np.clip(score, 0.0, 1.0))
    
    def _score_candlestick_patterns(
        self,
        prediction: int,
        h1_candles: Optional[List[Dict[str, float]]]
    ) -> float:
        """
        Score H1 candlestick pattern alignment (20% weight).
        
        Detects reversal and continuation patterns on H1 timeframe
        and scores based on alignment with prediction direction.
        
        Patterns detected:
        - Single: Hammer, Shooting Star, Doji, Marubozu
        - Double: Engulfing, Harami
        - Triple: Morning/Evening Star, Three White Soldiers/Black Crows
        """
        if h1_candles is None or len(h1_candles) < 3:
            return 0.5  # Neutral if no candle data
        
        if prediction == 1:  # HOLD
            return 0.5
        
        # Use pattern recognizer to analyze candles
        score, patterns = self.pattern_recognizer.analyze(h1_candles, prediction)
        
        return score
    
    def _score_htf_confirmation(
        self,
        features: Dict[str, float],
        prediction: int
    ) -> float:
        """
        Score H1/H4 trend confirmation alignment (20% weight).
        
        Validates trade signals against higher timeframe trend direction.
        Ensures trades align with broader market structure.
        
        Checks:
        - H1 EMA alignment (fast > slow for bullish)
        - H4 EMA alignment (same logic)
        - Price position relative to HTF EMAs
        - Trend momentum and strength
        """
        if prediction == 1:  # HOLD
            return 0.5
        
        # Use HTF confirmation analyzer
        score = self.htf_confirmer.get_score_from_features(features, prediction)
        
        return score
    
    def _adjust_weights_for_regime(self, regime: str) -> Dict[str, float]:
        """
        Adjust factor weights based on market regime.
        
        Trending: Increase momentum weight, HTF confirmation critical
        Ranging: Increase support/resistance weight, candlestick patterns for reversal
        Volatile: Increase volatility and strategy consensus weight
        """
        adjusted = self.weights.copy()
        
        if regime == 'trending':
            adjusted['momentum'] *= 1.5
            adjusted['mtf_trend'] *= 1.3
            adjusted['support_resistance'] *= 0.7
            if 'strategy_consensus' in adjusted:
                adjusted['strategy_consensus'] *= 1.2
            if 'candlestick_patterns' in adjusted:
                adjusted['candlestick_patterns'] *= 1.1
            if 'htf_confirmation' in adjusted:
                adjusted['htf_confirmation'] *= 1.4  # HTF alignment critical in trends
        elif regime == 'ranging':
            adjusted['support_resistance'] *= 1.5
            adjusted['momentum'] *= 0.7
            adjusted['mtf_trend'] *= 0.8
            if 'strategy_consensus' in adjusted:
                adjusted['strategy_consensus'] *= 1.2
            if 'candlestick_patterns' in adjusted:
                adjusted['candlestick_patterns'] *= 1.3
            if 'htf_confirmation' in adjusted:
                adjusted['htf_confirmation'] *= 0.8  # Less important in ranging
        elif regime == 'volatile':
            adjusted['volatility'] *= 1.5
            adjusted['volume'] *= 1.3
            adjusted['momentum'] *= 0.8
            if 'strategy_consensus' in adjusted:
                adjusted['strategy_consensus'] *= 1.3
            if 'candlestick_patterns' in adjusted:
                adjusted['candlestick_patterns'] *= 0.9
            if 'htf_confirmation' in adjusted:
                adjusted['htf_confirmation'] *= 1.1  # Still useful in volatile markets
        
        total = sum(adjusted.values())
        return {k: v / total for k, v in adjusted.items()}
    
    def get_threshold_info(self) -> Dict[str, Any]:
        """Return current threshold configuration."""
        return {
            'high_threshold': self.high_threshold,
            'medium_threshold': self.medium_threshold,
            'min_passing_factors': self.min_passing_factors,
            'factor_pass_threshold': self.factor_pass_threshold,
            'total_factors': len(self.weights)
        }

```

---

## `confluence/hard_filters.py`

```py
"""
Hard Filters - Binary Pass/Fail Gates
======================================

These filters must ALL pass before a trade can be considered.
Any single failure blocks the trade entirely.

Filters:
- ATR Filter: Minimum volatility for tradeable conditions
- News Filter: No major economic events within buffer period
- Session Filter: London/NY sessions only (Asian session disabled)
- HTF Trend Filter: Trade must align with H1/H4 trend direction

Returns:
- passed: bool (True = all filters pass)
- reasons: list of failure reasons (empty if passed)

v2.2 (2025-12-04): Added HTF trend as hard gate
- Trade direction must align with H1/H4 trend
- Counter-trend trades are BLOCKED entirely
- Moved from 20% weighted factor to binary gate

v2.1 (2025-12-04): Disabled all trading during Asian session
- ALL pairs blocked during Asian session (22:00-08:00 UTC)
- Trade only during London (08:00-17:00) and NY (13:00-22:00) sessions
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass


@dataclass
class FilterResult:
    """Result from running hard filters"""
    passed: bool
    failed_filters: List[str]
    filter_details: Dict[str, Dict[str, Any]]
    
    def __str__(self) -> str:
        if self.passed:
            return "✅ All hard filters PASSED"
        else:
            reasons = ", ".join(self.failed_filters)
            return f"❌ Hard filters FAILED: {reasons}"


class HardFilters:
    """
    Binary pass/fail gates that must ALL pass before trading.
    """
    
    def __init__(
        self,
        min_atr_pips: float = 8.0,
        news_buffer_minutes: int = 30,
        require_liquid_session: bool = True,
        pip_values: Optional[Dict[str, float]] = None
    ):
        self.min_atr_pips = min_atr_pips
        self.news_buffer_minutes = news_buffer_minutes
        self.require_liquid_session = require_liquid_session
        
        self.pip_values = pip_values or {
            'EURUSD': 0.0001, 'GBPUSD': 0.0001, 'USDJPY': 0.01, 'USDCHF': 0.0001,
            'AUDUSD': 0.0001, 'USDCAD': 0.0001, 'NZDUSD': 0.0001, 'EURGBP': 0.0001,
            'EURUSD.sim': 0.0001, 'GBPUSD.sim': 0.0001, 'USDJPY.sim': 0.01, 'USDCHF.sim': 0.0001,
            'AUDUSD.sim': 0.0001, 'USDCAD.sim': 0.0001, 'NZDUSD.sim': 0.0001, 'EURGBP.sim': 0.0001,
        }
        
        self.london_open = 8
        self.london_close = 17
        self.ny_open = 13
        self.ny_close = 22
    
    def check_all(
        self,
        features: Dict[str, float],
        symbol: str,
        current_time: Optional[datetime] = None,
        upcoming_news: Optional[List[Dict[str, Any]]] = None,
        prediction: Optional[int] = None
    ) -> FilterResult:
        if current_time is None:
            current_time = datetime.utcnow()
        
        if upcoming_news is None:
            upcoming_news = []
        
        failed_filters = []
        filter_details = {}
        
        atr_passed, atr_details = self._check_atr(features, symbol)
        filter_details['atr'] = atr_details
        if not atr_passed:
            failed_filters.append('ATR')
        
        news_passed, news_details = self._check_news(current_time, upcoming_news)
        filter_details['news'] = news_details
        if not news_passed:
            failed_filters.append('NEWS')
        
        # Pass symbol for per-pair session filtering
        session_passed, session_details = self._check_session(current_time, symbol)
        filter_details['session'] = session_details
        if not session_passed:
            failed_filters.append('SESSION')
        
        # HTF trend gate - only check if we have a directional prediction
        if prediction is not None and prediction != 1:  # Not HOLD
            htf_passed, htf_details = self._check_htf_trend(features, prediction)
            filter_details['htf_trend'] = htf_details
            if not htf_passed:
                failed_filters.append('HTF_TREND')
        
        return FilterResult(
            passed=len(failed_filters) == 0,
            failed_filters=failed_filters,
            filter_details=filter_details
        )
    
    def _check_atr(self, features: Dict[str, float], symbol: str) -> Tuple[bool, Dict[str, Any]]:
        atr_value = features.get('atr', 0.0)
        
        if atr_value <= 0:
            return False, {
                'passed': False, 'reason': f'Invalid ATR value: {atr_value}',
                'atr_value': atr_value, 'atr_pips': 0.0, 'min_required': self.min_atr_pips
            }
        
        symbol_clean = symbol.replace('.sim', '')
        pip_value = self.pip_values.get(symbol, self.pip_values.get(symbol_clean, 0.0001))
        atr_pips = atr_value / pip_value
        passed = atr_pips >= self.min_atr_pips
        
        return passed, {
            'passed': passed, 'atr_value': float(atr_value), 'atr_pips': float(atr_pips),
            'min_required': self.min_atr_pips, 'pip_value': pip_value,
            'reason': None if passed else f'ATR {atr_pips:.1f} pips < {self.min_atr_pips} minimum'
        }
    
    def _check_news(self, current_time: datetime, upcoming_news: List[Dict[str, Any]]) -> Tuple[bool, Dict[str, Any]]:
        buffer = timedelta(minutes=self.news_buffer_minutes)
        blocking_events = []
        
        for event in upcoming_news:
            event_time = event.get('time')
            impact = event.get('impact', 1)
            
            if impact < 2 or event_time is None:
                continue
            
            time_diff = abs((event_time - current_time).total_seconds() / 60)
            
            if time_diff <= self.news_buffer_minutes:
                blocking_events.append({
                    'time': event_time.isoformat(), 'impact': impact,
                    'minutes_away': time_diff, 'name': event.get('name', 'Unknown Event')
                })
        
        passed = len(blocking_events) == 0
        
        return passed, {
            'passed': passed, 'buffer_minutes': self.news_buffer_minutes,
            'blocking_events': blocking_events,
            'reason': None if passed else f'{len(blocking_events)} high-impact event(s) within {self.news_buffer_minutes} min'
        }
    
    def _check_session(self, current_time: datetime, symbol: str = '') -> Tuple[bool, Dict[str, Any]]:
        """
        Session filtering - London and New York sessions only.
        
        ALL pairs blocked during Asian session (22:00-08:00 UTC).
        
        NOTE: Existing position management (scale-in, scale-out, BE, trailing)
        continues 24/7 regardless of this filter.
        """
        if not self.require_liquid_session:
            return True, {
                'passed': True, 'reason': 'Session filter disabled', 
                'current_hour': current_time.hour, 'session': 'ANY', 'symbol': symbol
            }
        
        hour = current_time.hour
        weekday = current_time.weekday()
        
        # Weekend check - all pairs blocked
        if weekday >= 5:
            return False, {
                'passed': False, 'reason': 'Weekend - markets closed', 
                'current_hour': hour, 'weekday': weekday, 'session': 'CLOSED', 'symbol': symbol
            }
        
        in_london = self.london_open <= hour < self.london_close
        in_ny = self.ny_open <= hour < self.ny_close
        
        # Determine current session
        if in_london and in_ny:
            session = 'LONDON_NY_OVERLAP'
        elif in_london:
            session = 'LONDON'
        elif in_ny:
            session = 'NEW_YORK'
        else:
            session = 'ASIAN'
        
        # During London or NY - all pairs allowed
        if in_london or in_ny:
            return True, {
                'passed': True, 'current_hour': hour, 'weekday': weekday, 'session': session,
                'in_london': in_london, 'in_ny': in_ny, 'symbol': symbol,
                'reason': None
            }
        
        # Asian session - ALL pairs blocked
        return False, {
            'passed': False, 'current_hour': hour, 'weekday': weekday, 'session': 'ASIAN',
            'in_london': False, 'in_ny': False, 'symbol': symbol,
            'reason': 'Asian session blocked - trade London/NY only'
        }
    
    def _check_htf_trend(self, features: Dict[str, float], prediction: int) -> Tuple[bool, Dict[str, Any]]:
        """
        HTF Trend Gate - Block counter-trend trades.
        
        Trade direction must align with H1/H4 trend.
        Uses htf_trend_direction and htf_trend_alignment features.
        
        Args:
            features: Feature dict containing HTF trend indicators
            prediction: 0=SELL, 2=BUY (1=HOLD should not reach here)
            
        Returns:
            (passed, details) tuple
        """
        is_bullish_trade = prediction == 2
        
        # Get HTF trend features
        htf_trend_dir = features.get('htf_trend_direction', 0)
        htf_trend_align = features.get('htf_trend_alignment', 0)
        htf_fast_ema = features.get('htf_fast_ema', 0)
        htf_slow_ema = features.get('htf_slow_ema', 0)
        
        # Determine HTF trend direction
        # htf_trend_direction: positive = bullish, negative = bearish, 0 = neutral
        if htf_trend_dir > 0:
            htf_bullish = True
            htf_bearish = False
        elif htf_trend_dir < 0:
            htf_bullish = False
            htf_bearish = True
        else:
            # Check EMA alignment as fallback
            if htf_fast_ema > 0 and htf_slow_ema > 0:
                htf_bullish = htf_fast_ema > htf_slow_ema
                htf_bearish = htf_fast_ema < htf_slow_ema
            else:
                # Neutral - allow trade (no clear trend to oppose)
                return True, {
                    'passed': True,
                    'reason': 'HTF trend neutral - trade allowed',
                    'htf_trend_dir': htf_trend_dir,
                    'htf_trend_align': htf_trend_align,
                    'trade_direction': 'BUY' if is_bullish_trade else 'SELL',
                    'htf_direction': 'NEUTRAL'
                }
        
        # Check alignment
        if is_bullish_trade:
            passed = htf_bullish
            htf_direction = 'BULLISH' if htf_bullish else 'BEARISH'
            reason = None if passed else f'BUY blocked - HTF trend is BEARISH'
        else:  # SELL
            passed = htf_bearish
            htf_direction = 'BEARISH' if htf_bearish else 'BULLISH'
            reason = None if passed else f'SELL blocked - HTF trend is BULLISH'
        
        return passed, {
            'passed': passed,
            'reason': reason,
            'htf_trend_dir': htf_trend_dir,
            'htf_trend_align': htf_trend_align,
            'trade_direction': 'BUY' if is_bullish_trade else 'SELL',
            'htf_direction': htf_direction
        }
    
    def get_session_info(self, current_time: Optional[datetime] = None) -> Dict[str, Any]:
        if current_time is None:
            current_time = datetime.utcnow()
        
        hour = current_time.hour
        in_london = self.london_open <= hour < self.london_close
        in_ny = self.ny_open <= hour < self.ny_close
        
        if in_london and in_ny:
            session_name = 'London/NY Overlap'
            liquidity = 'HIGH'
            allowed_pairs = 'ALL'
        elif in_london:
            session_name = 'London'
            liquidity = 'MEDIUM-HIGH'
            allowed_pairs = 'ALL'
        elif in_ny:
            session_name = 'New York'
            liquidity = 'MEDIUM-HIGH'
            allowed_pairs = 'ALL'
        else:
            session_name = 'Asian'
            liquidity = 'LOW'
            allowed_pairs = 'NONE - Trading disabled'
        
        if not in_london and not in_ny:
            if hour < self.london_open:
                hours_until = self.london_open - hour
            else:
                hours_until = (24 - hour) + self.london_open
        else:
            hours_until = 0
        
        return {
            'current_time_utc': current_time.isoformat(), 
            'session_name': session_name,
            'liquidity': liquidity, 
            'in_london': in_london, 
            'in_ny': in_ny, 
            'hours_until_liquid': hours_until,
            'allowed_pairs': allowed_pairs
        }


def passes_hard_filters(
    features: Dict[str, float],
    symbol: str,
    current_time: Optional[datetime] = None,
    upcoming_news: Optional[List[Dict[str, Any]]] = None
) -> bool:
    filters = HardFilters()
    result = filters.check_all(features, symbol, current_time, upcoming_news)
    return result.passed

```

---

## `confluence/htf_confirmation.py`

```py
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

```

---

## `confluence/level_confluence.py`

```py
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

```

---

## `confluence/pullback_detector.py`

```py
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

```

---

## `confluence/regime_detector.py`

```py
"""
Regime Detector - ADX-Based Market Regime Classification
=========================================================

Detects current market regime:
- TRENDING: Strong directional movement (ADX > 25)
- RANGING: Sideways consolidation (ADX < 20)
- TRANSITIONAL: Between states (ADX 20-25)

Regime affects confluence weight adjustments.
"""

import numpy as np
from typing import Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum


class Regime(Enum):
    TRENDING = "TRENDING"
    RANGING = "RANGING"
    TRANSITIONAL = "TRANSITIONAL"
    VOLATILE = "VOLATILE"


@dataclass
class RegimeState:
    """Current market regime state"""
    regime: Regime
    confidence: float
    adx_value: float
    volatility_percentile: float
    details: Dict[str, Any]
    
    def __str__(self) -> str:
        return f"Regime: {self.regime.value} (confidence: {self.confidence:.0%}, ADX: {self.adx_value:.1f})"


class RegimeDetector:
    """
    ADX-based market regime detection.
    
    Uses ADX (Average Directional Index) to classify market state:
    - ADX > 25: Trending (strong directional movement)
    - ADX < 20: Ranging (consolidation)
    - ADX 20-25: Transitional
    
    Also monitors volatility percentile for crisis detection.
    """
    
    def __init__(
        self,
        trending_threshold: float = 25.0,
        ranging_threshold: float = 20.0,
        volatile_percentile: float = 95.0,
        persistence_bars: int = 5
    ):
        self.trending_threshold = trending_threshold
        self.ranging_threshold = ranging_threshold
        self.volatile_percentile = volatile_percentile
        self.persistence_bars = persistence_bars
        
        self.regime_history: Dict[str, list] = {}
        self.current_regimes: Dict[str, Regime] = {}
    
    def detect(
        self,
        features: Dict[str, float],
        symbol: str
    ) -> RegimeState:
        """
        Detect current market regime for a symbol.
        
        Args:
            features: Dict containing ADX and volatility features
            symbol: Trading symbol (handles .sim suffix)
            
        Returns:
            RegimeState with regime classification and confidence
        """
        adx = features.get('market_regime', 0)
        if adx == 0:
            adx = self._calculate_adx_proxy(features)
        
        volatility = features.get('volatility', 0)
        atr = features.get('atr', 0)
        
        vol_percentile = features.get('regime_confidence', 50)
        if vol_percentile == 0:
            vol_percentile = self._estimate_volatility_percentile(features)
        
        if vol_percentile >= self.volatile_percentile:
            regime = Regime.VOLATILE
            confidence = min((vol_percentile - self.volatile_percentile) / 5 + 0.5, 1.0)
        elif adx >= self.trending_threshold:
            regime = Regime.TRENDING
            confidence = min((adx - self.trending_threshold) / 25 + 0.5, 1.0)
        elif adx <= self.ranging_threshold:
            regime = Regime.RANGING
            confidence = min((self.ranging_threshold - adx) / 20 + 0.5, 1.0)
        else:
            regime = Regime.TRANSITIONAL
            mid = (self.trending_threshold + self.ranging_threshold) / 2
            confidence = 1 - abs(adx - mid) / (self.trending_threshold - self.ranging_threshold)
        
        symbol_clean = symbol.replace('.sim', '')
        
        if symbol_clean not in self.regime_history:
            self.regime_history[symbol_clean] = []
        
        self.regime_history[symbol_clean].append(regime)
        if len(self.regime_history[symbol_clean]) > self.persistence_bars:
            self.regime_history[symbol_clean] = self.regime_history[symbol_clean][-self.persistence_bars:]
        
        if len(self.regime_history[symbol_clean]) >= self.persistence_bars:
            recent = self.regime_history[symbol_clean][-self.persistence_bars:]
            if all(r == regime for r in recent):
                confidence = min(confidence * 1.2, 1.0)
        
        self.current_regimes[symbol_clean] = regime
        
        return RegimeState(
            regime=regime,
            confidence=float(confidence),
            adx_value=float(adx),
            volatility_percentile=float(vol_percentile),
            details={
                'trending_threshold': self.trending_threshold,
                'ranging_threshold': self.ranging_threshold,
                'atr': float(atr),
                'volatility': float(volatility),
                'persistence_count': len(self.regime_history.get(symbol_clean, []))
            }
        )
    
    def _calculate_adx_proxy(self, features: Dict[str, float]) -> float:
        """
        Calculate ADX proxy from available features if direct ADX not available.
        """
        mtf_alignment = abs(features.get('mtf_alignment_score', 0))
        htf_trend = abs(features.get('htf_trend_direction', 0))
        trend_confirm = features.get('trend_confirm', 0)
        
        if mtf_alignment > 0 or htf_trend > 0:
            proxy = (mtf_alignment * 30 + htf_trend * 20 + trend_confirm * 10)
            return min(proxy, 50)
        
        return 22.5
    
    def _estimate_volatility_percentile(self, features: Dict[str, float]) -> float:
        """
        Estimate volatility percentile from available features.
        """
        atr = features.get('atr', 0)
        volatility = features.get('volatility', 0)
        returns_std = features.get('returns_std', 0)
        
        if volatility > 0.02:
            return 90
        elif volatility > 0.01:
            return 70
        elif volatility > 0.005:
            return 50
        else:
            return 30
    
    def get_regime_weights(self, regime: Regime) -> Dict[str, float]:
        """
        Get recommended confluence weight adjustments for regime.
        
        Returns multipliers for each confluence factor.
        """
        if regime == Regime.TRENDING:
            return {
                'mtf_trend': 1.3,
                'support_resistance': 0.7,
                'momentum': 1.5,
                'volume': 1.2,
                'volatility': 0.8
            }
        elif regime == Regime.RANGING:
            return {
                'mtf_trend': 0.8,
                'support_resistance': 1.5,
                'momentum': 0.7,
                'volume': 1.0,
                'volatility': 1.0
            }
        elif regime == Regime.VOLATILE:
            return {
                'mtf_trend': 0.5,
                'support_resistance': 1.3,
                'momentum': 0.5,
                'volume': 1.5,
                'volatility': 1.5
            }
        else:  # TRANSITIONAL
            return {
                'mtf_trend': 1.0,
                'support_resistance': 1.0,
                'momentum': 1.0,
                'volume': 1.0,
                'volatility': 1.0
            }
    
    def get_position_size_multiplier(self, regime: Regime) -> float:
        """
        Get position size multiplier based on regime.
        
        In volatile regimes, reduce position count.
        """
        if regime == Regime.VOLATILE:
            return 0.5
        elif regime == Regime.TRANSITIONAL:
            return 0.75
        else:
            return 1.0
    
    def should_trade(self, regime: Regime) -> bool:
        """
        Check if trading is recommended in current regime.
        
        All regimes allow trading but with different parameters.
        """
        return True
    
    def get_all_regimes(self) -> Dict[str, Regime]:
        """Return current regime for all tracked symbols."""
        return self.current_regimes.copy()

```

---

## `confluence/risk_manager.py`

```py
"""
Risk Manager - Portfolio Risk Tracking
======================================

Tracks risk across all open positions:
- Max total portfolio risk: 2% of account ($200 on $10K)
- Each trade: 0.01 lots
- Calculates available risk budget for new positions

All trades are 0.01 lots - no exceptions.
Scale IN = Add another 0.01 lot position
Scale OUT = Close one 0.01 lot position
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


@dataclass
class PositionRisk:
    """Risk information for a single position"""
    symbol: str
    direction: str  # 'BUY' or 'SELL'
    entry_price: float
    stop_loss: float
    lot_size: float  # Always 0.01
    risk_amount: float  # Dollar risk
    risk_percent: float  # Percent of account
    opened_at: datetime
    position_id: str
    
    def __str__(self) -> str:
        return f"{self.symbol} {self.direction} @ {self.entry_price:.5f} | Risk: ${self.risk_amount:.2f} ({self.risk_percent:.2%})"


@dataclass
class PortfolioRisk:
    """Current portfolio risk status"""
    total_risk_amount: float
    total_risk_percent: float
    available_risk_amount: float
    available_risk_percent: float
    position_count: int
    max_new_positions: int
    can_open_new: bool
    positions_by_symbol: Dict[str, int]
    details: Dict[str, Any]
    
    def __str__(self) -> str:
        return (f"Portfolio Risk: ${self.total_risk_amount:.2f} ({self.total_risk_percent:.2%}) | "
                f"Available: ${self.available_risk_amount:.2f} | "
                f"Positions: {self.position_count}")


class RiskManager:
    """
    Portfolio risk management system.
    
    Tracks all open positions and their risk contribution.
    Ensures total portfolio risk never exceeds 2% of account.
    
    Key Rules:
    - All trades are 0.01 lots - no exceptions
    - Max portfolio risk: 2% ($200 on $10K)
    - Each position risk calculated from entry to stop loss
    """
    
    def __init__(
        self,
        account_balance: float = 10000.0,
        max_portfolio_risk_percent: float = 0.02,
        default_lot_size: float = 0.01,
        max_positions_per_symbol: int = 3,
        pip_values: Optional[Dict[str, float]] = None
    ):
        self.account_balance = account_balance
        self.max_portfolio_risk_percent = max_portfolio_risk_percent
        self.default_lot_size = default_lot_size
        self.max_positions_per_symbol = max_positions_per_symbol
        
        self.max_risk_amount = account_balance * max_portfolio_risk_percent
        
        self.pip_values = pip_values or {
            'EURUSD': 0.0001, 'GBPUSD': 0.0001, 'USDJPY': 0.01, 'USDCHF': 0.0001,
            'AUDUSD': 0.0001, 'USDCAD': 0.0001, 'NZDUSD': 0.0001, 'EURGBP': 0.0001,
            'EURUSD.sim': 0.0001, 'GBPUSD.sim': 0.0001, 'USDJPY.sim': 0.01, 'USDCHF.sim': 0.0001,
            'AUDUSD.sim': 0.0001, 'USDCAD.sim': 0.0001, 'NZDUSD.sim': 0.0001, 'EURGBP.sim': 0.0001,
        }
        
        self.pip_dollar_values = {
            'EURUSD': 10.0, 'GBPUSD': 10.0, 'USDJPY': 6.7, 'USDCHF': 10.5,
            'AUDUSD': 10.0, 'USDCAD': 7.5, 'NZDUSD': 10.0, 'EURGBP': 12.5,
            'EURUSD.sim': 10.0, 'GBPUSD.sim': 10.0, 'USDJPY.sim': 6.7, 'USDCHF.sim': 10.5,
            'AUDUSD.sim': 10.0, 'USDCAD.sim': 7.5, 'NZDUSD.sim': 10.0, 'EURGBP.sim': 12.5,
        }
        
        self.open_positions: Dict[str, PositionRisk] = {}
        self._position_counter = 0
    
    def calculate_position_risk(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        lot_size: float = 0.01
    ) -> Tuple[float, float]:
        """
        Calculate risk for a potential position.
        
        Args:
            symbol: Trading symbol
            direction: 'BUY' or 'SELL'
            entry_price: Entry price
            stop_loss: Stop loss price
            lot_size: Position size (always 0.01)
            
        Returns:
            Tuple of (risk_amount_dollars, risk_percent)
        """
        symbol_clean = symbol.replace('.sim', '')
        pip_value = self.pip_values.get(symbol, self.pip_values.get(symbol_clean, 0.0001))
        pip_dollar = self.pip_dollar_values.get(symbol, self.pip_dollar_values.get(symbol_clean, 10.0))
        
        # v2.33 FIX: Check for zero-risk positions (SL at/beyond entry)
        if direction.upper() == 'BUY' and stop_loss >= entry_price:
            return 0.0, 0.0  # Zero risk for scale-in with SL at/above entry
        elif direction.upper() == 'SELL' and stop_loss <= entry_price:
            return 0.0, 0.0  # Zero risk for scale-in with SL at/below entry
        
        if direction.upper() == 'BUY':
            price_diff = entry_price - stop_loss
        else:
            price_diff = stop_loss - entry_price
        
        pips_at_risk = abs(price_diff) / pip_value
        
        # FIX: pip_dollar is per standard lot (1.0), so multiply by lot_size directly
        risk_amount = pips_at_risk * pip_dollar * lot_size
        risk_percent = risk_amount / self.account_balance
        
        return float(risk_amount), float(risk_percent)
    
    def can_open_position(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        lot_size: float = 0.01
    ) -> Tuple[bool, str]:
        """
        Check if a new position can be opened within risk limits.
        
        Args:
            symbol: Trading symbol
            direction: 'BUY' or 'SELL'
            entry_price: Entry price
            stop_loss: Stop loss price
            lot_size: Position size (always 0.01)
            
        Returns:
            Tuple of (can_open, reason)
        """
        risk_amount, risk_percent = self.calculate_position_risk(
            symbol, direction, entry_price, stop_loss, lot_size
        )
        
        current_risk = self._get_total_risk_amount()
        new_total_risk = current_risk + risk_amount
        
        if new_total_risk > self.max_risk_amount:
            return False, (
                f"Would exceed max portfolio risk: "
                f"${new_total_risk:.2f} > ${self.max_risk_amount:.2f} "
                f"(Current: ${current_risk:.2f}, New: ${risk_amount:.2f})"
            )
        
        symbol_clean = symbol.replace('.sim', '')
        symbol_positions = sum(
            1 for pos in self.open_positions.values()
            if pos.symbol.replace('.sim', '') == symbol_clean
        )
        
        if symbol_positions >= self.max_positions_per_symbol:
            return False, (
                f"Max positions per symbol reached: "
                f"{symbol_positions} >= {self.max_positions_per_symbol}"
            )
        
        return True, "OK"
    
    def add_position(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        lot_size: float = 0.01
    ) -> PositionRisk:
        """
        Add a new position to tracking.
        
        Args:
            symbol: Trading symbol
            direction: 'BUY' or 'SELL'
            entry_price: Entry price
            stop_loss: Stop loss price
            lot_size: Position size (always 0.01)
            
        Returns:
            PositionRisk object for the new position
        """
        risk_amount, risk_percent = self.calculate_position_risk(
            symbol, direction, entry_price, stop_loss, lot_size
        )
        
        self._position_counter += 1
        position_id = f"{symbol}_{direction}_{self._position_counter}"
        
        position = PositionRisk(
            symbol=symbol,
            direction=direction.upper(),
            entry_price=entry_price,
            stop_loss=stop_loss,
            lot_size=lot_size,
            risk_amount=risk_amount,
            risk_percent=risk_percent,
            opened_at=datetime.utcnow(),
            position_id=position_id
        )
        
        self.open_positions[position_id] = position
        
        return position
    
    def remove_position(self, position_id: str) -> Optional[PositionRisk]:
        """
        Remove a position from tracking (closed or stopped out).
        
        Args:
            position_id: Position identifier
            
        Returns:
            Removed PositionRisk or None if not found
        """
        return self.open_positions.pop(position_id, None)
    
    def remove_positions_for_symbol(self, symbol: str, count: int = 1) -> List[PositionRisk]:
        """
        Remove oldest positions for a symbol (for scale out).
        
        Args:
            symbol: Trading symbol
            count: Number of positions to remove
            
        Returns:
            List of removed positions
        """
        symbol_clean = symbol.replace('.sim', '')
        
        symbol_positions = [
            (pos_id, pos) for pos_id, pos in self.open_positions.items()
            if pos.symbol.replace('.sim', '') == symbol_clean
        ]
        
        symbol_positions.sort(key=lambda x: x[1].opened_at)
        
        removed = []
        for i in range(min(count, len(symbol_positions))):
            pos_id, pos = symbol_positions[i]
            if pos_id in self.open_positions:
                removed.append(self.open_positions.pop(pos_id))
        
        return removed
    
    def get_portfolio_risk(self) -> PortfolioRisk:
        """
        Get current portfolio risk status.
        
        Returns:
            PortfolioRisk with complete risk breakdown
        """
        total_risk = self._get_total_risk_amount()
        total_risk_pct = total_risk / self.account_balance
        
        available_risk = max(0, self.max_risk_amount - total_risk)
        available_risk_pct = available_risk / self.account_balance
        
        avg_position_risk = total_risk / len(self.open_positions) if self.open_positions else 20.0
        max_new = int(available_risk / avg_position_risk) if avg_position_risk > 0 else 0
        
        positions_by_symbol: Dict[str, int] = {}
        for pos in self.open_positions.values():
            symbol_clean = pos.symbol.replace('.sim', '')
            positions_by_symbol[symbol_clean] = positions_by_symbol.get(symbol_clean, 0) + 1
        
        return PortfolioRisk(
            total_risk_amount=total_risk,
            total_risk_percent=total_risk_pct,
            available_risk_amount=available_risk,
            available_risk_percent=available_risk_pct,
            position_count=len(self.open_positions),
            max_new_positions=max_new,
            can_open_new=available_risk > 0,
            positions_by_symbol=positions_by_symbol,
            details={
                'account_balance': self.account_balance,
                'max_risk_amount': self.max_risk_amount,
                'max_risk_percent': self.max_portfolio_risk_percent,
                'avg_position_risk': avg_position_risk
            }
        )
    
    def _get_total_risk_amount(self) -> float:
        """Calculate total risk from all open positions."""
        return sum(pos.risk_amount for pos in self.open_positions.values())
    
    def get_positions_for_symbol(self, symbol: str) -> List[PositionRisk]:
        """Get all positions for a specific symbol."""
        symbol_clean = symbol.replace('.sim', '')
        return [
            pos for pos in self.open_positions.values()
            if pos.symbol.replace('.sim', '') == symbol_clean
        ]
    
    def update_account_balance(self, new_balance: float) -> None:
        """
        Update account balance (after realized P&L).
        
        Args:
            new_balance: New account balance
        """
        self.account_balance = new_balance
        self.max_risk_amount = new_balance * self.max_portfolio_risk_percent
    
    def get_scaling_capacity(self, symbol: str) -> Dict[str, Any]:
        """
        Get scaling capacity for a symbol.
        
        Returns info about whether scale in/out is possible.
        """
        symbol_positions = self.get_positions_for_symbol(symbol)
        position_count = len(symbol_positions)
        
        can_scale_in = position_count < self.max_positions_per_symbol
        can_scale_out = position_count > 0
        
        portfolio_risk = self.get_portfolio_risk()
        
        return {
            'symbol': symbol,
            'current_positions': position_count,
            'max_positions': self.max_positions_per_symbol,
            'can_scale_in': can_scale_in and portfolio_risk.can_open_new,
            'can_scale_out': can_scale_out,
            'available_risk': portfolio_risk.available_risk_amount,
            'positions': symbol_positions
        }
    
    def clear_all_positions(self) -> int:
        """Clear all tracked positions. Returns count removed."""
        count = len(self.open_positions)
        self.open_positions.clear()
        return count
    
    def remove_position(self, position_id: str) -> bool:
        """
        Remove a position by ID.
        
        Args:
            position_id: Position ticket/ID to remove
            
        Returns:
            True if removed, False if not found
        """
        if position_id in self.open_positions:
            del self.open_positions[position_id]
            return True
        return False
    
    def add_position(
        self,
        symbol: str,
        direction: str,
        volume: float,
        entry_price: float,
        position_id: str,
        stop_loss: float = 0.0
    ) -> bool:
        """
        Add a position from external sync (MT5).
        
        Args:
            symbol: Trading symbol
            direction: 'BUY' or 'SELL'
            volume: Position volume
            entry_price: Entry price
            position_id: Unique position ID/ticket
            stop_loss: Stop loss price (optional)
            
        Returns:
            True if added, False if already exists
        """
        if position_id in self.open_positions:
            return False
        
        # Calculate risk if SL is provided
        risk_amount = 0.0
        if stop_loss > 0:
            # v2.33 FIX: Check for zero-risk positions (SL at/beyond entry)
            is_zero_risk = False
            if direction.upper() == 'BUY' and stop_loss >= entry_price:
                is_zero_risk = True  # SL above entry = no risk for BUY
            elif direction.upper() == 'SELL' and stop_loss <= entry_price:
                is_zero_risk = True  # SL below entry = no risk for SELL
            
            if is_zero_risk:
                risk_amount = 0.0  # Scale-in with SL at BE = zero additional risk
            else:
                pip_value = self.pip_values.get(symbol, 0.0001)
                pip_dollar = self.pip_dollar_values.get(symbol, 10.0)
                sl_pips = abs(entry_price - stop_loss) / pip_value
                # FIX: pip_dollar is per standard lot (1.0), so multiply by volume directly
                risk_amount = sl_pips * pip_dollar * volume
        else:
            # Estimate risk as $2 per 0.01 lot if no SL (reasonable for 20 pip average SL)
            risk_amount = 2.0 * (volume / 0.01)
        
        risk_percent = risk_amount / self.account_balance
        
        self.open_positions[position_id] = PositionRisk(
            symbol=symbol,
            direction=direction.upper(),
            entry_price=entry_price,
            stop_loss=stop_loss,
            lot_size=volume,
            risk_amount=risk_amount,
            risk_percent=risk_percent,
            opened_at=datetime.now(),
            position_id=position_id
        )
        
        return True

```
