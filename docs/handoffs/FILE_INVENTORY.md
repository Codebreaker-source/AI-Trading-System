# FILE INVENTORY - v86 (2026-01-23)

**Status:** ✅ V6 SOLUTION 7 LIVE | ✅ 16 MODELS | ✅ 27 CLEAN FEATURES
**Synced with MHP v81-solution7**

---

## 🎯 ACTIVE FILES

### Live System
| File | Lines | Purpose |
|------|-------|---------|
| `live_trading_system_v6_solution7.py` | 1,997 | MAIN system |
| `ensemble_predictor_v3_treebased.py` | 727 | Tree ensemble |
| `feature_expander.py` | 495 | Feature expansion |
| `news_integration.py` | ~300 | MT5 + Web news |
| `mt5_calendar_reader.py` | ~280 | Calendar reader |

### Dimensions Module
| File | Lines | Purpose |
|------|-------|---------|
| `dimensions/dimension_checker.py` | 325 | 4-dimension validation |
| `dimensions/danger_scorer.py` | 636 | 7-category danger |
| `dimensions/anti_fragile_builder.py` | 632 | Probe-first building |
| `dimensions/trade_history_tracker.py` | 433 | Trade history |

### Confluence Module
| File | Purpose |
|------|---------|
| `confluence/confluence_scorer.py` | 8-factor scoring |
| `confluence/candlestick_patterns.py` | 169 patterns |
| `confluence/htf_confirmation.py` | H1/H4 trend |
| `confluence/pullback_detector.py` | Scale-in pullback |
| `confluence/regime_detector.py` | Market regime |
| `confluence/risk_manager.py` | Position/risk |
| `confluence/level_confluence.py` | Key levels |
| `confluence/hard_filters.py` | Session/news |

---

## 🤖 MODELS

**CURRENT:** `trained_models_CLEAN27/` (16 models)
- 8 XGBoost (*.joblib) - 70.5% avg
- 8 LightGBM (*.joblib) - 70.3% avg

**DEPRECATED:**
- `trained_models_105FEAT/` - OLD 58 features
- `trained_models_B1_CLEAN/` - OLD V4 models

---

## 📁 KEY PATHS

| Purpose | Path |
|---------|------|
| System | `Phase4_LITE_System/` |
| Models | `Phase4_LITE_System/trained_models_CLEAN27/` |
| Docs | `Phase4_LITE_System/0.1-Handoff Checklists/` |
| EA | `MQL5/Experts/BridgeEA_LITE_v2_32_STREAK_SIZE.mq5` |
| MT5 Files | `MQL5/Files/` |
| Logs | `Phase4_LITE_System/logs/` |
| Training | `Phase4_LITE_System/training/` |
| Historical | `Phase4_LITE_System/historical_data/` |

---

## 📚 DOCUMENTATION STATUS

| File | Status |
|------|--------|
| MASTER_PROJECT_HANDOFF.md | ✅ v86 |
| DATA_PIPELINE_FLOW.md | ✅ v86 |
| FILE_INVENTORY.md | ✅ v86 (this) |
| TECHNICAL_SPECIFICATIONS.md | ✅ v86 |
| QUICK_SETUP_GUIDE.md | ✅ v86 |
| COMPREHENSIVE_SYSTEM_CONTINUATION.md | ✅ Keep |
| IMPLEMENTATION_ROADMAP.md | ✅ Keep |

**ARCHIVED/REMOVED:**
- Continuation prompt.md → Archived (MHP replaces)
- DOCUMENTATION_COMPLETE.md → Archived
- CLAUDE_PROJECT_SETUP.md → Merged to MHP
- CUSTOM_INSTRUCTIONS.txt → Merged to MHP
- SESSION_SUMMARY.md → Archived

---

**END OF FILE INVENTORY v86**
