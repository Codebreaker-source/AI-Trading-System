# MASTER_PROJECT_HANDOFF v79 - COMPREHENSIVE SYSTEM DOCUMENTATION

**Last Updated:** 2025-11-18 05:30 UTC
**Version:** v79 (COMPLETE CONFLUENCE SYSTEM + ATR FILTER ADJUSTMENT)
**Status:** ✅ SYSTEM OPERATIONAL - TESTING WITH LOWERED ATR FILTER
**Backup:** Archive/MASTER_PROJECT_HANDOFF_20251118_v78.md

---

## 🎯 CURRENT STATE SUMMARY

### **WHAT'S DEPLOYED:**
The live trading system is now operational with 105 features, 9 rule-based strategies, and a complete 5-factor confluence scoring system with regime detection, collecting real execution data for future model optimization.

### **KEY ACHIEVEMENTS (Nov 17-18 Sessions):**
1. ✅ Created EA v2.24 with SCALE_OUT support for partial position closes
2. ✅ Integrated 9 rule-based strategies running in parallel with ML
3. ✅ Expanded features from 58 → 105 (pivot, fib, psych, MTF, regime, session)
4. ✅ Built complete confluence scoring system (~1,750 lines across 6 modules)
5. ✅ Added comprehensive logging for training data collection
6. ✅ Fixed critical bugs (Unicode encoding, confluence column, XGBoost-only mode)
7. ✅ Lowered ATR filter from 20 → 8 pips for Asian session testing

### **DEPLOY-FIRST PHILOSOPHY:**
Instead of extensive backtesting, the system is deployed to demo account immediately to collect REAL execution data. Models will be optimized using actual trading results rather than theoretical backtests.

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
| `confluence/confluence_scorer.py` | 543 | 5-factor weighted scoring |
| `confluence/regime_detector.py` | 230 | ADX-based regime detection |
| `confluence/risk_manager.py` | 362 | Portfolio risk tracking |
| `confluence/level_confluence.py` | 380 | Fib/Pivot/Psych level detection |

### **5-Factor Confluence Scoring:**

| Factor | Weight | Description |
|--------|--------|-------------|
| MTF Trend | 30% | Multi-timeframe alignment (H1, H4, HTF) |
| Support/Resistance | 25% | Proximity to key levels |
| Momentum | 20% | RSI, MACD, Stochastic confirmation |
| Volume | 15% | Volume profile and confirmation |
| Volatility | 10% | Volatility state and session quality |

**Score Thresholds:**
- HIGH: >= 0.80 → TAKE TRADE
- MEDIUM: >= 0.65 → TAKE TRADE WITH CAUTION
- LOW: < 0.65 → SKIP TRADE

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

### **Strategy-Regime Mapping:**

```python
TRENDING:   trend_following, currency_strength_divergence, currency_correlation
RANGING:    mean_reversion, low_volatility_momentum, volatility_contraction
VOLATILE:   volume_breakout, volatility_breakout, high_volatility_reversal
```

Only regime-appropriate strategies are counted in confluence scoring.

### **Risk Manager Specifications:**

| Parameter | Value | Description |
|-----------|-------|-------------|
| Max Portfolio Risk | 2% ($200 on $10K) | Total risk across all open positions |
| Lot Size | 0.01 | Fixed, no exceptions |
| Max Positions/Symbol | 3 | For scaling in/out |
| Scale IN | Add 0.01 lot | At support levels with confluence |
| Scale OUT | Close 0.01 lot | At resistance levels with confluence |

### **Level Confluence (Fib/Pivot/Psych):**

| Level Type | Tolerance | Strength |
|------------|-----------|----------|
| Fibonacci | 10 pips | 0.9 for 0.382/0.5/0.618, 0.6 for others |
| Pivot Points | 15 pips | 0.9 for PP, 0.8 for S1/R1 |
| Psychological | 10 pips | 0.9 for major (1.1000), 0.6 for minor |

Minimum 2 levels must align for scaling signals.

---

## 🔧 KEY FILES AND LOCATIONS

### **Live System Files:**
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
├─ BridgeEA_LITE_v2_24_SCALE_OUT.mq5     ← Current (with SCALE_OUT support)
└─ BridgeEA_LITE_v2_23_TRADE_EXECUTION.mq5 ← Previous version
```

### **Training Data Logs (Being Collected):**
```
C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System\logs\
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

### **Strategy Logging:**
Every signal logs all 9 strategy votes to `strategy_votes_B1_demo.csv` for future analysis and ensemble optimization.

---

## ⚠️ KNOWN ISSUES & LIMITATIONS

### **Critical: Confidence Calibration Crisis**
Models perform WORST when most confident:
- 85-100% confidence: **49.3% win rate** (WORST)
- 70-85% confidence: **86.5% win rate** (BEST - sweet spot)
- 60-70% confidence: **11.8% win rate** (TERRIBLE)

**Root Cause:** Not data imbalance (that was fixed). Likely model overconfidence on minority classes.

### **Currently Disabled/Missing:**
1. **Transformer/CNN Models** - Disabled due to label mapping issues (0=SELL, 1=HOLD, 2=BUY)
2. **News/Economic Calendar API** - Hard filter is placeholder only
3. **Session Filter** - Disabled for testing
4. **Social Media Sentiment** - Not implemented
5. **Bank Data API** - Not implemented

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

### **Expected Output:**
```
======================================================================
     LIVE TRADING SYSTEM V4.0 - 105 FEATURES + 9 STRATEGIES
======================================================================
Config: B1 | Mode: demo
Features: 105 (58 base + 47 expanded)
Strategies: 9 rule-based + XGBoost ML
...
```

### **Step 3: Monitor Logs**
```powershell
# Watch system log
Get-Content logs\system_v4_B1_demo.log -Wait -Tail 50

# Check expanded features
Import-Csv logs\expanded_features_B1_demo.csv | Select -Last 5

# Check strategy votes
Import-Csv logs\strategy_votes_B1_demo.csv | Select -Last 5
```

---

## 📈 IMMEDIATE NEXT STEPS

### **Priority 1: Verify Trade Execution (NOW)**
- [x] EA v2.24 compiled and attached
- [x] AutoTrading enabled
- [x] Python system running
- [x] ATR filter lowered to 8 pips for Asian session
- [ ] Confirm trades execute correctly
- [ ] Verify SCALE_OUT functionality

### **Priority 2: Collect Training Data**
- [ ] Run system continuously to build expanded_features CSV
- [ ] Collect strategy_votes for analysis
- [ ] Match features to trade outcomes

### **Priority 3: Future Enhancements**
- [ ] Add economic calendar API (ForexFactory or Investing.com)
- [ ] Fix and retrain Transformer/CNN models
- [ ] Retrain XGBoost on 105 features
- [ ] Add remaining 4 pairs (8 total)
- [ ] Implement confidence recalibration (Platt scaling)

---

## 📝 SESSION CHANGES LOG

### **2025-11-18 (This Session):**
- ✅ Lowered ATR filter from 20 → 8 pips for Asian session testing
- ✅ Complete documentation of confluence system
- ✅ Documented all information gaps from previous sessions

### **2025-11-17/18 Session:**

**EA Changes:**
- Created BridgeEA_LITE_v2_24_SCALE_OUT.mq5
- Added ExecuteScaleOut() function for partial position closes
- ProcessTradeCommands() now handles BUY/SELL/SCALE_OUT

**Python Changes:**
- Fixed Unicode encoding in log_system() - added encoding='utf-8'
- Removed 'confluence' column from trade_commands.csv output
- Disabled Transformer/CNN loading (XGBoost only)
- Disabled session filter for testing
- Integrated 9 rule-based strategies with logging
- Created feature_expander.py (58 → 105 features)
- Added training data logging (expanded_features, strategy_votes)

**New Files Created:**
- feature_expander.py (495 lines)
- confluence/ directory (6 modules, ~1,750 lines)
- logs/expanded_features_B1_demo.csv
- logs/strategy_votes_B1_demo.csv

---

## 📚 REFERENCE DOCUMENTS

### **Research & Planning:**
- `RESEARCH_HANDOFF_CONFLUENCE_SCORING.md` - Detailed research requirements
- `TECHNICAL_SPECIFICATIONS_UNIFIED_v77.md` - Complete feature specifications
- `ANTI_OVERSIGHT_PROTOCOL_PHASE_5.5.md` - Verification protocol

### **Session Summaries:**
- `SESSION_SUMMARY_20251118.md` - This session's changes
- `SESSION_SUMMARY_20251117.md` - Previous session

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

### **Key Configuration Files:**
- `confluence/hard_filters.py` line 42: ATR threshold (currently 8 pips)
- `live_trading_system_v4_confluence.py`: Main system configuration

---

## 🎯 SUCCESS METRICS

### **Short-term (This Week):**
- [ ] System runs without errors for 24+ hours
- [ ] Expanded features CSV growing with data
- [ ] Trades executing correctly during market hours
- [ ] EA executing BUY/SELL/SCALE_OUT commands

### **Medium-term (2-4 Weeks):**
- [ ] 1000+ trades executed for statistical significance
- [ ] Strategy performance analysis complete
- [ ] Feature importance ranking from execution data
- [ ] Model retraining with real execution results

### **Long-term (1-2 Months):**
- [ ] 55-65% win rate achieved
- [ ] Proper confidence calibration
- [ ] Ready for FTMO evaluation
- [ ] News integration complete

---

**END OF MASTER_PROJECT_HANDOFF v79**
