"""
News Integration - Compatibility Wrapper
=========================================

Provides backward-compatible interface for live_trading_system_v4_confluence.py
while using the new comprehensive news_analysis system.

Old interface methods:
- get_events_for_hard_filter(buffer_minutes) -> List[Dict]

New bias functionality:
- is_trade_allowed(pair, direction) -> (bool, str)
- get_confidence_adjustment(pair, direction) -> float
- get_bias(pair) -> UnifiedBias

V2.1 Update (2025-12-02):
- Added MT5CalendarReader as fallback/supplemental news source
- EA v2.33 exports calendar_events.csv from MT5 built-in calendar
- Works even when ForexFactory scraping is blocked

Author: AI Trading System
Version: 2.1
Date: 2025-12-02
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path
import json

# Import new news analysis system
from news_analysis import (
    NewsAnalyzer,
    BiasDirection,
    BiasStrength,
    UnifiedBias,
    ImpactLevel
)

# Import MT5 calendar reader (v2.33 EA exports calendar_events.csv)
try:
    from mt5_calendar_reader import MT5CalendarReader, should_block_for_news
    MT5_CALENDAR_AVAILABLE = True
except ImportError:
    MT5_CALENDAR_AVAILABLE = False
    print("[NewsIntegration] MT5CalendarReader not available - using web sources only")


class NewsIntegration:
    """
    News integration for trading system.
    
    Combines:
    - Economic calendar blocking (±30-60 min around high-impact events)
    - Data release surprise → bias generation
    - Central bank sentiment analysis
    - Fiscal policy analysis
    
    Bias System (Option C Hybrid, 4-8 hours):
    - Weak surprise (< 1.5σ): ±5% confidence adjustment, 4 hours
    - Medium surprise (1.5-2.5σ): ±10% confidence adjustment, 6 hours  
    - Strong surprise (> 2.5σ): Block counter-trend trades, 8 hours
    """
    
    def __init__(
        self,
        cache_duration_minutes: int = 30,
        log_dir: Path = None,
        fred_api_key: str = None,
        auto_update: bool = True
    ):
        """
        Initialize news integration.
        
        Args:
            cache_duration_minutes: How long to cache calendar data
            log_dir: Directory for logs
            fred_api_key: Optional FRED API key for economic data
            auto_update: Whether to auto-update on first call
        """
        self.cache_duration = cache_duration_minutes
        self.log_dir = Path(log_dir) if log_dir else Path('logs')
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize the new analyzer
        self.analyzer = NewsAnalyzer(
            fred_api_key=fred_api_key,
            auto_update=auto_update,
            update_interval=cache_duration_minutes * 60
        )
        
        # Cache for events
        self._events_cache: List[Dict] = []
        self._cache_time: Optional[datetime] = None
        
        # Initialize MT5 calendar reader (NEW v2.1)
        self.mt5_calendar = None
        if MT5_CALENDAR_AVAILABLE:
            try:
                self.mt5_calendar = MT5CalendarReader()
                print("[NewsIntegration] MT5 calendar reader initialized")
            except Exception as e:
                print(f"[NewsIntegration] MT5 calendar init failed: {e}")
        
        # Initialize on first use
        self._initialized = False
    
    def _ensure_initialized(self):
        """Ensure analyzer is initialized"""
        if not self._initialized:
            try:
                self.analyzer.update()
                self._initialized = True
            except Exception as e:
                print(f"[NewsIntegration] Init warning: {e}")
                self._initialized = True  # Don't retry repeatedly
    
    # =========================================================================
    # BACKWARD-COMPATIBLE INTERFACE (for existing code)
    # =========================================================================
    
    def get_events_for_hard_filter(
        self,
        buffer_minutes: int = 30
    ) -> List[Dict]:
        """
        Get high-impact events within buffer window for hard filtering.
        
        This is the BACKWARD-COMPATIBLE method for existing live trading system.
        Sources: NewsAnalyzer (web) + MT5 Calendar (EA export) for redundancy.
        
        Args:
            buffer_minutes: Minutes before event to trigger filter
            
        Returns:
            List of events within buffer window:
            [{'name': 'NFP', 'currency': 'USD', 'impact': 'high', 'minutes_until': 25}, ...]
        """
        self._ensure_initialized()
        
        events = []
        seen_events = set()  # Deduplicate events from multiple sources
        
        # Source 1: Web-based NewsAnalyzer
        try:
            # Get upcoming events from analyzer
            upcoming = self.analyzer.get_upcoming_events(hours_ahead=2)
            
            now = datetime.utcnow()
            
            for event in upcoming:
                # Check if within buffer
                minutes_until = event.minutes_until()
                
                # Include if within buffer before, or just released (within 5 min after)
                if -5 <= minutes_until <= buffer_minutes:
                    # Only include HIGH and CRITICAL impact
                    if event.impact.value >= ImpactLevel.HIGH.value:
                        event_key = f"{event.currency}_{event.event_name[:20]}"
                        if event_key not in seen_events:
                            seen_events.add(event_key)
                            events.append({
                                'name': event.event_name,
                                'currency': event.currency,
                                'impact': event.impact.name.lower(),
                                'minutes_until': round(minutes_until),
                                'datetime': event.datetime_utc.isoformat(),
                                'source': 'web'
                            })
            
        except Exception as e:
            print(f"[NewsIntegration] Web analyzer error: {e}")
        
        # Source 2: MT5 Calendar (NEW v2.1 - fallback/supplemental)
        if self.mt5_calendar is not None:
            try:
                mt5_events = self.mt5_calendar.get_upcoming_events(
                    min_impact='HIGH',
                    hours_ahead=2
                )
                
                now = datetime.now()
                
                for event in mt5_events:
                    event_time = event.get('time')
                    if event_time:
                        # Calculate minutes until event
                        if isinstance(event_time, datetime):
                            minutes_until = (event_time - now).total_seconds() / 60
                        else:
                            minutes_until = buffer_minutes  # Default to buffer if can't calculate
                        
                        # Include if within buffer
                        if -5 <= minutes_until <= buffer_minutes:
                            event_key = f"{event.get('currency', '')}_{event.get('event', '')[:20]}"
                            if event_key not in seen_events:
                                seen_events.add(event_key)
                                events.append({
                                    'name': event.get('event', 'Unknown'),
                                    'currency': event.get('currency', ''),
                                    'impact': event.get('impact', 'high').lower(),
                                    'minutes_until': round(minutes_until),
                                    'datetime': str(event_time),
                                    'source': 'mt5'
                                })
            except Exception as e:
                print(f"[NewsIntegration] MT5 calendar error: {e}")
        
        return events
    
    def get_upcoming_events(
        self,
        hours_ahead: int = 24,
        pair: str = None
    ) -> List[Dict]:
        """
        Get upcoming economic events.
        
        Args:
            hours_ahead: How far ahead to look
            pair: Optional pair to filter by
            
        Returns:
            List of event dicts
        """
        self._ensure_initialized()
        
        try:
            events = self.analyzer.get_upcoming_events(hours_ahead, pair)
            return [
                {
                    'name': e.event_name,
                    'currency': e.currency,
                    'impact': e.impact.name.lower(),
                    'datetime': e.datetime_utc.isoformat(),
                    'forecast': e.forecast,
                    'previous': e.previous,
                    'actual': e.actual,
                }
                for e in events
            ]
        except Exception as e:
            print(f"[NewsIntegration] Error: {e}")
            return []
    
    # =========================================================================
    # NEW BIAS FUNCTIONALITY
    # =========================================================================
    
    def is_trade_allowed(
        self,
        pair: str,
        direction: str,
        mt5_buffer_minutes: int = 30
    ) -> Tuple[bool, str]:
        """
        Check if a trade is allowed based on news analysis.
        
        Checks:
        1. Calendar blocking (±30-60 min around high-impact events)
        2. Strong bias blocking (blocks counter-trend trades)
        3. MT5 calendar blocking (NEW v2.1 - fallback/supplemental source)
        
        Args:
            pair: Currency pair (e.g., 'EURUSD' or 'EURUSD.sim')
            direction: 'BUY' or 'SELL'
            mt5_buffer_minutes: Minutes around high-impact events to block (MT5 calendar)
            
        Returns:
            (is_allowed, reason_if_blocked)
        """
        self._ensure_initialized()
        
        # Check MT5 calendar FIRST (most reliable when EA is running)
        if self.mt5_calendar is not None:
            try:
                blocked, reason = self.mt5_calendar.should_block_trading(pair, mt5_buffer_minutes)
                if blocked:
                    return False, f"[MT5 Calendar] {reason}"
            except Exception as e:
                print(f"[NewsIntegration] MT5 calendar check error: {e}")
        
        # Then check web-based analyzer
        try:
            return self.analyzer.is_trade_allowed(pair, direction)
        except Exception as e:
            print(f"[NewsIntegration] Error checking trade: {e}")
            return True, ""  # Fail open - allow trade if error
    
    def get_confidence_adjustment(
        self,
        pair: str,
        direction: str
    ) -> float:
        """
        Get confidence adjustment for a trade based on news bias.
        
        Positive value = bias supports trade direction (boost confidence)
        Negative value = bias opposes trade direction (reduce confidence)
        
        Args:
            pair: Currency pair
            direction: 'BUY' or 'SELL'
            
        Returns:
            Adjustment value (-0.15 to +0.15)
        """
        self._ensure_initialized()
        
        try:
            return self.analyzer.get_confidence_adjustment(pair, direction)
        except Exception as e:
            print(f"[NewsIntegration] Error getting adjustment: {e}")
            return 0.0
    
    def get_bias(self, pair: str) -> Optional[UnifiedBias]:
        """
        Get current unified bias for a pair.
        
        Args:
            pair: Currency pair
            
        Returns:
            UnifiedBias object or None
        """
        self._ensure_initialized()
        
        try:
            return self.analyzer.get_bias(pair)
        except Exception as e:
            print(f"[NewsIntegration] Error getting bias: {e}")
            return None
    
    def get_blocked_pairs(self) -> List[str]:
        """Get pairs currently blocked due to economic events"""
        self._ensure_initialized()
        
        try:
            return self.analyzer.get_blocked_pairs()
        except Exception as e:
            print(f"[NewsIntegration] Error: {e}")
            return []
    
    def update(self, force: bool = False):
        """
        Update all news analysis.
        
        Args:
            force: Force immediate update
        """
        try:
            self.analyzer.update(force=force)
            self._initialized = True
        except Exception as e:
            print(f"[NewsIntegration] Update error: {e}")
    
    def process_economic_release(
        self,
        event_name: str,
        currency: str,
        actual: float,
        forecast: float,
        previous: float = None
    ):
        """
        Process a new economic data release.
        
        Call this when actual values are released to generate immediate bias.
        
        Args:
            event_name: Name of the event (e.g., 'Non-Farm Payrolls')
            currency: Currency affected
            actual: Actual released value
            forecast: Consensus forecast
            previous: Previous value (optional)
        """
        try:
            return self.analyzer.process_economic_release(
                event_name, currency, actual, forecast, previous
            )
        except Exception as e:
            print(f"[NewsIntegration] Error processing release: {e}")
            return None
    
    def get_summary(self) -> str:
        """Get human-readable summary of news analysis state"""
        self._ensure_initialized()
        
        summary_parts = []
        
        # Web analyzer summary
        try:
            summary_parts.append(self.analyzer.get_summary())
        except Exception as e:
            summary_parts.append(f"[Web Analyzer] Error: {e}")
        
        # MT5 calendar summary (NEW v2.1)
        if self.mt5_calendar is not None:
            try:
                mt5_summary = self.mt5_calendar.get_status_summary()
                summary_parts.append(f"[MT5] {mt5_summary}")
            except Exception as e:
                summary_parts.append(f"[MT5] Error: {e}")
        else:
            summary_parts.append("[MT5] Calendar not available")
        
        return " | ".join(summary_parts)
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def should_skip_pair(self, pair: str) -> Tuple[bool, str]:
        """
        Check if pair should be skipped entirely (calendar block).
        
        Different from is_trade_allowed - this checks only calendar,
        not bias blocking.
        
        Args:
            pair: Currency pair
            
        Returns:
            (should_skip, reason)
        """
        blocked = self.get_blocked_pairs()
        pair_clean = pair.replace('.sim', '').upper()
        
        if pair_clean in blocked:
            return True, f"{pair_clean} blocked due to economic event"
        
        return False, ""
    
    def get_bias_for_logging(self, pair: str) -> Dict:
        """Get bias info formatted for logging"""
        bias = self.get_bias(pair)
        
        if bias is None:
            return {
                'direction': 'NEUTRAL',
                'strength': 'WEAK',
                'confidence_adj': 0.0,
                'sources': []
            }
        
        return {
            'direction': bias.direction.name,
            'strength': bias.strength.name,
            'confidence_adj': bias.confidence_adjustment,
            'sources': bias.sources,
            'block_buys': bias.should_block_buys,
            'block_sells': bias.should_block_sells,
        }
