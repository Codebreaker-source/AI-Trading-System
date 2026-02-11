# DATA_PIPELINE_FLOW - v86 (2026-01-23)

**Complete Data Flow:** EA v2.32 (27 Features M15) → Dimensions (4) → Danger Score → Anti-Fragile Build → 60-min Cooldown → Trade Commands → EA Execution

**Synced with MHP v81-solution7**

---

## 🎯 CURRENT LIVE DATA FLOW (V6 Solution 7)

### Real-Time Pipeline
```
┌─────────────────────────────────────────────────────────────────┐
│ BRIDGE EA v2.32 STREAK SIZE (MT5)                               │
│                                                                  │
│ Every 3 sec cycle:                                              │
│   • Reads M15 market data from MT5                              │
│   • Calculates features                                          │
│   • Writes: latest_features.csv                                 │
│   • Writes: open_positions.csv                                  │
│                                                                  │
│ Every 5 min:                                                    │
│   • Exports: calendar_events.csv (24h ahead)                    │
│                                                                  │
│ SOLUTION 7 SETTINGS:                                            │
│   • FixedLotSize = 0.01                                         │
│   • MinConfidence = 0.35                                        │
│   • BE_TriggerRR = 1.0 (earlier BE)                             │
│   • EnableProgressiveTrail = false (let winners run)            │
│                                                                  │
│ On trade command:                                               │
│   • Reads: trade_commands.csv                                   │
│   • Executes: BUY/SELL/SCALE_OUT                                │
│   • Logs: trades_execution_log.csv                              │
│   • Deletes: trade_commands.csv (prevents duplicates)           │
└────────────┬────────────────────────────────────────────────────┘
             ↓
┌─────────────────────────────────────────────────────────────────┐
│ PYTHON SYSTEM V6 SOLUTION 7 (1,997 lines)                       │
│                                                                  │
│ PHASE 1: CAPITAL SEGMENTATION                                   │
│   • Uses 10% of account as trading capital                      │
│   • $10,000 account → $1,000 effective capital                  │
└────────────┬────────────────────────────────────────────────────┘
             ↓
┌─────────────────────────────────────────────────────────────────┐
│ FEATURE PROCESSING                                              │
│                                                                  │
│ Input: latest_features.csv (from EA)                            │
│                                                                  │
│ ML Models use 27 CLEAN features:                                │
│   • Price (4): close, high, low, volume                         │
│   • Trend (8): sma_20, sma_50, fast_ema, slow_ema, htf_*       │
│   • Momentum (4): rsi, stoch_k, stoch_d, momentum               │
│   • Volatility (5): atr, bb_upper/middle/lower, volatility      │
│   • Volume (3): volume_sma, volume_ratio, price_volume          │
│   • Sentiment (3): bullish/bearish/net_sentiment                │
└────────────┬────────────────────────────────────────────────────┘
             ↓
┌─────────────────────────────────────────────────────────────────┐
│ TREE-BASED ENSEMBLE PREDICTOR (V3.1)                            │
│                                                                  │
│ Models: XGBoost + LightGBM only (16 total)                      │
│   • 8 XGBoost models (70.5% avg accuracy) ✅                    │
│   • 8 LightGBM models (70.3% avg accuracy) ✅                   │
│   • CatBoost EXCLUDED (underperformed 7%)                       │
│   • CNN/Transformer DISABLED (100% HOLD due to imbalance)       │
│                                                                  │
│ Weights: Equal [0.50, 0.50]                                     │
│ Output: BUY/SELL/HOLD + confidence + agreement                  │
│                                                                  │
│ Logs: logs/predictions/predictions_YYYYMMDD.csv                 │
└────────────┬────────────────────────────────────────────────────┘
             ↓
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 2: DIMENSION WRAPPERS                                     │
│                                                                  │
│ 4 Dimensions check signal validity:                             │
│                                                                  │
│ REGIME Dimension:                                               │
│   • TRENDING = AGREES with directional trades                   │
│   • RANGING/VOLATILE = ABSTAINS                                 │
│                                                                  │
│ SESSION Dimension:                                              │
│   • London/NY overlap = AGREES                                  │
│   • Off-hours = DISAGREES (blocks trade)                        │
│                                                                  │
│ ML Dimension:                                                   │
│   • Same direction + high confidence = AGREES                   │
│   • Opposite direction = DISAGREES (blocks)                     │
│                                                                  │
│ CONFLUENCE Dimension:                                           │
│   • Score ≥ 0.35 = AGREES                                       │
│   • Score < 0.35 = DISAGREES (blocks)                           │
└────────────┬────────────────────────────────────────────────────┘
             ↓
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 3: DIMENSION COUNTER                                      │
│                                                                  │
│ Decision Logic:                                                 │
│   • Count: 0-4 dimensions AGREEING                              │
│   • Veto: Any dimension DISAGREES = trade blocked               │
│   • Trade allowed: count ≥ 3 AND no veto                        │
└────────────┬────────────────────────────────────────────────────┘
             ↓
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 5: DANGER SCORING (7 Categories, 0-21 points)             │
│                                                                  │
│ Categories (0-3 points each):                                   │
│   1. Regime Hostility: ADX < 15, ATR > 2x avg, VOLATILE         │
│   2. Session Opposition: Off hours, not overlap                 │
│   3. ML Uncertainty: Low confidence, low agreement, HOLD        │
│   4. Technical Resistance: Low confluence, S/R nearby           │
│   5. System Stress: Drawdown > 5-10%, consecutive losses        │
│   6. Correlation Exposure: Portfolio heat > 4-6%                │
│   7. Event Risk: News within 30-60 min                          │
│                                                                  │
│ Score ≥ 13 = TRADE BLOCKED                                      │
│ Size multiplier = 1.0 - (score / 21)                            │
└────────────┬────────────────────────────────────────────────────┘
             ↓
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 6: ANTI-FRAGILE POSITION BUILDING                         │
│                                                                  │
│ Build Stages:                                                   │
│   PROBE (0.01 lot) → 0.3R → 0.6R → 1.0R → 1.5R → TARGET (0.05) │
│                                                                  │
│ Add Requirements:                                               │
│   • Position at breakeven (BE required)                         │
│   • Dimension count ≥ entry dimension count                     │
│   • Danger score < 13                                           │
│   • Confluence within 20% of entry value                        │
└────────────┬────────────────────────────────────────────────────┘
             ↓
┌─────────────────────────────────────────────────────────────────┐
│ SOLUTION 7: DIRECTION-AWARE COOLDOWN                            │
│                                                                  │
│ • 60-minute cooldown per symbol+direction                       │
│ • Allows opposite direction signals (reversals)                 │
│ • Blocks same-direction spam on exhausted moves                 │
│                                                                  │
│ Example:                                                        │
│   BUY EURUSD @ 10:00 → BUY EURUSD blocked until 11:00          │
│   But SELL EURUSD allowed immediately (reversal)                │
└────────────┬────────────────────────────────────────────────────┘
             ↓
┌─────────────────────────────────────────────────────────────────┐
│ TRADE COMMAND OUTPUT                                            │
│                                                                  │
│ Writes: trade_commands.csv                                      │
│ Format: symbol, action, confidence, timestamp                   │
│ Actions: BUY, SELL, SCALE_OUT                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8-FACTOR CONFLUENCE SCORING

```
┌─────────────────────────────────────────────────────────────────┐
│ CONFLUENCE SCORER (8 Factors)                                   │
│                                                                  │
│ Factor                    Weight   Passes If                    │
│ ─────────────────────────────────────────────────────────────   │
│ MTF Trend                 27%      Score ≥ 0.5                  │
│ Support/Resistance        22%      Score ≥ 0.5                  │
│ H1/H4 Trend Confirmation  20%      Score ≥ 0.5                  │
│ Momentum                  13%      Score ≥ 0.5                  │
│ Candlestick Patterns      12%      Score ≥ 0.5 (169 patterns)   │
│ Volume                    9%       Score ≥ 0.5                  │
│ Strategy Consensus        9%       Score ≥ 0.5 (9 strategies)   │
│ Volatility                8%       Score ≥ 0.5                  │
│                                                                  │
│ Levels:                                                         │
│   HIGH: ≥0.70 AND 3+ factors passing → TAKE TRADE              │
│   MEDIUM: ≥0.50 AND 2+ factors passing → TRADE WITH CAUTION    │
│   LOW: <0.50 → SKIP TRADE                                       │
│                                                                  │
│ Minimum threshold: 0.35                                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 FILE LOCATIONS (V6 Solution 7)

### Active System Files
```
C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System\
├── live_trading_system_v6_solution7.py    ← MAIN system (1,997 lines)
├── ensemble_predictor_v3_treebased.py     ← Tree ensemble (727 lines)
├── mt5_calendar_reader.py                 ← Reads EA calendar
├── news_integration.py                    ← v2.1: MT5 + Web news
├── feature_expander.py                    ← Feature expansion (495 lines)
├── rule_based_strategies_v1_0.py          ← 9 strategies (DISABLED)
├── dimensions/                            ← 4-dimension + danger + anti-fragile
│   ├── dimension_checker.py               (325 lines)
│   ├── danger_scorer.py                   (636 lines)
│   ├── anti_fragile_builder.py            (632 lines)
│   └── trade_history_tracker.py           (433 lines)
└── confluence/                            ← 8-factor scoring
    ├── confluence_scorer.py
    ├── candlestick_patterns.py            (169 patterns)
    ├── htf_confirmation.py
    ├── pullback_detector.py
    ├── regime_detector.py
    ├── risk_manager.py
    ├── level_confluence.py
    └── hard_filters.py
```

### MT5 Files Location
```
C:\Users\mt5-admin\AppData\Roaming\MetaQuotes\Terminal\
  EE0304F13905552AE0B5EAEFB04866EB\MQL5\Files\
├── latest_features.csv      (EA writes - features, every 3 sec)
├── trade_commands.csv       (Python writes, EA reads & deletes)
├── open_positions.csv       (EA writes - current positions)
├── calendar_events.csv      (EA writes - every 5 min)
└── trades_execution_log.csv (EA writes - execution results)
```

### EA Files
```
MQL5\Experts\
├── BridgeEA_LITE_v2_32_STREAK_SIZE.mq5   ← CURRENT (Solution 7 params)
└── (older versions archived)
```

### Model Files
```
trained_models_CLEAN27/      ← CURRENT: 16 models
├── *_xgboost.joblib        ← 8 XGBoost (70.5% avg) ✅
└── *_lightgbm.joblib       ← 8 LightGBM (70.3% avg) ✅
```

### Log Files
```
logs/
├── predictions/                        ← Individual model logs
│   └── predictions_YYYYMMDD.csv       For weight optimization
├── system_v6_demo.log                 System events
├── predictions_v6_demo.csv            ML predictions summary
├── strategy_votes_v6_demo.csv         Strategy votes
└── expanded_features_v6_demo.csv      Features per cycle
```

---

## ⚡ PERFORMANCE CHARACTERISTICS

### Processing Speed
| Stage | Time |
|-------|------|
| EA feature collection | Every M15 bar + 3 sec cycle |
| Feature processing | <50ms |
| Tree ensemble (2 models × 8 pairs) | <30ms |
| Dimension checks | <20ms |
| Danger scoring | <10ms |
| **Total cycle** | **<150ms for 8 pairs** |

### Memory Usage
| Component | RAM |
|-----------|-----|
| Tree models (16) | ~200 MB |
| Python runtime | ~200 MB |
| **Total system** | **~400 MB** |

---

## 🔧 CONFIGURATION

| Setting | Value |
|---------|-------|
| Account | OANDA 1600054407 (Demo) |
| Symbol Suffix | .sim |
| Timeframe | M15 |
| Models | XGBoost + LightGBM (16 total) |
| Weights | Equal [0.50, 0.50] |
| Features | 27 CLEAN |
| Cooldown | 60 min per symbol+direction |
| BE Trigger | 1.0 R:R |
| Progressive Trail | DISABLED |
| Pairs | All 8 |

---

**END OF DATA_PIPELINE_FLOW v86**
