# AI FOREX TRADING SYSTEM - COMPREHENSIVE CONTINUATION DOCUMENT
## Version 5.3 | Last Updated: 2025-12-02 | v83 (EA/Python Sync + MT5 Calendar)

---

# TABLE OF CONTENTS
1. [System Overview](#1-system-overview)
2. [Key Level Understanding](#2-key-level-understanding)
3. [Machine Learning Models](#3-machine-learning-models)
4. [Confluence Scoring System](#4-confluence-scoring-system)
5. [Candlestick Pattern Recognition](#5-candlestick-pattern-recognition)
6. [Scale-In Protocol](#6-scale-in-protocol)
7. [Scale-Out Protocol](#7-scale-out-protocol)
8. [Break-Even Protocol](#8-break-even-protocol)
9. [Risk Management](#9-risk-management)
10. [File Locations](#10-file-locations)
11. [Current Configuration](#11-current-configuration)
12. [Known Issues & Decisions](#12-known-issues--decisions)

---

# 1. SYSTEM OVERVIEW

## Architecture Summary
```
                    ┌─────────────────────────────────────┐
                    │     MetaTrader 5 (MT5)              │
                    │  ┌─────────────────────────────┐    │
                    │  │  BridgeEA_LITE_v2.32        │    │
                    │  │  - Extracts 58 features     │    │
                    │  │  - Writes to CSV every 3s   │    │
                    │  │  - Reads trade commands     │    │
                    │  │  - Executes trades          │    │
                    │  │  - Manages SL/TP/BE/Trail   │    │
                    │  └──────────┬──────────────────┘    │
                    └─────────────┼───────────────────────┘
                                  │ latest_features.csv
                                  │ trade_commands.csv
                                  │ open_positions.csv
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Python Trading System (v5.2)                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  live_trading_system_v5_treebased.py                        │    │
│  │                                                              │    │
│  │  1. Read 58 features from Bridge EA                         │    │
│  │  2. Expand to 108 features (feature_expander.py)           │    │
│  │  3. Get ML predictions (ensemble_predictor_v3_treebased.py)│    │
│  │  4. Run 9 rule-based strategies (rule_based_strategies.py) │    │
│  │  5. Apply confluence scoring (8 factors, 169 patterns)     │    │
│  │  6. Validate scale-in conditions if position exists         │    │
│  │  7. Write trade commands for EA execution                   │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │
│  │ XGBoost Models   │  │ LightGBM Models  │  │ CatBoost Models  │   │
│  │ 8 pairs × 1      │  │ 8 pairs × 1      │  │ ❌ DISABLED      │   │
│  │ = 8 models ✅    │  │ = 8 models ✅    │  │ = 8 models       │   │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘   │
│                              │                                       │
│                              ▼                                       │
│              Equal Weight Ensemble (0.50/0.50) XGB+LGB              │
│              Output: BUY/SELL/HOLD + confidence                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Trading Pairs (7 Active)
| Pair | Description | Pip Value |
|------|-------------|-----------|
| EURUSD | Euro/US Dollar | 0.0001 |
| GBPUSD | British Pound/US Dollar | 0.0001 |
| USDJPY | US Dollar/Japanese Yen | 0.01 |
| USDCHF | US Dollar/Swiss Franc | 0.0001 |
| AUDUSD | Australian Dollar/US Dollar | 0.0001 |
| USDCAD | US Dollar/Canadian Dollar | 0.0001 |
| NZDUSD | New Zealand Dollar/US Dollar | 0.0001 |

Note: EURGBP has models but is currently disabled.

---

# 2. KEY LEVEL UNDERSTANDING

## Quarter-Thousand Spacing (NOT Quarter-Hundred)

**Critical Distinction:**
- We use **250 pip** spacing for non-JPY pairs
- We use **25 pip** (0.250) spacing for JPY pairs
- This is quarter-THOUSAND, not quarter-hundred

### Non-JPY Pairs (EURUSD, GBPUSD, USDCHF, AUDUSD, USDCAD, NZDUSD)
```
Major Levels (Direction Indicating):
  .000  →  1.0000, 1.1000, 1.2000, etc.
  .500  →  1.0500, 1.1500, 1.2500, etc.

Quarter Levels (Lower Importance):
  .250  →  1.0250, 1.1250, 1.2250, etc.
  .750  →  1.0750, 1.1750, 1.2750, etc.
```

### JPY Pairs (USDJPY)
```
Major Levels (Direction Indicating):
  .000  →  150.000, 151.000, 152.000, etc.
  .500  →  150.500, 151.500, 152.500, etc.

Quarter Levels (Lower Importance):
  .250  →  150.250, 151.250, 152.250, etc.
  .750  →  150.750, 151.750, 152.750, etc.
```

## Role in Trading
- Key levels indicate **direction** but are NOT standalone deciding factors
- They feed into the **confluence system** as one of multiple factors
- Confluence weighs: key levels + H4/H1 pivots + Fib alignment + time of day + other factors
- All factors contribute to a confluence score for execution decision

## Scaling Logic with Key Levels
- **Scale-out**: At quarter levels (.25, .50, .75, 1.00) from entry when R:R ≥ 2.0
- **Scale-in**: Pullbacks FROM quarter levels (.25/.75) TO major levels (.00/.50)

---

# 3. MACHINE LEARNING MODELS

## Current Ensemble Architecture (v83 - CatBoost Disabled)
```
┌─────────────────────────────────────────────────────────────┐
│                   Tree-Based Ensemble                        │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │  XGBoost    │  │  LightGBM   │  │  CatBoost   │          │
│  │  Weight: 50%│  │  Weight: 50%│  │  ❌ DISABLED │          │
│  │  ✅ ACTIVE  │  │  ✅ ACTIVE  │  │             │          │
│  │ 8 models    │  │ 8 models    │  │ 8 models    │          │
│  │ (1 per pair)│  │ (1 per pair)│  │ (not used)  │          │
│  └──────┬──────┘  └──────┬──────┘  └─────────────┘          │
│         │                │                                   │
│         └────────────────┘                                   │
│                 ▼                                            │
│              Equal Vote → BUY/SELL/HOLD                     │
│              Confidence = avg probability                    │
└─────────────────────────────────────────────────────────────┘
```

## Model Details

### Input Features (105 total)
- **Base 58 features** from Bridge EA:
  - OHLCV data, RSI, MACD, Bollinger Bands, ATR
  - Currency strength indicators
  - Session indicators (London, NY, Tokyo)
  - MTF trend indicators (H1, H4, Daily)

- **Expanded 47 features** from feature_expander.py:
  - Cross-pair correlations
  - Volatility ratios
  - Trend strength indicators
  - Support/resistance derived features

### Output Classes
```
0 = SELL  (Bearish signal)
1 = HOLD  (No action)
2 = BUY   (Bullish signal)
```

### Known Issue: LightGBM HOLD Bias
- LightGBM models predict HOLD 80%+ of the time
- Training data was imbalanced (80% HOLD labels)
- Current workaround: When HOLD wins ensemble vote, use strongest directional signal
- Fix in ensemble_predictor_v3_treebased.py lines 180-200

### Model File Locations
```
trained_models_105FEAT/
├── {PAIR}_xgboost_105feat.pkl      (8 files) ✅ ACTIVE
├── lightgbm/
│   └── {PAIR}_lightgbm_105feat.pkl (8 files) ✅ ACTIVE
└── catboost/
    └── {PAIR}_catboost_105feat.pkl (8 files) ❌ DISABLED
```

---

# 4. CONFLUENCE SCORING SYSTEM

## 8-Factor Weighted Scoring

| Factor | Weight | Description | Passes If |
|--------|--------|-------------|-----------|
| **HTF Confirmation** | 20% | H1/H4 trend alignment with signal | Score ≥ 0.5 |
| **Candlestick Patterns** | 18% | 169 patterns aligned with direction | Score ≥ 0.5 |
| **MTF Trend** | 15% | H1, H4, Daily trend alignment | Score ≥ 0.5 |
| **Strategy Consensus** | 13% | 9 rule-based strategy votes | Score ≥ 0.5 |
| **Support/Resistance** | 12% | Distance to S/R, pivot confluence | Score ≥ 0.5 |
| **Momentum** | 10% | RSI, MACD histogram alignment | Score ≥ 0.5 |
| **Volume** | 6% | Volume vs average | Score ≥ 0.5 |
| **Volatility** | 6% | ATR regime, session activity | Score ≥ 0.5 |
| **TOTAL** | 100% | | |

## Confluence Level Determination
```
Score ≥ 0.70 AND 3+ factors passing → HIGH (take trade)
Score ≥ 0.50 AND 2+ factors passing → MEDIUM (take with caution)
Below thresholds                    → LOW (skip trade)
```

## Rule-Based Strategies (9 Total)
```python
strategies = [
    'volume_breakout',              # Volume spike detection
    'currency_strength_divergence', # Currency pair divergence
    'volatility_breakout',          # ATR-based breakout
    'trend_following',              # Moving average crossovers
    'mean_reversion',               # Oversold/overbought reversals
    'volatility_contraction',       # Squeeze patterns
    'currency_correlation',         # Cross-pair correlation
    'low_volatility_momentum',      # Quiet market momentum
    'high_volatility_reversal'      # Volatile market reversals
]
```

Each strategy outputs BUY/SELL/HOLD, filtered by regime (trending vs ranging).

---

# 5. CANDLESTICK PATTERN RECOGNITION

## 169 Patterns Across 11 Categories

| Category | Count | Examples |
|----------|-------|----------|
| **Single Candle** | 21 | Doji, Hammer, Shooting Star, Marubozu, Spinning Top |
| **Two Candle** | 23 | Engulfing, Harami, Piercing Line, Dark Cloud, Tweezers |
| **Three Candle** | 24 | Morning/Evening Star, Three White Soldiers, Three Black Crows |
| **Multi-Candle Continuation** | 38 | Rising/Falling Three Methods, Flags, NR4/NR7 |
| **Sloped/Structure** | 21 | Wedges, Channels, Triangles, H&S, Double Top/Bottom |
| **Rounded/Curved** | 6 | Rounding Top/Bottom, Cup and Handle, Saucer |
| **Harmonic (XABCD)** | 12 | Gartley, Bat, Butterfly, Crab, Shark, Cypher |
| **AB=CD** | 4 | Standard AB=CD, Extended AB=CD |
| **Three Drives** | 2 | Bullish/Bearish Three Drives |
| **Elliott Wave** | 8 | Impulse, Corrective ABC, Wave 3 Extension, Diagonals |
| **Volume-Based** | 6 | Volume Climax, No Demand/Supply, Stopping Volume |

## Pattern Weight Range
- Highest: 0.90 (Abandoned Baby, Crab patterns)
- Lowest: 0.45 (Long-Legged Doji, High Wave)
- Average: ~0.70

## Detection Methods
```python
CandlestickPatternRecognizer:
  _detect_single_candle_patterns()     # 21 patterns
  _detect_two_candle_patterns()        # 23 patterns
  _detect_three_candle_patterns()      # 24 patterns
  _detect_multi_candle_patterns()      # 38 patterns (gap, three methods, etc.)
  _detect_structure_patterns()         # 21 patterns (uses swing points)
  _detect_harmonic_patterns()          # 18 patterns (XABCD + AB=CD + Three Drives)
  _detect_elliott_wave_patterns()      # 8 patterns
  _detect_volume_patterns()            # 6 patterns (requires volume data)
```

---

# 6. SCALE-IN PROTOCOL

## Scale-In Requirements (5 HARD GATES)

```
Signal Generated for Existing Position
           │
           ▼
┌──────────────────────────────────────┐
│ 1. Max Positions Check               │
│    position_count < 3                │
│    (1 initial + 2 scale-ins max)     │
└──────────────────┬───────────────────┘
                   │ PASS
                   ▼
┌──────────────────────────────────────┐
│ 2. Direction Match                   │
│    signal_action == position_direction│
└──────────────────┬───────────────────┘
                   │ PASS
                   ▼
┌──────────────────────────────────────┐
│ 3. Breakeven Reached                 │
│    Position at BE (25% of risk)      │
│    NO EXCEPTIONS                     │
└──────────────────┬───────────────────┘
                   │ PASS
                   ▼
┌──────────────────────────────────────┐
│ 4. Reward Progress Check (NEW v5.2)  │
│    Current profit ≥ 35% of reward    │
│    (Entry to current vs Entry to TP) │
└──────────────────┬───────────────────┘
                   │ PASS
                   ▼
┌──────────────────────────────────────┐
│ 5. Confluence Check                  │
│    confluence_score ≥ 0.35           │
└──────────────────┬───────────────────┘
                   │ PASS
                   ▼
┌──────────────────────────────────────┐
│ 6. Pullback Validation               │
│    4 checks (3/4 + Fib OK = valid)   │
└──────────────────┬───────────────────┘
                   │ PASS
                   ▼
            SCALE-IN ALLOWED
```

## Pullback Detector (4 Checks)

| Check | Uptrend (BUY) | Downtrend (SELL) |
|-------|---------------|------------------|
| **Structure** | Higher low forming | Lower high forming |
| **Fib Zone** | Pullback 38.2-61.8% from high | Bounce 38.2-61.8% from low |
| **RSI Momentum** | RSI ≥ 40 | RSI ≤ 60 |
| **EMA Trend** | Price above/near 20 EMA | Price below/near 20 EMA |

**Validation:**
- 4/4 checks = VALID
- 3/4 checks + Fib OK = VALID
- Retracement > 61.8% = POTENTIAL REVERSAL (blocked)

## Scale-In Example
```
Initial Entry: BUY EURUSD @ 1.05000
  SL: 1.04750 (250 pip risk)
  TP: 1.05500 (500 pip reward, 2:1 R:R)

BE Trigger: 25% of 250 pips = 62.5 pips → 1.05062
35% Reward: 35% of 500 pips = 175 pips → 1.05175

Scale-in allowed when:
  ✓ Price ≥ 1.05175 (35% reward met)
  ✓ BE already triggered (SL moved to 1.05000)
  ✓ Confluence ≥ 0.35
  ✓ Pullback validated (3-4 checks pass)
```

---

# 7. SCALE-OUT PROTOCOL

## Quarter-Level R:R Based Scaling (v5.1)

**Only scales out when:**
1. Position at breakeven
2. R:R ≥ 2.0
3. Price at quarter level (.25, .50, .75, 1.00)

```
┌─────────────────────────────────┐
│ Position Exists                 │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│ R:R ≥ 2.0?                      │◄── CRITICAL GATE
└───────────────┬─────────────────┘
                │ YES
                ▼
┌─────────────────────────────────┐
│ At Quarter Level?               │
│ (.25, .50, .75, 1.00 from major)│
└───────────────┬─────────────────┘
                │ YES
                ▼
          SCALE-OUT 0.05 lots
```

## Quarter Level Calculation
```python
# For EURUSD at 1.05320 with entry @ 1.05000

Major level below: 1.0500
Quarter levels:
  1.0525 = Q25 @ 1.0500
  1.0550 = Q50 @ 1.0500
  1.0575 = Q75 @ 1.0500
  1.0600 = Q100 @ 1.0500 (next major)

# Current price 1.05320 is near Q25 (1.0525)
# If R:R ≥ 2.0, scale out 0.05 lots
```

---

# 8. BREAK-EVEN PROTOCOL

## BE Trigger: 25% of Risk

```
Entry: BUY @ 1.05000
SL: 1.04750 (250 pip risk)
TP: 1.05500 (500 pip reward)

25% of Risk = 25% × 250 = 62.5 pips
BE Trigger Price = 1.05000 + 0.00625 = 1.05062

When price reaches 1.05062:
  → SL moves from 1.04750 to 1.05000 (entry)
  → Position is now "risk-free"
  → Scale-in becomes possible (if other conditions met)
```

## BE Status Tracking
- EA writes `be_status=YES/NO` to open_positions.csv
- Python reads this to verify BE before allowing scale-in
- Also uses profit as fallback (profit >= 0 = at BE)

---

# 9. RISK MANAGEMENT

## Position Sizing
```
Default Lot Size: 0.10
Scale-Out Lot Size: 0.05
Max Positions Per Symbol: 3 (1 initial + 2 scale-ins)
Max Portfolio Risk: 2% of account
```

## Drawdown Scaling (EA v2.28+)
| Drawdown | Max Positions |
|----------|---------------|
| 0-1% | 100% |
| 1-2% | 80% |
| 2-2.5% | 60% |
| 2.5-3% | 40% |
| 3%+ | Trading paused |

## Streak-Based Sizing (EA v2.32)
| Streak | Max Positions |
|--------|---------------|
| Normal | 100% |
| 2 consecutive losses | 70% |
| 3+ consecutive losses | 50% |

## Signal Cooldown
- 15 minutes between signals for same symbol
- Prevents signal spam (same signal every 3 seconds)
- Allows scale-ins after cooldown expires

---

# 10. FILE LOCATIONS

## Python System
```
C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System\
├── live_trading_system_v5_treebased.py     # Main trading system
├── ensemble_predictor_v3_treebased.py      # ML ensemble predictor
├── feature_expander.py                      # 58→108 feature expansion
├── rule_based_strategies_v1_0.py           # 9 rule-based strategies
├── news_integration.py                      # Economic calendar integration
├── confluence/
│   ├── __init__.py
│   ├── confluence_scorer.py                # 8-factor scoring
│   ├── candlestick_patterns.py            # 169 patterns
│   ├── htf_confirmation.py                 # H1/H4 confirmation
│   ├── level_confluence.py                 # Key level/quarter detection
│   ├── pullback_detector.py                # Scale-in validation
│   ├── regime_detector.py                  # Trending vs ranging
│   ├── risk_manager.py                     # Position/risk tracking
│   └── hard_filters.py                     # Session/news filters
├── mt5_calendar_reader.py                   # MT5 calendar integration
├── trained_models_105FEAT/                  # XGBoost models ✅
├── trained_models_105FEAT/lightgbm/         # LightGBM models ✅
└── trained_models_105FEAT/catboost/         # CatBoost models ❌ DISABLED
```

## MT5 Files
```
C:\Users\mt5-admin\AppData\Roaming\MetaQuotes\Terminal\
  EE0304F13905552AE0B5EAEFB04866EB\MQL5\
├── Experts\
│   └── BridgeEA_LITE_v2_33_CALENDAR.mq5     # Current EA (Python sync + calendar)
└── Files\
    ├── latest_features.csv                   # EA → Python (features, every 3s)
    ├── trade_commands.csv                    # Python → EA (signals)
    ├── open_positions.csv                    # EA → Python (positions)
    └── calendar_events.csv                   # EA → Python (calendar, every 5 min)
```

---

# 11. CURRENT CONFIGURATION

```python
# live_trading_system_v5_treebased.py

# Thresholds
confidence_threshold = 0.35        # Minimum ML confidence
confluence_threshold = 0.35        # Minimum confluence score

# Scale-In Configuration
SCALE_IN_CONFLUENCE_MIN = 0.35     # Confluence required after BE
SCALE_IN_REWARD_PCT_MIN = 0.35     # 35% of reward must be reached
MIN_RR_RATIO = 2.0                 # Minimum R:R for trades

# Scale-Out Configuration
MIN_RR_FOR_SCALEOUT = 2.0          # R:R required before scale-out
MIN_HOLD_MINUTES_FOR_SCALEOUT = 30 # Minimum hold time
SCALEOUT_LOT_SIZE = 0.05           # Lots to close at quarter levels
REQUIRE_BE_FOR_SCALEOUT = True     # Must be at BE to scale out

# Signal Cooldown
SIGNAL_COOLDOWN_MINUTES = 15       # 1 M15 candle between signals
```

---

# 12. KNOWN ISSUES & DECISIONS

## Active Issues
1. **LightGBM HOLD Bias**: LGB predicts HOLD 80%+ due to training data imbalance
   - Workaround: Use strongest directional signal when HOLD wins vote

2. **EURGBP Disabled**: Has models but currently excluded from trading

## Key Decisions Made
| Date | Decision |
|------|----------|
| 2025-12-02 | Key levels use quarter-THOUSAND spacing (250 pips) |
| 2025-12-02 | Fresh entries always sent (no unchanged filter) |
| 2025-12-02 | BE at 25% of risk, scale-in at 35% of reward |
| 2025-12-02 | 169 candlestick patterns implemented |
| 2025-12-02 | Scale-in requires max 3 positions per symbol |

## Pending Considerations
1. Should candlestick pattern weight (18%) change after 169-pattern expansion?
2. Should scale-in confluence be stricter than fresh entry?
3. Half-risk scale-in approach (same total risk, double reward potential)

---

# CONTINUATION PROMPT FOR NEW CLAUDE

Copy and paste this at the start of a new conversation:

```
PROJECT: AI Forex Trading System - LITE v5.2 (Tree-Based Ensemble)

READ FIRST:
C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System\
├── 0.1-Handoff Checklists\COMPREHENSIVE_SYSTEM_CONTINUATION.md (THIS DOC)
├── live_trading_system_v5_treebased.py (main system)
├── mt5_calendar_reader.py (MT5 calendar integration)
├── confluence\candlestick_patterns.py (169 patterns)
├── confluence\confluence_scorer.py (8-factor scoring)
├── confluence\pullback_detector.py (scale-in validation)

CURRENT STATUS (v83 - Dec 02, 2025):
- 16 active models (8 XGBoost + 8 LightGBM) - CatBoost DISABLED
- MT5 calendar integration for news filtering
- EA v2.33 synced with Python (lot 0.01, confidence 0.35)
- 169 candlestick patterns across 11 categories
- 8-factor confluence scoring system
- Scale-in: BE (25% risk) + 35% reward + confluence 0.35 + pullback valid
- Scale-out: R:R ≥ 2.0 + at quarter level

USER RULES:
- ALWAYS clarify before making code changes
- Provide full file versions (not snippets)
- Never add/remove code without explicit permission
- Point out potential weaknesses

CURRENT TASK: [Describe your task here]
```

---

*Document generated: 2025-12-02*
*System Version: 5.2 (169 patterns, 35% reward scale-in)*
