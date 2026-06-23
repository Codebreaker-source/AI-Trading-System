"""
Risk Manager - Portfolio Risk Tracking
======================================

Tracks risk across all open positions:
- Max total portfolio risk: 2% of account ($200 on $10K)
- Each trade: 0.01 lots
- Calculates available risk budget for new positions

All trades are 0.01 lots - no exceptions.
Scale IN = Add another 0.01 lot position
Scale OUT = Close one 0.01 lot position
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

# Optional MT5 — used to derive exact per-symbol tick_size/tick_value so risk
# is priced correctly for FX, metals, indices, energy, crypto and exotics.
# Falls back to the forex pip tables below when MT5 is unavailable.
try:
    import MetaTrader5 as mt5
    _MT5_AVAILABLE = True
except Exception:
    _MT5_AVAILABLE = False


@dataclass
class PositionRisk:
    """Risk information for a single position"""
    symbol: str
    direction: str  # 'BUY' or 'SELL'
    entry_price: float
    stop_loss: float
    lot_size: float  # Always 0.01
    risk_amount: float  # Dollar risk
    risk_percent: float  # Percent of account
    opened_at: datetime
    position_id: str
    
    def __str__(self) -> str:
        return f"{self.symbol} {self.direction} @ {self.entry_price:.5f} | Risk: ${self.risk_amount:.2f} ({self.risk_percent:.2%})"


@dataclass
class PortfolioRisk:
    """Current portfolio risk status"""
    total_risk_amount: float
    total_risk_percent: float
    available_risk_amount: float
    available_risk_percent: float
    position_count: int
    max_new_positions: int
    can_open_new: bool
    positions_by_symbol: Dict[str, int]
    details: Dict[str, Any]
    
    def __str__(self) -> str:
        return (f"Portfolio Risk: ${self.total_risk_amount:.2f} ({self.total_risk_percent:.2%}) | "
                f"Available: ${self.available_risk_amount:.2f} | "
                f"Positions: {self.position_count}")


class RiskManager:
    """
    Portfolio risk management system.
    
    Tracks all open positions and their risk contribution.
    Ensures total portfolio risk never exceeds 2% of account.
    
    Key Rules:
    - All trades are 0.01 lots - no exceptions
    - Max portfolio risk: 2% ($200 on $10K)
    - Each position risk calculated from entry to stop loss
    """
    
    def __init__(
        self,
        account_balance: float = 10000.0,
        max_portfolio_risk_percent: float = 0.02,
        default_lot_size: float = 0.01,
        max_positions_per_symbol: int = 3,
        pip_values: Optional[Dict[str, float]] = None
    ):
        self.account_balance = account_balance
        self.max_portfolio_risk_percent = max_portfolio_risk_percent
        self.default_lot_size = default_lot_size
        self.max_positions_per_symbol = max_positions_per_symbol
        
        self.max_risk_amount = account_balance * max_portfolio_risk_percent
        
        self.pip_values = pip_values or {
            'EURUSD': 0.0001, 'GBPUSD': 0.0001, 'USDJPY': 0.01, 'USDCHF': 0.0001,
            'AUDUSD': 0.0001, 'USDCAD': 0.0001, 'NZDUSD': 0.0001, 'EURGBP': 0.0001,
            'EURUSD.sim': 0.0001, 'GBPUSD.sim': 0.0001, 'USDJPY.sim': 0.01, 'USDCHF.sim': 0.0001,
            'AUDUSD.sim': 0.0001, 'USDCAD.sim': 0.0001, 'NZDUSD.sim': 0.0001, 'EURGBP.sim': 0.0001,
        }
        
        self.pip_dollar_values = {
            'EURUSD': 10.0, 'GBPUSD': 10.0, 'USDJPY': 6.7, 'USDCHF': 10.5,
            'AUDUSD': 10.0, 'USDCAD': 7.5, 'NZDUSD': 10.0, 'EURGBP': 12.5,
            'EURUSD.sim': 10.0, 'GBPUSD.sim': 10.0, 'USDJPY.sim': 6.7, 'USDCHF.sim': 10.5,
            'AUDUSD.sim': 10.0, 'USDCAD.sim': 7.5, 'NZDUSD.sim': 10.0, 'EURGBP.sim': 12.5,
        }
        
        self.open_positions: Dict[str, PositionRisk] = {}
        self._position_counter = 0

        # Cache of successful MT5 (tick_size, tick_value) lookups per symbol.
        self._tick_spec_cache: Dict[str, Tuple[float, float]] = {}

    def _get_risk_spec(self, symbol: str) -> Tuple[float, float]:
        """
        Return (price_unit, dollar_per_unit_per_lot) for risk math:

            risk = (abs(entry - sl) / price_unit) * dollar_per_unit * lot_size

        Prefers live MT5 trade_tick_size / trade_tick_value, which is exact for
        every instrument class (FX, metals, indices, energy, crypto, exotics)
        and already converted to the account currency. Falls back to the forex
        pip tables (then forex defaults) when MT5 is unavailable or the symbol
        has no contract spec — e.g. running without a terminal attached.

        NOTE: with MT5 specs, price_unit == tick_size and dollar_per_unit ==
        tick_value, so the legacy 'pip_value/pip_dollar' formula is unchanged.
        """
        # 1) Live MT5 contract spec (cached after first success)
        cached = self._tick_spec_cache.get(symbol)
        if cached is not None:
            return cached
        if _MT5_AVAILABLE:
            try:
                info = mt5.symbol_info(symbol)
            except Exception:
                info = None
            if info is not None:
                tick_size = float(getattr(info, 'trade_tick_size', 0.0) or 0.0)
                tick_value = float(getattr(info, 'trade_tick_value', 0.0) or 0.0)
                if tick_size > 0.0 and tick_value > 0.0:
                    spec = (tick_size, tick_value)
                    self._tick_spec_cache[symbol] = spec
                    return spec

        # 2) Forex pip tables (fallback) — strip broker suffix to match keys
        symbol_clean = symbol.replace('.sim', '')
        pip_value = self.pip_values.get(symbol, self.pip_values.get(symbol_clean, 0.0001))
        pip_dollar = self.pip_dollar_values.get(symbol, self.pip_dollar_values.get(symbol_clean, 10.0))
        return float(pip_value), float(pip_dollar)

    def calculate_position_risk(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        lot_size: float = 0.01
    ) -> Tuple[float, float]:
        """
        Calculate risk for a potential position.
        
        Args:
            symbol: Trading symbol
            direction: 'BUY' or 'SELL'
            entry_price: Entry price
            stop_loss: Stop loss price
            lot_size: Position size (always 0.01)
            
        Returns:
            Tuple of (risk_amount_dollars, risk_percent)
        """
        # Option A: exact per-symbol tick spec from MT5 (forex table fallback)
        pip_value, pip_dollar = self._get_risk_spec(symbol)

        # v2.33 FIX: Check for zero-risk positions (SL at/beyond entry)
        if direction.upper() == 'BUY' and stop_loss >= entry_price:
            return 0.0, 0.0  # Zero risk for scale-in with SL at/above entry
        elif direction.upper() == 'SELL' and stop_loss <= entry_price:
            return 0.0, 0.0  # Zero risk for scale-in with SL at/below entry
        
        if direction.upper() == 'BUY':
            price_diff = entry_price - stop_loss
        else:
            price_diff = stop_loss - entry_price
        
        pips_at_risk = abs(price_diff) / pip_value
        
        # FIX: pip_dollar is per standard lot (1.0), so multiply by lot_size directly
        risk_amount = pips_at_risk * pip_dollar * lot_size
        risk_percent = risk_amount / self.account_balance
        
        return float(risk_amount), float(risk_percent)
    
    def can_open_position(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        lot_size: float = 0.01
    ) -> Tuple[bool, str]:
        """
        Check if a new position can be opened within risk limits.
        
        Args:
            symbol: Trading symbol
            direction: 'BUY' or 'SELL'
            entry_price: Entry price
            stop_loss: Stop loss price
            lot_size: Position size (always 0.01)
            
        Returns:
            Tuple of (can_open, reason)
        """
        risk_amount, risk_percent = self.calculate_position_risk(
            symbol, direction, entry_price, stop_loss, lot_size
        )
        
        current_risk = self._get_total_risk_amount()
        new_total_risk = current_risk + risk_amount
        
        if new_total_risk > self.max_risk_amount:
            return False, (
                f"Would exceed max portfolio risk: "
                f"${new_total_risk:.2f} > ${self.max_risk_amount:.2f} "
                f"(Current: ${current_risk:.2f}, New: ${risk_amount:.2f})"
            )
        
        symbol_clean = symbol.replace('.sim', '')
        symbol_positions = sum(
            1 for pos in self.open_positions.values()
            if pos.symbol.replace('.sim', '') == symbol_clean
        )
        
        if symbol_positions >= self.max_positions_per_symbol:
            return False, (
                f"Max positions per symbol reached: "
                f"{symbol_positions} >= {self.max_positions_per_symbol}"
            )
        
        return True, "OK"
    
    def add_position(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        stop_loss: float,
        lot_size: float = 0.01
    ) -> PositionRisk:
        """
        Add a new position to tracking.
        
        Args:
            symbol: Trading symbol
            direction: 'BUY' or 'SELL'
            entry_price: Entry price
            stop_loss: Stop loss price
            lot_size: Position size (always 0.01)
            
        Returns:
            PositionRisk object for the new position
        """
        risk_amount, risk_percent = self.calculate_position_risk(
            symbol, direction, entry_price, stop_loss, lot_size
        )
        
        self._position_counter += 1
        position_id = f"{symbol}_{direction}_{self._position_counter}"
        
        position = PositionRisk(
            symbol=symbol,
            direction=direction.upper(),
            entry_price=entry_price,
            stop_loss=stop_loss,
            lot_size=lot_size,
            risk_amount=risk_amount,
            risk_percent=risk_percent,
            opened_at=datetime.utcnow(),
            position_id=position_id
        )
        
        self.open_positions[position_id] = position
        
        return position
    
    def remove_position(self, position_id: str) -> Optional[PositionRisk]:
        """
        Remove a position from tracking (closed or stopped out).
        
        Args:
            position_id: Position identifier
            
        Returns:
            Removed PositionRisk or None if not found
        """
        return self.open_positions.pop(position_id, None)
    
    def remove_positions_for_symbol(self, symbol: str, count: int = 1) -> List[PositionRisk]:
        """
        Remove oldest positions for a symbol (for scale out).
        
        Args:
            symbol: Trading symbol
            count: Number of positions to remove
            
        Returns:
            List of removed positions
        """
        symbol_clean = symbol.replace('.sim', '')
        
        symbol_positions = [
            (pos_id, pos) for pos_id, pos in self.open_positions.items()
            if pos.symbol.replace('.sim', '') == symbol_clean
        ]
        
        symbol_positions.sort(key=lambda x: x[1].opened_at)
        
        removed = []
        for i in range(min(count, len(symbol_positions))):
            pos_id, pos = symbol_positions[i]
            if pos_id in self.open_positions:
                removed.append(self.open_positions.pop(pos_id))
        
        return removed
    
    def get_portfolio_risk(self) -> PortfolioRisk:
        """
        Get current portfolio risk status.
        
        Returns:
            PortfolioRisk with complete risk breakdown
        """
        total_risk = self._get_total_risk_amount()
        total_risk_pct = total_risk / self.account_balance
        
        available_risk = max(0, self.max_risk_amount - total_risk)
        available_risk_pct = available_risk / self.account_balance
        
        avg_position_risk = total_risk / len(self.open_positions) if self.open_positions else 20.0
        max_new = int(available_risk / avg_position_risk) if avg_position_risk > 0 else 0
        
        positions_by_symbol: Dict[str, int] = {}
        for pos in self.open_positions.values():
            symbol_clean = pos.symbol.replace('.sim', '')
            positions_by_symbol[symbol_clean] = positions_by_symbol.get(symbol_clean, 0) + 1
        
        return PortfolioRisk(
            total_risk_amount=total_risk,
            total_risk_percent=total_risk_pct,
            available_risk_amount=available_risk,
            available_risk_percent=available_risk_pct,
            position_count=len(self.open_positions),
            max_new_positions=max_new,
            can_open_new=available_risk > 0,
            positions_by_symbol=positions_by_symbol,
            details={
                'account_balance': self.account_balance,
                'max_risk_amount': self.max_risk_amount,
                'max_risk_percent': self.max_portfolio_risk_percent,
                'avg_position_risk': avg_position_risk
            }
        )
    
    def _get_total_risk_amount(self) -> float:
        """Calculate total risk from all open positions."""
        return sum(pos.risk_amount for pos in self.open_positions.values())
    
    def get_positions_for_symbol(self, symbol: str) -> List[PositionRisk]:
        """Get all positions for a specific symbol."""
        symbol_clean = symbol.replace('.sim', '')
        return [
            pos for pos in self.open_positions.values()
            if pos.symbol.replace('.sim', '') == symbol_clean
        ]
    
    def update_account_balance(self, new_balance: float) -> None:
        """
        Update account balance (after realized P&L).
        
        Args:
            new_balance: New account balance
        """
        self.account_balance = new_balance
        self.max_risk_amount = new_balance * self.max_portfolio_risk_percent
    
    def get_scaling_capacity(self, symbol: str) -> Dict[str, Any]:
        """
        Get scaling capacity for a symbol.
        
        Returns info about whether scale in/out is possible.
        """
        symbol_positions = self.get_positions_for_symbol(symbol)
        position_count = len(symbol_positions)
        
        can_scale_in = position_count < self.max_positions_per_symbol
        can_scale_out = position_count > 0
        
        portfolio_risk = self.get_portfolio_risk()
        
        return {
            'symbol': symbol,
            'current_positions': position_count,
            'max_positions': self.max_positions_per_symbol,
            'can_scale_in': can_scale_in and portfolio_risk.can_open_new,
            'can_scale_out': can_scale_out,
            'available_risk': portfolio_risk.available_risk_amount,
            'positions': symbol_positions
        }
    
    def clear_all_positions(self) -> int:
        """Clear all tracked positions. Returns count removed."""
        count = len(self.open_positions)
        self.open_positions.clear()
        return count
    
    def remove_position(self, position_id: str) -> bool:
        """
        Remove a position by ID.
        
        Args:
            position_id: Position ticket/ID to remove
            
        Returns:
            True if removed, False if not found
        """
        if position_id in self.open_positions:
            del self.open_positions[position_id]
            return True
        return False
    
    def add_position(
        self,
        symbol: str,
        direction: str,
        volume: float,
        entry_price: float,
        position_id: str,
        stop_loss: float = 0.0
    ) -> bool:
        """
        Add a position from external sync (MT5).
        
        Args:
            symbol: Trading symbol
            direction: 'BUY' or 'SELL'
            volume: Position volume
            entry_price: Entry price
            position_id: Unique position ID/ticket
            stop_loss: Stop loss price (optional)
            
        Returns:
            True if added, False if already exists
        """
        if position_id in self.open_positions:
            return False
        
        # Calculate risk if SL is provided
        risk_amount = 0.0
        if stop_loss > 0:
            # v2.33 FIX: Check for zero-risk positions (SL at/beyond entry)
            is_zero_risk = False
            if direction.upper() == 'BUY' and stop_loss >= entry_price:
                is_zero_risk = True  # SL above entry = no risk for BUY
            elif direction.upper() == 'SELL' and stop_loss <= entry_price:
                is_zero_risk = True  # SL below entry = no risk for SELL
            
            if is_zero_risk:
                risk_amount = 0.0  # Scale-in with SL at BE = zero additional risk
            else:
                # Option A: exact per-symbol tick spec from MT5 (forex fallback)
                pip_value, pip_dollar = self._get_risk_spec(symbol)
                sl_pips = abs(entry_price - stop_loss) / pip_value
                # FIX: pip_dollar is per standard lot (1.0), so multiply by volume directly
                risk_amount = sl_pips * pip_dollar * volume
        else:
            # Estimate risk as $2 per 0.01 lot if no SL (reasonable for 20 pip average SL)
            risk_amount = 2.0 * (volume / 0.01)
        
        risk_percent = risk_amount / self.account_balance
        
        self.open_positions[position_id] = PositionRisk(
            symbol=symbol,
            direction=direction.upper(),
            entry_price=entry_price,
            stop_loss=stop_loss,
            lot_size=volume,
            risk_amount=risk_amount,
            risk_percent=risk_percent,
            opened_at=datetime.now(),
            position_id=position_id
        )
        
        return True
