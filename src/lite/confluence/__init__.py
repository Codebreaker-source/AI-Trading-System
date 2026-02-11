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
