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
