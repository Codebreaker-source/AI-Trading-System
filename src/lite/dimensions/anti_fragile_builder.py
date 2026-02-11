"""
Anti-Fragile Position Builder - Phase 6 Ultimate Synthesis
==========================================================

Implements probe-first position building strategy:
- Enter with PROBE position (20% of target)
- Add at R-levels (0.3R, 0.6R, 1.0R, 1.5R) if dimensions still agree
- Full size only when market PROVES you right

Key Principle: Let winners prove themselves before committing capital.

Integration with existing system:
- Uses DimensionChecker for re-validation before adds
- Uses DangerScorer for size multiplier adjustments
- Respects existing BE/pullback requirements
- Works with TradeHistoryTracker for system stress awareness

Author: AI Trading System
Version: 1.0
Date: 2025-12-16
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum
import logging


class BuildStage(Enum):
    """Position building stages"""
    PROBE = "PROBE"           # Initial entry (20%)
    ADD_03R = "ADD_0.3R"      # First add at 0.3R (40%)
    ADD_06R = "ADD_0.6R"      # Second add at 0.6R (60%)
    ADD_10R = "ADD_1.0R"      # Third add at 1.0R (80%)
    ADD_15R = "ADD_1.5R"      # Fourth add at 1.5R (100%)
    COMPLETE = "COMPLETE"     # Fully built


@dataclass
class BuildPlan:
    """
    Build plan for a single position.
    
    Tracks the intended build stages and progress.
    """
    symbol: str
    direction: str  # BUY or SELL
    entry_price: float
    sl_price: float
    tp_price: float
    
    # Lot sizing
    probe_lot: float = 0.01
    target_lot: float = 0.05
    add_lot: float = 0.01
    
    # Current state
    current_stage: BuildStage = BuildStage.PROBE
    current_lot: float = 0.01
    
    # Entry conditions (saved for re-validation)
    entry_dimension_count: int = 0
    entry_danger_score: int = 0
    entry_confluence: float = 0.0
    entry_timestamp: datetime = field(default_factory=datetime.now)
    
    # Stage tracking
    stages_completed: List[str] = field(default_factory=list)
    stages_skipped: List[str] = field(default_factory=list)
    
    # R-level triggers (fraction of risk)
    r_triggers: Dict[str, float] = field(default_factory=lambda: {
        'ADD_0.3R': 0.3,
        'ADD_0.6R': 0.6,
        'ADD_1.0R': 1.0,
        'ADD_1.5R': 1.5
    })
    
    def __post_init__(self):
        """Initialize stages_completed if not set"""
        if not self.stages_completed:
            self.stages_completed = ['PROBE']
    
    @property
    def risk_pips(self) -> float:
        """Calculate risk in pips from entry to SL"""
        pip_value = 0.01 if 'JPY' in self.symbol else 0.0001
        if self.direction.upper() == 'BUY':
            return abs(self.entry_price - self.sl_price) / pip_value
        else:
            return abs(self.sl_price - self.entry_price) / pip_value
    
    @property
    def reward_pips(self) -> float:
        """Calculate reward in pips from entry to TP"""
        pip_value = 0.01 if 'JPY' in self.symbol else 0.0001
        if self.direction.upper() == 'BUY':
            return abs(self.tp_price - self.entry_price) / pip_value
        else:
            return abs(self.entry_price - self.tp_price) / pip_value
    
    @property
    def build_progress(self) -> float:
        """Returns build progress as percentage (0.0 to 1.0)"""
        return self.current_lot / self.target_lot
    
    @property
    def is_complete(self) -> bool:
        """Check if position is fully built"""
        return self.current_stage == BuildStage.COMPLETE
    
    def get_next_stage(self) -> Optional[BuildStage]:
        """Get the next build stage"""
        stage_order = [
            BuildStage.PROBE,
            BuildStage.ADD_03R,
            BuildStage.ADD_06R,
            BuildStage.ADD_10R,
            BuildStage.ADD_15R,
            BuildStage.COMPLETE
        ]
        
        try:
            current_idx = stage_order.index(self.current_stage)
            if current_idx < len(stage_order) - 1:
                return stage_order[current_idx + 1]
        except ValueError:
            pass
        
        return None
    
    def get_r_trigger_for_stage(self, stage: BuildStage) -> float:
        """Get the R-level trigger for a specific stage"""
        stage_name = stage.value.replace('ADD_', '').replace('R', '')
        return self.r_triggers.get(stage.value, 0.0)


@dataclass
class BuildSignal:
    """Signal to add to a position"""
    symbol: str
    direction: str
    lot_size: float
    stage: BuildStage
    current_r: float
    reason: str
    dimension_count: int
    danger_score: int
    confluence_score: float
    can_build: bool = True


class AntiFragileBuilder:
    """
    Manages anti-fragile position building.
    
    Responsibilities:
    - Create build plans for new positions
    - Track progress of existing build plans
    - Validate conditions for adding to positions
    - Generate build signals when conditions are met
    """
    
    def __init__(
        self,
        probe_lot: float = 0.01,
        target_lot: float = 0.05,
        add_lot: float = 0.01,
        min_dimension_count: int = 3,
        max_danger_score: int = 13,
        require_be_for_add: bool = True,
        logger: logging.Logger = None
    ):
        """
        Initialize position builder.
        
        Args:
            probe_lot: Initial probe position size
            target_lot: Target full position size
            add_lot: Size of each add
            min_dimension_count: Minimum dimensions required for adds
            max_danger_score: Maximum danger score to allow adds
            require_be_for_add: Require position at BE before adding
            logger: Logger instance
        """
        self.probe_lot = probe_lot
        self.target_lot = target_lot
        self.add_lot = add_lot
        self.min_dimension_count = min_dimension_count
        self.max_danger_score = max_danger_score
        self.require_be_for_add = require_be_for_add
        self.logger = logger or logging.getLogger(__name__)
        
        # Active build plans: {symbol: BuildPlan}
        self.build_plans: Dict[str, BuildPlan] = {}
        
        # R-level triggers
        self.r_triggers = {
            BuildStage.ADD_03R: 0.3,
            BuildStage.ADD_06R: 0.6,
            BuildStage.ADD_10R: 1.0,
            BuildStage.ADD_15R: 1.5
        }
    
    def create_build_plan(
        self,
        symbol: str,
        direction: str,
        entry_price: float,
        sl_price: float,
        tp_price: float,
        dimension_count: int,
        danger_score: int,
        confluence_score: float,
        size_multiplier: float = 1.0
    ) -> BuildPlan:
        """
        Create a new build plan for a position.
        
        Args:
            symbol: Trading symbol
            direction: BUY or SELL
            entry_price: Entry price
            sl_price: Stop loss price
            tp_price: Take profit price
            dimension_count: Number of agreeing dimensions at entry
            danger_score: Danger score at entry
            confluence_score: Confluence score at entry
            size_multiplier: Danger-based size multiplier (0.0-1.0)
            
        Returns:
            BuildPlan instance
        """
        # Apply size multiplier to lot sizes
        adjusted_probe = self.probe_lot  # Probe always minimum
        adjusted_target = self.target_lot * size_multiplier
        adjusted_add = self.add_lot * size_multiplier
        
        # Ensure minimum lot sizes
        adjusted_target = max(adjusted_target, self.probe_lot)
        adjusted_add = max(adjusted_add, self.probe_lot)
        
        plan = BuildPlan(
            symbol=symbol,
            direction=direction,
            entry_price=entry_price,
            sl_price=sl_price,
            tp_price=tp_price,
            probe_lot=adjusted_probe,
            target_lot=adjusted_target,
            add_lot=adjusted_add,
            current_stage=BuildStage.PROBE,
            current_lot=adjusted_probe,
            entry_dimension_count=dimension_count,
            entry_danger_score=danger_score,
            entry_confluence=confluence_score,
            entry_timestamp=datetime.now()
        )
        
        # Store plan
        self.build_plans[symbol] = plan
        
        self.logger.info(
            f"[BUILD] Created plan: {symbol} {direction} | "
            f"Probe: {adjusted_probe} → Target: {adjusted_target} | "
            f"Dims: {dimension_count}, Danger: {danger_score}"
        )
        
        return plan
    
    def get_build_plan(self, symbol: str) -> Optional[BuildPlan]:
        """Get existing build plan for a symbol"""
        return self.build_plans.get(symbol)
    
    def remove_build_plan(self, symbol: str):
        """Remove build plan (position closed)"""
        if symbol in self.build_plans:
            plan = self.build_plans.pop(symbol)
            self.logger.info(
                f"[BUILD] Removed plan: {symbol} | "
                f"Progress: {plan.build_progress:.0%} | "
                f"Stage: {plan.current_stage.value}"
            )
    
    def calculate_current_r(
        self,
        symbol: str,
        current_price: float,
        plan: BuildPlan
    ) -> float:
        """
        Calculate current R-multiple (profit in terms of risk).
        
        R = 1.0 means price moved equal to risk distance.
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            plan: Build plan for the position
            
        Returns:
            Current R-multiple (can be negative if in loss)
        """
        pip_value = 0.01 if 'JPY' in symbol else 0.0001
        
        # Risk in price terms
        risk_distance = abs(plan.entry_price - plan.sl_price)
        
        if risk_distance == 0:
            return 0.0
        
        # Current profit in price terms
        if plan.direction.upper() == 'BUY':
            profit_distance = current_price - plan.entry_price
        else:
            profit_distance = plan.entry_price - current_price
        
        return profit_distance / risk_distance
    
    def check_build_opportunity(
        self,
        symbol: str,
        current_price: float,
        is_at_be: bool,
        current_dimension_count: int,
        current_danger_score: int,
        current_confluence: float
    ) -> Optional[BuildSignal]:
        """
        Check if conditions are met to add to a position.
        
        Validation checks:
        1. Build plan exists and not complete
        2. R-level trigger reached
        3. Position at breakeven (if required)
        4. Dimension count >= entry dimension count
        5. Danger score < max threshold
        6. Confluence still adequate
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            is_at_be: Whether position is at breakeven
            current_dimension_count: Current dimension agreement count
            current_danger_score: Current danger score
            current_confluence: Current confluence score
            
        Returns:
            BuildSignal if add is recommended, None otherwise
        """
        plan = self.build_plans.get(symbol)
        
        if not plan:
            return None
        
        if plan.is_complete:
            return None
        
        # Calculate current R
        current_r = self.calculate_current_r(symbol, current_price, plan)
        
        # Get next stage
        next_stage = plan.get_next_stage()
        if not next_stage or next_stage == BuildStage.COMPLETE:
            return None
        
        # Get R trigger for next stage
        r_trigger = self.r_triggers.get(next_stage, 0.0)
        
        # Check 1: R-level reached?
        if current_r < r_trigger:
            return None  # Not at trigger level yet
        
        # Check 2: At breakeven? (if required)
        if self.require_be_for_add and not is_at_be:
            return BuildSignal(
                symbol=symbol,
                direction=plan.direction,
                lot_size=0,
                stage=next_stage,
                current_r=current_r,
                reason=f"R-level {r_trigger} reached but not at BE",
                dimension_count=current_dimension_count,
                danger_score=current_danger_score,
                confluence_score=current_confluence,
                can_build=False
            )
        
        # Check 3: Dimensions still agree?
        if current_dimension_count < plan.entry_dimension_count:
            plan.stages_skipped.append(f"{next_stage.value}:dims_degraded")
            return BuildSignal(
                symbol=symbol,
                direction=plan.direction,
                lot_size=0,
                stage=next_stage,
                current_r=current_r,
                reason=f"Dimensions degraded: {current_dimension_count} < {plan.entry_dimension_count}",
                dimension_count=current_dimension_count,
                danger_score=current_danger_score,
                confluence_score=current_confluence,
                can_build=False
            )
        
        # Check 4: Danger score acceptable?
        if current_danger_score >= self.max_danger_score:
            plan.stages_skipped.append(f"{next_stage.value}:danger_high")
            return BuildSignal(
                symbol=symbol,
                direction=plan.direction,
                lot_size=0,
                stage=next_stage,
                current_r=current_r,
                reason=f"Danger too high: {current_danger_score} >= {self.max_danger_score}",
                dimension_count=current_dimension_count,
                danger_score=current_danger_score,
                confluence_score=current_confluence,
                can_build=False
            )
        
        # Check 5: Confluence still adequate?
        min_confluence = plan.entry_confluence * 0.8  # Allow 20% degradation
        if current_confluence < min_confluence:
            plan.stages_skipped.append(f"{next_stage.value}:confluence_low")
            return BuildSignal(
                symbol=symbol,
                direction=plan.direction,
                lot_size=0,
                stage=next_stage,
                current_r=current_r,
                reason=f"Confluence degraded: {current_confluence:.2f} < {min_confluence:.2f}",
                dimension_count=current_dimension_count,
                danger_score=current_danger_score,
                confluence_score=current_confluence,
                can_build=False
            )
        
        # All checks passed - generate build signal
        return BuildSignal(
            symbol=symbol,
            direction=plan.direction,
            lot_size=plan.add_lot,
            stage=next_stage,
            current_r=current_r,
            reason=f"Build at {r_trigger}R: dims={current_dimension_count}, danger={current_danger_score}",
            dimension_count=current_dimension_count,
            danger_score=current_danger_score,
            confluence_score=current_confluence,
            can_build=True
        )
    
    def execute_build(self, symbol: str, stage: BuildStage) -> bool:
        """
        Mark a build stage as executed.
        
        Args:
            symbol: Trading symbol
            stage: Stage that was executed
            
        Returns:
            True if successful
        """
        plan = self.build_plans.get(symbol)
        
        if not plan:
            return False
        
        # Update plan
        plan.current_stage = stage
        plan.current_lot += plan.add_lot
        plan.stages_completed.append(stage.value)
        
        # Check if complete
        if plan.current_lot >= plan.target_lot:
            plan.current_stage = BuildStage.COMPLETE
        
        self.logger.info(
            f"[BUILD] Executed {stage.value}: {symbol} | "
            f"Now: {plan.current_lot:.2f} / {plan.target_lot:.2f} "
            f"({plan.build_progress:.0%})"
        )
        
        return True
    
    def get_probe_lot_for_signal(
        self,
        size_multiplier: float = 1.0
    ) -> float:
        """
        Get the probe lot size for a new position.
        
        For anti-fragile entry, always use probe size regardless of multiplier.
        The multiplier affects the TARGET, not the probe.
        
        Args:
            size_multiplier: Danger-based size multiplier (for target calculation)
            
        Returns:
            Probe lot size (always minimum)
        """
        return self.probe_lot
    
    def get_all_build_plans(self) -> Dict[str, BuildPlan]:
        """Get all active build plans"""
        return self.build_plans.copy()
    
    def get_build_summary(self) -> str:
        """Get summary of all build plans"""
        if not self.build_plans:
            return "[BUILD] No active build plans"
        
        lines = ["[BUILD] Active Plans:"]
        for symbol, plan in self.build_plans.items():
            lines.append(
                f"  {symbol}: {plan.current_stage.value} | "
                f"{plan.current_lot:.2f}/{plan.target_lot:.2f} ({plan.build_progress:.0%}) | "
                f"Entry dims: {plan.entry_dimension_count}"
            )
        
        return "\n".join(lines)
    
    def sync_with_positions(self, open_positions: Dict[str, Dict]):
        """
        Sync build plans with actual open positions.
        
        Removes build plans for positions that no longer exist.
        
        Args:
            open_positions: Current open positions from EA
        """
        symbols_to_remove = []
        
        for symbol in self.build_plans:
            if symbol not in open_positions:
                symbols_to_remove.append(symbol)
        
        for symbol in symbols_to_remove:
            self.remove_build_plan(symbol)
            self.logger.info(f"[BUILD] Synced: removed plan for closed position {symbol}")


# Test function
def _test_position_builder():
    """Test position builder functionality"""
    print("=" * 60)
    print("ANTI-FRAGILE BUILDER TEST")
    print("=" * 60)
    
    builder = AntiFragileBuilder(
        probe_lot=0.01,
        target_lot=0.05,
        add_lot=0.01
    )
    
    # Test 1: Create build plan
    print("\n--- Test 1: Create Build Plan ---")
    plan = builder.create_build_plan(
        symbol="EURUSD.sim",
        direction="BUY",
        entry_price=1.0500,
        sl_price=1.0450,  # 50 pip SL
        tp_price=1.0600,  # 100 pip TP (2:1 R:R)
        dimension_count=4,
        danger_score=5,
        confluence_score=0.65,
        size_multiplier=0.80
    )
    
    print(f"Plan created: {plan.symbol}")
    print(f"  Probe: {plan.probe_lot}, Target: {plan.target_lot}")
    print(f"  Risk: {plan.risk_pips:.1f} pips, Reward: {plan.reward_pips:.1f} pips")
    print(f"  Entry dims: {plan.entry_dimension_count}")
    
    # Test 2: Check build at various R levels
    print("\n--- Test 2: Check Build Opportunities ---")
    
    test_prices = [
        (1.0515, False, "At 0.3R, no BE"),
        (1.0515, True, "At 0.3R, at BE"),
        (1.0530, True, "At 0.6R, at BE"),
        (1.0550, True, "At 1.0R, at BE"),
        (1.0575, True, "At 1.5R, at BE"),
    ]
    
    for price, is_be, desc in test_prices:
        current_r = builder.calculate_current_r("EURUSD.sim", price, plan)
        
        signal = builder.check_build_opportunity(
            symbol="EURUSD.sim",
            current_price=price,
            is_at_be=is_be,
            current_dimension_count=4,
            current_danger_score=5,
            current_confluence=0.60
        )
        
        print(f"\n{desc} (R={current_r:.2f}):")
        if signal:
            print(f"  Can build: {signal.can_build}")
            print(f"  Stage: {signal.stage.value}")
            print(f"  Reason: {signal.reason}")
            
            if signal.can_build:
                builder.execute_build("EURUSD.sim", signal.stage)
                print(f"  -> Executed! Now at {plan.build_progress:.0%}")
    
    # Test 3: Dimension degradation
    print("\n--- Test 3: Dimension Degradation ---")
    signal = builder.check_build_opportunity(
        symbol="EURUSD.sim",
        current_price=1.0590,
        is_at_be=True,
        current_dimension_count=2,  # Degraded from 4
        current_danger_score=5,
        current_confluence=0.60
    )
    
    if signal:
        print(f"Can build: {signal.can_build}")
        print(f"Reason: {signal.reason}")
    
    # Test 4: Summary
    print("\n--- Test 4: Build Summary ---")
    print(builder.get_build_summary())
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    _test_position_builder()
