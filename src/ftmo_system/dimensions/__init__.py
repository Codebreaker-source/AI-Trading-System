"""
Dimension Checking Module for Ultimate Synthesis Trading System
================================================================

Four complementary systems for trade validation:

1. DIMENSION CHECKER - Should we trade? (Direction validation)
   Checks 4 dimensions: REGIME, SESSION, ML, CONFLUENCE
   Returns: can_trade (YES/NO), count (0-4)

2. DANGER SCORER - How much should we trade? (Position sizing)
   Scores 7 danger categories: Regime, Session, ML, Technical, 
   Stress, Correlation, Event Risk
   Returns: danger_score (0-21), size_multiplier (0-100%)

3. TRADE HISTORY TRACKER - System stress data provider
   Loads from EA's trades_execution_log.csv at startup
   Tracks: drawdown, consecutive losses, daily P&L
   Syncs with CSV every 5 minutes

4. ANTI-FRAGILE BUILDER - Position building strategy (Phase 6)
   Probe-first approach: Enter small, build as market confirms
   Stages: PROBE (0.01) -> 0.3R -> 0.6R -> 1.0R -> COMPLETE (0.05)
   Integrates with dimension/danger checks for add validation

All four work together:
- Dimensions must pass (can_trade=True)
- Danger score determines initial probe size (multiplier)
- Anti-fragile builder manages staged position building
- Each add stage re-validates dimensions + danger

Usage:
    from dimensions import (
        DimensionChecker, DangerScorer, 
        TradeHistoryTracker, AntiFragileBuilder
    )
    
    # Initialize all four
    dim_checker = DimensionChecker()
    history_tracker = TradeHistoryTracker()
    danger_scorer = DangerScorer()
    builder = AntiFragileBuilder(probe_lot=0.01, target_lot=0.05)
    
    # On new signal: create build plan with probe entry
    plan = builder.create_build_plan(symbol, direction, entry, sl, tp, dim_count)
    
    # Periodically: check for build opportunities
    build_signal = builder.check_build_opportunity(
        symbol, current_price, is_at_be, dim_count, danger_score, ...
    )
"""

from .dimension_checker import DimensionChecker, DimensionResult
from .danger_scorer import DangerScorer, DangerResult
from .trade_history_tracker import TradeHistoryTracker, TradeHistoryState
from .anti_fragile_builder import AntiFragileBuilder, BuildPlan, BuildSignal, BuildStage

__all__ = [
    'DimensionChecker', 'DimensionResult',
    'DangerScorer', 'DangerResult',
    'TradeHistoryTracker', 'TradeHistoryState',
    'AntiFragileBuilder', 'BuildPlan', 'BuildSignal', 'BuildStage'
]
