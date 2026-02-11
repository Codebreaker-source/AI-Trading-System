# CONTINUATION PROMPT FOR NEXT SESSION

## 🎯 COPY THIS AT START OF NEXT CLAUDE SESSION

```
PROJECT: AI Trading System - Phase 4 LITE (Ensemble: 16 Active Models)

CURRENT STATUS (Dec 02, 2025):
✅ EA v2.33 SYNCED WITH PYTHON
✅ MT5 CALENDAR INTEGRATION WORKING
✅ 16 ACTIVE MODELS (XGBoost + LightGBM)
❌ CatBoost DISABLED

CRITICAL SYNC (EA ↔ Python):
- Lot Size: 0.01 (both)
- Min Confidence: 0.35 (both)
- Confluence: 0.35 (Python only)

READ THESE FILES FIRST:
C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System\0.1-Handoff Checklists\
├─ MASTER_PROJECT_HANDOFF.md (v83 - overall status)
├─ FILE_INVENTORY.md (all file locations)
├─ DATA_PIPELINE_FLOW.md (complete data flow)
├─ QUICK_SETUP_GUIDE.md (quick reference)
└─ SESSION_SUMMARY.md (Dec 02 session notes)

SYSTEM DETAILS:
- EA Version: BridgeEA_LITE_v2_33_CALENDAR.mq5
- Python: live_trading_system_v5_treebased.py
- Timeframe: M15
- Models: XGBoost (85%) + LightGBM (87%)
- Weights: Equal [0.50, 0.50]
- Pairs: 8 (EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD, EURGBP)
- Account: OANDA 1600054407 (Demo)

NEW IN v83:
- mt5_calendar_reader.py - Reads EA calendar export
- news_integration.py v2.1 - MT5 calendar as primary
- calendar_events.csv - EA exports every 5 min
- 4-dimension signal validation

IMMEDIATE NEXT STEPS:
1. Monitor live trading with synced settings
2. Verify calendar blocking works during news
3. Collect 500+ trades for model optimization
4. Consider re-enabling CatBoost after analysis

CRITICAL USER PREFERENCES:
1. ALWAYS clarify before making code changes
2. Provide FULL file versions (not snippets)
3. Explain thought process before executing
4. Ask questions when requirements ambiguous
5. Never add/remove code without explicit permission
```

---

## 📋 SESSION START CHECKLIST

### Before Starting Work
- [ ] Read MASTER_PROJECT_HANDOFF.md (v83)
- [ ] Review QUICK_SETUP_GUIDE.md
- [ ] Check SESSION_SUMMARY.md (context)
- [ ] Verify EA v2.33 is running

### Verify System State
- [ ] EA v2.33 deployed? (Check MT5)
- [ ] Lot size = 0.01? (Verify in EA Inputs)
- [ ] Confidence = 0.35? (Verify in EA Inputs)
- [ ] Calendar export working? (Check calendar_events.csv)

### Key File Locations
```
EA: MQL5/Experts/BridgeEA_LITE_v2_33_CALENDAR.mq5
Python: Phase4_LITE_System/live_trading_system_v5_treebased.py
Calendar: MQL5/Files/calendar_events.csv
Models: Phase4_LITE_System/trained_models_105FEAT/
```

---

## 🎓 QUICK CONTEXT SUMMARY

### What's Deployed
- EA v2.33 with calendar export and Python sync
- Python V5 with XGBoost + LightGBM ensemble
- MT5 calendar integration (48 events, 7 HIGH impact)
- 4-dimension signal validation
- 6-factor confluence scoring

### How It Works
1. **EA v2.33** → Writes features every 3 sec + calendar every 5 min
2. **Python V5** → Reads features, checks calendar, runs ensemble
3. **XGB + LGB** → Equal-weighted vote [0.50, 0.50]
4. **4 Dimensions** → ML + Confluence + Regime + Session validation
5. **Trade Commands** → Python writes, EA executes

### Recent Changes (Dec 02)
- Fixed lot size mismatch (was 0.10 in EA, now 0.01)
- Fixed confidence mismatch (was 0.60 in EA, now 0.35)
- Added MT5 calendar export (ForexFactory blocked)
- Disabled CatBoost (performance issues)

---

## 💡 USEFUL COMMANDS

### Test Calendar Integration
```powershell
cd C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System
python mt5_calendar_reader.py
```

### Start Trading System
```powershell
cd C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System
.\venv_lite\Scripts\python.exe live_trading_system_v5_treebased.py --mode demo
```

### Check MT5 Files
```powershell
dir "C:\Users\mt5-admin\AppData\Roaming\MetaQuotes\Terminal\EE0304F13905552AE0B5EAEFB04866EB\MQL5\Files\"
```

### Key Metrics
```
Active Models: 16 (8 XGBoost + 8 LightGBM)
Average Accuracy: 86% (XGB 85%, LGB 87%)
Features: 58 base, 108 expanded
Pairs: 8
Calendar Events: 48 (7 HIGH impact)
```

---

## 📝 VERSION HISTORY

| Version | Date | Key Changes |
|---------|------|-------------|
| v83 | 2025-12-02 | EA sync, calendar, CatBoost disabled |
| v82 | 2025-11-29 | Tree ensemble, M15 timeframe |
| v81 | 2025-11-25 | System audit, cleanup |

---

**END OF CONTINUATION PROMPT v83**
