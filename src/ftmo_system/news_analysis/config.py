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
