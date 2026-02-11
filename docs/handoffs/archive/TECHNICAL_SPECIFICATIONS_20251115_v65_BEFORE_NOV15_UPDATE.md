# TECHNICAL SPECIFICATIONS - v68 (2025-11-12 21:00 UTC)

**System:** AI Trading System - LITE (Enhanced with Month 1 Features)  
**Version:** v68  
**Status:** 🚀 ENHANCED - 77 Features (58 + 19 New), Backup System Active  
**Major Update:** Phase 1 (Critical Fixes) + Phase 3 (Month 1 Features) COMPLETE

---

## 🎉 MAJOR ENHANCEMENT (Nov 12, 2025)

### **Feature Count Evolution:**
- **Previous:** 58 features
- **Month 1 Added:** 19 features
- **Current:** 77 features (+33% increase)
- **Expected Accuracy Improvement:** +10-15%

### **New Feature Categories:**
1. **Psychological Levels:** 5 features
2. **Pivot Points:** 7 features  
3. **Session Overlap:** 4 features
4. **Volume Surge:** 3 features

---

## 📊 MONTH 1 FEATURE SPECIFICATIONS

### **1. PSYCHOLOGICAL LEVEL FEATURES (5 features)**

**Module:** `features/psychological_levels.py` (297 lines)

#### **Feature 1.1: dist_to_major_psych**
- **Type:** Continuous (float)
- **Unit:** Pips
- **Range:** -500 to +500 (typical)
- **Description:** Distance to nearest major psychological level
- **Major Levels:**
  - Non-JPY: 1.10000, 1.20000, 1.30000 (intervals of 0.01000)
  - JPY: 150.00, 151.00, 152.00 (intervals of 1.00)
- **Sign Convention:**
  - Positive: Level is above current price
  - Negative: Level is below current price
- **Example:**
  - Price: 1.09725
  - Nearest major: 1.10000
  - Distance: +27.5 pips

#### **Feature 1.2: dist_to_minor_psych**
- **Type:** Continuous (float)
- **Unit:** Pips
- **Range:** -250 to +250 (typical)
- **Description:** Distance to nearest minor psychological level
- **Minor Levels:**
  - Non-JPY: 1.10500, 1.10050 (intervals of 0.00500)
  - JPY: 150.50 (intervals of 0.50)
- **Sign Convention:** Same as major levels
- **Example:**
  - Price: 1.09725
  - Nearest minor: 1.10000
  - Distance: +27.5 pips

#### **Feature 1.3: psychological_confluence**
- **Type:** Integer
- **Range:** 0-6 (typical)
- **Description:** Number of psychological levels within 20 pips
- **Confluence Range:** ±20 pips from current price
- **Interpretation:**
  - 0-1: Low confluence (clear price zone)
  - 2-3: Moderate confluence
  - 4+: High confluence (strong support/resistance zone)
- **Example:**
  - Price: 1.09950
  - Nearby levels: 1.10000 (major), 1.09900 (minor)
  - Confluence: 2

#### **Feature 1.4: at_psychological_level**
- **Type:** Binary (0 or 1)
- **Threshold:** 10 pips
- **Description:** Price within 10 pips of major level
- **Values:**
  - 1: At psychological level (potential bounce/break)
  - 0: Not at psychological level
- **Trading Signal:** High when price tests major round numbers

#### **Feature 1.5: psych_level_strength**
- **Type:** Continuous (float)
- **Range:** 0-100
- **Description:** Strength score of nearest major level
- **Components:**
  - Roundness: 0-60 points (more zeros = stronger)
  - Distance penalty: 0-30 points (closer = stronger)
  - Historical touches: 0-20 points (more touches = stronger)
- **Interpretation:**
  - 0-30: Weak level
  - 31-60: Moderate level
  - 61-100: Strong level (high probability of reaction)

---

### **2. PIVOT POINT FEATURES (7 features)**

**Module:** `features/pivot_points.py` (407 lines)

#### **Pivot Point Systems Used:**
1. **Traditional (Standard):**
   - PP = (High + Low + Close) / 3
   - R1 = (2 × PP) - Low
   - S1 = (2 × PP) - High
   - R2, R3, S2, S3 calculated

2. **Fibonacci:**
   - Uses Fibonacci ratios (0.382, 0.618, 1.000)
   - R1 = PP + 0.382 × (High - Low)
   - S1 = PP - 0.382 × (High - Low)

3. **Camarilla:**
   - More price-sensitive
   - R1 = Close + ((High - Low) × 1.0833)
   - S1 = Close - ((High - Low) × 1.0833)
   - Up to R4/S4 levels

#### **Feature 2.1: dist_to_pivot**
- **Type:** Continuous (float)
- **Unit:** Pips
- **Range:** -200 to +200 (typical)
- **Description:** Distance to main pivot point (PP)
- **Sign Convention:**
  - Positive: PP above price (price below pivot = bearish)
  - Negative: PP below price (price above pivot = bullish)
- **Pivot Calculation:** Previous day's High, Low, Close

#### **Feature 2.2: dist_to_nearest_support**
- **Type:** Continuous (float)
- **Unit:** Pips
- **Range:** 0-200 (always positive - distance below)
- **Description:** Distance to nearest support level (S1, S2, or S3)
- **Interpretation:**
  - 0-20 pips: Very close to support (potential bounce)
  - 50+ pips: Far from support (no immediate floor)

#### **Feature 2.3: dist_to_nearest_resistance**
- **Type:** Continuous (float)
- **Unit:** Pips
- **Range:** 0-200 (always positive - distance above)
- **Description:** Distance to nearest resistance level (R1, R2, or R3)
- **Interpretation:**
  - 0-20 pips: Very close to resistance (potential rejection)
  - 50+ pips: Far from resistance (no immediate ceiling)

#### **Feature 2.4: pivot_position**
- **Type:** Continuous (float)
- **Range:** 0.0-1.0
- **Description:** Normalized position within day's range
- **Calculation:** (Price - Low) / (High - Low)
- **Interpretation:**
  - 0.0-0.3: Lower third (near support)
  - 0.4-0.6: Middle range
  - 0.7-1.0: Upper third (near resistance)

#### **Feature 2.5: pivot_strength**
- **Type:** Continuous (float)
- **Range:** 0-100
- **Description:** Strength of nearest pivot level
- **Components:**
  - Level type: PP (80), R1/S1 (70), R2/S2 (60), R3/S3 (50)
  - Distance penalty: Closer = stronger
- **Interpretation:**
  - 0-40: Weak level
  - 41-70: Moderate level
  - 71-100: Strong level

#### **Feature 2.6: at_pivot_level**
- **Type:** Binary (0 or 1)
- **Threshold:** 10 pips
- **Description:** Price within 10 pips of any pivot level
- **Values:**
  - 1: At pivot level (potential pivot)
  - 0: Not at pivot level
- **Trading Signal:** High when price tests S/R

#### **Feature 2.7: pivot_confluence**
- **Type:** Integer
- **Range:** 0-10 (typical)
- **Description:** Count of pivot systems agreeing within 15 pips
- **Confluence Range:** ±15 pips from current price
- **Interpretation:**
  - 0-2: Low confluence
  - 3-5: Moderate confluence
  - 6+: High confluence (multiple systems agree = strong S/R)

---

### **3. SESSION OVERLAP FEATURES (4 features)**

**Module:** `features/session_overlap.py` (341 lines)

#### **Trading Sessions (EST):**
- **Tokyo:** 19:00-04:00 (7PM-4AM)
- **London:** 03:00-12:00 (3AM-12PM)
- **New York:** 08:00-17:00 (8AM-5PM)

#### **Key Overlaps:**
- **Tokyo-London:** 03:00-04:00 EST (1 hour)
- **London-NY:** 08:00-12:00 EST (4 hours) ⭐ **GOLDEN PERIOD (70% of volume!)**
- **Dead Zone:** 17:00-19:00 EST (very low liquidity)

#### **Feature 3.1: active_session_count**
- **Type:** Integer
- **Range:** 0-2
- **Description:** Number of trading sessions currently active
- **Values:**
  - 0: Dead zone (no major sessions)
  - 1: Single session (Tokyo, London, or NY alone)
  - 2: Overlap (two sessions active simultaneously)
- **Trading Impact:**
  - 0: Avoid trading (wide spreads, low volume)
  - 1: Normal trading
  - 2: Increased activity (higher volume & volatility)

#### **Feature 3.2: overlap_intensity**
- **Type:** Integer
- **Range:** 0-3
- **Description:** Quality of session overlap
- **Values:**
  - 0: No sessions (dead zone)
  - 1: One session active
  - 2: Two sessions overlap (Tokyo-London or other)
  - 3: London-NY overlap ⭐ **HIGHEST VALUE (70% of daily volume)**
- **Trading Impact:**
  - 0: Avoid
  - 1: Standard conditions
  - 2: Good liquidity
  - 3: Optimal trading window (highest success rates)

#### **Feature 3.3: session_volatility_mult**
- **Type:** Continuous (float)
- **Range:** 0.5-1.5
- **Description:** Expected volatility multiplier for current session(s)
- **Session Multipliers:**
  - Tokyo: 0.7x (lower volatility)
  - London: 1.2x (higher volatility)
  - New York: 1.3x (highest volatility)
  - Multiple sessions: Average with 10% overlap bonus
- **Example:**
  - London-NY overlap: (1.2 + 1.3) / 2 × 1.1 = 1.375x
- **Trading Impact:** Adjust stop-loss and take-profit based on expected volatility

#### **Feature 3.4: is_high_liquidity_period**
- **Type:** Binary (0 or 1)
- **Description:** Currently in London-NY overlap (08:00-12:00 EST)
- **Values:**
  - 1: High liquidity period (70% of daily forex volume)
  - 0: Not high liquidity period
- **Trading Impact:**
  - 1: Tightest spreads, best execution, highest win rates
  - 0: Standard liquidity
- **Strategy:** Prioritize trading during this window

---

### **4. VOLUME SURGE FEATURES (3 features)**

**Module:** `features/volume_surge.py` (283 lines)

#### **Feature 4.1: volume_ratio**
- **Type:** Continuous (float)
- **Range:** 0.1-5.0+ (typical)
- **Description:** Current volume / 20-period average volume
- **Calculation:** Volume(t) / SMA(Volume, 20)
- **Interpretation:**
  - 0.5-0.8: Below average (weak conviction)
  - 0.9-1.1: Normal volume
  - 1.2-1.8: Above average (strong move)
  - 2.0+: Surge (exceptional conviction) ⭐
- **Trading Impact:** Confirm breakouts/breakdowns

#### **Feature 4.2: volume_spike**
- **Type:** Binary (0 or 1)
- **Threshold:** 2.0x average
- **Description:** Volume exceeds 2× the 20-period average
- **Values:**
  - 1: Volume spike detected (strong conviction)
  - 0: Normal volume
- **Trading Impact:**
  - Confirms trend continuation
  - Validates breakout/breakdown
  - Increases confidence in directional trades

#### **Feature 4.3: volume_price_divergence**
- **Type:** Continuous (float)
- **Range:** -100 to +100 (typical)
- **Description:** Volume-price trend correlation over 10 bars
- **Calculation:**
  - Positive: Volume and price moving in same direction (confirmation)
  - Negative: Volume and price diverging (warning)
  - Zero: Neutral correlation
- **Interpretation:**
  - +50 to +100: Strong confirmation (volume confirms price)
  - -50 to -100: Strong divergence (potential reversal)
  - -10 to +10: Neutral
- **Trading Impact:**
  - Positive divergence: Continue trend
  - Negative divergence: Consider counter-trend or exit

---

## 🧮 COMPLETE FEATURE SPECIFICATIONS (77 TOTAL)

### **Feature Categories Overview:**

**Original 58 Features:**
1. Technical Indicators (26)
2. Currency Strength (8)
3. Market State (8)
4. Volatility Metrics (6)
5. Price Action (10)

**Month 1 Features (+19):**
6. Psychological Levels (5)
7. Pivot Points (7)
8. Session Overlap (4)
9. Volume Surge (3)

**Total: 77 features**

### **Feature List (All 77):**

#### **[1-26] Technical Indicators**
(Existing 58 features - see previous versions)

#### **[27-34] Currency Strength**
(Existing 58 features - see previous versions)

#### **[35-42] Market State**
(Existing 58 features - see previous versions)

#### **[43-48] Volatility Metrics**
(Existing 58 features - see previous versions)

#### **[49-58] Price Action**
(Existing 58 features - see previous versions)

#### **[59-63] Psychological Levels ⭐ NEW**
59. dist_to_major_psych (pips)
60. dist_to_minor_psych (pips)
61. psychological_confluence (count)
62. at_psychological_level (binary)
63. psych_level_strength (0-100)

#### **[64-70] Pivot Points ⭐ NEW**
64. dist_to_pivot (pips)
65. dist_to_nearest_support (pips)
66. dist_to_nearest_resistance (pips)
67. pivot_position (0-1)
68. pivot_strength (0-100)
69. at_pivot_level (binary)
70. pivot_confluence (count)

#### **[71-74] Session Overlap ⭐ NEW**
71. active_session_count (0-2)
72. overlap_intensity (0-3)
73. session_volatility_mult (0.5-1.5)
74. is_high_liquidity_period (binary)

#### **[75-77] Volume Surge ⭐ NEW**
75. volume_ratio (float)
76. volume_spike (binary)
77. volume_price_divergence (float)

---

## 🔄 FEATURE EXTRACTION PIPELINE (Enhanced)

### **Updated Data Flow:**

```
MT5 Bridge EA
    ↓ (2-3 seconds)
Extract Base OHLCV + Indicators
    ↓
58 Base Features Calculated
    ↓
┌─────────────────────────────────────────────┐
│ MONTH 1 FEATURE ENHANCEMENT                  │
│                                              │
│ ┌─────────────────────────────────────────┐ │
│ │ Psychological Level Detector            │ │
│ │ → 5 features                            │ │
│ └─────────────────────────────────────────┘ │
│                ↓                             │
│ ┌─────────────────────────────────────────┐ │
│ │ Pivot Point Calculator                  │ │
│ │ → 7 features                            │ │
│ └─────────────────────────────────────────┘ │
│                ↓                             │
│ ┌─────────────────────────────────────────┐ │
│ │ Session Overlap Detector                │ │
│ │ → 4 features                            │ │
│ └─────────────────────────────────────────┘ │
│                ↓                             │
│ ┌─────────────────────────────────────────┐ │
│ │ Volume Surge Detector                   │ │
│ │ → 3 features                            │ │
│ └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
    ↓
77 Total Features
    ↓
Feature Buffer (20 candles rolling)
    ↓
3 Models per Pair (21 total)
    ↓
Weighted Ensemble Voting
    ↓
Trading Signal
```

### **Processing Time:**
- **Base 58 features:** ~50ms per calculation
- **Month 1 features:** +30ms per calculation
- **Total:** ~80ms per calculation (real-time compatible)

---

## 🚨 CRITICAL DISCOVERY: CONFIDENCE MISCALIBRATION (Nov 8, 2025)

### **The Confidence Paradox:**

**Analysis Period:** Nov 5-7, 2025 (538 closed orders)

```
CONFIDENCE RANGE    | ORDERS | WINS | WIN RATE | EXPECTED
High (85-100%)      |   408  | 201  |  49.3%   |   ≥85% ❌
Medium (70-85%)     |    37  |  32  |  86.5%   |  70-85% ✅
Low (60-70%)        |    93  |  11  |  11.8%   |  60-70% ❌
```

**What This Means:**
- **Models are MOST accurate when moderately confident (70-85%)**
- **Models are LEAST accurate when very confident (>85%)**
- **Current 80% threshold captures mostly POOR predictions (49% win rate)**
- **Sweet spot is 70-85% range (86.5% win rate)**

### **Three-Phase Recalibration Strategy:**

**Phase 1: Immediate Threshold Adjustment (5 minutes) - PENDING**
- Change: `confidence >= 0.80` → `0.70 <= confidence <= 0.85`
- Expected Impact: 49% → 86% win rate
- Status: ⏳ Waiting for model retraining with 77 features

**Phase 2: Calibration Layers (This Weekend) - PENDING**
- Temperature Scaling, Platt Scaling, Isotonic Regression
- Train on execution outcomes
- Target: ECE < 0.05

**Phase 3: Full Retraining with 77 Features (Next Weekend) - PENDING**
- Retrain all 24 models with enhanced datasets
- Custom loss function + RL from outcomes
- Expected improvement: +10-15% accuracy from new features

**Documentation:** `CONFIDENCE_RECALIBRATION_STRATEGY.md`

---

## 💾 DATA SPECIFICATIONS

### **Current Training Data (58 features):**
```
train_data_24c_10p_offset.csv       (1,451,828 samples, 70%)
val_data_24c_10p_offset.csv         (311,106 samples, 15%)
test_data_24c_10p_offset.csv        (311,106 samples, 15%)
```

### **Enhanced Training Data (77 features) - TO BE CREATED:**
```
train_data_24c_10p_ENHANCED.csv     (1,451,828 samples, 70%, 77 features)
val_data_24c_10p_ENHANCED.csv       (311,106 samples, 15%, 77 features)
test_data_24c_10p_ENHANCED.csv      (311,106 samples, 15%, 77 features)
```

**Creation Command:**
```powershell
python integrate_month1_features.py --integrate-all
```

### **Label Distribution:**
- SELL (0): ~9.24%
- HOLD (1): ~81.79%
- BUY (2): ~8.97%

### **Labeling Parameters:**
- **Lookforward:** 24 candles (2 hours on M5)
- **Threshold:** 10 pips
- **Timeframe:** M5 (5-minute candles)

---

## 🎯 MODEL SPECIFICATIONS

### **Ensemble Architecture:**
- **Models per pair:** 3 (XGBoost + Transformer + CNN)
- **Total models:** 21 (7 pairs × 3 types)
- **Input features:** 77 (after Month 1 enhancement)
- **Output classes:** 3 (SELL, HOLD, BUY)

### **Model Types:**

**1. XGBoost:**
- Input: 77 features (flat vector)
- Architecture: Gradient boosting trees
- Class weights: 6-10x for BUY/SELL
- Current accuracy: 90-92% (will improve with 77 features)

**2. Transformer:**
- Input: 20 candles × 77 features (sequence)
- Architecture: Multi-head attention
- Temporal encoding: Learned positional embeddings
- Current accuracy: 90-92% (will improve with 77 features)

**3. CNN:**
- Input: 20 candles × 77 features (2D)
- Architecture: Conv1D + pooling
- Known issue: 3-18% accuracy (needs debugging)
- Status: ⏳ Pending investigation

### **Voting Mechanism:**
- **Method:** Weighted confidence voting
- **Threshold:** 80% (needs adjustment to 70-85%)
- **Min models required:** 2/3 agreement
- **Confidence calculation:** Sum of votes / Total votes

---

## 📊 PERFORMANCE TARGETS (Updated with 77 Features)

### **Accuracy Targets:**
- **Previous (58 features):** 90-92%
- **Expected (77 features):** 92-95% (+2-3% improvement)
- **Current:** 90-92% (pending retraining)

### **Win Rate Targets:**
- **Overall:** ≥60% (realistic for forex)
- **High confidence (70-85%):** ≥80%
- **Current:** 49% at >85% (miscalibrated), 86.5% at 70-85% ✅

### **Profit Targets:**
- **Monthly:** +5-10% account growth
- **Risk/Reward:** 2:1 minimum
- **Max drawdown:** <15%

---

## ✅ VERSION HISTORY

### **v68 (2025-11-12 21:00)** - CURRENT ⭐ **MAJOR UPDATE**
- 🎉 **19 NEW FEATURES ADDED** (58 → 77)
- 📝 Complete specifications for all Month 1 features
- 🔄 Updated data flow pipeline
- 📊 Feature extraction timing updated
- ⏳ Enhanced datasets pending creation

### **v65 (2025-11-08 23:45)**
- 🚨 Confidence calibration crisis documented
- 📊 Symbol-specific performance added
- 🔧 Recalibration strategy detailed

### **v64 and earlier**
- See Archive/ for complete history

---

**VERSION: v68 (MONTH 1 FEATURES + ENHANCED SPECIFICATIONS)**  
**STATUS:** 🚀 ENHANCED - 77 Features Specified  
**READY FOR:** Integration → Retraining → Deployment  

**NEXT ACTIONS:**
1. Run feature integration on training data
2. Create ENHANCED datasets with 77 features
3. Retrain all 24 models
4. Deploy updated models
5. Monitor performance improvement (+10-15% expected)

---
