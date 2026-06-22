# Source Bundle: docs/full_source_bundles/04_dimensions.md


---

## `dimensions/__init__.py`

```py
"""
Dimension Checking Module for Ultimate Synthesis Trading System
================================================================

Four complementary systems for trade validation:

1. DIMENSION CHECKER - Should we trade? (Direction validation)
   Checks 4 dimensions: REGIME, SESSION, ML, CONFLUENCE
   Returns: can_trade (YES/NO), count (0-4)

2. DANGER SCORER - How much should we trade? (Position sizing)
   Scores 7 danger categories: Regime, Session, ML, Technical, 
   Stress, Correlation, Event Risk
   Returns: danger_score (0-21), size_multiplier (0-100%)

3. TRADE HISTORY TRACKER - System stress data provider
   Loads from EA's trades_execution_log.csv at startup
   Tracks: drawdown, consecutive losses, daily P&L
   Syncs with CSV every 5 minutes

4. ANTI-FRAGILE BUILDER - Position building strategy (Phase 6)
   Probe-first approach: Enter small, build as market confirms
   Stages: PROBE (0.01) -> 0.3R -> 0.6R -> 1.0R -> COMPLETE (0.05)
   Integrates with dimension/danger checks for add validation

All four work together:
- Dimensions must pass (can_trade=True)
- Danger score determines initial probe size (multiplier)
- Anti-fragile builder manages staged position building
- Each add stage re-validates dimensions + danger

Usage:
    from dimensions import (
        DimensionChecker, DangerScorer, 
        TradeHistoryTracker, AntiFragileBuilder
    )
    
    # Initialize all four
    dim_checker = DimensionChecker()
    history_tracker = TradeHistoryTracker()
    danger_scorer = DangerScorer()
    builder = AntiFragileBuilder(probe_lot=0.01, target_lot=0.05)
    
    # On new signal: create build plan with probe entry
    plan = builder.create_build_plan(symbol, direction, entry, sl, tp, dim_count)
    
    # Periodically: check for build opportunities
    build_signal = builder.check_build_opportunity(
        symbol, current_price, is_at_be, dim_count, danger_score, ...
    )
"""

from .dimension_checker import DimensionChecker, DimensionResult
from .danger_scorer import DangerScorer, DangerResult
from .trade_history_tracker import TradeHistoryTracker, TradeHistoryState
from .anti_fragile_builder import AntiFragileBuilder, BuildPlan, BuildSignal, BuildStage

__all__ = [
    'DimensionChecker', 'DimensionResult',
    'DangerScorer', 'DangerResult',
    'TradeHistoryTracker', 'TradeHistoryState',
    'AntiFragileBuilder', 'BuildPlan', 'BuildSignal', 'BuildStage'
]

```

---

## `dimensions/dimension_checker.py`

```py
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

```

---

## `dimensions/danger_scorer.py`

```py
"""
Danger Scorer - Consolidated Risk Assessment
=============================================

Consolidates 7 danger categories into a single score (0-21).
Used ALONGSIDE dimension checking:
- Dimensions: Decide IF we should trade (direction validation)
- Danger Score: Decide HOW MUCH to trade (position sizing)

Danger Categories (0-3 points each):
1. Regime Hostility - Weak trend, extreme volatility
2. Session Opposition - Off hours, not overlap
3. ML Uncertainty - Low confidence, low agreement
4. Technical Resistance - Low confluence, S/R nearby
5. System Stress - Drawdown, consecutive losses
6. Correlation Exposure - Portfolio heat, same-direction
7. Event Risk - High-impact news within window

Scoring Logic:
- Score >= 13: NO TRADE (too dangerous)
- Score < 13: Size multiplier = 1.0 - (score / 21)

Author: AI Trading System
Version: 1.0
Date: 2025-12-16
"""

from dataclasses import dataclass
from typing import Dict, Optional, List
from datetime import datetime
from enum import Enum


@dataclass
class DangerResult:
    """Result of danger scoring"""
    total_score: int                    # 0-21 total danger score
    can_trade: bool                     # True if score < 13
    size_multiplier: float              # Position size multiplier (0.0 - 1.0)
    category_scores: Dict[str, int]     # Individual category scores
    category_details: Dict[str, str]    # Explanation for each category
    
    def __str__(self):
        status = "CAN TRADE" if self.can_trade else "TOO DANGEROUS"
        return f"[DANGER {self.total_score}/21 {status}] Size: {self.size_multiplier:.0%}"


class DangerScorer:
    """
    Consolidated danger scoring system.
    
    Evaluates 7 independent risk categories and produces
    a single danger score that determines position sizing.
    
    Works alongside DimensionChecker:
    - DimensionChecker: Should we trade this direction? (YES/NO)
    - DangerScorer: How much should we risk? (0-100% of normal size)
    """
    
    def __init__(
        self,
        danger_threshold: int = 13,
        # Category-specific thresholds
        adx_weak_threshold: float = 15.0,
        atr_extreme_multiplier: float = 2.0,
        ml_low_confidence: float = 0.40,
        ml_low_agreement: float = 0.50,
        confluence_low_threshold: float = 0.30,
        drawdown_warning: float = 0.05,
        drawdown_danger: float = 0.10,
        consecutive_loss_warning: int = 2,
        consecutive_loss_danger: int = 4,
        portfolio_heat_warning: float = 0.04,
        portfolio_heat_danger: float = 0.06,
        news_warning_minutes: int = 60,
        news_danger_minutes: int = 30
    ):
        """
        Initialize danger scorer with configurable thresholds.
        
        Args:
            danger_threshold: Score at/above which trading is blocked (default 13)
            adx_weak_threshold: ADX below this = weak trend
            atr_extreme_multiplier: ATR above avg * this = extreme volatility
            ml_low_confidence: ML confidence below this = uncertain
            ml_low_agreement: Model agreement below this = uncertain
            confluence_low_threshold: Confluence below this = weak technicals
            drawdown_warning: Drawdown % triggering warning (5%)
            drawdown_danger: Drawdown % triggering danger (10%)
            consecutive_loss_warning: Consecutive losses triggering warning
            consecutive_loss_danger: Consecutive losses triggering danger
            portfolio_heat_warning: Portfolio risk % triggering warning
            portfolio_heat_danger: Portfolio risk % triggering danger
            news_warning_minutes: Minutes before HIGH news = warning
            news_danger_minutes: Minutes before HIGH news = danger
        """
        self.danger_threshold = danger_threshold
        
        # Regime thresholds
        self.adx_weak_threshold = adx_weak_threshold
        self.atr_extreme_multiplier = atr_extreme_multiplier
        
        # ML thresholds
        self.ml_low_confidence = ml_low_confidence
        self.ml_low_agreement = ml_low_agreement
        
        # Technical thresholds
        self.confluence_low_threshold = confluence_low_threshold
        
        # System stress thresholds
        self.drawdown_warning = drawdown_warning
        self.drawdown_danger = drawdown_danger
        self.consecutive_loss_warning = consecutive_loss_warning
        self.consecutive_loss_danger = consecutive_loss_danger
        
        # Portfolio thresholds
        self.portfolio_heat_warning = portfolio_heat_warning
        self.portfolio_heat_danger = portfolio_heat_danger
        
        # News thresholds
        self.news_warning_minutes = news_warning_minutes
        self.news_danger_minutes = news_danger_minutes
    
    def score_regime_hostility(
        self,
        adx: float,
        atr: float,
        atr_average: float,
        regime: str = None
    ) -> tuple[int, str]:
        """
        Category 1: Regime Hostility (0-3 points)
        
        Checks:
        - ADX < 15 = weak/choppy trend (1 point)
        - ATR > 2x average = extreme volatility (1 point)
        - VOLATILE regime detected (1 point)
        
        Args:
            adx: Current ADX value
            atr: Current ATR value
            atr_average: Average ATR (e.g., 20-period SMA of ATR)
            regime: Detected regime ('TRENDING', 'RANGING', 'VOLATILE')
            
        Returns:
            Tuple of (score 0-3, explanation string)
        """
        score = 0
        reasons = []
        
        # Check weak trend
        if adx < self.adx_weak_threshold:
            score += 1
            reasons.append(f"Weak trend (ADX {adx:.1f} < {self.adx_weak_threshold})")
        
        # Check extreme volatility
        if atr_average > 0 and atr > (atr_average * self.atr_extreme_multiplier):
            score += 1
            reasons.append(f"Extreme volatility (ATR {atr:.5f} > {self.atr_extreme_multiplier}x avg)")
        
        # Check volatile regime
        if regime and regime.upper() == 'VOLATILE':
            score += 1
            reasons.append("VOLATILE regime detected")
        
        detail = "; ".join(reasons) if reasons else "Regime OK"
        return score, detail
    
    def score_session_opposition(
        self,
        hour_utc: int,
        symbol: str = None,
        is_overlap: bool = False
    ) -> tuple[int, str]:
        """
        Category 2: Session Opposition (0-3 points)
        
        Checks:
        - Not in major session (1 point)
        - Not in overlap period (1 point)  
        - Asian session for non-JPY/AUD/NZD (1 point)
        
        Args:
            hour_utc: Current hour in UTC (0-23)
            symbol: Trading symbol (for JPY/AUD/NZD handling)
            is_overlap: Whether currently in London/NY overlap
            
        Returns:
            Tuple of (score 0-3, explanation string)
        """
        score = 0
        reasons = []
        
        # Define sessions
        london_hours = range(7, 16)      # 07:00-16:00 UTC
        ny_hours = range(12, 21)         # 12:00-21:00 UTC
        overlap_hours = range(12, 16)    # 12:00-16:00 UTC
        asian_hours = list(range(23, 24)) + list(range(0, 8))  # 23:00-08:00 UTC
        
        # Check home currency pairs for Asian session
        is_asian_home = False
        if symbol:
            symbol_upper = symbol.upper()
            is_asian_home = any(curr in symbol_upper for curr in ['JPY', 'AUD', 'NZD'])
        
        in_major_session = hour_utc in london_hours or hour_utc in ny_hours
        in_overlap = hour_utc in overlap_hours
        in_asian = hour_utc in asian_hours
        
        # Not in any major session
        if not in_major_session and not (in_asian and is_asian_home):
            score += 1
            reasons.append(f"Off-hours (UTC {hour_utc}:00)")
        
        # Not in overlap (best liquidity)
        if not in_overlap:
            score += 1
            reasons.append("Not in London/NY overlap")
        
        # Asian session for non-home currencies
        if in_asian and not is_asian_home:
            score += 1
            reasons.append("Asian session (non-home currency)")
        
        detail = "; ".join(reasons) if reasons else "Session OK"
        return score, detail
    
    def score_ml_uncertainty(
        self,
        ml_confidence: float,
        ml_agreement: float,
        prediction: str = None
    ) -> tuple[int, str]:
        """
        Category 3: ML Uncertainty (0-3 points)
        
        Checks:
        - Confidence < 40% (1 point)
        - Model agreement < 50% (1 point)
        - HOLD prediction (1 point)
        
        Args:
            ml_confidence: ML confidence score (0-1)
            ml_agreement: Percent of models agreeing (0-1)
            prediction: ML prediction ('BUY', 'SELL', 'HOLD')
            
        Returns:
            Tuple of (score 0-3, explanation string)
        """
        score = 0
        reasons = []
        
        # Low confidence
        if ml_confidence < self.ml_low_confidence:
            score += 1
            reasons.append(f"Low confidence ({ml_confidence:.0%} < {self.ml_low_confidence:.0%})")
        
        # Low agreement
        if ml_agreement < self.ml_low_agreement:
            score += 1
            reasons.append(f"Low agreement ({ml_agreement:.0%} < {self.ml_low_agreement:.0%})")
        
        # HOLD prediction
        if prediction and prediction.upper() == 'HOLD':
            score += 1
            reasons.append("HOLD prediction")
        
        detail = "; ".join(reasons) if reasons else "ML OK"
        return score, detail
    
    def score_technical_resistance(
        self,
        confluence_score: float,
        sr_distance_atr: float = None,
        trend_alignment: bool = True
    ) -> tuple[int, str]:
        """
        Category 4: Technical Resistance (0-3 points)
        
        Checks:
        - Confluence < 30% (1 point)
        - S/R level within 1 ATR (1 point)
        - Counter-trend trade (1 point)
        
        Args:
            confluence_score: Confluence score (0-1)
            sr_distance_atr: Distance to nearest S/R in ATR units (None = unknown)
            trend_alignment: Whether trade aligns with HTF trend
            
        Returns:
            Tuple of (score 0-3, explanation string)
        """
        score = 0
        reasons = []
        
        # Low confluence
        if confluence_score < self.confluence_low_threshold:
            score += 1
            reasons.append(f"Low confluence ({confluence_score:.0%} < {self.confluence_low_threshold:.0%})")
        
        # S/R nearby
        if sr_distance_atr is not None and sr_distance_atr < 1.0:
            score += 1
            reasons.append(f"S/R nearby ({sr_distance_atr:.1f} ATR)")
        
        # Counter-trend
        if not trend_alignment:
            score += 1
            reasons.append("Counter-trend trade")
        
        detail = "; ".join(reasons) if reasons else "Technicals OK"
        return score, detail
    
    def score_system_stress(
        self,
        current_drawdown: float,
        consecutive_losses: int,
        daily_pnl_percent: float = 0.0
    ) -> tuple[int, str]:
        """
        Category 5: System Stress (0-3 points)
        
        Checks:
        - Drawdown > 5% warning / > 10% danger (0-2 points)
        - Consecutive losses > 2 warning / > 4 danger (0-1 point)
        
        Args:
            current_drawdown: Current drawdown as decimal (0.05 = 5%)
            consecutive_losses: Number of consecutive losing trades
            daily_pnl_percent: Today's P&L as decimal (for future use)
            
        Returns:
            Tuple of (score 0-3, explanation string)
        """
        score = 0
        reasons = []
        
        # Drawdown check
        if current_drawdown >= self.drawdown_danger:
            score += 2
            reasons.append(f"DANGER drawdown ({current_drawdown:.1%} >= {self.drawdown_danger:.1%})")
        elif current_drawdown >= self.drawdown_warning:
            score += 1
            reasons.append(f"Warning drawdown ({current_drawdown:.1%} >= {self.drawdown_warning:.1%})")
        
        # Consecutive losses check
        if consecutive_losses >= self.consecutive_loss_danger:
            score += 1
            reasons.append(f"Losing streak ({consecutive_losses} >= {self.consecutive_loss_danger})")
        elif consecutive_losses >= self.consecutive_loss_warning:
            # Only add if we have room (max 3)
            if score < 3:
                score += 1
                reasons.append(f"Minor losing streak ({consecutive_losses} >= {self.consecutive_loss_warning})")
        
        # Cap at 3
        score = min(score, 3)
        
        detail = "; ".join(reasons) if reasons else "System OK"
        return score, detail
    
    def score_correlation_exposure(
        self,
        portfolio_heat: float,
        same_direction_count: int,
        symbol: str = None,
        open_symbols: List[str] = None
    ) -> tuple[int, str]:
        """
        Category 6: Correlation Exposure (0-3 points)
        
        Checks:
        - Portfolio heat > 4% warning / > 6% danger (0-2 points)
        - 3+ positions in same direction (1 point)
        
        Args:
            portfolio_heat: Current portfolio risk as decimal (0.04 = 4%)
            same_direction_count: Positions in same direction as proposed trade
            symbol: Symbol being traded (for correlation check)
            open_symbols: List of currently open symbols
            
        Returns:
            Tuple of (score 0-3, explanation string)
        """
        score = 0
        reasons = []
        
        # Portfolio heat check
        if portfolio_heat >= self.portfolio_heat_danger:
            score += 2
            reasons.append(f"High portfolio heat ({portfolio_heat:.1%} >= {self.portfolio_heat_danger:.1%})")
        elif portfolio_heat >= self.portfolio_heat_warning:
            score += 1
            reasons.append(f"Elevated portfolio heat ({portfolio_heat:.1%} >= {self.portfolio_heat_warning:.1%})")
        
        # Same direction exposure
        if same_direction_count >= 3:
            if score < 3:
                score += 1
                reasons.append(f"Same-direction exposure ({same_direction_count} positions)")
        
        # Cap at 3
        score = min(score, 3)
        
        detail = "; ".join(reasons) if reasons else "Exposure OK"
        return score, detail
    
    def score_event_risk(
        self,
        minutes_to_high_impact: int = None,
        has_pending_high_impact: bool = False,
        news_sentiment: str = None
    ) -> tuple[int, str]:
        """
        Category 7: Event Risk (0-3 points)
        
        Checks:
        - HIGH impact news within 60 min (1 point)
        - HIGH impact news within 30 min (2 points)
        - Currently in news blackout (3 points)
        
        Args:
            minutes_to_high_impact: Minutes until next HIGH impact event (None = no event)
            has_pending_high_impact: Whether HIGH impact news is pending
            news_sentiment: News sentiment if available ('POSITIVE', 'NEGATIVE', 'NEUTRAL')
            
        Returns:
            Tuple of (score 0-3, explanation string)
        """
        score = 0
        reasons = []
        
        if minutes_to_high_impact is not None and minutes_to_high_impact >= 0:
            if minutes_to_high_impact <= 0:
                # Currently in news window
                score = 3
                reasons.append("In news blackout window")
            elif minutes_to_high_impact <= self.news_danger_minutes:
                score = 2
                reasons.append(f"HIGH news in {minutes_to_high_impact} min (< {self.news_danger_minutes})")
            elif minutes_to_high_impact <= self.news_warning_minutes:
                score = 1
                reasons.append(f"HIGH news in {minutes_to_high_impact} min (< {self.news_warning_minutes})")
        elif has_pending_high_impact:
            score = 1
            reasons.append("HIGH impact news pending today")
        
        detail = "; ".join(reasons) if reasons else "No event risk"
        return score, detail
    
    def calculate_danger_score(
        self,
        # Category 1: Regime
        adx: float = 25.0,
        atr: float = 0.0,
        atr_average: float = 0.0,
        regime: str = None,
        # Category 2: Session
        hour_utc: int = 12,
        symbol: str = None,
        # Category 3: ML
        ml_confidence: float = 0.50,
        ml_agreement: float = 0.67,
        ml_prediction: str = None,
        # Category 4: Technical
        confluence_score: float = 0.40,
        sr_distance_atr: float = None,
        trend_alignment: bool = True,
        # Category 5: System Stress
        current_drawdown: float = 0.0,
        consecutive_losses: int = 0,
        daily_pnl_percent: float = 0.0,
        # Category 6: Correlation
        portfolio_heat: float = 0.0,
        same_direction_count: int = 0,
        open_symbols: List[str] = None,
        # Category 7: Event Risk
        minutes_to_high_impact: int = None,
        has_pending_high_impact: bool = False
    ) -> DangerResult:
        """
        Calculate total danger score from all 7 categories.
        
        Args:
            [See individual category methods for parameter descriptions]
            
        Returns:
            DangerResult with total score, can_trade flag, size multiplier, and details
        """
        category_scores = {}
        category_details = {}
        
        # Score each category
        score1, detail1 = self.score_regime_hostility(adx, atr, atr_average, regime)
        category_scores['regime'] = score1
        category_details['regime'] = detail1
        
        score2, detail2 = self.score_session_opposition(hour_utc, symbol)
        category_scores['session'] = score2
        category_details['session'] = detail2
        
        score3, detail3 = self.score_ml_uncertainty(ml_confidence, ml_agreement, ml_prediction)
        category_scores['ml'] = score3
        category_details['ml'] = detail3
        
        score4, detail4 = self.score_technical_resistance(confluence_score, sr_distance_atr, trend_alignment)
        category_scores['technical'] = score4
        category_details['technical'] = detail4
        
        score5, detail5 = self.score_system_stress(current_drawdown, consecutive_losses, daily_pnl_percent)
        category_scores['stress'] = score5
        category_details['stress'] = detail5
        
        score6, detail6 = self.score_correlation_exposure(portfolio_heat, same_direction_count, symbol, open_symbols)
        category_scores['correlation'] = score6
        category_details['correlation'] = detail6
        
        score7, detail7 = self.score_event_risk(minutes_to_high_impact, has_pending_high_impact)
        category_scores['event'] = score7
        category_details['event'] = detail7
        
        # Calculate total
        total_score = sum(category_scores.values())
        
        # Determine if can trade
        can_trade = total_score < self.danger_threshold
        
        # Calculate size multiplier (linear scaling)
        if not can_trade:
            size_multiplier = 0.0
        else:
            # Linear: 0 danger = 100%, 12 danger = 43%, etc.
            size_multiplier = 1.0 - (total_score / 21.0)
            size_multiplier = max(0.0, min(1.0, size_multiplier))  # Clamp 0-1
        
        return DangerResult(
            total_score=total_score,
            can_trade=can_trade,
            size_multiplier=size_multiplier,
            category_scores=category_scores,
            category_details=category_details
        )


# Convenience function for quick danger check
def quick_danger_check(
    adx: float = 25.0,
    atr: float = 0.0,
    atr_average: float = 0.0,
    hour_utc: int = 12,
    ml_confidence: float = 0.50,
    confluence_score: float = 0.40,
    current_drawdown: float = 0.0,
    portfolio_heat: float = 0.0
) -> DangerResult:
    """
    Quick danger check with minimal parameters.
    
    Example:
        result = quick_danger_check(adx=10, hour_utc=22, current_drawdown=0.08)
        if result.can_trade:
            print(f"Trade at {result.size_multiplier:.0%} size")
        else:
            print(f"Skip trade - danger score {result.total_score}/21")
    """
    scorer = DangerScorer()
    return scorer.calculate_danger_score(
        adx=adx,
        atr=atr,
        atr_average=atr_average,
        hour_utc=hour_utc,
        ml_confidence=ml_confidence,
        confluence_score=confluence_score,
        current_drawdown=current_drawdown,
        portfolio_heat=portfolio_heat
    )


# Test function
def _test_danger_scorer():
    """Test danger scorer with various scenarios"""
    scorer = DangerScorer()
    
    print("=" * 60)
    print("DANGER SCORER TEST")
    print("=" * 60)
    
    # Scenario 1: Perfect conditions
    print("\n1. PERFECT CONDITIONS:")
    result = scorer.calculate_danger_score(
        adx=30.0, atr=0.001, atr_average=0.001,
        hour_utc=14, symbol='EURUSD',
        ml_confidence=0.75, ml_agreement=0.80,
        confluence_score=0.55,
        current_drawdown=0.02, consecutive_losses=0,
        portfolio_heat=0.02, same_direction_count=1
    )
    print(f"   {result}")
    for cat, score in result.category_scores.items():
        print(f"   - {cat}: {score}/3 - {result.category_details[cat]}")
    
    # Scenario 2: Moderate danger
    print("\n2. MODERATE DANGER:")
    result = scorer.calculate_danger_score(
        adx=12.0, atr=0.002, atr_average=0.001,  # Weak trend, high vol
        hour_utc=20, symbol='EURUSD',  # Late session
        ml_confidence=0.45, ml_agreement=0.55,  # Low confidence
        confluence_score=0.35,
        current_drawdown=0.06, consecutive_losses=2,  # Some stress
        portfolio_heat=0.04, same_direction_count=2
    )
    print(f"   {result}")
    for cat, score in result.category_scores.items():
        print(f"   - {cat}: {score}/3 - {result.category_details[cat]}")
    
    # Scenario 3: High danger (should block)
    print("\n3. HIGH DANGER (should block):")
    result = scorer.calculate_danger_score(
        adx=10.0, atr=0.003, atr_average=0.001, regime='VOLATILE',
        hour_utc=4, symbol='EURUSD',  # Asian, non-home
        ml_confidence=0.30, ml_agreement=0.40, ml_prediction='HOLD',
        confluence_score=0.20,
        current_drawdown=0.12, consecutive_losses=5,
        portfolio_heat=0.07, same_direction_count=4,
        minutes_to_high_impact=15
    )
    print(f"   {result}")
    for cat, score in result.category_scores.items():
        print(f"   - {cat}: {score}/3 - {result.category_details[cat]}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    _test_danger_scorer()

```

---

## `dimensions/trade_history_tracker.py`

```py
"""
Trade History Tracker - Hybrid CSV + Memory Tracking
=====================================================

Loads trade history from EA's trades_execution_log.csv at startup,
then tracks in memory during runtime with periodic sync.

Provides:
- Current drawdown estimate (from dd_tier + daily_pnl_pct)
- Consecutive loss count
- Daily P&L
- Portfolio heat (from RiskManager)

Used by DangerScorer for System Stress category.

Author: AI Trading System
Version: 1.0
Date: 2025-12-16
"""

import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field
import logging


# Default path to EA's trade execution log
DEFAULT_MT5_FILES_PATH = r"C:\Users\mt5-admin\AppData\Roaming\MetaQuotes\Terminal\EE0304F13905552AE0B5EAEFB04866EB\MQL5\Files"
DEFAULT_TRADES_LOG = "trades_execution_log.csv"


@dataclass
class TradeRecord:
    """Single trade record"""
    timestamp: datetime
    symbol: str
    action: str  # BUY or SELL
    lot_size: float
    result: str  # SUCCESS, FAILED, etc.
    daily_pnl_pct: float
    dd_tier: int
    ticket: int = 0
    
    @property
    def is_success(self) -> bool:
        return self.result.upper() == 'SUCCESS'
    
    @property
    def is_loss(self) -> bool:
        # Consider failed trades and successful trades that closed at loss
        # For now, we can only determine from result column
        return self.result.upper() == 'FAILED'


@dataclass
class TradeHistoryState:
    """Current state derived from trade history"""
    consecutive_losses: int = 0
    consecutive_wins: int = 0
    current_drawdown: float = 0.0  # Decimal (0.05 = 5%)
    daily_pnl_pct: float = 0.0
    dd_tier: int = 0
    total_trades_today: int = 0
    last_sync: datetime = field(default_factory=datetime.now)
    
    def __str__(self):
        return (f"[HISTORY] DD: {self.current_drawdown:.1%} (Tier {self.dd_tier}) | "
                f"Daily: {self.daily_pnl_pct:+.2%} | "
                f"Streak: {self.consecutive_losses}L/{self.consecutive_wins}W")


class TradeHistoryTracker:
    """
    Hybrid trade history tracker.
    
    - Loads from CSV at startup
    - Tracks in memory during runtime
    - Syncs with CSV periodically (default: 5 minutes)
    
    Provides data for DangerScorer's System Stress category.
    """
    
    def __init__(
        self,
        trades_log_path: str = None,
        sync_interval_minutes: int = 5,
        logger: logging.Logger = None
    ):
        """
        Initialize trade history tracker.
        
        Args:
            trades_log_path: Path to trades_execution_log.csv (or auto-detect)
            sync_interval_minutes: How often to re-sync with CSV (default 5)
            logger: Logger instance (optional)
        """
        self.logger = logger or logging.getLogger(__name__)
        self.sync_interval = timedelta(minutes=sync_interval_minutes)
        
        # Resolve CSV path
        if trades_log_path:
            self.trades_log_path = Path(trades_log_path)
        else:
            self.trades_log_path = Path(DEFAULT_MT5_FILES_PATH) / DEFAULT_TRADES_LOG
        
        # State
        self.state = TradeHistoryState()
        self.trade_history: List[TradeRecord] = []
        self._last_sync_time = datetime.min
        
        # Drawdown tier mapping (from EA's risk management)
        self.dd_tier_to_percent = {
            0: 0.02,   # Normal: ~2% or less
            1: 0.07,   # Warning: ~5-10%
            2: 0.12,   # Danger: ~10-15%
            3: 0.18    # Critical: >15%
        }
        
        # Initial load
        self._load_from_csv()
    
    def _load_from_csv(self) -> bool:
        """
        Load trade history from CSV file.
        
        Returns:
            True if loaded successfully, False otherwise
        """
        if not self.trades_log_path.exists():
            self.logger.warning(f"Trades log not found: {self.trades_log_path}")
            return False
        
        try:
            df = pd.read_csv(self.trades_log_path)
            
            if df.empty:
                self.logger.info("Trades log is empty")
                return True
            
            # Parse records
            self.trade_history = []
            for _, row in df.iterrows():
                try:
                    record = TradeRecord(
                        timestamp=pd.to_datetime(row.get('timestamp', '')),
                        symbol=str(row.get('symbol', '')),
                        action=str(row.get('action', '')),
                        lot_size=float(row.get('lot_size', 0.01)),
                        result=str(row.get('result', 'UNKNOWN')),
                        daily_pnl_pct=float(row.get('daily_pnl_pct', 0.0)),
                        dd_tier=int(row.get('dd_tier', 0)),
                        ticket=int(row.get('ticket', 0))
                    )
                    self.trade_history.append(record)
                except Exception as e:
                    # Skip malformed rows
                    continue
            
            # Update state from history
            self._update_state_from_history()
            self._last_sync_time = datetime.now()
            
            self.logger.info(f"Loaded {len(self.trade_history)} trades from CSV")
            self.logger.info(f"Current state: {self.state}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading trades CSV: {e}")
            return False
    
    def _update_state_from_history(self):
        """Update state from loaded trade history."""
        if not self.trade_history:
            self.state = TradeHistoryState()
            return
        
        # Get latest trade for dd_tier and daily_pnl
        latest = self.trade_history[-1]
        self.state.dd_tier = latest.dd_tier
        self.state.daily_pnl_pct = latest.daily_pnl_pct
        
        # Calculate drawdown estimate
        self.state.current_drawdown = self._calculate_drawdown(
            latest.dd_tier, 
            latest.daily_pnl_pct
        )
        
        # Count consecutive losses (from most recent backwards)
        self.state.consecutive_losses = self._count_consecutive_losses()
        self.state.consecutive_wins = self._count_consecutive_wins()
        
        # Count today's trades
        today = datetime.now().date()
        self.state.total_trades_today = sum(
            1 for t in self.trade_history 
            if t.timestamp.date() == today
        )
        
        self.state.last_sync = datetime.now()
    
    def _calculate_drawdown(self, dd_tier: int, daily_pnl_pct: float) -> float:
        """
        Calculate drawdown estimate from dd_tier and daily_pnl_pct.
        
        Uses hybrid approach:
        - Base from dd_tier (EA's categorization)
        - Adjust with daily_pnl if negative
        
        Args:
            dd_tier: EA's drawdown tier (0-3)
            daily_pnl_pct: Today's P&L as decimal
            
        Returns:
            Estimated drawdown as decimal (0.05 = 5%)
        """
        # Base drawdown from tier
        base_dd = self.dd_tier_to_percent.get(dd_tier, 0.02)
        
        # Adjust with daily P&L if negative
        if daily_pnl_pct < 0:
            return max(base_dd, abs(daily_pnl_pct))
        
        return base_dd
    
    def _count_consecutive_losses(self) -> int:
        """
        Count consecutive losing trades from most recent.
        
        Only counts SUCCESS trades as potential losses (FAILED = didn't execute).
        For now, we don't have profit data, so we estimate from patterns.
        
        Returns:
            Number of consecutive losses
        """
        if not self.trade_history:
            return 0
        
        # Filter to only executed trades (SUCCESS)
        executed = [t for t in self.trade_history if t.result.upper() == 'SUCCESS']
        
        if not executed:
            return 0
        
        # We don't have actual P&L, so we use dd_tier changes as proxy
        # If dd_tier increased recently, likely had losses
        consecutive = 0
        
        # Look at last N trades for dd_tier pattern
        recent = executed[-10:]  # Last 10 executed trades
        
        if len(recent) < 2:
            return 0
        
        # Check if dd_tier has been increasing (indicates losses)
        for i in range(len(recent) - 1, 0, -1):
            if recent[i].dd_tier >= recent[i-1].dd_tier and recent[i].dd_tier > 0:
                consecutive += 1
            else:
                break
        
        return consecutive
    
    def _count_consecutive_wins(self) -> int:
        """
        Count consecutive winning trades from most recent.
        
        Returns:
            Number of consecutive wins
        """
        if not self.trade_history:
            return 0
        
        # Filter to only executed trades
        executed = [t for t in self.trade_history if t.result.upper() == 'SUCCESS']
        
        if not executed:
            return 0
        
        consecutive = 0
        recent = executed[-10:]
        
        if len(recent) < 2:
            return 0
        
        # Check if dd_tier has been decreasing or stable at 0 (indicates wins)
        for i in range(len(recent) - 1, 0, -1):
            if recent[i].dd_tier <= recent[i-1].dd_tier and recent[i].dd_tier == 0:
                consecutive += 1
            else:
                break
        
        return consecutive
    
    def sync_if_needed(self) -> bool:
        """
        Re-sync with CSV if sync interval has passed.
        
        Returns:
            True if synced, False if not needed yet
        """
        if datetime.now() - self._last_sync_time > self.sync_interval:
            self.logger.debug("Sync interval reached, reloading CSV...")
            return self._load_from_csv()
        return False
    
    def force_sync(self) -> bool:
        """
        Force immediate sync with CSV.
        
        Returns:
            True if synced successfully
        """
        return self._load_from_csv()
    
    def get_current_drawdown(self) -> float:
        """
        Get current drawdown estimate.
        
        Returns:
            Drawdown as decimal (0.05 = 5%)
        """
        self.sync_if_needed()
        return self.state.current_drawdown
    
    def get_consecutive_losses(self) -> int:
        """
        Get current consecutive loss count.
        
        Returns:
            Number of consecutive losses
        """
        self.sync_if_needed()
        return self.state.consecutive_losses
    
    def get_daily_pnl(self) -> float:
        """
        Get today's P&L percentage.
        
        Returns:
            Daily P&L as decimal
        """
        self.sync_if_needed()
        return self.state.daily_pnl_pct
    
    def get_dd_tier(self) -> int:
        """
        Get current drawdown tier (0-3).
        
        Returns:
            Drawdown tier from EA
        """
        self.sync_if_needed()
        return self.state.dd_tier
    
    def get_danger_inputs(self) -> Dict:
        """
        Get all inputs needed for DangerScorer's System Stress category.
        
        Returns:
            Dict with current_drawdown, consecutive_losses, daily_pnl_percent
        """
        self.sync_if_needed()
        return {
            'current_drawdown': self.state.current_drawdown,
            'consecutive_losses': self.state.consecutive_losses,
            'daily_pnl_percent': self.state.daily_pnl_pct
        }
    
    def get_state_summary(self) -> str:
        """Get human-readable state summary."""
        return str(self.state)
    
    def update_trade_result(self, symbol: str, action: str, result: str, 
                           daily_pnl_pct: float = None, dd_tier: int = None):
        """
        Update state with new trade result (runtime tracking).
        
        Call this after a trade completes to keep state fresh without CSV sync.
        
        Args:
            symbol: Trading symbol
            action: BUY or SELL
            result: SUCCESS or FAILED
            daily_pnl_pct: Updated daily P&L (optional)
            dd_tier: Updated drawdown tier (optional)
        """
        record = TradeRecord(
            timestamp=datetime.now(),
            symbol=symbol,
            action=action,
            lot_size=0.01,
            result=result,
            daily_pnl_pct=daily_pnl_pct or self.state.daily_pnl_pct,
            dd_tier=dd_tier or self.state.dd_tier
        )
        
        self.trade_history.append(record)
        self._update_state_from_history()
        
        self.logger.info(f"Trade result updated: {symbol} {action} {result}")
        self.logger.info(f"New state: {self.state}")


# Test function
def _test_trade_history_tracker():
    """Test trade history tracker."""
    print("=" * 60)
    print("TRADE HISTORY TRACKER TEST")
    print("=" * 60)
    
    # Initialize tracker
    tracker = TradeHistoryTracker()
    
    print(f"\nCSV Path: {tracker.trades_log_path}")
    print(f"CSV Exists: {tracker.trades_log_path.exists()}")
    print(f"Trades Loaded: {len(tracker.trade_history)}")
    print(f"\nCurrent State:")
    print(f"  {tracker.state}")
    
    print(f"\nDanger Inputs:")
    inputs = tracker.get_danger_inputs()
    for key, value in inputs.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    _test_trade_history_tracker()

```

---

## `dimensions/anti_fragile_builder.py`

```py
"""
Anti-Fragile Position Builder - Phase 6 Ultimate Synthesis
==========================================================

Implements probe-first position building strategy:
- Enter with PROBE position (20% of target)
- Add at R-levels (0.3R, 0.6R, 1.0R, 1.5R) if dimensions still agree
- Full size only when market PROVES you right

Key Principle: Let winners prove themselves before committing capital.

Integration with existing system:
- Uses DimensionChecker for re-validation before adds
- Uses DangerScorer for size multiplier adjustments
- Respects existing BE/pullback requirements
- Works with TradeHistoryTracker for system stress awareness

Author: AI Trading System
Version: 1.0
Date: 2025-12-16
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum
import logging


class BuildStage(Enum):
    """Position building stages"""
    PROBE = "PROBE"           # Initial entry (20%)
    ADD_03R = "ADD_0.3R"      # First add at 0.3R (40%)
    ADD_06R = "ADD_0.6R"      # Second add at 0.6R (60%)
    ADD_10R = "ADD_1.0R"      # Third add at 1.0R (80%)
    ADD_15R = "ADD_1.5R"      # Fourth add at 1.5R (100%)
    COMPLETE = "COMPLETE"     # Fully built


@dataclass
class BuildPlan:
    """
    Build plan for a single position.
    
    Tracks the intended build stages and progress.
    """
    symbol: str
    direction: str  # BUY or SELL
    entry_price: float
    sl_price: float
    tp_price: float
    
    # Lot sizing
    probe_lot: float = 0.01
    target_lot: float = 0.05
    add_lot: float = 0.01
    
    # Current state
    current_stage: BuildStage = BuildStage.PROBE
    current_lot: float = 0.01
    
    # Entry conditions (saved for re-validation)
    entry_dimension_count: int = 0
    entry_danger_score: int = 0
    entry_confluence: float = 0.0
    entry_timestamp: datetime = field(default_factory=datetime.now)
    
    # Stage tracking
    stages_completed: List[str] = field(default_factory=list)
    stages_skipped: List[str] = field(default_factory=list)
    
    # R-level triggers (fraction of risk)
    r_triggers: Dict[str, float] = field(default_factory=lambda: {
        'ADD_0.3R': 0.3,
        'ADD_0.6R': 0.6,
        'ADD_1.0R': 1.0,
        'ADD_1.5R': 1.5
    })
    
    def __post_init__(self):
        """Initialize stages_completed if not set"""
        if not self.stages_completed:
            self.stages_completed = ['PROBE']
    
    @property
    def risk_pips(self) -> float:
        """Calculate risk in pips from entry to SL"""
        pip_value = 0.01 if 'JPY' in self.symbol else 0.0001
        if self.direction.upper() == 'BUY':
            return abs(self.entry_price - self.sl_price) / pip_value
        else:
            return abs(self.sl_price - self.entry_price) / pip_value
    
    @property
    def reward_pips(self) -> float:
        """Calculate reward in pips from entry to TP"""
        pip_value = 0.01 if 'JPY' in self.symbol else 0.0001
        if self.direction.upper() == 'BUY':
            return abs(self.tp_price - self.entry_price) / pip_value
        else:
            return abs(self.entry_price - self.tp_price) / pip_value
    
    @property
    def build_progress(self) -> float:
        """Returns build progress as percentage (0.0 to 1.0)"""
        return self.current_lot / self.target_lot
    
    @property
    def is_complete(self) -> bool:
        """Check if position is fully built"""
        return self.current_stage == BuildStage.COMPLETE
    
    def get_next_stage(self) -> Optional[BuildStage]:
        """Get the next build stage"""
        stage_order = [
            BuildStage.PROBE,
            BuildStage.ADD_03R,
            BuildStage.ADD_06R,
            BuildStage.ADD_10R,
            BuildStage.ADD_15R,
            BuildStage.COMPLETE
        ]
        
        try:
            current_idx = stage_order.index(self.current_stage)
            if current_idx < len(stage_order) - 1:
                return stage_order[current_idx + 1]
        except ValueError:
            pass
        
        return None
    
    def get_r_trigger_for_stage(self, stage: BuildStage) -> float:
        """Get the R-level trigger for a specific stage"""
        stage_name = stage.value.replace('ADD_', '').replace('R', '')
        return self.r_triggers.get(stage.value, 0.0)


@dataclass
class BuildSignal:
    """Signal to add to a position"""
    symbol: str
    direction: str
    lot_size: float
    stage: BuildStage
    current_r: float
    reason: str
    dimension_count: int
    danger_score: int
    confluence_score: float
    can_build: bool = True


class AntiFragileBuilder:
    """
    Manages anti-fragile position building.
    
    Responsibilities:
    - Create build plans for new positions
    - Track progress of existing build plans
    - Validate conditions for adding to positions
    - Generate build signals when conditions are met
    """
    
    def __init__(
        self,
        probe_lot: float = 0.01,
        target_lot: float = 0.05,
        add_lot: float = 0.01,
        min_dimension_count: int = 3,
        max_danger_score: int = 13,
        require_be_for_add: bool = True,
        logger: logging.Logger = None
    ):
        """
        Initialize position builder.
        
        Args:
            probe_lot: Initial probe position size
            target_lot: Target full position size
            add_lot: Size of each add
            min_dimension_count: Minimum dimensions required for adds
            max_danger_score: Maximum danger score to allow adds
            require_be_for_add: Require position at BE before adding
            logger: Logger instance
        """
        self.probe_lot = probe_lot
        self.target_lot = target_lot
        self.add_lot = add_lot
        self.min_dimension_count = min_dimension_count
        self.max_danger_score = max_danger_score
        self.require_be_for_add = require_be_for_add
        self.logger = logger or logging.getLogger(__name__)
        
        # Active build plans: {symbol: BuildPlan}
        self.build_plans: Dict[str, BuildPlan] = {}
        
        # R-level triggers
        self.r_triggers = {
            BuildStage.ADD_03R: 0.3,
            BuildStage.ADD_06R: 0.6,
            BuildStage.ADD_10R: 1.0,
            BuildStage.ADD_15R: 1.5
        }
    
    def create_build_plan(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        sl_price: float,
        tp_price: float,
        dimension_count: int,
        danger_score: int,
        confluence_score: float,
        size_multiplier: float = 1.0
    ) -> BuildPlan:
        """
        Create a new build plan for a position.
        
        Args:
            symbol: Trading symbol
            direction: BUY or SELL
            entry_price: Entry price
            sl_price: Stop loss price
            tp_price: Take profit price
            dimension_count: Number of agreeing dimensions at entry
            danger_score: Danger score at entry
            confluence_score: Confluence score at entry
            size_multiplier: Danger-based size multiplier (0.0-1.0)
            
        Returns:
            BuildPlan instance
        """
        # Apply size multiplier to lot sizes
        adjusted_probe = self.probe_lot  # Probe always minimum
        adjusted_target = self.target_lot * size_multiplier
        adjusted_add = self.add_lot * size_multiplier
        
        # Ensure minimum lot sizes
        adjusted_target = max(adjusted_target, self.probe_lot)
        adjusted_add = max(adjusted_add, self.probe_lot)
        
        plan = BuildPlan(
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            sl_price=sl_price,
            tp_price=tp_price,
            probe_lot=adjusted_probe,
            target_lot=adjusted_target,
            add_lot=adjusted_add,
            current_stage=BuildStage.PROBE,
            current_lot=adjusted_probe,
            entry_dimension_count=dimension_count,
            entry_danger_score=danger_score,
            entry_confluence=confluence_score,
            entry_timestamp=datetime.now()
        )
        
        # Store plan
        self.build_plans[symbol] = plan
        
        self.logger.info(
            f"[BUILD] Created plan: {symbol} {direction} | "
            f"Probe: {adjusted_probe} → Target: {adjusted_target} | "
            f"Dims: {dimension_count}, Danger: {danger_score}"
        )
        
        return plan
    
    def get_build_plan(self, symbol: str) -> Optional[BuildPlan]:
        """Get existing build plan for a symbol"""
        return self.build_plans.get(symbol)
    
    def remove_build_plan(self, symbol: str):
        """Remove build plan (position closed)"""
        if symbol in self.build_plans:
            plan = self.build_plans.pop(symbol)
            self.logger.info(
                f"[BUILD] Removed plan: {symbol} | "
                f"Progress: {plan.build_progress:.0%} | "
                f"Stage: {plan.current_stage.value}"
            )
    
    def calculate_current_r(
        self,
        symbol: str,
        current_price: float,
        plan: BuildPlan
    ) -> float:
        """
        Calculate current R-multiple (profit in terms of risk).
        
        R = 1.0 means price moved equal to risk distance.
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            plan: Build plan for the position
            
        Returns:
            Current R-multiple (can be negative if in loss)
        """
        pip_value = 0.01 if 'JPY' in symbol else 0.0001
        
        # Risk in price terms
        risk_distance = abs(plan.entry_price - plan.sl_price)
        
        if risk_distance == 0:
            return 0.0
        
        # Current profit in price terms
        if plan.direction.upper() == 'BUY':
            profit_distance = current_price - plan.entry_price
        else:
            profit_distance = plan.entry_price - current_price
        
        return profit_distance / risk_distance
    
    def check_build_opportunity(
        self,
        symbol: str,
        current_price: float,
        is_at_be: bool,
        current_dimension_count: int,
        current_danger_score: int,
        current_confluence: float
    ) -> Optional[BuildSignal]:
        """
        Check if conditions are met to add to a position.
        
        Validation checks:
        1. Build plan exists and not complete
        2. R-level trigger reached
        3. Position at breakeven (if required)
        4. Dimension count >= entry dimension count
        5. Danger score < max threshold
        6. Confluence still adequate
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            is_at_be: Whether position is at breakeven
            current_dimension_count: Current dimension agreement count
            current_danger_score: Current danger score
            current_confluence: Current confluence score
            
        Returns:
            BuildSignal if add is recommended, None otherwise
        """
        plan = self.build_plans.get(symbol)
        
        if not plan:
            return None
        
        if plan.is_complete:
            return None
        
        # Calculate current R
        current_r = self.calculate_current_r(symbol, current_price, plan)
        
        # Get next stage
        next_stage = plan.get_next_stage()
        if not next_stage or next_stage == BuildStage.COMPLETE:
            return None
        
        # Get R trigger for next stage
        r_trigger = self.r_triggers.get(next_stage, 0.0)
        
        # Check 1: R-level reached?
        if current_r < r_trigger:
            return None  # Not at trigger level yet
        
        # Check 2: At breakeven? (if required)
        if self.require_be_for_add and not is_at_be:
            return BuildSignal(
                symbol=symbol,
                direction=plan.direction,
                lot_size=0,
                stage=next_stage,
                current_r=current_r,
                reason=f"R-level {r_trigger} reached but not at BE",
                dimension_count=current_dimension_count,
                danger_score=current_danger_score,
                confluence_score=current_confluence,
                can_build=False
            )
        
        # Check 3: Dimensions still agree?
        if current_dimension_count < plan.entry_dimension_count:
            plan.stages_skipped.append(f"{next_stage.value}:dims_degraded")
            return BuildSignal(
                symbol=symbol,
                direction=plan.direction,
                lot_size=0,
                stage=next_stage,
                current_r=current_r,
                reason=f"Dimensions degraded: {current_dimension_count} < {plan.entry_dimension_count}",
                dimension_count=current_dimension_count,
                danger_score=current_danger_score,
                confluence_score=current_confluence,
                can_build=False
            )
        
        # Check 4: Danger score acceptable?
        if current_danger_score >= self.max_danger_score:
            plan.stages_skipped.append(f"{next_stage.value}:danger_high")
            return BuildSignal(
                symbol=symbol,
                direction=plan.direction,
                lot_size=0,
                stage=next_stage,
                current_r=current_r,
                reason=f"Danger too high: {current_danger_score} >= {self.max_danger_score}",
                dimension_count=current_dimension_count,
                danger_score=current_danger_score,
                confluence_score=current_confluence,
                can_build=False
            )
        
        # Check 5: Confluence still adequate?
        min_confluence = plan.entry_confluence * 0.8  # Allow 20% degradation
        if current_confluence < min_confluence:
            plan.stages_skipped.append(f"{next_stage.value}:confluence_low")
            return BuildSignal(
                symbol=symbol,
                direction=plan.direction,
                lot_size=0,
                stage=next_stage,
                current_r=current_r,
                reason=f"Confluence degraded: {current_confluence:.2f} < {min_confluence:.2f}",
                dimension_count=current_dimension_count,
                danger_score=current_danger_score,
                confluence_score=current_confluence,
                can_build=False
            )
        
        # All checks passed - generate build signal
        return BuildSignal(
            symbol=symbol,
            direction=plan.direction,
            lot_size=plan.add_lot,
            stage=next_stage,
            current_r=current_r,
            reason=f"Build at {r_trigger}R: dims={current_dimension_count}, danger={current_danger_score}",
            dimension_count=current_dimension_count,
            danger_score=current_danger_score,
            confluence_score=current_confluence,
            can_build=True
        )
    
    def execute_build(self, symbol: str, stage: BuildStage) -> bool:
        """
        Mark a build stage as executed.
        
        Args:
            symbol: Trading symbol
            stage: Stage that was executed
            
        Returns:
            True if successful
        """
        plan = self.build_plans.get(symbol)
        
        if not plan:
            return False
        
        # Update plan
        plan.current_stage = stage
        plan.current_lot += plan.add_lot
        plan.stages_completed.append(stage.value)
        
        # Check if complete
        if plan.current_lot >= plan.target_lot:
            plan.current_stage = BuildStage.COMPLETE
        
        self.logger.info(
            f"[BUILD] Executed {stage.value}: {symbol} | "
            f"Now: {plan.current_lot:.2f} / {plan.target_lot:.2f} "
            f"({plan.build_progress:.0%})"
        )
        
        return True
    
    def get_probe_lot_for_signal(
        self,
        size_multiplier: float = 1.0
    ) -> float:
        """
        Get the probe lot size for a new position.
        
        For anti-fragile entry, always use probe size regardless of multiplier.
        The multiplier affects the TARGET, not the probe.
        
        Args:
            size_multiplier: Danger-based size multiplier (for target calculation)
            
        Returns:
            Probe lot size (always minimum)
        """
        return self.probe_lot
    
    def get_all_build_plans(self) -> Dict[str, BuildPlan]:
        """Get all active build plans"""
        return self.build_plans.copy()
    
    def get_build_summary(self) -> str:
        """Get summary of all build plans"""
        if not self.build_plans:
            return "[BUILD] No active build plans"
        
        lines = ["[BUILD] Active Plans:"]
        for symbol, plan in self.build_plans.items():
            lines.append(
                f"  {symbol}: {plan.current_stage.value} | "
                f"{plan.current_lot:.2f}/{plan.target_lot:.2f} ({plan.build_progress:.0%}) | "
                f"Entry dims: {plan.entry_dimension_count}"
            )
        
        return "\n".join(lines)
    
    def sync_with_positions(self, open_positions: Dict[str, Dict]):
        """
        Sync build plans with actual open positions.
        
        Removes build plans for positions that no longer exist.
        
        Args:
            open_positions: Current open positions from EA
        """
        symbols_to_remove = []
        
        for symbol in self.build_plans:
            if symbol not in open_positions:
                symbols_to_remove.append(symbol)
        
        for symbol in symbols_to_remove:
            self.remove_build_plan(symbol)
            self.logger.info(f"[BUILD] Synced: removed plan for closed position {symbol}")


# Test function
def _test_position_builder():
    """Test position builder functionality"""
    print("=" * 60)
    print("ANTI-FRAGILE BUILDER TEST")
    print("=" * 60)
    
    builder = AntiFragileBuilder(
        probe_lot=0.01,
        target_lot=0.05,
        add_lot=0.01
    )
    
    # Test 1: Create build plan
    print("\n--- Test 1: Create Build Plan ---")
    plan = builder.create_build_plan(
        symbol="EURUSD.sim",
        direction="BUY",
        entry_price=1.0500,
        sl_price=1.0450,  # 50 pip SL
        tp_price=1.0600,  # 100 pip TP (2:1 R:R)
        dimension_count=4,
        danger_score=5,
        confluence_score=0.65,
        size_multiplier=0.80
    )
    
    print(f"Plan created: {plan.symbol}")
    print(f"  Probe: {plan.probe_lot}, Target: {plan.target_lot}")
    print(f"  Risk: {plan.risk_pips:.1f} pips, Reward: {plan.reward_pips:.1f} pips")
    print(f"  Entry dims: {plan.entry_dimension_count}")
    
    # Test 2: Check build at various R levels
    print("\n--- Test 2: Check Build Opportunities ---")
    
    test_prices = [
        (1.0515, False, "At 0.3R, no BE"),
        (1.0515, True, "At 0.3R, at BE"),
        (1.0530, True, "At 0.6R, at BE"),
        (1.0550, True, "At 1.0R, at BE"),
        (1.0575, True, "At 1.5R, at BE"),
    ]
    
    for price, is_be, desc in test_prices:
        current_r = builder.calculate_current_r("EURUSD.sim", price, plan)
        
        signal = builder.check_build_opportunity(
            symbol="EURUSD.sim",
            current_price=price,
            is_at_be=is_be,
            current_dimension_count=4,
            current_danger_score=5,
            current_confluence=0.60
        )
        
        print(f"\n{desc} (R={current_r:.2f}):")
        if signal:
            print(f"  Can build: {signal.can_build}")
            print(f"  Stage: {signal.stage.value}")
            print(f"  Reason: {signal.reason}")
            
            if signal.can_build:
                builder.execute_build("EURUSD.sim", signal.stage)
                print(f"  -> Executed! Now at {plan.build_progress:.0%}")
    
    # Test 3: Dimension degradation
    print("\n--- Test 3: Dimension Degradation ---")
    signal = builder.check_build_opportunity(
        symbol="EURUSD.sim",
        current_price=1.0590,
        is_at_be=True,
        current_dimension_count=2,  # Degraded from 4
        current_danger_score=5,
        current_confluence=0.60
    )
    
    if signal:
        print(f"Can build: {signal.can_build}")
        print(f"Reason: {signal.reason}")
    
    # Test 4: Summary
    print("\n--- Test 4: Build Summary ---")
    print(builder.get_build_summary())
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    _test_position_builder()

```
