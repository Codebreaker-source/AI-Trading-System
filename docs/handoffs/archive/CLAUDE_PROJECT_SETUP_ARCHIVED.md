# CLAUDE PROJECT SETUP - v83 (2025-12-02)

**Project:** AI Trading System - LITE  
**Version:** v83  
**Status:** ✅ EA/PYTHON SYNCED | ✅ MT5 CALENDAR | ✅ 16 MODELS ACTIVE

---

## 🎯 CURRENT PROJECT STATUS

### **Dec 02, 2025 Updates:**
- ✅ EA v2.33 with Python sync (lot 0.01, confidence 0.35)
- ✅ MT5 calendar export integrated (calendar_events.csv)
- ✅ news_integration.py v2.1 with MT5 calendar
- ✅ CatBoost DISABLED - now XGBoost + LightGBM only
- ✅ 4-dimension signal validation working

### **Live System Status:**
- ✅ 16 models active (8 XGBoost + 8 LightGBM)
- ✅ 58 features base, 108 expanded
- ✅ 9 rule-based strategies (currently disabled)
- ✅ 6-factor confluence scoring
- ✅ EA v2.33 with calendar export

---

## 📂 PROJECT KNOWLEDGE FILES

### **8 Core Documents (All Updated to v83):**

| # | File | Version | Purpose |
|---|------|---------|---------|
| 1 | MASTER_PROJECT_HANDOFF.md | v83 | Main status & architecture |
| 2 | FILE_INVENTORY.md | v83 | All file locations |
| 3 | DATA_PIPELINE_FLOW.md | v83 | Complete data flow |
| 4 | TECHNICAL_SPECIFICATIONS.md | v83 | Feature specs |
| 5 | QUICK_SETUP_GUIDE.md | v83 | Quick reference |
| 6 | SESSION_SUMMARY.md | Dec 02 | Session notes |
| 7 | CLAUDE_PROJECT_SETUP.md | v83 | This file |
| 8 | DOCUMENTATION_COMPLETE.md | v83 | Doc status |

### **Additional Files:**
- CUSTOM_INSTRUCTIONS.txt - User rules
- Continuation prompt.md - Next session template (v83)

---

## 🤖 CLAUDE CUSTOM INSTRUCTIONS

### **Critical Rules:**

**1. ALWAYS Read Handoff First**
- Before responding to ANY user message
- Check MASTER_PROJECT_HANDOFF.md for current status
- Reference "IMMEDIATE NEXT STEPS" section
- Understand current blocker (if any)

**2. ALWAYS Clarify Before Coding**
- Explain what you plan to do BEFORE doing it
- Get explicit permission for code changes
- Never add/remove code without permission
- Ask questions when requirements ambiguous

**3. ALWAYS Provide Full Files**
- Give complete copy-paste file versions
- NOT code snippets
- NOT partial updates
- Full, executable files

**4. ALWAYS Explain Thought Process**
- Share reasoning before executing
- Explain trade-offs of different approaches
- Point out potential issues
- Offer alternatives when uncertain

**5. NEVER Give Up**
- Persist through difficulties
- Debug systematically
- Try multiple approaches
- Don't suggest compromises easily

---

## 📋 FILE UPDATE PROTOCOL

### **After Completing Any Task:**

1. **Create Backup First:**
   ```
   Archive/MASTER_PROJECT_HANDOFF_YYYYMMDD_vXX.md
   ```

2. **Update MASTER_PROJECT_HANDOFF.md:**
   - "Last Updated" timestamp
   - "Current Blocker" section
   - Phase Status Tracker
   - "Immediate Next Steps"
   - Version History

3. **Update Other Relevant Docs:**
   - FILE_INVENTORY.md (if files created/moved)
   - SESSION_SUMMARY.md (major milestones)
   - DOCUMENTATION_COMPLETE.md (doc status)

---

## 📁 FOLDER STRUCTURE (CURRENT v83)

```
Phase4_LITE_System/
├── ACTIVE PYTHON FILES:
│   ├── live_trading_system_v5_treebased.py  ← MAIN
│   ├── ensemble_predictor_v3_treebased.py
│   ├── mt5_calendar_reader.py               ← NEW
│   ├── news_integration.py (v2.1)
│   ├── feature_expander.py
│   └── rule_based_strategies_v1_0.py
│
├── ACTIVE DIRECTORIES:
│   ├── confluence/                (6 modules)
│   ├── dimensions/                (4-dimension validation)
│   ├── trained_models_105FEAT/    (16 active models)
│   ├── logs/                      (system logs)
│   ├── config/                    (configurations)
│   └── venv_lite/                 (Python env)
│
├── MT5 FILES:
│   ├── latest_features.csv        (EA writes)
│   ├── trade_commands.csv         (Python writes)
│   ├── calendar_events.csv        (EA writes) ← NEW
│   └── open_positions.csv         (EA writes)
│
└── DOCUMENTATION:
    └── 0.1-Handoff Checklists/    (8 core docs)
```

---

## 🎯 KEY PROJECT PRINCIPLES

### **1. Deploy-First Optimization**
- Train with default parameters
- Deploy to demo ASAP
- Optimize based on REAL execution data
- Don't over-optimize on backtests

### **2. Data Quality > Model Complexity**
- Validate training data thoroughly
- Check for frozen prices (.sim symbols)
- Ensure proper time-based splits
- Verify label distribution

### **3. Memory Management is Critical**
- System has 5-8 GB RAM
- Use chunked loading (10K rows)
- Sequential processing
- Aggressive cleanup after each step

### **4. 93% HOLD is Normal**
- Forex reality: Most time = no trade
- Models should be selective
- This distribution is GOOD, not bad
- Focus on accuracy of SELL/BUY predictions

### **5. Keep System Clean**
- Only essential files in ROOT
- Old files go to _SAFE_TO_DELETE/
- Uncertain files go to _NEEDS_REVIEW/
- Document everything

---

## 🚨 CRITICAL WARNINGS

### **What NOT to Do:**

**❌ DON'T:**
- Change code without permission
- Provide code snippets instead of full files
- Assume requirements without asking
- Give up when encountering problems
- Create new files without organizing
- Leave old versions cluttering directories

**✅ DO:**
- Always clarify first
- Provide full working files
- Ask questions when uncertain
- Persist through difficulties
- Move old files to _SAFE_TO_DELETE/
- Keep documentation current

---

## 📊 CURRENT SYSTEM CONTEXT

### **System Architecture (v83):**
```
MT5 Bridge EA v2.33 CALENDAR
    ↓ (writes 58 features every 3 sec)
    ↓ (writes calendar every 5 min)
latest_features.csv + calendar_events.csv
    ↓ (reads + expands to 108)
Python System (live_trading_system_v5_treebased.py)
    ↓ (loads)
XGBoost + LightGBM (16 models) + Confluence + Dimensions
    ↓ (generates)
trade_commands.csv
    ↓ (reads)
MT5 Bridge EA v2.33
    ↓ (executes)
Trade Execution (lot 0.01, confidence 0.35)
```

### **Key Paths:**
```
System: C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System\
Docs:   Phase4_LITE_System\0.1-Handoff Checklists\
Models: Phase4_LITE_System\trained_models_105FEAT\
EA:     C:\...\MetaQuotes\Terminal\EE0304F13905552AE0B5EAEFB04866EB\MQL5\Experts\
Files:  C:\...\MetaQuotes\Terminal\EE0304F13905552AE0B5EAEFB04866EB\MQL5\Files\
```

---

## ✅ SESSION START CHECKLIST

**Before Any Work:**
- [ ] Read MASTER_PROJECT_HANDOFF.md (v83)
- [ ] Check EA v2.33 is running
- [ ] Verify lot size = 0.01 in EA Inputs
- [ ] Verify confidence = 0.35 in EA Inputs
- [ ] Confirm user's goal

**During Work:**
- [ ] Clarify before coding
- [ ] Provide full files
- [ ] Explain reasoning
- [ ] Get approvals
- [ ] Test changes

**After Work:**
- [ ] Update documentation
- [ ] Create backups
- [ ] Summarize what was done
- [ ] Identify next steps

---

## 🔧 CONFIGURATION REFERENCE (v83)

| Setting | EA v2.33 | Python v5 |
|---------|----------|-----------|
| Account | 1600054407 | - |
| Lot Size | 0.01 | 0.01 |
| Min Confidence | 0.35 | 0.35 |
| Confluence | - | 0.35 |
| Models | - | XGB + LGB |
| Weights | - | [0.50, 0.50] |
| Calendar | Exports | Reads |
| ATR Filter | 8-100 pips | - |

---

**END OF CLAUDE_PROJECT_SETUP v80**
