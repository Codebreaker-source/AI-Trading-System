# MASTER_PROJECT_HANDOFF v82 - COMPREHENSIVE SYSTEM DOCUMENTATION

**Last Updated:** 2025-11-29 (Tree-Based Ensemble V5 Complete)
**Version:** v82 (V5 TREE-BASED ENSEMBLE + M15 TIMEFRAME)
**Status:** ✅ SYSTEM READY FOR LIVE TRADING
**Backup:** Archive/MASTER_PROJECT_HANDOFF_20251125_v80.md

---

## 🎯 CURRENT STATE SUMMARY

### **WHAT'S DEPLOYED:**
Live Trading System V5.0 with tree-based ensemble (XGBoost + LightGBM + CatBoost) on M15 timeframe. All 24 models trained with 85-87% validation accuracy. Equal weights with prediction logging for future optimization.

### **KEY ACHIEVEMENTS (Nov 29 Session):**
1. ✅ **M15 TIMEFRAME MIGRATION** - Switched from M5 to M15 for better signal quality
2. ✅ **TREE-BASED ENSEMBLE** - XGBoost (85%) + LightGBM (87%) + CatBoost (86%)
3. ✅ **ALL 8 PAIRS WORKING** - Including EURGBP (was missing in V4)
4. ✅ **PREDICTION LOGGING** - CSV logging for weight optimization after live data
5. ✅ **V5 LIVE SYSTEM** - New live_trading_system_v5_treebased.py

### **MODEL PERFORMANCE (M15, 58 Features):**
| Model | Average Accuracy | Best Pair | Worst Pair |
|-------|------------------|-----------|------------|
| XGBoost | 85.0% | EURGBP 91.6% | NZDUSD 74.1% |
| LightGBM | 87.0% | EURGBP 98.0% | USDCAD 80.4% |
| CatBoost | 85.8% | EURGBP 96.0% | NZDUSD 74.4% |

### **CRITICAL LEARNING:**
Class weighting kills models. Focal Loss, WeightedRandomSampler, auto_class_weights all caused model collapse. Standard cross-entropy loss without class balancing works fine for 80/10/10 imbalanced data.

---

## 📁 FOLDER STRUCTURE (CURRENT)

### **ROOT Directory:**
```
C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System\
├─ live_trading_system_v5_treebased.py   ← NEW: V5 with tree ensemble (1014 lines)
├─ live_trading_system_v4_confluence.py  ← OLD: V4 backup (1145 lines)
├─ ensemble_predictor_v3_treebased.py    ← NEW: Tree ensemble predictor (727 lines)
├─ ensemble_predictor_v2_4_ondemand.py   ← OLD: XGBoost-only predictor
├─ feature_expander.py                   ← 58 → 108 feature expansion
├─ rule_based_strategies_v1_0.py         ← 9 trading strategies
├─ news_integration.py                   ← News/calendar integration
├─ confluence/                           ← Confluence scoring (6 modules)
├─ trained_models_105FEAT/               ← ACTIVE: 24 tree models
│   ├─ *_xgboost_105feat.pkl            ← 8 XGBoost models
│   ├─ lightgbm/*_lightgbm_105feat.pkl  ← 8 LightGBM models
│   └─ catboost/*_catboost_105feat.pkl  ← 8 CatBoost models
├─ training/                             ← Training scripts & data
├─ logs/                                 ← System logs
│   └─ predictions/                      ← Prediction logs for optimization
├─ 0.1-Handoff Checklists/               ← Documentation
├─ _SAFE_TO_DELETE/                      ← Archived obsolete files
└─ _NEEDS_REVIEW/                        ← Files pending review
```


---

## 📋 SYSTEM ARCHITECTURE

### **Data Flow (V5):**
```
Bridge EA v2.25 M15 (MT5)
├─ Timeframe: M15 (15-minute candles)
├─ Writes: latest_features.csv (58 base features per pair)
├─ Reads: trade_commands.csv (BUY/SELL/SCALE_OUT commands)
└─ Logs: trades_execution_log.csv (execution results)

    ↓

Live Trading System V5.0 (Python)
├─ Reads: latest_features.csv
├─ Expands: 58 → 108 features (feature_expander.py)
├─ Predicts: Tree Ensemble (XGB + LGB + CatBoost) + 9 Rule Strategies
├─ Weights: Equal [0.333, 0.333, 0.333] (adaptive after live data)
├─ Filters: Hard filters + Confluence scoring + Regime detection
├─ Writes: trade_commands.csv
└─ Logs:
    ├─ predictions/predictions_YYYYMMDD.csv (individual model predictions)
    ├─ expanded_features_v5_demo.csv (108 features for analysis)
    ├─ strategy_votes_v5_demo.csv (9 strategy predictions)
    └─ system_v5_demo.log (system events)
```

### **Ensemble Voting (V3.1):**
```
For each prediction:
1. XGBoost predicts class + confidence
2. LightGBM predicts class + confidence  
3. CatBoost predicts class + confidence
4. Equal-weighted vote: each model gets 0.333 weight
5. Final prediction = class with highest combined weight
6. All predictions logged for future weight optimization
```

---

## 🔧 TREE-BASED ENSEMBLE (V3.1)

### **Model Details:**
| Model | Library | Features | Accuracy | Training Time |
|-------|---------|----------|----------|---------------|
| XGBoost | xgboost | 58 | 85.0% avg | ~5 min |
| LightGBM | lightgbm | 58 | 87.0% avg | ~2 min |
| CatBoost | catboost | 58 | 85.8% avg | ~2 min |

### **Per-Pair Performance:**
| Pair | XGBoost | LightGBM | CatBoost | Best Model |
|------|---------|----------|----------|------------|
| EURUSD | 86.8% | 87.0% | 87.5% | CatBoost |
| GBPUSD | 89.1% | 89.3% | 89.6% | CatBoost |
| USDJPY | 87.8% | 87.6% | 88.9% | CatBoost |
| USDCHF | 86.3% | 86.4% | 86.3% | LightGBM |
| AUDUSD | 83.8% | 84.3% | 83.6% | LightGBM |
| USDCAD | 80.7% | 80.4% | 80.4% | XGBoost |
| NZDUSD | 74.1% | 83.4% | 74.4% | LightGBM |
| EURGBP | 91.6% | 98.0% | 96.0% | LightGBM |

### **Weighting Strategy:**
- **Phase 1 (Now):** Equal weights [0.333, 0.333, 0.333]
- **Phase 2 (After 100+ trades):** Analyze prediction logs, adjust weights
- **Future:** Per-pair optimal weights based on live execution data

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
| News Filter | 30 min buffer | High-impact news blocking |
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
├─ news_integration.py                   ← News calendar
└─ confluence/                           ← 6-factor scoring
    ├─ __init__.py
    ├─ hard_filters.py
    ├─ confluence_scorer.py
    ├─ regime_detector.py
    ├─ risk_manager.py
    └─ level_confluence.py
```

### **EA File (M15):**
```
C:\Users\mt5-admin\AppData\Roaming\MetaQuotes\Terminal\
  EE0304F13905552AE0B5EAEFB04866EB\MQL5\Experts\
└─ BridgeEA_LITE_v2_25_M15.mq5           ← M15 timeframe EA
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
- Account: 600013344 (Demo)
- Server: OANDA-Prop Trader
- Symbol Suffix: .sim (e.g., EURUSD.sim)

### **Trading Parameters:**
- Timeframe: M15 (15-minute candles)
- Lot Size: 0.01 (fixed)
- Risk/Reward: 2:1
- SL: ATR × 2.0
- Magic Number: 20251028

### **Model Configuration:**
- Models: XGBoost + LightGBM + CatBoost (tree ensemble)
- Features: 58 (base features from EA)
- Weights: Equal [0.333, 0.333, 0.333]
- Label Mapping: 0=SELL, 1=HOLD, 2=BUY
- Pairs: All 8 (EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD, EURGBP)


---

## 🚀 HOW TO RUN THE SYSTEM

### **Step 1: Ensure EA is Running**
EA v2.25 M15 should be compiled and attached to M15 chart with AutoTrading enabled.

### **Step 2: Run Python System (V5)**
```powershell
cd C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System
.\venv_lite\Scripts\python.exe live_trading_system_v5_treebased.py --mode demo
```

### **Optional Parameters:**
```powershell
--mode demo|live          # Trading mode (default: demo)
--confidence 0.60         # ML confidence threshold (default: 0.60)
--confluence 0.50         # Confluence score threshold (default: 0.50)
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
- [ ] Start V5 live trading system
- [ ] Monitor prediction logs accumulating
- [ ] Verify trades execute correctly

### **Pending Development:**
- [ ] Implement H1 candlestick pattern recognition (7th confluence factor)
- [ ] Implement H1/H4 trend confirmation (8th confluence factor)
- [ ] After 100+ trades: Analyze logs and optimize weights

### **Completed This Session:**
- [x] M15 timeframe migration
- [x] Tree-based ensemble training (XGB + LGB + CatBoost)
- [x] V5 live trading system creation
- [x] Prediction logging for weight optimization

---

## 📝 VERSION HISTORY

| Version | Date | Changes |
|---------|------|---------|
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
├─ latest_features.csv      (EA writes every M15 bar)
├─ trade_commands.csv       (Python writes, EA reads)
└─ open_positions.csv       (EA writes current positions)
```

### **Model Locations:**
```
trained_models_105FEAT/
├─ *_xgboost_105feat.pkl    (8 XGBoost models)
├─ lightgbm/*.pkl           (8 LightGBM models)
└─ catboost/*.pkl           (8 CatBoost models)
```

---

**END OF MASTER_PROJECT_HANDOFF v82**
