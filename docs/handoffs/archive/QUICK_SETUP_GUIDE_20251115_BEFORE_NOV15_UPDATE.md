# QUICK SETUP GUIDE - v67 (2025-11-10 17:30 UTC)

**System:** AI Trading System - 7 Pairs Active  
**Status:** 🚀 **LIVE DEMO** - ⚠️ Confidence Calibration Issues Discovered  
**Latest Update:** MT5 Account Credentials Updated (Nov 10)

---

## 🔐 MT5 ACCOUNT INFORMATION (Updated Nov 10, 2025)

**Active Trading Account:**
- **Broker:** OANDA-Prop Trader
- **Login:** 600013344
- **Master Password:** rzH478?@G
- **Server:** OANDA-Prop Trader
- **Account Type:** Prop Trader / Demo
- **Updated:** 2025-11-10 17:30 UTC

**Terminal Path:**
- `C:\Users\mt5-admin\AppData\Roaming\MetaQuotes\Terminal\EE0304F13905552AE0B5EAEFB04866EB\`

**Risk Settings:**
- Max Lot Size: 0.1 per trade
- Stop Loss: 2× ATR (dynamic)
- Take Profit: 4× ATR (2:1 R/R)
- Confidence-based sizing enabled

---

## ⚡ CURRENT STATUS (November 10, 2025)

### **🚀 System Active:**
- ✅ 21/24 models trained and deployed
- ✅ 7 pairs active (EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD)
- ✅ EA v2.22_OPTIMIZED attached and executing trades
- ✅ MCP monitoring server available
- ⚠️ **CONFIDENCE MISCALIBRATION DISCOVERED**
  - High confidence (>85%): 49% win rate ❌
  - Medium confidence (70-85%): 86% win rate ✅
  - Need threshold adjustment to 70-85% range

### **Critical Issues Pending:**
- [ ] Fix profit attribution bug (50% under-counting)
- [ ] Implement execution log backup system
- [ ] Collect 500+ trades per symbol (need 2-4 weeks)
- [ ] Adjust confidence threshold to 70-85% (Phase 1)

---

## ⚡ QUICK START: RESTART SYSTEM

### **STEP 1: Verify Bridge EA Running in MT5**

1. Open MT5
2. Check "Experts" tab for: `BridgeEA_LITE_v2_22_OPTIMIZED initialized`
3. Verify "Algo Trading" button is **GREEN**
4. EA should show: "Features written: 7 symbols" every 2-3 seconds
5. Check for: "Trade executed" messages when signals are generated

**Expected EA Output:**
```
BridgeEA_LITE_v2_22_OPTIMIZED initialized
Features written: 7 symbols
Processing trade commands...
Trade executed: EURUSD.sim BUY 0.02 lots
```

---

### **STEP 2: Restart Python Trading System**

```powershell
cd C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System
python live_trading_system_v3.0.py --config B1 --mode demo --confidence 0.80 --interval 3
```

**⚠️ Note:** Confidence threshold is 0.80 (MISCALIBRATED - will be adjusted to 0.70-0.85 after data collection)

**Expected Output:**
```
[OK] Initializing Trading System v3.0
[OK] Loading models from: trained_models_B1_CLEAN/
[OK] Active pairs: 7 (EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD)
[OK] Confidence threshold: 80%
[OK] System ready

--- Cycle 1 ---
[OK] Reading features from latest_features.csv
[OK] Processing 7 pairs...
  [1/7] EURUSD.sim: HOLD (confidence: 75%)
  [2/7] GBPUSD.sim: BUY (confidence: 85%)
  [3/7] USDJPY.sim: HOLD (confidence: 70%)
  ...
[OK] Wrote 1 trade command(s)
```

**Key Configuration:**
- Config: B1 (24 candles, 10 pips, stratified split)
- Models: `trained_models_B1_CLEAN/`
- Pairs: 7 active (EURGBP excluded - no SELL labels)
- Threshold: 80% (will be adjusted after profit bug fix)

---

### **STEP 3: Set Up MCP Monitoring Server** ⭐ NEW

**Install MCP Server (One-Time Setup):**

```powershell
cd C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System
.\install_mt5_mcp.ps1
```

**The installer will:**
1. Install required packages (mcp, fastmcp)
2. Create Claude Desktop config
3. Set up MT5 MCP server
4. Provide restart instructions

**After Installation:**
1. Restart Claude Desktop
2. MCP server auto-starts when Claude Desktop launches
3. Use monitoring commands in Claude conversations

**Available Monitoring Commands:**
```
"What's my account balance?"           → Real-time account info
"Show me open positions"               → All active trades
"Get recent trades from last 2 hours"  → Trade history
"Trading stats for last week"          → Performance analysis
"What's the current EURUSD price?"     → Symbol information
"Give me a system status check"        → Quick health overview
```

**Documentation:** See `MT5_MCP_SETUP_GUIDE.md` for full details

---

## 📊 SYSTEM OVERVIEW

### **Current Configuration (B1):**

**Training Parameters:**
- Lookforward: 24 candles (2 hours on M5)
- Threshold: 10 pips
- Split Method: Stratified (ensures all classes present)
- Temporal Offset: Features shifted by 1 row

**Model Architecture:**
- 7 active pairs × 3 models = 21 models
- XGBoost: Fast tabular learning
- Transformer: Sequence pattern recognition
- CNN: Spatial feature extraction

**Ensemble Voting:**
- Weighted confidence voting
- ⚠️ Amplifies miscalibration issues
- Need calibration layer (planned Phase 2)

**Risk Management:**
- Confidence: ≥80% (⚠️ needs adjustment to 70-85%)
- Max lot size: 0.04 per order
- Risk/Reward: 2:1 ratio (ATR-based SL/TP)
- Position limit: 1 per pair

---

## 🔍 MONITORING SYSTEM HEALTH

### **Check Python System Status:**

```powershell
# View current process
Get-Process -Name python | Where-Object {$_.Path -like "*live_trading_system*"}

# Check prediction logs (last 10 lines)
Get-Content logs\predictions_v3_B1_demo.csv -Tail 10

# Check trade signals (last 10 lines)
Get-Content logs\trades_v3_B1_demo.csv -Tail 10

# Check system logs for errors
Get-Content logs\system_v3_B1_demo.log -Tail 20
```

### **Check MT5 EA Status:**

1. Open MT5 → Experts tab
2. Look for:
   - `Features written: 7 symbols` (every 2-3 seconds)
   - `Processing trade commands...` (when signals present)
   - `Trade executed: [symbol] [action] [lots]` (when trades execute)
3. Check for errors (highlighted in red)

### **Use MCP Monitoring (Easiest):**

**In Claude Desktop:**
```
"Show me system status"
"What trades did I make today?"
"How's my account performing?"
```

---

## 📈 PERFORMANCE ANALYSIS (Nov 5-8)

### **Overall Results:**
- **Period:** Nov 5-7 (3 days - limited data)
- **Orders:** 555 total, 538 closed
- **Win Rate:** 45.4% (⚠️ below breakeven)
- **MT5 Actual Profit:** $1,379.58 (Oct 29 - Nov 8)

### **Symbol Performance:**
```
AUDUSD: 97.4% win rate (76/78) ✅ EXCELLENT
GBPUSD: 79.4% win rate (27/34) ✅ GOOD
EURUSD: 55.9% win rate (19/34) ✅ ACCEPTABLE
USDCAD: 47.2% win rate (51/108) ⚠️ BELOW TARGET
USDCHF: 17.4% win rate (20/115) ❌ POOR
USDJPY: 0.0% win rate (0/61) ❌ BROKEN
NZDUSD: 0.0% win rate (0/26) ❌ BROKEN
```

### **Confidence Analysis:**
```
High (85-100%):   49.3% win rate (408 orders) ❌ MISCALIBRATED
Medium (70-85%):  86.5% win rate (37 orders)  ✅ SWEET SPOT
Low (60-70%):     11.8% win rate (93 orders)  ❌ POOR
```

**⚠️ Critical Finding:** Models severely overconfident at >85%

---

## 🔧 TROUBLESHOOTING

### **Issue: No Trades Being Executed**

**Check:**
1. Is Python system running? (check processes)
2. Is EA attached? (check MT5 Experts tab)
3. Are signals being generated? (check `trade_commands.csv`)
4. Is confidence threshold too high? (80% may be capturing bad predictions)

**Solution:**
```powershell
# Restart Python system
python live_trading_system_v3.0.py --config B1 --mode demo --confidence 0.80 --interval 3

# Check if commands are being written
Get-Content "C:\Users\mt5-admin\AppData\Roaming\MetaQuotes\Terminal\EE0304F13905552AE0B5EAEFB04866EB\MQL5\Files\trade_commands.csv"
```

### **Issue: High Trading Frequency (Too Many Trades)**

**Possible Cause:** System generating many signals

**Check:**
```powershell
# Count trade commands in last hour
Get-Content logs\trades_v3_B1_demo.csv | Select-String (Get-Date).AddHours(-1).ToString("yyyy-MM-dd HH")
```

**Solution:** This may normalize after confidence threshold adjustment

### **Issue: MCP Server Not Responding**

**Solution:**
```powershell
# Restart Claude Desktop (MCP server auto-restarts)
# Or check installation:
cd C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System
python -m mt5_mcp_server
```

### **Issue: All Predictions Show HOLD**

**Possible Causes:**
- Models not loading correctly
- Features not updating
- Confidence threshold too high

**Check:**
```python
# Test model predictions manually
python -c "from ensemble_predictor_v2_4_ondemand import EnsemblePredictor; \
           predictor = EnsemblePredictor('trained_models_B1_CLEAN'); \
           import pandas as pd; \
           features = pd.read_csv('latest_features.csv'); \
           pred = predictor.predict('EURUSD.sim', features); \
           print(pred)"
```

---

## 🚀 CRITICAL ACTION ITEMS

### **Priority 1: Before Any Retraining**

1. **Fix Profit Attribution Bug:**
   ```powershell
   # Edit collect_trade_outcomes_v2.py
   # Use MT5 actual deal profit instead of proportional attribution
   # Verify: Total profit matches $1,379.58
   ```

2. **Implement Execution Log Backup:**
   ```powershell
   # Create daily backup script
   # Store to: backups/execution_logs/YYYY-MM-DD.csv
   # Keep 30 days retention
   ```

### **Priority 2: Data Collection (2-4 Weeks)**

- Continue trading all 7 pairs
- Monitor daily performance by symbol
- Track confidence vs outcome patterns
- Collect minimum 500 trades per symbol
- **Don't disable poor symbols yet - need more data**

### **Priority 3: Confidence Recalibration**

**Phase 1 (After Profit Fix):**
```python
# Adjust threshold to 70-85% range
# In live_trading_system_v3.0.py:
if 0.70 <= confidence <= 0.85 and prediction != 1:
    execute_trade()
```

**Phase 2 (This Weekend):**
- Train calibration layers (Temperature, Platt, Isotonic)
- Use 538 execution outcomes
- Validate ECE < 0.05

**Phase 3 (2-4 Weeks):**
- Retrain all models with execution data
- Custom loss function (Focal + confidence penalty)
- Full reinforcement learning

---

## 📁 KEY FILE LOCATIONS

### **System Files:**
```
C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System\
├─ live_trading_system_v3.0.py          (Main system)
├─ ensemble_predictor_v2_4_ondemand.py  (Model loader)
├─ trained_models_B1_CLEAN\             (21 models)
├─ logs\                                 (All logs)
│  ├─ predictions_v3_B1_demo.csv
│  ├─ trades_v3_B1_demo.csv
│  └─ system_v3_B1_demo.log
├─ training\
│  ├─ trade_outcomes_v2.csv             (555 orders)
│  └─ reinforcement_dataset_v2.csv      (538 closed)
└─ mt5_mcp_server.py                    (MCP monitoring)
```

### **MT5 Files:**
```
C:\Users\mt5-admin\AppData\Roaming\MetaQuotes\Terminal\EE0304F13905552AE0B5EAEFB04866EB\MQL5\
├─ Files\
│  ├─ latest_features.csv               (7 symbols × 58 features)
│  ├─ trade_commands.csv                (Python → EA)
│  └─ trades_execution_log.csv          (All executions)
└─ Experts\
   └─ BridgeEA_LITE_v2_22_OPTIMIZED.mq5
```

---

## 📚 DOCUMENTATION REFERENCES

**Core Documents (v65):**
1. `MASTER_PROJECT_HANDOFF.md` - Overall project status
2. `FILE_INVENTORY.md` - All file locations
3. `SESSION_SUMMARY.md` - Nov 4-8 session details
4. `TECHNICAL_SPECIFICATIONS.md` - System specifications
5. `DATA_PIPELINE_FLOW.md` - Complete data flow
6. `CONFIDENCE_RECALIBRATION_STRATEGY.md` - Fix plan
7. `MT5_MCP_SETUP_GUIDE.md` - MCP server documentation

**Analysis Scripts:**
- `collect_trade_outcomes_v2.py` - Order outcome tracking
- `analyze_confidence_calibration.py` - Calibration analysis
- `check_mt5_actual_profit.py` - Profit verification

---

## 🎯 EXPECTED BEHAVIOR

### **Normal Operation:**
- **Predictions:** Every 3 seconds for all 7 pairs
- **Trade Signals:** Variable (depends on market conditions and confidence)
- **Execution:** Immediate when signal meets threshold
- **Logging:** Continuous to all log files

### **With Current Miscalibration:**
- **High confidence predictions (>85%):** Often WRONG (49% win rate)
- **Medium confidence (70-85%):** Usually RIGHT (86% win rate)
- **Low confidence (<70%):** Often WRONG (11% win rate)

### **After Phase 1 Threshold Adjustment:**
- **Expected win rate:** 86% (targeting 70-85% range)
- **Trade frequency:** Lower but much better quality
- **System behavior:** More conservative, fewer bad trades

---

## ⚠️ CRITICAL WARNINGS

1. **Don't retrain models yet** - Fix profit bug first
2. **Don't disable symbols prematurely** - Need 500+ trades each
3. **Don't trust high confidence (>85%)** - Severely miscalibrated
4. **Don't skip backup system** - Prevent data loss like October trades
5. **Do collect 2-4 weeks of data** - Need statistical significance

---

**LAST UPDATED:** 2025-11-10 17:30 UTC  
**VERSION:** v67  
**STATUS:** 🚀 Live (7 pairs) - ⚠️ Confidence issues discovered  
**ACCOUNT:** OANDA-Prop Trader (Login: 600013344)  
**NEXT ACTIONS:** Restart system with new account, fix profit bug, backup system, data collection

---
