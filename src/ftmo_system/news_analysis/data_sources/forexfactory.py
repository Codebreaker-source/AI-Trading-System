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
