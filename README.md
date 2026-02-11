# AI Trading System

> Self-improving multi-platform forex trading system using ensemble machine learning models

## 🎯 Overview

This repository contains the codebase for an AI-powered forex trading system that:
- Monitors 8+ currency pairs in real-time
- Uses ensemble ML models (XGBoost + LightGBM) for trade signals
- Executes trades automatically via MetaTrader 5
- Employs multi-dimensional signal validation
- Features anti-fragile position building

## 📊 Current System Status

| Component | Value |
|-----------|-------|
| **System Version** | v86 (Solution 7) |
| **Models** | 16 (XGBoost + LightGBM per pair) |
| **Features** | 27 CLEAN features |
| **Pairs** | EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD, EURGBP |
| **Average Accuracy** | 70.4% (validation set) |
| **Account** | OANDA Demo (1600054407) |

## 🏗️ Repository Structure

```
AI-Trading-System/
├── .ai/                    # AI agent metadata (schemas, indexes)
├── docs/                   # Documentation and handoffs
├── src/
│   ├── lite/              # LITE system (active)
│   └── full/              # FULL system (paused)
├── expert_advisors/       # MQL5 Expert Advisors
├── models/                # Trained ML models (.joblib)
├── mhp/                   # Memory Handoff Protocol
├── DATA_MANIFEST.json     # Links to data in Azure
└── CHANGELOG.md           # Version history
```

## 📁 Data Storage

Large data files (CSVs, logs) are stored in **Azure Blob Storage** to keep this repo lightweight.

See `DATA_MANIFEST.json` for URLs to:
- Training data (train/val/test CSVs)
- Execution logs
- Prediction history
- System backups

## 🚀 Quick Start

1. Clone this repository
2. Set up Python environment: `pip install -r requirements.txt`
3. Configure MT5 connection in `config/`
4. Download data from Azure URLs in `DATA_MANIFEST.json`
5. Run: `python src/lite/live_trading_system_v6_solution7.py`

## 📈 Model Architecture

### Signal Flow (6 Phases)
1. **Capital Segmentation** - 10% of account as trading capital
2. **Dimension Wrappers** - Regime, Session, ML, Confluence
3. **Dimension Counter** - 3+ dimensions must agree
4. **Main System Integration** - DimensionChecker validation
5. **Danger Scoring** - 7-category risk assessment (0-21 points)
6. **Anti-Fragile Building** - Probe → Build → Target position

### 8-Factor Confluence Scoring
- MTF Trend (27%)
- Support/Resistance (22%)
- H1/H4 Confirmation (20%)
- Momentum (13%)
- Candlestick Patterns (12%)
- Volume (9%)
- Strategy Consensus (9%)
- Volatility (8%)

## 🔧 Two Workstreams

### LITE System (Active)
- Ensemble tree models (XGBoost + LightGBM)
- 27 clean features
- Runs locally or Azure
- **Current focus**

### FULL System (Paused)
- 12 neural trading bots
- Transformer coordination
- Azure Docker containers
- **Future development**

## 📚 Documentation

- `docs/SYSTEM_CONTEXT.md` - Complete system overview
- `docs/CHANGELOG.md` - All changes chronologically
- `docs/VERSION_TIMELINE.md` - Version → Results mapping
- `docs/handoffs/` - Session handoff documents

## ⚠️ Disclaimer

This system is for educational and research purposes. Trading involves substantial risk. Past performance does not guarantee future results.

## 📄 License

Proprietary - All Rights Reserved
