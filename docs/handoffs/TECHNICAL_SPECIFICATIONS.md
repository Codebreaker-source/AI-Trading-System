# TECHNICAL SPECIFICATIONS - v86 (2026-01-23)

**System:** AI Trading System V6 Solution 7
**Status:** ✅ LIVE | ✅ 16 MODELS | ✅ 27 FEATURES
**Synced with MHP v81-solution7**

---

## 🎯 SYSTEM ARCHITECTURE

### Signal Flow
```
EA v2.32 (27 features) → Dimensions (4) → Danger Score (0-21) 
→ Anti-Fragile Build → 60-min Cooldown → Trade Commands → EA Execution
```

### Active Files
| File | Lines | Purpose |
|------|-------|---------|
| live_trading_system_v6_solution7.py | 1,997 | Main system |
| ensemble_predictor_v3_treebased.py | 727 | ML ensemble |
| dimensions/dimension_checker.py | 325 | 4-dimension validation |
| dimensions/danger_scorer.py | 636 | Danger scoring |
| dimensions/anti_fragile_builder.py | 632 | Position building |

---

## 🔄 EA ↔ PYTHON SYNC

| Parameter | EA v2.32 | Python v6 |
|-----------|----------|-----------|
| FixedLotSize | 0.01 | 0.01 |
| MinConfidence | 0.35 | 0.35 |
| BE_TriggerRR | 1.0 | - |
| EnableProgressiveTrail | false | - |
| Cooldown | - | 60 min |
| Confluence | - | 0.35 |

---

## 🤖 MODEL CONFIGURATION

### XGBoost (8 models) ✅ ACTIVE
- Accuracy: 70.5% avg
- Weight: 0.50

### LightGBM (8 models) ✅ ACTIVE  
- Accuracy: 70.3% avg
- Weight: 0.50

### EXCLUDED
- CatBoost: Underperformed 7%
- CNN/Transformer: 100% HOLD (class imbalance)

### Per-Pair Accuracy
| Pair | XGBoost | LightGBM |
|------|---------|----------|
| EURUSD | 68.8% | 69.1% |
| GBPUSD | 65.3% | 64.7% |
| USDJPY | 63.6% | 61.9% |
| USDCHF | 70.9% | 70.9% |
| AUDUSD | 69.4% | 69.3% |
| USDCAD | 68.0% | 68.3% |
| NZDUSD | 71.9% | 72.3% |
| EURGBP | 86.0% | 86.3% |

---

## 📊 27 CLEAN FEATURES

| Category | Features | Count |
|----------|----------|-------|
| Price | close, high, low, volume | 4 |
| Trend | sma_20, sma_50, fast_ema, slow_ema, htf_fast_ema, htf_slow_ema, htf_trend_direction, htf_trend_alignment | 8 |
| Momentum | rsi, stoch_k, stoch_d, momentum | 4 |
| Volatility | atr, bb_upper, bb_middle, bb_lower, volatility | 5 |
| Volume | volume_sma, volume_ratio, price_volume | 3 |
| Sentiment | bullish_sentiment, bearish_sentiment, net_sentiment | 3 |
| **TOTAL** | | **27** |

### Removed Features (31)
- Correlations: pair_correlation_* (cross-pair unavailable)
- Currency Strength: *_strength (requires all pairs)
- Confirmation Flags: *_confirm (redundant)
- Risk Metrics: risk_*, position_* (execution-only)

---

## 🎯 8-FACTOR CONFLUENCE

| Factor | Weight |
|--------|--------|
| MTF Trend | 27% |
| Support/Resistance | 22% |
| H1/H4 Trend | 20% |
| Momentum | 13% |
| Candlestick Patterns (169) | 12% |
| Volume | 9% |
| Strategy Consensus | 9% |
| Volatility | 8% |

**Thresholds:** HIGH ≥0.70, MEDIUM ≥0.50, MIN 0.35

---

## ⚠️ DANGER SCORING (7 Categories)

| Category | Max Points |
|----------|------------|
| Regime Hostility | 3 |
| Session Opposition | 3 |
| ML Uncertainty | 3 |
| Technical Resistance | 3 |
| System Stress | 3 |
| Correlation Exposure | 3 |
| Event Risk | 3 |
| **TOTAL** | **21** |

Score ≥ 13 = TRADE BLOCKED

---

## 🔧 SYSTEM CONFIGURATION

| Setting | Value |
|---------|-------|
| Account | OANDA 1600054407 (Demo) |
| Suffix | .sim |
| Timeframe | M15 |
| Pairs | 8 (EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD, EURGBP) |
| Lot Size | 0.01 |
| Cooldown | 60 min per symbol+direction |

---

**END OF TECHNICAL_SPECIFICATIONS v86**
