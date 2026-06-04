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
