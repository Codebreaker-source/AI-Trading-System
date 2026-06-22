# Handoff/Context Doc Update Spec — 2026-06-14 (rev. 2)

**For: Claude Code.** Apply the edits below to the named files on disk. This is a
**docs-only** update — no code, config, process, or trading-state changes.

> rev.2 note: `system_flowchart_v2.html` has since been restored to
> `docs\system_flowchart_v2.html` (2026-06-11 content, saved 2026-06-14). EDIT 5,
> EDIT 9, EDIT 10, and q14 reflect that it now EXISTS and is the verified reference.

## Pre-flight
1. Back up `docs\CLAUDE_CHAT_HANDOFF.md` -> `docs\CLAUDE_CHAT_HANDOFF.backup-2026-06-14.md`.
2. All edits are non-destructive find/replace or insert. Preserve everything not named.
3. Do NOT touch `## 8. Decisions Log` — its two 2026-06-14 entries already exist and
   are correct. These edits only update sections 0–7.
4. Keep UTF-8 (em-dashes —, arrows ->, box-drawing chars must survive; no BOM).
5. After applying: verify §8 still has 4 entries newest-first (2026-06-14 trade
   analysis, 2026-06-14 pretraining, 2026-06-13, 2026-06-11), and that em-dashes/tree
   chars render (no mojibake).
6. Confirm `docs\system_flowchart_v2.html` exists (restored 2026-06-14). No search needed.

---

## FILE 1: docs\CLAUDE_CHAT_HANDOFF.md

### EDIT 1 — header "Last verified" date
FIND:
```
directly. Last verified: 2026-06-11.
```
REPLACE:
```
directly. Last verified: 2026-06-14 (Chat, via Windows-MCP — pretraining +
Dukascopy data-integrity + per-model-independence verification, and a
simulated-vs-actual trade analysis; see the two 2026-06-14 entries in §8).
```

### EDIT 2 — §3 inventory: feature_sequences / tick_trajectories counts
FIND:
```
│   ├── feature_sequences/           # 4,355 files — sequence data (likely for transformer/Colab)
│   ├── tick_trajectories/           # 8,103 files — tick-level data post-signal
```
REPLACE:
```
│   ├── feature_sequences/           # 5,379 files (as of 2026-06-14) — sequence data (transformer/Colab)
│   ├── tick_trajectories/           # 8,973 files (as of 2026-06-14) — tick-level data post-signal
```

### EDIT 3 — §3 inventory: models block
FIND:
```
│   └── models/                    # 9 *.joblib XGBoost models:
│       AUDCAD, AUDUSD, EURGBP, EURUSD, GBPUSD, NZDUSD, USDCAD, USDCHF, USDJPY
│       (Note: AUDCAD is NEW — not one of the original 8 pretrained pairs.
│        Either retraining already produced it, or it was added manually.)
```
REPLACE:
```
│   └── models/                    # 26 *.joblib XGBoost models (as of 2026-06-14):
│       original 8 majors + 18 from the HALTED Dukascopy pretrain run
│       (alphabetical AUDCAD..GBPAUD). 17 instruments have data prepped but
│       NO model yet: NZDCAD, NZDCHF, US100, US30, US500, USDCNH, USDCZK,
│       USDHUF, USDMXN, USDNOK, USDPLN, USDSEK, USDSGD, USDZAR, USOIL,
│       XAGUSD, XAUUSD. (AUDCAD origin RESOLVED: Dukascopy pretraining.)
│       NOTE: LightGBM/CatBoost/Transformer models do NOT live here — they are
│       written to C:\Users\mt5-admin\Documents\GitHub\AI-Trading-System\
│       models\current (+ transformer\ subdir) by the same pretrainer.
```

### EDIT 4 — §3 inventory: unified_trades.csv pointer/gotcha
FIND:
```
│   ├── unified_trades.csv         # Master trade log (root of data/)
```
REPLACE:
```
│   ├── unified_trades.csv         # Master PYTHON SIM trade log (root of data/). NOTE:
│   │                               #   every row has actually_executed=True, but that means
│   │                               #   "sim decided to execute", NOT a broker fill. Only ~536
│   │                               #   of ~9,948 rows became real MT5 orders. P&L columns
│   │                               #   (profit_pips/profit_usd) are unit-inconsistent across
│   │                               #   asset classes — use win/loss SIGN only, not aggregates.
```

### EDIT 5 — §3 docs subtree: point to v2 as the verified reference
FIND:
```
    ├── system_flowchart.html       # 2026-06-09, existing detailed flowchart — START HERE
```
REPLACE:
```
    ├── system_flowchart_v2.html    # 2026-06-11 content, saved to disk 2026-06-14 —
    │                                #   VERIFIED architectural reference (START HERE).
    ├── system_flowchart.html       # 2026-06-09 baseline flowchart (superseded by v2)
```

### EDIT 6 — §4 architecture facts: replace the last two bullets + add four new
FIND:
```
- **`data/feature_sequences/` (4,355 files) and `data/tick_trajectories/` (8,103
  files)** show substantial accumulated runtime data already — this system has
  been running in sim mode for a while, not freshly started.
- **`data/models/` has 9 models including AUDCAD** (not one of the original 8
  pretrained pairs) — worth confirming with Andy whether this came from
  retraining/auto-creation or was added manually.
```
REPLACE:
```
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
```

### EDIT 7 — §6 open questions: mark #3 resolved, then append q7–q14
FIND:
```
3. `data/models/AUDCAD_xgboost.joblib` — where did this come from?
```
REPLACE:
```
3. `data/models/AUDCAD_xgboost.joblib` — where did this come from?
   **(RESOLVED 2026-06-14: produced by the Dukascopy pretraining run.)**
```

FIND:
```
6. Should `colab/edge_profile/` be added to `.gitignore` (see §7)? It's not
   currently excluded and contains live Google session data.
```
REPLACE:
```
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
```

### EDIT 8 — append an MT5 runtime map at the END of §7 (before the `---` that precedes `## 8`)
FIND:
```
with placeholder/empty account fields. `colab/edge_profile/` contains a *live*
Google session and is **not yet gitignored** — see open question #6.
```
REPLACE:
```
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
```

### EDIT 9 — §2 prose: redirect "START HERE" to v2
FIND:
```
**Claude Chat should treat this as the baseline and produce an updated/expanded
version**, not start from scratch — it likely already encodes a lot of the
"how it actually works" detail Chat would otherwise have to guess.
```
REPLACE:
```
**UPDATE 2026-06-14:** the updated/expanded version now exists as
`docs/system_flowchart_v2.html` (verified rebuild, 2026-06-11 content) — treat
**v2 as the current verified reference / START HERE**. The text below describes
the superseded 2026-06-09 `system_flowchart.html` baseline, kept for history.
```

### EDIT 10 — §5 source-of-truth ranking: bump to v2
FIND:
```
3. **Source of truth ranking** when docs disagree: (1) actual code in
   `FTMO_System/`, (2) `system_flowchart.html` (2026-06-09), (3)
   `FTMO_SYSTEM_HANDOFF.md` (2026-06-01), (4) `claude.md` original spec (oldest,
   most superseded).
```
REPLACE:
```
3. **Source of truth ranking** when docs disagree: (1) actual code in
   `FTMO_System/`, (2) `system_flowchart_v2.html` (verified 2026-06-11, saved
   2026-06-14; the older `system_flowchart.html` 2026-06-09 is superseded),
   (3) `FTMO_SYSTEM_HANDOFF.md` (2026-06-01), (4) `claude.md` original spec
   (oldest, most superseded).
```

---

## FILE 2: docs\FTMO_SYSTEM_HANDOFF.md
INSERT at the very top of the file (before the current first line):
```
> ⚠️ As of 2026-06-14, this file is SUPERSEDED by `CLAUDE_CHAT_HANDOFF.md` for
> current state. Retained for history. Where they disagree, CLAUDE_CHAT_HANDOFF.md
> and on-disk code win.

```

## FILE 3: docs\KEY_FILES_FOR_CHAT.md
INSERT at the very top of the file (before the current first line):
```
> ⚠️ As of 2026-06-14, superseded by the full source bundles in
> `docs/full_source_bundles/` and by `CLAUDE_CHAT_HANDOFF.md` for current state.
> Retained for reference.

```

---

## Explicitly OUT of scope (do NOT do without Andy)
- §5 legacy "paste files into Chat" mechanics — obsolete now Chat reads directly,
  but it's a process-wording judgment call. Leave unless Andy says otherwise.
- Project Instructions (the system-level block) — Andy edits those himself
  (they still reference v2 + a "START HERE" index; now consistent since v2 exists).
- No code/config/process/trading-state changes anywhere.

## Report back to Andy after applying
- Confirmation each FILE 1 edit matched its anchor exactly (flag any that didn't).
- Confirmation `docs\system_flowchart_v2.html` is present (restored 2026-06-14).
