"""
Shared Exit Logic
==================
Pure-Python port of the position-management logic in
ea/BridgeEA_FTMO_v1.mq5 (`ManagePositions()`, ~lines 757-867,
"from v2.29-2.31").

This is the single source of truth for break-even, partial-TP,
regime-adaptive trailing, and progressive-trailing behavior. It is
used by:
  - live_trading_system.py (reading EA-confirmed position state — kept
    behavior-preserving)
  - core/trade_outcome_simulator.py (tick replay, to label simulated
    trades exactly as the live EA would manage them)

All functions are pure (no I/O, no MT5 calls) and operate on plain
numbers/strings so they can be unit tested and reused in replay loops.

`direction` is "BUY" or "SELL" throughout.
"""

from dataclasses import dataclass, field
from typing import Optional


# ----------------------------------------------------------------------
# Regime-adaptive trail multiplier
# ----------------------------------------------------------------------

def compute_regime_trail_multiplier(
    atr: float,
    pip: float,
    enable_regime_trailing: bool,
    trail_atr_multiplier: float,
    trail_atr_ranging: float,
    trail_atr_trending: float,
    trail_atr_volatile: float,
    regime_atr_low_threshold: float,
    regime_atr_high_threshold: float,
) -> float:
    """Mirror of the 'Regime-adaptive trail multiplier' block (~lines 780-787)."""
    trail_mult = trail_atr_multiplier
    if enable_regime_trailing and atr > 0 and pip > 0:
        atr_pips = atr / pip
        if atr_pips < regime_atr_low_threshold:
            trail_mult = trail_atr_ranging
        elif atr_pips > regime_atr_high_threshold:
            trail_mult = trail_atr_volatile
        else:
            trail_mult = trail_atr_trending
    return trail_mult


# ----------------------------------------------------------------------
# RR calculation
# ----------------------------------------------------------------------

def compute_rr_now(entry: float, sl: float, current: float, direction: str) -> Optional[float]:
    """Mirror of the rr_now calc (~lines 789-793). Returns None if sl/entry invalid."""
    if sl <= 0 or entry <= 0:
        return None
    risk_dist = abs(entry - sl)
    if risk_dist <= 0:
        return None
    if direction == "BUY":
        profit_dist = current - entry
    else:
        profit_dist = entry - current
    return profit_dist / risk_dist


# ----------------------------------------------------------------------
# Progressive trailing modifier
# ----------------------------------------------------------------------

def compute_progressive_trail_modifier(
    rr_now: float,
    enable_progressive_trail: bool,
    progtrail_tier1_rr: float,
    progtrail_tier2_rr: float,
    progtrail_tier3_rr: float,
    progtrail_mult_tier1: float,
    progtrail_mult_tier2: float,
    progtrail_mult_tier3: float,
) -> float:
    """Mirror of the 'Progressive trailing modifier' block (~lines 796-802)."""
    prog_mod = 1.0
    if enable_progressive_trail:
        if rr_now >= progtrail_tier3_rr:
            prog_mod = progtrail_mult_tier3
        elif rr_now >= progtrail_tier2_rr:
            prog_mod = progtrail_mult_tier2
        elif rr_now >= progtrail_tier1_rr:
            prog_mod = progtrail_mult_tier1
    return prog_mod


# ----------------------------------------------------------------------
# Partial TP
# ----------------------------------------------------------------------

@dataclass
class PartialTPResult:
    triggered: bool
    close_volume: Optional[float] = None
    new_tp: Optional[float] = None
    new_sl: Optional[float] = None  # BE-buffer SL applied alongside partial TP


def check_partial_tp(
    rr_now: float,
    entry: float,
    sl: float,
    direction: str,
    vol: float,
    pip: float,
    already_taken: bool,
    enable_partial_tp: bool,
    partial_tp_trigger_rr: float,
    partial_tp_close_percent: float,
    partial_tp_extend_rr: float,
    be_buffer_pips: float,
    volume_min: float = 0.01,
) -> PartialTPResult:
    """
    Mirror of the 'Partial TP' block (~lines 805-829).

    risk_dist is recomputed from entry/sl (same as rr_now's denominator).
    """
    if not enable_partial_tp or already_taken or rr_now < partial_tp_trigger_rr:
        return PartialTPResult(triggered=False)

    risk_dist = abs(entry - sl)

    close_vol = round(vol * (partial_tp_close_percent / 100.0), 2)
    close_vol = max(close_vol, volume_min)

    if direction == "BUY":
        new_tp = entry + risk_dist * partial_tp_extend_rr
        be_sl = entry + be_buffer_pips * pip
    else:
        new_tp = entry - risk_dist * partial_tp_extend_rr
        be_sl = entry - be_buffer_pips * pip

    return PartialTPResult(
        triggered=True,
        close_volume=close_vol,
        new_tp=new_tp,
        new_sl=be_sl,
    )


# ----------------------------------------------------------------------
# Break-even trigger
# ----------------------------------------------------------------------

def check_breakeven_trigger(
    rr_now: float,
    entry: float,
    sl: float,
    direction: str,
    bid_now: float,
    ask_now: float,
    pip: float,
    enable_breakeven: bool,
    be_trigger_rr: float,
    be_buffer_pips: float,
) -> Optional[float]:
    """
    Mirror of the 'Break-even' block (~lines 836-849).

    Returns the new SL if BE should be applied, else None.
    """
    if not enable_breakeven or rr_now < be_trigger_rr:
        return None

    if direction == "BUY":
        be_sl = entry + be_buffer_pips * pip
        needs = sl < be_sl
        valid_be = be_sl < bid_now
    else:
        be_sl = entry - be_buffer_pips * pip
        needs = sl > be_sl
        valid_be = be_sl > ask_now

    if needs and valid_be:
        return be_sl
    return None


# ----------------------------------------------------------------------
# Trailing stop
# ----------------------------------------------------------------------

def compute_trailing_stop(
    rr_now: float,
    current: float,
    sl: float,
    direction: str,
    bid_now: float,
    ask_now: float,
    eff_trail: float,
    pip: float,
    enable_trailing: bool,
) -> Optional[float]:
    """
    Mirror of the 'Trailing stop' block (~lines 852-865).

    `eff_trail` = atr * trail_mult * prog_mod (computed by the caller via
    compute_regime_trail_multiplier / compute_progressive_trail_modifier).

    Returns the new SL if trailing should be applied, else None.
    """
    if not enable_trailing or rr_now <= 0:
        return None

    if direction == "BUY":
        new_sl = current - eff_trail
        trail_ok = new_sl > sl + pip
        valid_sl = new_sl < bid_now
    else:
        new_sl = current + eff_trail
        trail_ok = (new_sl < sl - pip) and (sl > 0)
        valid_sl = new_sl > ask_now

    if trail_ok and valid_sl:
        return new_sl
    return None


# ----------------------------------------------------------------------
# Convenience: default EA parameter set (from ea/BridgeEA_FTMO_v1.mq5 inputs)
# ----------------------------------------------------------------------

@dataclass
class ExitParams:
    """Default values mirror the EA's input parameters."""
    enable_breakeven: bool = True
    be_trigger_rr: float = 0.25
    be_buffer_pips: float = 2.0

    enable_trailing: bool = True
    trail_atr_multiplier: float = 2.0

    enable_regime_trailing: bool = True
    trail_atr_ranging: float = 1.5
    trail_atr_trending: float = 2.5
    trail_atr_volatile: float = 3.5
    regime_atr_low_threshold: float = 15.0
    regime_atr_high_threshold: float = 40.0

    enable_partial_tp: bool = True
    partial_tp_trigger_rr: float = 2.0
    partial_tp_close_percent: float = 50.0
    partial_tp_extend_rr: float = 3.0

    enable_progressive_trail: bool = True
    progtrail_tier1_rr: float = 1.0
    progtrail_tier2_rr: float = 1.5
    progtrail_tier3_rr: float = 2.0
    progtrail_mult_tier1: float = 0.9
    progtrail_mult_tier2: float = 0.75
    progtrail_mult_tier3: float = 0.5


@dataclass
class PositionState:
    """Mutable state tracked across a tick-replay loop for one simulated trade."""
    entry: float
    sl: float
    tp: float
    direction: str  # "BUY" | "SELL"
    vol: float = 0.01
    partial_tp_taken: bool = False
    mfe_pips: float = 0.0
    mae_pips: float = 0.0


def step_position(
    state: PositionState,
    current: float,
    bid_now: float,
    ask_now: float,
    atr: float,
    pip: float,
    params: ExitParams = field(default_factory=ExitParams),
) -> PositionState:
    """
    Advance `state` by one tick/bar of price `current`.

    Applies, in EA order: regime trail mult -> rr_now -> progressive
    trail modifier -> partial TP -> break-even -> trailing stop.
    Updates MFE/MAE (in pips) along the way. Mutates and returns `state`.

    Caller is responsible for detecting SL/TP hits separately (this
    function only adjusts sl/tp/partial_tp_taken).
    """
    rr_now = compute_rr_now(state.entry, state.sl, current, state.direction)
    if rr_now is None:
        return state

    # MFE/MAE tracking
    if state.direction == "BUY":
        excursion_pips = (current - state.entry) / pip if pip > 0 else 0.0
    else:
        excursion_pips = (state.entry - current) / pip if pip > 0 else 0.0

    if excursion_pips > state.mfe_pips:
        state.mfe_pips = excursion_pips
    if excursion_pips < -state.mae_pips:
        state.mae_pips = -excursion_pips

    trail_mult = compute_regime_trail_multiplier(
        atr, pip,
        params.enable_regime_trailing,
        params.trail_atr_multiplier,
        params.trail_atr_ranging,
        params.trail_atr_trending,
        params.trail_atr_volatile,
        params.regime_atr_low_threshold,
        params.regime_atr_high_threshold,
    )

    prog_mod = compute_progressive_trail_modifier(
        rr_now,
        params.enable_progressive_trail,
        params.progtrail_tier1_rr,
        params.progtrail_tier2_rr,
        params.progtrail_tier3_rr,
        params.progtrail_mult_tier1,
        params.progtrail_mult_tier2,
        params.progtrail_mult_tier3,
    )

    eff_trail = atr * trail_mult * prog_mod

    partial = check_partial_tp(
        rr_now, state.entry, state.sl, state.direction, state.vol, pip,
        state.partial_tp_taken,
        params.enable_partial_tp,
        params.partial_tp_trigger_rr,
        params.partial_tp_close_percent,
        params.partial_tp_extend_rr,
        params.be_buffer_pips,
    )
    if partial.triggered:
        state.partial_tp_taken = True
        state.vol = max(state.vol - partial.close_volume, 0.0)
        state.tp = partial.new_tp
        state.sl = partial.new_sl
        return state  # EA `continue`s after partial TP — skip BE/trail this step

    be_sl = check_breakeven_trigger(
        rr_now, state.entry, state.sl, state.direction, bid_now, ask_now, pip,
        params.enable_breakeven,
        params.be_trigger_rr,
        params.be_buffer_pips,
    )
    if be_sl is not None:
        state.sl = be_sl

    new_sl = compute_trailing_stop(
        rr_now, current, state.sl, state.direction, bid_now, ask_now,
        eff_trail, pip,
        params.enable_trailing,
    )
    if new_sl is not None:
        state.sl = new_sl

    return state
