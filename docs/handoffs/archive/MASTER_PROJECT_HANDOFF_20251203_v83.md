# MASTER_PROJECT_HANDOFF v84 - COMPREHENSIVE SYSTEM DOCUMENTATION

**Last Updated:** 2025-12-03 (CLEAN27 Models - Dukascopy Data)
**Version:** v84 (CLEAN27 MODELS - XGB+LGB ONLY)
**Status:** MODELS TRAINED - PENDING LIVE INTEGRATION
**Backup:** Archive/MASTER_PROJECT_HANDOFF_20251203_v83.md

---

## CURRENT STATE SUMMARY

### **WHAT'S NEW (Dec 03):**
Retrained all models on CLEAN Dukascopy data (3 years, 598K candles). Reduced from 58 to 27 features. **CatBoost EXCLUDED** (underperformed by 7%). Now 16 models total (XGB + LGB only).

### **KEY ACHIEVEMENTS (Dec 03 Session):**
1. Downloaded 3 years Dukascopy M15 data (Dec 2022 - Dec 2025)
2. Fixed frozen FTMO .sim data issue (5/8 pairs had no price variance)
3. Reduced 58 features to 27 CLEAN signal features
4. Trained 16 models: 8 XGBoost + 8 LightGBM (CatBoost excluded)
5. Better label distribution: 21.5% SELL, 56.7% HOLD, 21.8% BUY
6. Models saved to trained_models_CLEAN27/

### **MODEL ARCHITECTURE:**
| Component | Old (v83) | New (v84) |
|-----------|-----------|-----------|
| **Data Source** | FTMO/OANDA (frozen) | Dukascopy (clean) |
| **Features** | 58 | 27 CLEAN |
| **Models** | XGB+LGB+CatBoost | XGB+LGB only |
| **Total Models** | 24 | 16 |
| **HOLD %** | 80-96% | 56.7% |

### **NEW MODEL ACCURACY (CLEAN27, Validation Set):**
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

## IMMEDIATE NEXT STEPS

1. **PENDING**: Update ensemble_predictor_v3_treebased.py to use CLEAN27 models
2. **PENDING**: Update feature extraction in live system to match 27 features
3. **PENDING**: Test on demo before live deployment
4. **PENDING**: Remove CatBoost code paths entirely

---

## 📁 FOLDER STRUCTURE (CURRENT)

### **ROOT Directory:**
```
C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System\
├─ live_trading_system_v5_treebased.py   ← MAIN: V5 with tree ensemble (1560 lines)
├─ live_trading_system_v4_confluence.py  ← OLD: V4 backup
├─ ensemble_predictor_v3_treebased.py    ← Tree ensemble predictor (727 lines)
├─ ensemble_predictor_v2_4_ondemand.py   ← OLD: XGBoost-only predictor
├─ feature_expander.py                   ← 58 → 108 feature expansion
├─ rule_based_strategies_v1_0.py         ← 9 trading strategies
├─ news_integration.py                   ← v2.1: MT5 + Web news sources
├─ mt5_calendar_reader.py                ← NEW: Reads EA calendar export
├─ confluence/                           ← Confluence scoring (6 modules)
├─ dimensions/                           ← 4-dimension signal validation
├─ trained_models_CLEAN27/               ← NEW: 16 models (XGB+LGB, no CatBoost)
│   ├─ *_xgboost.joblib                  ← 8 XGBoost models (CLEAN27)
│   └─ *_lightgbm.joblib                 ← 8 LightGBM models (CLEAN27)
├─ trained_models_105FEAT/               ← OLD: 24 tree models (deprecated)
├─ training/                             ← Training scripts & data
├─ logs/                                 ← System logs
│   └─ predictions/                      ← Prediction logs for optimization
├─ 0.1-Handoff Checklists/               ← Documentation
├─ _SAFE_TO_DELETE/                      ← Archived obsolete files
└─ _NEEDS_REVIEW/                        ← Files pending review
```


---

## 📋 SYSTEM ARCHITECTURE

### **Data Flow (V5 + EA v2.33):**
```
Bridge EA v2.33 M15 (MT5)
├─ Timeframe: M15 (15-minute candles)
├─ Writes: latest_features.csv (58 base features per pair)
├─ Writes: calendar_events.csv (economic calendar, every 5 min) ← NEW
├─ Writes: open_positions.csv (current positions)
├─ Reads: trade_commands.csv (BUY/SELL/SCALE_OUT commands)
├─ Logs: trades_execution_log.csv (execution results)
├─ SYNCED: FixedLotSize=0.01, MinConfidence=0.35 ← CRITICAL
└─ Features: Break-even, trailing, partial TP, streak sizing, pyramiding

    ↓

Live Trading System V5.0 (Python)
├─ Reads: latest_features.csv
├─ Reads: calendar_events.csv (via mt5_calendar_reader.py) ← NEW
├─ Expands: 58 → 108 features (feature_expander.py)
├─ Predicts: Tree Ensemble (XGB + LGB) + 9 Rule Strategies (CatBoost DISABLED)
├─ Weights: Equal [0.50, 0.50] XGBoost/LightGBM
├─ Filters: Hard filters + Confluence + Regime + 4-Dimension Check
├─ News: MT5 calendar (primary) + Web scraping (backup)
├─ Writes: trade_commands.csv
└─ Logs:
    ├─ predictions/predictions_YYYYMMDD.csv
    ├─ expanded_features_v5_demo.csv
    ├─ strategy_votes_v5_demo.csv
    └─ system_v5_demo.log
```

### **Calendar Integration (NEW v2.33):**
```
MT5 Terminal (Built-in Calendar)
    │
    └──► EA v2.33 exports calendar_events.csv (every 5 min)
                │
                └──► mt5_calendar_reader.py reads CSV
                            │
                            └──► news_integration.py v2.1
                                        │
                                        ├──► is_trade_allowed() ─► Block ±30min HIGH impact
                                        │
                                        └──► get_events_for_hard_filter() ─► Hard filter
```

### **Ensemble Voting (V3.1 - CatBoost Disabled):**
```
For each prediction:
1. XGBoost predicts class + confidence
2. LightGBM predicts class + confidence  
3. (CatBoost DISABLED - was causing issues)
4. Equal-weighted vote: each model gets 0.50 weight
5. Final prediction = class with highest combined weight
6. All predictions logged for future weight optimization
```

---

## 🔧 TREE-BASED ENSEMBLE (V3.1 - 2 MODELS ACTIVE)

### **Model Details:**
| Model | Library | Features | Accuracy | Status |
|-------|---------|----------|----------|--------|
| XGBoost | xgboost | 58 | 85.0% avg | ✅ ACTIVE |
| LightGBM | lightgbm | 58 | 87.0% avg | ✅ ACTIVE |
| CatBoost | catboost | 58 | 85.8% avg | ❌ DISABLED |

### **Per-Pair Performance:**
| Pair | XGBoost | LightGBM | CatBoost | Active Best |
|------|---------|----------|----------|-------------|
| EURUSD | 86.8% | 87.0% | ~~87.5%~~ | LightGBM |
| GBPUSD | 89.1% | 89.3% | ~~89.6%~~ | LightGBM |
| USDJPY | 87.8% | 87.6% | ~~88.9%~~ | XGBoost |
| USDCHF | 86.3% | 86.4% | ~~86.3%~~ | LightGBM |
| AUDUSD | 83.8% | 84.3% | ~~83.6%~~ | LightGBM |
| USDCAD | 80.7% | 80.4% | ~~80.4%~~ | XGBoost |
| NZDUSD | 74.1% | 83.4% | ~~74.4%~~ | LightGBM |
| EURGBP | 91.6% | 98.0% | ~~96.0%~~ | LightGBM |

### **Weighting Strategy:**
- **Phase 1 (Now):** Equal weights [0.50, 0.50] XGBoost/LightGBM
- **Phase 2 (After 100+ trades):** Analyze prediction logs, adjust weights
- **Future:** Per-pair optimal weights, possibly re-enable CatBoost

### **Prediction Logging:**
All predictions logged to `logs/predictions/predictions_YYYYMMDD.csv`:
- Timestamp, pair, ensemble prediction
- Individual model predictions + confidences + probabilities
- Agreement level, unanimous flag
- Trade ID for linking to execution outcomes

---

## 🔧 CONFLUENCE SCORING SYSTEM (6 FACTORS)

### **Current Factors:**
| Factor | Weight | Description |
|--------|--------|-------------|
| MTF Trend | 25% | Multi-timeframe alignment (H1, H4) |
| Support/Resistance | 20% | Proximity to key levels |
| Momentum | 15% | RSI, MACD, Stochastic confirmation |
| Volume | 10% | Volume profile and confirmation |
| Volatility | 10% | Volatility state and session quality |
| Strategy Consensus | 20% | 9 rule-based strategy votes |

### **Planned Additions:**
- **Factor 7:** H1 Candlestick Patterns (pending implementation)
- **Factor 8:** H1/H4 Trend Confirmation (pending implementation)

### **Hard Filters:**
| Filter | Setting | Description |
|--------|---------|-------------|
| ATR Filter | 8 pips min | Minimum volatility |
| News Filter | 30 min buffer | High-impact news blocking (MT5 calendar primary) |
| Session Filter | DISABLED | Was London/NY only |


---

## 🔧 KEY FILES AND LOCATIONS

### **Live System Files (V5 ACTIVE):**
```
Phase4_LITE_System/
├─ live_trading_system_v5_treebased.py   ← MAIN: V5 trading system
├─ ensemble_predictor_v3_treebased.py    ← Tree ensemble with logging
├─ feature_expander.py                   ← 58 → 108 features
├─ rule_based_strategies_v1_0.py         ← 9 strategies
├─ news_integration.py                   ← v2.1: MT5 + Web calendar
├─ mt5_calendar_reader.py                ← NEW: Reads calendar_events.csv
├─ dimensions/                           ← 4-dimension signal validation
└─ confluence/                           ← 6-factor scoring
    ├─ __init__.py
    ├─ hard_filters.py
    ├─ confluence_scorer.py
    ├─ regime_detector.py
    ├─ risk_manager.py
    └─ level_confluence.py
```

### **EA File (v2.33 - CURRENT):**
```
C:\Users\mt5-admin\AppData\Roaming\MetaQuotes\Terminal\
  EE0304F13905552AE0B5EAEFB04866EB\MQL5\Experts\
├─ BridgeEA_LITE_v2_33_CALENDAR.mq5      ← CURRENT: Python sync + calendar
├─ BridgeEA_LITE_v2_32_STREAK_SIZE.mq5   ← Previous version
└─ (older versions v2.16-v2.31)

EA v2.33 Settings (SYNCED WITH PYTHON):
- FixedLotSize = 0.01
- MinConfidence = 0.35
- EnableCalendarExport = true
- CalendarLookAheadHours = 24
- CalendarExportIntervalMin = 5
```

### **MT5 Files Directory:**
```
MQL5/Files/
├─ latest_features.csv      ← EA exports (every 3 sec)
├─ trade_commands.csv       ← Python writes, EA reads
├─ open_positions.csv       ← EA exports current positions
├─ calendar_events.csv      ← NEW: EA exports (every 5 min)
└─ trades_execution_log.csv ← EA logs executions
```

### **Models Directory:**
```
trained_models_105FEAT/                   ← ACTIVE: 24 models
├─ EURUSD.sim_xgboost_105feat.pkl        ← 8 XGBoost
├─ (etc for all 8 pairs)
├─ lightgbm/
│   └─ EURUSD.sim_lightgbm_105feat.pkl   ← 8 LightGBM
└─ catboost/
    └─ EURUSD.sim_catboost_105feat.pkl   ← 8 CatBoost
```

### **Training Data:**
```
training/
├─ train_data_24c_10p_105FEAT.csv        ← 680K samples (M15)
├─ val_data_24c_10p_105FEAT.csv          ← 127K samples (M15)
├─ train_xgboost_105FEAT.py              ← XGBoost training
├─ train_lightgbm_105FEAT.py             ← LightGBM training
└─ train_catboost_105FEAT.py             ← CatBoost training
```

---

## 📊 FEATURE BREAKDOWN

### **ML Models Use 58 Base Features:**
- OHLCV: close, high, low, volume (4)
- Moving Averages: sma_20, sma_50, fast_ema, slow_ema (4)
- Oscillators: rsi, stoch_k, stoch_d (3)
- Volatility: atr, bb_upper, bb_middle, bb_lower (4)
- Volume: volume_sma, volume_ratio, price_volume (3)
- Momentum: volatility, momentum, returns_std, sharpe_approx, max_drawdown (5)
- Confirmations: trend_confirm, momentum_confirm, volatility_confirm (3)
- HTF: htf_fast_ema, htf_slow_ema, htf_trend_direction, htf_trend_alignment (4)
- Sentiment: bullish_sentiment, bearish_sentiment, net_sentiment (3)
- Correlations: 8 pair correlations + avg_correlation (9)
- Currency Strengths: 8 currencies (8)
- Confirmations: htf_confirm, price_action_confirm, etc. (8)

### **Strategy/Confluence Use 108 Expanded Features:**
Base 58 + 50 expanded:
- Pivot Points (7), Fibonacci (9), Psychological Levels (4)
- MTF Alignment (6), Market Regime (4), Session Features (4)
- Momentum Extended (5), Volume Extended (4)

---

## 🎯 9 RULE-BASED STRATEGIES

### **Regime-Mapped Strategies:**
| Regime | Strategies (3 per regime) |
|--------|---------------------------|
| TRENDING | trend_following, currency_strength_divergence, currency_correlation |
| RANGING | mean_reversion, low_volatility_momentum, volatility_contraction |
| VOLATILE | volume_breakout, volatility_breakout, high_volatility_reversal |

Trade requires 2 of 3 regime-appropriate strategies to agree with ML signal.

---

## 🔧 CRITICAL CONFIGURATION

### **Account Details:**
- Broker: OANDA
- Account: 1600054407 (Demo - current)
- Server: OANDA-Prop Trader
- Symbol Suffix: .sim (e.g., EURUSD.sim)

### **Trading Parameters (SYNCED EA ↔ Python):**
| Parameter | EA v2.33 | Python v5 | Status |
|-----------|----------|-----------|--------|
| Lot Size | 0.01 | 0.01 | ✅ SYNCED |
| Min Confidence | 0.35 | 0.35 | ✅ SYNCED |
| Confluence Threshold | - | 0.35 | Python only |
| Timeframe | M15 | M15 | ✅ SYNCED |
| Risk/Reward | 2:1 | 2:1 | ✅ SYNCED |
| SL ATR Mult | 2.0 | 1.5 | EA uses 2.0 |
| TP ATR Mult | 4.0 | 3.0 | EA uses 4.0 |
| Magic Number | 20251129 | - | EA only |

### **EA v2.33 Risk Features:**
- Max Daily Loss: 3.0%
- Max Portfolio Risk: 2.0%
- Max Total Positions: 10 (base)
- Max Correlation Exposure: 2 per group
- Drawdown Scaling: Tier 1-4 (0.75% → 3.0%)
- Equity Curve Trailing: 3.0% drawdown pause
- Volatility Filter: 8-100 pips ATR
- Streak-based Sizing: 2-3 loss tiers
- Pyramiding: After 3 consecutive wins

### **Model Configuration:**
- Models: XGBoost + LightGBM (CatBoost DISABLED)
- Total Active Models: 16 (8 pairs × 2 models)
- Features: 58 (base features from EA)
- Weights: Equal [0.50, 0.50] XGBoost/LightGBM
- Label Mapping: 0=SELL, 1=HOLD, 2=BUY
- Pairs: All 8 (EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD, EURGBP)


---

## 🚀 HOW TO RUN THE SYSTEM

### **Step 1: Ensure EA is Running**
EA v2.33 CALENDAR should be compiled and attached to M15 chart with AutoTrading enabled.
Verify settings: FixedLotSize=0.01, MinConfidence=0.35, EnableCalendarExport=true

### **Step 2: Run Python System (V5)**
```powershell
cd C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System
.\venv_lite\Scripts\python.exe live_trading_system_v5_treebased.py --mode demo
```

### **Optional Parameters:**
```powershell
--mode demo|live          # Trading mode (default: demo)
--confidence 0.35         # ML confidence threshold (default: 0.35, synced with EA)
--confluence 0.35         # Confluence score threshold (default: 0.35)
--weighting equal         # Weight mode: equal|validation|confidence
--interval 3              # Update interval seconds (default: 3)
```

### **Step 3: Monitor Logs**
```powershell
Get-Content logs\system_v5_demo.log -Wait -Tail 50
```

---

## 📈 WEIGHT OPTIMIZATION WORKFLOW

### **After 100-200 Trades:**
```python
from ensemble_predictor_v3_treebased import EnsemblePredictorV3

predictor = EnsemblePredictorV3()
results = predictor.analyze_logged_predictions()

print(f"Win Rate: {results['win_rate']:.1%}")
print(f"Recommended Weights: {results['recommended_weights']}")

# Apply new weights
predictor.set_weights(results['recommended_weights'])
```

---

## 📋 IMMEDIATE NEXT STEPS

### **Ready for Tomorrow:**
- [ ] Monitor V5 live trading system with synced settings
- [ ] Verify MT5 calendar blocking works during news events
- [ ] Collect 500+ trades for model optimization

### **Pending Development:**
- [ ] Implement H1 candlestick pattern recognition (7th confluence factor)
- [ ] Implement H1/H4 trend confirmation (8th confluence factor)
- [ ] After 100+ trades: Analyze logs and optimize XGB/LGB weights
- [ ] Re-evaluate CatBoost after live data collection

### **Completed This Session (Dec 02):**
- [x] EA ↔ Python sync (lot size 0.01, confidence 0.35)
- [x] EA v2.33 with calendar export
- [x] MT5 calendar reader Python module
- [x] News integration v2.1 with MT5 calendar as primary source
- [x] CatBoost disabled from ensemble
- [x] Documentation updated to v83

---

## 📝 VERSION HISTORY

| Version | Date | Changes |
|---------|------|---------|
| v83 | 2025-12-02 | EA v2.33 Python sync, MT5 calendar integration, CatBoost disabled |
| v82 | 2025-11-29 | V5 tree-based ensemble, M15 timeframe, all 8 pairs |
| v81 | 2025-11-25 | Full system audit, training folder cleanup |
| v80 | 2025-11-24 | ROOT folder cleanup (180→25 files) |
| v79 | 2025-11-24 | Confluence scoring system integration |

---

## ⚡ QUICK REFERENCE

### **Start V5 System:**
```powershell
cd C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System
.\venv_lite\Scripts\python.exe live_trading_system_v5_treebased.py --mode demo
```

### **Check MT5 Files:**
```
C:\Users\mt5-admin\AppData\Roaming\MetaQuotes\Terminal\
  EE0304F13905552AE0B5EAEFB04866EB\MQL5\Files\
├─ latest_features.csv      (EA writes every 3 sec)
├─ trade_commands.csv       (Python writes, EA reads)
├─ open_positions.csv       (EA writes current positions)
└─ calendar_events.csv      (EA writes every 5 min) ← NEW
```

### **Model Locations:**
```
trained_models_105FEAT/
├─ *_xgboost_105feat.pkl    (8 XGBoost models) ✅ ACTIVE
├─ lightgbm/*.pkl           (8 LightGBM models) ✅ ACTIVE
└─ catboost/*.pkl           (8 CatBoost models) ❌ DISABLED
```

### **Test Calendar Integration:**
```powershell
cd C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System
python mt5_calendar_reader.py
```

---

**END OF MASTER_PROJECT_HANDOFF v83**
