# FTMO AI Trading System — Handoff Document
Date: 2026-06-01

## System Overview

Phase 4 LITE trading system deployed for FTMO prop firm account on MetaTrader 5.

```
Bridge EA (MT5)
  ↓  writes 27-feature CSV per symbol every 3s
Python (live_trading_system.py)
  ↓  expands 27 → 105 features
  ↓  XGBoost prediction (where model exists) or ABSTAIN
  ↓  confluence scoring + dimension check + danger scoring
  ↓  writes signal_{SYMBOL}.txt
Bridge EA reads signal, executes trade
  ↓  logs to data/execution_log/trades.csv
daily_retrainer.py (background, runs 00:00 UTC Sunday)
  ↓  reads trades.csv, labels outcomes, trains new XGBoost per symbol
```

## Directory Layout

```
FTMO_System/
├── config/
│   └── ftmo_config.json          # FTMO risk limits, ML thresholds, session windows
├── data/
│   ├── features/                 # {SYMBOL}_features.csv (EA writes every 3s)
│   │                             # signal_{SYMBOL}.txt   (Python writes, EA reads+deletes)
│   │                             # open_positions.csv    (EA writes, Python reads)
│   ├── execution_log/
│   │   └── trades.csv            # All trade outcomes (source for daily retrain)
│   ├── training_data/            # Reserved for future use
│   └── models/                   # *.joblib XGBoost models (8 pretrained + any auto-trained)
├── ea/
│   └── BridgeEA_FTMO_v1.mq5     # Load on any M15 chart in MT5
├── core/
│   ├── live_trading_system.py    # Main orchestrator (run via run_system.py)
│   ├── ensemble_predictor.py     # XGBoost-only predictor
│   ├── feature_expander.py       # 27 → 105 feature expansion
│   ├── rule_based_strategies.py  # 9 rule-based strategies (fallback for no-model symbols)
│   └── symbol_manager.py         # Dynamic MT5 symbol discovery
├── confluence/                   # 7-factor confluence scoring
├── dimensions/                   # 4-dimension validation (REGIME/SESSION/ML/CONFLUENCE)
├── training/
│   └── daily_retrainer.py        # Daily XGBoost retraining
├── logs/                         # System logs + prediction CSVs
├── docs/
│   └── FTMO_SYSTEM_HANDOFF.md   # This file
└── run_system.py                 # Entry point
```

## How to Start

### 1. Set FTMO credentials in config/ftmo_config.json
```json
"account": {
  "login": <your_ftmo_login>,
  "password": "<your_password>",
  "server": "<ftmo_server>"
}
```

### 2. Load Bridge EA in MT5
- Open MetaEditor → open `ea/BridgeEA_FTMO_v1.mq5` → compile
- Copy compiled `.ex5` to MT5 Experts folder
- In MT5: open any M15 chart → drag EA onto chart
- Set `SystemDataPath = C:\Users\mt5-admin\Documents\TradingSystem\FTMO_System\data`
- Enable "Allow DLL imports" and "Allow automated trading"

### 3. Start Python system
```bash
cd C:\Users\mt5-admin\Documents\TradingSystem\FTMO_System
python run_system.py --mode demo --balance 100000
```

For live trading:
```bash
python run_system.py --mode live
```

To run retrainer only:
```bash
python run_system.py --retrain-only
```

## Key Design Decisions

### Symbol discovery
- EA scans Market Watch at startup for all tradeable symbols
- Python's `symbol_manager.py` does the same via `mt5.symbols_get()`
- FTMO suffixes (`.i`, `_SB`, etc.) are stripped when matching model filenames
- Symbol names used AS-IS from MT5 for all trading operations

### ML gate logic
- 8 symbols have pretrained XGBoost models: EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD, EURGBP
- Symbols WITH models: ML dimension returns AGREES or DISAGREES
- Symbols WITHOUT models: ML dimension returns ABSTAIN → still need 3/3 remaining dimensions (REGIME + SESSION + CONFLUENCE)
- This is intentional — symbols without models CAN trade from day 1

### Label encoding (DO NOT CHANGE)
- The pretrained XGBoost models use: **0 = SELL, 1 = HOLD, 2 = BUY**
- `ensemble_predictor.py` line: `LABELS = ['SELL', 'HOLD', 'BUY']`
- Changing this mapping will invert all predictions

### HOLD-bias fix
- Models tend to over-predict HOLD (~57% of training labels)
- When model votes HOLD, predictor promotes strongest directional signal instead
- Confidence = max(directional_weight, hold_conf × 0.5, 0.35)
- Implemented in `ensemble_predictor.py` `predict_pair()`

### FTMO risk limits (in EA + Python)
| Limit | Value | Where enforced |
|-------|-------|----------------|
| System daily loss | 3% | EA + Python |
| FTMO daily loss | 5% | EA + Python |
| FTMO total drawdown | 10% | EA + Python |
| Portfolio risk | 2% | EA |
| Correlation exposure | 2 per group | EA |

### Feature communication
- EA writes: `data/features/{SYMBOL}_features.csv` (27 features, overwritten every 3s)
- Python writes: `data/features/signal_{SYMBOL}.txt` (action, confidence, SL, TP, lot)
- EA reads signal file then **deletes it** (prevents stale signal re-execution)
- EA writes: `data/features/open_positions.csv` (Python reads for position sync)
- EA writes: `data/execution_log/trades.csv` (Python reads for daily retrain)

## Daily Retraining

Runs in background thread, scheduled at 00:00 UTC on Sundays (configurable in `ftmo_config.json`).

Requirements:
- Minimum 50 trade outcomes per symbol
- New model must have val_acc ≥ existing model to replace it
- Labels: BUY+TP→BUY, BUY+SL→SELL, SELL+TP→SELL, SELL+SL→BUY, no-trade→HOLD
- Saves to `data/models/{SYMBOL}_xgboost_CLEAN27.joblib`

## Verification Checklist

- [ ] MT5 connects to FTMO account (`run_system.py` logs account balance)
- [ ] Bridge EA loads on M15 chart (green smiley in top-right corner)
- [ ] Feature CSVs appear in `data/features/` within 10 seconds of EA loading
- [ ] Python reads CSVs: run `python -c "import pandas as pd; print(pd.read_csv('data/features/EURUSD_features.csv'))"`
- [ ] 8 pretrained models load without error (check logs/ on startup)
- [ ] Symbols without models show ABSTAIN in dimension logs (not DISAGREES)
- [ ] Confluence scoring runs for all symbols
- [ ] FTMO risk limits log warnings when approaching thresholds
- [ ] Signal files appear in data/features/ and disappear after EA reads them
- [ ] trades.csv grows as positions open/close
- [ ] Daily retrainer runs without error (test with `--retrain-only` flag)

## Known Issues / Watch Points

1. **Feature expander compatibility**: `feature_expander.py` was copied unchanged. Verify it accepts 27-element arrays (not 58). Check `expand()` method signature.

2. **news_integration import**: `live_trading_system.py` has graceful fallback if `news_integration` is missing. Install or skip as needed.

3. **MT5 file path**: The EA uses the `SystemDataPath` input parameter. If MT5 cannot write to this path, use the MT5 Common Files path instead and update `ReadSignal()` / `WriteFeatureCSV()` to add `FILE_COMMON` flag.

4. **Symbol suffix mismatches**: If FTMO uses non-standard suffixes not in the strip list, add them to `suffix_strip_patterns` in `ftmo_config.json` and `SUFFIX_STRIP` in `ensemble_predictor.py`.

5. **Rule-based strategies**: `rule_based_strategies.py` was copied as-is. The 9 strategies may need currency strength data (`eur_strength`, etc.) that is not in the 27 CLEAN features. If `make_strategy_predictions()` errors, these can be disabled by returning a neutral result.

## File Versions

| File | Source | Status |
|------|--------|--------|
| `core/ensemble_predictor.py` | v3.2 (adapted) | XGBoost only, dynamic symbols |
| `core/live_trading_system.py` | v5.0 (adapted) | Dynamic symbols, FTMO safety |
| `core/feature_expander.py` | original | Unchanged |
| `core/rule_based_strategies.py` | v1.0 | Unchanged |
| `core/symbol_manager.py` | NEW | Dynamic MT5 discovery |
| `ea/BridgeEA_FTMO_v1.mq5` | v2.32 (adapted) | 27 features, dynamic symbols |
| `training/daily_retrainer.py` | NEW | Execution-data retraining |
| `config/ftmo_config.json` | NEW | FTMO-specific config |
| `confluence/*` | original | Unchanged |
| `dimensions/dimension_checker.py` | original (adapted) | ML=None → ABSTAIN |
| `dimensions/*` | original | Unchanged |
| `news_analysis/*` | original | Unchanged |
| `data/models/*.joblib` | pretrained | 8 XGBoost models |
