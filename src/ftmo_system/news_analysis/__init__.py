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
