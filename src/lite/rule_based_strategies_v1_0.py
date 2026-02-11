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
