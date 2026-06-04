"""
Trade History Tracker - Hybrid CSV + Memory Tracking
=====================================================

Loads trade history from EA's trades_execution_log.csv at startup,
then tracks in memory during runtime with periodic sync.

Provides:
- Current drawdown estimate (from dd_tier + daily_pnl_pct)
- Consecutive loss count
- Daily P&L
- Portfolio heat (from RiskManager)

Used by DangerScorer for System Stress category.

Author: AI Trading System
Version: 1.0
Date: 2025-12-16
"""

import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass, field
import logging


# Default path to EA's trade execution log
DEFAULT_MT5_FILES_PATH = r"C:\Users\mt5-admin\AppData\Roaming\MetaQuotes\Terminal\EE0304F13905552AE0B5EAEFB04866EB\MQL5\Files"
DEFAULT_TRADES_LOG = "trades_execution_log.csv"


@dataclass
class TradeRecord:
    """Single trade record"""
    timestamp: datetime
    symbol: str
    action: str  # BUY or SELL
    lot_size: float
    result: str  # SUCCESS, FAILED, etc.
    daily_pnl_pct: float
    dd_tier: int
    ticket: int = 0
    
    @property
    def is_success(self) -> bool:
        return self.result.upper() == 'SUCCESS'
    
    @property
    def is_loss(self) -> bool:
        # Consider failed trades and successful trades that closed at loss
        # For now, we can only determine from result column
        return self.result.upper() == 'FAILED'


@dataclass
class TradeHistoryState:
    """Current state derived from trade history"""
    consecutive_losses: int = 0
    consecutive_wins: int = 0
    current_drawdown: float = 0.0  # Decimal (0.05 = 5%)
    daily_pnl_pct: float = 0.0
    dd_tier: int = 0
    total_trades_today: int = 0
    last_sync: datetime = field(default_factory=datetime.now)
    
    def __str__(self):
        return (f"[HISTORY] DD: {self.current_drawdown:.1%} (Tier {self.dd_tier}) | "
                f"Daily: {self.daily_pnl_pct:+.2%} | "
                f"Streak: {self.consecutive_losses}L/{self.consecutive_wins}W")


class TradeHistoryTracker:
    """
    Hybrid trade history tracker.
    
    - Loads from CSV at startup
    - Tracks in memory during runtime
    - Syncs with CSV periodically (default: 5 minutes)
    
    Provides data for DangerScorer's System Stress category.
    """
    
    def __init__(
        self,
        trades_log_path: str = None,
        sync_interval_minutes: int = 5,
        logger: logging.Logger = None
    ):
        """
        Initialize trade history tracker.
        
        Args:
            trades_log_path: Path to trades_execution_log.csv (or auto-detect)
            sync_interval_minutes: How often to re-sync with CSV (default 5)
            logger: Logger instance (optional)
        """
        self.logger = logger or logging.getLogger(__name__)
        self.sync_interval = timedelta(minutes=sync_interval_minutes)
        
        # Resolve CSV path
        if trades_log_path:
            self.trades_log_path = Path(trades_log_path)
        else:
            self.trades_log_path = Path(DEFAULT_MT5_FILES_PATH) / DEFAULT_TRADES_LOG
        
        # State
        self.state = TradeHistoryState()
        self.trade_history: List[TradeRecord] = []
        self._last_sync_time = datetime.min
        
        # Drawdown tier mapping (from EA's risk management)
        self.dd_tier_to_percent = {
            0: 0.02,   # Normal: ~2% or less
            1: 0.07,   # Warning: ~5-10%
            2: 0.12,   # Danger: ~10-15%
            3: 0.18    # Critical: >15%
        }
        
        # Initial load
        self._load_from_csv()
    
    def _load_from_csv(self) -> bool:
        """
        Load trade history from CSV file.
        
        Returns:
            True if loaded successfully, False otherwise
        """
        if not self.trades_log_path.exists():
            self.logger.warning(f"Trades log not found: {self.trades_log_path}")
            return False
        
        try:
            df = pd.read_csv(self.trades_log_path)
            
            if df.empty:
                self.logger.info("Trades log is empty")
                return True
            
            # Parse records
            self.trade_history = []
            for _, row in df.iterrows():
                try:
                    record = TradeRecord(
                        timestamp=pd.to_datetime(row.get('timestamp', '')),
                        symbol=str(row.get('symbol', '')),
                        action=str(row.get('action', '')),
                        lot_size=float(row.get('lot_size', 0.01)),
                        result=str(row.get('result', 'UNKNOWN')),
                        daily_pnl_pct=float(row.get('daily_pnl_pct', 0.0)),
                        dd_tier=int(row.get('dd_tier', 0)),
                        ticket=int(row.get('ticket', 0))
                    )
                    self.trade_history.append(record)
                except Exception as e:
                    # Skip malformed rows
                    continue
            
            # Update state from history
            self._update_state_from_history()
            self._last_sync_time = datetime.now()
            
            self.logger.info(f"Loaded {len(self.trade_history)} trades from CSV")
            self.logger.info(f"Current state: {self.state}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading trades CSV: {e}")
            return False
    
    def _update_state_from_history(self):
        """Update state from loaded trade history."""
        if not self.trade_history:
            self.state = TradeHistoryState()
            return
        
        # Get latest trade for dd_tier and daily_pnl
        latest = self.trade_history[-1]
        self.state.dd_tier = latest.dd_tier
        self.state.daily_pnl_pct = latest.daily_pnl_pct
        
        # Calculate drawdown estimate
        self.state.current_drawdown = self._calculate_drawdown(
            latest.dd_tier, 
            latest.daily_pnl_pct
        )
        
        # Count consecutive losses (from most recent backwards)
        self.state.consecutive_losses = self._count_consecutive_losses()
        self.state.consecutive_wins = self._count_consecutive_wins()
        
        # Count today's trades
        today = datetime.now().date()
        self.state.total_trades_today = sum(
            1 for t in self.trade_history 
            if t.timestamp.date() == today
        )
        
        self.state.last_sync = datetime.now()
    
    def _calculate_drawdown(self, dd_tier: int, daily_pnl_pct: float) -> float:
        """
        Calculate drawdown estimate from dd_tier and daily_pnl_pct.
        
        Uses hybrid approach:
        - Base from dd_tier (EA's categorization)
        - Adjust with daily_pnl if negative
        
        Args:
            dd_tier: EA's drawdown tier (0-3)
            daily_pnl_pct: Today's P&L as decimal
            
        Returns:
            Estimated drawdown as decimal (0.05 = 5%)
        """
        # Base drawdown from tier
        base_dd = self.dd_tier_to_percent.get(dd_tier, 0.02)
        
        # Adjust with daily P&L if negative
        if daily_pnl_pct < 0:
            return max(base_dd, abs(daily_pnl_pct))
        
        return base_dd
    
    def _count_consecutive_losses(self) -> int:
        """
        Count consecutive losing trades from most recent.
        
        Only counts SUCCESS trades as potential losses (FAILED = didn't execute).
        For now, we don't have profit data, so we estimate from patterns.
        
        Returns:
            Number of consecutive losses
        """
        if not self.trade_history:
            return 0
        
        # Filter to only executed trades (SUCCESS)
        executed = [t for t in self.trade_history if t.result.upper() == 'SUCCESS']
        
        if not executed:
            return 0
        
        # We don't have actual P&L, so we use dd_tier changes as proxy
        # If dd_tier increased recently, likely had losses
        consecutive = 0
        
        # Look at last N trades for dd_tier pattern
        recent = executed[-10:]  # Last 10 executed trades
        
        if len(recent) < 2:
            return 0
        
        # Check if dd_tier has been increasing (indicates losses)
        for i in range(len(recent) - 1, 0, -1):
            if recent[i].dd_tier >= recent[i-1].dd_tier and recent[i].dd_tier > 0:
                consecutive += 1
            else:
                break
        
        return consecutive
    
    def _count_consecutive_wins(self) -> int:
        """
        Count consecutive winning trades from most recent.
        
        Returns:
            Number of consecutive wins
        """
        if not self.trade_history:
            return 0
        
        # Filter to only executed trades
        executed = [t for t in self.trade_history if t.result.upper() == 'SUCCESS']
        
        if not executed:
            return 0
        
        consecutive = 0
        recent = executed[-10:]
        
        if len(recent) < 2:
            return 0
        
        # Check if dd_tier has been decreasing or stable at 0 (indicates wins)
        for i in range(len(recent) - 1, 0, -1):
            if recent[i].dd_tier <= recent[i-1].dd_tier and recent[i].dd_tier == 0:
                consecutive += 1
            else:
                break
        
        return consecutive
    
    def sync_if_needed(self) -> bool:
        """
        Re-sync with CSV if sync interval has passed.
        
        Returns:
            True if synced, False if not needed yet
        """
        if datetime.now() - self._last_sync_time > self.sync_interval:
            self.logger.debug("Sync interval reached, reloading CSV...")
            return self._load_from_csv()
        return False
    
    def force_sync(self) -> bool:
        """
        Force immediate sync with CSV.
        
        Returns:
            True if synced successfully
        """
        return self._load_from_csv()
    
    def get_current_drawdown(self) -> float:
        """
        Get current drawdown estimate.
        
        Returns:
            Drawdown as decimal (0.05 = 5%)
        """
        self.sync_if_needed()
        return self.state.current_drawdown
    
    def get_consecutive_losses(self) -> int:
        """
        Get current consecutive loss count.
        
        Returns:
            Number of consecutive losses
        """
        self.sync_if_needed()
        return self.state.consecutive_losses
    
    def get_daily_pnl(self) -> float:
        """
        Get today's P&L percentage.
        
        Returns:
            Daily P&L as decimal
        """
        self.sync_if_needed()
        return self.state.daily_pnl_pct
    
    def get_dd_tier(self) -> int:
        """
        Get current drawdown tier (0-3).
        
        Returns:
            Drawdown tier from EA
        """
        self.sync_if_needed()
        return self.state.dd_tier
    
    def get_danger_inputs(self) -> Dict:
        """
        Get all inputs needed for DangerScorer's System Stress category.
        
        Returns:
            Dict with current_drawdown, consecutive_losses, daily_pnl_percent
        """
        self.sync_if_needed()
        return {
            'current_drawdown': self.state.current_drawdown,
            'consecutive_losses': self.state.consecutive_losses,
            'daily_pnl_percent': self.state.daily_pnl_pct
        }
    
    def get_state_summary(self) -> str:
        """Get human-readable state summary."""
        return str(self.state)
    
    def update_trade_result(self, symbol: str, action: str, result: str, 
                           daily_pnl_pct: float = None, dd_tier: int = None):
        """
        Update state with new trade result (runtime tracking).
        
        Call this after a trade completes to keep state fresh without CSV sync.
        
        Args:
            symbol: Trading symbol
            action: BUY or SELL
            result: SUCCESS or FAILED
            daily_pnl_pct: Updated daily P&L (optional)
            dd_tier: Updated drawdown tier (optional)
        """
        record = TradeRecord(
            timestamp=datetime.now(),
            symbol=symbol,
            action=action,
            lot_size=0.01,
            result=result,
            daily_pnl_pct=daily_pnl_pct or self.state.daily_pnl_pct,
            dd_tier=dd_tier or self.state.dd_tier
        )
        
        self.trade_history.append(record)
        self._update_state_from_history()
        
        self.logger.info(f"Trade result updated: {symbol} {action} {result}")
        self.logger.info(f"New state: {self.state}")


# Test function
def _test_trade_history_tracker():
    """Test trade history tracker."""
    print("=" * 60)
    print("TRADE HISTORY TRACKER TEST")
    print("=" * 60)
    
    # Initialize tracker
    tracker = TradeHistoryTracker()
    
    print(f"\nCSV Path: {tracker.trades_log_path}")
    print(f"CSV Exists: {tracker.trades_log_path.exists()}")
    print(f"Trades Loaded: {len(tracker.trade_history)}")
    print(f"\nCurrent State:")
    print(f"  {tracker.state}")
    
    print(f"\nDanger Inputs:")
    inputs = tracker.get_danger_inputs()
    for key, value in inputs.items():
        print(f"  {key}: {value}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    _test_trade_history_tracker()
