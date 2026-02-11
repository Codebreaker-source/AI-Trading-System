# MASTER_PROJECT_HANDOFF v86 - COMPREHENSIVE SYSTEM DOCUMENTATION

**Last Updated:** 2026-01-23 (MHP Sync Complete)
**Version:** v86 (Synced with MHP v81-solution7)
**Status:** LIVE - Solution 7 Deployed
**Backup:** Archive/MASTER_PROJECT_HANDOFF_20260123_v85.md

---

## CURRENT STATE SUMMARY

### **LIVE SYSTEM (Jan 2026):**
- **File:** `live_trading_system_v6_solution7.py` (1,997 lines)
- **EA:** `BridgeEA_LITE_v2_32_STREAK_SIZE.mq5`
- **Models:** XGBoost + LightGBM only (16 total = 2 per pair × 8 pairs)
- **Features:** 27 CLEAN features (reduced from 58)
- **Account:** OANDA 1600054407 (Demo)

### **KEY ACHIEVEMENTS (Solution 7 - Jan 11, 2026):**
1. Fixed entry clustering issue (44.4% of losses)
2. Fixed trailing stop killing winners (39.3% of losses)
3. Implemented 60-minute direction-aware cooldown per symbol+direction
4. EA params: BE_TriggerRR 1.5→1.0, EnableProgressiveTrail disabled

### **MODEL ARCHITECTURE:**
| Component | Value |
|-----------|-------|
| **Data Source** | Dukascopy (clean 3 years) |
| **Features** | 27 CLEAN |
| **Models** | XGBoost + LightGBM |
| **Total Models** | 16 (2 per pair × 8 pairs) |
| **Model Directory** | `trained_models_CLEAN27/` |

### **MODEL ACCURACY (CLEAN27, Validation Set):**
| Pair | XGBoost | LightGBM |
|------|---------|----------|
| EURUSD | 68.8% | 69.1% |
| GBPUSD | 65.3% | 64.7% |
| USDJPY | 63.6% | 61.9% |
| USDCHF | 70.9% | 70.9% |
| AUDUSD | 69.4% | 69.3% |
| USDCAD | 68.0% | 68.3% |
| NZDUSD | 71.9% | 72.3% |
| EURGBP | 86.0% | 86.3% |
| **AVG** | **70.5%** | **70.3%** |

### **27 CLEAN FEATURES:**
- Price (4): close, high, low, volume
- Trend (8): sma_20, sma_50, fast_ema, slow_ema, htf_fast_ema, htf_slow_ema, htf_trend_direction, htf_trend_alignment
- Momentum (4): rsi, stoch_k, stoch_d, momentum
- Volatility (5): atr, bb_upper, bb_middle, bb_lower, volatility
- Volume (3): volume_sma, volume_ratio, price_volume
- Sentiment (3): bullish_sentiment, bearish_sentiment, net_sentiment

### **REMOVED FEATURES (31 noise):**
- Correlations: pair_correlation_* (cross-pair, not available in training)
- Currency Strength: *_strength (requires all pairs simultaneously)
- Confirmation Flags: *_confirm (derived/redundant)
- Risk Metrics: risk_*, position_* (execution-time only)

---

## 6-PHASE SIGNAL FLOW (Ultimate Synthesis)

```
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 1: CAPITAL SEGMENTATION                                   │
│ • 10% of account used as trading capital                        │
│ • $10,000 account → $1,000 trading capital                      │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 2: DIMENSION WRAPPERS                                     │
│ • REGIME: TRENDING=AGREES, RANGING/VOLATILE=ABSTAINS            │
│ • SESSION: Overlap=AGREES, Off-hours=DISAGREES                  │
│ • ML: Same direction+high conf=AGREES, opposite=DISAGREES       │
│ • CONFLUENCE: Score≥0.35=AGREES, low=DISAGREES                  │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 3: DIMENSION COUNTER                                      │
│ • Count: 0-4 dimensions agreeing                                │
│ • Veto: Any DISAGREES blocks trade                              │
│ • Trade allowed if count ≥ 3 AND no veto                        │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 4: MAIN SYSTEM INTEGRATION                                │
│ • DimensionChecker validates all signals                        │
│ • Results logged for analysis                                   │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 5: DANGER SCORING                                         │
│ • 7 categories (0-3 points each = 0-21 total)                   │
│ • Score ≥ 13 = BLOCKED                                          │
│ • Size multiplier = 1.0 - (score/21)                            │
│                                                                  │
│ Categories: Regime Hostility, Session Opposition, ML Uncertainty│
│ Technical Resistance, System Stress, Correlation Exposure,      │
│ Event Risk                                                      │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ PHASE 6: ANTI-FRAGILE POSITION BUILDING                         │
│ • PROBE: Enter with 0.01 lot                                    │
│ • BUILD: Add 0.01 at R-levels (0.3R, 0.6R, 1.0R, 1.5R)         │
│ • TARGET: Full 0.05 lot position                                │
│ • Requirements: BE reached, dims still agree, danger < 13       │
└────────────────────────┬────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│ SOLUTION 7: DIRECTION-AWARE COOLDOWN                            │
│ • 60-minute cooldown per symbol+direction                       │
│ • Allows opposite direction signals (reversals)                 │
│ • Blocks same-direction spam on exhausted moves                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8-FACTOR CONFLUENCE SCORING

| Factor | Weight | Description |
|--------|--------|-------------|
| MTF Trend | 27% | Multi-timeframe alignment (H1, H4) |
| Support/Resistance | 22% | Proximity to key levels |
| H1/H4 Trend Confirmation | 20% | Higher timeframe trend validation |
| Momentum | 13% | RSI, MACD, Stochastic confirmation |
| Candlestick Patterns | 12% | 169 patterns aligned with direction |
| Volume | 9% | Volume profile and confirmation |
| Strategy Consensus | 9% | 9 rule-based strategy votes |
| Volatility | 8% | Volatility state and session quality |

**Thresholds:**
- HIGH (≥0.70 AND 3+ factors passing): TAKE TRADE
- MEDIUM (≥0.50 AND 2+ factors passing): TRADE WITH CAUTION
- LOW (<0.50): SKIP TRADE

---

## 📁 FOLDER STRUCTURE (CURRENT)

```
C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System\
├─ live_trading_system_v6_solution7.py   ← MAIN: Current live system (1,997 lines)
├─ ensemble_predictor_v3_treebased.py    ← Tree ensemble predictor (727 lines)
├─ feature_expander.py                   ← Feature expansion (495 lines)
├─ rule_based_strategies_v1_0.py         ← 9 trading strategies (457 lines)
├─ news_integration.py                   ← v2.1: MT5 + Web news sources
├─ mt5_calendar_reader.py                ← Reads EA calendar export
├─ confluence/                           ← Confluence scoring (6 modules)
│   ├─ confluence_scorer.py              ← 8-factor scoring
│   ├─ candlestick_patterns.py           ← 169 patterns
│   ├─ htf_confirmation.py               ← H1/H4 trend confirmation
│   ├─ pullback_detector.py              ← Scale-in pullback logic
│   ├─ regime_detector.py                ← Market regime detection
│   ├─ risk_manager.py                   ← Position/risk tracking
│   ├─ level_confluence.py               ← Key level detection
│   └─ hard_filters.py                   ← Session/news filters
├─ dimensions/                           ← 4-dimension signal validation
│   ├─ dimension_checker.py              ← 4-dimension validation (325 lines)
│   ├─ danger_scorer.py                  ← 7-category danger scoring (636 lines)
│   ├─ anti_fragile_builder.py           ← Probe-first building (632 lines)
│   └─ trade_history_tracker.py          ← Hybrid CSV + memory (433 lines)
├─ trained_models_CLEAN27/               ← CURRENT: 16 models (XGB+LGB)
│   ├─ *_xgboost.joblib                  ← 8 XGBoost models
│   └─ *_lightgbm.joblib                 ← 8 LightGBM models
├─ training/                             ← Training scripts & data
│   ├─ *_CLEAN27.py                      ← CLEAN27 training scripts
│   ├─ *_CLEAN27.csv                     ← train/val/test splits
│   └─ dukascopy_CLEAN27_features.csv    ← 598K rows, 27 features
├─ historical_data/                      ← Dukascopy M15 raw data
│   └─ *_M15_dukascopy.csv               ← 8 pairs, 3 years each
├─ logs/                                 ← System logs
│   └─ predictions/                      ← Prediction logs for optimization
├─ docs/                                 ← Research & documentation
├─ 0.1-Handoff Checklists/               ← Documentation
├─ _SAFE_TO_DELETE/                      ← Archived obsolete files
└─ _NEEDS_REVIEW/                        ← Files pending review
```

---

## 🔧 KEY FILES AND LOCATIONS

### **Live System Files:**
```
Phase4_LITE_System/
├─ live_trading_system_v6_solution7.py   ← MAIN: Current live system
├─ ensemble_predictor_v3_treebased.py    ← Tree ensemble with logging
├─ feature_expander.py                   ← Feature expansion
├─ rule_based_strategies_v1_0.py         ← 9 strategies (DISABLED)
├─ news_integration.py                   ← v2.1: MT5 + Web calendar
├─ dimensions/                           ← 4-dimension + danger + anti-fragile
└─ confluence/                           ← 8-factor scoring
```

### **EA File (v2.32 - CURRENT):**
```
C:\Users\mt5-admin\AppData\Roaming\MetaQuotes\Terminal\
  EE0304F13905552AE0B5EAEFB04866EB\MQL5\Experts\
├─ BridgeEA_LITE_v2_32_STREAK_SIZE.mq5   ← CURRENT

EA v2.32 Settings (Solution 7 params):
- FixedLotSize = 0.01
- MinConfidence = 0.35
- BE_TriggerRR = 1.0 (changed from 1.5)
- EnableProgressiveTrail = false (changed from true)
```

### **MT5 Files Directory:**
```
MQL5/Files/
├─ latest_features.csv      ← EA exports (every 3 sec)
├─ trade_commands.csv       ← Python writes, EA reads
├─ open_positions.csv       ← EA exports current positions
├─ calendar_events.csv      ← EA exports (every 5 min)
└─ trades_execution_log.csv ← EA logs executions
```

### **Models Directory:**
```
trained_models_CLEAN27/     ← CURRENT: 16 models
├─ *_xgboost.joblib        ← 8 XGBoost models
└─ *_lightgbm.joblib       ← 8 LightGBM models
```

---

## 🔧 CRITICAL CONFIGURATION

### **Trading Parameters:**
| Parameter | EA v2.32 | Python v6 | Status |
|-----------|----------|-----------|--------|
| Lot Size | 0.01 | 0.01 | ✅ SYNCED |
| Min Confidence | 0.35 | 0.35 | ✅ SYNCED |
| Confluence Threshold | - | 0.35 | Python only |
| BE Trigger R:R | 1.0 | - | EA only |
| Progressive Trail | false | - | EA only |
| Cooldown | - | 60 min | Python only |
| Magic Number | 20251129 | - | EA only |

### **8 Currency Pairs:**
EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD, EURGBP

---

## 🚀 HOW TO RUN THE SYSTEM

### **Step 1: Ensure EA is Running**
EA v2.32 should be compiled and attached to M15 chart with AutoTrading enabled.
Verify settings: BE_TriggerRR=1.0, EnableProgressiveTrail=false

### **Step 2: Run Python System**
```powershell
cd C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System
.\venv_lite\Scripts\python.exe live_trading_system_v6_solution7.py --mode demo
```

### **Step 3: Monitor Logs**
```powershell
Get-Content logs\system_v6_demo.log -Wait -Tail 50
```

---

## 📋 IMMEDIATE NEXT STEPS

### **Ready Now:**
- [ ] Collect 500+ trades for model optimization
- [ ] Monitor Solution 7 effectiveness (cooldown, trailing)
- [ ] Review trade logs for cooldown blocking patterns

### **Pending Development:**
- [ ] Integrate CLEAN27 models into production
- [ ] Implement half-risk scale-in lot sizing
- [ ] Build full Python backtester
- [ ] Consider FTMO challenge after validation

---

## 📝 VERSION HISTORY

| Version | Date | Changes |
|---------|------|---------|
| v86 | 2026-01-23 | Synced with MHP v81-solution7, updated all sections |
| v85 | 2025-12-06 | BE/Trailing stop research document |
| v84 | 2025-12-03 | CLEAN27 models on Dukascopy data, CatBoost excluded |
| v83 | 2025-12-02 | EA v2.33 Python sync, MT5 calendar integration |
| v82 | 2025-11-29 | V5 tree-based ensemble, M15 timeframe |
| v81 | 2025-11-25 | Full system audit, training folder cleanup |

---

## ⚡ QUICK REFERENCE

### **Start System:**
```powershell
cd C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System
.\venv_lite\Scripts\python.exe live_trading_system_v6_solution7.py --mode demo
```

### **Check MT5 Files:**
```
MQL5/Files/
├─ latest_features.csv      (EA writes every 3 sec)
├─ trade_commands.csv       (Python writes, EA reads)
├─ open_positions.csv       (EA writes current positions)
└─ calendar_events.csv      (EA writes every 5 min)
```

### **Model Locations:**
```
trained_models_CLEAN27/
├─ *_xgboost.joblib     (8 XGBoost models) ✅ ACTIVE
└─ *_lightgbm.joblib    (8 LightGBM models) ✅ ACTIVE
```

---

**END OF MASTER_PROJECT_HANDOFF v86**
