# Source Bundle: docs/full_source_bundles/08_training.md


---

## `training/daily_retrainer.py`

```py
"""
Daily retraining — all 4 model types, PER SYMBOL, price-action labels.
Run once per day (Task Scheduler, 00:00 UTC).

Reads data/training_sets/{SYMBOL}_tabular.parquet (produced by
training/build_training_sets.py from PRICE ACTION in
data/feature_history/{SYMBOL}.csv — forward 24-candle / 20-pip labeling,
identical methodology to the original 8 pretrained models). Labels are
never derived from any signal source's trade outcomes.

For each symbol with >= MIN_TRADES rows:
  1. Use the 27 raw features + label/weight from build_training_sets.py
  2. Retrain XGBoost, LightGBM, CatBoost, SimpleTransformer — each
     INDEPENDENTLY on the SAME per-symbol price-action label set.
     Diversification comes from differing model architectures, not
     differing label sources.
  3. Only replace a model if new val_acc >= existing val_acc
  4. After all symbols: git commit + push updated models to GitHub
     so Colab picks them up on next session start.

Model save paths (flat, matching the original 8 pretrained models)
--------------------------------------------------------------------
  XGBoost     → FTMO_System/data/models/{SYM}_xgboost.joblib       (local)
  LightGBM    → GITHUB_MODELS_DIR/{SYM}_lightgbm.joblib
  CatBoost    → GITHUB_MODELS_DIR/{SYM}_catboost.joblib
  Transformer → GITHUB_MODELS_DIR/transformer/{SYM}_transformer.pth

Rule-based strategies are never retrained and never contribute data here.
"""

from __future__ import annotations

import logging
import json
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.feature_history_recorder import FEATURE_27  # noqa: E402

logger = logging.getLogger(__name__)

# ── Default GitHub models directory ──────────────────────────────────────
# Override via config["paths"]["github_models_dir"]
_DEFAULT_GITHUB_MODELS = (
    r"C:\Users\mt5-admin\Documents\GitHub\AI-Trading-System\models\current"
)


# ══════════════════════════════════════════════════════════════════════════
# Data helpers
# ══════════════════════════════════════════════════════════════════════════

def load_training_sets(training_sets_dir: Path) -> dict[str, pd.DataFrame]:
    """
    Load every data/training_sets/{symbol}_tabular.parquet.
    Returns {symbol: DataFrame}.
    """
    result = {}
    if not training_sets_dir.exists():
        logger.warning(f"Training sets dir not found: {training_sets_dir}")
        return result

    for parquet_path in training_sets_dir.glob("*_tabular.parquet"):
        symbol = parquet_path.stem[: -len("_tabular")]
        try:
            df = pd.read_parquet(parquet_path)
        except Exception as e:
            logger.error(f"Failed to read {parquet_path}: {e}")
            continue
        if not df.empty:
            result[symbol] = df

    return result


def extract_feature_matrix(df: pd.DataFrame) -> np.ndarray | None:
    """Return (N, 27) float32 matrix from the feat_* columns written by build_training_sets.py."""
    cols = [f"feat_{f}" for f in FEATURE_27]
    missing = [c for c in cols if c not in df.columns]
    if missing:
        logger.warning(f"Feature columns missing: {missing[:5]}...")
        return None
    return df[cols].values.astype(np.float32)


# ══════════════════════════════════════════════════════════════════════════
# Model trainers
# ══════════════════════════════════════════════════════════════════════════

def _split(X, y, w, holdout_pct):
    """Stratified train/val split, propagating sample weights."""
    return train_test_split(X, y, w, test_size=holdout_pct,
                            random_state=42, stratify=y)


def _val_acc_of_saved(model_path: str, X, y, holdout_pct: float,
                      model_type: str = "sklearn") -> float:
    """Evaluate an existing saved model on the same holdout split. Returns -1 if absent."""
    if not os.path.exists(model_path):
        return -1.0
    try:
        _, X_val, _, y_val, _, _ = _split(X, y, np.ones(len(y)), holdout_pct)
        if model_type == "sklearn":
            m = joblib.load(model_path)
            return accuracy_score(y_val, m.predict(X_val))
        if model_type == "transformer":
            import torch
            import torch.nn as nn

            class _T(nn.Module):
                def __init__(self):
                    super().__init__()
                    self.embedding  = nn.Linear(len(FEATURE_27), 64)
                    enc = nn.TransformerEncoderLayer(d_model=64, nhead=4,
                                                     dim_feedforward=128,
                                                     dropout=0.1, batch_first=True)
                    self.transformer = nn.TransformerEncoder(enc, num_layers=2)
                    self.classifier  = nn.Linear(64, 3)
                    self.dropout     = nn.Dropout(0.1)
                def forward(self, x):
                    x = x.unsqueeze(1)
                    x = self.embedding(x)
                    x = self.transformer(x)
                    x = x.squeeze(1)
                    x = self.dropout(x)
                    return self.classifier(x)

            device = torch.device("cpu")
            m = _T().to(device)
            state = torch.load(model_path, map_location=device)
            if isinstance(state, dict) and "model_state_dict" in state:
                state = state["model_state_dict"]
            m.load_state_dict(state)
            m.eval()
            tx = torch.tensor(X_val, dtype=torch.float32).to(device)
            with torch.no_grad():
                preds = m(tx).argmax(dim=1).cpu().numpy()
            return accuracy_score(y_val, preds)
    except Exception as e:
        logger.warning(f"Could not evaluate existing model {model_path}: {e}")
    return -1.0


# ── XGBoost ───────────────────────────────────────────────────────────────

def train_xgboost(X, y, w, holdout_pct=0.2):
    """Returns (model, train_acc, val_acc) or (None, 0, 0)."""
    from xgboost import XGBClassifier
    if len(np.unique(y)) < 2:
        logger.warning("XGB: only one class — skipping")
        return None, 0.0, 0.0
    X_tr, X_val, y_tr, y_val, w_tr, _ = _split(X, y, w, holdout_pct)
    m = XGBClassifier(n_estimators=200, max_depth=4, learning_rate=0.05,
                      subsample=0.8, colsample_bytree=0.8,
                      use_label_encoder=False, eval_metric="mlogloss",
                      num_class=3, objective="multi:softprob",
                      random_state=42, n_jobs=-1)
    m.fit(X_tr, y_tr, sample_weight=w_tr,
          eval_set=[(X_val, y_val)], verbose=False)
    return m, accuracy_score(y_tr, m.predict(X_tr)), accuracy_score(y_val, m.predict(X_val))


# ── LightGBM ──────────────────────────────────────────────────────────────

def train_lightgbm(X, y, w, holdout_pct=0.2):
    """Returns (model, train_acc, val_acc) or (None, 0, 0)."""
    try:
        from lightgbm import LGBMClassifier
    except ImportError:
        logger.warning("LightGBM not installed — skipping")
        return None, 0.0, 0.0
    if len(np.unique(y)) < 2:
        logger.warning("LGB: only one class — skipping")
        return None, 0.0, 0.0
    X_tr, X_val, y_tr, y_val, w_tr, _ = _split(X, y, w, holdout_pct)
    m = LGBMClassifier(n_estimators=200, max_depth=4, learning_rate=0.05,
                       subsample=0.8, colsample_bytree=0.8,
                       num_class=3, objective="multiclass",
                       class_weight="balanced",
                       random_state=42, n_jobs=-1, verbose=-1)
    m.fit(X_tr, y_tr, sample_weight=w_tr)
    return m, accuracy_score(y_tr, m.predict(X_tr)), accuracy_score(y_val, m.predict(X_val))


# ── CatBoost ──────────────────────────────────────────────────────────────

def train_catboost(X, y, w, holdout_pct=0.2):
    """Returns (model, train_acc, val_acc) or (None, 0, 0)."""
    try:
        from catboost import CatBoostClassifier
    except ImportError:
        logger.warning("CatBoost not installed — skipping")
        return None, 0.0, 0.0
    if len(np.unique(y)) < 2:
        logger.warning("CAT: only one class — skipping")
        return None, 0.0, 0.0
    X_tr, X_val, y_tr, y_val, w_tr, _ = _split(X, y, w, holdout_pct)
    m = CatBoostClassifier(iterations=200, depth=4, learning_rate=0.05,
                           loss_function="MultiClass",
                           random_seed=42, verbose=0)
    m.fit(X_tr, y_tr, sample_weight=w_tr)
    return m, accuracy_score(y_tr, m.predict(X_tr).flatten()), \
              accuracy_score(y_val, m.predict(X_val).flatten())


# ── SimpleTransformer ─────────────────────────────────────────────────────

class SimpleTransformer:
    """Thin wrapper around the PyTorch SimpleTransformer for train/eval."""

    def __init__(self, input_dim=len(FEATURE_27), d_model=64, nhead=4,
                 num_layers=2, num_classes=3, dropout=0.1):
        import torch.nn as nn
        from torch.nn import TransformerEncoderLayer, TransformerEncoder

        class _Net(nn.Module):
            def __init__(self):
                super().__init__()
                self.embedding  = nn.Linear(input_dim, d_model)
                enc = TransformerEncoderLayer(d_model=d_model, nhead=nhead,
                                              dim_feedforward=128,
                                              dropout=dropout, batch_first=True)
                self.transformer = TransformerEncoder(enc, num_layers=num_layers)
                self.classifier  = nn.Linear(d_model, num_classes)
                self.dropout     = nn.Dropout(dropout)

            def forward(self, x):
                x = x.unsqueeze(1)
                x = self.embedding(x)
                x = self.transformer(x)
                x = x.squeeze(1)
                x = self.dropout(x)
                return self.classifier(x)

        self._net_cls = _Net

    def fit(self, X, y, w, epochs=50, batch_size=32, lr=1e-3):
        import torch
        import torch.nn as nn
        from torch.utils.data import TensorDataset, DataLoader

        device = torch.device("cpu")
        net    = self._net_cls().to(device)
        opt    = torch.optim.Adam(net.parameters(), lr=lr)
        crit   = nn.CrossEntropyLoss(reduction="none")

        Xt = torch.tensor(X, dtype=torch.float32)
        yt = torch.tensor(y, dtype=torch.long)
        wt = torch.tensor(w, dtype=torch.float32)
        ds = TensorDataset(Xt, yt, wt)
        dl = DataLoader(ds, batch_size=batch_size, shuffle=True)

        net.train()
        for _ in range(epochs):
            for xb, yb, wb in dl:
                xb, yb, wb = xb.to(device), yb.to(device), wb.to(device)
                opt.zero_grad()
                loss = (crit(net(xb), yb) * wb).mean()
                loss.backward()
                opt.step()

        self._net    = net
        self._device = device
        return self

    def predict(self, X):
        import torch
        self._net.eval()
        with torch.no_grad():
            x = torch.tensor(X, dtype=torch.float32).to(self._device)
            return self._net(x).argmax(dim=1).cpu().numpy()

    def state_dict(self):
        return self._net.state_dict()


def train_transformer(X, y, w, holdout_pct=0.2):
    """Returns (model_wrapper, train_acc, val_acc) or (None, 0, 0)."""
    try:
        import torch  # noqa: F401
    except ImportError:
        logger.warning("PyTorch not installed — skipping Transformer")
        return None, 0.0, 0.0
    if len(np.unique(y)) < 2:
        logger.warning("TRF: only one class — skipping")
        return None, 0.0, 0.0
    X_tr, X_val, y_tr, y_val, w_tr, _ = _split(X, y, w, holdout_pct)
    m = SimpleTransformer().fit(X_tr, y_tr, w_tr)
    return m, accuracy_score(y_tr, m.predict(X_tr)), accuracy_score(y_val, m.predict(X_val))


# ══════════════════════════════════════════════════════════════════════════
# Per-symbol retraining
# ══════════════════════════════════════════════════════════════════════════

def retrain_symbol(symbol: str, df: pd.DataFrame,
                   local_model_dir: str, github_models_dir: str,
                   min_trades: int = 50, holdout_pct: float = 0.2) -> dict:

    result = {"symbol": symbol, "updated": [], "kept": [], "skipped": [], "errors": []}

    if len(df) < min_trades:
        logger.info(f"{symbol}: {len(df)} rows < {min_trades} minimum — skipping all")
        result["skipped"] = ["xgboost", "lightgbm", "catboost", "transformer"]
        return result

    X = extract_feature_matrix(df)
    if X is None:
        result["errors"].append("no_features")
        return result

    y = df["label"].values.astype(int)
    w = df["weight"].values.astype(float)

    valid = ~np.isnan(X).any(axis=1)
    X, y, w = X[valid], y[valid], w[valid]

    if len(X) < min_trades:
        logger.info(f"{symbol}: after NaN drop {len(X)} usable rows < {min_trades} — skipping all")
        result["skipped"] = ["xgboost", "lightgbm", "catboost", "transformer"]
        return result

    dist = Counter(y.tolist())
    logger.info(
        f"{symbol}: n={len(X)}  SELL={dist.get(0,0)} HOLD={dist.get(1,0)} "
        f"BUY={dist.get(2,0)}  mean_w={w.mean():.3f}"
    )

    gh_trf_dir = os.path.join(github_models_dir, "transformer")
    os.makedirs(local_model_dir, exist_ok=True)
    os.makedirs(github_models_dir, exist_ok=True)
    os.makedirs(gh_trf_dir, exist_ok=True)

    # Clean symbol name for filename (strip broker suffixes)
    sym_clean = symbol
    for sfx in (".sim", ".i", "_SB", ".r", ".a", ".b", ".m", ".pro"):
        if sym_clean.endswith(sfx):
            sym_clean = sym_clean[:-len(sfx)]
            break

    tasks = [
        ("xgboost",     train_xgboost,     os.path.join(local_model_dir,   f"{sym_clean}_xgboost.joblib"),   "sklearn"),
        ("lightgbm",    train_lightgbm,    os.path.join(github_models_dir, f"{sym_clean}_lightgbm.joblib"),  "sklearn"),
        ("catboost",    train_catboost,    os.path.join(github_models_dir, f"{sym_clean}_catboost.joblib"),  "sklearn"),
        ("transformer", train_transformer, os.path.join(gh_trf_dir,        f"{sym_clean}_transformer.pth"),  "transformer"),
    ]

    for name, trainer, model_path, mtype in tasks:
        try:
            existing_acc = _val_acc_of_saved(model_path, X, y, holdout_pct, mtype)
            new_model, tr_acc, val_acc = trainer(X, y, w, holdout_pct)

            if new_model is None:
                result["skipped"].append(name)
                continue

            if val_acc >= existing_acc:
                if name == "transformer":
                    import torch
                    torch.save(new_model.state_dict(), model_path)
                else:
                    joblib.dump(new_model, model_path)
                result["updated"].append(name)
                logger.info(
                    f"{symbol} [{name}] updated — val={val_acc:.3f} "
                    f"(was {existing_acc:.3f})  train={tr_acc:.3f}"
                )
            else:
                result["kept"].append(name)
                logger.info(
                    f"{symbol} [{name}] kept existing — new={val_acc:.3f} < old={existing_acc:.3f}"
                )

        except Exception as e:
            logger.error(f"{symbol} [{name}] crashed: {e}", exc_info=True)
            result["errors"].append(f"{name}: {e}")

    return result


# ══════════════════════════════════════════════════════════════════════════
# GitHub push
# ══════════════════════════════════════════════════════════════════════════

def push_models_to_github(github_models_dir: str, symbols_updated: list[str]) -> bool:
    """
    git add + commit + push the retrained model files.
    Only runs if at least one model was actually updated.
    Returns True on success.
    """
    if not symbols_updated:
        logger.info("No models updated — skipping GitHub push")
        return True

    repo_root = str(Path(github_models_dir).parent.parent)  # …/AI-Trading-System
    ts        = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    try:
        subprocess.run(
            ["git", "add", "models/"],
            cwd=repo_root, check=True, capture_output=True
        )
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=repo_root, capture_output=True
        )
        if result.returncode == 0:
            logger.info("GitHub: nothing new to commit after git add")
            return True

        msg = (
            f"Daily retrain {ts}: updated {len(symbols_updated)} symbol(s)\n\n"
            + "\n".join(f"  - {s}" for s in symbols_updated)
            + "\n\nCo-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
        )
        subprocess.run(
            ["git", "commit", "-m", msg],
            cwd=repo_root, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=repo_root, check=True, capture_output=True
        )
        logger.info(f"GitHub push complete — {len(symbols_updated)} symbol(s) committed")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"GitHub push failed: {e.stderr.decode()}")
        return False


# ══════════════════════════════════════════════════════════════════════════
# Main entry point
# ══════════════════════════════════════════════════════════════════════════

def run_daily_retraining(config: dict | None = None) -> list[dict]:
    config       = config or {}
    trading_cfg  = config.get("trading", {})
    retrain_cfg  = config.get("retraining", {})
    ml_cfg       = config.get("ml", {})
    paths_cfg    = config.get("paths", {})

    training_sets_dir = BASE_DIR / "data" / "training_sets"
    local_model_dir    = str(BASE_DIR / ml_cfg.get("model_dir", "data/models"))
    github_models_dir  = paths_cfg.get("github_models_dir", _DEFAULT_GITHUB_MODELS)
    min_trades         = trading_cfg.get("min_trades_for_retrain", 50)
    holdout_pct        = retrain_cfg.get("holdout_pct", 0.2)

    logger.info(f"=== Daily Retraining started {datetime.now(timezone.utc).isoformat()} ===")
    logger.info(f"Training sets : {training_sets_dir}")
    logger.info(f"Local models  : {local_model_dir}")
    logger.info(f"GitHub models : {github_models_dir}")

    # Build/refresh per-symbol price-action training sets from feature_history
    try:
        from training.build_training_sets import build_training_sets
        build_summary = build_training_sets()
        logger.info(f"Training sets built: {len(build_summary)} symbol(s)")
    except Exception as e:
        logger.error(f"build_training_sets failed: {e}", exc_info=True)

    training_sets = load_training_sets(training_sets_dir)
    if not training_sets:
        logger.info("No training sets available — retraining skipped")
        return []

    results          = []
    symbols_updated  = []

    for symbol, group in training_sets.items():
        try:
            r = retrain_symbol(symbol, group, local_model_dir,
                               github_models_dir, min_trades, holdout_pct)
            results.append(r)
            if r["updated"]:
                symbols_updated.append(f"{symbol} ({', '.join(r['updated'])})")
        except Exception as e:
            logger.error(f"{symbol}: retraining crashed — {e}", exc_info=True)
            results.append({"symbol": symbol, "errors": [str(e)]})

    # Summary
    total_updated = sum(len(r.get("updated", [])) for r in results)
    total_kept    = sum(len(r.get("kept",    [])) for r in results)
    total_skipped = sum(len(r.get("skipped", [])) for r in results)
    logger.info(
        f"=== Retraining complete: {total_updated} updated | "
        f"{total_kept} kept | {total_skipped} skipped ==="
    )

    # Push updated models to GitHub so Colab gets them
    push_models_to_github(github_models_dir, symbols_updated)

    return results


if __name__ == "__main__":
    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "retrainer.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    cfg_path = BASE_DIR / "config" / "ftmo_config.json"
    config   = {}
    if cfg_path.exists():
        with open(cfg_path) as f:
            config = json.load(f)
    run_daily_retraining(config)

```

---

## `training/data_labeler.py`

```py
"""
Profit-aware 3-tier trade labeling for ML training.

Outcome values written by BridgeEA_FTMO_v1 (from DEAL_REASON):
  "TP"    — actual take-profit order hit               → correct direction, full weight
  "TRAIL" — trailing stop closed while in profit       → correct direction, half weight
  "SL"    — stop loss closed at a loss                 → wrong direction,  full weight
  "HOLD"  — no trade taken / filtered out              → HOLD label,       full weight

Label encoding (MUST match all pretrained models):
  0 = SELL
  1 = HOLD
  2 = BUY

Backward compatibility:
  Legacy logs only have "TP" and "SL" (no "TRAIL").  The function handles this
  gracefully — "TP" still maps to full-weight directional, "SL" still maps to
  opposite-direction full-weight.
"""

from __future__ import annotations

LABEL_SELL = 0
LABEL_HOLD = 1
LABEL_BUY  = 2


def label_trade(direction: str, outcome: str) -> tuple[int, float]:
    """
    Convert one execution-log row into a (label, sample_weight) pair.

    Parameters
    ----------
    direction : str   "BUY" or "SELL"
    outcome   : str   "TP", "TRAIL", "SL", or anything else (→ HOLD)

    Returns
    -------
    (label: int, weight: float)
        label  ∈ {LABEL_SELL=0, LABEL_HOLD=1, LABEL_BUY=2}
        weight ∈ {0.5, 1.0}

    Labeling rules
    --------------
    Outcome  Direction  Label   Weight  Rationale
    -------- ---------- ------- ------- -----------------------------------------
    TP       BUY        BUY     1.0     Strong correct signal — reached target
    TP       SELL       SELL    1.0     Strong correct signal — reached target
    TRAIL    BUY        BUY     0.5     Correct direction but didn't reach target
    TRAIL    SELL       SELL    0.5     Correct direction but didn't reach target
    SL       BUY        SELL    1.0     Wrong direction — should have sold
    SL       SELL       BUY     1.0     Wrong direction — should have bought
    other    *          HOLD    1.0     No trade / unknown outcome
    """
    d = str(direction).upper().strip()
    o = str(outcome).upper().strip()

    if o == "TP":
        if d == "BUY":
            return LABEL_BUY,  1.0
        if d == "SELL":
            return LABEL_SELL, 1.0

    elif o == "TRAIL":
        # Correct direction — price moved our way — but trailing stop
        # fired before the full TP target was reached.  Treat as a
        # weaker confirmation of the direction.
        if d == "BUY":
            return LABEL_BUY,  0.5
        if d == "SELL":
            return LABEL_SELL, 0.5

    elif o == "SL":
        # Stopped out at a loss — the direction call was wrong.
        if d == "BUY":
            return LABEL_SELL, 1.0
        if d == "SELL":
            return LABEL_BUY,  1.0

    # HOLD / unrecognised outcome
    return LABEL_HOLD, 1.0


def label_dataframe(df, direction_col: str = "direction",
                    outcome_col: str = "outcome"):
    """
    Apply label_trade() to every row of a DataFrame.

    Returns two Series: (labels, weights) — both aligned with df.index.
    """
    import pandas as pd
    results = df.apply(
        lambda r: label_trade(r[direction_col], r[outcome_col]), axis=1
    )
    labels  = results.map(lambda t: t[0]).astype(int)
    weights = results.map(lambda t: t[1]).astype(float)
    return labels, weights

```

---

## `training/build_training_sets.py`

```py
"""
Per-Symbol Price-Action Training Set Builder
=============================================
Builds ML training data the SAME way the 8 original pretrained XGBoost
models were built (src/lite/training/data_labeler_CLEAN27.py):

  - Forward window = 24 rows (M15 candles -> 6 hours)
  - Label = BUY if forward max gain >= 20 pips (and max loss < 20 pips)
            SELL if forward max loss >= 20 pips (and max gain < 20 pips)
            HOLD otherwise
  - Row i is labeled using rows i+1 .. i+FORWARD_CANDLES (no lookahead
    into row i's own future close)

Labels are derived PURELY from price action in
data/feature_history/{SYMBOL}.csv (Phase 4 recorder) — never from any
signal source's trade outcomes. Every ML model type (XGBoost, LightGBM,
CatBoost, Transformer) trains on this SAME per-symbol label set
independently; diversification comes from differing model architectures,
not differing label sources. Rule-based strategies are not retrained and
never contribute to this data.

Output: data/training_sets/{SYMBOL}_tabular.parquet
  - feat_<name> columns (27 raw features, FEATURE_27 order)
  - label  (0=SELL, 1=HOLD, 2=BUY)
  - weight (always 1.0 — price-action labels have no execution-based weighting)
  - timestamp

Run on a schedule (daily, before retraining) or manually:
    python training/build_training_sets.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.feature_history_recorder import FEATURE_27  # noqa: E402
from core.trade_outcome_simulator import _pip_value  # noqa: E402

logger = logging.getLogger(__name__)

FEATURE_HISTORY_DIR = BASE_DIR / "data" / "feature_history"
TRAINING_SETS_DIR = BASE_DIR / "data" / "training_sets"

FORWARD_CANDLES = 24   # 6 hours on M15 — matches data_labeler_CLEAN27.py
PIP_THRESHOLD = 20     # 20 pips — matches data_labeler_CLEAN27.py

LABEL_SELL, LABEL_HOLD, LABEL_BUY = 0, 1, 2


def label_symbol(close_prices: np.ndarray, threshold: float) -> np.ndarray:
    """Forward-window pip-threshold labeling, identical to data_labeler_CLEAN27.label_pair()."""
    n = len(close_prices)
    labels = np.full(n, LABEL_HOLD, dtype=int)

    for i in range(n - FORWARD_CANDLES):
        current_price = close_prices[i]
        future_prices = close_prices[i + 1: i + 1 + FORWARD_CANDLES]

        max_gain = np.max(future_prices) - current_price
        max_loss = current_price - np.min(future_prices)

        if max_gain >= threshold and max_loss < threshold:
            labels[i] = LABEL_BUY
        elif max_loss >= threshold and max_gain < threshold:
            labels[i] = LABEL_SELL
        # else stays HOLD

    return labels


def _resample_to_m15(df: pd.DataFrame) -> pd.DataFrame:
    """
    feature_history rows are recorded every ~15s (one per main loop cycle),
    not per M15 candle. Resample to M15 bars (last snapshot in each 15-minute
    bucket) so FORWARD_CANDLES=24 actually represents 6 hours, matching the
    original data_labeler_CLEAN27.py methodology.
    """
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.set_index("timestamp").resample("15min").last().dropna().reset_index()
    return df


def build_training_sets(history_dir: Path = FEATURE_HISTORY_DIR,
                         min_rows: int = 50) -> dict:
    """Returns a summary dict: {symbol: n_rows}."""
    if not history_dir.exists():
        logger.warning(f"{history_dir} not found")
        return {}

    summary = {}

    for path in sorted(history_dir.glob("*.csv")):
        symbol = path.stem
        try:
            df = pd.read_csv(path)
        except Exception as e:
            logger.error(f"Failed to read {path}: {e}")
            continue

        if "close" not in df.columns:
            continue

        df = df.sort_values("timestamp").reset_index(drop=True)
        df = _resample_to_m15(df)

        if len(df) <= FORWARD_CANDLES:
            continue

        threshold = PIP_THRESHOLD * _pip_value(symbol)
        labels = label_symbol(df["close"].to_numpy(dtype=np.float64), threshold)

        # Drop the trailing rows that have no full forward window
        usable = df.iloc[: len(df) - FORWARD_CANDLES].copy()
        usable["label"] = labels[: len(usable)]

        if len(usable) < min_rows:
            continue

        feat_cols = {f"feat_{name}": usable[name].astype(np.float32) for name in FEATURE_27}
        out_df = pd.DataFrame(feat_cols)
        out_df["label"] = usable["label"].values.astype(int)
        out_df["weight"] = 1.0
        out_df["timestamp"] = usable["timestamp"].values

        TRAINING_SETS_DIR.mkdir(parents=True, exist_ok=True)
        out_path = TRAINING_SETS_DIR / f"{symbol}_tabular.parquet"
        out_df.to_parquet(out_path, index=False)
        summary[symbol] = len(out_df)

        dist = pd.Series(out_df["label"]).value_counts().sort_index()
        logger.info(
            f"[BUILD] {symbol}: {len(out_df)} rows -> {out_path}  "
            f"SELL={dist.get(0,0)} HOLD={dist.get(1,0)} BUY={dist.get(2,0)}"
        )

    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result = build_training_sets()
    total = sum(result.values())
    logger.info(f"=== Built {len(result)} symbol training set(s), {total} total rows ===")

```

---

## `training/download_dukascopy_all.py`

```py
"""
Dukascopy Historical Data Downloader — All FTMO Symbols
=========================================================
Downloads 3 years of M15 OHLCV data for every FTMO symbol that has a
matching Dukascopy instrument (forex majors/crosses, metals, indices,
crypto, energy). Free institutional-quality data from Dukascopy Bank SA.

Output: data/historical_data/{SYMBOL}_M15_dukascopy.csv
  columns: timestamp, symbol, open, high, low, close, tick_volume

Run: python training/download_dukascopy_all.py
"""

from __future__ import annotations

import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

import dukascopy_python
from dukascopy_python import instruments as I

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "data" / "historical_data"

# Symbol (FTMO name, suffix-stripped) -> Dukascopy instrument constant
SYMBOL_INSTRUMENTS = {
    # 8 majors (already pretrained, included for completeness/refresh)
    "EURUSD": I.INSTRUMENT_FX_MAJORS_EUR_USD,
    "GBPUSD": I.INSTRUMENT_FX_MAJORS_GBP_USD,
    "USDJPY": I.INSTRUMENT_FX_MAJORS_USD_JPY,
    "USDCHF": I.INSTRUMENT_FX_MAJORS_USD_CHF,
    "AUDUSD": I.INSTRUMENT_FX_MAJORS_AUD_USD,
    "USDCAD": I.INSTRUMENT_FX_MAJORS_USD_CAD,
    "NZDUSD": I.INSTRUMENT_FX_MAJORS_NZD_USD,
    "EURGBP": I.INSTRUMENT_FX_CROSSES_EUR_GBP,

    # Forex crosses / exotics
    "AUDCAD": I.INSTRUMENT_FX_CROSSES_AUD_CAD,
    "AUDCHF": I.INSTRUMENT_FX_CROSSES_AUD_CHF,
    "AUDJPY": I.INSTRUMENT_FX_CROSSES_AUD_JPY,
    "AUDNZD": I.INSTRUMENT_FX_CROSSES_AUD_NZD,
    "CADCHF": I.INSTRUMENT_FX_CROSSES_CAD_CHF,
    "CADJPY": I.INSTRUMENT_FX_CROSSES_CAD_JPY,
    "CHFJPY": I.INSTRUMENT_FX_CROSSES_CHF_JPY,
    "EURAUD": I.INSTRUMENT_FX_CROSSES_EUR_AUD,
    "EURCAD": I.INSTRUMENT_FX_CROSSES_EUR_CAD,
    "EURCHF": I.INSTRUMENT_FX_CROSSES_EUR_CHF,
    "EURCZK": I.INSTRUMENT_FX_CROSSES_EUR_CZK,
    "EURHUF": I.INSTRUMENT_FX_CROSSES_EUR_HUF,
    "EURNOK": I.INSTRUMENT_FX_CROSSES_EUR_NOK,
    "EURNZD": I.INSTRUMENT_FX_CROSSES_EUR_NZD,
    "EURPLN": I.INSTRUMENT_FX_CROSSES_EUR_PLN,
    "EURSEK": I.INSTRUMENT_FX_CROSSES_EUR_SEK,
    "GBPAUD": I.INSTRUMENT_FX_CROSSES_GBP_AUD,
    "NZDCAD": I.INSTRUMENT_FX_CROSSES_NZD_CAD,
    "NZDCHF": I.INSTRUMENT_FX_CROSSES_NZD_CHF,
    "USDCNH": I.INSTRUMENT_FX_CROSSES_USD_CNH,
    "USDCZK": I.INSTRUMENT_FX_CROSSES_USD_CZK,
    "USDHUF": I.INSTRUMENT_FX_CROSSES_USD_HUF,
    "USDMXN": I.INSTRUMENT_FX_CROSSES_USD_MXN,
    "USDNOK": I.INSTRUMENT_FX_CROSSES_USD_NOK,
    "USDPLN": I.INSTRUMENT_FX_CROSSES_USD_PLN,
    "USDSEK": I.INSTRUMENT_FX_CROSSES_USD_SEK,
    "USDSGD": I.INSTRUMENT_FX_CROSSES_USD_SGD,
    "USDZAR": I.INSTRUMENT_FX_CROSSES_USD_ZAR,

    # Metals
    "XAUUSD": I.INSTRUMENT_FX_METALS_XAU_USD,
    "XAGUSD": I.INSTRUMENT_FX_METALS_XAG_USD,

    # Indices
    "US100": I.INSTRUMENT_IDX_AMERICA_E_NQ_100,
    "US30": I.INSTRUMENT_IDX_AMERICA_E_D_J_IND,
    "US500": I.INSTRUMENT_IDX_AMERICA_E_SANDP_500,

    # Crypto
    "BTCUSD": I.INSTRUMENT_VCCY_BTC_USD,

    # Energy
    "USOIL": I.INSTRUMENT_CMD_ENERGY_E_LIGHT,
}

END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=3 * 365)


def download_symbol(symbol_name: str, instrument) -> pd.DataFrame | None:
    logger.info(f"[{symbol_name}] downloading...")
    try:
        df = dukascopy_python.fetch(
            instrument=instrument,
            interval=dukascopy_python.INTERVAL_MIN_15,
            offer_side=dukascopy_python.OFFER_SIDE_BID,
            start=START_DATE,
            end=END_DATE,
        )
    except Exception as e:
        logger.error(f"[{symbol_name}] fetch failed: {e}")
        return None

    if df is None or len(df) == 0:
        logger.warning(f"[{symbol_name}] no data returned")
        return None

    df = df.reset_index()
    df = df.rename(columns={"index": "timestamp", "volume": "tick_volume"})
    df["symbol"] = symbol_name
    cols = ["timestamp", "symbol", "open", "high", "low", "close", "tick_volume"]
    df = df[[c for c in cols if c in df.columns]]

    out_path = OUTPUT_DIR / f"{symbol_name}_M15_dukascopy.csv"
    df.to_csv(out_path, index=False)
    return df


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Downloading {len(SYMBOL_INSTRUMENTS)} symbols, {START_DATE.date()} -> {END_DATE.date()}, M15")

    summary = []
    for symbol, instrument in SYMBOL_INSTRUMENTS.items():
        df = download_symbol(symbol, instrument)
        if df is not None:
            span_days = (df["timestamp"].max() - df["timestamp"].min()).days
            summary.append((symbol, len(df), df["timestamp"].min(), df["timestamp"].max(), span_days))
        else:
            summary.append((symbol, 0, None, None, 0))
        time.sleep(1)

    logger.info("=" * 70)
    logger.info(f"{'SYMBOL':<10} {'CANDLES':>10} {'SPAN_DAYS':>10}  RANGE")
    for symbol, n, start, end, days in summary:
        if n == 0:
            logger.info(f"{symbol:<10} {'FAILED':>10}")
        else:
            logger.info(f"{symbol:<10} {n:>10,} {days:>10}  {start} -> {end}")

    ok = sum(1 for _, n, *_ in summary if n > 0)
    logger.info(f"=== Downloaded {ok}/{len(summary)} symbols to {OUTPUT_DIR} ===")


if __name__ == "__main__":
    main()

```

---

## `training/extract_features_all.py`

```py
"""
Feature Extraction — All Dukascopy Symbols, with Frozen-Data Exclusion
========================================================================
Computes the 27 CLEAN signal features (same names/order as
core.feature_history_recorder.FEATURE_27) from each
data/historical_data/{SYMBOL}_M15_dukascopy.csv.

Any symbol whose price history fails the frozen/flat-data validation
(constant price across long stretches, near-zero variance) is EXCLUDED —
no feature/label/model files are produced for it, and it is reported in
the summary so it can stay on rule-based + confluence (ML=ABSTAIN) until
live feature_history accumulates real data.

Output: data/historical_data/features/{SYMBOL}_features.parquet
  columns: timestamp + FEATURE_27 (27 columns)

Run: python training/extract_features_all.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.feature_history_recorder import FEATURE_27  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

INPUT_DIR = BASE_DIR / "data" / "historical_data"
OUTPUT_DIR = INPUT_DIR / "features"

FAST_EMA, SLOW_EMA = 12, 26
RSI_PERIOD = 14
ATR_PERIOD = 14
BB_PERIOD, BB_STD = 20, 2.0
STOCH_K, STOCH_D = 14, 3
SMA_20, SMA_50 = 20, 50
MOMENTUM_PERIOD = 20
VOLUME_SMA = 20
HTF_MULTIPLIER = 16  # M15 -> H4


# ── Frozen/corrupted data validation ────────────────────────────────────────

def validate_data(df: pd.DataFrame) -> list[str]:
    """Return a list of issues; non-empty means the symbol should be excluded."""
    issues = []
    close = df["close"].values

    price_std = np.std(close)
    price_range = np.max(close) - np.min(close)

    if price_std < 1e-9:
        issues.append(f"price std dev too low: {price_std:.8f}")
    if price_range / max(np.mean(close), 1e-9) < 1e-5:
        issues.append(f"price range too small relative to level: {price_range:.8f}")

    df_temp = df.copy()
    df_temp["month"] = pd.to_datetime(df_temp["timestamp"]).dt.to_period("M")
    monthly = df_temp.groupby("month")["close"].agg(["min", "max"])

    def count_consecutive_same(arr):
        if len(arr) == 0:
            return 0
        max_count = current = 1
        for i in range(1, len(arr)):
            if arr[i] == arr[i - 1]:
                current += 1
                max_count = max(max_count, current)
            else:
                current = 1
        return max_count

    consec_max = count_consecutive_same(monthly["max"].round(6).values)
    consec_min = count_consecutive_same(monthly["min"].round(6).values)

    if consec_max >= 4:
        issues.append(f"FROZEN: {consec_max} consecutive months with same MAX")
    if consec_min >= 4:
        issues.append(f"FROZEN: {consec_min} consecutive months with same MIN")

    return issues


# ── Indicators ───────────────────────────────────────────────────────────────

def calc_ema(data, period):
    return data.ewm(span=period, adjust=False).mean()

def calc_sma(data, period):
    return data.rolling(window=period).mean()

def calc_rsi(data, period):
    delta = data.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calc_atr(df, period):
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def calc_bollinger(data, period, std_dev):
    middle = calc_sma(data, period)
    std = data.rolling(window=period).std()
    return middle + std * std_dev, middle, middle - std * std_dev

def calc_stochastic(df, k_period, d_period):
    low_min = df["low"].rolling(window=k_period).min()
    high_max = df["high"].rolling(window=k_period).max()
    stoch_k = 100 * (df["close"] - low_min) / (high_max - low_min)
    stoch_d = stoch_k.rolling(window=d_period).mean()
    return stoch_k, stoch_d

def calc_sentiment(df):
    range_hl = (df["high"] - df["low"]).replace(0, np.nan)
    bullish = (df["close"] - df["low"]) / range_hl
    bearish = (df["high"] - df["close"]) / range_hl
    net = bullish - bearish
    return bullish.fillna(0.5), bearish.fillna(0.5), net.fillna(0)

def resample_to_htf(df, multiplier):
    df_indexed = df.set_index("timestamp")
    htf = df_indexed.resample(f"{multiplier * 15}min").agg({
        "open": "first", "high": "max", "low": "min",
        "close": "last", "tick_volume": "sum",
    }).dropna()
    return htf.reset_index()


def extract_features(df: pd.DataFrame) -> pd.DataFrame:
    f = pd.DataFrame()
    f["timestamp"] = df["timestamp"]
    f["close"] = df["close"].values
    f["high"] = df["high"].values
    f["low"] = df["low"].values
    f["volume"] = df["tick_volume"].values

    f["sma_20"] = calc_sma(df["close"], SMA_20).values
    f["sma_50"] = calc_sma(df["close"], SMA_50).values
    f["fast_ema"] = calc_ema(df["close"], FAST_EMA).values
    f["slow_ema"] = calc_ema(df["close"], SLOW_EMA).values

    htf = resample_to_htf(df, HTF_MULTIPLIER)
    htf["htf_fast_ema"] = calc_ema(htf["close"], FAST_EMA)
    htf["htf_slow_ema"] = calc_ema(htf["close"], SLOW_EMA)
    htf["htf_trend_direction"] = np.where(htf["htf_fast_ema"] > htf["htf_slow_ema"], 1, -1)

    htf_merge = htf[["timestamp", "htf_fast_ema", "htf_slow_ema", "htf_trend_direction"]]
    df_with_htf = pd.merge_asof(
        df.sort_values("timestamp"), htf_merge.sort_values("timestamp"),
        on="timestamp", direction="backward",
    )
    f["htf_fast_ema"] = df_with_htf["htf_fast_ema"].values
    f["htf_slow_ema"] = df_with_htf["htf_slow_ema"].values
    f["htf_trend_direction"] = df_with_htf["htf_trend_direction"].values

    m15_trend = np.where(f["fast_ema"] > f["slow_ema"], 1, -1)
    f["htf_trend_alignment"] = (m15_trend == f["htf_trend_direction"]).astype(int)

    f["rsi"] = calc_rsi(df["close"], RSI_PERIOD).values
    stoch_k, stoch_d = calc_stochastic(df, STOCH_K, STOCH_D)
    f["stoch_k"] = stoch_k.values
    f["stoch_d"] = stoch_d.values
    f["momentum"] = df["close"].pct_change(periods=MOMENTUM_PERIOD).values

    f["atr"] = calc_atr(df, ATR_PERIOD).values
    bb_u, bb_m, bb_l = calc_bollinger(df["close"], BB_PERIOD, BB_STD)
    f["bb_upper"] = bb_u.values
    f["bb_middle"] = bb_m.values
    f["bb_lower"] = bb_l.values
    f["volatility"] = df["close"].rolling(window=20).std().values

    f["volume_sma"] = calc_sma(df["tick_volume"], VOLUME_SMA).values
    vol_sma = f["volume_sma"].replace(0, np.nan)
    f["volume_ratio"] = (df["tick_volume"].values / vol_sma).fillna(1.0)
    f["price_volume"] = df["close"].values * df["tick_volume"].values

    bullish, bearish, net = calc_sentiment(df)
    f["bullish_sentiment"] = bullish.values
    f["bearish_sentiment"] = bearish.values
    f["net_sentiment"] = net.values

    return f[["timestamp"] + FEATURE_27]


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    excluded = []
    extracted = []

    for path in sorted(INPUT_DIR.glob("*_M15_dukascopy.csv")):
        symbol = path.stem.replace("_M15_dukascopy", "")
        df = pd.read_csv(path)
        if "close" not in df.columns or len(df) < 100:
            excluded.append((symbol, "insufficient rows"))
            continue
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)

        issues = validate_data(df)
        if issues:
            excluded.append((symbol, "; ".join(issues)))
            logger.warning(f"[{symbol}] EXCLUDED — {'; '.join(issues)}")
            continue

        features = extract_features(df)
        before = len(features)
        features = features.dropna().reset_index(drop=True)
        dropped = before - len(features)

        out_path = OUTPUT_DIR / f"{symbol}_features.parquet"
        features.to_parquet(out_path, index=False)
        extracted.append((symbol, len(features), dropped))
        logger.info(f"[{symbol}] {len(features):,} rows ({dropped} warmup dropped) -> {out_path.name}")

    logger.info("=" * 70)
    logger.info(f"Extracted {len(extracted)} symbols, excluded {len(excluded)}")
    if excluded:
        logger.info("Excluded (frozen/invalid data):")
        for symbol, reason in excluded:
            logger.info(f"  {symbol}: {reason}")


if __name__ == "__main__":
    main()

```

---

## `training/label_dukascopy_all.py`

```py
"""
Labeling — All Dukascopy Symbols (Price-Action, Same Methodology as the
Original 8 Pretrained Models)
=========================================================================
Reads data/historical_data/features/{SYMBOL}_features.parquet (M15 bars,
27 CLEAN features), applies the proven 24-candle / 20-pip forward-window
labeling (SELL=0, HOLD=1, BUY=2), and writes per-symbol stratified
train/val/test splits.

Threshold is category-aware via _pip_value() (forex 0.0001, JPY 0.01,
metals 0.01, indices/crypto/energy 1.0) — same helper used by the live
build_training_sets.py, so all symbols use one consistent, already-reviewed
methodology. Symbols whose resulting label distribution is degenerate
(>95% one class, or any class at 0%) are flagged in the summary but still
produce a model — diversification across model types means a skewed XGBoost
label set is not fatal (e.g. EURGBP was already heavily skewed historically).

Output: data/historical_data/splits/{SYMBOL}_{train,val,test}.parquet
  columns: feat_<name> (27) + label + weight

Run: python training/label_dukascopy_all.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.feature_history_recorder import FEATURE_27  # noqa: E402
from core.trade_outcome_simulator import _pip_value  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

FEATURES_DIR = BASE_DIR / "data" / "historical_data" / "features"
SPLITS_DIR = BASE_DIR / "data" / "historical_data" / "splits"

FORWARD_CANDLES = 24   # 6 hours on M15
PIP_THRESHOLD = 20

LABEL_SELL, LABEL_HOLD, LABEL_BUY = 0, 1, 2

TRAIN_RATIO, VAL_RATIO, TEST_RATIO = 0.70, 0.15, 0.15
DEGENERATE_PCT = 0.95


def label_symbol(close_prices: np.ndarray, threshold: float) -> np.ndarray:
    n = len(close_prices)
    labels = np.full(n, LABEL_HOLD, dtype=int)

    for i in range(n - FORWARD_CANDLES):
        current = close_prices[i]
        future = close_prices[i + 1: i + 1 + FORWARD_CANDLES]
        max_gain = np.max(future) - current
        max_loss = current - np.min(future)

        if max_gain >= threshold and max_loss < threshold:
            labels[i] = LABEL_BUY
        elif max_loss >= threshold and max_gain < threshold:
            labels[i] = LABEL_SELL

    return labels


def main():
    SPLITS_DIR.mkdir(parents=True, exist_ok=True)

    summary = []

    for path in sorted(FEATURES_DIR.glob("*_features.parquet")):
        symbol = path.stem.replace("_features", "")
        df = pd.read_parquet(path)
        df = df.sort_values("timestamp").reset_index(drop=True)

        if len(df) <= FORWARD_CANDLES:
            logger.warning(f"[{symbol}] too few rows ({len(df)}) — skipping")
            continue

        threshold = PIP_THRESHOLD * _pip_value(symbol)
        labels = label_symbol(df["close"].to_numpy(dtype=np.float64), threshold)

        usable = df.iloc[: len(df) - FORWARD_CANDLES].copy()
        usable["label"] = labels[: len(usable)]

        feat_cols = {f"feat_{name}": usable[name].astype(np.float32) for name in FEATURE_27}
        out_df = pd.DataFrame(feat_cols)
        out_df["label"] = usable["label"].values.astype(int)
        out_df["weight"] = 1.0

        dist = out_df["label"].value_counts(normalize=True).reindex([0, 1, 2], fill_value=0.0)
        counts = out_df["label"].value_counts().reindex([0, 1, 2], fill_value=0)
        degenerate = (dist.max() > DEGENERATE_PCT) or (dist.min() == 0.0)

        # Stratified 70/15/15 split
        try:
            train_df, temp_df = train_test_split(
                out_df, test_size=(VAL_RATIO + TEST_RATIO),
                stratify=out_df["label"], random_state=42, shuffle=True,
            )
            val_ratio_of_temp = TEST_RATIO / (VAL_RATIO + TEST_RATIO)
            val_df, test_df = train_test_split(
                temp_df, test_size=val_ratio_of_temp,
                stratify=temp_df["label"], random_state=42, shuffle=True,
            )
        except ValueError:
            train_df, temp_df = train_test_split(
                out_df, test_size=(VAL_RATIO + TEST_RATIO), random_state=42, shuffle=True,
            )
            val_df, test_df = train_test_split(temp_df, test_size=0.5, random_state=42, shuffle=True)

        train_df.to_parquet(SPLITS_DIR / f"{symbol}_train.parquet", index=False)
        val_df.to_parquet(SPLITS_DIR / f"{symbol}_val.parquet", index=False)
        test_df.to_parquet(SPLITS_DIR / f"{symbol}_test.parquet", index=False)

        summary.append((symbol, len(out_df), counts[0], counts[1], counts[2], degenerate))

        flag = "  [DEGENERATE]" if degenerate else ""
        logger.info(
            f"[{symbol}] n={len(out_df):,}  SELL={counts[0]} ({dist[0]:.1%})  "
            f"HOLD={counts[1]} ({dist[1]:.1%})  BUY={counts[2]} ({dist[2]:.1%}){flag}"
        )

    logger.info("=" * 70)
    n_degenerate = sum(1 for *_, d in summary if d)
    logger.info(f"=== Labeled {len(summary)} symbols, {n_degenerate} with degenerate distributions ===")
    if n_degenerate:
        logger.info("Degenerate symbols (review threshold/category mapping later):")
        for symbol, n, sell, hold, buy, d in summary:
            if d:
                logger.info(f"  {symbol}: n={n} SELL={sell} HOLD={hold} BUY={buy}")


if __name__ == "__main__":
    main()

```

---

## `training/pretrain_dukascopy.py`

```py
"""
Pretrain XGBoost / LightGBM / CatBoost / Transformer for All Symbols
======================================================================
Bootstraps every symbol from the Dukascopy price-action label sets
produced by label_dukascopy_all.py (data/historical_data/splits/), using
the SAME retrain_symbol() function and "never regress" guard as the daily
retrainer — each model type trains independently on the same per-symbol
price-action labels (no cross-source contamination).

Train+val splits are combined here; retrain_symbol() does its own
stratified holdout internally for the val_acc comparison.

Output (matching daily_retrainer.py's flat layout, auto-discovered by
core/ensemble_predictor.py):
  XGBoost     -> FTMO_System/data/models/{SYM}_xgboost.joblib
  LightGBM    -> GITHUB_MODELS_DIR/{SYM}_lightgbm.joblib
  CatBoost    -> GITHUB_MODELS_DIR/{SYM}_catboost.joblib
  Transformer -> GITHUB_MODELS_DIR/transformer/{SYM}_transformer.pth

Run: python training/pretrain_dukascopy.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from training.daily_retrainer import retrain_symbol, _DEFAULT_GITHUB_MODELS  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SPLITS_DIR = BASE_DIR / "data" / "historical_data" / "splits"
LOCAL_MODEL_DIR = str(BASE_DIR / "data" / "models")
MIN_TRADES = 50
HOLDOUT_PCT = 0.2


def main():
    if not SPLITS_DIR.exists():
        logger.error(f"{SPLITS_DIR} not found — run label_dukascopy_all.py first")
        return

    symbols = sorted({p.stem.replace("_train", "") for p in SPLITS_DIR.glob("*_train.parquet")})
    logger.info(f"Pretraining {len(symbols)} symbols -> local={LOCAL_MODEL_DIR}  github={_DEFAULT_GITHUB_MODELS}")

    results = []
    for symbol in symbols:
        train_path = SPLITS_DIR / f"{symbol}_train.parquet"
        val_path = SPLITS_DIR / f"{symbol}_val.parquet"

        df = pd.read_parquet(train_path)
        if val_path.exists():
            df = pd.concat([df, pd.read_parquet(val_path)], ignore_index=True)

        result = retrain_symbol(
            symbol, df,
            local_model_dir=LOCAL_MODEL_DIR,
            github_models_dir=_DEFAULT_GITHUB_MODELS,
            min_trades=MIN_TRADES,
            holdout_pct=HOLDOUT_PCT,
        )
        results.append(result)

    logger.info("=" * 70)
    logger.info(f"{'SYMBOL':<10} {'UPDATED':<30} {'KEPT':<25} {'SKIPPED':<30} ERRORS")
    for r in results:
        logger.info(
            f"{r['symbol']:<10} {','.join(r['updated']):<30} {','.join(r['kept']):<25} "
            f"{','.join(r['skipped']):<30} {','.join(r['errors'])}"
        )

    n_updated = sum(1 for r in results if r["updated"])
    logger.info(f"=== Pretrained {len(results)} symbols, {n_updated} with at least one model updated ===")


if __name__ == "__main__":
    main()

```
