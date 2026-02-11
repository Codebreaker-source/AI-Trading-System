"""
Hard Filters - Binary Pass/Fail Gates
======================================

These filters must ALL pass before a trade can be considered.
Any single failure blocks the trade entirely.

Filters:
- ATR Filter: Minimum volatility for tradeable conditions
- News Filter: No major economic events within buffer period
- Session Filter: London/NY sessions only (Asian session disabled)
- HTF Trend Filter: Trade must align with H1/H4 trend direction

Returns:
- passed: bool (True = all filters pass)
- reasons: list of failure reasons (empty if passed)

v2.2 (2025-12-04): Added HTF trend as hard gate
- Trade direction must align with H1/H4 trend
- Counter-trend trades are BLOCKED entirely
- Moved from 20% weighted factor to binary gate

v2.1 (2025-12-04): Disabled all trading during Asian session
- ALL pairs blocked during Asian session (22:00-08:00 UTC)
- Trade only during London (08:00-17:00) and NY (13:00-22:00) sessions
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass


@dataclass
class FilterResult:
    """Result from running hard filters"""
    passed: bool
    failed_filters: List[str]
    filter_details: Dict[str, Dict[str, Any]]
    
    def __str__(self) -> str:
        if self.passed:
            return "✅ All hard filters PASSED"
        else:
            reasons = ", ".join(self.failed_filters)
            return f"❌ Hard filters FAILED: {reasons}"


class HardFilters:
    """
    Binary pass/fail gates that must ALL pass before trading.
    """
    
    def __init__(
        self,
        min_atr_pips: float = 8.0,
        news_buffer_minutes: int = 30,
        require_liquid_session: bool = True,
        pip_values: Optional[Dict[str, float]] = None
    ):
        self.min_atr_pips = min_atr_pips
        self.news_buffer_minutes = news_buffer_minutes
        self.require_liquid_session = require_liquid_session
        
        self.pip_values = pip_values or {
            'EURUSD': 0.0001, 'GBPUSD': 0.0001, 'USDJPY': 0.01, 'USDCHF': 0.0001,
            'AUDUSD': 0.0001, 'USDCAD': 0.0001, 'NZDUSD': 0.0001, 'EURGBP': 0.0001,
            'EURUSD.sim': 0.0001, 'GBPUSD.sim': 0.0001, 'USDJPY.sim': 0.01, 'USDCHF.sim': 0.0001,
            'AUDUSD.sim': 0.0001, 'USDCAD.sim': 0.0001, 'NZDUSD.sim': 0.0001, 'EURGBP.sim': 0.0001,
        }
        
        self.london_open = 8
        self.london_close = 17
        self.ny_open = 13
        self.ny_close = 22
    
    def check_all(
        self,
        features: Dict[str, float],
        symbol: str,
        current_time: Optional[datetime] = None,
        upcoming_news: Optional[List[Dict[str, Any]]] = None,
        prediction: Optional[int] = None
    ) -> FilterResult:
        if current_time is None:
            current_time = datetime.utcnow()
        
        if upcoming_news is None:
            upcoming_news = []
        
        failed_filters = []
        filter_details = {}
        
        atr_passed, atr_details = self._check_atr(features, symbol)
        filter_details['atr'] = atr_details
        if not atr_passed:
            failed_filters.append('ATR')
        
        news_passed, news_details = self._check_news(current_time, upcoming_news)
        filter_details['news'] = news_details
        if not news_passed:
            failed_filters.append('NEWS')
        
        # Pass symbol for per-pair session filtering
        session_passed, session_details = self._check_session(current_time, symbol)
        filter_details['session'] = session_details
        if not session_passed:
            failed_filters.append('SESSION')
        
        # HTF trend gate - only check if we have a directional prediction
        if prediction is not None and prediction != 1:  # Not HOLD
            htf_passed, htf_details = self._check_htf_trend(features, prediction)
            filter_details['htf_trend'] = htf_details
            if not htf_passed:
                failed_filters.append('HTF_TREND')
        
        return FilterResult(
            passed=len(failed_filters) == 0,
            failed_filters=failed_filters,
            filter_details=filter_details
        )
    
    def _check_atr(self, features: Dict[str, float], symbol: str) -> Tuple[bool, Dict[str, Any]]:
        atr_value = features.get('atr', 0.0)
        
        if atr_value <= 0:
            return False, {
                'passed': False, 'reason': f'Invalid ATR value: {atr_value}',
                'atr_value': atr_value, 'atr_pips': 0.0, 'min_required': self.min_atr_pips
            }
        
        symbol_clean = symbol.replace('.sim', '')
        pip_value = self.pip_values.get(symbol, self.pip_values.get(symbol_clean, 0.0001))
        atr_pips = atr_value / pip_value
        passed = atr_pips >= self.min_atr_pips
        
        return passed, {
            'passed': passed, 'atr_value': float(atr_value), 'atr_pips': float(atr_pips),
            'min_required': self.min_atr_pips, 'pip_value': pip_value,
            'reason': None if passed else f'ATR {atr_pips:.1f} pips < {self.min_atr_pips} minimum'
        }
    
    def _check_news(self, current_time: datetime, upcoming_news: List[Dict[str, Any]]) -> Tuple[bool, Dict[str, Any]]:
        buffer = timedelta(minutes=self.news_buffer_minutes)
        blocking_events = []
        
        for event in upcoming_news:
            event_time = event.get('time')
            impact = event.get('impact', 1)
            
            if impact < 2 or event_time is None:
                continue
            
            time_diff = abs((event_time - current_time).total_seconds() / 60)
            
            if time_diff <= self.news_buffer_minutes:
                blocking_events.append({
                    'time': event_time.isoformat(), 'impact': impact,
                    'minutes_away': time_diff, 'name': event.get('name', 'Unknown Event')
                })
        
        passed = len(blocking_events) == 0
        
        return passed, {
            'passed': passed, 'buffer_minutes': self.news_buffer_minutes,
            'blocking_events': blocking_events,
            'reason': None if passed else f'{len(blocking_events)} high-impact event(s) within {self.news_buffer_minutes} min'
        }
    
    def _check_session(self, current_time: datetime, symbol: str = '') -> Tuple[bool, Dict[str, Any]]:
        """
        Session filtering - London and New York sessions only.
        
        ALL pairs blocked during Asian session (22:00-08:00 UTC).
        
        NOTE: Existing position management (scale-in, scale-out, BE, trailing)
        continues 24/7 regardless of this filter.
        """
        if not self.require_liquid_session:
            return True, {
                'passed': True, 'reason': 'Session filter disabled', 
                'current_hour': current_time.hour, 'session': 'ANY', 'symbol': symbol
            }
        
        hour = current_time.hour
        weekday = current_time.weekday()
        
        # Weekend check - all pairs blocked
        if weekday >= 5:
            return False, {
                'passed': False, 'reason': 'Weekend - markets closed', 
                'current_hour': hour, 'weekday': weekday, 'session': 'CLOSED', 'symbol': symbol
            }
        
        in_london = self.london_open <= hour < self.london_close
        in_ny = self.ny_open <= hour < self.ny_close
        
        # Determine current session
        if in_london and in_ny:
            session = 'LONDON_NY_OVERLAP'
        elif in_london:
            session = 'LONDON'
        elif in_ny:
            session = 'NEW_YORK'
        else:
            session = 'ASIAN'
        
        # During London or NY - all pairs allowed
        if in_london or in_ny:
            return True, {
                'passed': True, 'current_hour': hour, 'weekday': weekday, 'session': session,
                'in_london': in_london, 'in_ny': in_ny, 'symbol': symbol,
                'reason': None
            }
        
        # Asian session - ALL pairs blocked
        return False, {
            'passed': False, 'current_hour': hour, 'weekday': weekday, 'session': 'ASIAN',
            'in_london': False, 'in_ny': False, 'symbol': symbol,
            'reason': 'Asian session blocked - trade London/NY only'
        }
    
    def _check_htf_trend(self, features: Dict[str, float], prediction: int) -> Tuple[bool, Dict[str, Any]]:
        """
        HTF Trend Gate - Block counter-trend trades.
        
        Trade direction must align with H1/H4 trend.
        Uses htf_trend_direction and htf_trend_alignment features.
        
        Args:
            features: Feature dict containing HTF trend indicators
            prediction: 0=SELL, 2=BUY (1=HOLD should not reach here)
            
        Returns:
            (passed, details) tuple
        """
        is_bullish_trade = prediction == 2
        
        # Get HTF trend features
        htf_trend_dir = features.get('htf_trend_direction', 0)
        htf_trend_align = features.get('htf_trend_alignment', 0)
        htf_fast_ema = features.get('htf_fast_ema', 0)
        htf_slow_ema = features.get('htf_slow_ema', 0)
        
        # Determine HTF trend direction
        # htf_trend_direction: positive = bullish, negative = bearish, 0 = neutral
        if htf_trend_dir > 0:
            htf_bullish = True
            htf_bearish = False
        elif htf_trend_dir < 0:
            htf_bullish = False
            htf_bearish = True
        else:
            # Check EMA alignment as fallback
            if htf_fast_ema > 0 and htf_slow_ema > 0:
                htf_bullish = htf_fast_ema > htf_slow_ema
                htf_bearish = htf_fast_ema < htf_slow_ema
            else:
                # Neutral - allow trade (no clear trend to oppose)
                return True, {
                    'passed': True,
                    'reason': 'HTF trend neutral - trade allowed',
                    'htf_trend_dir': htf_trend_dir,
                    'htf_trend_align': htf_trend_align,
                    'trade_direction': 'BUY' if is_bullish_trade else 'SELL',
                    'htf_direction': 'NEUTRAL'
                }
        
        # Check alignment
        if is_bullish_trade:
            passed = htf_bullish
            htf_direction = 'BULLISH' if htf_bullish else 'BEARISH'
            reason = None if passed else f'BUY blocked - HTF trend is BEARISH'
        else:  # SELL
            passed = htf_bearish
            htf_direction = 'BEARISH' if htf_bearish else 'BULLISH'
            reason = None if passed else f'SELL blocked - HTF trend is BULLISH'
        
        return passed, {
            'passed': passed,
            'reason': reason,
            'htf_trend_dir': htf_trend_dir,
            'htf_trend_align': htf_trend_align,
            'trade_direction': 'BUY' if is_bullish_trade else 'SELL',
            'htf_direction': htf_direction
        }
    
    def get_session_info(self, current_time: Optional[datetime] = None) -> Dict[str, Any]:
        if current_time is None:
            current_time = datetime.utcnow()
        
        hour = current_time.hour
        in_london = self.london_open <= hour < self.london_close
        in_ny = self.ny_open <= hour < self.ny_close
        
        if in_london and in_ny:
            session_name = 'London/NY Overlap'
            liquidity = 'HIGH'
            allowed_pairs = 'ALL'
        elif in_london:
            session_name = 'London'
            liquidity = 'MEDIUM-HIGH'
            allowed_pairs = 'ALL'
        elif in_ny:
            session_name = 'New York'
            liquidity = 'MEDIUM-HIGH'
            allowed_pairs = 'ALL'
        else:
            session_name = 'Asian'
            liquidity = 'LOW'
            allowed_pairs = 'NONE - Trading disabled'
        
        if not in_london and not in_ny:
            if hour < self.london_open:
                hours_until = self.london_open - hour
            else:
                hours_until = (24 - hour) + self.london_open
        else:
            hours_until = 0
        
        return {
            'current_time_utc': current_time.isoformat(), 
            'session_name': session_name,
            'liquidity': liquidity, 
            'in_london': in_london, 
            'in_ny': in_ny, 
            'hours_until_liquid': hours_until,
            'allowed_pairs': allowed_pairs
        }


def passes_hard_filters(
    features: Dict[str, float],
    symbol: str,
    current_time: Optional[datetime] = None,
    upcoming_news: Optional[List[Dict[str, Any]]] = None
) -> bool:
    filters = HardFilters()
    result = filters.check_all(features, symbol, current_time, upcoming_news)
    return result.passed
