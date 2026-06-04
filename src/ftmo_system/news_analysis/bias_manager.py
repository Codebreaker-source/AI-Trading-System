"""
Bias Manager - Central Bias State Management
=============================================

Combines all bias sources (economic releases, central bank statements,
fiscal policy) into unified trading biases per currency pair.

Implements Option C (Hybrid) with 4-8 hour duration:
- Weak surprise (< 1.5σ): Confidence ±5%, 4 hours
- Medium surprise (1.5-2.5σ): Confidence ±10%, 6 hours
- Strong surprise (> 2.5σ): Block counter-trend trades, 8 hours

Author: AI Trading System
Version: 1.0
Date: 2025-11-29
"""

from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple, Any
from dataclasses import dataclass, field
import json
from pathlib import Path

from .config import BiasDirection, BiasStrength, TIMING, LOGGING, CURRENCY_MAPPING
from .economic_calendar import EconomicCalendar
from .data_release_analyzer import DataReleaseAnalyzer, DataSurprise
from .central_bank_analyzer import CentralBankAnalyzer, CentralBankBias
from .government_analyzer import GovernmentAnalyzer, FiscalBias


@dataclass
class UnifiedBias:
    """Combined bias from all sources for a currency pair"""
    
    pair: str
    direction: BiasDirection
    strength: BiasStrength
    confidence_adjustment: float  # -0.15 to +0.15
    
    # Component biases
    data_bias: Optional[BiasDirection] = None
    central_bank_bias: Optional[BiasDirection] = None
    fiscal_bias: Optional[BiasDirection] = None
    
    # Metadata
    sources: List[str] = field(default_factory=list)
    expiry: datetime = None
    updated: datetime = None
    
    # Blocking
    should_block_buys: bool = False
    should_block_sells: bool = False
    block_reason: str = ""
    
    def is_active(self) -> bool:
        """Check if bias is still active"""
        if self.expiry is None:
            return False
        return datetime.utcnow() < self.expiry
    
    def to_dict(self) -> Dict:
        return {
            'pair': self.pair,
            'direction': self.direction.name,
            'strength': self.strength.name,
            'confidence_adjustment': self.confidence_adjustment,
            'data_bias': self.data_bias.name if self.data_bias else None,
            'central_bank_bias': self.central_bank_bias.name if self.central_bank_bias else None,
            'fiscal_bias': self.fiscal_bias.name if self.fiscal_bias else None,
            'sources': self.sources,
            'expiry': self.expiry.isoformat() if self.expiry else None,
            'updated': self.updated.isoformat() if self.updated else None,
            'should_block_buys': self.should_block_buys,
            'should_block_sells': self.should_block_sells,
            'block_reason': self.block_reason,
        }


class BiasManager:
    """
    Central manager for all trading biases.
    
    Combines:
    1. Economic data release surprises
    2. Central bank statement sentiment
    3. Fiscal policy analysis
    
    Provides unified interface for live trading system.
    """
    
    # Source weights for combining biases
    SOURCE_WEIGHTS = {
        'data_release': 0.50,      # Economic surprises most immediate
        'central_bank': 0.35,      # Policy direction important
        'fiscal': 0.15,            # Slower-moving, background
    }
    
    def __init__(
        self,
        fred_api_key: str = None,
        log_dir: str = None,
        auto_update_interval: int = 300  # 5 minutes
    ):
        """
        Initialize bias manager.
        
        Args:
            fred_api_key: API key for FRED economic data
            log_dir: Directory for logs
            auto_update_interval: Seconds between auto-updates
        """
        # Initialize analyzers
        self.calendar = EconomicCalendar()
        self.data_analyzer = DataReleaseAnalyzer(fred_api_key)
        self.central_bank = CentralBankAnalyzer()
        self.government = GovernmentAnalyzer()
        
        # Unified biases per pair
        self.pair_biases: Dict[str, UnifiedBias] = {}
        
        # Timing
        self.auto_update_interval = auto_update_interval
        self.last_update: Optional[datetime] = None
        
        # Logging
        self.log_dir = Path(log_dir) if log_dir else Path(LOGGING.log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.bias_log = self.log_dir / LOGGING.bias_log
        
        # Tracked pairs
        self.tracked_pairs = [
            'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF',
            'AUDUSD', 'USDCAD', 'NZDUSD', 'EURGBP'
        ]
    
    def update(self, force: bool = False) -> Dict[str, UnifiedBias]:
        """
        Update all biases.
        
        Args:
            force: Force update even if interval not elapsed
            
        Returns:
            Dict of pair -> UnifiedBias
        """
        now = datetime.utcnow()
        
        # Check if update needed
        if not force and self.last_update:
            elapsed = (now - self.last_update).total_seconds()
            if elapsed < self.auto_update_interval:
                return self.pair_biases
        
        # Update calendar
        self.calendar.update()
        
        # Update central bank analysis (less frequent)
        if force or self.last_update is None or \
           (now - self.last_update).total_seconds() > 900:  # 15 min
            self.central_bank.analyze_recent_statements(hours_back=48)
        
        # Update government analysis
        if force or self.last_update is None or \
           (now - self.last_update).total_seconds() > 1800:  # 30 min
            for currency in ['USD', 'EUR', 'GBP']:
                self.government.analyze_fiscal_news(currency)
        
        # Calculate unified biases for each pair
        for pair in self.tracked_pairs:
            self.pair_biases[pair] = self._calculate_unified_bias(pair)
        
        self.last_update = now
        
        # Log state
        self._log_biases()
        
        # Cleanup expired
        self._cleanup_expired()
        
        return self.pair_biases
    
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
        
        Call this when actual values are released to generate immediate bias.
        
        Args:
            event_name: Name of the event (e.g., 'Non-Farm Payrolls')
            currency: Currency affected
            actual: Actual released value
            forecast: Consensus forecast
            previous: Previous value (optional)
            
        Returns:
            DataSurprise with bias info
        """
        from .data_sources.forexfactory import EconomicEvent
        from .config import ImpactLevel
        
        # Create event object
        event = EconomicEvent(
            datetime_utc=datetime.utcnow(),
            currency=currency.upper(),
            event_name=event_name,
            impact=ImpactLevel.HIGH,  # Assume high if being processed
            forecast=forecast,
            previous=previous,
            actual=actual
        )
        
        # Analyze
        surprise = self.data_analyzer.analyze_release(event)
        
        if surprise:
            # Update unified biases for affected pairs
            affected_pairs = CURRENCY_MAPPING.get(currency.upper(), [])
            for pair in affected_pairs:
                if pair in self.tracked_pairs:
                    self.pair_biases[pair] = self._calculate_unified_bias(pair)
            
            self._log_biases()
        
        return surprise
    
    def get_bias(self, pair: str) -> UnifiedBias:
        """
        Get current unified bias for a pair.
        
        Args:
            pair: Currency pair (e.g., 'EURUSD' or 'EURUSD.sim')
            
        Returns:
            UnifiedBias for the pair
        """
        pair_clean = pair.replace('.sim', '').upper()
        
        if pair_clean not in self.pair_biases:
            return self._create_neutral_bias(pair_clean)
        
        bias = self.pair_biases[pair_clean]
        
        if not bias.is_active():
            return self._create_neutral_bias(pair_clean)
        
        return bias
    
    def is_trade_allowed(
        self,
        pair: str,
        direction: str  # 'BUY' or 'SELL'
    ) -> Tuple[bool, str]:
        """
        Check if a trade is allowed based on current biases.
        
        Args:
            pair: Currency pair
            direction: Trade direction
            
        Returns:
            (is_allowed, reason_if_blocked)
        """
        pair_clean = pair.replace('.sim', '').upper()
        
        # Check calendar blocking first
        calendar_allowed, calendar_reason = self.calendar.is_trading_allowed(pair_clean)
        if not calendar_allowed:
            return False, calendar_reason
        
        # Check bias blocking
        bias = self.get_bias(pair_clean)
        
        if direction.upper() == 'BUY' and bias.should_block_buys:
            return False, bias.block_reason
        
        if direction.upper() == 'SELL' and bias.should_block_sells:
            return False, bias.block_reason
        
        return True, ""
    
    def get_confidence_adjustment(self, pair: str, direction: str) -> float:
        """
        Get confidence adjustment for a trade.
        
        Positive = bias supports trade direction
        Negative = bias opposes trade direction
        
        Args:
            pair: Currency pair
            direction: Trade direction ('BUY' or 'SELL')
            
        Returns:
            Confidence adjustment (-0.15 to +0.15)
        """
        bias = self.get_bias(pair)
        
        if bias.direction == BiasDirection.NEUTRAL:
            return 0.0
        
        trade_is_bullish = direction.upper() == 'BUY'
        bias_is_bullish = bias.direction == BiasDirection.BULLISH
        
        if trade_is_bullish == bias_is_bullish:
            # Trade aligns with bias - boost confidence
            return abs(bias.confidence_adjustment)
        else:
            # Trade opposes bias - reduce confidence
            return -abs(bias.confidence_adjustment)
    
    def _calculate_unified_bias(self, pair: str) -> UnifiedBias:
        """Calculate combined bias for a pair"""
        pair_clean = pair.replace('.sim', '').upper()
        
        # Get component biases
        data_dir, data_strength, data_adj = self.data_analyzer.get_bias_for_pair(pair_clean)
        cb_dir, cb_adj = self.central_bank.get_bias_for_pair(pair_clean)
        fiscal_dir, fiscal_adj = self.government.get_bias_for_pair(pair_clean)
        
        # Combine with weights
        sources = []
        
        # Convert directions to scores (-1, 0, 1)
        scores = []
        
        if data_dir != BiasDirection.NEUTRAL:
            score = 1 if data_dir == BiasDirection.BULLISH else -1
            scores.append(score * self.SOURCE_WEIGHTS['data_release'])
            sources.append(f"data:{data_dir.name}")
        
        if cb_dir != BiasDirection.NEUTRAL:
            score = 1 if cb_dir == BiasDirection.BULLISH else -1
            scores.append(score * self.SOURCE_WEIGHTS['central_bank'])
            sources.append(f"central_bank:{cb_dir.name}")
        
        if fiscal_dir != BiasDirection.NEUTRAL:
            score = 1 if fiscal_dir == BiasDirection.BULLISH else -1
            scores.append(score * self.SOURCE_WEIGHTS['fiscal'])
            sources.append(f"fiscal:{fiscal_dir.name}")
        
        # Calculate weighted direction
        if not scores:
            return self._create_neutral_bias(pair_clean)
        
        total_score = sum(scores)
        
        # Determine direction
        if total_score > 0.2:
            direction = BiasDirection.BULLISH
        elif total_score < -0.2:
            direction = BiasDirection.BEARISH
        else:
            direction = BiasDirection.NEUTRAL
        
        # Determine strength (use strongest component)
        strength = data_strength if data_strength else BiasStrength.WEAK
        
        # Calculate confidence adjustment
        confidence_adj = data_adj + cb_adj + fiscal_adj
        confidence_adj = max(-0.15, min(0.15, confidence_adj))  # Cap at ±15%
        
        # Determine blocking
        should_block_buys = False
        should_block_sells = False
        block_reason = ""
        
        if strength == BiasStrength.STRONG:
            if direction == BiasDirection.BEARISH:
                should_block_buys = True
                block_reason = f"Strong bearish bias for {pair_clean}"
            elif direction == BiasDirection.BULLISH:
                should_block_sells = True
                block_reason = f"Strong bullish bias for {pair_clean}"
        
        # Calculate expiry (use longest active bias)
        expiry = datetime.utcnow() + timedelta(hours=4)  # Default 4 hours
        
        active_surprises = self.data_analyzer.get_active_surprises()
        for surprise in active_surprises:
            if surprise.currency in pair_clean:
                if surprise.bias_expiry > expiry:
                    expiry = surprise.bias_expiry
        
        return UnifiedBias(
            pair=pair_clean,
            direction=direction,
            strength=strength,
            confidence_adjustment=round(confidence_adj, 4),
            data_bias=data_dir if data_dir != BiasDirection.NEUTRAL else None,
            central_bank_bias=cb_dir if cb_dir != BiasDirection.NEUTRAL else None,
            fiscal_bias=fiscal_dir if fiscal_dir != BiasDirection.NEUTRAL else None,
            sources=sources,
            expiry=expiry,
            updated=datetime.utcnow(),
            should_block_buys=should_block_buys,
            should_block_sells=should_block_sells,
            block_reason=block_reason
        )
    
    def _create_neutral_bias(self, pair: str) -> UnifiedBias:
        """Create neutral bias for a pair"""
        return UnifiedBias(
            pair=pair,
            direction=BiasDirection.NEUTRAL,
            strength=BiasStrength.WEAK,
            confidence_adjustment=0.0,
            sources=[],
            expiry=datetime.utcnow() + timedelta(hours=1),
            updated=datetime.utcnow()
        )
    
    def _log_biases(self):
        """Log current biases to file"""
        try:
            data = {
                'updated': datetime.utcnow().isoformat(),
                'biases': {
                    pair: bias.to_dict()
                    for pair, bias in self.pair_biases.items()
                }
            }
            
            with open(self.bias_log, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            print(f"[BiasManager] Log error: {e}")
    
    def _cleanup_expired(self):
        """Cleanup expired biases from all analyzers"""
        self.central_bank.cleanup_expired()
        self.government.cleanup_expired()
        self.data_analyzer._cleanup_expired()
    
    def get_summary(self) -> str:
        """Get human-readable summary of all biases"""
        lines = ["=" * 60]
        lines.append("NEWS ANALYSIS BIAS SUMMARY")
        lines.append("=" * 60)
        lines.append(f"Last Update: {self.last_update}")
        lines.append("")
        
        # Calendar status
        lines.append("--- Economic Calendar ---")
        blocked = list(self.calendar.state.blocked_pairs)
        if blocked:
            lines.append(f"BLOCKED PAIRS: {', '.join(blocked)}")
        else:
            lines.append("No trading blocks active")
        
        # Pair biases
        lines.append("\n--- Pair Biases ---")
        for pair, bias in sorted(self.pair_biases.items()):
            if bias.direction != BiasDirection.NEUTRAL:
                lines.append(
                    f"{pair}: {bias.direction.name} [{bias.strength.name}] "
                    f"adj={bias.confidence_adjustment:+.1%}"
                )
                if bias.should_block_buys or bias.should_block_sells:
                    blocks = []
                    if bias.should_block_buys:
                        blocks.append("BUYS")
                    if bias.should_block_sells:
                        blocks.append("SELLS")
                    lines.append(f"  BLOCKING: {', '.join(blocks)}")
        
        if not any(b.direction != BiasDirection.NEUTRAL for b in self.pair_biases.values()):
            lines.append("All pairs neutral")
        
        lines.append("=" * 60)
        return "\n".join(lines)
