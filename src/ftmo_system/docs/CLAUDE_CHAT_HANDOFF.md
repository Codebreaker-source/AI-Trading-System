# Claude Chat ↔ Claude Code Handoff Notes

Purpose: ground Claude Chat (planning) in the **actual current state of the
codebase**, which Claude Code (this CLI, direct filesystem access) verified
directly. Last updated: 2026-06-22 (Claude Code, direct VPS edits + GitHub push —
XGBoost moved to Colab, two tick-pricing bugs fixed, flat 0.01 mode, retrainer
disabled, training rule corrected to Option A; see the 2026-06-22 entry at the
top of §8). Prior verification 2026-06-14 (Chat) covered pretraining +
Dukascopy data-integrity + per-model-independence + sim-vs-actual analysis.

---

## 0. COMPLETE FILE BUNDLES — upload these to Claude Chat

Every `.py`/`.mq5`/`.json` file in `FTMO_System` (excluding `__pycache__`,
`colab/edge_profile/` browser cache, and `catboost_info/` training artifacts)
has been bundled into markdown files at
`FTMO_System/docs/full_source_bundles/`. **Upload all of these as file
attachments to Claude Chat** so nothing is left out:

| Bundle | Contents |
|---|---|
| `01_live_trading_system.md` | `core/live_trading_system.py` (full, 2386 lines — main orchestrator, 6-phase decision, Colab polling, main loop) |
| `02_confluence.md` | `confluence/__init__.py`, `confluence_scorer.py`, `hard_filters.py`, `htf_confirmation.py`, `level_confluence.py`, `pullback_detector.py`, `regime_detector.py`, `risk_manager.py` |
| `03_candlestick_patterns.md` | `confluence/candlestick_patterns.py` (2912 lines — 169 pattern definitions) |
| `04_dimensions.md` | `dimensions/__init__.py`, `dimension_checker.py`, `danger_scorer.py`, `trade_history_tracker.py`, `anti_fragile_builder.py` |
| `05_core_misc.md` | `core/feature_expander.py`, `feature_history_recorder.py`, `exit_logic.py`, `symbol_manager.py`, `unified_trade_logger.py`, `trade_outcome_simulator.py`, `rule_based_strategies.py` |
| `06_strategies.md` | `core/strategies/*` — the 6 EA-translated strategies + base class |
| `07_news_analysis.md` | All of `news_analysis/` incl. `data_sources/` (forexfactory, FRED, central bank feeds) |
| `08_training.md` | All of `training/` — daily retrainer, data labeler, Dukascopy pipeline, training set builder |
| `09_scripts.md` | All of `scripts/` — health watchdog, scheduled-task setup scripts |
| `10_ea_bridge.md` | `ea/BridgeEA_FTMO_v1.mq5` (full, 1025 lines) |
| `11_config_and_entry.md` | `run_system.py`, `config/ftmo_config.json`, `.gitignore` |
| `12_colab_scripts.md` | `colab/keepalive.py`, `find_notebook.py`, `save_to_drive.py` |

Plus already-created reference docs (also upload):
- `docs/system_flowchart.html` — existing flowchart (baseline, 2026-06-09)
- `docs/FTMO_SYSTEM_HANDOFF.md` — older handoff (2026-06-01, partially stale)
- `docs/KEY_FILES_FOR_CHAT.md` — earlier curated excerpt (now superseded by
  the full bundles above, but harmless to include)
- `docs/CREDENTIALS_MAP.md` — **where every credential/secret goes** (no
  actual secret values — see §7 below)

**Total**: ~21,900 lines of source across 12 bundles (~850KB). This is
everything in `FTMO_System` except: `colab/edge_profile/` (browser
cache/session — see §7), `catboost_info/` (stale training run artifacts),
`__pycache__/`, and binary `.joblib` model files.

---

## 1. MHP handoff is broken — don't rely on it

`memory_get_handoff` for `ai-trading-system-v81` throws a charmap/UTF-8 decode
error (`'charmap' codec can't decode byte 0x9d in position 1550`). Repo/project
context is currently unreadable from MHP. Leave the fix alone until Andy approves
it (separate task, requires editing `state.db`).

---

## 2. A flowchart already exists — check it first

`FTMO_System/docs/system_flowchart.html` (877 lines, **last modified 2026-06-09**,
just 1-2 days behind the current code) is an existing detailed visual flowchart
covering: MT5/OANDA → BridgeEA → 27-feature CSV → Strategy Runner (15 signal
sources) → 6-phase decision (Capital Check, Dimension Check, Counter Vote,
Integration, Danger Scoring, Anti-Fragile Entry) → signal file → EA execution →
logging → daily retrainer → FTMO risk limits/correlation/session filters.

**UPDATE 2026-06-14:** the updated/expanded version now exists as
`docs/system_flowchart_v2.html` (verified rebuild, 2026-06-11 content) — treat
**v2 as the current verified reference / START HERE**. The text below describes
the superseded 2026-06-09 `system_flowchart.html` baseline, kept for history.

A second doc, `docs/FTMO_SYSTEM_HANDOFF.md` (dated 2026-06-01), is **more stale**
— some details in it (label encoding) are now superseded by actual code (see §4).

---

## 3. Full directory/file inventory — `FTMO_System/`

```
FTMO_System/
├── run_system.py                  # Entry point
├── .gitignore
├── config/
│   └── ftmo_config.json           # Risk limits, ML thresholds, sessions, symbol config
├── core/
│   ├── live_trading_system.py     # Main orchestrator — 6-phase decision framework
│   ├── ensemble_predictor.py      # XGBoost-only predictor (LABELS=['SELL','HOLD','BUY'])
│   ├── feature_expander.py        # 27 → 105 feature expansion (unchanged)
│   ├── feature_history_recorder.py# Records feature snapshots for training/sequences
│   ├── exit_logic.py              # Trade exit/management logic
│   ├── azure_bridge.py            # Uploads features to Azure Blob; downloads Colab
│   │                               #   predictions (lgbm/catboost/transformer) — PARALLEL
│   │                               #   cloud inference path, separate from local XGBoost
│   ├── strategy_runner.py         # Runs 15 independent signal sources every cycle:
│   │                               #   6 EA-translated (sma_3crossover, tema_barrington,
│   │                               #   ama_scalper, sma_price_cross, dema_rsi_hf,
│   │                               #   dema_supertrend) + 9 rule-based
│   ├── rule_based_strategies.py   # The 9 rule-based strategies
│   ├── symbol_manager.py          # Dynamic MT5 symbol discovery + suffix stripping
│   ├── trade_outcome_simulator.py # Simulates fills/outcomes in sim mode
│   ├── unified_trade_logger.py    # Single logger for all trade sources
│   └── strategies/                # Implementations for the 6 EA-translated strategies:
│       ├── base_strategy.py
│       ├── ama_scalper.py
│       ├── dema_rsi_hf.py
│       ├── dema_supertrend.py
│       ├── sma_3crossover.py
│       ├── sma_price_cross.py
│       └── tema_barrington.py
├── confluence/                    # Confluence scoring (7-factor)
│   ├── confluence_scorer.py
│   ├── candlestick_patterns.py
│   ├── hard_filters.py
│   ├── htf_confirmation.py
│   ├── level_confluence.py
│   ├── pullback_detector.py
│   └── regime_detector.py
│   └── risk_manager.py
├── dimensions/                    # 4-dimension validation
│   ├── dimension_checker.py       # REGIME / SESSION / ML / CONFLUENCE → AGREE/DISAGREE/ABSTAIN
│   ├── danger_scorer.py           # 0-21 danger score, ≥13 blocks
│   ├── trade_history_tracker.py   # Streak tracking
│   └── anti_fragile_builder.py    # Probe (0.01) → build position logic
├── news_analysis/
│   ├── bias_manager.py
│   ├── sentiment_engine.py
│   ├── central_bank_analyzer.py
│   ├── data_release_analyzer.py
│   ├── economic_calendar.py
│   ├── government_analyzer.py
│   ├── config.py
│   └── data_sources/
│       ├── forexfactory.py
│       ├── central_bank_feeds.py
│       └── fred_api.py
├── training/
│   ├── daily_retrainer.py         # Daily/weekly XGBoost retraining
│   ├── data_labeler.py            # Labels execution outcomes
│   ├── build_training_sets.py
│   ├── download_dukascopy_all.py
│   ├── extract_features_all.py
│   ├── label_dukascopy_all.py
│   └── pretrain_dukascopy.py
├── scripts/
│   ├── health_watchdog.py         # Monitoring/alerting
│   ├── setup_colab_task.py        # Schedules Colab inference job
│   ├── setup_retrainer_task.py    # Schedules daily retrainer
│   ├── setup_trading_task.py      # Schedules main trading loop
│   └── setup_watchdog_task.py     # Schedules watchdog
├── ea/
│   └── BridgeEA_FTMO_v1.mq5       # MT5 EA (v2.32-derived, 27 features, dynamic symbols)
├── data/
│   ├── unified_trades.csv         # Master PYTHON SIM trade log (root of data/). NOTE:
│   │                               #   every row has actually_executed=True, but that means
│   │                               #   "sim decided to execute", NOT a broker fill. Only ~536
│   │                               #   of ~9,948 rows became real MT5 orders. P&L columns
│   │                               #   (profit_pips/profit_usd) are unit-inconsistent across
│   │                               #   asset classes — use win/loss SIGN only, not aggregates.
│   ├── features/                  # {SYMBOL}_features.csv, signal_{SYMBOL}.txt — empty now
│   ├── execution_log/             # trades.csv — empty now
│   ├── feature_history/           # 42 files — historical feature snapshots
│   ├── feature_sequences/         # 5,379 files (as of 2026-06-14) — sequence data (transformer/Colab)
│   ├── tick_trajectories/         # 8,973 files (as of 2026-06-14) — tick-level data post-signal
│   ├── training_data/             # empty (reserved)
│   ├── training_sets/             # 42 files — built train/val/test sets
│   ├── historical_data/           # 43 files (incl. features/, splits/ subdirs) — Dukascopy data
│   └── models/                    # 26 *.joblib XGBoost models (as of 2026-06-14):
│       original 8 majors + 18 from the HALTED Dukascopy pretrain run
│       (alphabetical AUDCAD..GBPAUD). 17 instruments have data prepped but
│       NO model yet: NZDCAD, NZDCHF, US100, US30, US500, USDCNH, USDCZK,
│       USDHUF, USDMXN, USDNOK, USDPLN, USDSEK, USDSGD, USDZAR, USOIL,
│       XAGUSD, XAUUSD. (AUDCAD origin RESOLVED: Dukascopy pretraining.)
│       NOTE: LightGBM/CatBoost/Transformer models do NOT live here — they are
│       written to C:\Users\mt5-admin\Documents\GitHub\AI-Trading-System\
│       models\current (+ transformer\ subdir) by the same pretrainer.
├── logs/
│   └── predictions/                # Prediction CSVs
├── colab/                          # keepalive.py, find_notebook.py, save_to_drive.py
│                                    #   (Colab automation scripts — bundled in §0)
│   └── edge_profile/                # Edge browser profile/session for Google login
│                                    #   (large — browser cache + LIVE Google session, see §7)
├── catboost_info/                  # CatBoost training artifacts (from a training run,
│                                    #   relevant to the Colab-side models, not local XGBoost)
└── docs/
    ├── FTMO_SYSTEM_HANDOFF.md      # 2026-06-01, partially stale (see §4)
    ├── system_flowchart_v2.html    # 2026-06-11 content, saved to disk 2026-06-14 —
    │                                #   VERIFIED architectural reference (START HERE).
    ├── system_flowchart.html       # 2026-06-09 baseline flowchart (superseded by v2)
    ├── CLAUDE_CHAT_HANDOFF.md      # this file
    ├── CREDENTIALS_MAP.md          # where every credential/secret goes (§7)
    ├── KEY_FILES_FOR_CHAT.md       # earlier curated excerpt (superseded by full bundles)
    └── full_source_bundles/        # complete source code, 12 files (see §0)
```

### Other top-level project folders (for context, not part of FTMO_System)
```
TradingSystem/
├── claude.md                          # Governs Claude Code behavior/rules
├── AzureDeploy/Phase4_LITE_System/    # OLD reference system (paused) — copy-source only
├── FTMO_System/                       # ACTIVE — described above
├── new_project_052626/AI-Trading-System/  # Local clone of GitHub repo
├── get_mt5_symbols.py
└── mt5_available_symbols.csv
```

---

## 4. Architecture facts — corrected/reconciled

- **Local ensemble = XGBoost ONLY**, confirmed in `core/ensemble_predictor.py`:
  `LABELS = ['SELL', 'HOLD', 'BUY']`, model files matched via `*_xgboost*.joblib`,
  `models_used: ['xgboost']`. The "XGBoost+LightGBM+CatBoost equal-weight ensemble"
  text in `live_trading_system.py`'s docstring is **stale leftover commentary**
  from the pre-adaptation v5.0 file — it does not reflect current behavior for the
  local path.
- **Label encoding is `0=SELL, 1=HOLD, 2=BUY`** (per `FTMO_SYSTEM_HANDOFF.md` and
  actual code) — this **differs from CLAUDE.md's stated `0=HOLD, 1=BUY, 2=SELL`**.
  The deployed code uses SELL/HOLD/BUY ordering. Do not "fix" this without
  confirming with Andy — changing it would invert predictions.
- **LightGBM/CatBoost/Transformer are real, but they live on the Colab/cloud
  side**, not local: `azure_bridge.py` uploads per-symbol feature CSVs to Azure
  Blob; Google Colab reads them, runs LightGBM/CatBoost/Transformer inference,
  and writes prediction JSONs back (`{"lgbm": {...}, "catboost": {...},
  "transformer": {...}}`). `live_trading_system.py` polls
  `azure.get_all_predictions()` and has staleness-warning logic for when Colab
  predictions go stale. **This cloud path is a fully separate model ensemble
  feeding into the decision alongside local XGBoost + the 15 strategy-runner
  signals.**
- **Strategy Runner is a major component not in the original CLAUDE.md spec**:
  15 independent signal sources every cycle (6 EA-translated technical
  strategies + 9 rule-based strategies), each contributing a vote with
  attribution into the decision framework.
- **`data/feature_sequences/` (5,379 files) and `data/tick_trajectories/` (8,973
  files, as of 2026-06-14)** show substantial accumulated runtime data — this
  system has been running in sim mode for a while, not freshly started.
- **`data/models/` now has 26 XGBoost models** (original 8 majors + 18 from the
  halted Dukascopy pretrain). The earlier "AUDCAD mystery" is RESOLVED: the
  Dukascopy pretraining run produces per-symbol models. LightGBM/CatBoost/
  Transformer counterparts live at `GitHub\AI-Trading-System\models\current`.
- **Per-model training independence VERIFIED (2026-06-14):** each symbol's 4
  model types train only on that symbol's own splits (no cross-symbol pooling);
  labels = forward 24-candle/20-pip price-action (`label_dukascopy_all.py`),
  never derived from any signal source's trade outcomes; the 27 features
  (`feature_history_recorder.FEATURE_27`) are pure technical/price-derived
  (incl. candle-geometry "sentiment" via `extract_features_all.calc_sentiment`),
  with NO model output used as a feature and NO stacking. The 4 types share
  identical features+labels and diversify by ARCHITECTURE — confirmed intended
  by Andy. (See §8 2026-06-14.)
- **Dukascopy training data validated clean (2026-06-14):** raw M15 candles for
  all 43 instruments span 2023-06-12 -> 2026-06-11 with no frozen/stale chunks
  (the prior failure mode); `extract_features_all.validate_data()` has its own
  frozen gate and all 43 passed. Minor: EURCZK has one ~19-bar flat patch
  (~0.03%, negligible); EURHUF has short history (46,606 bars vs ~74,500).
- **In practice the live system is rule/EA-strategy-driven, NOT ML-driven
  (2026-06-14):** over 06-04..06-09 the EA placed 536 real orders, of which
  XGBoost = 4 and Colab/LGBM = 0; the bulk were high_volatility_reversal +
  EA-translated strategies. XGBoost signals also get NO simulated outcome in
  `unified_trades.csv` (outcome empty, profit_pips NaN), so there is currently
  zero sim performance data for the local ML path. The pretrained models are
  not meaningfully influencing execution. (See §8 2026-06-14 + §6 q8/q9.)

---

## 5. Coordination protocol: Chat plans, Code implements

**Division of labor (per Andy):**
- **Claude Chat** = planning, architecture decisions, flowcharts/diagrams,
  reconciling requirements with Andy.
- **Claude Code** = all actual file reads, edits, and implementation on the local
  drive — same files and same repo Chat is reasoning about.

**Practical mechanics (Chat now has direct Windows-MCP FileSystem access):**
1. Chat should produce **plans/specs**, not code diffs to be hand-applied. When a
   plan is ready, Andy relays it to Claude Code, which reads the real files,
   confirms feasibility against actual current code (not the plan's assumptions),
   and implements per `claude.md` rules (plan mode, explicit approval per file,
   full files, no hardcoded credentials).
2. When Chat needs to see real file contents to plan accurately (e.g., the 6-phase
   logic in `live_trading_system.py`, `azure_bridge.py`, `strategy_runner.py`,
   `confluence_scorer.py`), Andy should ask Claude Code to dump those specific
   files/sections, then paste into Chat. Don't let Chat guess from
   `system_flowchart.html` alone if precision matters (e.g., exact thresholds,
   exact label order).
3. **Source of truth ranking** when docs disagree: (1) actual code in
   `FTMO_System/`, (2) `system_flowchart_v2.html` (verified 2026-06-11, saved
   2026-06-14; the older `system_flowchart.html` 2026-06-09 is superseded),
   (3) `FTMO_SYSTEM_HANDOFF.md` (2026-06-01), (4) `claude.md` original spec
   (oldest, most superseded).
4. **Decisions/clarifications must be written down**, since MHP handoff is
   currently broken. Suggested home: append a "Decisions Log" section to this
   file (`CLAUDE_CHAT_HANDOFF.md`) any time Andy resolves an open question —
   Claude Code can do this on request. This file then becomes the durable
   cross-session memory until MHP is fixed.
5. Both Chat and Code should reference files by their path under
   `C:\Users\mt5-admin\Documents\TradingSystem\FTMO_System\` so there's no
   ambiguity about which copy (vs. `AzureDeploy/` or the GitHub clone) is meant.

---

## 6. Open questions for Andy

1. Confirm: local inference is XGBoost-only; LightGBM/CatBoost/Transformer run on
   Colab via `azure_bridge.py`. Is that the intended permanent split, or should
   everything eventually run locally?
2. Label encoding is `0=SELL,1=HOLD,2=BUY` in deployed code vs `0=HOLD,1=BUY,2=SELL`
   in `claude.md` — which is correct going forward?
3. `data/models/AUDCAD_xgboost.joblib` — where did this come from?
   **(RESOLVED 2026-06-14: produced by the Dukascopy pretraining run.)**
4. Is `new_project_052626/AI-Trading-System` (GitHub clone) in sync with
   `FTMO_System/`, or has one diverged from the other?
5. Should the MHP `state.db` encoding bug be fixed (with approval)?
6. Should `colab/edge_profile/` be added to `.gitignore` (see §7)? It's not
   currently excluded and contains live Google session data.

   --- Added 2026-06-14 (from trade-analysis + verification session) ---
7. **Real P&L is unknown.** Sim log P&L columns are unit-broken; the EA's
   `Terminal\Common\Files\trades.csv` is an order-PLACEMENT log (all OPEN,
   profit=0). Realized results exist only in MT5's binary history (`bases\`).
   To get true P&L: an MQL5 `HistorySelect` export OR a Python `MetaTrader5`
   `history_deals_get` pull (terminal running + Andy approval). trades.csv
   tickets join to the 536 placed orders.
8. **XGBoost outcome-scoring gap.** `trade_outcome_simulator` never scores the
   XGBoost path -> zero sim performance data for XGBoost. Likely cause: XGBoost
   rows have empty entry/SL/TP so no simulated position opens. (Code task — plan first.)
9. **Strategic: ML path barely executes** — XGBoost 4 real orders, Colab 0.
   Continue investing in the 4-model-per-symbol / Dukascopy pretraining path, or
   refocus on the rule/EA strategies that actually drive trades?
10. **EA stopped placing orders after 06-09** while the sim ran to 06-11 — why?
    Check `mt5_bridge_commands.csv` / `mt5_bridge_responses.csv` + the EE0304
    Experts log across 06-09..06-11. (Read-only diagnosis OK.)
11. **Colab (93.6% sim win, n=78) never executed** (0 real orders) — filtered by
    the gate, or not wired to the EA path?
12. **USDJPY underperforms** — 43.3% sim win on 263 trades (worst symbol).
    Review / exclude / retune? (JPY pip = 0.01 — check pip handling.)
13. **Pretraining resume scope.** PID 10300 (`pretrain_dukascopy`) killed by Andy
    ~2026-06-13 17:57, mid-GBPAUD. To finish: GBPAUD needs its transformer
    (xgb+lgbm+catboost saved, transformer missing) + the 17 unmodeled instruments
    in §3. (Training-state action — approval.)
14. **`system_flowchart_v2.html`** — **(RESOLVED 2026-06-14: restored to
    `docs\system_flowchart_v2.html` from Andy's pasted content; it is the
    VERIFIED reference, superseding the 2026-06-09 `system_flowchart.html`.)**

---

## 7. Credentials & secrets — see `docs/CREDENTIALS_MAP.md` for full detail

Quick summary (no actual values anywhere — just where each goes):

| Credential | Location | Set? |
|---|---|---|
| FTMO MT5 login/password/server | `config/ftmo_config.json` → `account` (gitignored) | No — blank/demo |
| Azure Storage connection string | env var `AZURE_STORAGE_CONNECTION_STRING` | No |
| FRED API key | env var `FRED_API_KEY` | No |
| Google account (Colab) | `colab/edge_profile/` browser session (one-time manual login via `colab/keepalive.py --login`) | Yes — already logged in |

`config/ftmo_config.json` is gitignored ("# Credentials") but exists on disk
with placeholder/empty account fields. `colab/edge_profile/` contains a *live*
Google session and is **not yet gitignored** — see open question #6.

### MT5 / terminal runtime map (added 2026-06-14)

- **Active terminal instance:** `…\MetaQuotes\Terminal\EE0304F13905552AE0B5EAEFB04866EB\`
  (one of 7 instances). EA = **`BridgeEA_FTMO_v1`**, attached to EURUSD.sim H4;
  Experts log live through 2026-06-11.
- **EA <-> Python comms (`…\MetaQuotes\Terminal\Common\Files\`):**
  - `trades.csv` — EA order PLACEMENTS only (all OPEN, profit=0; schema shifts
    mid-file 11->13 cols; later rows add `signal_id`+`source`; `signal_id` ==
    sim `trade_id`). NOT realized P&L.
  - `open_positions.csv` — open positions (header-only when flat).
  - `mt5_bridge_commands.csv` / `mt5_bridge_responses.csv` — bridge command/ack
    stream (use for the 06-09 EA-stop investigation, q10).
- **Terminal MQL5\Files (`…\EE0304…\MQL5\Files\`):** `latest_features.csv`,
  `trades_execution_log.csv` (header-only).
- **Realized P&L is NOT in any CSV** — only MT5's internal binary history
  (`…\EE0304…\bases\`), via the MT5 UI statement export or a `HistorySelect`
  script (see §6 q7).


---

## 8. Decisions Log

(Durable cross-session memory while MHP `memory_get_handoff` is broken. Newest first.)

### 2026-06-22 — XGBoost moved to Colab, two tick-pricing bugs fixed, flat 0.01 mode, retrainer disabled, training rule corrected to Option A (Claude Code, direct edits + GitHub push)

**All changes by Claude Code (this CLI) on the VPS, then synced to repo. New demo account `1600149577`, $200,000, `simulation_mode`, trade_allowed=True; EA on M15; account trades enabled (unlike old 1600140290).**

**1) XGBoost moved INTO Colab (it now runs there, NOT locally).** "Put xgboost in colab" = *move* it to free the local device — NOT run in both places. There is one xgboost source: `colab_xgboost`.
- `colab/trading_inference.ipynb` (repo copy, the one Colab clones): Cell 4 loads `_xgboost.joblib` → `xgboost_models`; Cell 7 runs it in `run_inference_for_symbol` (4-tuple return) uploading `colab_xgboost`; Cells 8/9 show XGB. Also fixed a latent Cell 9 heartbeat bug (literal `\n` would SyntaxError the loop).
- Copied 35 missing `_xgboost.joblib` into repo `models/current/` (was 8, now 43 — full LGB/CAT/XGB parity). **Pushed: commit c301712.**
- `core/azure_bridge.py:158` now ingests `xgboost` in `get_all_predictions` source list.
- ENCODING: the whole pipeline (build_training_sets, label_dukascopy_all, data_labeler, all retrainer models) uses **0=SELL,1=HOLD,2=BUY** — matches Colab Cell 7. The CLAUDE.md "0=HOLD,1=BUY,2=SELL" note is STALE. No inversion risk.
- **PENDING:** removing the local 6-phase XGBoost path (the actual "free local"). Deferred until clean post-fix data shows which sources are profitable — Andy wants to see performance before cutting.

**2) TWO tick-pricing bugs fixed — same MT5 approach (`mt5.symbol_info` trade_tick_size/trade_tick_value, forex table fallback).**
- `confluence/risk_manager.py`: position risk used a hardcoded forex pip table (0.0001/$10) for ALL symbols → non-forex grossly mispriced (US500 0.10 lot = $225,000 phantom), pinning portfolio risk at **208.5%** and blocking ALL signals. Fixed via `_get_risk_spec()` (US500 → $2.25, gold/CNH correct, forex unchanged).
- `core/trade_outcome_simulator.py`: `profit_usd = (exit-entry)*100000*vol` hardcoded forex contract size → indices/metals/crypto PnL overstated up to 100,000× (US500 $7,800 vs real $0.08; this is why old `unified_trades` shows −$320M sources). Fixed via `_contract_spec()`. Now simulated PnL matches the MT5 broker P/L files (the cross-check Andy wants).

**3) Flat 0.01 mode** — `core/live_trading_system.py`: `FLAT_LOT=0.01`, `DISABLE_SCALING=True`. One 0.01 position per signal; no probe/build/scale-in/scale-out (broker min is 0.01; can't partial-close it). EA already honors the lot Python sends (≥0.01), so no recompile. Strategy + Colab paths already emitted 0.01.

**4) Daily retrainer DISABLED** — `config/ftmo_config.json` `retraining.enabled=false` + `run_system.py` gates the thread. No Windows retrainer task is registered.

**5) Training rule CORRECTED → Option A (hard rule).** Andy: "I do not want them trained by a signal other than the ones they themselves generate." Each ML model trains ONLY on the outcomes of trades IT generated (filter `unified_trades` by `signal_source`), labeled by price resolution (TP/SL via `data_labeler.label_trade`). NOT the shared full-history price-action labels that `daily_retrainer.py` currently builds (that is Option B and contradicts the rule). Source map: xgboost←`colab_xgboost`, lightgbm←`colab_lgbm`, catboost←`colab_catboost`, transformer←`colab_transformer`. Rule-based strategies never retrained. Option-A rework was PLANNED then SHELVED (retrainer disabled until post-fix own-trade data exists). Pretrained seeds = ~3yr Dukascopy (separate pipeline). Prior handoff/memory said "price-action labels only" — that was WRONG; corrected.

**6) DO NOT use pre-2026-06-22 `unified_trades.csv`** for training or performance decisions: `profit_usd` corrupted (sim bug #2), lots vary (old scaling), ML/6-phase was risk-blocked so it barely traded. Win-rate-by-geometry (PnL-independent) leader so far: `colab_lgbm` ~85%, but win rate ≠ profit. Also ~10 malformed rows (signal_source = PARTIAL_TP/numbers) — concurrent-write corruption; a guard was approved but not yet added.

**7) GitHub pushes:** `c301712` (xgboost notebook + 35 models), `35db803` (VPS→repo sync of the 5 changed code files: risk_manager, trade_outcome_simulator, live_trading_system, azure_bridge, run_system). Config stays gitignored.

**Open / pending:** (a) Andy restarts `run_system.py` manually (picks up flat-0.01 + both pricing fixes) and re-runs the Colab notebook (picks up xgboost). (b) Accumulate clean post-fix data. (c) Build per-source profitability report vs MT5 broker P/L. (d) THEN decide local 6-phase removal + re-enable an Option-A retrainer. (e) Add the malformed-row guard. (f) The earlier full VPS→repo sync (34 VPS-only files, §8 2026-06-18b item 6) is still only partially done — this session synced the 5 it touched; the rest remain.

### 2026-06-18b — CatBoost/Transformer failure root-caused, M15 timeframe correction, EA recompile not needed, full VPS→repo sync planned (Chat, read-only + Decisions-Log write)

**Continuation of the 2026-06-18 session. All analysis read-only via Windows-MCP.**

**1) Option C XGBoost scoring fix — IMPLEMENTED by Claude Code (reported complete).**
- Spec was: `core/live_trading_system.py` — thread `features_dict` into `write_trade_commands(...)` and restore dropped keys in the `commands.append({...})` block (`features`, `trade_id`, `source`, `source_type`, `confluence_score`, `dimension_count`, `danger_score`, `strategy_votes`). No change to `_write_per_symbol_signals` or `trade_outcome_simulator`.
- Code confirmed done. VPS `live_trading_system.py` mtime now 06-18 11:43. NOT YET VALIDATED — system is paused (no run_system, scheduled tasks disabled since 06-11), so no new XGBoost rows exist to check. Validation pending first sim run: confirm new xgboost rows show close>0/atr>0 + non-empty trade_id/context + simulator assigns outcomes.

**2) Why CatBoost + Transformer (Colab) generated 0 signals — ROOT-CAUSED from `colab/trading_inference.ipynb` + model inventory (verified).**
- ARCHITECTURE REMINDER (Andy corrected): neural nets (LightGBM, CatBoost, Transformer) MUST run in Colab — running them on the VPS crashes it (memory). Only XGBoost runs locally (PowerShell via ensemble_predictor). The `GitHub\AI-Trading-System\models\current\` dir is the REPO Colab clones from, NOT local-execution models.
- Notebook Cell 4 loads each model type independently behind a strict 27-feature gate: `if n != N_FEATURES (27): SKIP`. lgbm from `*_lightgbm.joblib`, catboost from `*_catboost.joblib`, transformer from `transformer/*.pth` subdir.
- **CatBoost = 0 signals: feature-gate BUG.** The gate read feature count via `getattr(m,'n_features_in_', getattr(m,'n_features_',None))` which returns **0 for CatBoost** (CatBoost doesn't populate n_features_in_). Verified: all 43 catboost .joblib report features=0 → all SKIPPED. The models are fine; the introspection check was wrong. ALSO timeline: earliest catboost file mtime 06-11 10:01 → NO catboost models existed during the live window (06-05→06-09) anyway.
- **Transformer = 0 signals: 58-feature stale models.** During the live window the only transformer files were old `{SYM}.sim_transformer.pth` (mtime 06-09 02:12, **input_dim=58**) → SKIPPED by the 27-feature gate. New 27-feature `{SYM}_transformer.pth` files (input_dim=27, OK) were created 06-11 18:23→06-16 — AFTER the window. Extra structural risk: SYMBOL_MAP (Cell 8) is built from `.joblib` files only; transformer looked up by a differently-normalized base name → mismatch can skip it even when loaded.
- **LightGBM = 78 signals: worked.** 27-feature major models predated the window and passed the gate.
- Execution (all 3 = 0 live orders): uniform cause already known — Azure bridge disabled (no AZURE_STORAGE_CONNECTION_STRING), nothing reached the EA.

**3) CatBoost gate fix — SPECCED + IMPLEMENTED by Claude Code (reported complete).**
- Fix in `trading_inference.ipynb` Cell 4 (BOTH the FTMO_System copy and the GitHub repo copy `src/ftmo_system/colab/`): added `import numpy as np` + a `get_model_feature_count(model)` helper with a 3-tier cascade — (1) `n_features_in_`/`n_features_` (LightGBM, no regression), (2) `get_feature_importance()` length (CatBoost), (3) `predict_proba(np.zeros((1,N_FEATURES)))` test-predict fallback else None. Gate line changed to `n = get_model_feature_count(m)`. Transformer `.pth` gate (reads embedding.weight shape) untouched; Cells 5–9 untouched.
- **NOT yet live in Colab** — Colab clones from GitHub at session start, and the repo copy is committed-pending (see #6). Must be pushed before Colab picks it up.

**4) EA restart facts (verified on disk):**
- EA does NOT need recompile. `ea/BridgeEA_FTMO_v1.mq5` source mtime 06-09 02:25; compiled `BridgeEA_FTMO_v1.ex5` mtime 06-09 02:29 (matches). Today's fixes were Python-side (Option C) and Colab-side (CatBoost) — neither touched the EA. Same compiled EA.
- EA is timer-driven (OnTimer every TimerSeconds=3); OnTick empty. Scans all Market Watch symbols regardless of which chart it's attached to.

**5) EA TIMEFRAME CORRECTION — place EA on M15, NOT H4 (verified from training pipeline).**
- `training/extract_features_all.py` computes all 27 features from `{SYMBOL}_M15_dukascopy.csv` — i.e. PRIMARY features are M15. HTF features are resampled M15→H4 (HTF_MULTIPLIER=16 = 16×15min).
- EA primary indicators use `iATR(sym, 0, ...)`, `iRSI(sym, 0, ...)` etc. where timeframe `0` = CHART timeframe. HTF uses hardcoded input `HTF_Timeframe=PERIOD_H4`.
- So on an H4 chart, every primary live feature (ATR/RSI/EMA/Bollinger/SMA/momentum/stochastic/sentiment) is computed on H4 bars while models were trained on M15 → distribution mismatch (H4 ATR much larger, H4 RSI smoother, etc.). The EA has been fed mismatched features the entire run.
- **ACTION: attach EA to an M15 chart** (any symbol, e.g. EURUSD.sim M15). HTF inputs stay H4 (correct). This was the prior-session architectural note now confirmed against code.

**6) FULL VPS→repo SYNC — audited, planned, handed to Code (was: FTMO_System not under git).**
- `FTMO_System\` on the VPS is NOT its own git repo. It is meant to be tracked AS `src/ftmo_system/` inside repo `Codebreaker-source/AI-Trading-System` (branch main, remote origin https://github.com/Codebreaker-source/AI-Trading-System.git). The VPS working copy had drifted and was never fully committed.
- Read-only divergence audit (hash-compare, excluding __pycache__/logs/data/binaries): **45 identical, 9 differ (ALL VPS-newer), 34 VPS-only, 0 repo-only.** repo_only=0 ⇒ clean ONE-DIRECTIONAL sync VPS→repo; no repo-side edits to reconcile. (Earlier ensemble_predictor.py "repo newer" scare was a false alarm — identical by hash; mtime ≠ content.)
- 9 differ (VPS-newer): live_trading_system.py (Option C), trading_inference.ipynb (CatBoost fix, already staged M), config/ftmo_config.json (IGNORED-credentials), unified_trade_logger.py, run_system.py, training/daily_retrainer.py, colab/keepalive.py, scripts/setup_colab_task.py, docs/FTMO_SYSTEM_HANDOFF.md.
- 34 VPS-only highlights (real code never tracked): core/exit_logic.py, core/feature_history_recorder.py, **core/trade_outcome_simulator.py** (sim oracle), full training/ pipeline (extract_features_all, download_dukascopy_all, label_dukascopy_all, build_training_sets, pretrain_dukascopy), scripts/health_watchdog.py + setup_watchdog_task.py, colab/find_notebook.py + save_to_drive.py; plus docs.
- Repo `.gitignore` already covers: config/ftmo_config.json, data/features|execution_log|training_data, data/models/*.joblib, logs/, __pycache__, ea/*.ex5. Confirmed ftmo_config.json is NOT tracked (ls-files empty) — stays ignored. CREDENTIALS_MAP not tracked.
- **DECISIONS (Andy, 2026-06-18):** (a) FULL sync — make `src/ftmo_system` a true mirror of the VPS. (b) CREDENTIALS_MAP.md → SAFE TO COMMIT (only meaningful to Andy). (c) docs/FTMO_SYSTEM_HANDOFF.md → UPDATE the stale 06-04 repo copy (06-16 VPS version) as a VPS-failure backstop. (d) Add gitignore rules for handoff backups, .claude/, data/, *.parquet, model binaries.
- Sync spec handed to Claude Code (implementer for the copies/gitignore/commit/push). Steps: branch backup → extend .gitignore → copy 7 updated (minus ignored config) + FTMO_SYSTEM_HANDOFF update + ~24 new code/doc files → single commit → push origin/main → verify tracked count rose and no ignored file staged.

**Open / pending after this:** push the sync (Code) so Colab picks up the CatBoost fix; start sim system + manual Colab and VALIDATE all sources generate+score (XGBoost via Option C; LightGBM still works; CatBoost via gate fix; Transformer via new 27-feat models) and that Colab signals reach the EA once Azure bridge is enabled; place EA on M15; demo account 1600140290 still trading-disabled on OANDA server (blocks live fills until re-enabled / fresh demo).

### 2026-06-18 — XGBoost outcome-scoring root cause (verified in data), Colab routing, EA-stop cause, account identity, retro-scoring ruled out, Option-C fix decision (Chat, read-only)

**Scope:** Followed the 2026-06-14 sim-vs-actual analysis into the open follow-ups. All read-only via Windows-MCP (FileSystem reliable; PowerShell+Python+pandas worked this session — earlier flakiness did not recur). Code-trace + data-verification.

**1) XGBoost outcome-scoring gap — ROOT CAUSE FOUND, supersedes q8's hypothesis.**
- q8 guessed "XGBoost rows have empty entry/SL/TP so no sim position opens." That is NOT the mechanism. `trade_outcome_simulator._process_row` RECONSTRUCTS entry/SL/TP itself from the row's `close`+`atr`; it does not need them pre-filled.
- Actual cause: **all 300 XGBoost rows are logged with `close=0.0` and `atr=0.0`** (verified in data: 300/300 close==0 AND atr==0, literal zeros not NaN; all 300 actually_executed=true, clean BUY/SELL 159/141; 0 scored). The simulator guard `if atr<=0 or close<=0: return` skips them before any outcome is written.
- Why zero: the XGBoost unified row is written in `live_trading_system._write_per_symbol_signals`, which reads `close=float(features[0])`, `atr=float(features[16])` from `cmd['features']`. But `write_trade_commands` builds each `cmd` with only 7 keys (symbol, action, confidence, sl_price, tp_price, lot_size, timestamp) and **drops `features`** (plus `trade_id`, `source`, `source_type`, `confluence_score`, `dimension_count`, `danger_score`, `strategy_votes`) — even though `generate_signals` put them on the `signal` dict. So features=[] -> close/atr default 0.0.
- Contrast: strategy/ea_translation rows are logged in `_run_strategy_engine` with the REAL `features_dict.get(symbol)` vector -> real close/atr (verified: 9,560/9,560 strategy rows have close>0 AND atr>0; 9,546 scored). That is the ENTIRE difference between scored and unscored.
- Secondary damage from same dropped-keys bug: `_write_per_symbol_signals` mints a NEW `make_trade_id` (not the make_ml_predictions trade_id in `logs/predictions/`), breaking lineage; and gate-context columns log as 0 for the one source that actually runs the gate.

**2) Colab routing (q11) — RESOLVED: wired correctly; the 0 is upstream config, not a routing break.**
- Colab signals ARE wired to the EA identically to the 15 strategy sources (`_run_strategy_engine` writes the same `signal_{SYMBOL}_{source}.txt` into Common\Files, same cooldown, same `log_signal` with real features[0]/[16] — which is why the 78 colab rows DID get sim-scored).
- The whole Colab block sits behind `if self.azure and self.azure.enabled:`. `azure_bridge.AzureBridge.enabled` requires the SDK installed AND `AZURE_STORAGE_CONNECTION_STRING` set AND a successful connect. Per CREDENTIALS_MAP that env var is NOT set -> enabled=False -> no feature upload, `get_all_predictions()` returns {} -> no colab signal files -> EA never sees one -> 0 colab orders. Turning Colab on is a config/[Code] decision, not a code-routing fix.
- (The 78 colab rows existing means azure.enabled was True during SOME earlier window; not investigated further per Andy — Colab runs fine on manual start, staying as-is.)

**3) EA stopped placing after 06-09 (q10) — RESOLVED: broker-side trading disablement, not a fault.**
- Evidence from EE0304 terminal JOURNAL logs (`...\EE0304...\logs\YYYYMMDD.log`; the Common\Files `mt5_bridge_commands.csv` named in q10 is a STALE 2025-09-23 file from an old bridge — ignore it):
  - `trades.csv` (EA placements) last write 2026-06-09 09:46:13.
  - 06-09 journal: 09:46:34 burst of closing deals flattens positions; 09:49:35 `connection to OANDA-Demo-1 lost` -> re-auth 09:49:36 -> 09:49:38 sync "0 positions, 0 orders" then **`trading has been disabled - disabled on server`**; 13:35 EA removed from chart + terminal exit (code 0).
  - 06-10 journal: terminal relaunched 07:30:25 (the FTMO_Trading_System scheduled-task time — still enabled pre-06-11), EA loaded, but every order from 07:31 fails `'0': failed market ... [Request rejected due to absence of network connection]` — account context is **`'0'`** (trade account not authorized).
- So: broker disabled trading on **account 1600140290** server-side at 06-09 09:49 (positions force-flattened first); relaunched terminal could not authorize the trade account, so 100% of post-06-09 orders were rejected. The EA keeps writing feature CSVs the whole time (needs no trade auth — explains EURUSD.sim_features.csv updating to 06-16) and Python kept issuing commands to 06-11; neither means anything filled. **`actually_executed=True` in the sim log is doubly meaningless post-06-09.**
- RISK (flagged, not acted on): demo account 1600140290 is currently trading-disabled on the broker / terminal relaunches as account '0'. This BLOCKS the roadmap's validate-on-demo phase until the account is re-enabled or a fresh demo is provisioned and the terminal re-authorized. Cause unknown (demo expiry / inactivity / server action). Verify in OANDA dashboard before demo-validation.

**4) Account identity (was open):** the live account during the 06-04..06-09 run = **1600140290** (from 06-09 journal authorize lines), matching the flowchart baseline, NOT the blank config account.

**5) Real-P&L export (q7) — plan was drafted then DROPPED by Andy.** Recommended path had been an MQL5 `HistorySelect` script (Option B) over 06-03..06-10 (all real fills confined to 06-04..06-09 09:46; nothing filled after). Andy decided broker P&L reconciliation is not wanted — in sim mode the `trade_outcome_simulator` is the outcome oracle by design, and the demo only filled a partial window before being disabled. **No MT5 export will be done.** trades.csv remains placement-only (536 rows, all OPEN, profit=0).

**6) Complete source x symbol metrics produced (read-only, from `unified_trades.csv` + `trades.csv`):**
- Only **8 of the ~19 expected signal sources ever logged any row.** Present: high_volatility_reversal (3,295), tema_barrington (2,330), dema_supertrend (2,167), dema_rsi_hf (1,142), ama_scalper (602), xgboost (300, unscored), colab_lgbm (78), sma_price_cross (24). MISSING/zero: sma_3crossover; 8 of 9 rule-based (volume_breakout, currency_strength_divergence, volatility_breakout, trend_following, mean_reversion, volatility_contraction, currency_correlation, low_volatility_momentum); colab_catboost; colab_transformer.
- Sim win% by source (sign-only, PARTIAL_TP-inflated, NOT profitability): colab_lgbm 93.6, dema_rsi_hf 74.0, rule_based/high_volatility_reversal 67.9, dema_supertrend 66.0, tema_barrington 65.2, ama_scalper 64.3, sma_price_cross 50.0 (n=24, noise), xgboost — (0 scored). Direction BUY 68.6% / SELL 64.6% (long-biased, ~72% BUY).
- Fired live orders (`trades.csv`, 536, placement-only, no outcomes): high_volatility_reversal 188 (BUY-only), tema_barrington 128, dema_supertrend 128, dema_rsi_hf 65, pre-attribution 23, xgboost 4; ama_scalper/sma_price_cross/colab_lgbm = 0 fired. Dominated by high_volatility_reversal on US500 (140) + USOIL (45). Confirms live execution is rule/EA-driven, and the highest sim-win sources (colab_lgbm, ama_scalper) placed ZERO live orders.

**7) XGBoost retro-scoring — investigated and RULED OUT (Andy chose Option C).**
- Backfill sources for the missing close/atr checked: `logs/predictions/predictions_*.csv` carry only timestamp/pair/prediction/confidence/probs/trade_id + empty actual_outcome/pnl — NO close/atr/features. A same-cycle strategy-row join (inherit close/atr from a same-symbol strategy row) covers only **46/300** rows within 120s (median gap ~43min, p90 ~6h) — XGBoost and strategies don't share cycles. So retro-scoring the 300 would require reconstructing close/atr from historical Dukascopy bars + a coarser price path -> approximate, not comparable to natively-scored rows.
- **DECISION (Andy, 2026-06-18): Option C** — do NOT retro-score the existing 300; fix the logging path so all FUTURE XGBoost signals carry real close/atr and get scored natively. First scored XGBoost numbers come from the next sim run after the fix. (XGBoost runs LOCALLY in a PowerShell process via ensemble_predictor — NOT in Colab; Colab = lgbm/catboost/transformer cloud path.)

**8) Code fix specced for Claude Code (Option C) — PENDING implementation, plan-first/full-file/version-bump:**
- `core/live_trading_system.py`: thread `features_dict` into `write_trade_commands(...)` and, in the `commands.append({...})` block, add `'features': features_dict.get(pair, [])` plus the dropped attribution/context (`trade_id`, `source`, `source_type`, `confluence_score`, `dimension_count`, `danger_score`, `strategy_votes`) sourced from the `signal` dict. No change to `_write_per_symbol_signals` (already reads cmd.get('features',...)) or `trade_outcome_simulator` (guard is correct — it was being fed zeros). Validate after deploy: new XGBoost rows show close>0/atr>0 + non-empty trade_id/context + simulator assigns outcomes.

**Open follow-ups carried forward:** implement the Option-C fix (Code); the 8-of-19 missing sources (esp. 8 rule-based + sma_3crossover never firing) is unexplained — possible code check on `rule_based_strategies.py`/`strategy_runner.py` if Andy wants to know why; demo-account 1600140290 trading-disabled blocker for demo-validation phase.

### 2026-06-14 — Sim vs actual trade analysis (06-05→06-11 data) + XGBoost/calibration corrections (Chat, read-only)

**Scope:** Analyzed `data\unified_trades.csv` (Python sim log) vs `Terminal\Common\Files\trades.csv` (EA actual orders). All read-only.

**Data inventory:**
- Sim log `unified_trades.csv`: 9,948 rows, 2026-06-05 → 06-11 (~6 days), all `.sim`, every row would_execute=True AND actually_executed=True (no shadow/declined rows in-file). ~10 malformed rows. 06-11 had a 5,542-row spike (89% ea_translation) that produced NO real orders — likely a loop/replay anomaly.
- Actual EA log `trades.csv` (MT5 Common\Files): 536 orders placed 2026-06-04 → 06-09. Schema shifts mid-file (11→13 cols; later rows add `signal_id`+`source`, where signal_id == sim trade_id). EVERY row is OPEN with profit=0 — it is an order-PLACEMENT log, NOT realized P&L. `open_positions.csv` empty. Active terminal = EE0304..., EA = BridgeEA_FTMO_v1.

**KEY CORRECTION (supersedes claims I made earlier the same day in this chat):**
- XGBoost "0% win on 300" is NOT a model failure or direction inversion. Per-model split: XGBoost rows have NO simulated outcome at all (`outcome` empty, `profit_pips` all NaN); the 0% was a NaN-counted-as-non-win artifact. Real issue = `trade_outcome_simulator` does not score the XGBoost path, so there is zero sim performance data for XGBoost.
- The "inverted ML confidence calibration" flagged earlier was a POOLING artifact (high-conf buckets were XGBoost=NaN, low-conf had Colab). Per-model there is NO inversion. Retracted.

**A) Sim vs actual executed:**
- 9,938 sim shadow signals vs 536 actual orders. Execution gate DOES select better signals: placed signals' sim win% = 87.5% vs not-placed = 64.2% (driven by rule/EA sources that have outcomes).
- Actual orders by source: high_volatility_reversal 188, tema_barrington 128, dema_supertrend 128, dema_rsi_hf 65, xgboost 4, colab_cloud 0.
- Realized P&L is NOT available on disk anywhere (searched all terminals/logs). It exists only in MT5's binary history DB (`bases\`). To obtain: MT5 UI statement export OR a HistorySelect script (terminal/code action, needs approval).
- EA stopped placing orders after 06-09 while sim ran to 06-11 (gap to investigate). EA correctly skipped the 06-06/06-07 weekend; sim logged weekend forex (stale-market fills — sim-fidelity issue).

**B) Signal source (sim shadow win%):** colab_cloud 93.6% (n=78, never executed, tiny +/-6 pip outcomes, unproven); rule_based 67.9% (n=3,295, BUY-only high_volatility_reversal); ea_translation 66.8% (n=6,265; best strategy dema_rsi_hf 73.9%); xgboost = no outcomes recorded.

**C) Sim trade shape:**
- Exit mix: PARTIAL_TP 49% (always a small booked win), SL 40% (loss), TP 10%. The ~65% headline win rate is mechanically inflated by partial-TP and does NOT establish profitability — need R/expectancy, which is uncomputable from the sim log (entry/SL not stored per row; only `close`, `exit_price`, `outcome`, `profit_pips`).
- Direction: BUY 67.0% (n=7,140) vs SELL 61.2% (n=2,798); book is long-biased.
- Per-symbol weakest: USDJPY 43.3%, USOIL 51.2%, AUDUSD 55.5%, GBPUSD 55.6%, XAUUSD 56.1%. Strongest: USDHUF 87.8%, BTCUSD 76.6%, USDZAR 75.3%.

**BIGGEST STRATEGIC FINDING:** In practice the live system is rule/EA-strategy-driven, NOT ML-driven — XGBoost unscored + only 4 orders, Colab 0 orders. The pretrained models are not currently influencing execution; the gate routes around them. Worth weighing against ongoing investment in the 4-model-per-symbol / Dukascopy pretraining path.

**Data-quality flags:** sim `profit_usd`/`profit_pips` are unit-inconsistent across asset classes (forex pips vs index points vs crypto $) — unusable in aggregate (sum profit_usd = -$359M artifact); win/loss SIGN only. `mfe_pips`/`mae_pips` broken for crypto/indices (e.g. BTCUSD 12.97M). ~10 malformed sim rows; ~1 malformed EA row.

**Open follow-ups:** (1) export MT5 deal history for real P&L [approval needed — MQL5 HistorySelect script or Python MetaTrader5 pull]; (2) fix XGBoost outcome-scoring coverage so it can be evaluated; (3) investigate EA-stopped-06-09 and why Colab never executes; (4) review USDJPY underperformance.

### 2026-06-14 — Pretraining halt state, Dukascopy data integrity, and per-model training independence — all verified (Chat, read-only)

**Context:** Andy asked Chat to confirm (a) how far Dukascopy pretraining got before he killed it, (b) that simulated signal/execution files were stored, (c) that the downloaded data is not stale/frozen (the prior large-pull failure mode), and (d) that each model is trained as its own independent signal source (not on another model's data). All checks read-only via Windows-MCP.

**Pretraining progress (PID 10300, `pretrain_dukascopy`, killed by Andy ~2026-06-13 17:57):**
- Pipeline stages download -> features -> labels+splits: COMPLETE for all 43 instruments.
- Model training halted mid-run (alphabetical):
  - 20 symbols fully trained (XGB+LGBM+CatBoost+Transformer): AUDCAD, AUDCHF, AUDJPY, AUDNZD, AUDUSD, BTCUSD, CADCHF, CADJPY, CHFJPY, EURAUD, EURCAD, EURCHF, EURCZK, EURGBP, EURHUF, EURNOK, EURNZD, EURPLN, EURSEK, EURUSD.
  - GBPAUD = PARTIAL: XGB+LGBM+CatBoost saved, transformer MISSING (killed during its transformer step).
  - 22 symbols not reached. Of these, 5 majors retain prior usable models (GBPUSD, NZDUSD, USDCAD, USDCHF, USDJPY); 17 have data ready but ZERO models: NZDCAD, NZDCHF, US100, US30, US500, USDCNH, USDCZK, USDHUF, USDMXN, USDNOK, USDPLN, USDSEK, USDSGD, USDZAR, USOIL, XAGUSD, XAUUSD.
  - Never-regress guard kept original XGB on AUDUSD/EURGBP/EURUSD (new model did not beat val-acc) — expected, not a bug.

**Sim signal/execution storage: intact.**
- `data/unified_trades.csv` — 9,949 rows, clean 33-col schema (signal + execution/outcome co-stored per record), last write 2026-06-11 17:14 = clean stop at the pause.
- Runtime dirs: feature_history 42, feature_sequences 5,379, tick_trajectories 8,973, logs/predictions 5.
- `data/features/` and `data/execution_log/` empty — expected (live scratch buffers; empty while paused, not lost).

**Dukascopy data integrity (frozen-data check): clean.**
- Read-only scan of all 43 raw `*_M15_dukascopy.csv`: coverage 2023-06-12 -> 2026-06-11, 0 duplicate timestamps, zero-return <=3.1%, longest frozen runs <=7 bars (normal off-hours). No stale/frozen chunk.
- Minor: EURCZK has one ~19-bar flat run (~0.03% of bars, negligible); EURHUF has short history (46,606 bars vs ~74,500). Neither is frozen-corruption.
- `extract_features_all.validate_data()` already gates frozen data (excludes near-zero variance or >=4 consecutive months identical max/min); all 43 passed -> independent corroboration.

**Per-model independence: verified against code.**
- Per-symbol isolation: `retrain_symbol(symbol, df)` trains on ONE symbol's splits only; pretrainer/daily-retrainer never concatenate symbols.
- Labels: forward 24-candle / 20-pip price-action (`label_dukascopy_all.label_symbol`), from the symbol's own future close only — NEVER from any signal source's trade outcomes. (`_pip_value` import from trade_outcome_simulator is a pip-size constant, not a sim output.)
- Features: the 27 in `feature_history_recorder.FEATURE_27` are all pure technical/price-derived; sentiment trio = candle-position geometry (`extract_features_all.calc_sentiment`: (close-low)/(high-low) etc.). No model prediction is a feature; no stacking.
- The 4 model types per symbol share the SAME features+labels and diversify by ARCHITECTURE, not by data — satisfies "not trained on another model's data" (no leakage).

**Resolved (Andy, 2026-06-14):** intent is the no-leakage sense - the four model types per symbol SHOULD share identical features+labels and diversify by ARCHITECTURE alone; current design is correct as-is, no change needed. (NOT the distinct-dataset / per-model-partition interpretation.)

**Supersedes** the 2026-06-13 "Still open: PID 10300 pretrain still running" TODO — Andy has now killed it.

### 2026-06-13 — Chat gets direct VPS file access (Windows-MCP); DC retired for chat; instructions + memory overhauled

**DC root cause:** Desktop Commander never appears in Claude *chat* because it's a
Claude Desktop *Extension* whose host is disconnected — NOT a claude_desktop_config.json
MCP server (that config only holds memory-handoff-protocol). It works in Claude Code,
not in this Desktop chat.

**Key finding:** This Desktop chat already has Windows-MCP (FileSystem + PowerShell) and
memory-handoff-protocol loaded. Chat read this handoff directly via Windows-MCP FileSystem
— Chat now has the same direct disk read/write as Code, without DC. The §5 note "Chat has
no direct filesystem/repo access" is obsolete (flagged; not yet edited).

**Decisions:**
- Adopt Windows-MCP as Chat's file hand; don't chase a DC fix for chat (DC restorable later
  via Desktop → Settings → Extensions for parity only).
- Project instructions rewritten: startup reads this file via Windows-MCP (not DC); DC marked
  disconnected; added per-model LABEL-ENCODING verification gate (each network has its own
  order; mismatch fails silently / wastes hours — verify against the model's own code and
  confirm before training); added fetch-trade-params-from-config (no hardcoding/memorizing);
  added don't-auto-fix-intentionally-managed-issues; added MEMORY section ranking memory
  edits LOWEST and routing continuity to this Decisions Log; reframed 24-model ensemble +
  LITE/CLEAN27 from "DEAD/IGNORE" to SHELVED (revival planned) — preserve, don't delete.
- Claude memory edits cut 6 → 2 (removed all LITE-era items incl. a now-wrong "MHP is source
  of truth / call it first"): (1) FTMO_System active, old systems shelved-not-dead; (2) don't
  store volatile specifics in memory (params/run-state/tasks/filenames live in config/code/log).

**Project Knowledge audit (label-order hunt, approved):** No dangerous inverted 0=HOLD,1=BUY,
2=SELL claim anywhere in PK; all label refs use SELL/HOLD/BUY (0=SELL,1=HOLD,2=BUY) matching
code. Revival-pass only: v11.4 Neural Networks doc lists actions two ways in one file (loop
vs index order). Plan = label, don't delete: keep all 27 PK docs, add a "START HERE" index
(FTMO current/truth-on-disk; rest = shelved/paused systems + research). SYSTEM_ARCHITECTURE_
OVERVIEW = 24-model (shelved) doc; its "current" wording is stale.

**Tooling note:** Windows-MCP FileSystem (read/write/copy) reliable this session; Windows-MCP
PowerShell timed out (~4 min, unresponsive) — shell access via Windows-MCP currently flaky;
prefer FileSystem, treat PowerShell as unreliable until confirmed.

**Still open:** START HERE index pending add to PK; §5 obsolete line pending edit; PID 10300
pretrain still running (prior TODO).

### 2026-06-11 — Trading/training paused; all four scheduled tasks disabled

**Why:** This machine is compute-limited and Andy needs it free for analysis,
planning, and potential local model training.

**Done (via Claude Chat + Desktop Commander):**
- Disabled all four Windows scheduled tasks (reversible — `/DISABLE`, not deleted):
  - `FTMO_Trading_System` (was: daily 07:30 launch + RestartOnFailure ×3) → **Disabled**
  - `FTMO_Health_Watchdog` (was: every 10 min; health checks + stale-log auto-restart of the trading task) → **Disabled**
  - `FTMO_Colab_Keepalive` (was: every 5 min) → **Disabled** (was already disabled; re-confirmed)
  - `FTMO_Daily_Retrainer` (was: Sunday 08:00, auto-pushes models to GitHub) → **Disabled**
- Process sweep: no `run_system` / `live_trading_system` / `health_watchdog` /
  `keepalive` / Colab Edge-automation processes were running. No trading loop active.

**Still running, intentionally NOT killed yet (Andy wants to look at other things first):**
- PID 10300 — `python -m training.pretrain_dukascopy` (Dukascopy pretraining). **TODO: stop on Andy's go.**

**Left untouched (infrastructure, not trading/training):**
- MHP MCP server (`MemoryHandoffProtocol/core/mcp_server.py`, PIDs 780 + 9688)
- Claude windows-mcp tooling processes.

**To resume later (re-enable tasks):**
```
schtasks /Change /TN "FTMO_Trading_System"  /ENABLE
schtasks /Change /TN "FTMO_Health_Watchdog" /ENABLE
schtasks /Change /TN "FTMO_Colab_Keepalive" /ENABLE   # only if Colab path is wanted again
schtasks /Change /TN "FTMO_Daily_Retrainer" /ENABLE
```
**Consequence while paused:** system is manual-start only — nothing auto-launches at
07:30, no watchdog restart on hang/crash, no weekly retrain, no Colab keepalive.

**Reference deliverable:** corrected end-to-end flowchart `system_flowchart_v2.html`
(source-verified rebuild of `system_flowchart.html`, produced 2026-06-11) — supersedes
the 2026-06-09 baseline; key correction = two execution paths (only XGBoost is gated;
the 15 strategy sources + 3 Colab models are ungated).
