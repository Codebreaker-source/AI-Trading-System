"""
Dimension Checker - Simple Multi-Dimensional Signal Validation
==============================================================

Checks 4 independent dimensions before allowing a trade signal.
Each dimension returns: AGREES, ABSTAINS, or DISAGREES

Count Logic:
- 4/4 AGREES = OPTIMAL setup
- 3/4 AGREES = GOOD setup  
- 2/4 AGREES = MARGINAL (skip or reduce size)
- Any DISAGREES = VETO (skip regardless of count)

Author: AI Trading System
Version: 1.0
Date: 2024-12-02
"""

from dataclasses import dataclass
from typing import Dict, Optional
from datetime import datetime
from enum import Enum


class DimensionStatus(Enum):
    """Status of each dimension check"""
    AGREES = "AGREES"
    ABSTAINS = "ABSTAINS"  
    DISAGREES = "DISAGREES"


@dataclass
class DimensionResult:
    """Result of dimension checking"""
    count: int                          # Number of AGREES (0-4)
    has_veto: bool                      # True if any DISAGREES
    can_trade: bool                     # True if count >= 3 and no veto
    details: Dict[str, str]             # Each dimension's status
    
    # Individual dimension results
    regime: str
    session: str
    ml: str
    confluence: str
    
    def __str__(self):
        status = "CAN TRADE" if self.can_trade else "BLOCKED"
        return f"[DIMS {self.count}/4 {status}] R:{self.regime[0]} S:{self.session[0]} M:{self.ml[0]} C:{self.confluence[0]}"


class DimensionChecker:
    """
    Simple dimension checker that validates trade signals across
    4 independent analytical frameworks.
    """
    
    def __init__(
        self,
        min_dimensions: int = 3,
        confluence_threshold: float = 0.35,
        ml_confidence_threshold: float = 0.35
    ):
        """
        Initialize dimension checker.
        
        Args:
            min_dimensions: Minimum AGREES needed to trade (default 3)
            confluence_threshold: Minimum confluence score for AGREES
            ml_confidence_threshold: Minimum ML confidence for AGREES
        """
        self.min_dimensions = min_dimensions
        self.confluence_threshold = confluence_threshold
        self.ml_confidence_threshold = ml_confidence_threshold
    
    def check_regime(
        self,
        proposed_direction: str,
        regime: str,
        regime_confidence: float = 0.5
    ) -> str:
        """
        Check if market regime supports proposed direction.
        
        Args:
            proposed_direction: 'BUY' or 'SELL'
            regime: 'TRENDING', 'RANGING', 'VOLATILE', or other
            regime_confidence: Confidence in regime detection (0-1)
            
        Returns:
            'AGREES', 'ABSTAINS', or 'DISAGREES'
        """
        regime = regime.upper() if regime else 'UNKNOWN'
        direction = proposed_direction.upper()
        
        # Low confidence = abstain
        if regime_confidence < 0.4:
            return DimensionStatus.ABSTAINS.value
        
        if regime == 'TRENDING':
            # In trending, we generally agree (trend direction checked elsewhere)
            return DimensionStatus.AGREES.value
            
        elif regime == 'RANGING':
            # In ranging, we abstain - could go either way
            return DimensionStatus.ABSTAINS.value
            
        elif regime == 'VOLATILE':
            # In volatile, we're cautious - abstain
            return DimensionStatus.ABSTAINS.value
            
        else:
            # Unknown regime = abstain
            return DimensionStatus.ABSTAINS.value
    
    def check_session(
        self,
        current_hour_utc: int,
        symbol: str = None
    ) -> str:
        """
        Check if current trading session is favorable.
        
        London: 07:00-16:00 UTC
        New York: 12:00-21:00 UTC  
        Overlap: 12:00-16:00 UTC (BEST)
        Tokyo: 23:00-08:00 UTC (for JPY pairs)
        
        Args:
            current_hour_utc: Current hour in UTC (0-23)
            symbol: Trading symbol (optional, for JPY handling)
            
        Returns:
            'AGREES', 'ABSTAINS', or 'DISAGREES'
        """
        hour = current_hour_utc
        is_jpy_pair = symbol and 'JPY' in symbol.upper() if symbol else False
        
        # Overlap period (12:00-16:00 UTC) = BEST
        if 12 <= hour < 16:
            return DimensionStatus.AGREES.value
        
        # London session (07:00-16:00 UTC) = GOOD
        if 7 <= hour < 16:
            return DimensionStatus.AGREES.value
        
        # New York session (12:00-21:00 UTC) = GOOD
        if 12 <= hour < 21:
            return DimensionStatus.AGREES.value
            
        # Tokyo session (23:00-08:00 UTC) - only for JPY pairs
        if is_jpy_pair and (hour >= 23 or hour < 8):
            return DimensionStatus.ABSTAINS.value  # Not ideal but acceptable
        
        # Off hours = DISAGREES (don't trade)
        if hour < 7 or hour >= 21:
            return DimensionStatus.DISAGREES.value
        
        # Default = abstain
        return DimensionStatus.ABSTAINS.value
    
    def check_ml(
        self,
        proposed_direction: str,
        ml_prediction: str,
        ml_confidence: float,
        ml_agreement: float = 1.0
    ) -> str:
        """
        Check if ML models support proposed direction.
        
        Args:
            proposed_direction: 'BUY' or 'SELL'
            ml_prediction: ML prediction ('BUY', 'SELL', 'HOLD')
            ml_confidence: ML confidence (0-1)
            ml_agreement: Percent of models agreeing (0-1)
            
        Returns:
            'AGREES', 'ABSTAINS', or 'DISAGREES'
        """
        direction = proposed_direction.upper()

        # None means no model exists for this symbol → ABSTAIN (not DISAGREE)
        if ml_prediction is None:
            return DimensionStatus.ABSTAINS.value

        prediction = ml_prediction.upper() if ml_prediction else 'HOLD'

        # HOLD prediction = abstain
        if prediction == 'HOLD':
            return DimensionStatus.ABSTAINS.value
        
        # Low confidence = abstain
        if ml_confidence < self.ml_confidence_threshold:
            return DimensionStatus.ABSTAINS.value
        
        # Prediction matches direction
        if prediction == direction:
            # High agreement = strong agree
            if ml_agreement >= 0.67:  # 2/3 models agree
                return DimensionStatus.AGREES.value
            else:
                return DimensionStatus.ABSTAINS.value  # Low agreement
        
        # Prediction opposite to direction = DISAGREE
        if (prediction == 'BUY' and direction == 'SELL') or \
           (prediction == 'SELL' and direction == 'BUY'):
            return DimensionStatus.DISAGREES.value
        
        # Default = abstain
        return DimensionStatus.ABSTAINS.value
    
    def check_confluence(
        self,
        confluence_score: float,
        proposed_direction: str = None
    ) -> str:
        """
        Check if technical confluence supports the trade.
        
        Args:
            confluence_score: Confluence score (0-1)
            proposed_direction: Direction (not used currently, for future)
            
        Returns:
            'AGREES', 'ABSTAINS', or 'DISAGREES'
        """
        if confluence_score >= self.confluence_threshold + 0.15:  # Strong confluence (0.50+)
            return DimensionStatus.AGREES.value
            
        elif confluence_score >= self.confluence_threshold:  # Meets threshold
            return DimensionStatus.AGREES.value
            
        elif confluence_score >= self.confluence_threshold - 0.10:  # Close to threshold
            return DimensionStatus.ABSTAINS.value
            
        else:  # Below threshold
            return DimensionStatus.DISAGREES.value
    
    def check_all(
        self,
        proposed_direction: str,
        regime: str,
        regime_confidence: float,
        current_hour_utc: int,
        ml_prediction: str,
        ml_confidence: float,
        confluence_score: float,
        symbol: str = None,
        ml_agreement: float = 1.0
    ) -> DimensionResult:
        """
        Check all 4 dimensions and return result.
        
        Args:
            proposed_direction: 'BUY' or 'SELL'
            regime: Market regime ('TRENDING', 'RANGING', 'VOLATILE')
            regime_confidence: Confidence in regime (0-1)
            current_hour_utc: Current hour UTC (0-23)
            ml_prediction: ML prediction ('BUY', 'SELL', 'HOLD')
            ml_confidence: ML confidence (0-1)
            confluence_score: Confluence score (0-1)
            symbol: Trading symbol (optional)
            ml_agreement: ML model agreement (0-1)
            
        Returns:
            DimensionResult with count, veto status, and details
        """
        # Check each dimension
        regime_result = self.check_regime(proposed_direction, regime, regime_confidence)
        session_result = self.check_session(current_hour_utc, symbol)
        ml_result = self.check_ml(proposed_direction, ml_prediction, ml_confidence, ml_agreement)
        confluence_result = self.check_confluence(confluence_score, proposed_direction)
        
        # Collect results
        results = {
            'regime': regime_result,
            'session': session_result,
            'ml': ml_result,
            'confluence': confluence_result
        }
        
        # Count AGREES
        agrees_count = sum(1 for v in results.values() if v == DimensionStatus.AGREES.value)
        
        # Check for DISAGREES (veto)
        has_veto = any(v == DimensionStatus.DISAGREES.value for v in results.values())
        
        # Determine if can trade
        can_trade = (agrees_count >= self.min_dimensions) and (not has_veto)
        
        return DimensionResult(
            count=agrees_count,
            has_veto=has_veto,
            can_trade=can_trade,
            details=results,
            regime=regime_result,
            session=session_result,
            ml=ml_result,
            confluence=confluence_result
        )


# Convenience function for quick checking
def quick_dimension_check(
    direction: str,
    regime: str,
    hour_utc: int,
    ml_pred: str,
    ml_conf: float,
    confluence: float
) -> DimensionResult:
    """
    Quick dimension check with defaults.
    
    Example:
        result = quick_dimension_check('BUY', 'TRENDING', 14, 'BUY', 0.65, 0.45)
        if result.can_trade:
            print(f"Trade allowed: {result.count}/4 dimensions agree")
    """
    checker = DimensionChecker()
    return checker.check_all(
        proposed_direction=direction,
        regime=regime,
        regime_confidence=0.6,
        current_hour_utc=hour_utc,
        ml_prediction=ml_pred,
        ml_confidence=ml_conf,
        confluence_score=confluence
    )
