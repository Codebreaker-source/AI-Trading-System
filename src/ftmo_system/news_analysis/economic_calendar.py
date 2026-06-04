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
