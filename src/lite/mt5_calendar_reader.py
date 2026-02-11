"""
MT5 Calendar Reader - Reads economic calendar exported by BridgeEA v2.33
Replaces ForexFactory web scraping with MT5's built-in calendar
"""

import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class MT5CalendarReader:
    """Reads economic calendar events exported by BridgeEA v2.33"""
    
    def __init__(self, calendar_file: str = None):
        """
        Initialize calendar reader
        
        Args:
            calendar_file: Path to calendar_events.csv (default: MT5 Files folder)
        """
        if calendar_file is None:
            self.calendar_file = Path(
                "C:/Users/mt5-admin/AppData/Roaming/MetaQuotes/Terminal/"
                "EE0304F13905552AE0B5EAEFB04866EB/MQL5/Files/calendar_events.csv"
            )
        else:
            self.calendar_file = Path(calendar_file)
        
        self.events_df: Optional[pd.DataFrame] = None
        self.last_load_time: Optional[datetime] = None
        
        # Impact mapping for consistency
        self.impact_map = {
            'HIGH': 3,
            'MEDIUM': 2,
            'LOW': 1
        }
    
    def load_events(self, force_reload: bool = False) -> pd.DataFrame:
        """
        Load calendar events from CSV file
        
        Args:
            force_reload: Force reload even if recently loaded
            
        Returns:
            DataFrame with calendar events
        """
        # Check if we need to reload (reload every 60 seconds max)
        if not force_reload and self.events_df is not None:
            if self.last_load_time and (datetime.now() - self.last_load_time).seconds < 60:
                return self.events_df
        
        if not self.calendar_file.exists():
            logger.warning(f"[Calendar] File not found: {self.calendar_file}")
            return pd.DataFrame()
        
        try:
            self.events_df = pd.read_csv(self.calendar_file)
            self.last_load_time = datetime.now()
            
            # Parse event_time column
            if 'event_time' in self.events_df.columns:
                self.events_df['event_time'] = pd.to_datetime(
                    self.events_df['event_time'], 
                    format='%Y.%m.%d %H:%M',
                    errors='coerce'
                )
            
            # Add numeric impact
            if 'importance' in self.events_df.columns:
                self.events_df['impact_num'] = self.events_df['importance'].map(self.impact_map)
            
            logger.info(f"[Calendar] Loaded {len(self.events_df)} events from MT5")
            return self.events_df
            
        except Exception as e:
            logger.error(f"[Calendar] Error loading events: {e}")
            return pd.DataFrame()
    
    def get_upcoming_events(
        self, 
        currency: str = None,
        min_impact: str = 'LOW',
        hours_ahead: int = 24
    ) -> List[Dict]:
        """
        Get upcoming economic events
        
        Args:
            currency: Filter by currency (USD, EUR, GBP, etc.)
            min_impact: Minimum impact level ('LOW', 'MEDIUM', 'HIGH')
            hours_ahead: How many hours ahead to look
            
        Returns:
            List of event dictionaries
        """
        df = self.load_events()
        
        if df.empty:
            return []
        
        now = datetime.now()
        cutoff = now + timedelta(hours=hours_ahead)
        
        # Filter by time
        mask = (df['event_time'] >= now) & (df['event_time'] <= cutoff)
        
        # Filter by currency if specified
        if currency:
            mask &= (df['currency'] == currency)
        
        # Filter by impact
        min_impact_num = self.impact_map.get(min_impact, 1)
        mask &= (df['impact_num'] >= min_impact_num)
        
        filtered = df[mask].copy()
        
        # Convert to list of dicts
        events = []
        for _, row in filtered.iterrows():
            events.append({
                'event_id': row.get('event_id'),
                'time': row.get('event_time'),
                'currency': row.get('currency'),
                'country': row.get('country'),
                'event': row.get('event_name'),
                'impact': row.get('importance'),
                'actual': row.get('actual'),
                'forecast': row.get('forecast'),
                'previous': row.get('previous')
            })
        
        return events
    
    def has_high_impact_soon(
        self, 
        currency: str,
        minutes_buffer: int = 30
    ) -> bool:
        """
        Check if there's a high-impact event within buffer period
        
        Args:
            currency: Currency to check (USD, EUR, etc.)
            minutes_buffer: Minutes before/after event to block
            
        Returns:
            True if high-impact event is within buffer
        """
        df = self.load_events()
        
        if df.empty:
            return False
        
        now = datetime.now()
        buffer_start = now - timedelta(minutes=minutes_buffer)
        buffer_end = now + timedelta(minutes=minutes_buffer)
        
        # Filter for high impact events in buffer window
        mask = (
            (df['event_time'] >= buffer_start) & 
            (df['event_time'] <= buffer_end) &
            (df['currency'] == currency) &
            (df['importance'] == 'HIGH')
        )
        
        return mask.any()
    
    def should_block_trading(
        self, 
        symbol: str,
        minutes_buffer: int = 30
    ) -> tuple[bool, str]:
        """
        Check if trading should be blocked for a symbol due to news
        
        Args:
            symbol: Trading symbol (e.g., 'EURUSD.sim')
            minutes_buffer: Minutes buffer around high-impact events
            
        Returns:
            Tuple of (should_block, reason)
        """
        # Extract currencies from symbol
        clean_symbol = symbol.replace('.sim', '')
        base_currency = clean_symbol[:3]
        quote_currency = clean_symbol[3:]
        
        # Check both currencies
        if self.has_high_impact_soon(base_currency, minutes_buffer):
            return True, f"High-impact {base_currency} news"
        
        if self.has_high_impact_soon(quote_currency, minutes_buffer):
            return True, f"High-impact {quote_currency} news"
        
        return False, ""
    
    def get_status_summary(self) -> str:
        """Get a summary string for logging"""
        df = self.load_events()
        
        if df.empty:
            return "Calendar: No events loaded"
        
        # Count events by impact
        high_count = len(df[df['importance'] == 'HIGH'])
        medium_count = len(df[df['importance'] == 'MEDIUM'])
        
        # Next high-impact event
        now = datetime.now()
        upcoming_high = df[(df['importance'] == 'HIGH') & (df['event_time'] > now)]
        
        next_event = ""
        if not upcoming_high.empty:
            next_row = upcoming_high.iloc[0]
            time_until = next_row['event_time'] - now
            hours_until = time_until.total_seconds() / 3600
            next_event = f" | Next HIGH: {next_row['currency']} in {hours_until:.1f}h"
        
        return f"Calendar: {high_count} HIGH, {medium_count} MEDIUM events{next_event}"


# Create singleton instance
_calendar_reader: Optional[MT5CalendarReader] = None

def get_calendar_reader() -> MT5CalendarReader:
    """Get singleton calendar reader instance"""
    global _calendar_reader
    if _calendar_reader is None:
        _calendar_reader = MT5CalendarReader()
    return _calendar_reader


def should_block_for_news(symbol: str, minutes_buffer: int = 30) -> tuple[bool, str]:
    """
    Convenience function to check if trading should be blocked
    
    Args:
        symbol: Trading symbol
        minutes_buffer: Minutes around events to block
        
    Returns:
        Tuple of (should_block, reason)
    """
    reader = get_calendar_reader()
    return reader.should_block_trading(symbol, minutes_buffer)


# Test if run directly
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    reader = MT5CalendarReader()
    
    print("\n=== MT5 Calendar Reader Test ===\n")
    
    # Load events
    events_df = reader.load_events()
    print(f"Loaded {len(events_df)} events")
    
    if not events_df.empty:
        print("\nSample events:")
        print(events_df.head(10).to_string())
    
    # Test blocking function
    print("\n=== Testing News Blocking ===")
    test_symbols = ['EURUSD.sim', 'USDJPY.sim', 'GBPUSD.sim']
    
    for symbol in test_symbols:
        blocked, reason = reader.should_block_trading(symbol)
        status = f"BLOCKED: {reason}" if blocked else "OK"
        print(f"{symbol}: {status}")
    
    # Status summary
    print(f"\n{reader.get_status_summary()}")
