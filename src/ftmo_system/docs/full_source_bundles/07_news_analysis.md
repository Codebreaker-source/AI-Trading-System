# Source Bundle: docs/full_source_bundles/07_news_analysis.md


---

## `news_analysis/__init__.py`

```py
"""
News Analysis System
=====================

Comprehensive news and economic analysis system for forex trading.

Components:
1. Economic Calendar - Event scheduling and trade blocking
2. Data Release Analyzer - Surprise detection and bias generation
3. Central Bank Analyzer - Fed/ECB/BOJ/BOE sentiment analysis
4. Government Analyzer - Fiscal policy and Treasury analysis
5. Bias Manager - Unified bias state management

Usage:
    from news_analysis import NewsAnalyzer
    
    # Initialize
    analyzer = NewsAnalyzer()
    
    # Update all biases
    analyzer.update()
    
    # Check if trade is allowed
    allowed, reason = analyzer.is_trade_allowed('EURUSD', 'BUY')
    
    # Get confidence adjustment
    adjustment = analyzer.get_confidence_adjustment('EURUSD', 'BUY')
    
    # Get current bias
    bias = analyzer.get_bias('EURUSD')
    print(f"Direction: {bias.direction}, Strength: {bias.strength}")

Author: AI Trading System
Version: 1.0
Date: 2025-11-29
"""

from typing import Dict, Tuple, Optional, List

# Core config
from .config import (
    ImpactLevel,
    BiasDirection,
    BiasStrength,
    TIMING,
    CURRENCY_MAPPING,
    HIGH_IMPACT_EVENTS,
)

# Sentiment engine
from .sentiment_engine import SentimentEngine, SentimentResult

# Analyzers
from .economic_calendar import EconomicCalendar, CalendarState, BlockedPeriod
from .data_release_analyzer import DataReleaseAnalyzer, DataSurprise
from .central_bank_analyzer import CentralBankAnalyzer, CentralBankBias
from .government_analyzer import GovernmentAnalyzer, FiscalBias

# Unified manager
from .bias_manager import BiasManager, UnifiedBias

# Data sources
from .data_sources import (
    ForexFactoryScraper,
    EconomicEvent,
    FREDClient,
    EconomicDataPoint,
    CentralBankFeeds,
    CentralBankStatement,
)


class NewsAnalyzer:
    """
    Main interface for news analysis system.
    
    Provides simplified access to all news analysis functionality.
    """
    
    def __init__(
        self,
        fred_api_key: str = None,
        auto_update: bool = True,
        update_interval: int = 300  # 5 minutes
    ):
        """
        Initialize news analyzer.
        
        Args:
            fred_api_key: Optional FRED API key for economic data
            auto_update: Whether to auto-update on first access
            update_interval: Seconds between updates
        """
        self.bias_manager = BiasManager(
            fred_api_key=fred_api_key,
            auto_update_interval=update_interval
        )
        
        self.auto_update = auto_update
        self._initialized = False
    
    def update(self, force: bool = False) -> Dict[str, UnifiedBias]:
        """
        Update all news analysis.
        
        Args:
            force: Force immediate update
            
        Returns:
            Dict of pair -> UnifiedBias
        """
        result = self.bias_manager.update(force=force)
        self._initialized = True
        return result
    
    def is_trade_allowed(
        self,
        pair: str,
        direction: str
    ) -> Tuple[bool, str]:
        """
        Check if a trade is allowed.
        
        Checks both calendar blocking and strong bias blocking.
        
        Args:
            pair: Currency pair (e.g., 'EURUSD' or 'EURUSD.sim')
            direction: 'BUY' or 'SELL'
            
        Returns:
            (is_allowed, reason_if_blocked)
        """
        self._ensure_initialized()
        return self.bias_manager.is_trade_allowed(pair, direction)
    
    def get_confidence_adjustment(
        self,
        pair: str,
        direction: str
    ) -> float:
        """
        Get confidence adjustment for a trade.
        
        Returns positive value if bias supports trade,
        negative if bias opposes trade.
        
        Args:
            pair: Currency pair
            direction: 'BUY' or 'SELL'
            
        Returns:
            Adjustment value (-0.15 to +0.15)
        """
        self._ensure_initialized()
        return self.bias_manager.get_confidence_adjustment(pair, direction)
    
    def get_bias(self, pair: str) -> UnifiedBias:
        """
        Get current unified bias for a pair.
        
        Args:
            pair: Currency pair
            
        Returns:
            UnifiedBias with direction, strength, and components
        """
        self._ensure_initialized()
        return self.bias_manager.get_bias(pair)
    
    def get_all_biases(self) -> Dict[str, UnifiedBias]:
        """Get biases for all tracked pairs"""
        self._ensure_initialized()
        return self.bias_manager.pair_biases
    
    def process_economic_release(
        self,
        event_name: str,
        currency: str,
        actual: float,
        forecast: float,
        previous: float = None
    ) -> Optional[DataSurprise]:
        """
        Process a new economic data release.
        
        Call this when actual values are released.
        
        Args:
            event_name: Name of the event
            currency: Affected currency
            actual: Actual value
            forecast: Consensus forecast
            previous: Previous value (optional)
            
        Returns:
            DataSurprise if significant
        """
        return self.bias_manager.process_economic_release(
            event_name, currency, actual, forecast, previous
        )
    
    def get_upcoming_events(
        self,
        hours_ahead: int = 24,
        pair: str = None
    ) -> List[EconomicEvent]:
        """
        Get upcoming economic events.
        
        Args:
            hours_ahead: How far ahead to look
            pair: Optional pair to filter by
            
        Returns:
            List of upcoming events
        """
        self._ensure_initialized()
        
        if pair:
            return self.bias_manager.calendar.get_upcoming_for_pair(pair, hours_ahead)
        
        return self.bias_manager.calendar.state.upcoming_events
    
    def get_blocked_pairs(self) -> List[str]:
        """Get currently blocked pairs due to economic events"""
        self._ensure_initialized()
        return list(self.bias_manager.calendar.state.blocked_pairs)
    
    def get_summary(self) -> str:
        """Get human-readable summary of all biases"""
        self._ensure_initialized()
        return self.bias_manager.get_summary()
    
    def _ensure_initialized(self):
        """Ensure system is initialized"""
        if not self._initialized and self.auto_update:
            self.update()


# Convenience functions for quick access
def check_trade_allowed(pair: str, direction: str) -> Tuple[bool, str]:
    """Quick check if trade is allowed"""
    analyzer = NewsAnalyzer(auto_update=True)
    return analyzer.is_trade_allowed(pair, direction)


def get_pair_bias(pair: str) -> UnifiedBias:
    """Quick bias lookup"""
    analyzer = NewsAnalyzer(auto_update=True)
    return analyzer.get_bias(pair)


__all__ = [
    # Main class
    'NewsAnalyzer',
    
    # Config enums
    'ImpactLevel',
    'BiasDirection',
    'BiasStrength',
    
    # Data classes
    'UnifiedBias',
    'DataSurprise',
    'CentralBankBias',
    'FiscalBias',
    'EconomicEvent',
    'CalendarState',
    'BlockedPeriod',
    'SentimentResult',
    
    # Component classes
    'BiasManager',
    'EconomicCalendar',
    'DataReleaseAnalyzer',
    'CentralBankAnalyzer',
    'GovernmentAnalyzer',
    'SentimentEngine',
    
    # Data sources
    'ForexFactoryScraper',
    'FREDClient',
    'CentralBankFeeds',
    
    # Convenience functions
    'check_trade_allowed',
    'get_pair_bias',
]

```

---

## `news_analysis/config.py`

```py
"""
News Analysis System - Configuration
=====================================

Central configuration for economic calendar, sentiment analysis,
and bias management system.

Author: AI Trading System
Version: 1.0
Date: 2025-11-29
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set
from enum import Enum


class ImpactLevel(Enum):
    """Event impact levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4  # Fed decisions, NFP, etc.


class BiasDirection(Enum):
    """Currency bias direction"""
    BULLISH = 1
    NEUTRAL = 0
    BEARISH = -1


class BiasStrength(Enum):
    """Bias strength based on surprise magnitude"""
    WEAK = 1      # < 1.5 sigma
    MEDIUM = 2    # 1.5 - 2.5 sigma
    STRONG = 3    # > 2.5 sigma


# =============================================================================
# TIMING CONFIGURATION
# =============================================================================

@dataclass
class TimingConfig:
    """Timing settings for blocking and bias duration"""
    
    # Pre-event blocking (minutes before release)
    pre_event_block_high: int = 30      # High impact events
    pre_event_block_critical: int = 60  # Critical events (NFP, FOMC)
    
    # Post-event blocking (minutes after release)
    post_event_block: int = 5  # Wait for initial spike to settle
    
    # Bias duration by strength (hours)
    bias_duration_weak: float = 4.0
    bias_duration_medium: float = 6.0
    bias_duration_strong: float = 8.0
    
    # Confidence adjustments (percentage points)
    confidence_adj_weak: float = 0.05      # ±5%
    confidence_adj_medium: float = 0.10    # ±10%
    # Strong = block counter-trend (no confidence adj needed)


TIMING = TimingConfig()


# =============================================================================
# SURPRISE THRESHOLDS (Standard Deviations)
# =============================================================================

@dataclass
class SurpriseThresholds:
    """Thresholds for categorizing surprise magnitude"""
    
    weak_max: float = 1.5       # < 1.5σ = weak
    medium_max: float = 2.5     # 1.5-2.5σ = medium
    # > 2.5σ = strong


SURPRISE = SurpriseThresholds()


# =============================================================================
# CURRENCY MAPPINGS
# =============================================================================

# Which currencies are affected by which country's data
CURRENCY_MAPPING: Dict[str, List[str]] = {
    'USD': ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD'],
    'EUR': ['EURUSD', 'EURGBP'],
    'GBP': ['GBPUSD', 'EURGBP'],
    'JPY': ['USDJPY'],
    'CHF': ['USDCHF'],
    'AUD': ['AUDUSD'],
    'CAD': ['USDCAD'],
    'NZD': ['NZDUSD'],
}

# Quote currency position (True = quote, False = base)
# Determines if bullish data = bullish or bearish for the pair
QUOTE_CURRENCY: Dict[str, Dict[str, bool]] = {
    'EURUSD': {'EUR': False, 'USD': True},   # EUR is base, USD is quote
    'GBPUSD': {'GBP': False, 'USD': True},
    'USDJPY': {'USD': False, 'JPY': True},
    'USDCHF': {'USD': False, 'CHF': True},
    'AUDUSD': {'AUD': False, 'USD': True},
    'USDCAD': {'USD': False, 'CAD': True},
    'NZDUSD': {'NZD': False, 'USD': True},
    'EURGBP': {'EUR': False, 'GBP': True},
}


# =============================================================================
# HIGH-IMPACT EVENTS
# =============================================================================

# Events that trigger blocking and bias calculation
HIGH_IMPACT_EVENTS: Dict[str, Dict] = {
    # US Events
    'Non-Farm Payrolls': {'currency': 'USD', 'impact': ImpactLevel.CRITICAL},
    'NFP': {'currency': 'USD', 'impact': ImpactLevel.CRITICAL},
    'Nonfarm Payrolls': {'currency': 'USD', 'impact': ImpactLevel.CRITICAL},
    'FOMC': {'currency': 'USD', 'impact': ImpactLevel.CRITICAL},
    'Fed Interest Rate Decision': {'currency': 'USD', 'impact': ImpactLevel.CRITICAL},
    'Federal Funds Rate': {'currency': 'USD', 'impact': ImpactLevel.CRITICAL},
    'CPI': {'currency': 'USD', 'impact': ImpactLevel.CRITICAL},
    'Core CPI': {'currency': 'USD', 'impact': ImpactLevel.HIGH},
    'PPI': {'currency': 'USD', 'impact': ImpactLevel.HIGH},
    'GDP': {'currency': 'USD', 'impact': ImpactLevel.HIGH},
    'Retail Sales': {'currency': 'USD', 'impact': ImpactLevel.HIGH},
    'ISM Manufacturing': {'currency': 'USD', 'impact': ImpactLevel.HIGH},
    'ISM Services': {'currency': 'USD', 'impact': ImpactLevel.HIGH},
    'Unemployment Rate': {'currency': 'USD', 'impact': ImpactLevel.HIGH},
    'Initial Jobless Claims': {'currency': 'USD', 'impact': ImpactLevel.MEDIUM},
    'Durable Goods': {'currency': 'USD', 'impact': ImpactLevel.MEDIUM},
    'Consumer Confidence': {'currency': 'USD', 'impact': ImpactLevel.MEDIUM},
    'Michigan Consumer Sentiment': {'currency': 'USD', 'impact': ImpactLevel.MEDIUM},
    'Fed Chair Powell': {'currency': 'USD', 'impact': ImpactLevel.HIGH},
    'FOMC Minutes': {'currency': 'USD', 'impact': ImpactLevel.HIGH},
    'Treasury Auction': {'currency': 'USD', 'impact': ImpactLevel.MEDIUM},
    
    # EUR Events
    'ECB Interest Rate Decision': {'currency': 'EUR', 'impact': ImpactLevel.CRITICAL},
    'ECB Rate Decision': {'currency': 'EUR', 'impact': ImpactLevel.CRITICAL},
    'ECB Press Conference': {'currency': 'EUR', 'impact': ImpactLevel.CRITICAL},
    'ECB President Lagarde': {'currency': 'EUR', 'impact': ImpactLevel.HIGH},
    'German CPI': {'currency': 'EUR', 'impact': ImpactLevel.HIGH},
    'German GDP': {'currency': 'EUR', 'impact': ImpactLevel.HIGH},
    'German ZEW': {'currency': 'EUR', 'impact': ImpactLevel.MEDIUM},
    'German Ifo': {'currency': 'EUR', 'impact': ImpactLevel.MEDIUM},
    'Eurozone CPI': {'currency': 'EUR', 'impact': ImpactLevel.HIGH},
    'Eurozone GDP': {'currency': 'EUR', 'impact': ImpactLevel.HIGH},
    
    # GBP Events
    'BOE Interest Rate Decision': {'currency': 'GBP', 'impact': ImpactLevel.CRITICAL},
    'Bank of England Rate': {'currency': 'GBP', 'impact': ImpactLevel.CRITICAL},
    'BOE Governor Bailey': {'currency': 'GBP', 'impact': ImpactLevel.HIGH},
    'UK CPI': {'currency': 'GBP', 'impact': ImpactLevel.HIGH},
    'UK GDP': {'currency': 'GBP', 'impact': ImpactLevel.HIGH},
    'UK Retail Sales': {'currency': 'GBP', 'impact': ImpactLevel.HIGH},
    'UK Employment': {'currency': 'GBP', 'impact': ImpactLevel.HIGH},
    
    # JPY Events
    'BOJ Interest Rate Decision': {'currency': 'JPY', 'impact': ImpactLevel.CRITICAL},
    'Bank of Japan Rate': {'currency': 'JPY', 'impact': ImpactLevel.CRITICAL},
    'BOJ Governor Ueda': {'currency': 'JPY', 'impact': ImpactLevel.HIGH},
    'Japan CPI': {'currency': 'JPY', 'impact': ImpactLevel.HIGH},
    'Japan GDP': {'currency': 'JPY', 'impact': ImpactLevel.HIGH},
    'Tankan Survey': {'currency': 'JPY', 'impact': ImpactLevel.MEDIUM},
    
    # AUD Events
    'RBA Interest Rate Decision': {'currency': 'AUD', 'impact': ImpactLevel.CRITICAL},
    'RBA Rate Decision': {'currency': 'AUD', 'impact': ImpactLevel.CRITICAL},
    'Australia CPI': {'currency': 'AUD', 'impact': ImpactLevel.HIGH},
    'Australia Employment': {'currency': 'AUD', 'impact': ImpactLevel.HIGH},
    'Australia GDP': {'currency': 'AUD', 'impact': ImpactLevel.HIGH},
    
    # CAD Events
    'BOC Interest Rate Decision': {'currency': 'CAD', 'impact': ImpactLevel.CRITICAL},
    'Bank of Canada Rate': {'currency': 'CAD', 'impact': ImpactLevel.CRITICAL},
    'Canada CPI': {'currency': 'CAD', 'impact': ImpactLevel.HIGH},
    'Canada Employment': {'currency': 'CAD', 'impact': ImpactLevel.HIGH},
    'Canada GDP': {'currency': 'CAD', 'impact': ImpactLevel.HIGH},
    
    # NZD Events
    'RBNZ Interest Rate Decision': {'currency': 'NZD', 'impact': ImpactLevel.CRITICAL},
    'RBNZ Rate Decision': {'currency': 'NZD', 'impact': ImpactLevel.CRITICAL},
    'New Zealand CPI': {'currency': 'NZD', 'impact': ImpactLevel.HIGH},
    'New Zealand Employment': {'currency': 'NZD', 'impact': ImpactLevel.HIGH},
    'New Zealand GDP': {'currency': 'NZD', 'impact': ImpactLevel.HIGH},
    
    # CHF Events
    'SNB Interest Rate Decision': {'currency': 'CHF', 'impact': ImpactLevel.CRITICAL},
    'SNB Rate Decision': {'currency': 'CHF', 'impact': ImpactLevel.CRITICAL},
    'Switzerland CPI': {'currency': 'CHF', 'impact': ImpactLevel.HIGH},
    'Switzerland GDP': {'currency': 'CHF', 'impact': ImpactLevel.HIGH},
}


# =============================================================================
# SENTIMENT KEYWORDS
# =============================================================================

# Hawkish keywords (bullish for currency)
HAWKISH_KEYWORDS: Set[str] = {
    # Rate-related
    'rate hike', 'rate increase', 'tightening', 'hawkish', 'restrictive',
    'raise rates', 'higher rates', 'rate rises', 'hiking cycle',
    
    # Inflation fighting
    'combat inflation', 'fight inflation', 'inflation concerns', 'price pressures',
    'inflation too high', 'persistent inflation', 'sticky inflation',
    
    # Economic strength
    'strong economy', 'robust growth', 'solid labor market', 'tight labor',
    'overheating', 'above target', 'exceeds expectations',
    
    # Policy stance
    'further tightening', 'more work to do', 'not done yet', 'vigilant',
    'data dependent', 'prepared to act', 'all options', 'whatever it takes',
    
    # Quantitative
    'reduce balance sheet', 'quantitative tightening', 'QT', 'tapering',
}

# Dovish keywords (bearish for currency)
DOVISH_KEYWORDS: Set[str] = {
    # Rate-related
    'rate cut', 'rate decrease', 'easing', 'dovish', 'accommodative',
    'lower rates', 'rate reduction', 'cutting cycle', 'pause',
    
    # Inflation softening
    'inflation falling', 'disinflation', 'inflation easing', 'price stability',
    'inflation moderating', 'transitory', 'temporary',
    
    # Economic weakness
    'slowing growth', 'economic weakness', 'recession risk', 'soft landing',
    'labor cooling', 'unemployment rising', 'below expectations',
    
    # Policy stance
    'supportive stance', 'patient', 'wait and see', 'monitor developments',
    'downside risks', 'uncertainties', 'headwinds',
    
    # Quantitative
    'expand balance sheet', 'quantitative easing', 'QE', 'asset purchases',
}

# Neutral/uncertain keywords
NEUTRAL_KEYWORDS: Set[str] = {
    'mixed signals', 'balanced risks', 'two-sided', 'uncertain outlook',
    'data dependent', 'meeting by meeting', 'evolving', 'monitoring',
}


# =============================================================================
# GOVERNMENT/FISCAL KEYWORDS
# =============================================================================

FISCAL_BULLISH_KEYWORDS: Set[str] = {
    # Fiscal health
    'budget surplus', 'deficit reduction', 'fiscal discipline', 'debt reduction',
    'balanced budget', 'fiscal responsibility',
    
    # Economic support
    'stimulus', 'fiscal stimulus', 'infrastructure spending', 'tax cuts',
    'government investment', 'fiscal expansion',
    
    # Stability
    'debt ceiling raised', 'shutdown averted', 'bipartisan agreement',
    'fiscal deal', 'budget passed',
}

FISCAL_BEARISH_KEYWORDS: Set[str] = {
    # Fiscal concerns
    'budget deficit', 'debt ceiling', 'government shutdown', 'default risk',
    'credit downgrade', 'fiscal cliff', 'debt crisis',
    
    # Political dysfunction
    'gridlock', 'impasse', 'no deal', 'negotiations failed', 'deadline missed',
    
    # Economic drag
    'austerity', 'spending cuts', 'tax increases', 'fiscal drag',
}


# =============================================================================
# DATA SOURCE URLS
# =============================================================================

@dataclass
class DataSourceURLs:
    """URLs for data sources"""
    
    # ForexFactory
    forexfactory_calendar: str = "https://www.forexfactory.com/calendar"
    
    # Investing.com
    investing_calendar: str = "https://www.investing.com/economic-calendar/"
    
    # FRED API (Federal Reserve Economic Data)
    fred_base: str = "https://api.stlouisfed.org/fred"
    fred_series: str = "https://api.stlouisfed.org/fred/series/observations"
    
    # Central Bank RSS Feeds
    fed_rss: str = "https://www.federalreserve.gov/feeds/press_all.xml"
    ecb_rss: str = "https://www.ecb.europa.eu/rss/press.html"
    boe_rss: str = "https://www.bankofengland.co.uk/rss/news"


DATA_SOURCES = DataSourceURLs()


# =============================================================================
# FRED SERIES CODES (Free API)
# =============================================================================

FRED_SERIES: Dict[str, Dict] = {
    # Employment
    'PAYEMS': {'name': 'Nonfarm Payrolls', 'currency': 'USD', 'higher_is_bullish': True},
    'UNRATE': {'name': 'Unemployment Rate', 'currency': 'USD', 'higher_is_bullish': False},
    'ICSA': {'name': 'Initial Jobless Claims', 'currency': 'USD', 'higher_is_bullish': False},
    
    # Inflation
    'CPIAUCSL': {'name': 'CPI', 'currency': 'USD', 'higher_is_bullish': True},  # Hawks want to fight it
    'CPILFESL': {'name': 'Core CPI', 'currency': 'USD', 'higher_is_bullish': True},
    'PPIACO': {'name': 'PPI', 'currency': 'USD', 'higher_is_bullish': True},
    
    # GDP
    'GDP': {'name': 'GDP', 'currency': 'USD', 'higher_is_bullish': True},
    'GDPC1': {'name': 'Real GDP', 'currency': 'USD', 'higher_is_bullish': True},
    
    # Consumer
    'RSXFS': {'name': 'Retail Sales', 'currency': 'USD', 'higher_is_bullish': True},
    'UMCSENT': {'name': 'Consumer Sentiment', 'currency': 'USD', 'higher_is_bullish': True},
    
    # Manufacturing
    'MANEMP': {'name': 'Manufacturing Employment', 'currency': 'USD', 'higher_is_bullish': True},
    
    # Interest Rates
    'FEDFUNDS': {'name': 'Fed Funds Rate', 'currency': 'USD', 'higher_is_bullish': True},
    'DGS10': {'name': '10Y Treasury Yield', 'currency': 'USD', 'higher_is_bullish': True},
    'DGS2': {'name': '2Y Treasury Yield', 'currency': 'USD', 'higher_is_bullish': True},
}


# =============================================================================
# LOGGING CONFIG
# =============================================================================

@dataclass
class LoggingConfig:
    """Logging settings"""
    log_dir: str = "logs/news_analysis"
    events_log: str = "economic_events.csv"
    bias_log: str = "active_biases.csv"
    sentiment_log: str = "sentiment_scores.csv"
    blocking_log: str = "trade_blocks.csv"


LOGGING = LoggingConfig()

```

---

## `news_analysis/bias_manager.py`

```py
"""
Bias Manager - Central Bias State Management
=============================================

Combines all bias sources (economic releases, central bank statements,
fiscal policy) into unified trading biases per currency pair.

Implements Option C (Hybrid) with 4-8 hour duration:
- Weak surprise (< 1.5σ): Confidence ±5%, 4 hours
- Medium surprise (1.5-2.5σ): Confidence ±10%, 6 hours
- Strong surprise (> 2.5σ): Block counter-trend trades, 8 hours

Author: AI Trading System
Version: 1.0
Date: 2025-11-29
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple, Any
from dataclasses import dataclass, field
import json
from pathlib import Path

from .config import BiasDirection, BiasStrength, TIMING, LOGGING, CURRENCY_MAPPING
from .economic_calendar import EconomicCalendar
from .data_release_analyzer import DataReleaseAnalyzer, DataSurprise
from .central_bank_analyzer import CentralBankAnalyzer, CentralBankBias
from .government_analyzer import GovernmentAnalyzer, FiscalBias


@dataclass
class UnifiedBias:
    """Combined bias from all sources for a currency pair"""
    
    pair: str
    direction: BiasDirection
    strength: BiasStrength
    confidence_adjustment: float  # -0.15 to +0.15
    
    # Component biases
    data_bias: Optional[BiasDirection] = None
    central_bank_bias: Optional[BiasDirection] = None
    fiscal_bias: Optional[BiasDirection] = None
    
    # Metadata
    sources: List[str] = field(default_factory=list)
    expiry: datetime = None
    updated: datetime = None
    
    # Blocking
    should_block_buys: bool = False
    should_block_sells: bool = False
    block_reason: str = ""
    
    def is_active(self) -> bool:
        """Check if bias is still active"""
        if self.expiry is None:
            return False
        return datetime.utcnow() < self.expiry
    
    def to_dict(self) -> Dict:
        return {
            'pair': self.pair,
            'direction': self.direction.name,
            'strength': self.strength.name,
            'confidence_adjustment': self.confidence_adjustment,
            'data_bias': self.data_bias.name if self.data_bias else None,
            'central_bank_bias': self.central_bank_bias.name if self.central_bank_bias else None,
            'fiscal_bias': self.fiscal_bias.name if self.fiscal_bias else None,
            'sources': self.sources,
            'expiry': self.expiry.isoformat() if self.expiry else None,
            'updated': self.updated.isoformat() if self.updated else None,
            'should_block_buys': self.should_block_buys,
            'should_block_sells': self.should_block_sells,
            'block_reason': self.block_reason,
        }


class BiasManager:
    """
    Central manager for all trading biases.
    
    Combines:
    1. Economic data release surprises
    2. Central bank statement sentiment
    3. Fiscal policy analysis
    
    Provides unified interface for live trading system.
    """
    
    # Source weights for combining biases
    SOURCE_WEIGHTS = {
        'data_release': 0.50,      # Economic surprises most immediate
        'central_bank': 0.35,      # Policy direction important
        'fiscal': 0.15,            # Slower-moving, background
    }
    
    def __init__(
        self,
        fred_api_key: str = None,
        log_dir: str = None,
        auto_update_interval: int = 300  # 5 minutes
    ):
        """
        Initialize bias manager.
        
        Args:
            fred_api_key: API key for FRED economic data
            log_dir: Directory for logs
            auto_update_interval: Seconds between auto-updates
        """
        # Initialize analyzers
        self.calendar = EconomicCalendar()
        self.data_analyzer = DataReleaseAnalyzer(fred_api_key)
        self.central_bank = CentralBankAnalyzer()
        self.government = GovernmentAnalyzer()
        
        # Unified biases per pair
        self.pair_biases: Dict[str, UnifiedBias] = {}
        
        # Timing
        self.auto_update_interval = auto_update_interval
        self.last_update: Optional[datetime] = None
        
        # Logging
        self.log_dir = Path(log_dir) if log_dir else Path(LOGGING.log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.bias_log = self.log_dir / LOGGING.bias_log
        
        # Tracked pairs
        self.tracked_pairs = [
            'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF',
            'AUDUSD', 'USDCAD', 'NZDUSD', 'EURGBP'
        ]
    
    def update(self, force: bool = False) -> Dict[str, UnifiedBias]:
        """
        Update all biases.
        
        Args:
            force: Force update even if interval not elapsed
            
        Returns:
            Dict of pair -> UnifiedBias
        """
        now = datetime.utcnow()
        
        # Check if update needed
        if not force and self.last_update:
            elapsed = (now - self.last_update).total_seconds()
            if elapsed < self.auto_update_interval:
                return self.pair_biases
        
        # Update calendar
        self.calendar.update()
        
        # Update central bank analysis (less frequent)
        if force or self.last_update is None or \
           (now - self.last_update).total_seconds() > 900:  # 15 min
            self.central_bank.analyze_recent_statements(hours_back=48)
        
        # Update government analysis
        if force or self.last_update is None or \
           (now - self.last_update).total_seconds() > 1800:  # 30 min
            for currency in ['USD', 'EUR', 'GBP']:
                self.government.analyze_fiscal_news(currency)
        
        # Calculate unified biases for each pair
        for pair in self.tracked_pairs:
            self.pair_biases[pair] = self._calculate_unified_bias(pair)
        
        self.last_update = now
        
        # Log state
        self._log_biases()
        
        # Cleanup expired
        self._cleanup_expired()
        
        return self.pair_biases
    
    def process_economic_release(
        self,
        event_name: str,
        currency: str,
        actual: float,
        forecast: float,
        previous: float = None
    ) -> Optional[DataSurprise]:
        """
        Process a new economic data release.
        
        Call this when actual values are released to generate immediate bias.
        
        Args:
            event_name: Name of the event (e.g., 'Non-Farm Payrolls')
            currency: Currency affected
            actual: Actual released value
            forecast: Consensus forecast
            previous: Previous value (optional)
            
        Returns:
            DataSurprise with bias info
        """
        from .data_sources.forexfactory import EconomicEvent
        from .config import ImpactLevel
        
        # Create event object
        event = EconomicEvent(
            datetime_utc=datetime.utcnow(),
            currency=currency.upper(),
            event_name=event_name,
            impact=ImpactLevel.HIGH,  # Assume high if being processed
            forecast=forecast,
            previous=previous,
            actual=actual
        )
        
        # Analyze
        surprise = self.data_analyzer.analyze_release(event)
        
        if surprise:
            # Update unified biases for affected pairs
            affected_pairs = CURRENCY_MAPPING.get(currency.upper(), [])
            for pair in affected_pairs:
                if pair in self.tracked_pairs:
                    self.pair_biases[pair] = self._calculate_unified_bias(pair)
            
            self._log_biases()
        
        return surprise
    
    def get_bias(self, pair: str) -> UnifiedBias:
        """
        Get current unified bias for a pair.
        
        Args:
            pair: Currency pair (e.g., 'EURUSD' or 'EURUSD.sim')
            
        Returns:
            UnifiedBias for the pair
        """
        pair_clean = pair.replace('.sim', '').upper()
        
        if pair_clean not in self.pair_biases:
            return self._create_neutral_bias(pair_clean)
        
        bias = self.pair_biases[pair_clean]
        
        if not bias.is_active():
            return self._create_neutral_bias(pair_clean)
        
        return bias
    
    def is_trade_allowed(
        self,
        pair: str,
        direction: str  # 'BUY' or 'SELL'
    ) -> Tuple[bool, str]:
        """
        Check if a trade is allowed based on current biases.
        
        Args:
            pair: Currency pair
            direction: Trade direction
            
        Returns:
            (is_allowed, reason_if_blocked)
        """
        pair_clean = pair.replace('.sim', '').upper()
        
        # Check calendar blocking first
        calendar_allowed, calendar_reason = self.calendar.is_trading_allowed(pair_clean)
        if not calendar_allowed:
            return False, calendar_reason
        
        # Check bias blocking
        bias = self.get_bias(pair_clean)
        
        if direction.upper() == 'BUY' and bias.should_block_buys:
            return False, bias.block_reason
        
        if direction.upper() == 'SELL' and bias.should_block_sells:
            return False, bias.block_reason
        
        return True, ""
    
    def get_confidence_adjustment(self, pair: str, direction: str) -> float:
        """
        Get confidence adjustment for a trade.
        
        Positive = bias supports trade direction
        Negative = bias opposes trade direction
        
        Args:
            pair: Currency pair
            direction: Trade direction ('BUY' or 'SELL')
            
        Returns:
            Confidence adjustment (-0.15 to +0.15)
        """
        bias = self.get_bias(pair)
        
        if bias.direction == BiasDirection.NEUTRAL:
            return 0.0
        
        trade_is_bullish = direction.upper() == 'BUY'
        bias_is_bullish = bias.direction == BiasDirection.BULLISH
        
        if trade_is_bullish == bias_is_bullish:
            # Trade aligns with bias - boost confidence
            return abs(bias.confidence_adjustment)
        else:
            # Trade opposes bias - reduce confidence
            return -abs(bias.confidence_adjustment)
    
    def _calculate_unified_bias(self, pair: str) -> UnifiedBias:
        """Calculate combined bias for a pair"""
        pair_clean = pair.replace('.sim', '').upper()
        
        # Get component biases
        data_dir, data_strength, data_adj = self.data_analyzer.get_bias_for_pair(pair_clean)
        cb_dir, cb_adj = self.central_bank.get_bias_for_pair(pair_clean)
        fiscal_dir, fiscal_adj = self.government.get_bias_for_pair(pair_clean)
        
        # Combine with weights
        sources = []
        
        # Convert directions to scores (-1, 0, 1)
        scores = []
        
        if data_dir != BiasDirection.NEUTRAL:
            score = 1 if data_dir == BiasDirection.BULLISH else -1
            scores.append(score * self.SOURCE_WEIGHTS['data_release'])
            sources.append(f"data:{data_dir.name}")
        
        if cb_dir != BiasDirection.NEUTRAL:
            score = 1 if cb_dir == BiasDirection.BULLISH else -1
            scores.append(score * self.SOURCE_WEIGHTS['central_bank'])
            sources.append(f"central_bank:{cb_dir.name}")
        
        if fiscal_dir != BiasDirection.NEUTRAL:
            score = 1 if fiscal_dir == BiasDirection.BULLISH else -1
            scores.append(score * self.SOURCE_WEIGHTS['fiscal'])
            sources.append(f"fiscal:{fiscal_dir.name}")
        
        # Calculate weighted direction
        if not scores:
            return self._create_neutral_bias(pair_clean)
        
        total_score = sum(scores)
        
        # Determine direction
        if total_score > 0.2:
            direction = BiasDirection.BULLISH
        elif total_score < -0.2:
            direction = BiasDirection.BEARISH
        else:
            direction = BiasDirection.NEUTRAL
        
        # Determine strength (use strongest component)
        strength = data_strength if data_strength else BiasStrength.WEAK
        
        # Calculate confidence adjustment
        confidence_adj = data_adj + cb_adj + fiscal_adj
        confidence_adj = max(-0.15, min(0.15, confidence_adj))  # Cap at ±15%
        
        # Determine blocking
        should_block_buys = False
        should_block_sells = False
        block_reason = ""
        
        if strength == BiasStrength.STRONG:
            if direction == BiasDirection.BEARISH:
                should_block_buys = True
                block_reason = f"Strong bearish bias for {pair_clean}"
            elif direction == BiasDirection.BULLISH:
                should_block_sells = True
                block_reason = f"Strong bullish bias for {pair_clean}"
        
        # Calculate expiry (use longest active bias)
        expiry = datetime.utcnow() + timedelta(hours=4)  # Default 4 hours
        
        active_surprises = self.data_analyzer.get_active_surprises()
        for surprise in active_surprises:
            if surprise.currency in pair_clean:
                if surprise.bias_expiry > expiry:
                    expiry = surprise.bias_expiry
        
        return UnifiedBias(
            pair=pair_clean,
            direction=direction,
            strength=strength,
            confidence_adjustment=round(confidence_adj, 4),
            data_bias=data_dir if data_dir != BiasDirection.NEUTRAL else None,
            central_bank_bias=cb_dir if cb_dir != BiasDirection.NEUTRAL else None,
            fiscal_bias=fiscal_dir if fiscal_dir != BiasDirection.NEUTRAL else None,
            sources=sources,
            expiry=expiry,
            updated=datetime.utcnow(),
            should_block_buys=should_block_buys,
            should_block_sells=should_block_sells,
            block_reason=block_reason
        )
    
    def _create_neutral_bias(self, pair: str) -> UnifiedBias:
        """Create neutral bias for a pair"""
        return UnifiedBias(
            pair=pair,
            direction=BiasDirection.NEUTRAL,
            strength=BiasStrength.WEAK,
            confidence_adjustment=0.0,
            sources=[],
            expiry=datetime.utcnow() + timedelta(hours=1),
            updated=datetime.utcnow()
        )
    
    def _log_biases(self):
        """Log current biases to file"""
        try:
            data = {
                'updated': datetime.utcnow().isoformat(),
                'biases': {
                    pair: bias.to_dict()
                    for pair, bias in self.pair_biases.items()
                }
            }
            
            with open(self.bias_log, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"[BiasManager] Log error: {e}")
    
    def _cleanup_expired(self):
        """Cleanup expired biases from all analyzers"""
        self.central_bank.cleanup_expired()
        self.government.cleanup_expired()
        self.data_analyzer._cleanup_expired()
    
    def get_summary(self) -> str:
        """Get human-readable summary of all biases"""
        lines = ["=" * 60]
        lines.append("NEWS ANALYSIS BIAS SUMMARY")
        lines.append("=" * 60)
        lines.append(f"Last Update: {self.last_update}")
        lines.append("")
        
        # Calendar status
        lines.append("--- Economic Calendar ---")
        blocked = list(self.calendar.state.blocked_pairs)
        if blocked:
            lines.append(f"BLOCKED PAIRS: {', '.join(blocked)}")
        else:
            lines.append("No trading blocks active")
        
        # Pair biases
        lines.append("\n--- Pair Biases ---")
        for pair, bias in sorted(self.pair_biases.items()):
            if bias.direction != BiasDirection.NEUTRAL:
                lines.append(
                    f"{pair}: {bias.direction.name} [{bias.strength.name}] "
                    f"adj={bias.confidence_adjustment:+.1%}"
                )
                if bias.should_block_buys or bias.should_block_sells:
                    blocks = []
                    if bias.should_block_buys:
                        blocks.append("BUYS")
                    if bias.should_block_sells:
                        blocks.append("SELLS")
                    lines.append(f"  BLOCKING: {', '.join(blocks)}")
        
        if not any(b.direction != BiasDirection.NEUTRAL for b in self.pair_biases.values()):
            lines.append("All pairs neutral")
        
        lines.append("=" * 60)
        return "\n".join(lines)

```

---

## `news_analysis/sentiment_engine.py`

```py
"""
Sentiment Analysis Engine
==========================

Combines TextBlob and VADER for financial text sentiment analysis.
Also includes keyword-based hawkish/dovish detection for central bank statements.

Author: AI Trading System
Version: 1.0
Date: 2025-11-29
"""

import re
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass
from datetime import datetime

# Sentiment libraries
try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False
    print("[WARNING] TextBlob not installed. Run: pip install textblob")

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False
    print("[WARNING] VADER not installed. Run: pip install vaderSentiment")

from .config import (
    HAWKISH_KEYWORDS, DOVISH_KEYWORDS, NEUTRAL_KEYWORDS,
    FISCAL_BULLISH_KEYWORDS, FISCAL_BEARISH_KEYWORDS,
    BiasDirection
)


@dataclass
class SentimentResult:
    """Container for sentiment analysis results"""
    
    # Overall scores
    composite_score: float      # -1 to 1 (bearish to bullish for currency)
    confidence: float           # 0 to 1 (how confident in the score)
    
    # Component scores
    textblob_polarity: float    # -1 to 1
    textblob_subjectivity: float  # 0 to 1
    vader_compound: float       # -1 to 1
    vader_pos: float            # 0 to 1
    vader_neg: float            # 0 to 1
    vader_neu: float            # 0 to 1
    
    # Keyword analysis
    hawkish_count: int
    dovish_count: int
    keyword_score: float        # -1 to 1 based on keyword balance
    
    # Metadata
    text_length: int
    analysis_time: str
    
    def to_dict(self) -> Dict:
        return {
            'composite_score': self.composite_score,
            'confidence': self.confidence,
            'textblob_polarity': self.textblob_polarity,
            'textblob_subjectivity': self.textblob_subjectivity,
            'vader_compound': self.vader_compound,
            'hawkish_count': self.hawkish_count,
            'dovish_count': self.dovish_count,
            'keyword_score': self.keyword_score,
            'text_length': self.text_length,
            'analysis_time': self.analysis_time,
        }
    
    def get_direction(self) -> BiasDirection:
        """Convert score to direction enum"""
        if self.composite_score > 0.1:
            return BiasDirection.BULLISH
        elif self.composite_score < -0.1:
            return BiasDirection.BEARISH
        return BiasDirection.NEUTRAL


class SentimentEngine:
    """
    Multi-method sentiment analyzer for financial text.
    
    Combines:
    - TextBlob: General NLP sentiment
    - VADER: Social media optimized (good for news headlines)
    - Keyword matching: Domain-specific hawkish/dovish detection
    """
    
    def __init__(self):
        """Initialize sentiment analyzers"""
        
        # VADER analyzer
        if VADER_AVAILABLE:
            self.vader = SentimentIntensityAnalyzer()
        else:
            self.vader = None
        
        # Precompile keyword patterns for efficiency
        self._compile_keyword_patterns()
    
    def _compile_keyword_patterns(self):
        """Compile regex patterns for keyword matching"""
        
        # Hawkish patterns
        self.hawkish_patterns = [
            re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE)
            for kw in HAWKISH_KEYWORDS
        ]
        
        # Dovish patterns
        self.dovish_patterns = [
            re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE)
            for kw in DOVISH_KEYWORDS
        ]
        
        # Fiscal patterns
        self.fiscal_bullish_patterns = [
            re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE)
            for kw in FISCAL_BULLISH_KEYWORDS
        ]
        
        self.fiscal_bearish_patterns = [
            re.compile(r'\b' + re.escape(kw) + r'\b', re.IGNORECASE)
            for kw in FISCAL_BEARISH_KEYWORDS
        ]
    
    def analyze(self, text: str, context: str = 'monetary') -> SentimentResult:
        """
        Analyze text sentiment with combined methods.
        
        Args:
            text: Text to analyze
            context: 'monetary' for central bank, 'fiscal' for government
            
        Returns:
            SentimentResult with all scores
        """
        if not text or not text.strip():
            return self._empty_result()
        
        # Clean text
        cleaned = self._clean_text(text)
        
        # TextBlob analysis
        tb_polarity, tb_subjectivity = self._analyze_textblob(cleaned)
        
        # VADER analysis
        vader_scores = self._analyze_vader(cleaned)
        
        # Keyword analysis
        if context == 'fiscal':
            keyword_score, hawkish, dovish = self._analyze_fiscal_keywords(cleaned)
        else:
            keyword_score, hawkish, dovish = self._analyze_monetary_keywords(cleaned)
        
        # Combine scores
        composite, confidence = self._combine_scores(
            tb_polarity, vader_scores['compound'], keyword_score,
            tb_subjectivity, len(cleaned)
        )
        
        return SentimentResult(
            composite_score=composite,
            confidence=confidence,
            textblob_polarity=tb_polarity,
            textblob_subjectivity=tb_subjectivity,
            vader_compound=vader_scores['compound'],
            vader_pos=vader_scores['pos'],
            vader_neg=vader_scores['neg'],
            vader_neu=vader_scores['neu'],
            hawkish_count=hawkish,
            dovish_count=dovish,
            keyword_score=keyword_score,
            text_length=len(cleaned),
            analysis_time=datetime.now().isoformat()
        )
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove URLs
        text = re.sub(r'http\S+|www\.\S+', '', text)
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep punctuation for sentiment
        text = re.sub(r'[^\w\s.,!?;:\'-]', '', text)
        
        return text.strip()
    
    def _analyze_textblob(self, text: str) -> Tuple[float, float]:
        """Analyze with TextBlob"""
        if not TEXTBLOB_AVAILABLE:
            return 0.0, 0.5
        
        try:
            blob = TextBlob(text)
            return blob.sentiment.polarity, blob.sentiment.subjectivity
        except Exception:
            return 0.0, 0.5
    
    def _analyze_vader(self, text: str) -> Dict[str, float]:
        """Analyze with VADER"""
        if self.vader is None:
            return {'compound': 0.0, 'pos': 0.0, 'neg': 0.0, 'neu': 1.0}
        
        try:
            scores = self.vader.polarity_scores(text)
            return scores
        except Exception:
            return {'compound': 0.0, 'pos': 0.0, 'neg': 0.0, 'neu': 1.0}
    
    def _analyze_monetary_keywords(self, text: str) -> Tuple[float, int, int]:
        """
        Count hawkish vs dovish keywords.
        
        Returns:
            (score, hawkish_count, dovish_count)
            score: -1 (all dovish) to 1 (all hawkish)
        """
        hawkish_count = sum(
            1 for pattern in self.hawkish_patterns
            if pattern.search(text)
        )
        
        dovish_count = sum(
            1 for pattern in self.dovish_patterns
            if pattern.search(text)
        )
        
        total = hawkish_count + dovish_count
        if total == 0:
            return 0.0, 0, 0
        
        # Score: hawkish = positive (bullish for currency)
        score = (hawkish_count - dovish_count) / total
        
        return score, hawkish_count, dovish_count
    
    def _analyze_fiscal_keywords(self, text: str) -> Tuple[float, int, int]:
        """
        Count fiscal bullish vs bearish keywords.
        
        Returns:
            (score, bullish_count, bearish_count)
        """
        bullish_count = sum(
            1 for pattern in self.fiscal_bullish_patterns
            if pattern.search(text)
        )
        
        bearish_count = sum(
            1 for pattern in self.fiscal_bearish_patterns
            if pattern.search(text)
        )
        
        total = bullish_count + bearish_count
        if total == 0:
            return 0.0, 0, 0
        
        score = (bullish_count - bearish_count) / total
        
        return score, bullish_count, bearish_count
    
    def _combine_scores(
        self,
        tb_polarity: float,
        vader_compound: float,
        keyword_score: float,
        subjectivity: float,
        text_length: int
    ) -> Tuple[float, float]:
        """
        Combine all sentiment scores into composite.
        
        Weighting:
        - Keyword matching: 50% (most relevant for financial text)
        - VADER: 30% (good for headlines)
        - TextBlob: 20% (general NLP)
        
        Returns:
            (composite_score, confidence)
        """
        # Weighted average
        composite = (
            keyword_score * 0.50 +
            vader_compound * 0.30 +
            tb_polarity * 0.20
        )
        
        # Confidence based on:
        # - Agreement between methods
        # - Text length (more text = more confident)
        # - Subjectivity (less subjective = more factual = more confident)
        
        # Method agreement (0-1)
        scores = [tb_polarity, vader_compound, keyword_score]
        non_zero = [s for s in scores if abs(s) > 0.05]
        
        if len(non_zero) >= 2:
            # Check if signs agree
            signs = [1 if s > 0 else -1 for s in non_zero]
            agreement = 1.0 if len(set(signs)) == 1 else 0.5
        else:
            agreement = 0.3  # Not enough signal
        
        # Text length factor (more text = more confident, cap at 500 chars)
        length_factor = min(text_length / 500, 1.0)
        
        # Subjectivity factor (less subjective = more confident)
        objectivity_factor = 1.0 - subjectivity * 0.5
        
        # Combined confidence
        confidence = (
            agreement * 0.50 +
            length_factor * 0.25 +
            objectivity_factor * 0.25
        )
        
        return round(composite, 4), round(confidence, 4)
    
    def _empty_result(self) -> SentimentResult:
        """Return empty result for invalid input"""
        return SentimentResult(
            composite_score=0.0,
            confidence=0.0,
            textblob_polarity=0.0,
            textblob_subjectivity=0.5,
            vader_compound=0.0,
            vader_pos=0.0,
            vader_neg=0.0,
            vader_neu=1.0,
            hawkish_count=0,
            dovish_count=0,
            keyword_score=0.0,
            text_length=0,
            analysis_time=datetime.now().isoformat()
        )
    
    def analyze_headline(self, headline: str) -> SentimentResult:
        """
        Optimized analysis for short headlines.
        
        Uses higher keyword weight since headlines are keyword-dense.
        """
        result = self.analyze(headline)
        
        # Boost keyword influence for short text
        if result.text_length < 100:
            # Recalculate with 70% keyword weight
            adjusted = (
                result.keyword_score * 0.70 +
                result.vader_compound * 0.20 +
                result.textblob_polarity * 0.10
            )
            result.composite_score = round(adjusted, 4)
        
        return result
    
    def analyze_batch(self, texts: List[str], context: str = 'monetary') -> List[SentimentResult]:
        """Analyze multiple texts efficiently"""
        return [self.analyze(text, context) for text in texts]
    
    def get_dominant_sentiment(self, results: List[SentimentResult]) -> SentimentResult:
        """
        Aggregate multiple results into dominant sentiment.
        
        Useful for analyzing multiple headlines/statements about same event.
        """
        if not results:
            return self._empty_result()
        
        # Weighted average by confidence
        total_weight = sum(r.confidence for r in results)
        
        if total_weight == 0:
            # Equal weighting
            avg_score = sum(r.composite_score for r in results) / len(results)
            avg_confidence = 0.3
        else:
            avg_score = sum(
                r.composite_score * r.confidence for r in results
            ) / total_weight
            avg_confidence = total_weight / len(results)
        
        # Return aggregated result
        return SentimentResult(
            composite_score=round(avg_score, 4),
            confidence=round(avg_confidence, 4),
            textblob_polarity=sum(r.textblob_polarity for r in results) / len(results),
            textblob_subjectivity=sum(r.textblob_subjectivity for r in results) / len(results),
            vader_compound=sum(r.vader_compound for r in results) / len(results),
            vader_pos=sum(r.vader_pos for r in results) / len(results),
            vader_neg=sum(r.vader_neg for r in results) / len(results),
            vader_neu=sum(r.vader_neu for r in results) / len(results),
            hawkish_count=sum(r.hawkish_count for r in results),
            dovish_count=sum(r.dovish_count for r in results),
            keyword_score=sum(r.keyword_score for r in results) / len(results),
            text_length=sum(r.text_length for r in results),
            analysis_time=datetime.now().isoformat()
        )


# Convenience function
def analyze_sentiment(text: str, context: str = 'monetary') -> SentimentResult:
    """Quick sentiment analysis function"""
    engine = SentimentEngine()
    return engine.analyze(text, context)

```

---

## `news_analysis/economic_calendar.py`

```py
"""
Economic Calendar Manager
==========================

Manages economic event scheduling, trade blocking around high-impact events,
and integrates with ForexFactory scraper.

Author: AI Trading System
Version: 1.0
Date: 2025-11-29
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, field
import json
from pathlib import Path

from .config import (
    ImpactLevel, TIMING, CURRENCY_MAPPING, HIGH_IMPACT_EVENTS, LOGGING
)
from .data_sources.forexfactory import ForexFactoryScraper, EconomicEvent


@dataclass
class BlockedPeriod:
    """Represents a period when trading is blocked"""
    start: datetime
    end: datetime
    event: EconomicEvent
    reason: str
    affected_pairs: List[str]
    
    def is_active(self) -> bool:
        """Check if block is currently active"""
        now = datetime.utcnow()
        return self.start <= now <= self.end
    
    def minutes_remaining(self) -> float:
        """Minutes until block ends (negative if not active)"""
        if not self.is_active():
            return -1
        return (self.end - datetime.utcnow()).total_seconds() / 60
    
    def to_dict(self) -> Dict:
        return {
            'start': self.start.isoformat(),
            'end': self.end.isoformat(),
            'event_name': self.event.event_name,
            'currency': self.event.currency,
            'impact': self.event.impact.name,
            'reason': self.reason,
            'affected_pairs': self.affected_pairs,
        }


@dataclass
class CalendarState:
    """Current state of the economic calendar"""
    upcoming_events: List[EconomicEvent] = field(default_factory=list)
    active_blocks: List[BlockedPeriod] = field(default_factory=list)
    blocked_pairs: Set[str] = field(default_factory=set)
    last_update: Optional[datetime] = None
    
    def is_pair_blocked(self, pair: str) -> bool:
        """Check if a specific pair is blocked"""
        return pair.replace('.sim', '') in self.blocked_pairs
    
    def get_block_reason(self, pair: str) -> Optional[str]:
        """Get reason why pair is blocked"""
        pair_clean = pair.replace('.sim', '')
        for block in self.active_blocks:
            if pair_clean in block.affected_pairs:
                return block.reason
        return None


class EconomicCalendar:
    """
    Manages economic calendar events and trade blocking.
    
    Features:
    - Fetches events from ForexFactory
    - Blocks trading before/after high-impact events
    - Tracks which currency pairs are affected
    - Provides countdown to next event
    """
    
    def __init__(
        self,
        pre_block_minutes_high: int = None,
        pre_block_minutes_critical: int = None,
        post_block_minutes: int = None,
        log_dir: str = None
    ):
        """
        Initialize calendar manager.
        
        Args:
            pre_block_minutes_high: Minutes to block before HIGH impact events
            pre_block_minutes_critical: Minutes to block before CRITICAL events
            post_block_minutes: Minutes to block after release
            log_dir: Directory for logging
        """
        self.pre_block_high = pre_block_minutes_high or TIMING.pre_event_block_high
        self.pre_block_critical = pre_block_minutes_critical or TIMING.pre_event_block_critical
        self.post_block = post_block_minutes or TIMING.post_event_block
        
        # Initialize scraper
        self.scraper = ForexFactoryScraper(cache_minutes=5)
        
        # Current state
        self.state = CalendarState()
        
        # Logging
        self.log_dir = Path(log_dir) if log_dir else Path(LOGGING.log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.events_log = self.log_dir / LOGGING.events_log
        self.blocking_log = self.log_dir / LOGGING.blocking_log
    
    def update(self) -> CalendarState:
        """
        Update calendar state.
        
        Fetches latest events, calculates active blocks, updates state.
        Call this periodically (every 1-5 minutes).
        
        Returns:
            Updated CalendarState
        """
        # Fetch upcoming events
        events = self.scraper.get_events(
            hours_ahead=48,
            min_impact=ImpactLevel.MEDIUM
        )
        
        self.state.upcoming_events = events
        
        # Calculate active blocks
        self.state.active_blocks = self._calculate_blocks(events)
        
        # Update blocked pairs set
        self.state.blocked_pairs = set()
        for block in self.state.active_blocks:
            if block.is_active():
                self.state.blocked_pairs.update(block.affected_pairs)
        
        self.state.last_update = datetime.utcnow()
        
        # Log state
        self._log_state()
        
        return self.state
    
    def is_trading_allowed(self, pair: str) -> Tuple[bool, Optional[str]]:
        """
        Check if trading is allowed for a pair.
        
        Args:
            pair: Currency pair (e.g., 'EURUSD' or 'EURUSD.sim')
            
        Returns:
            (is_allowed, reason_if_blocked)
        """
        pair_clean = pair.replace('.sim', '').upper()
        
        if self.state.is_pair_blocked(pair_clean):
            reason = self.state.get_block_reason(pair_clean)
            return False, reason
        
        return True, None
    
    def get_upcoming_for_pair(
        self,
        pair: str,
        hours_ahead: int = 24
    ) -> List[EconomicEvent]:
        """Get upcoming events affecting a specific pair"""
        pair_clean = pair.replace('.sim', '').upper()
        
        # Find currencies in this pair
        currencies = self._get_pair_currencies(pair_clean)
        
        # Filter events
        cutoff = datetime.utcnow() + timedelta(hours=hours_ahead)
        
        return [
            e for e in self.state.upcoming_events
            if e.currency in currencies and e.datetime_utc <= cutoff
        ]
    
    def get_next_event(self, currency: str = None) -> Optional[EconomicEvent]:
        """Get next upcoming event (optionally filtered by currency)"""
        now = datetime.utcnow()
        
        upcoming = [
            e for e in self.state.upcoming_events
            if e.datetime_utc > now
        ]
        
        if currency:
            upcoming = [e for e in upcoming if e.currency == currency.upper()]
        
        if not upcoming:
            return None
        
        return min(upcoming, key=lambda e: e.datetime_utc)
    
    def get_minutes_until_next_block(self, pair: str = None) -> Optional[float]:
        """
        Get minutes until next trading block starts.
        
        Args:
            pair: Optional pair to check (None = any pair)
            
        Returns:
            Minutes until next block, or None if no upcoming blocks
        """
        now = datetime.utcnow()
        
        # Find upcoming blocks
        upcoming_blocks = [
            b for b in self.state.active_blocks
            if b.start > now
        ]
        
        if pair:
            pair_clean = pair.replace('.sim', '').upper()
            upcoming_blocks = [
                b for b in upcoming_blocks
                if pair_clean in b.affected_pairs
            ]
        
        if not upcoming_blocks:
            return None
        
        next_block = min(upcoming_blocks, key=lambda b: b.start)
        return (next_block.start - now).total_seconds() / 60
    
    def get_high_impact_today(self) -> List[EconomicEvent]:
        """Get all HIGH and CRITICAL events for today"""
        today = datetime.utcnow().date()
        
        return [
            e for e in self.state.upcoming_events
            if e.datetime_utc.date() == today
            and e.impact.value >= ImpactLevel.HIGH.value
        ]
    
    def _calculate_blocks(self, events: List[EconomicEvent]) -> List[BlockedPeriod]:
        """Calculate blocking periods for events"""
        blocks = []
        now = datetime.utcnow()
        
        for event in events:
            # Only block for HIGH and CRITICAL impact
            if event.impact.value < ImpactLevel.HIGH.value:
                continue
            
            # Calculate block times
            if event.impact == ImpactLevel.CRITICAL:
                pre_minutes = self.pre_block_critical
            else:
                pre_minutes = self.pre_block_high
            
            block_start = event.datetime_utc - timedelta(minutes=pre_minutes)
            block_end = event.datetime_utc + timedelta(minutes=self.post_block)
            
            # Skip if block has already ended
            if block_end < now:
                continue
            
            # Get affected pairs
            affected_pairs = CURRENCY_MAPPING.get(event.currency, [])
            
            # Create block
            reason = f"{event.event_name} ({event.currency}) at {event.datetime_utc.strftime('%H:%M')} UTC"
            
            blocks.append(BlockedPeriod(
                start=block_start,
                end=block_end,
                event=event,
                reason=reason,
                affected_pairs=affected_pairs
            ))
        
        return blocks
    
    def _get_pair_currencies(self, pair: str) -> List[str]:
        """Extract currencies from a pair symbol"""
        pair = pair.upper().replace('.SIM', '')
        
        # Standard 6-char pairs
        if len(pair) == 6:
            return [pair[:3], pair[3:]]
        
        return []
    
    def _log_state(self):
        """Log current state to files"""
        try:
            # Log upcoming events
            events_data = [e.to_dict() for e in self.state.upcoming_events[:20]]
            
            with open(self.events_log, 'w') as f:
                json.dump({
                    'updated': datetime.utcnow().isoformat(),
                    'events': events_data
                }, f, indent=2)
            
            # Log active blocks
            blocks_data = [b.to_dict() for b in self.state.active_blocks if b.is_active()]
            
            with open(self.blocking_log, 'w') as f:
                json.dump({
                    'updated': datetime.utcnow().isoformat(),
                    'active_blocks': blocks_data,
                    'blocked_pairs': list(self.state.blocked_pairs)
                }, f, indent=2)
                
        except Exception as e:
            print(f"[Calendar] Log error: {e}")
    
    def get_summary(self) -> str:
        """Get human-readable summary of current state"""
        lines = []
        lines.append(f"=== Economic Calendar Summary ===")
        lines.append(f"Last Update: {self.state.last_update}")
        lines.append(f"Upcoming Events: {len(self.state.upcoming_events)}")
        lines.append(f"Active Blocks: {len([b for b in self.state.active_blocks if b.is_active()])}")
        lines.append(f"Blocked Pairs: {', '.join(self.state.blocked_pairs) or 'None'}")
        
        # Next events
        lines.append("\n--- Next High Impact Events ---")
        high_impact = [
            e for e in self.state.upcoming_events
            if e.impact.value >= ImpactLevel.HIGH.value
        ][:5]
        
        for event in high_impact:
            mins = event.minutes_until()
            if mins > 0:
                time_str = f"in {mins:.0f} min"
            else:
                time_str = f"{abs(mins):.0f} min ago"
            
            lines.append(f"  {event.currency} {event.event_name}: {time_str}")
        
        return "\n".join(lines)


# Convenience function
def check_trading_allowed(pair: str, calendar: EconomicCalendar = None) -> Tuple[bool, str]:
    """
    Quick check if trading is allowed for a pair.
    
    Args:
        pair: Currency pair
        calendar: Optional calendar instance (creates new if None)
        
    Returns:
        (is_allowed, reason)
    """
    if calendar is None:
        calendar = EconomicCalendar()
        calendar.update()
    
    return calendar.is_trading_allowed(pair)

```

---

## `news_analysis/central_bank_analyzer.py`

```py
"""
Central Bank Statement Analyzer
================================

Analyzes central bank statements, speeches, and minutes to extract
hawkish/dovish sentiment and generate trading biases.

Author: AI Trading System
Version: 1.0
Date: 2025-11-29
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass

from .config import BiasDirection, BiasStrength, TIMING, CURRENCY_MAPPING
from .sentiment_engine import SentimentEngine, SentimentResult
from .data_sources.central_bank_feeds import CentralBankFeeds, CentralBankStatement


@dataclass
class CentralBankBias:
    """Bias derived from central bank communication"""
    
    bank: str
    currency: str
    direction: BiasDirection
    strength: BiasStrength
    sentiment_score: float      # -1 to 1
    confidence: float           # 0 to 1
    
    # Source info
    statement_title: str
    statement_type: str         # rate_decision, minutes, speech
    analysis_time: datetime
    bias_expiry: datetime
    
    # Raw sentiment data
    hawkish_count: int
    dovish_count: int
    
    def is_active(self) -> bool:
        """Check if bias is still active"""
        return datetime.utcnow() < self.bias_expiry
    
    def hours_remaining(self) -> float:
        """Hours until bias expires"""
        delta = self.bias_expiry - datetime.utcnow()
        return max(0, delta.total_seconds() / 3600)
    
    def to_dict(self) -> Dict:
        return {
            'bank': self.bank,
            'currency': self.currency,
            'direction': self.direction.name,
            'strength': self.strength.name,
            'sentiment_score': self.sentiment_score,
            'confidence': self.confidence,
            'statement_title': self.statement_title,
            'statement_type': self.statement_type,
            'analysis_time': self.analysis_time.isoformat(),
            'bias_expiry': self.bias_expiry.isoformat(),
            'hawkish_count': self.hawkish_count,
            'dovish_count': self.dovish_count,
        }


class CentralBankAnalyzer:
    """
    Analyzes central bank communications for trading biases.
    
    Sources:
    - Rate decisions
    - Meeting minutes
    - Policy statements
    - Governor speeches
    
    Uses TextBlob + VADER + keyword matching for sentiment.
    """
    
    # Statement type weights (some are more market-moving)
    STATEMENT_WEIGHTS = {
        'rate_decision': 1.5,
        'press_conference': 1.3,
        'minutes': 1.2,
        'speech': 1.0,
        'report': 0.8,
        'other': 0.5,
    }
    
    def __init__(self):
        """Initialize analyzer"""
        self.feeds = CentralBankFeeds()
        self.sentiment = SentimentEngine()
        
        # Active biases by currency
        self.active_biases: Dict[str, CentralBankBias] = {}
    
    def analyze_recent_statements(
        self,
        hours_back: int = 48
    ) -> Dict[str, CentralBankBias]:
        """
        Analyze recent statements from all central banks.
        
        Args:
            hours_back: How far back to look
            
        Returns:
            Dict mapping currency to bias
        """
        all_statements = self.feeds.get_all_recent(hours_back)
        
        for bank, statements in all_statements.items():
            if statements:
                bias = self._analyze_statements(bank, statements)
                if bias and bias.confidence > 0.3:
                    self.active_biases[bias.currency] = bias
        
        return self.active_biases
    
    def analyze_bank(self, bank: str, hours_back: int = 48) -> Optional[CentralBankBias]:
        """
        Analyze statements from a specific central bank.
        
        Args:
            bank: Bank code (FED, ECB, BOE, BOJ, etc.)
            hours_back: How far back to look
            
        Returns:
            CentralBankBias or None
        """
        statements = self.feeds.get_recent_statements(bank, hours_back)
        
        if not statements:
            return None
        
        bias = self._analyze_statements(bank, statements)
        
        if bias and bias.confidence > 0.3:
            self.active_biases[bias.currency] = bias
            return bias
        
        return None
    
    def get_bias_for_currency(self, currency: str) -> Optional[CentralBankBias]:
        """Get current central bank bias for a currency"""
        currency = currency.upper()
        
        bias = self.active_biases.get(currency)
        
        if bias and bias.is_active():
            return bias
        
        return None
    
    def get_bias_for_pair(self, pair: str) -> Tuple[BiasDirection, float]:
        """
        Get combined central bank bias for a currency pair.
        
        Args:
            pair: Currency pair (e.g., 'EURUSD')
            
        Returns:
            (direction, confidence_adjustment)
        """
        pair_clean = pair.replace('.sim', '').upper()
        
        if len(pair_clean) != 6:
            return BiasDirection.NEUTRAL, 0.0
        
        base_currency = pair_clean[:3]
        quote_currency = pair_clean[3:]
        
        base_bias = self.get_bias_for_currency(base_currency)
        quote_bias = self.get_bias_for_currency(quote_currency)
        
        # Combine biases
        if base_bias and quote_bias:
            # Both have biases - net effect
            base_score = base_bias.sentiment_score * base_bias.confidence
            quote_score = quote_bias.sentiment_score * quote_bias.confidence
            
            # Base bullish = pair up, Quote bullish = pair down
            net_score = base_score - quote_score
            
            if net_score > 0.1:
                direction = BiasDirection.BULLISH
            elif net_score < -0.1:
                direction = BiasDirection.BEARISH
            else:
                direction = BiasDirection.NEUTRAL
            
            conf_adj = abs(net_score) * 0.1  # Max 10% adjustment
            
        elif base_bias:
            direction = base_bias.direction
            conf_adj = base_bias.confidence * 0.05
            
        elif quote_bias:
            # Invert quote bias for pair
            if quote_bias.direction == BiasDirection.BULLISH:
                direction = BiasDirection.BEARISH
            elif quote_bias.direction == BiasDirection.BEARISH:
                direction = BiasDirection.BULLISH
            else:
                direction = BiasDirection.NEUTRAL
            conf_adj = quote_bias.confidence * 0.05
            
        else:
            return BiasDirection.NEUTRAL, 0.0
        
        # Sign the adjustment
        if direction == BiasDirection.BEARISH:
            conf_adj = -conf_adj
        
        return direction, conf_adj
    
    def _analyze_statements(
        self,
        bank: str,
        statements: List[CentralBankStatement]
    ) -> Optional[CentralBankBias]:
        """
        Analyze multiple statements and produce aggregate bias.
        
        Weights by statement type and recency.
        """
        if not statements:
            return None
        
        currency = statements[0].currency
        
        # Analyze each statement
        weighted_scores = []
        total_weight = 0
        total_hawkish = 0
        total_dovish = 0
        
        most_important_statement = None
        highest_weight = 0
        
        for statement in statements:
            # Get type weight
            type_weight = self.STATEMENT_WEIGHTS.get(
                statement.statement_type, 
                self.STATEMENT_WEIGHTS['other']
            )
            
            # Recency weight (more recent = higher weight)
            hours_ago = (datetime.utcnow() - statement.published).total_seconds() / 3600
            recency_weight = max(0.5, 1.0 - hours_ago / 48)
            
            total_weight_for_statement = type_weight * recency_weight
            
            # Analyze sentiment
            text = statement.summary
            
            # Try to get full text for important statements
            if statement.statement_type in ['rate_decision', 'minutes']:
                full_text = self.feeds.fetch_full_statement(statement)
                if full_text:
                    text = full_text
            
            sentiment_result = self.sentiment.analyze(text, context='monetary')
            
            # Accumulate
            weighted_scores.append(
                (sentiment_result.composite_score, total_weight_for_statement)
            )
            total_weight += total_weight_for_statement
            total_hawkish += sentiment_result.hawkish_count
            total_dovish += sentiment_result.dovish_count
            
            # Track most important
            if total_weight_for_statement > highest_weight:
                highest_weight = total_weight_for_statement
                most_important_statement = statement
        
        if total_weight == 0 or most_important_statement is None:
            return None
        
        # Calculate weighted average sentiment
        avg_score = sum(s * w for s, w in weighted_scores) / total_weight
        
        # Determine direction and strength
        if avg_score > 0.3:
            direction = BiasDirection.BULLISH
            if avg_score > 0.6:
                strength = BiasStrength.STRONG
            elif avg_score > 0.4:
                strength = BiasStrength.MEDIUM
            else:
                strength = BiasStrength.WEAK
        elif avg_score < -0.3:
            direction = BiasDirection.BEARISH
            if avg_score < -0.6:
                strength = BiasStrength.STRONG
            elif avg_score < -0.4:
                strength = BiasStrength.MEDIUM
            else:
                strength = BiasStrength.WEAK
        else:
            direction = BiasDirection.NEUTRAL
            strength = BiasStrength.WEAK
        
        # Calculate confidence
        # Higher if: more hawkish/dovish keywords, higher agreement between statements
        keyword_signal = abs(total_hawkish - total_dovish) / max(1, total_hawkish + total_dovish)
        confidence = min(1.0, keyword_signal + abs(avg_score))
        
        # Duration based on statement type
        if most_important_statement.statement_type in ['rate_decision', 'minutes']:
            duration_hours = 8.0  # Longer for official policy
        elif most_important_statement.statement_type == 'speech':
            duration_hours = 6.0
        else:
            duration_hours = 4.0
        
        return CentralBankBias(
            bank=bank,
            currency=currency,
            direction=direction,
            strength=strength,
            sentiment_score=round(avg_score, 3),
            confidence=round(confidence, 3),
            statement_title=most_important_statement.title,
            statement_type=most_important_statement.statement_type,
            analysis_time=datetime.utcnow(),
            bias_expiry=datetime.utcnow() + timedelta(hours=duration_hours),
            hawkish_count=total_hawkish,
            dovish_count=total_dovish
        )
    
    def get_summary(self) -> str:
        """Get human-readable summary of active biases"""
        lines = ["=== Central Bank Sentiment Summary ==="]
        
        active = [b for b in self.active_biases.values() if b.is_active()]
        
        if not active:
            lines.append("No active central bank biases")
        else:
            for bias in active:
                lines.append(
                    f"{bias.bank} ({bias.currency}): {bias.direction.name} "
                    f"[{bias.strength.name}] - {bias.hours_remaining():.1f}h remaining"
                )
                lines.append(f"  Score: {bias.sentiment_score:.2f}, Conf: {bias.confidence:.2f}")
                lines.append(f"  Source: {bias.statement_title[:50]}...")
        
        return "\n".join(lines)
    
    def cleanup_expired(self):
        """Remove expired biases"""
        expired = [
            currency for currency, bias in self.active_biases.items()
            if not bias.is_active()
        ]
        
        for currency in expired:
            del self.active_biases[currency]

```

---

## `news_analysis/data_release_analyzer.py`

```py
"""
Economic Data Release Analyzer
===============================

Analyzes economic data releases (actual vs forecast) to generate
trading biases based on surprise magnitude.

Author: AI Trading System
Version: 1.0
Date: 2025-11-29
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
import statistics

from .config import (
    BiasDirection, BiasStrength, SURPRISE, TIMING,
    CURRENCY_MAPPING, QUOTE_CURRENCY, FRED_SERIES
)
from .data_sources.forexfactory import EconomicEvent
from .data_sources.fred_api import FREDClient, EconomicDataPoint


@dataclass
class DataSurprise:
    """Analysis of an economic data surprise"""
    
    event_name: str
    currency: str
    actual: float
    forecast: float
    previous: float
    surprise: float           # Actual - Forecast
    surprise_std: float       # Surprise in standard deviations
    strength: BiasStrength
    direction: BiasDirection  # Bullish/Bearish for the currency
    
    # Timing
    release_time: datetime
    bias_expiry: datetime
    
    def is_active(self) -> bool:
        """Check if bias from this surprise is still active"""
        return datetime.utcnow() < self.bias_expiry
    
    def hours_remaining(self) -> float:
        """Hours until bias expires"""
        delta = self.bias_expiry - datetime.utcnow()
        return max(0, delta.total_seconds() / 3600)
    
    def to_dict(self) -> Dict:
        return {
            'event_name': self.event_name,
            'currency': self.currency,
            'actual': self.actual,
            'forecast': self.forecast,
            'previous': self.previous,
            'surprise': self.surprise,
            'surprise_std': self.surprise_std,
            'strength': self.strength.name,
            'direction': self.direction.name,
            'release_time': self.release_time.isoformat(),
            'bias_expiry': self.bias_expiry.isoformat(),
            'is_active': self.is_active(),
        }


class DataReleaseAnalyzer:
    """
    Analyzes economic data releases and generates biases.
    
    Option C Implementation:
    - Weak surprise (< 1.5σ): 4 hour bias, ±5% confidence adjustment
    - Medium surprise (1.5-2.5σ): 6 hour bias, ±10% confidence adjustment
    - Strong surprise (> 2.5σ): 8 hour bias, block counter-trend trades
    """
    
    # Historical volatility estimates for common indicators
    # (Used when historical data not available)
    DEFAULT_STDEVS = {
        'NFP': 75000,           # Non-farm payrolls typical surprise
        'Nonfarm Payrolls': 75000,
        'Non-Farm Payrolls': 75000,
        'Unemployment Rate': 0.2,
        'CPI': 0.1,             # CPI month-over-month
        'Core CPI': 0.1,
        'GDP': 0.3,             # GDP quarter-over-quarter
        'Retail Sales': 0.3,
        'ISM Manufacturing': 1.5,
        'ISM Services': 1.5,
        'Interest Rate': 0.25,
    }
    
    def __init__(self, fred_api_key: str = None):
        """
        Initialize analyzer.
        
        Args:
            fred_api_key: Optional FRED API key for historical data
        """
        self.fred = FREDClient(api_key=fred_api_key) if fred_api_key else None
        
        # Track active surprises
        self.active_surprises: Dict[str, DataSurprise] = {}
        
        # Historical surprise data for std dev calculation
        self._historical_surprises: Dict[str, List[float]] = {}
    
    def analyze_release(
        self,
        event: EconomicEvent,
        historical_std: float = None
    ) -> Optional[DataSurprise]:
        """
        Analyze an economic release and generate bias.
        
        Args:
            event: Economic event with actual value released
            historical_std: Optional historical standard deviation
            
        Returns:
            DataSurprise with bias info, or None if no significant surprise
        """
        # Must have actual and forecast
        if event.actual is None or event.forecast is None:
            return None
        
        # Calculate raw surprise
        surprise = event.actual - event.forecast
        
        # Get standard deviation for this indicator
        std_dev = historical_std or self._get_historical_std(event)
        
        if std_dev == 0:
            return None
        
        # Calculate surprise in standard deviations
        surprise_std = abs(surprise / std_dev)
        
        # Determine strength
        if surprise_std < SURPRISE.weak_max:
            strength = BiasStrength.WEAK
            duration_hours = TIMING.bias_duration_weak
        elif surprise_std < SURPRISE.medium_max:
            strength = BiasStrength.MEDIUM
            duration_hours = TIMING.bias_duration_medium
        else:
            strength = BiasStrength.STRONG
            duration_hours = TIMING.bias_duration_strong
        
        # Determine direction
        direction = self._determine_direction(event, surprise)
        
        # Create surprise object
        release_time = event.datetime_utc
        bias_expiry = release_time + timedelta(hours=duration_hours)
        
        data_surprise = DataSurprise(
            event_name=event.event_name,
            currency=event.currency,
            actual=event.actual,
            forecast=event.forecast,
            previous=event.previous or 0,
            surprise=surprise,
            surprise_std=round(surprise_std, 2),
            strength=strength,
            direction=direction,
            release_time=release_time,
            bias_expiry=bias_expiry
        )
        
        # Store active surprise
        key = f"{event.currency}_{event.event_name}"
        self.active_surprises[key] = data_surprise
        
        # Update historical data
        self._update_historical(event.event_name, surprise)
        
        return data_surprise
    
    def get_bias_for_pair(self, pair: str) -> Tuple[BiasDirection, BiasStrength, float]:
        """
        Get current bias for a currency pair based on active surprises.
        
        Args:
            pair: Currency pair (e.g., 'EURUSD' or 'EURUSD.sim')
            
        Returns:
            (direction, strength, confidence_adjustment)
            confidence_adjustment: Positive = boost aligned trades, negative = reduce
        """
        pair_clean = pair.replace('.sim', '').upper()
        
        # Get currencies in this pair
        if len(pair_clean) != 6:
            return BiasDirection.NEUTRAL, BiasStrength.WEAK, 0.0
        
        base_currency = pair_clean[:3]
        quote_currency = pair_clean[3:]
        
        # Find active surprises for these currencies
        base_bias = self._get_currency_bias(base_currency)
        quote_bias = self._get_currency_bias(quote_currency)
        
        # Combine biases
        # Base currency bullish = pair bullish
        # Quote currency bullish = pair bearish
        
        if base_bias and quote_bias:
            # Both have active biases - use stronger one
            if base_bias[1].value >= quote_bias[1].value:
                direction = base_bias[0]
                strength = base_bias[1]
            else:
                # Invert quote bias for pair
                direction = BiasDirection.BEARISH if quote_bias[0] == BiasDirection.BULLISH else BiasDirection.BULLISH
                strength = quote_bias[1]
        elif base_bias:
            direction = base_bias[0]
            strength = base_bias[1]
        elif quote_bias:
            # Invert for pair direction
            direction = BiasDirection.BEARISH if quote_bias[0] == BiasDirection.BULLISH else BiasDirection.BULLISH
            strength = quote_bias[1]
        else:
            return BiasDirection.NEUTRAL, BiasStrength.WEAK, 0.0
        
        # Calculate confidence adjustment
        if strength == BiasStrength.WEAK:
            conf_adj = TIMING.confidence_adj_weak
        elif strength == BiasStrength.MEDIUM:
            conf_adj = TIMING.confidence_adj_medium
        else:
            conf_adj = 0.0  # Strong = blocking, not adjustment
        
        # Make adjustment signed based on direction
        if direction == BiasDirection.BEARISH:
            conf_adj = -conf_adj
        
        return direction, strength, conf_adj
    
    def should_block_trade(self, pair: str, trade_direction: str) -> Tuple[bool, str]:
        """
        Check if a trade should be blocked due to strong contrary bias.
        
        Args:
            pair: Currency pair
            trade_direction: 'BUY' or 'SELL'
            
        Returns:
            (should_block, reason)
        """
        direction, strength, _ = self.get_bias_for_pair(pair)
        
        if strength != BiasStrength.STRONG:
            return False, ""
        
        # Strong bias - check if trade is counter-trend
        trade_is_bullish = trade_direction.upper() == 'BUY'
        bias_is_bullish = direction == BiasDirection.BULLISH
        
        if trade_is_bullish != bias_is_bullish:
            # Counter-trend trade - block it
            reason = f"Strong {direction.name} bias active for {pair}"
            return True, reason
        
        return False, ""
    
    def get_active_surprises(self) -> List[DataSurprise]:
        """Get all currently active surprises"""
        # Clean up expired
        self._cleanup_expired()
        
        return [s for s in self.active_surprises.values() if s.is_active()]
    
    def _get_currency_bias(
        self, 
        currency: str
    ) -> Optional[Tuple[BiasDirection, BiasStrength]]:
        """Get current bias for a single currency"""
        currency = currency.upper()
        
        # Find most recent active surprise for this currency
        relevant = [
            s for s in self.active_surprises.values()
            if s.currency == currency and s.is_active()
        ]
        
        if not relevant:
            return None
        
        # Use most recent
        latest = max(relevant, key=lambda s: s.release_time)
        return (latest.direction, latest.strength)
    
    def _determine_direction(
        self, 
        event: EconomicEvent, 
        surprise: float
    ) -> BiasDirection:
        """
        Determine if surprise is bullish or bearish for the currency.
        
        Most indicators: higher = bullish (GDP, employment, retail sales)
        Some indicators: higher = bearish (unemployment rate, jobless claims)
        """
        # Check FRED series for direction mapping
        for series_id, info in FRED_SERIES.items():
            if info['name'].lower() in event.event_name.lower():
                higher_is_bullish = info.get('higher_is_bullish', True)
                break
        else:
            # Default: higher is bullish
            higher_is_bullish = self._is_higher_bullish(event.event_name)
        
        # Determine direction
        if surprise > 0:
            return BiasDirection.BULLISH if higher_is_bullish else BiasDirection.BEARISH
        elif surprise < 0:
            return BiasDirection.BEARISH if higher_is_bullish else BiasDirection.BULLISH
        else:
            return BiasDirection.NEUTRAL
    
    def _is_higher_bullish(self, event_name: str) -> bool:
        """Determine if higher values are bullish for an indicator"""
        event_lower = event_name.lower()
        
        # Indicators where higher = bearish
        bearish_if_higher = [
            'unemployment', 'jobless', 'claims',
            'deficit', 'debt',
        ]
        
        for term in bearish_if_higher:
            if term in event_lower:
                return False
        
        return True
    
    def _get_historical_std(self, event: EconomicEvent) -> float:
        """Get historical standard deviation for surprise calculation"""
        event_name = event.event_name
        
        # Check our historical data first
        if event_name in self._historical_surprises:
            surprises = self._historical_surprises[event_name]
            if len(surprises) >= 5:
                return statistics.stdev(surprises)
        
        # Try FRED data
        if self.fred:
            for series_id, info in FRED_SERIES.items():
                if info['name'].lower() in event_name.lower():
                    data = self.fred.get_series_data(series_id, limit=20)
                    if len(data) >= 5:
                        changes = [d.change for d in data if d.change is not None]
                        if len(changes) >= 5:
                            return statistics.stdev(changes)
                    break
        
        # Fall back to default estimates
        for key, std in self.DEFAULT_STDEVS.items():
            if key.lower() in event_name.lower():
                return std
        
        # Last resort: use 1% of forecast as rough estimate
        if event.forecast and event.forecast != 0:
            return abs(event.forecast * 0.01)
        
        return 1.0  # Avoid division by zero
    
    def _update_historical(self, event_name: str, surprise: float):
        """Update historical surprise data"""
        if event_name not in self._historical_surprises:
            self._historical_surprises[event_name] = []
        
        self._historical_surprises[event_name].append(surprise)
        
        # Keep only last 20 surprises
        if len(self._historical_surprises[event_name]) > 20:
            self._historical_surprises[event_name] = \
                self._historical_surprises[event_name][-20:]
    
    def _cleanup_expired(self):
        """Remove expired surprises"""
        expired_keys = [
            key for key, surprise in self.active_surprises.items()
            if not surprise.is_active()
        ]
        
        for key in expired_keys:
            del self.active_surprises[key]

```

---

## `news_analysis/government_analyzer.py`

```py
"""
Government/Fiscal Policy Analyzer
==================================

Analyzes government fiscal policy, Treasury operations, and political
developments that impact currency markets.

Author: AI Trading System
Version: 1.0
Date: 2025-11-29
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from bs4 import BeautifulSoup
import re

from .config import (
    BiasDirection, BiasStrength, TIMING,
    FISCAL_BULLISH_KEYWORDS, FISCAL_BEARISH_KEYWORDS
)
from .sentiment_engine import SentimentEngine, SentimentResult


@dataclass
class FiscalBias:
    """Bias derived from fiscal/government analysis"""
    
    currency: str
    direction: BiasDirection
    strength: BiasStrength
    sentiment_score: float
    confidence: float
    
    # Source info
    headline: str
    source: str
    analysis_time: datetime
    bias_expiry: datetime
    
    # Keywords found
    bullish_keywords: int
    bearish_keywords: int
    
    def is_active(self) -> bool:
        return datetime.utcnow() < self.bias_expiry
    
    def hours_remaining(self) -> float:
        delta = self.bias_expiry - datetime.utcnow()
        return max(0, delta.total_seconds() / 3600)
    
    def to_dict(self) -> Dict:
        return {
            'currency': self.currency,
            'direction': self.direction.name,
            'strength': self.strength.name,
            'sentiment_score': self.sentiment_score,
            'confidence': self.confidence,
            'headline': self.headline,
            'source': self.source,
            'analysis_time': self.analysis_time.isoformat(),
            'bias_expiry': self.bias_expiry.isoformat(),
        }


@dataclass
class TreasuryAuction:
    """Treasury auction data"""
    
    security_type: str      # 2Y, 5Y, 10Y, 30Y
    auction_date: datetime
    amount: float           # Billion USD
    yield_result: Optional[float]
    bid_to_cover: Optional[float]
    indirect_pct: Optional[float]  # Foreign demand proxy
    
    def is_strong_demand(self) -> bool:
        """Check if auction showed strong demand"""
        if self.bid_to_cover is None:
            return False
        
        # Thresholds vary by security type
        thresholds = {
            '2Y': 2.5,
            '5Y': 2.4,
            '10Y': 2.3,
            '30Y': 2.2,
        }
        
        threshold = thresholds.get(self.security_type, 2.3)
        return self.bid_to_cover >= threshold


class GovernmentAnalyzer:
    """
    Analyzes fiscal policy and government news for trading biases.
    
    Covers:
    - Debt ceiling / government shutdown news
    - Treasury auctions
    - Fiscal stimulus / austerity announcements
    - Credit rating changes
    - Political gridlock / policy uncertainty
    
    Primarily affects USD but methodology extends to other currencies.
    """
    
    # News sources for fiscal policy
    NEWS_SOURCES = {
        'USD': [
            'https://www.reuters.com/markets/us/',
            'https://www.bloomberg.com/markets/economics',
        ],
        'EUR': [
            'https://www.reuters.com/markets/europe/',
        ],
        'GBP': [
            'https://www.reuters.com/world/uk/',
        ],
    }
    
    # High-impact fiscal events
    FISCAL_EVENTS = {
        'debt_ceiling': {'impact': 'high', 'duration_hours': 8},
        'government_shutdown': {'impact': 'high', 'duration_hours': 8},
        'credit_downgrade': {'impact': 'critical', 'duration_hours': 12},
        'stimulus': {'impact': 'medium', 'duration_hours': 6},
        'budget': {'impact': 'medium', 'duration_hours': 6},
        'tax': {'impact': 'medium', 'duration_hours': 6},
    }
    
    def __init__(self):
        """Initialize analyzer"""
        self.sentiment = SentimentEngine()
        
        # Active biases
        self.active_biases: Dict[str, FiscalBias] = {}
        
        # Treasury auction tracking
        self.recent_auctions: List[TreasuryAuction] = []
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
    
    def analyze_fiscal_news(
        self,
        currency: str = 'USD',
        headlines: List[str] = None
    ) -> Optional[FiscalBias]:
        """
        Analyze fiscal/government news for a currency.
        
        Args:
            currency: Currency to analyze (USD, EUR, GBP, etc.)
            headlines: Optional pre-fetched headlines to analyze
            
        Returns:
            FiscalBias or None if no significant signal
        """
        currency = currency.upper()
        
        # Get headlines if not provided
        if headlines is None:
            headlines = self._fetch_fiscal_headlines(currency)
        
        if not headlines:
            return None
        
        # Analyze each headline
        results = []
        bullish_total = 0
        bearish_total = 0
        most_impactful = None
        highest_impact = 0
        
        for headline in headlines:
            sentiment = self.sentiment.analyze(headline, context='fiscal')
            
            # Count fiscal keywords
            bullish = self._count_keywords(headline, FISCAL_BULLISH_KEYWORDS)
            bearish = self._count_keywords(headline, FISCAL_BEARISH_KEYWORDS)
            
            bullish_total += bullish
            bearish_total += bearish
            
            # Check for high-impact events
            impact_score = self._get_event_impact(headline)
            if impact_score > highest_impact:
                highest_impact = impact_score
                most_impactful = headline
            
            results.append(sentiment)
        
        if not results:
            return None
        
        # Aggregate sentiment
        aggregate = self.sentiment.get_dominant_sentiment(results)
        
        # Determine direction
        if bullish_total > bearish_total * 1.5:
            direction = BiasDirection.BULLISH
        elif bearish_total > bullish_total * 1.5:
            direction = BiasDirection.BEARISH
        else:
            direction = BiasDirection.NEUTRAL
        
        # Override with aggregate score if strong
        if aggregate.composite_score > 0.4:
            direction = BiasDirection.BULLISH
        elif aggregate.composite_score < -0.4:
            direction = BiasDirection.BEARISH
        
        # Determine strength
        keyword_imbalance = abs(bullish_total - bearish_total)
        if keyword_imbalance > 5 or abs(aggregate.composite_score) > 0.6:
            strength = BiasStrength.STRONG
        elif keyword_imbalance > 2 or abs(aggregate.composite_score) > 0.4:
            strength = BiasStrength.MEDIUM
        else:
            strength = BiasStrength.WEAK
        
        # Calculate confidence
        confidence = min(1.0, aggregate.confidence + keyword_imbalance * 0.1)
        
        # Only create bias if significant
        if direction == BiasDirection.NEUTRAL and confidence < 0.5:
            return None
        
        # Duration based on event impact
        duration = self._get_duration(most_impactful or headlines[0])
        
        bias = FiscalBias(
            currency=currency,
            direction=direction,
            strength=strength,
            sentiment_score=aggregate.composite_score,
            confidence=round(confidence, 3),
            headline=most_impactful or headlines[0],
            source='fiscal_analysis',
            analysis_time=datetime.utcnow(),
            bias_expiry=datetime.utcnow() + timedelta(hours=duration),
            bullish_keywords=bullish_total,
            bearish_keywords=bearish_total
        )
        
        # Store active bias
        if confidence > 0.3:
            self.active_biases[currency] = bias
        
        return bias
    
    def analyze_treasury_auction(
        self,
        auction: TreasuryAuction
    ) -> Optional[FiscalBias]:
        """
        Analyze Treasury auction results for USD bias.
        
        Strong demand (high bid-to-cover, foreign demand) = USD bullish
        Weak demand = USD bearish
        """
        self.recent_auctions.append(auction)
        
        # Keep only last 10 auctions
        self.recent_auctions = self.recent_auctions[-10:]
        
        # Analyze this auction
        if auction.bid_to_cover is None:
            return None
        
        is_strong = auction.is_strong_demand()
        
        # Check indirect (foreign) demand
        foreign_strong = False
        if auction.indirect_pct is not None:
            # Typical indirect is 60-70%, above 70% is strong
            foreign_strong = auction.indirect_pct > 70
        
        # Determine direction
        if is_strong and foreign_strong:
            direction = BiasDirection.BULLISH
            strength = BiasStrength.MEDIUM
        elif is_strong or foreign_strong:
            direction = BiasDirection.BULLISH
            strength = BiasStrength.WEAK
        elif auction.bid_to_cover < 2.0:
            direction = BiasDirection.BEARISH
            strength = BiasStrength.WEAK
        else:
            return None  # Neutral auction
        
        headline = f"{auction.security_type} Treasury auction: B/C {auction.bid_to_cover:.2f}"
        
        bias = FiscalBias(
            currency='USD',
            direction=direction,
            strength=strength,
            sentiment_score=0.3 if direction == BiasDirection.BULLISH else -0.3,
            confidence=0.5,
            headline=headline,
            source='treasury_auction',
            analysis_time=datetime.utcnow(),
            bias_expiry=datetime.utcnow() + timedelta(hours=4),
            bullish_keywords=1 if is_strong else 0,
            bearish_keywords=0 if is_strong else 1
        )
        
        return bias
    
    def get_bias_for_currency(self, currency: str) -> Optional[FiscalBias]:
        """Get current fiscal bias for a currency"""
        currency = currency.upper()
        bias = self.active_biases.get(currency)
        
        if bias and bias.is_active():
            return bias
        
        return None
    
    def get_bias_for_pair(self, pair: str) -> Tuple[BiasDirection, float]:
        """
        Get fiscal bias impact on a currency pair.
        
        Args:
            pair: Currency pair (e.g., 'EURUSD')
            
        Returns:
            (direction, confidence_adjustment)
        """
        pair_clean = pair.replace('.sim', '').upper()
        
        if len(pair_clean) != 6:
            return BiasDirection.NEUTRAL, 0.0
        
        base = pair_clean[:3]
        quote = pair_clean[3:]
        
        base_bias = self.get_bias_for_currency(base)
        quote_bias = self.get_bias_for_currency(quote)
        
        # Combine biases
        if base_bias and quote_bias:
            net = base_bias.sentiment_score - quote_bias.sentiment_score
            if net > 0.2:
                direction = BiasDirection.BULLISH
            elif net < -0.2:
                direction = BiasDirection.BEARISH
            else:
                direction = BiasDirection.NEUTRAL
            conf_adj = abs(net) * 0.05
        elif base_bias:
            direction = base_bias.direction
            conf_adj = base_bias.confidence * 0.03
        elif quote_bias:
            # Invert for pair
            if quote_bias.direction == BiasDirection.BULLISH:
                direction = BiasDirection.BEARISH
            elif quote_bias.direction == BiasDirection.BEARISH:
                direction = BiasDirection.BULLISH
            else:
                direction = BiasDirection.NEUTRAL
            conf_adj = quote_bias.confidence * 0.03
        else:
            return BiasDirection.NEUTRAL, 0.0
        
        if direction == BiasDirection.BEARISH:
            conf_adj = -conf_adj
        
        return direction, conf_adj
    
    def _fetch_fiscal_headlines(self, currency: str) -> List[str]:
        """Fetch recent fiscal headlines for a currency"""
        # This is a placeholder - in production, would scrape news sources
        # For now, return empty list (headlines would be provided externally)
        return []
    
    def _count_keywords(self, text: str, keywords: set) -> int:
        """Count keyword occurrences in text"""
        text_lower = text.lower()
        count = 0
        for keyword in keywords:
            if keyword.lower() in text_lower:
                count += 1
        return count
    
    def _get_event_impact(self, headline: str) -> float:
        """Get impact score for fiscal event"""
        headline_lower = headline.lower()
        
        for event, info in self.FISCAL_EVENTS.items():
            if event in headline_lower:
                if info['impact'] == 'critical':
                    return 1.0
                elif info['impact'] == 'high':
                    return 0.7
                elif info['impact'] == 'medium':
                    return 0.5
        
        return 0.3  # Default low impact
    
    def _get_duration(self, headline: str) -> float:
        """Get bias duration based on event type"""
        headline_lower = headline.lower()
        
        for event, info in self.FISCAL_EVENTS.items():
            if event in headline_lower:
                return info['duration_hours']
        
        return 4.0  # Default 4 hours
    
    def get_summary(self) -> str:
        """Get human-readable summary"""
        lines = ["=== Fiscal Policy Analysis ==="]
        
        active = [b for b in self.active_biases.values() if b.is_active()]
        
        if not active:
            lines.append("No active fiscal biases")
        else:
            for bias in active:
                lines.append(
                    f"{bias.currency}: {bias.direction.name} [{bias.strength.name}]"
                )
                lines.append(f"  {bias.headline[:60]}...")
                lines.append(f"  Expires in {bias.hours_remaining():.1f}h")
        
        if self.recent_auctions:
            lines.append("\n--- Recent Treasury Auctions ---")
            for auction in self.recent_auctions[-3:]:
                lines.append(
                    f"  {auction.security_type}: B/C {auction.bid_to_cover or 'N/A'}"
                )
        
        return "\n".join(lines)
    
    def cleanup_expired(self):
        """Remove expired biases"""
        expired = [
            currency for currency, bias in self.active_biases.items()
            if not bias.is_active()
        ]
        for currency in expired:
            del self.active_biases[currency]

```

---

## `news_analysis/data_sources/__init__.py`

```py
"""
News Analysis Data Sources
===========================

Data source modules for economic calendar, FRED API, and central bank feeds.

Author: AI Trading System
Version: 1.0
Date: 2025-11-29
"""

from .forexfactory import ForexFactoryScraper, EconomicEvent
from .fred_api import FREDClient, EconomicDataPoint
from .central_bank_feeds import CentralBankFeeds, CentralBankStatement

__all__ = [
    'ForexFactoryScraper',
    'EconomicEvent',
    'FREDClient',
    'EconomicDataPoint',
    'CentralBankFeeds',
    'CentralBankStatement',
]

```

---

## `news_analysis/data_sources/forexfactory.py`

```py
"""
ForexFactory Calendar Scraper
==============================

Scrapes economic calendar data from ForexFactory.com
for event scheduling, blocking, and surprise detection.

Author: AI Trading System
Version: 1.0
Date: 2025-11-29
"""

import re
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
from bs4 import BeautifulSoup
import time

from ..config import ImpactLevel, HIGH_IMPACT_EVENTS


@dataclass
class EconomicEvent:
    """Container for a single economic event"""
    
    datetime_utc: datetime
    currency: str
    event_name: str
    impact: ImpactLevel
    forecast: Optional[float]
    previous: Optional[float]
    actual: Optional[float]
    
    # Calculated fields
    surprise: Optional[float] = None      # Actual - Forecast
    surprise_pct: Optional[float] = None  # (Actual - Forecast) / |Forecast| * 100
    
    def has_released(self) -> bool:
        """Check if actual value has been released"""
        return self.actual is not None
    
    def is_upcoming(self, hours_ahead: int = 24) -> bool:
        """Check if event is within next N hours"""
        now = datetime.utcnow()
        return now <= self.datetime_utc <= now + timedelta(hours=hours_ahead)
    
    def minutes_until(self) -> float:
        """Minutes until event (negative if passed)"""
        delta = self.datetime_utc - datetime.utcnow()
        return delta.total_seconds() / 60
    
    def to_dict(self) -> Dict:
        return {
            'datetime_utc': self.datetime_utc.isoformat(),
            'currency': self.currency,
            'event_name': self.event_name,
            'impact': self.impact.name,
            'forecast': self.forecast,
            'previous': self.previous,
            'actual': self.actual,
            'surprise': self.surprise,
            'surprise_pct': self.surprise_pct,
        }


class ForexFactoryScraper:
    """
    Scrapes economic calendar from ForexFactory.
    
    Features:
    - Gets upcoming events for next 24-48 hours
    - Parses impact levels (low/medium/high)
    - Extracts forecast/previous/actual values
    - Calculates surprises when actual releases
    """
    
    BASE_URL = "https://www.forexfactory.com/calendar"
    
    def __init__(self, cache_minutes: int = 5):
        """
        Initialize scraper.
        
        Args:
            cache_minutes: How long to cache results
        """
        self.cache_minutes = cache_minutes
        self._cache: List[EconomicEvent] = []
        self._cache_time: Optional[datetime] = None
        
        # Request headers to avoid blocking
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    
    def get_events(
        self, 
        hours_ahead: int = 48,
        currencies: Optional[List[str]] = None,
        min_impact: ImpactLevel = ImpactLevel.MEDIUM,
        force_refresh: bool = False
    ) -> List[EconomicEvent]:
        """
        Get upcoming economic events.
        
        Args:
            hours_ahead: How far ahead to look
            currencies: Filter by currency (None = all)
            min_impact: Minimum impact level to include
            force_refresh: Bypass cache
            
        Returns:
            List of EconomicEvent objects
        """
        # Check cache
        if not force_refresh and self._is_cache_valid():
            events = self._cache
        else:
            events = self._scrape_calendar()
            self._cache = events
            self._cache_time = datetime.utcnow()
        
        # Filter results
        now = datetime.utcnow()
        cutoff = now + timedelta(hours=hours_ahead)
        
        filtered = []
        for event in events:
            # Time filter
            if event.datetime_utc > cutoff:
                continue
            
            # Currency filter
            if currencies and event.currency not in currencies:
                continue
            
            # Impact filter
            if event.impact.value < min_impact.value:
                continue
            
            filtered.append(event)
        
        return filtered
    
    def get_upcoming_high_impact(
        self, 
        hours_ahead: int = 24,
        currencies: Optional[List[str]] = None
    ) -> List[EconomicEvent]:
        """Get only HIGH and CRITICAL impact events"""
        return self.get_events(
            hours_ahead=hours_ahead,
            currencies=currencies,
            min_impact=ImpactLevel.HIGH
        )
    
    def get_events_for_currency(
        self, 
        currency: str,
        hours_ahead: int = 48
    ) -> List[EconomicEvent]:
        """Get events affecting a specific currency"""
        return self.get_events(
            hours_ahead=hours_ahead,
            currencies=[currency]
        )
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if self._cache_time is None:
            return False
        
        age = datetime.utcnow() - self._cache_time
        return age < timedelta(minutes=self.cache_minutes)
    
    def _scrape_calendar(self) -> List[EconomicEvent]:
        """Scrape ForexFactory calendar page"""
        events = []
        
        try:
            # Get today's calendar
            response = requests.get(
                self.BASE_URL,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            events.extend(self._parse_calendar_page(soup))
            
            # Also get tomorrow's calendar
            tomorrow = datetime.utcnow() + timedelta(days=1)
            tomorrow_url = f"{self.BASE_URL}?day={tomorrow.strftime('%b%d.%Y').lower()}"
            
            time.sleep(1)  # Rate limiting
            
            response = requests.get(
                tomorrow_url,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            events.extend(self._parse_calendar_page(soup, tomorrow.date()))
            
        except requests.RequestException as e:
            print(f"[ForexFactory] Request error: {e}")
        except Exception as e:
            print(f"[ForexFactory] Parse error: {e}")
        
        return events
    
    def _parse_calendar_page(
        self, 
        soup: BeautifulSoup,
        base_date: Optional[datetime.date] = None
    ) -> List[EconomicEvent]:
        """Parse events from calendar HTML"""
        events = []
        
        if base_date is None:
            base_date = datetime.utcnow().date()
        
        # Find calendar table
        calendar_table = soup.find('table', class_='calendar__table')
        if not calendar_table:
            return events
        
        current_date = base_date
        current_time = None
        
        # Parse rows
        rows = calendar_table.find_all('tr', class_='calendar__row')
        
        for row in rows:
            try:
                # Check for date row
                date_cell = row.find('td', class_='calendar__date')
                if date_cell and date_cell.text.strip():
                    date_text = date_cell.text.strip()
                    parsed_date = self._parse_date(date_text)
                    if parsed_date:
                        current_date = parsed_date
                
                # Get time
                time_cell = row.find('td', class_='calendar__time')
                if time_cell and time_cell.text.strip():
                    time_text = time_cell.text.strip()
                    current_time = self._parse_time(time_text)
                
                if current_time is None:
                    continue
                
                # Get currency
                currency_cell = row.find('td', class_='calendar__currency')
                if not currency_cell:
                    continue
                currency = currency_cell.text.strip().upper()
                
                # Get event name
                event_cell = row.find('td', class_='calendar__event')
                if not event_cell:
                    continue
                event_name = event_cell.text.strip()
                
                # Get impact
                impact_cell = row.find('td', class_='calendar__impact')
                impact = self._parse_impact(impact_cell)
                
                # Get values (forecast, previous, actual)
                forecast = self._parse_value(row.find('td', class_='calendar__forecast'))
                previous = self._parse_value(row.find('td', class_='calendar__previous'))
                actual = self._parse_value(row.find('td', class_='calendar__actual'))
                
                # Combine date and time
                try:
                    event_datetime = datetime.combine(current_date, current_time)
                except:
                    continue
                
                # Override impact for known high-impact events
                event_info = HIGH_IMPACT_EVENTS.get(event_name)
                if event_info:
                    impact = event_info['impact']
                
                # Calculate surprise if actual is available
                surprise = None
                surprise_pct = None
                if actual is not None and forecast is not None:
                    surprise = actual - forecast
                    if forecast != 0:
                        surprise_pct = (surprise / abs(forecast)) * 100
                
                event = EconomicEvent(
                    datetime_utc=event_datetime,
                    currency=currency,
                    event_name=event_name,
                    impact=impact,
                    forecast=forecast,
                    previous=previous,
                    actual=actual,
                    surprise=surprise,
                    surprise_pct=surprise_pct
                )
                
                events.append(event)
                
            except Exception as e:
                continue  # Skip malformed rows
        
        return events
    
    def _parse_date(self, date_text: str) -> Optional[datetime.date]:
        """Parse date from ForexFactory format"""
        try:
            # Format: "Mon Dec 2" or "Dec 2"
            date_text = date_text.replace('\n', ' ').strip()
            
            # Remove day name if present
            parts = date_text.split()
            if len(parts) >= 2:
                month_str = parts[-2]
                day_str = parts[-1]
                
                year = datetime.utcnow().year
                date_str = f"{month_str} {day_str} {year}"
                
                return datetime.strptime(date_str, "%b %d %Y").date()
        except:
            pass
        return None
    
    def _parse_time(self, time_text: str) -> Optional[datetime.time]:
        """Parse time from ForexFactory format"""
        try:
            time_text = time_text.strip().lower()
            
            # Handle "All Day" or "Tentative"
            if 'all day' in time_text or 'tentative' in time_text:
                return datetime.strptime("00:00", "%H:%M").time()
            
            # Handle "12:30pm" format
            time_text = time_text.replace('am', ' AM').replace('pm', ' PM')
            
            for fmt in ['%I:%M %p', '%H:%M']:
                try:
                    return datetime.strptime(time_text, fmt).time()
                except:
                    continue
        except:
            pass
        return None
    
    def _parse_impact(self, cell) -> ImpactLevel:
        """Parse impact level from cell class"""
        if not cell:
            return ImpactLevel.LOW
        
        # Check for impact icon classes
        span = cell.find('span')
        if span:
            classes = span.get('class', [])
            class_str = ' '.join(classes).lower()
            
            if 'high' in class_str or 'red' in class_str:
                return ImpactLevel.HIGH
            elif 'medium' in class_str or 'orange' in class_str:
                return ImpactLevel.MEDIUM
            elif 'low' in class_str or 'yellow' in class_str:
                return ImpactLevel.LOW
        
        return ImpactLevel.LOW
    
    def _parse_value(self, cell) -> Optional[float]:
        """Parse numeric value from cell"""
        if not cell:
            return None
        
        text = cell.text.strip()
        if not text or text == '-':
            return None
        
        try:
            # Remove common suffixes (K, M, B, %)
            text = text.replace(',', '').replace('%', '')
            
            multiplier = 1
            if 'K' in text.upper():
                multiplier = 1000
                text = text.upper().replace('K', '')
            elif 'M' in text.upper():
                multiplier = 1000000
                text = text.upper().replace('M', '')
            elif 'B' in text.upper():
                multiplier = 1000000000
                text = text.upper().replace('B', '')
            
            value = float(text) * multiplier
            return value
        except:
            return None


# Backup method using requests if scraping fails
def get_events_from_api_backup() -> List[Dict]:
    """
    Backup method using alternative free API.
    
    Uses FXStreet or similar free calendar API.
    """
    # Placeholder for backup implementation
    return []

```

---

## `news_analysis/data_sources/fred_api.py`

```py
"""
FRED API Integration
=====================

Fetches economic data from Federal Reserve Economic Data (FRED).
Free API with 120 requests/minute limit.

Author: AI Trading System
Version: 1.0
Date: 2025-11-29

API Key: Get free at https://fred.stlouisfed.org/docs/api/api_key.html
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import os

from ..config import FRED_SERIES


@dataclass
class EconomicDataPoint:
    """Single data release"""
    series_id: str
    series_name: str
    date: datetime
    value: float
    previous_value: Optional[float]
    change: Optional[float]
    change_pct: Optional[float]
    currency: str
    higher_is_bullish: bool
    
    def to_dict(self) -> Dict:
        return {
            'series_id': self.series_id,
            'series_name': self.series_name,
            'date': self.date.isoformat(),
            'value': self.value,
            'previous_value': self.previous_value,
            'change': self.change,
            'change_pct': self.change_pct,
            'currency': self.currency,
            'higher_is_bullish': self.higher_is_bullish,
        }


class FREDClient:
    """
    Client for FRED (Federal Reserve Economic Data) API.
    
    Provides access to US economic indicators:
    - Employment: NFP, Unemployment Rate, Jobless Claims
    - Inflation: CPI, Core CPI, PPI
    - GDP: Real GDP, Nominal GDP
    - Consumer: Retail Sales, Consumer Sentiment
    - Interest Rates: Fed Funds, Treasury Yields
    """
    
    BASE_URL = "https://api.stlouisfed.org/fred"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize FRED client.
        
        Args:
            api_key: FRED API key (or set FRED_API_KEY env variable)
        """
        self.api_key = api_key or os.environ.get('FRED_API_KEY')
        
        if not self.api_key:
            print("[WARNING] No FRED API key. Set FRED_API_KEY environment variable.")
            print("Get free key at: https://fred.stlouisfed.org/docs/api/api_key.html")
        
        # Cache for series data
        self._cache: Dict[str, List[EconomicDataPoint]] = {}
        self._cache_times: Dict[str, datetime] = {}
        self.cache_hours = 1  # Cache for 1 hour
    
    def get_latest_value(self, series_id: str) -> Optional[EconomicDataPoint]:
        """
        Get most recent value for a series.
        
        Args:
            series_id: FRED series ID (e.g., 'PAYEMS' for NFP)
            
        Returns:
            Latest EconomicDataPoint or None
        """
        data = self.get_series_data(series_id, limit=2)
        return data[0] if data else None
    
    def get_series_data(
        self,
        series_id: str,
        limit: int = 10,
        force_refresh: bool = False
    ) -> List[EconomicDataPoint]:
        """
        Get recent data for a series.
        
        Args:
            series_id: FRED series ID
            limit: Number of observations to return
            force_refresh: Bypass cache
            
        Returns:
            List of EconomicDataPoint, most recent first
        """
        # Check cache
        if not force_refresh and self._is_cache_valid(series_id):
            return self._cache[series_id][:limit]
        
        if not self.api_key:
            return []
        
        series_info = FRED_SERIES.get(series_id, {})
        series_name = series_info.get('name', series_id)
        currency = series_info.get('currency', 'USD')
        higher_is_bullish = series_info.get('higher_is_bullish', True)
        
        try:
            # Fetch from API
            params = {
                'series_id': series_id,
                'api_key': self.api_key,
                'file_type': 'json',
                'sort_order': 'desc',
                'limit': max(limit + 1, 20),  # Get extra for change calc
            }
            
            response = requests.get(
                f"{self.BASE_URL}/series/observations",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            observations = data.get('observations', [])
            
            # Parse observations
            results = []
            for i, obs in enumerate(observations):
                try:
                    date = datetime.strptime(obs['date'], '%Y-%m-%d')
                    value_str = obs['value']
                    
                    # Skip missing values
                    if value_str == '.':
                        continue
                    
                    value = float(value_str)
                    
                    # Calculate change from previous
                    previous_value = None
                    change = None
                    change_pct = None
                    
                    if i + 1 < len(observations):
                        prev_str = observations[i + 1]['value']
                        if prev_str != '.':
                            previous_value = float(prev_str)
                            change = value - previous_value
                            if previous_value != 0:
                                change_pct = (change / abs(previous_value)) * 100
                    
                    results.append(EconomicDataPoint(
                        series_id=series_id,
                        series_name=series_name,
                        date=date,
                        value=value,
                        previous_value=previous_value,
                        change=change,
                        change_pct=change_pct,
                        currency=currency,
                        higher_is_bullish=higher_is_bullish
                    ))
                    
                except (ValueError, KeyError):
                    continue
            
            # Cache results
            self._cache[series_id] = results
            self._cache_times[series_id] = datetime.utcnow()
            
            return results[:limit]
            
        except requests.RequestException as e:
            print(f"[FRED] Request error for {series_id}: {e}")
            return []
        except Exception as e:
            print(f"[FRED] Parse error for {series_id}: {e}")
            return []
    
    def get_all_latest(self) -> Dict[str, EconomicDataPoint]:
        """
        Get latest values for all tracked series.
        
        Returns:
            Dict mapping series_id to latest data point
        """
        results = {}
        
        for series_id in FRED_SERIES.keys():
            data = self.get_latest_value(series_id)
            if data:
                results[series_id] = data
        
        return results
    
    def get_employment_data(self) -> Dict[str, EconomicDataPoint]:
        """Get employment-related data"""
        employment_series = ['PAYEMS', 'UNRATE', 'ICSA']
        return {
            sid: self.get_latest_value(sid)
            for sid in employment_series
            if self.get_latest_value(sid)
        }
    
    def get_inflation_data(self) -> Dict[str, EconomicDataPoint]:
        """Get inflation-related data"""
        inflation_series = ['CPIAUCSL', 'CPILFESL', 'PPIACO']
        return {
            sid: self.get_latest_value(sid)
            for sid in inflation_series
            if self.get_latest_value(sid)
        }
    
    def get_gdp_data(self) -> Dict[str, EconomicDataPoint]:
        """Get GDP data"""
        gdp_series = ['GDP', 'GDPC1']
        return {
            sid: self.get_latest_value(sid)
            for sid in gdp_series
            if self.get_latest_value(sid)
        }
    
    def get_interest_rate_data(self) -> Dict[str, EconomicDataPoint]:
        """Get interest rate data"""
        rate_series = ['FEDFUNDS', 'DGS10', 'DGS2']
        return {
            sid: self.get_latest_value(sid)
            for sid in rate_series
            if self.get_latest_value(sid)
        }
    
    def calculate_surprise(
        self,
        series_id: str,
        actual: float,
        forecast: float
    ) -> Tuple[float, float, str]:
        """
        Calculate surprise and determine bias direction.
        
        Args:
            series_id: FRED series ID
            actual: Actual released value
            forecast: Consensus forecast
            
        Returns:
            (surprise, surprise_std, direction)
            direction: 'bullish', 'bearish', or 'neutral'
        """
        series_info = FRED_SERIES.get(series_id, {})
        higher_is_bullish = series_info.get('higher_is_bullish', True)
        
        # Raw surprise
        surprise = actual - forecast
        
        # Get historical data for std dev calculation
        historical = self.get_series_data(series_id, limit=50)
        
        if len(historical) >= 10:
            # Calculate change distribution
            changes = [
                d.change for d in historical 
                if d.change is not None
            ]
            
            if changes:
                import statistics
                std_dev = statistics.stdev(changes) if len(changes) > 1 else 1
                surprise_std = surprise / std_dev if std_dev > 0 else 0
            else:
                surprise_std = 0
        else:
            # Fallback: use percentage
            surprise_std = abs(surprise / forecast * 10) if forecast != 0 else 0
        
        # Determine direction
        if abs(surprise_std) < 0.5:
            direction = 'neutral'
        elif (surprise > 0) == higher_is_bullish:
            direction = 'bullish'
        else:
            direction = 'bearish'
        
        return surprise, surprise_std, direction
    
    def _is_cache_valid(self, series_id: str) -> bool:
        """Check if cache is valid"""
        if series_id not in self._cache_times:
            return False
        
        age = datetime.utcnow() - self._cache_times[series_id]
        return age < timedelta(hours=self.cache_hours)
    
    def get_release_schedule(self, series_id: str) -> Optional[datetime]:
        """
        Get next release date for a series.
        
        Note: FRED doesn't provide future release dates via API.
        This returns estimated next release based on typical schedule.
        """
        # Most economic data follows predictable schedules
        schedules = {
            'PAYEMS': 'monthly_first_friday',
            'UNRATE': 'monthly_first_friday',
            'ICSA': 'weekly_thursday',
            'CPIAUCSL': 'monthly_mid',
            'CPILFESL': 'monthly_mid',
            'GDP': 'quarterly',
        }
        
        schedule = schedules.get(series_id)
        if not schedule:
            return None
        
        now = datetime.utcnow()
        
        if schedule == 'monthly_first_friday':
            # Find first Friday of next month
            if now.day > 7:
                next_month = now.month + 1 if now.month < 12 else 1
                year = now.year if now.month < 12 else now.year + 1
            else:
                next_month = now.month
                year = now.year
            
            first_day = datetime(year, next_month, 1)
            # Find first Friday (weekday 4)
            days_until_friday = (4 - first_day.weekday()) % 7
            return first_day + timedelta(days=days_until_friday, hours=13, minutes=30)
        
        elif schedule == 'weekly_thursday':
            # Next Thursday 8:30 AM ET
            days_until_thursday = (3 - now.weekday()) % 7
            if days_until_thursday == 0 and now.hour >= 13:
                days_until_thursday = 7
            return (now + timedelta(days=days_until_thursday)).replace(
                hour=13, minute=30, second=0, microsecond=0
            )
        
        elif schedule == 'monthly_mid':
            # Around 10th-15th of each month
            if now.day > 15:
                next_month = now.month + 1 if now.month < 12 else 1
                year = now.year if now.month < 12 else now.year + 1
            else:
                next_month = now.month
                year = now.year
            
            return datetime(year, next_month, 12, 13, 30)
        
        return None


# Create empty __init__.py for data_sources package
def create_init_file():
    """Utility to create package init file"""
    pass

```

---

## `news_analysis/data_sources/central_bank_feeds.py`

```py
"""
Central Bank RSS Feeds
=======================

Fetches and parses news/statements from major central banks:
- Federal Reserve (Fed)
- European Central Bank (ECB)
- Bank of England (BOE)
- Bank of Japan (BOJ)
- Reserve Bank of Australia (RBA)
- Bank of Canada (BOC)
- Reserve Bank of New Zealand (RBNZ)
- Swiss National Bank (SNB)

Author: AI Trading System
Version: 1.0
Date: 2025-11-29
"""

import feedparser
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
from bs4 import BeautifulSoup
import re


@dataclass
class CentralBankStatement:
    """Container for a central bank statement/release"""
    
    bank: str                    # Fed, ECB, BOE, BOJ, etc.
    currency: str                # USD, EUR, GBP, JPY, etc.
    title: str
    summary: str
    full_text: Optional[str]
    url: str
    published: datetime
    statement_type: str          # rate_decision, minutes, speech, report
    
    def to_dict(self) -> Dict:
        return {
            'bank': self.bank,
            'currency': self.currency,
            'title': self.title,
            'summary': self.summary,
            'url': self.url,
            'published': self.published.isoformat(),
            'statement_type': self.statement_type,
        }


class CentralBankFeeds:
    """
    Fetches statements and news from central bank RSS feeds.
    
    Used for sentiment analysis on monetary policy.
    """
    
    # RSS Feed URLs (some banks don't have RSS, use alternative)
    FEEDS = {
        'FED': {
            'currency': 'USD',
            'rss': 'https://www.federalreserve.gov/feeds/press_all.xml',
            'backup_url': 'https://www.federalreserve.gov/newsevents/pressreleases.htm',
        },
        'ECB': {
            'currency': 'EUR',
            'rss': None,  # ECB doesn't have clean RSS
            'backup_url': 'https://www.ecb.europa.eu/press/pr/html/index.en.html',
        },
        'BOE': {
            'currency': 'GBP',
            'rss': None,
            'backup_url': 'https://www.bankofengland.co.uk/news',
        },
        'BOJ': {
            'currency': 'JPY',
            'rss': None,
            'backup_url': 'https://www.boj.or.jp/en/mopo/index.htm',
        },
        'RBA': {
            'currency': 'AUD',
            'rss': None,
            'backup_url': 'https://www.rba.gov.au/media-releases/',
        },
        'BOC': {
            'currency': 'CAD',
            'rss': None,
            'backup_url': 'https://www.bankofcanada.ca/press/',
        },
        'RBNZ': {
            'currency': 'NZD',
            'rss': None,
            'backup_url': 'https://www.rbnz.govt.nz/news',
        },
        'SNB': {
            'currency': 'CHF',
            'rss': None,
            'backup_url': 'https://www.snb.ch/en/mmr/reference/pre_all/source',
        },
    }
    
    # Keywords to identify statement types
    STATEMENT_TYPES = {
        'rate_decision': ['rate decision', 'interest rate', 'policy rate', 'funds rate', 
                         'monetary policy decision', 'policy decision'],
        'minutes': ['minutes', 'meeting minutes', 'fomc minutes', 'mpc minutes'],
        'speech': ['speech', 'remarks', 'testimony', 'address', 'powell', 'lagarde', 
                  'bailey', 'ueda', 'governor'],
        'report': ['report', 'outlook', 'projections', 'forecast', 'financial stability',
                  'monetary policy report'],
        'press_conference': ['press conference', 'q&a', 'presser'],
    }
    
    def __init__(self, cache_minutes: int = 15):
        """Initialize with cache duration"""
        self.cache_minutes = cache_minutes
        self._cache: Dict[str, List[CentralBankStatement]] = {}
        self._cache_times: Dict[str, datetime] = {}
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
    
    def get_recent_statements(
        self,
        bank: str,
        hours_back: int = 48,
        force_refresh: bool = False
    ) -> List[CentralBankStatement]:
        """
        Get recent statements from a central bank.
        
        Args:
            bank: Bank code (FED, ECB, BOE, BOJ, RBA, BOC, RBNZ, SNB)
            hours_back: How far back to look
            force_refresh: Bypass cache
            
        Returns:
            List of CentralBankStatement objects
        """
        bank = bank.upper()
        
        if bank not in self.FEEDS:
            print(f"[CentralBank] Unknown bank: {bank}")
            return []
        
        # Check cache
        if not force_refresh and self._is_cache_valid(bank):
            return self._filter_by_time(self._cache[bank], hours_back)
        
        # Fetch new data
        feed_info = self.FEEDS[bank]
        statements = []
        
        if feed_info.get('rss'):
            statements = self._fetch_rss(bank, feed_info)
        else:
            statements = self._fetch_backup(bank, feed_info)
        
        # Cache results
        self._cache[bank] = statements
        self._cache_times[bank] = datetime.utcnow()
        
        return self._filter_by_time(statements, hours_back)
    
    def get_all_recent(self, hours_back: int = 48) -> Dict[str, List[CentralBankStatement]]:
        """Get recent statements from all banks"""
        results = {}
        
        for bank in self.FEEDS.keys():
            statements = self.get_recent_statements(bank, hours_back)
            if statements:
                results[bank] = statements
        
        return results
    
    def get_statements_for_currency(
        self, 
        currency: str,
        hours_back: int = 48
    ) -> List[CentralBankStatement]:
        """Get statements affecting a specific currency"""
        currency = currency.upper()
        
        # Find bank for this currency
        for bank, info in self.FEEDS.items():
            if info['currency'] == currency:
                return self.get_recent_statements(bank, hours_back)
        
        return []
    
    def _fetch_rss(self, bank: str, feed_info: Dict) -> List[CentralBankStatement]:
        """Fetch and parse RSS feed"""
        statements = []
        
        try:
            feed = feedparser.parse(feed_info['rss'])
            
            for entry in feed.entries[:20]:  # Limit to recent 20
                try:
                    # Parse date
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        published = datetime(*entry.updated_parsed[:6])
                    else:
                        published = datetime.utcnow()
                    
                    # Get content
                    title = entry.title if hasattr(entry, 'title') else ''
                    summary = entry.summary if hasattr(entry, 'summary') else ''
                    url = entry.link if hasattr(entry, 'link') else ''
                    
                    # Clean HTML from summary
                    summary = self._clean_html(summary)
                    
                    # Determine statement type
                    statement_type = self._classify_statement(title + ' ' + summary)
                    
                    statements.append(CentralBankStatement(
                        bank=bank,
                        currency=feed_info['currency'],
                        title=title,
                        summary=summary[:500],  # Truncate
                        full_text=None,
                        url=url,
                        published=published,
                        statement_type=statement_type
                    ))
                    
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"[CentralBank] RSS error for {bank}: {e}")
        
        return statements
    
    def _fetch_backup(self, bank: str, feed_info: Dict) -> List[CentralBankStatement]:
        """Fetch from website when RSS not available"""
        statements = []
        
        try:
            response = requests.get(
                feed_info['backup_url'],
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Bank-specific parsing
            if bank == 'FED':
                statements = self._parse_fed_page(soup, feed_info['currency'])
            elif bank == 'ECB':
                statements = self._parse_ecb_page(soup, feed_info['currency'])
            elif bank == 'BOE':
                statements = self._parse_generic_news(soup, bank, feed_info['currency'])
            else:
                statements = self._parse_generic_news(soup, bank, feed_info['currency'])
                
        except Exception as e:
            print(f"[CentralBank] Backup fetch error for {bank}: {e}")
        
        return statements
    
    def _parse_fed_page(self, soup: BeautifulSoup, currency: str) -> List[CentralBankStatement]:
        """Parse Federal Reserve press releases page"""
        statements = []
        
        # Find news items
        news_items = soup.find_all('div', class_='row')
        
        for item in news_items[:15]:
            try:
                # Find date
                date_elem = item.find('time') or item.find(class_='ng-binding')
                if date_elem:
                    date_text = date_elem.get('datetime') or date_elem.text.strip()
                    try:
                        published = datetime.strptime(date_text[:10], '%Y-%m-%d')
                    except:
                        published = datetime.utcnow()
                else:
                    published = datetime.utcnow()
                
                # Find title and link
                link_elem = item.find('a')
                if link_elem:
                    title = link_elem.text.strip()
                    url = 'https://www.federalreserve.gov' + link_elem.get('href', '')
                else:
                    continue
                
                statement_type = self._classify_statement(title)
                
                statements.append(CentralBankStatement(
                    bank='FED',
                    currency=currency,
                    title=title,
                    summary=title,
                    full_text=None,
                    url=url,
                    published=published,
                    statement_type=statement_type
                ))
                
            except Exception:
                continue
        
        return statements
    
    def _parse_ecb_page(self, soup: BeautifulSoup, currency: str) -> List[CentralBankStatement]:
        """Parse ECB press releases page"""
        statements = []
        
        # Find press releases
        items = soup.find_all('dd', class_='ecb-pressItem')
        
        for item in items[:15]:
            try:
                date_elem = item.find('dt')
                link_elem = item.find('a')
                
                if not link_elem:
                    continue
                
                title = link_elem.text.strip()
                url = 'https://www.ecb.europa.eu' + link_elem.get('href', '')
                
                # Parse date
                if date_elem:
                    date_text = date_elem.text.strip()
                    try:
                        published = datetime.strptime(date_text, '%d %B %Y')
                    except:
                        published = datetime.utcnow()
                else:
                    published = datetime.utcnow()
                
                statement_type = self._classify_statement(title)
                
                statements.append(CentralBankStatement(
                    bank='ECB',
                    currency=currency,
                    title=title,
                    summary=title,
                    full_text=None,
                    url=url,
                    published=published,
                    statement_type=statement_type
                ))
                
            except Exception:
                continue
        
        return statements
    
    def _parse_generic_news(
        self, 
        soup: BeautifulSoup, 
        bank: str, 
        currency: str
    ) -> List[CentralBankStatement]:
        """Generic parser for news pages"""
        statements = []
        
        # Find common news item patterns
        for selector in ['article', '.news-item', '.press-release', 'li']:
            items = soup.select(selector)[:15]
            
            for item in items:
                try:
                    link = item.find('a')
                    if not link:
                        continue
                    
                    title = link.text.strip()
                    if len(title) < 10:
                        continue
                    
                    url = link.get('href', '')
                    
                    statement_type = self._classify_statement(title)
                    
                    statements.append(CentralBankStatement(
                        bank=bank,
                        currency=currency,
                        title=title,
                        summary=title,
                        full_text=None,
                        url=url,
                        published=datetime.utcnow(),  # Date parsing varies
                        statement_type=statement_type
                    ))
                    
                except Exception:
                    continue
            
            if statements:
                break
        
        return statements
    
    def _classify_statement(self, text: str) -> str:
        """Classify statement type based on keywords"""
        text_lower = text.lower()
        
        for stmt_type, keywords in self.STATEMENT_TYPES.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return stmt_type
        
        return 'other'
    
    def _clean_html(self, text: str) -> str:
        """Remove HTML tags from text"""
        soup = BeautifulSoup(text, 'html.parser')
        return soup.get_text(separator=' ').strip()
    
    def _filter_by_time(
        self, 
        statements: List[CentralBankStatement],
        hours_back: int
    ) -> List[CentralBankStatement]:
        """Filter statements by time"""
        cutoff = datetime.utcnow() - timedelta(hours=hours_back)
        return [s for s in statements if s.published >= cutoff]
    
    def _is_cache_valid(self, bank: str) -> bool:
        """Check if cache is still valid"""
        if bank not in self._cache_times:
            return False
        
        age = datetime.utcnow() - self._cache_times[bank]
        return age < timedelta(minutes=self.cache_minutes)
    
    def fetch_full_statement(self, statement: CentralBankStatement) -> Optional[str]:
        """
        Fetch full text of a statement for deeper analysis.
        
        Args:
            statement: Statement to fetch full text for
            
        Returns:
            Full text content or None
        """
        if not statement.url:
            return None
        
        try:
            response = requests.get(
                statement.url,
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try common content selectors
            for selector in ['article', '.content', '#content', 'main', '.body']:
                content = soup.select_one(selector)
                if content:
                    text = content.get_text(separator=' ')
                    # Clean up whitespace
                    text = re.sub(r'\s+', ' ', text).strip()
                    return text[:5000]  # Limit size
            
            # Fallback to body
            return soup.body.get_text(separator=' ')[:5000] if soup.body else None
            
        except Exception as e:
            print(f"[CentralBank] Error fetching full statement: {e}")
            return None

```
