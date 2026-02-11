# IMPLEMENTATION ROADMAP - COMBINED
## Ultimate Synthesis Integration + System Enhancements
**Version:** v2.4 | **Created:** 2025-12-03 | **Last Updated:** 2025-12-16

---

## PROGRESS SUMMARY

| Ultimate Synthesis | Status |
|--------------------|--------|
| Phases 1-6 | ✅ **ALL COMPLETE** |

---

# TABLE OF CONTENTS
1. [Executive Summary](#1-executive-summary)
2. [PRIMARY: Ultimate Synthesis 6-Phase Plan](#2-primary-ultimate-synthesis-6-phase-plan)
3. [SECONDARY: System Enhancements](#3-secondary-system-enhancements)
4. [Current Progress](#4-current-progress)
5. [Conflict Resolution](#5-conflict-resolution)
6. [File Reference](#6-file-reference)

---

# 1. EXECUTIVE SUMMARY

## Two Roadmaps Combined

| Roadmap | Purpose | Priority | Est. Time |
|---------|---------|----------|-----------|
| **Ultimate Synthesis** | Decision Architecture - HOW system makes decisions | PRIMARY | 15-20 hours |
| **System Enhancements** | Capabilities - WHAT system can do | SECONDARY | 6 months |

## System Goal
Build a self-improving AI forex trading system that achieves:
- **Target Sharpe Ratio:** 2.0-2.5
- **Target Win Rate:** 55-65%
- **Target Max Drawdown:** 12-15%
- **Risk/Reward:** 2:1 minimum

## Key Principle
**Ultimate Synthesis wraps and coordinates existing components** - your existing code stays 95% unchanged. The new orchestration layer USES your existing modules.

---

# 2. PRIMARY: ULTIMATE SYNTHESIS 6-PHASE PLAN

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    NEW: SYNTHESIS ORCHESTRATOR                              │
│                    (dimensions/ folder)                                     │
│                                                                             │
│    This layer WRAPS and COORDINATES your existing components                │
│    Your existing code stays 95% unchanged                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ Calls existing modules
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────┐         ┌───────────────┐         ┌───────────────┐
│  YOUR         │         │  YOUR         │         │  YOUR         │
│  EXISTING     │         │  EXISTING     │         │  EXISTING     │
│  ML ENSEMBLE  │         │  CONFLUENCE   │         │  HARD         │
│               │         │  SYSTEM       │         │  FILTERS      │
└───────────────┘         └───────────────┘         └───────────────┘
```

---

## PHASE 1: CAPITAL SEGMENTATION ✅ COMPLETE
**Effort:** 10 minutes | **Dependencies:** None | **Completed:** Dec 2024

### Goal
Treat 10% of account as trading capital. Psychologically trade the tier, not the full account.

### Implementation (DONE)
```python
# In live_trading_system_v5_treebased.py __init__ (lines 82-98):

account_balance = 10000.0
trading_capital_percent = 0.10  # Use 10% as trading capital

self.full_account_balance = account_balance  # Keep reference to real balance
self.trading_capital_percent = trading_capital_percent
self.account_balance = account_balance * trading_capital_percent  # $1,000
```

### What This Does
- Your real account: $10,000
- System treats it as: $1,000
- 1% risk per trade = $10 (actually 0.1% of real account)
- 2% max portfolio risk = $20 (actually 0.2% of real account)
- You can "blow up" trading capital = lose only 10% of real account

### Tasks
- [x] Add `trading_capital_percent` parameter to `__init__`
- [x] Calculate effective trading capital
- [x] Update `_print_banner()` to show both values
- [x] Update `RiskManager` initialization to use trading capital
- [x] Update command line `--balance` help text

### Status: ✅ COMPLETE

---

## PHASE 2: DIMENSION WRAPPERS ✅ COMPLETE
**Effort:** 4 hours | **Dependencies:** Phase 1 | **Completed:** Dec 2024

### Goal
Create wrapper functions that convert existing module outputs to dimension format:
- **AGREES** (with proposed direction)
- **DISAGREES** (against proposed direction)
- **ABSTAINS** (neutral/uncertain)

### Implementation (DONE)
**File:** `dimensions/dimension_checker.py` (325 lines)

### 4 Dimension Wrappers Implemented

| Wrapper | Wraps Existing | Logic |
|---------|----------------|-------|
| `check_regime()` | regime_detector.py | TRENDING=AGREES, RANGING/VOLATILE=ABSTAINS |
| `check_session()` | hard_filters.py | Overlap=AGREES, Off-hours=DISAGREES |
| `check_ml()` | ensemble_predictor | Same direction+high conf=AGREES, opposite=DISAGREES |
| `check_confluence()` | confluence_scorer | Score≥threshold=AGREES, low=DISAGREES |

### Tasks
- [x] Create `dimensions/` folder
- [x] Create `dimensions/__init__.py`
- [x] Create `dimensions/dimension_checker.py`
- [x] Implement `check_regime()`
- [x] Implement `check_session()`
- [x] Implement `check_ml()`
- [x] Implement `check_confluence()`
- [ ] Implement `check_edge()` (trade history - FUTURE)

### Status: ✅ COMPLETE (4/5 dimensions, edge dimension future)

---

## PHASE 3: DIMENSION COUNTER ✅ COMPLETE
**Effort:** 2 hours | **Dependencies:** Phase 2 | **Completed:** Dec 2024

### Goal
Count dimension agreements and produce trading decision.

### Implementation (DONE)
**File:** `dimensions/dimension_checker.py` - `check_all()` method

### Logic Implemented
```python
def check_all(...) -> DimensionResult:
    """
    Returns:
        - count: 0-4 dimensions agreeing
        - has_veto: True if any dimension DISAGREES
        - can_trade: True if count >= 3 and no veto
        - details: dict of each dimension's status
    """
```

### Tasks
- [x] Create `check_all()` function in dimension_checker.py
- [x] Implement count logic (0-4 AGREES)
- [x] Implement veto logic (any DISAGREES blocks)
- [x] Return DimensionResult dataclass
- [x] Add logging for dimension counts

### Status: ✅ COMPLETE

---

## PHASE 4: MAIN SYSTEM INTEGRATION ✅ COMPLETE
**Effort:** 3 hours | **Dependencies:** Phase 3 | **Completed:** Dec 2024

### Goal
Modify `live_trading_system_v5_treebased.py` to use dimension counting.

### Implementation (DONE)
**File:** `live_trading_system_v5_treebased.py`

**Key Integration Points:**
- Line 65: `from dimensions import DimensionChecker`
- Line 227-231: `self.dimension_checker = DimensionChecker(...)`
- Lines 708-718: `dimension_result = self.dimension_checker.check_all(...)`
- Lines 723-728: Trade blocking if `not can_trade` or `has_veto`
- Lines 755-757: Dimension results added to signal dict
- Lines 801-827: `_log_dimension_result()` method for logging

### Tasks
- [x] Add dimension imports to live_trading_system_v5
- [x] Initialize DimensionChecker in `__init__`
- [x] Integrate dimension checking into signal flow
- [x] Add dimension count to signal dict
- [x] Add dimension logging method
- [x] Block trades if dimensions don't agree

### Status: ✅ COMPLETE

---

## PHASE 5: DANGER SCORING ✅ COMPLETE
**Effort:** 3 hours | **Dependencies:** Phase 4 | **Completed:** 2025-12-16

### Goal
Consolidate all danger signals into single score (0-21).

### Implementation (DONE)
**File:** `dimensions/danger_scorer.py` (636 lines)

### 7 Danger Categories (0-3 points each)
| Category | What It Checks | Max Points |
|----------|---------------|------------|
| Regime Hostility | ADX < 15, ATR > 2x average, VOLATILE regime | 3 |
| Session Opposition | Off hours, not overlap, Asian for non-home | 3 |
| ML Uncertainty | Low confidence, low agreement, HOLD | 3 |
| Technical Resistance | Low confluence, S/R nearby, counter-trend | 3 |
| System Stress | Drawdown > 5-10%, consecutive losses | 3 |
| Correlation Exposure | Portfolio heat > 4-6%, same-direction | 3 |
| Event Risk | News within 30-60 min | 3 |

### Danger → Size Multiplier
```python
if danger_score >= 13:
    return 0  # No trade - too dangerous
else:
    return 1.0 - (danger_score / 21)  # Linear scaling

# Examples:
# Danger 0  → 100% size
# Danger 5  → 76% size
# Danger 10 → 52% size
# Danger 13 → 0% (blocked)
```

### Tasks
- [x] Create `dimensions/danger_scorer.py`
- [x] Implement 7 category scoring methods
- [x] Implement `calculate_danger_score()` function
- [x] Implement `DangerResult` dataclass
- [x] Add test function with 3 scenarios
- [x] Update `dimensions/__init__.py` exports
- [x] Create `dimensions/trade_history_tracker.py` (hybrid CSV + memory)
- [x] Integrate with main system (live_trading_system_v5)
- [x] Add `_log_danger_result()` method for analysis

### Status: ✅ COMPLETE (module created AND integrated)

---

## PHASE 6: ANTI-FRAGILE POSITION BUILDING ✅ COMPLETE
**Effort:** 4 hours | **Dependencies:** Phase 4 | **Completed:** 2025-12-16

### Goal
Replace current scale-in logic with probe-first approach.

### Implementation (DONE)
**File:** `dimensions/anti_fragile_builder.py` (632 lines)

### Key Components
| Component | Description |
|-----------|-------------|
| `BuildStage` | Enum: PROBE, ADD_0.3R, ADD_0.6R, ADD_1.0R, ADD_1.5R, COMPLETE |
| `BuildPlan` | Dataclass tracking position build progress |
| `BuildSignal` | Signal to add to position at R-level |
| `AntiFragileBuilder` | Main class managing build plans |

### Position Building Logic
```
PROBE (0.01 lot) → 0.3R → 0.6R → 1.0R → 1.5R → TARGET (0.05 lot)
```

### Requirements for Each Add
1. Position at breakeven (BE required)
2. Dimension count >= entry dimension count
3. Danger score < 13
4. Confluence within 20% of entry value

### Size Configuration
| Parameter | Value |
|-----------|-------|
| probe_lot | 0.01 |
| target_lot | 0.05 |
| add_lot | 0.01 |

### Tasks
- [x] Create `dimensions/anti_fragile_builder.py`
- [x] Implement `BuildStage` enum
- [x] Implement `BuildPlan` dataclass
- [x] Implement `BuildSignal` dataclass
- [x] Implement `AntiFragileBuilder` class
- [x] Implement `create_build_plan()` method
- [x] Implement `check_build_opportunity()` method
- [x] Implement `execute_build()` method
- [x] Implement `calculate_current_r()` method
- [x] Update `dimensions/__init__.py` exports
- [x] Integrate into live_trading_system_v5
- [x] Add `_log_build_signal()` method
- [x] Fix 6 integration bugs (methods, parameters, attributes)
- [x] Test passed: Probe → 0.3R → 0.6R → 1.0R builds correctly

### Status: ✅ COMPLETE

---

# 3. SECONDARY: SYSTEM ENHANCEMENTS

These are capability improvements to run in parallel or after Ultimate Synthesis integration.

## Enhancement Category A: Foundation ✅ COMPLETE
- [x] Bridge EA v2.33 development
- [x] CSV-based communication
- [x] MT5 integration
- [x] Historical data collection (Dukascopy)
- [x] XGBoost models (8 pairs)
- [x] LightGBM models (8 pairs)
- [x] Feature reduction (58 → 27 CLEAN)
- [x] Live system V5 deployment
- [x] Confluence scoring system

## Enhancement Category B: Calendar & News ✅ COMPLETE
- [x] MT5 calendar integration
- [x] EA v2.33 calendar export
- [x] mt5_calendar_reader.py
- [x] ±30 min HIGH impact blocking
- [x] news_integration.py v2.1
- [x] Per-pair Asian session filtering (Dec 03)

## Enhancement Category C: Risk Management ⏳ IN PROGRESS
- [ ] Change BE trigger 0.25 → 1.0 R:R
- [ ] ATR-based BE buffer (0.3x ATR)
- [ ] Delay trail until 1.5:1 R:R
- [ ] Regime-specific BE triggers
- [ ] Reversal warning system
- [x] Research doc: DYNAMIC_BE_TRAILING_RESEARCH.md

## Enhancement Category D: Model Integration ⏳ PENDING
- [ ] Update ensemble_predictor to use CLEAN27 models
- [ ] Update feature extraction to match 27 features
- [ ] Test CLEAN27 on demo
- [ ] Remove CatBoost code paths

## Enhancement Category E: Asset Expansion ⏳ FUTURE
- [ ] GBP/JPY (high volatility, trending)
- [ ] AUD/NZD (mean-reverting)
- [ ] XAU/USD (Gold)
- [ ] EUR/JPY (carry trade proxy)

## Enhancement Category F: Advanced ML ⏳ FUTURE
- [ ] Meta-labeling secondary model
- [ ] HMM regime detection
- [ ] Walk-forward optimization
- [ ] Deflated Sharpe ratio validation

---

# 4. CURRENT PROGRESS

## Ultimate Synthesis Phases

| Phase | Name | Status | Notes |
|-------|------|--------|-------|
| 1 | Capital Segmentation | ✅ COMPLETE | 10% capital, code in live_trading_system_v5 |
| 2 | Dimension Wrappers | ✅ COMPLETE | dimensions/dimension_checker.py (325 lines) |
| 3 | Dimension Counter | ✅ COMPLETE | check_all() with count/veto logic |
| 4 | Main System Integration | ✅ COMPLETE | Integrated in generate_signals() |
| 5 | Danger Scoring | ✅ COMPLETE | dimensions/danger_scorer.py (636 lines) |
| 6 | Anti-Fragile Building | ✅ COMPLETE | dimensions/anti_fragile_builder.py (632 lines) |

## Recent Completed Work (Dec 03 - Dec 16)

| Item | Status | Notes |
|------|--------|-------|
| Per-pair Asian session filter | ✅ COMPLETE | USDJPY/AUDUSD/NZDUSD allowed during Asian |
| feedparser installed | ✅ COMPLETE | News dependency |
| Documentation v85 | ✅ COMPLETE | All core docs updated |
| hard_filters.py v2.0 | ✅ COMPLETE | Session filter with symbol support |
| **danger_scorer.py** | ✅ COMPLETE | 636 lines, 7 danger categories, tested |
| **trade_history_tracker.py** | ✅ COMPLETE | 433 lines, hybrid CSV + memory |
| **anti_fragile_builder.py** | ✅ COMPLETE | 632 lines, probe-first building, tested |
| **__init__.py updated** | ✅ COMPLETE | Exports all dimension components |
| **live_trading_system_v5 integration** | ✅ COMPLETE | All 6 phases integrated |

---

# 5. CONFLICT RESOLUTION

## Resolved Conflict: Scale-In Logic

| Item | Current System | After Phase 6 |
|------|----------------|---------------|
| Entry Size | 100% intended risk | 20% probe |
| Scale-In Trigger | BE + confluence 0.35 | 0.3R, 0.6R, 1.0R + dimensions agree |
| Max Positions | 3 per symbol | Gradual build to 100% |
| Scale-In SL | 75% of prev risk | Uses build plan |

**Decision:** Phase 6 REPLACES current scale-in approach.

## New Requirement: Trade History Tracking

Phase 2 Edge Dimension needs:
- Recent trade outcomes (win/loss)
- Consecutive loss count
- Current drawdown

**Solution:** Add `self.trade_history = []` to Python system, populate from EA execution logs.

---

# 6. FILE REFERENCE

## Files Created (Ultimate Synthesis) ✅
```
Phase4_LITE_System/
├── dimensions/                    # CREATED
│   ├── __init__.py               # ✅ Phase 2 (updated Phase 5, 6)
│   ├── dimension_checker.py      # ✅ Phase 2-3 (325 lines)
│   ├── danger_scorer.py          # ✅ Phase 5 (636 lines)
│   ├── trade_history_tracker.py  # ✅ Phase 5 (433 lines)
│   └── anti_fragile_builder.py   # ✅ Phase 6 (632 lines)
```

## Files Modified ✅
```
├── live_trading_system_v5_treebased.py  # ✅ Phase 1, 4, 5, 6
│   ├── trading_capital_percent=0.10     # Phase 1
│   ├── from dimensions import DimensionChecker, DangerScorer, TradeHistoryTracker, AntiFragileBuilder  # Phase 4-6
│   ├── self.dimension_checker = ...     # Phase 4
│   ├── self.trade_history_tracker = ... # Phase 5
│   ├── self.danger_scorer = ...         # Phase 5
│   ├── self.anti_fragile_builder = ...  # Phase 6
│   ├── danger_result = calculate_danger_score()  # Phase 5
│   ├── build_plan = create_build_plan() # Phase 6
│   ├── build_signal = check_build_opportunity() # Phase 6
│   ├── _log_danger_result()             # Phase 5
│   └── _log_build_signal()              # Phase 6
```

## Existing Files (Unchanged, Wrapped by Dimensions)
```
├── ensemble_predictor_v3_treebased.py   # Wrapped by ML dimension
├── confluence/confluence_scorer.py       # Wrapped by Confluence dimension
├── confluence/regime_detector.py         # Wrapped by Regime dimension
├── confluence/hard_filters.py            # Wrapped by Session dimension
└── confluence/risk_manager.py            # Used by Edge dimension
```

---

# QUICK START COMMAND

```powershell
cd C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System
.\venv_lite\Scripts\python.exe live_trading_system_v5_treebased.py --mode demo
```

---

**END OF COMBINED IMPLEMENTATION ROADMAP v2.0**
