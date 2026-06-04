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
