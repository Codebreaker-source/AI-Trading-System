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
