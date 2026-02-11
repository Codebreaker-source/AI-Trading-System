# QUICK SETUP GUIDE - v86 (2026-01-23)

**For new Claude sessions or quick reference**
**Synced with MHP v81-solution7**

---

## 🚀 SYSTEM STATUS

| Component | Status |
|-----------|--------|
| Live System | ✅ V6 Solution 7 |
| Models | ✅ 16 (XGB + LGB) |
| Features | ✅ 27 CLEAN |
| EA | ✅ v2.32 |
| Timeframe | ✅ M15 |
| Pairs | ✅ All 8 |

---

## ⚠️ CRITICAL SYNC

| Setting | EA v2.32 | Python v6 |
|---------|----------|-----------|
| Lot Size | **0.01** | **0.01** |
| Confidence | **0.35** | **0.35** |
| BE Trigger | **1.0** | - |
| Prog Trail | **false** | - |
| Cooldown | - | **60 min** |

---

## ▶️ START SYSTEM

```powershell
cd C:\Users\mt5-admin\Documents\TradingSystem\AzureDeploy\Phase4_LITE_System
.\venv_lite\Scripts\python.exe live_trading_system_v6_solution7.py --mode demo
```

---

## 📁 KEY FILES

| Purpose | File |
|---------|------|
| Main System | `live_trading_system_v6_solution7.py` |
| ML Ensemble | `ensemble_predictor_v3_treebased.py` |
| Dimensions | `dimensions/dimension_checker.py` |
| Danger Score | `dimensions/danger_scorer.py` |
| Anti-Fragile | `dimensions/anti_fragile_builder.py` |
| Models | `trained_models_CLEAN27/*.joblib` |
| EA | `BridgeEA_LITE_v2_32_STREAK_SIZE.mq5` |

---

## 🎯 SIGNAL FLOW

```
Dimensions (4) → Danger Score (0-21) → Anti-Fragile Build → 60-min Cooldown
```

- **Dimensions:** REGIME, SESSION, ML, CONFLUENCE (need ≥3, no veto)
- **Danger:** Score ≥13 = blocked
- **Build:** Probe 0.01 → 0.05 at R-levels
- **Cooldown:** 60 min per symbol+direction

---

## 🤖 MODELS

| Model | Accuracy | Weight |
|-------|----------|--------|
| XGBoost | 70.5% | 0.50 |
| LightGBM | 70.3% | 0.50 |

---

## 📚 DOCUMENTATION

| For This | Read This |
|----------|-----------|
| Overview | MASTER_PROJECT_HANDOFF.md |
| Data Flow | DATA_PIPELINE_FLOW.md |
| File Locations | FILE_INVENTORY.md |
| Technical Specs | TECHNICAL_SPECIFICATIONS.md |
| Deep Dive | COMPREHENSIVE_SYSTEM_CONTINUATION.md |

---

## ⚠️ USER RULES

1. **ALWAYS** clarify before making code changes
2. **NEVER** add/remove code without permission
3. **ALWAYS** provide full files (not snippets)
4. **USE MHP FIRST** - call memory_get_handoff before answering

---

**END OF QUICK SETUP GUIDE v86**
