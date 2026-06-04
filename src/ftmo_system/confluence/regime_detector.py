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
