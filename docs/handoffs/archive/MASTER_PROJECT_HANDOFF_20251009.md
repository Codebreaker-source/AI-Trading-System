# 🎯 MASTER PROJECT HANDOFF - AI TRADING SYSTEM
**Last Updated**: 2025-10-09 00:00:00  
**Project Status**: LITE System Phase 2 - Data Collection (DATA LOSS BUG FIXED)  
**Current Blocker**: Need to migrate to data_accumulator_v2_BACKUP.py  
**Next Session Starts Here**: See IMMEDIATE NEXT STEPS section below

---

## 🚨 CRITICAL: READ THIS FIRST

**TWO PARALLEL WORKSTREAMS:**
1. **FULL COMPLEX SYSTEM** (PAUSED) - 12-bot ensemble with transformers, Azure Docker containers - complex neural architecture
2. **LITE SIMPLIFIED SYSTEM** (ACTIVE) - Single LSTM bot, can run locally or Azure Functions - FOCUS ON THIS FIRST

**STRATEGY**: Get LITE system working end-to-end BEFORE resuming full complex system.

**LATEST DEVELOPMENT (2025-10-09)**: 
- ❌ **Bug Found**: Original data_accumulator.py had file overwrite bug causing data loss (7,860 → 3,890 samples)
- ✅ **Bug Fixed**: Created data_accumulator_v2_BACKUP.py with comprehensive 5-layer backup system
- ⏳ **Status**: Ready to migrate to v2.0, then resume data collection

---

## 📋 PROJECT OVERVIEW

### LITE System (Current Focus)
**Goal**: Build lightweight LSTM trading system that:
- Monitors 2-3 currency pairs (EURUSD, GBPUSD)
- Uses 65 technical indicators as features  
- Makes BUY/SELL/HOLD decisions every 2 seconds
- Executes trades automatically via MT5
- Runs on local VM or Azure Functions

**Why LITE First**: Validates architecture quickly (2-3 weeks vs 3+ months for full system)

### Full System (Future)
**Goal**: Enterprise-grade 12-bot ensemble system that:
- Monitors 39 instruments (forex, metals, indices)
- Uses 12 specialized neural networks
- Transformer coordinator for meta-learning
- Runs on Azure Docker containers
- Advanced risk management and portfolio optimization

---

## 🎯 CURRENT STATUS SNAPSHOT

### What's Working ✅
1. ✅ LSTM Model: 0.67MB, 2.75ms inference, 175K params (Phase 1 complete)
2. ✅ Bridge EA: Writing 65 features every 2s to local CSV
3. ✅ Azure Uploader: Uploading to Azure File Share every 2s
4. ✅ Azure Infrastructure: Storage account, file share, all configured
5. ✅ Test Suite: 10/10 tests passed, model optimized for deployment

### What's Broken/Fixed ❌→✅
1. ❌ data_accumulator.py had file overwrite bug → ✅ Fixed in v2.0 with backup system
2. ✅ New v2.0 has 5 protection layers (see details in BACKUP_SYSTEM_README.md)

### What's Pending ⏳
1. ⏳ Migrate to data_accumulator_v2_BACKUP.py (IMMEDIATE - see steps below)
2. ⏳ Collect 10,000+ samples (2-3 days with v2.0)
3. ⏳ Label data (5 min)
4. ⏳ Train model (15 min)
5. ⏳ Deploy and test (Phase 3-6)

### Current Sample Count
- **Yesterday (2025-10-08 01:37)**: 7,860 samples
- **Today (2025-10-09 00:00)**: 3,898 samples  
- **Status**: Lost ~4,000 samples due to bug (NOW FIXED in v2.0)

---

## 🔧 IMMEDIATE NEXT STEPS (DO THIS NOW)

### STEP 1: Stop Old Data Accumulator
```powershell
# If data_accumulator.py is running, press Ctrl+C to stop it
```

### STEP 2: Check Current Status & Restore if Needed
```powershell
cd C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System
venv_lite\Scripts\activate
python training\verify_and_recover.py --check
```

**If verify shows a backup has MORE samples than current:**
```powershell
python training\verify_and_recover.py --restore
```

### STEP 3: Start New Data Accumulator v2.0
```powershell
python training\data_accumulator_v2_BACKUP.py
```

**Expected output:**
```
============================================================
LIVE DATA ACCUMULATOR v2.0 (WITH BACKUP) - Starting
============================================================
Local backup dir: C:\...\backups
Azure backup dir: training_data/backups
Max local backups: 5
Max Azure backups: 3

✓ Local backup created: accumulated_20251009_000512.csv (3,900 samples)
✓ Azure backup created: training_data/backups/accumulated_20251009_000512.csv
✓ Write verified: 3,900 samples written to Azure
✓ Successfully collected 2 new samples
```

### STEP 4: Verify Backups Being Created (5 min later)
```powershell
dir backups\
# Should see timestamped CSV files
```

### STEP 5: Monitor Progress
```powershell
python training\check_collection_progress.py
# Run every hour to track progress
```

**Target**: 10,000+ samples (enough for quick training)  
**ETA**: ~2-3 days at current rate

---

## 📊 PHASE STATUS TRACKER

### ✅ PHASE 0: Infrastructure (COMPLETE)
- Azure Storage Account: tradingsystem12345
- File Share: csv-exchange (100GB)
- Connection strings configured
- MT5 Bridge EA operational

### ✅ PHASE 1: LSTM Model (COMPLETE) 
- Model: ama_scalper_lstm_v1.py
- Tests: 10/10 passed
- Performance: 0.67MB, 2.75ms inference, 0.02s cold start
- **Status**: EXCELLENT - ready for deployment

### 🔄 PHASE 2: Data Collection (IN PROGRESS - 40% COMPLETE)
**Completed:**
- [x] Bridge EA writing data
- [x] Azure uploader operational
- [x] Data accumulator created
- [x] Data labeler ready
- [x] Progress checker ready
- [x] **NEW**: Bug fixed with v2.0 backup system

**In Progress:**
- [ ] Migrate to data_accumulator_v2_BACKUP.py (IMMEDIATE)
- [ ] Collect 10,000+ samples (2-3 days)
- [ ] Verify 24h stability
- [ ] Label data

**Next Actions:**
1. Stop old data_accumulator.py
2. Run verify_and_recover.py --check
3. Restore from backup if needed
4. Start data_accumulator_v2_BACKUP.py
5. Monitor for 24h

### ⏳ PHASE 3: Train Model (NOT STARTED)
- Estimated Duration: 15-30 minutes
- Prerequisites: 10,000+ labeled samples
- Files to Create:
  - training/quick_train.py (CREATED - ready to use)
  - Trained weights output

### ⏳ PHASE 4: Deploy (NOT STARTED)
- Option A: Local deployment (immediate)
- Option B: Azure Functions (production)
- Files to Create:
  - live_trading_system.py (CREATED - ready to use)

### ⏳ PHASE 5: Test (NOT STARTED)
- Integration test: Bridge EA → LSTM → Execution
- Stability test: 24-48h continuous
- Demo account validation

### ⏳ PHASE 6: Live Trading (NOT STARTED)
- 1 week demo profitability required
- Risk management verification
- Go live

---

## 🗂️ FILE LOCATIONS

### Core System Files
```
Phase4_LITE_System/
├── models/
│   └── ama_scalper_lstm_v1.py              [COMPLETE] LSTM model
├── training/
│   ├── data_accumulator.py                 [OLD - HAS BUG - DON'T USE]
│   ├── data_accumulator_v2_BACKUP.py       [NEW - USE THIS]
│   ├── verify_and_recover.py               [NEW - RECOVERY TOOL]
│   ├── data_labeler.py                     [READY]
│   ├── quick_train.py                      [READY]
│   └── check_collection_progress.py        [READY]
├── config/
│   └── trading_config.json                 [COMPLETE]
├── backups/                                [AUTO-CREATED BY V2.0]
│   └── accumulated_YYYYMMDD_HHMMSS.csv    [TIMESTAMPED BACKUPS]
├── logs/
│   ├── data_accumulator.log                [OLD]
│   └── data_accumulator_v2.log             [NEW]
├── azure_uploader.py                       [RUNNING]
├── live_trading_system.py                  [READY FOR PHASE 4]
├── BACKUP_SYSTEM_README.md                 [DOCUMENTATION]
└── IMPLEMENTATION_SUMMARY.md               [QUICK START GUIDE]
```

### Handoff Documentation
```
0.1-Handoff Checklists/
├── MASTER_PROJECT_HANDOFF.md               [THIS FILE - ALWAYS READ FIRST]
├── Archive/
│   └── MASTER_PROJECT_HANDOFF_YYYYMMDD.md [DATED BACKUPS]
├── Handoff Phase 1 doc.md                  [REFERENCE]
├── Handoff Phase 2 doc.md                  [REFERENCE]
└── Handoff Phase 2 part 2 doc.md           [REFERENCE - DATA LOSS ISSUE]
```

---

## 🐛 BUG FIX DETAILS - DATA LOSS ISSUE

### Problem Identified
**File**: `training/data_accumulator.py` (v1.0)  
**Bug**: File overwrite without safety checks  
**Impact**: Sample count decreased from 7,860 → 3,890 (lost ~4,000 samples)  
**Root Cause**: Azure file overwritten without backup if read operation failed

### Solution Implemented  
**File**: `training/data_accumulator_v2_BACKUP.py`  
**Fix**: 5-layer protection system

**Protection Layers:**
1. **Sample Count Detection** - Refuses write if count decreases
2. **Local Backups** - Saves to backups/ folder before every write (keeps last 5)
3. **Azure Backups** - Copies to Azure backups/ before overwriting (keeps last 3)
4. **Write Verification** - Reads back after write to confirm success
5. **Auto-Recovery** - Falls back to local backup if Azure read fails

**Storage Impact**: ~20-30MB total, <$0.01/month  
**Performance Impact**: +120-230ms per cycle (still within 2s cycle time)

### Migration Status
- ✅ v2.0 created and tested
- ✅ verify_and_recover.py created
- ✅ Documentation complete
- ⏳ Need to migrate (user action required)

---

## 🔑 KEY TECHNICAL SPECS

### LSTM Model
```python
Architecture: Bidirectional LSTM
- Input: (batch, 20 sequences, 65 features)
- Hidden: 2 layers, 64 units each, bidirectional
- Output: (batch, 3) [BUY, SELL, HOLD] probabilities
- Attention: Feature attention layer (prioritizes MAs)
- Size: 0.67 MB
- Parameters: 175,493
- Inference: 2.75ms average
- Cold Start: 0.02s
```

### Feature Set (65 Features)
**Categories:**
- Price Data: OHLC, Volume (5)
- Moving Averages: MA, EMA, AMA (14)
- Momentum: RSI, MACD, Stochastic, CCI, Williams %R (10)
- Volatility: ATR, Bollinger Bands, StdDev (8)
- Trend: ADX, DI, Parabolic SAR (4)
- Volume: Volume MA, OBV, Volume ROC (3)
- Patterns: Support/Resistance, Pivots (3)
- Custom: MA distances, crossovers, regime (9)
- Sessions: Asian, European, US (3)
- Time: Hour, Day of week (2)
- Additional: ROC, ranges, spread (6)

### Data Pipeline
- **Collection**: Every 2 seconds
- **Target**: 10,000+ samples (minimum), 50,000+ (ideal)
- **Labeling**: Forward-looking (10 candles, ±20 pips)
- **Training Split**: 70% train, 15% val, 15% test
- **Expected Labels**: BUY 15-25%, SELL 15-25%, HOLD 50-70%

### Azure Infrastructure
- **Storage Account**: tradingsystem12345 (Standard LRS, East US)
- **File Share**: csv-exchange (100GB)
- **Paths**:
  - Input: market_data/latest_features.csv
  - Accumulated: training_data/accumulated_features.csv
  - Backups: training_data/backups/accumulated_*.csv
  - Labeled: training_data/labeled_data.csv

### MT5 Configuration
- **Active Instance**: D35B57988819A3E61EA69BCE2D92B103
- **Files Path**: C:\Users\mt5-admin\AppData\Roaming\MetaQuotes\Terminal\D35B57988819A3E61EA69BCE2D92B103\MQL5\Files
- **Bridge EA**: BridgeEA_LITE_v1.0.mq5 (compiled and running)
- **Active Pairs**: EURUSD, GBPUSD
- **Timeframe**: M5 (5-minute)
- **Update Interval**: 2 seconds

---

## 💾 BACKUP & RECOVERY

### Backup Locations
**Local Backups:**
- Path: `backups/accumulated_YYYYMMDD_HHMMSS.csv`
- Retention: Last 5 backups
- Rotation: Automatic
- Frequency: Every collection cycle (2s)

**Azure Backups:**
- Path: `csv-exchange/training_data/backups/accumulated_YYYYMMDD_HHMMSS.csv`
- Retention: Last 3 backups
- Rotation: Automatic
- Frequency: Every collection cycle (only if file exists)

### Recovery Commands
```powershell
# Check status and list backups
python training\verify_and_recover.py --check

# List all available backups
python training\verify_and_recover.py --list

# Restore from best backup
python training\verify_and_recover.py --restore

# Check data integrity
python training\verify_and_recover.py --integrity
```

---

## 🎛️ MONITORING COMMANDS

### Collection Progress
```powershell
python training\check_collection_progress.py
```

### Verify Backups
```powershell
dir backups\
```

### Check Logs
```powershell
# v1.0 log (old)
type logs\data_accumulator.log | more

# v2.0 log (new)
type logs\data_accumulator_v2.log | more
```

### Diagnose CSV
```powershell
python diagnose_csv.py
```

---

## 🚨 TROUBLESHOOTING GUIDE

### Issue: "REFUSING TO OVERWRITE - Data integrity protection"
**Cause**: v2.0 detected sample count decrease  
**Action**: This is GOOD - data loss prevented  
**Fix**: Run `verify_and_recover.py --restore`

### Issue: Sample count not increasing
**Check**:
1. Bridge EA running? (MT5 Experts tab)
2. azure_uploader.py running? (Terminal 1)
3. data_accumulator_v2_BACKUP.py running? (Terminal 2)

**Fix**: Restart any stopped components

### Issue: No backups being created
**Check**: Look in backups/ folder  
**Expected**: New CSV files every few minutes  
**Fix**: Check logs/data_accumulator_v2.log for errors

### Issue: Want to restore older data
**Action**:
1. Run `verify_and_recover.py --list`
2. Find desired backup timestamp
3. Run `verify_and_recover.py --restore`

---

## 📈 SUCCESS CRITERIA

### Phase 2 Success (Current)
- [ ] Migrated to v2.0 ✅ (files created, need to start)
- [ ] Backups being created regularly
- [ ] 10,000+ samples collected
- [ ] 24h stability without crashes
- [ ] Data labeled successfully

### Phase 3 Success (Training)
- [ ] Model trains without errors
- [ ] Validation accuracy >55%
- [ ] Not overfitting (train/val gap <10%)
- [ ] Reasonable prediction distribution

### Phase 4 Success (Deployment)
- [ ] Model loads successfully
- [ ] Makes predictions every 2 seconds
- [ ] Writes decisions to CSV correctly
- [ ] Execution engine can read decisions

### Phase 5 Success (Testing)
- [ ] End-to-end flow works
- [ ] Trades execute in MT5
- [ ] 24-48h stability
- [ ] Decisions are reasonable

### Phase 6 Success (Live)
- [ ] 1 week profitable on demo
- [ ] Drawdown <10%
- [ ] Win rate >45%
- [ ] Go live approved

---

## 🔮 FUTURE ROADMAP

### LITE System Enhancements (After Phase 6)
1. Add 2nd bot (breakout detector)
2. Multi-timeframe analysis (M1, M15)
3. Position sizing optimization
4. Performance dashboard

### Full System Resume (After LITE Complete)
1. Deploy to Azure Docker containers
2. Add remaining 10 bots (12 total)
3. Implement transformer coordinator
4. Scale to 39 instruments
5. Portfolio management
6. Reinforcement learning layer

### Advanced Features (Long-term)
1. Multi-broker support
2. News sentiment integration
3. Order flow analysis
4. Distributed system architecture
5. Automated retraining pipeline

---

## 📚 KEY DOCUMENTATION FILES

### Must Read
- **THIS FILE**: Master status and next steps
- **BACKUP_SYSTEM_README.md**: v2.0 backup system details
- **IMPLEMENTATION_SUMMARY.md**: Quick start guide for v2.0 migration

### Reference
- **PHASE2_README.md**: Phase 2 detailed documentation
- **Handoff Phase 1 doc.md**: Phase 1 completion details
- **Handoff Phase 2 doc.md**: Phase 2 setup details
- **Handoff Phase 2 part 2 doc.md**: Data loss issue documentation

### Configuration
- **trading_config.json**: System configuration
- **requirements_lite.txt**: Python dependencies

---

## 👤 USER PREFERENCES & CONSTRAINTS

### Communication Style
- ✅ Always clarify before making code changes
- ✅ Provide full copy-paste versions (not snippets)
- ✅ Explain thought process before executing
- ✅ Step-by-step approach preferred
- ✅ Detailed explanations of trade-offs

### Critical Rules
- ❌ NEVER change code without explicit permission
- ❌ NEVER assume functionality - always verify
- ❌ NEVER use code snippets - always full files
- ❌ NEVER skip clarification steps
- ✅ ALWAYS ask before adding/removing functionality

### File Management
- Increment version numbers when updating files
- Keep full name, change version only
- Create backups before major changes
- Document all changes in comments

---

## 🔐 ENVIRONMENT VARIABLES

```powershell
# Set these if not already configured
$env:AZURE_STORAGE_CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=tradingsystem12345;AccountKey=...;EndpointSuffix=core.windows.net"

$env:MT5_FILES_PATH = "C:\Users\mt5-admin\AppData\Roaming\MetaQuotes\Terminal\D35B57988819A3E61EA69BCE2D92B103\MQL5\Files"
```

**Verify with:**
```powershell
echo $env:AZURE_STORAGE_CONNECTION_STRING
echo $env:MT5_FILES_PATH
```

---

## 💰 COST SUMMARY

### Current (LITE System)
- Azure Storage: ~$2/month
- File Share (100GB): ~$5/month
- Data Transfer: <$1/month
- **Total**: ~$8/month

### After Deployment (Phase 4)
- Add Azure Functions: ~$35-45/month
- Add Application Insights: ~$5/month
- **Total**: ~$50-60/month

### Full System (Future)
- Container Instances: ~$150-200/month
- Additional Storage: ~$10/month
- **Total**: ~$165-215/month

---

## 📞 GETTING HELP

### If New AI Session
1. Read this MASTER_PROJECT_HANDOFF.md file FIRST
2. Check IMMEDIATE NEXT STEPS section
3. Review Phase Status Tracker
4. Read relevant documentation in Key Documentation Files section

### If Stuck
1. Check TROUBLESHOOTING GUIDE section above
2. Review logs in logs/ folder
3. Run diagnostic scripts (diagnose_csv.py, verify_and_recover.py)
4. Check that all components are running (Bridge EA, uploader, accumulator)

### If Major Issue
1. DON'T PANIC - all data backed up in v2.0
2. Run `verify_and_recover.py --check`
3. Restore from backup if needed
4. Check logs for error messages
5. Restart components systematically

---

## 🎯 QUICK START FOR NEW AI SESSION

**Copy-paste this into new chat to get started:**

```
I'm continuing work on the AI Trading System project. 

Please read:
C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System\0.1-Handoff Checklists\MASTER_PROJECT_HANDOFF.md

Current status: LITE System Phase 2 - migrating to data_accumulator_v2_BACKUP.py after fixing data loss bug.

Please confirm you've read the master handoff file and understand where we are in the project.
```

---

## 📝 VERSION HISTORY

### v1.0.0 - 2025-10-09 00:00:00
- Initial comprehensive master handoff created
- Consolidated all previous handoff docs
- Added backup system documentation
- Added data loss bug fix details
- Structured for easy programmatic updates

---

**END OF MASTER PROJECT HANDOFF**

*This file is the single source of truth for project status.*  
*Always read this file first when starting a new AI session.*  
*Backup created automatically in Archive folder before each update.*

---

## 🤖 FOR AI ASSISTANTS: HOW TO UPDATE THIS FILE

### When to Update
- After completing any phase or sub-step
- After discovering/fixing bugs
- After major decisions or architecture changes
- After creating new files or tools
- Daily during active development

### How to Update
1. **ALWAYS backup first**: Copy current version to Archive/MASTER_PROJECT_HANDOFF_YYYYMMDD.md
2. **Update "Last Updated" timestamp** at top
3. **Update "Current Blocker"** section
4. **Update Phase Status Tracker** - check/uncheck boxes
5. **Update "Current Sample Count"** if applicable
6. **Update "Immediate Next Steps"** - what to do NOW
7. **Add to Version History** at bottom
8. **Increment version number** if major changes

### Auto-Update Template
```python
# Pseudo-code for automatic updates
1. Read current MASTER_PROJECT_HANDOFF.md
2. Create backup: Archive/MASTER_PROJECT_HANDOFF_{date}.md
3. Update relevant sections based on completion
4. Write updated file
5. Verify backup exists
```

### Critical Sections to Keep Updated
- Last Updated timestamp
- Current Blocker
- Phase Status Tracker (checkboxes)
- Current Sample Count
- Immediate Next Steps
- File Locations (if new files created)
- Success Criteria (check off completed items)

---

**THIS IS THE MASTER FILE - KEEP IT CURRENT!**
