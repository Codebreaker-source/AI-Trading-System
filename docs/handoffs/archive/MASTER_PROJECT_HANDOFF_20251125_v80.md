# MASTER_PROJECT_HANDOFF v81 - COMPREHENSIVE SYSTEM DOCUMENTATION

**Last Updated:** 2025-11-25 (Full System Audit + Cleanup Complete)
**Version:** v81 (FULL SYSTEM AUDIT + TRAINING FOLDER CLEANUP)
**Status:** ✅ SYSTEM OPERATIONAL + FOLDERS ORGANIZED + FULL AUDIT COMPLETE
**Backup:** Archive/MASTER_PROJECT_HANDOFF_20251125_v80.md

---

## 🎯 CURRENT STATE SUMMARY

### **WHAT'S DEPLOYED:**
The live trading system is now operational with 105 features, 9 rule-based strategies, and a complete 6-factor confluence scoring system with regime detection, collecting real execution data for future model optimization.

### **KEY ACHIEVEMENTS (Nov 25 Session):**
1. ✅ **TRAINING FOLDER CLEANUP** - Reduced from ~115 files to ~22 active files
2. ✅ **FULL SYSTEM AUDIT** - Verified complete pipeline end-to-end
3. ✅ **DOCUMENTATION CORRECTED** - Updated to show 6-factor confluence (was incorrectly showing 5)
4. ✅ A1 config archived to `training/_ARCHIVE/`
5. ✅ Old logs/scripts moved to `training/_SAFE_TO_DELETE/`

### **KEY ACHIEVEMENTS (Nov 24 Session):**
1. ✅ **MAJOR FOLDER CLEANUP** - Reduced ROOT from ~180 files to ~25 active files
2. ✅ Organized obsolete files into `_SAFE_TO_DELETE/` with 8 categorized subfolders
3. ✅ Moved uncertain files to `_NEEDS_REVIEW/` for manual decision
4. ✅ Preserved all critical system files and documentation

### **FOLDER CLEANUP SUMMARY:**
| Location | Before | After | Reduction |
|----------|--------|-------|-----------|
| ROOT | ~180 files | ~25 files | 86% |
| _SAFE_TO_DELETE | - | 200+ files organized | - |
| _NEEDS_REVIEW | - | 4 retrain scripts | - |

### **DEPLOY-FIRST PHILOSOPHY:**
Instead of extensive backtesting, the system is deployed to demo account immediately to collect REAL execution data. Models will be optimized using actual trading results rather than theoretical backtests.

---

## 📁 FOLDER STRUCTURE (POST-CLEANUP)

### **ROOT Directory (CLEAN - ~25 Active Items):**
```
C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System\
├─ live_trading_system_v4_confluence.py  ← Main trading system (952 lines)
├─ ensemble_predictor_v2_4_ondemand.py   ← ML predictor (XGBoost only)
├─ feature_expander.py                   ← 58 → 105 feature expansion (495 lines)
├─ feature_loader.py                     ← Feature loading utility
├─ rule_based_strategies_v1_0.py         ← 9 trading strategies (457 lines)
├─ strategies_10_features.py             ← 10-feature strategy set
├─ strategies_rule_based.py              ← Rule-based strategies
├─ news_integration.py                   ← News API integration
├─ azure_uploader.py                     ← Azure blob uploader
├─ requirements_lite.txt                 ← Python dependencies
├─ BACKUP_SYSTEM_README.md               ← Backup documentation
├─ train_data.csv                        ← Training data
├─ val_data.csv                          ← Validation data
├─ test_data.csv                         ← Test data
├─ confluence/                           ← Confluence scoring (6 modules)
├─ features/                             ← Feature extraction modules
├─ config/                               ← Configuration files
├─ logs/                                 ← System logs
├─ trained_models_B1_CLEAN/              ← Active models (24 models)
├─ training/                             ← Training scripts & data
├─ Dashboard/                            ← Dashboard system
├─ venv_lite/                            ← Python virtual environment
├─ 0.1-Handoff Checklists/               ← Documentation (needs cleanup)
├─ _SAFE_TO_DELETE/                      ← Organized obsolete files
├─ _NEEDS_REVIEW/                        ← Files needing manual review
└─ __pycache__/                          ← Python cache (auto-generated)
```

### **_SAFE_TO_DELETE/ Structure (200+ Files Organized):**
```
_SAFE_TO_DELETE/
├─ old_data_files/          (19 files) - Old CSV data, configs
├─ old_directories/         (6 dirs)  - attention_meta_ensemble, azure_download, etc.
├─ old_documentation/       (27 files) - Old README, SUMMARY files
├─ old_model_directories/   (9 dirs)  - OLD/LEAKED/WRONG model directories
├─ old_model_files/         (23 files) - Orphaned .pkl model files
├─ old_powershell_batch/    (26 files) - Old .ps1 and .bat scripts
├─ old_scripts/             (100+ files) - analyze_*, test_*, train_*, etc.
└─ temp_output_files/       (25 files) - Log outputs, temp files
```

### **_NEEDS_REVIEW/ (4 Files - Manual Decision Required):**
```
_NEEDS_REVIEW/
├─ retrain_24_ULTRA_SAFE.py
├─ retrain_all_24_models_SAFE.py
├─ retrain_cnn_ENHANCED.py
└─ retrain_xgb_transformer_ENHANCED.py
```

### **STILL NEEDS CLEANUP:**
- `0.1-Handoff Checklists/` - ~75 files (next priority)
- `training/` - ~100+ files (low priority)

---

## 📋 SYSTEM ARCHITECTURE

### **Data Flow:**
```
Bridge EA v2.24 (MT5)
├─ Writes: latest_features.csv (58 base features per pair)
├─ Reads: trade_commands.csv (BUY/SELL/SCALE_OUT commands)
└─ Logs: trades_execution_log.csv (execution results)

    ↓

Live Trading System v4.0 (Python)
├─ Reads: latest_features.csv
├─ Expands: 58 → 105 features (feature_expander.py)
├─ Predicts: XGBoost ML + 9 Rule Strategies
├─ Filters: Hard filters + Confluence scoring + Regime detection
├─ Writes: trade_commands.csv
└─ Logs:
    ├─ expanded_features_B1_demo.csv (105 features for training)
    ├─ strategy_votes_B1_demo.csv (9 strategy predictions)
    ├─ predictions_B1_demo.csv (ML predictions)
    └─ system_log_B1_demo.txt (system events)
```

---

## 🔧 CONFLUENCE SCORING SYSTEM (6 MODULES)

### **Module Overview (~1,750 lines total):**

| Module | Lines | Purpose |
|--------|-------|---------|
| `confluence/__init__.py` | 53 | Module exports, version 1.0.0 |
| `confluence/hard_filters.py` | 230 | ATR, News, Session filters |
| `confluence/confluence_scorer.py` | 543 | 6-factor weighted scoring |
| `confluence/regime_detector.py` | 230 | ADX-based regime detection |
| `confluence/risk_manager.py` | 362 | Portfolio risk tracking |
| `confluence/level_confluence.py` | 380 | Fib/Pivot/Psych level detection |

### **6-Factor Confluence Scoring:**

| Factor | Weight | Description |
|--------|--------|-------------|
| MTF Trend | 25% | Multi-timeframe alignment (H1, H4, HTF) |
| Support/Resistance | 20% | Proximity to key levels |
| Momentum | 15% | RSI, MACD, Stochastic confirmation |
| Volume | 10% | Volume profile and confirmation |
| Volatility | 10% | Volatility state and session quality |
| Strategy Consensus | 20% | 9 rule-based strategy votes (regime-filtered) |

**Score Thresholds:**
- HIGH: >= 0.70 → TAKE TRADE
- MEDIUM: >= 0.50 → TAKE TRADE WITH CAUTION (lowered for testing)
- LOW: < 0.50 → SKIP TRADE

### **Hard Filters (Binary Pass/Fail):**

| Filter | Current Setting | Description |
|--------|-----------------|-------------|
| ATR Filter | **8 pips** (lowered from 20) | Minimum volatility for tradeable conditions |
| News Filter | 30 min buffer | Placeholder only - no actual API connected |
| Session Filter | **DISABLED** | Was: London 8-17 UTC, NY 13-22 UTC |

### **Regime Detector (ADX-Based):**

| Regime | ADX Threshold | Weight Adjustments |
|--------|---------------|-------------------|
| TRENDING | ADX > 25 | Momentum ×1.5, MTF ×1.3, S/R ×0.7 |
| RANGING | ADX < 20 | S/R ×1.5, Momentum ×0.7, MTF ×0.8 |
| TRANSITIONAL | ADX 20-25 | All weights ×1.0 |
| VOLATILE | Vol > 95th percentile | Volatility ×1.5, Volume ×1.3, Momentum ×0.8 |

### **Strategy-Regime Mapping (6th Confluence Factor):**

The Strategy Consensus factor only counts votes from regime-appropriate strategies:

| Regime | Strategies Counted (3 of 9) |
|--------|----------------------------|
| **TRENDING** | trend_following, currency_strength_divergence, currency_correlation |
| **RANGING** | mean_reversion, low_volatility_momentum, volatility_contraction |
| **VOLATILE** | volume_breakout, volatility_breakout, high_volatility_reversal |
| **TRANSITIONAL** | All 9 strategies |

---

## 🔧 KEY FILES AND LOCATIONS

### **Live System Files (ACTIVE):**
```
C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System\
├─ live_trading_system_v4_confluence.py  ← Main trading system (952 lines)
├─ ensemble_predictor_v2_4_ondemand.py   ← ML predictor (XGBoost only)
├─ feature_expander.py                   ← 58 → 105 feature expansion (495 lines)
├─ rule_based_strategies_v1_0.py         ← 9 trading strategies (457 lines)
└─ confluence/                           ← Confluence scoring system (~1,750 lines)
    ├─ __init__.py
    ├─ hard_filters.py
    ├─ confluence_scorer.py
    ├─ regime_detector.py
    ├─ risk_manager.py
    └─ level_confluence.py
```

### **EA File:**
```
C:\Users\mt5-admin\AppData\Roaming\MetaQuotes\Terminal\
  EE0304F13905552AE0B5EAEFB04866EB\MQL5\Experts\
└─ BridgeEA_LITE_v2_24_SCALE_OUT.mq5     ← Current (with SCALE_OUT support)
```

### **Models Directory:**
```
trained_models_B1_CLEAN/                  ← ACTIVE - 24 models
├─ XGBoost_EURUSD_B1.pkl (etc.)          ← 8 XGBoost models
├─ Transformer_EURUSD_B1.pkl (etc.)      ← 8 Transformer models
└─ CNN_EURUSD_B1.pkl (etc.)              ← 8 CNN models
```

### **Training Data Logs (Being Collected):**
```
logs/
├─ expanded_features_B1_demo.csv         ← 105 features every cycle
├─ strategy_votes_B1_demo.csv            ← Strategy predictions every signal
├─ predictions_v4_B1_demo.csv            ← ML predictions
└─ system_v4_B1_demo.log                 ← System events
```

---

## 📊 FEATURE BREAKDOWN (105 TOTAL)

### **Base Features from EA (58):**
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
- Confirmations: htf_confirm, price_action_confirm, correlation_confirm, ema_confirm, rsi_confirm, volume_confirm, bb_confirm, stoch_confirm (8)

### **Expanded Features from Python (47):**
- Pivot Points: pp, s1, s2, s3, r1, r2, r3 (7)
- Pivot Distances: dist_to_pivot, dist_to_nearest_support, dist_to_nearest_resistance, pivot_position (4)
- Fibonacci Levels: fib_0236, fib_0382, fib_0500, fib_0618, fib_0786, fib_1000 (6)
- Fib Distances: dist_to_nearest_fib, fib_level_strength, at_fib_level (3)
- Psychological Levels: dist_to_major_psych, dist_to_minor_psych, psych_confluence, at_psych_level (4)
- MTF Alignment: mtf_trend_h1, mtf_momentum_h1, mtf_trend_h4, mtf_rsi_h4, mtf_alignment_score, htf_momentum (6)
- Market Regime: market_regime, regime_confidence, regime_transition, regime_duration (4)
- Session Features: session_volatility_mult, is_high_liquidity_period, active_session_count, overlap_intensity (4)
- Momentum Extended: momentum_acceleration, momentum_divergence, rsi_divergence, macd_divergence, stoch_divergence (5)
- Volume Extended: volume_trend, volume_breakout, cumulative_delta, volume_climax (4)

---

## 🎯 9 RULE-BASED STRATEGIES

### **Integrated Strategies:**
1. **volume_breakout** - High volume + currency strength divergence
2. **currency_strength_divergence** - Base vs quote currency spread
3. **volatility_breakout** - High volatility + momentum alignment
4. **trend_following** - High returns + high ATR confirmation
5. **mean_reversion** - Low volatility + oversold/overbought
6. **volatility_contraction** - Coiling pattern + direction bias
7. **currency_correlation** - Multi-pair alignment
8. **low_volatility_momentum** - Quiet accumulation/distribution
9. **high_volatility_reversal** - ATR spike + reversal signs

---

## ⚠️ KNOWN ISSUES & LIMITATIONS

### **Critical: Confidence Calibration Crisis**
Models perform WORST when most confident:
- 85-100% confidence: **49.3% win rate** (WORST)
- 70-85% confidence: **86.5% win rate** (BEST - sweet spot)
- 60-70% confidence: **11.8% win rate** (TERRIBLE)

### **Currently Disabled/Missing:**
1. **Transformer/CNN Models** - Disabled due to label mapping issues
2. **News/Economic Calendar API** - Hard filter is placeholder only
3. **Session Filter** - Disabled for testing
4. **Social Media Sentiment** - Not implemented

### **Current Test Configuration:**
- ATR Filter: **8 pips** (lowered from 20 for Asian session testing)
- Session Filter: **DISABLED**
- Models: **XGBoost only** (8 pairs)
- Pairs: 4 active (EURUSD, GBPUSD, AUDUSD, USDCAD)

---

## 🔧 CRITICAL CONFIGURATION

### **Account Details:**
- Broker: OANDA
- Account: 600013344 (Demo)
- Server: OANDA-Prop Trader
- Symbol Suffix: .sim (e.g., EURUSD.sim)

### **Trading Parameters:**
- Lot Size: 0.01 (fixed)
- Max Lot: 0.04
- Risk/Reward: 2:1
- SL: ATR × 2.0
- Max Spread: 5.0 pips
- Magic Number: 20251028

### **Model Configuration:**
- Config: B1 (24 candles lookforward, 10 pips threshold)
- Models: XGBoost only (8 pairs)
- Model Directory: trained_models_B1_CLEAN
- Label Mapping: 0=SELL, 1=HOLD, 2=BUY

---

## 🚀 HOW TO RUN THE SYSTEM

### **Step 1: Ensure EA is Running**
EA v2.24 should already be compiled and attached to chart with AutoTrading enabled.

### **Step 2: Run Python System**
```powershell
cd C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System
.\venv_lite\Scripts\python.exe live_trading_system_v4_confluence.py --config B1 --mode demo
```

### **Step 3: Monitor Logs**
```powershell
# Watch system log
Get-Content logs\system_v4_B1_demo.log -Wait -Tail 50
```

---

## 📈 IMMEDIATE NEXT STEPS

### **Priority 1: Complete Folder Cleanup**
- [x] ROOT directory cleaned (180 → 25 files)
- [x] _SAFE_TO_DELETE organized (8 subfolders)
- [x] _NEEDS_REVIEW populated (4 retrain scripts)
- [ ] Organize 0.1-Handoff Checklists folder (~75 files)
- [ ] Organize training/ folder (~100 files) - LOW PRIORITY
- [ ] Create system verification test script
- [ ] Create "prevent clutter" instructions for future Claude

### **Priority 2: Verify Trade Execution**
- [ ] Confirm trades execute correctly
- [ ] Verify SCALE_OUT functionality

### **Priority 3: Collect Training Data**
- [ ] Run system continuously to build expanded_features CSV
- [ ] Collect strategy_votes for analysis

---

## 📝 SESSION CHANGES LOG

### **2025-11-24 (This Session):**
- ✅ **MAJOR FOLDER CLEANUP COMPLETED**
- ✅ Moved 150+ old scripts to `_SAFE_TO_DELETE/old_scripts/`
- ✅ Moved 9 old model directories to `_SAFE_TO_DELETE/old_model_directories/`
- ✅ Moved 23 orphaned .pkl files to `_SAFE_TO_DELETE/old_model_files/`
- ✅ Moved 27 old documentation files to `_SAFE_TO_DELETE/old_documentation/`
- ✅ Moved 26 old PowerShell/batch scripts to `_SAFE_TO_DELETE/old_powershell_batch/`
- ✅ Moved 19 old data files to `_SAFE_TO_DELETE/old_data_files/`
- ✅ Moved 25 temp output files to `_SAFE_TO_DELETE/temp_output_files/`
- ✅ Moved 6 old directories to `_SAFE_TO_DELETE/old_directories/`
- ✅ Moved 4 retrain scripts to `_NEEDS_REVIEW/`
- ✅ Updated MASTER_PROJECT_HANDOFF to v80

### **Previous Sessions:**
- See Archive/ for historical versions

---

## 📚 CORE DOCUMENTATION (8 FILES)

| File | Purpose |
|------|---------|
| MASTER_PROJECT_HANDOFF.md | Main status & architecture (THIS FILE) |
| FILE_INVENTORY.md | All file locations |
| DATA_PIPELINE_FLOW.md | Complete data flow |
| TECHNICAL_SPECIFICATIONS.md | Feature specifications |
| QUICK_SETUP_GUIDE.md | Quick reference |
| SESSION_SUMMARY.md | Session notes |
| CLAUDE_PROJECT_SETUP.md | Claude configuration |
| CUSTOM_INSTRUCTIONS.txt | User rules |

---

## ⚡ QUICK REFERENCE

### **Start System:**
```powershell
cd C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System
.\venv_lite\Scripts\python.exe live_trading_system_v4_confluence.py --config B1 --mode demo
```

### **Check MT5 Files Location:**
```
C:\Users\mt5-admin\AppData\Roaming\MetaQuotes\Terminal\EE0304F13905552AE0B5EAEFB04866EB\MQL5\Files\
├─ latest_features.csv      (EA writes)
├─ trade_commands.csv       (Python writes, EA reads & deletes)
└─ trades_execution_log.csv (EA writes)
```

---

**END OF MASTER_PROJECT_HANDOFF v80**
