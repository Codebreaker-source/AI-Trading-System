# MASTER_PROJECT_HANDOFF v77 - UNIFIED TRAINING & WALK-FORWARD IMPLEMENTATION

**Last Updated:** 2025-11-17 23:00 UTC
**Version:** v77 (UNIFIED TRAINING - STRATEGIES + FEATURES + WALK-FORWARD)
**Status:** 🔄 IMPLEMENTATION IN PROGRESS - COMPLETE TONIGHT
**Backup:** Archive/MASTER_PROJECT_HANDOFF_20251117_v76.md

---

## 🎯 MISSION CRITICAL: TONIGHT'S IMPLEMENTATION

### **OBJECTIVE:**
Complete unified training system with all strategies, features, and walk-forward optimization, then deploy to paper trading.

### **WHY THIS APPROACH:**
- Current system trained on 105 features but live only receives 10 → GARBAGE PREDICTIONS
- Strategies exist in features/ but never integrated into trading logic
- No walk-forward optimization → OVERFITTING RISK
- 37% win rate with inverted confidence calibration → SYSTEM BROKEN

### **EXPECTED OUTCOME:**
- 50-58% win rate (vs current 37%)
- Proper confidence calibration
- Robust parameters via walk-forward (WFE > 0.6)
- Ready for FTMO evaluation

---

## 📋 COMPLETE IMPLEMENTATION PLAN

### **PHASE 1: Generate Strategy Signals on Historical Data (1-2 hours)**

**Objective:** Run all 9 strategies on training data, output signals as new features

**Input:**
- train_data_24c_10p_105FEAT.csv (1.59 GB, 1.45M rows)
- val_data_24c_10p_105FEAT.csv (341.6 MB)
- test_data_24c_10p_105FEAT.csv (341.5 MB)

**Output:**
- train_data_UNIFIED.csv (123 columns = 105 + 18 strategy features)
- val_data_UNIFIED.csv
- test_data_UNIFIED.csv

**Strategy Features Added (18 total):**
1. volume_breakout_signal (-1, 0, 1)
2. volume_breakout_confidence (0-1)
3. currency_strength_divergence_signal
4. currency_strength_divergence_confidence
5. volatility_breakout_signal
6. volatility_breakout_confidence
7. trend_following_signal
8. trend_following_confidence
9. mean_reversion_signal
10. mean_reversion_confidence
11. volatility_contraction_signal
12. volatility_contraction_confidence
13. currency_correlation_signal
14. currency_correlation_confidence
15. low_volatility_momentum_signal
16. low_volatility_momentum_confidence
17. high_volatility_reversal_signal
18. high_volatility_reversal_confidence

**NEW Strategies to Add (using pivot/Fibonacci/psych):**
19. fibonacci_bounce_signal
20. fibonacci_bounce_confidence
21. pivot_breakout_signal
22. pivot_breakout_confidence
23. psychological_level_reversal_signal
24. psychological_level_reversal_confidence

**TOTAL: 129 features (105 + 24 strategy features)**

---

### **PHASE 2: Walk-Forward Optimization (2-3 hours)**

**Objective:** Find robust parameter set that generalizes to unseen data

**Methodology:**
```
Window 1: Train on rows 0-1,000,000 | Test on rows 1,000,000-1,200,000
Window 2: Train on rows 200,000-1,200,000 | Test on rows 1,200,000-1,400,000
Window 3: Train on rows 400,000-1,400,000 | Test on rows 1,400,000-1,450,000
```

**Parameters to Optimize:**
- XGBoost: n_estimators, max_depth, learning_rate, subsample
- Strategy thresholds: pip distances, volume ratios, strength thresholds
- Ensemble weights: XGBoost vs strategy contribution

**Success Criteria:**
- WFE (Walk-Forward Efficiency) > 0.6 for each strategy
- Consistent performance across all windows
- No parameter instability (flip-flopping)

**Output:**
- optimal_params.json (best parameter set)
- walk_forward_results.csv (performance per window)
- strategy_wfe_scores.csv (WFE per strategy)

---

### **PHASE 3: Unified Model Training (1-2 hours)**

**Objective:** Train XGBoost on complete 129-feature dataset with optimized parameters

**Training Configuration:**
- Algorithm: XGBoost only (skip neural networks due to class imbalance)
- Features: 129 (105 original + 24 strategy signals)
- Pairs: 8 (EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD, EURGBP)
- Parameters: From walk-forward optimization

**Expected Metrics:**
- Training accuracy: >90%
- Validation accuracy: >85%
- Prediction distribution: Not 100% HOLD (verified)
- Memory per model: <500 MB

**Output:**
- trained_models_UNIFIED/ (8 XGBoost models)
- training_metrics.json (accuracy per pair)

---

### **PHASE 4: Hybrid Feature Extraction Setup (1-2 hours)**

**Objective:** Configure live system to calculate all 129 features

**Architecture:**
```
Bridge EA (MQL5) → Basic Features (20-30)
    ↓
Python API → Derived Features (100+)
    ↓
Combined → 129 Features → XGBoost → Prediction
```

**EA Extracts:**
- OHLCV data (5)
- Basic indicators: SMA, EMA, RSI, ATR, BB, Stoch (15)
- Volume data (3)
- Currency strengths (8)

**Python Calculates:**
- Pivot points (7)
- Fibonacci levels (calculated from OHLC)
- Psychological levels (5)
- Session overlap (4)
- Volume surge (3)
- MACD/EMA (6)
- Multi-timeframe (5)
- HMM regime (3)
- Economic calendar (9)
- All strategy signals (24)

---

### **PHASE 5: Paper Trading Deployment (Tonight)**

**Configuration:**
- Account: OANDA Demo 600013344
- Lot size: 0.01 FIXED (min and max)
- Max positions per pair: Unlimited (for data gathering)
- Max total positions: Unlimited (for data gathering)
- Pairs: Start with 4 (EURUSD, GBPUSD, AUDUSD, USDCAD)

**Monitoring:**
- Win rate tracking
- Confidence calibration check
- Drawdown monitoring
- Feature extraction validation

---

## 🚨 ERROR PREVENTION CHECKLIST

### **FROM TECHNICAL_ISSUES_CATALOG - RECURRING ISSUES:**

**ISSUE #1: Feature Count Mismatch**
- [ ] Verify model expects 129 features
- [ ] Verify live extraction provides exactly 129 features
- [ ] Column order matches training data
- [ ] No NaN values in features

**ISSUE #2: Symbol Suffix Mismatch**
- [ ] Demo account uses ".sim" suffix (EURUSD.sim)
- [ ] Live account uses no suffix (EURUSD)
- [ ] Verify suffix handling in all code paths

**ISSUE #3: Label Mapping Error**
- [ ] Confirm: 0=SELL, 1=HOLD, 2=BUY
- [ ] Check prediction→action mapping
- [ ] Verify in both training AND live code

**ISSUE #4: Data Staleness**
- [ ] EA running in MT5 terminal
- [ ] File timestamp < 60 seconds old
- [ ] Add staleness check in live system

**ISSUE #5: Type Mismatches (MQL5)**
- [ ] Use ENUM types not integers
- [ ] Use uint for error codes
- [ ] Compile EA before deployment

---

## 💻 CPU OPTIMIZATION COMMANDS

### **Prevent System Freezes During Training:**

**1. Set Process Priority to Below Normal:**
```powershell
# Start training with lower priority
Start-Process -FilePath "python.exe" -ArgumentList "train_unified_walkforward.py" -PassThru | ForEach-Object { $_.PriorityClass = "BelowNormal" }
```

**2. Limit CPU Cores (Leave 2 for system):**
```python
# Add at top of training script
import os
os.environ['OMP_NUM_THREADS'] = '6'  # For 8-core CPU, use 6
os.environ['MKL_NUM_THREADS'] = '6'

# XGBoost specific
xgb_params = {
    'nthread': 6,  # Not all cores
    # ... other params
}
```

**3. Memory-Efficient Chunked Processing:**
```python
# Process data in chunks
chunk_size = 100000
for i in range(0, len(df), chunk_size):
    chunk = df.iloc[i:i+chunk_size]
    # Process chunk
    gc.collect()  # Force garbage collection
```

**4. Run Training in Background:**
```powershell
# PowerShell - run and continue working
Start-Job -ScriptBlock {
    cd C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System
    .\venv_lite\Scripts\python.exe train_unified_walkforward.py 2>&1 | Out-File training_log.txt
}

# Check progress
Get-Job
Receive-Job -Id <job_id>
```

**5. Monitor System Resources:**
```powershell
# In separate terminal
while ($true) {
    Get-Process python | Select-Object CPU, WorkingSet64
    Start-Sleep 10
}
```

---

## ⚠️ RISK SOLUTIONS

### **Risk 1: Insufficient Training Time Tonight**

**Problem:** Walk-forward on 1.45M samples with 129 features may take hours

**Solutions:**
1. **Subset training:** Start with 500K samples, scale up if time permits
2. **4 pairs first:** EURUSD, GBPUSD, AUDUSD, USDCAD (skip 4 initially)
3. **Parallel training:** Train multiple pairs simultaneously
4. **Pre-computed strategy signals:** Calculate once, save to file

**Implementation:**
```python
# Quick mode - 500K samples
df = pd.read_csv('train_data.csv', nrows=500000)

# Or sample 50% randomly
df = pd.read_csv('train_data.csv').sample(frac=0.5, random_state=42)
```

---

### **Risk 2: Strategy Parameters Not Optimized**

**Problem:** Default thresholds (10 pips from pivot) may not be optimal

**Solutions:**
1. **Walk-forward handles this:** Automatically finds optimal thresholds
2. **Grid search on key params:** Test 5, 10, 15, 20 pip distances
3. **Use backtest results:** See which thresholds had highest WFE

**Implementation:**
```python
# Parameter grid for strategies
param_grid = {
    'pivot_distance_pips': [5, 10, 15, 20],
    'volume_surge_ratio': [1.3, 1.5, 2.0],
    'strength_threshold': [0.5, 0.6, 0.7]
}
```

---

### **Risk 3: Feature Calculation Bugs**

**Problem:** Mismatch between training and live feature calculation = garbage predictions

**Solutions:**
1. **Single source of truth:** Use SAME Python functions for training AND live
2. **Validation script:** Compare live features to training samples
3. **Log all features:** Write to file for debugging

**Implementation:**
```python
# Feature validator
def validate_features(live_features, sample_training_row):
    for i, (live, train) in enumerate(zip(live_features, sample_training_row)):
        if abs(live - train) > 0.001:
            print(f"MISMATCH at feature {i}: live={live}, train={train}")
```

---

### **Risk 4: Market Conditions Changed**

**Problem:** Training data (2023-2024) may not reflect current market

**Solutions:**
1. **Extract recent data:** Add last 2-4 weeks to training set
2. **Walk-forward validates:** Tests adaptability to new conditions
3. **Weight recent data:** Give higher weight to newer samples

**Implementation:**
```powershell
# Extract recent M5 data from MT5
# (Add to existing training data)
```

---

## 📊 DATA EXTRACTION PLAN

### **Existing Data:**
- train_data_24c_10p_105FEAT.csv: 1.45M rows (Jan 2023 - Oct 2024)
- val_data_24c_10p_105FEAT.csv: ~300K rows
- test_data_24c_10p_105FEAT.csv: ~300K rows

### **New Data to Extract:**
- Period: November 1-17, 2025 (2.5 weeks)
- Timeframe: M5
- Pairs: 8
- Expected rows: ~2,500 per pair × 8 = ~20,000 new samples

### **Extraction Method:**
```python
# Use MT5 API to pull recent data
import MetaTrader5 as mt5

mt5.initialize()

# Get M5 data for last 3 weeks
rates = mt5.copy_rates_from_pos(
    "EURUSD.sim", 
    mt5.TIMEFRAME_M5, 
    0,  # Start from current bar
    6000  # ~3 weeks of M5 data
)
```

### **Integration:**
1. Extract raw OHLCV from MT5
2. Calculate all 105 features using same functions as training
3. Append to existing training data
4. Re-run walk-forward with combined dataset

---


## 🔄 EXECUTION SEQUENCE (TONIGHT)

### **STEP 1: Create Strategy Signal Generator (30 min)**
```powershell
cd C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System
.\venv_lite\Scripts\python.exe generate_strategy_signals.py
```

**Script creates:**
- Runs all strategies on historical data
- Outputs strategy signals as new columns
- Saves unified training dataset

---

### **STEP 2: Generate Unified Dataset (45 min)**
```powershell
# Run with lower priority to prevent freezing
Start-Process -FilePath ".\venv_lite\Scripts\python.exe" -ArgumentList "create_unified_dataset.py" -PassThru | ForEach-Object { $_.PriorityClass = "BelowNormal" }
```

**Verification:**
```powershell
.\venv_lite\Scripts\python.exe -c "import pandas as pd; df = pd.read_csv('training/train_data_UNIFIED.csv', nrows=1); print(f'Columns: {len(df.columns)}')"
# Expected: 130 columns (129 features + label)
```

---

### **STEP 3: Run Walk-Forward Optimization (1-2 hours)**
```powershell
# This is the longest step - run in background
Start-Job -ScriptBlock {
    cd C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System
    .\venv_lite\Scripts\python.exe walk_forward_optimization.py 2>&1 | Tee-Object -FilePath walkforward_log.txt
}

# Monitor progress
Get-Content walkforward_log.txt -Tail 20 -Wait
```

**Output files:**
- optimal_params.json
- walk_forward_results.csv
- strategy_wfe_scores.csv

---

### **STEP 4: Train Unified XGBoost Models (30-45 min)**
```powershell
.\venv_lite\Scripts\python.exe train_unified_xgboost.py
```

**Expected output:**
```
Training EURUSD.sim... Accuracy: 94.2%
Training GBPUSD.sim... Accuracy: 93.8%
...
All 8 models saved to trained_models_UNIFIED/
```

---

### **STEP 5: Setup Hybrid Feature Extraction (30 min)**
```powershell
# Create feature extraction module
.\venv_lite\Scripts\python.exe setup_live_feature_extraction.py
```

**Verification:**
```powershell
# Test feature extraction with sample data
.\venv_lite\Scripts\python.exe test_feature_extraction.py
# Should output 129 features for sample input
```

---

### **STEP 6: Deploy to Paper Trading (15 min)**

**Update live system:**
```powershell
# Update model paths in live_trading_system_v3.py
# Update feature extraction to use hybrid approach
# Set lot size to 0.01 fixed
```

**Start paper trading:**
```powershell
.\venv_lite\Scripts\python.exe live_trading_system_v4_UNIFIED.py --mode demo --lot-size 0.01
```

**Verify operation:**
- Check logs for feature extraction (129 features)
- Confirm predictions being made
- Verify trade commands written

---

## 📊 MONITORING CHECKLIST (During Paper Trading)

### **First Hour:**
- [ ] Features extracting correctly (129 count)
- [ ] No NaN values in features
- [ ] Predictions being made (not all HOLD)
- [ ] Trade commands written to CSV
- [ ] EA executing trades

### **First 4 Hours:**
- [ ] Multiple trades executed
- [ ] No system errors/crashes
- [ ] Memory stable (<3 GB)
- [ ] CPU reasonable (<80%)

### **First 24 Hours:**
- [ ] Win rate tracking started
- [ ] Confidence calibration check
- [ ] Drawdown within limits
- [ ] All 8 pairs trading

---

## 💾 FILE INVENTORY (Updated)

### **Training Data:**
```
training/
├── train_data_24c_10p_105FEAT.csv (1.59 GB) - Original
├── val_data_24c_10p_105FEAT.csv (341.6 MB)
├── test_data_24c_10p_105FEAT.csv (341.5 MB)
├── train_data_UNIFIED.csv (NEW - 129 features)
├── val_data_UNIFIED.csv (NEW)
└── test_data_UNIFIED.csv (NEW)
```

### **Models:**
```
trained_models_UNIFIED/
├── EURUSD.sim_xgboost.pkl (NEW)
├── GBPUSD.sim_xgboost.pkl (NEW)
├── USDJPY.sim_xgboost.pkl (NEW)
├── USDCHF.sim_xgboost.pkl (NEW)
├── AUDUSD.sim_xgboost.pkl (NEW)
├── USDCAD.sim_xgboost.pkl (NEW)
├── NZDUSD.sim_xgboost.pkl (NEW)
└── EURGBP.sim_xgboost.pkl (NEW)
```

### **Walk-Forward Results:**
```
walk_forward_results/
├── optimal_params.json
├── walk_forward_results.csv
├── strategy_wfe_scores.csv
└── parameter_stability.csv
```

### **Scripts (To Create):**
```
generate_strategy_signals.py (NEW)
create_unified_dataset.py (NEW)
walk_forward_optimization.py (NEW)
train_unified_xgboost.py (NEW)
setup_live_feature_extraction.py (NEW)
live_trading_system_v4_UNIFIED.py (NEW)
```

---

## 🎯 SUCCESS CRITERIA

### **Phase 1 Complete When:**
- [ ] Strategy signals generated for all training samples
- [ ] 24 new columns added (12 strategies × 2 outputs each)
- [ ] No NaN values in strategy signals
- [ ] File saved as train_data_UNIFIED.csv

### **Phase 2 Complete When:**
- [ ] Walk-forward completed on 3+ windows
- [ ] WFE > 0.6 for majority of strategies
- [ ] Optimal parameters identified
- [ ] Parameters stable across windows

### **Phase 3 Complete When:**
- [ ] 8 XGBoost models trained
- [ ] All models >85% validation accuracy
- [ ] Predictions show reasonable class distribution
- [ ] Models saved to trained_models_UNIFIED/

### **Phase 4 Complete When:**
- [ ] Live feature extraction produces 129 features
- [ ] Features match training calculation exactly
- [ ] Validation test passes

### **Phase 5 Complete When:**
- [ ] Paper trading running without errors
- [ ] Trades being executed
- [ ] Logs showing activity
- [ ] Ready for overnight monitoring

---

## 📈 EXPECTED PERFORMANCE TARGETS

### **After Tonight's Implementation:**

| Metric | Current | Target | Stretch |
|--------|---------|--------|---------|
| Win Rate | 37% | 50-55% | 58%+ |
| Profit Factor | ~0.8 | 1.3-1.5 | 1.8+ |
| Max Drawdown | Uncontrolled | <5% | <3% |
| Sharpe Ratio | Unknown | 1.5 | 2.0+ |
| WFE | N/A | >0.6 | >0.7 |

### **FTMO Evaluation Timeline:**

| Phase | Duration | Cumulative |
|-------|----------|------------|
| Tonight's implementation | 6-8 hours | Day 1 |
| Paper trading validation | 2-5 days | Day 3-6 |
| Adjustments if needed | 1-2 days | Day 5-8 |
| FTMO Challenge start | Day 8-10 | |
| FTMO Challenge complete | 10-20 trading days | Day 18-30 |

---

## 🔧 ANTI-OVERSIGHT PROTOCOL

### **BEFORE Each Phase:**
- [ ] Read this section of handoff
- [ ] Verify input files exist
- [ ] Check disk space (need 5+ GB free)
- [ ] Confirm Python environment activated

### **AFTER Each Phase:**
- [ ] Verify output files created
- [ ] Check file sizes reasonable
- [ ] Run validation script
- [ ] Update handoff with results
- [ ] Commit to version control (if applicable)

### **RECURRING ISSUES TO WATCH:**
1. **Feature count mismatch** - Always verify 129 columns
2. **Symbol suffix** - .sim for demo
3. **Label mapping** - 0=SELL, 1=HOLD, 2=BUY
4. **Data staleness** - Check timestamps
5. **Memory overflow** - Monitor during training

---

## 📚 VERSION HISTORY

**v77 (2025-11-17 23:00):** Unified training implementation plan
- Complete walk-forward optimization approach
- Strategies integrated as features (129 total)
- CPU optimization commands
- Risk mitigation solutions
- Paper trading deployment plan

**v76 (2025-11-17 13:20):** 105-feature integration, neural network issue
**v75 (2025-11-16 22:45):** Feature modules created
**v74 (2025-11-16 18:30):** Feature audit complete

---

## 🚀 IMMEDIATE NEXT ACTION

**START HERE:**

1. **Create generate_strategy_signals.py**
   - This generates strategy outputs for all training samples
   - Adds 24 new columns to dataset
   - Foundation for everything else

2. **Run with:**
```powershell
cd C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System
.\venv_lite\Scripts\python.exe generate_strategy_signals.py
```

**Ready to proceed? Confirm and I'll create the first script.**

---

**END OF MASTER HANDOFF v77**

**Status:** Implementation plan documented, ready to execute
**Next:** Create generate_strategy_signals.py → Generate unified dataset
**Blocker:** None - all prerequisites in place
**Critical:** Complete all 5 phases tonight, start paper trading before sleep
