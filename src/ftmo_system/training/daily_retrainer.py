"""
Daily retraining — all 4 model types.
Run once per day (Task Scheduler, 00:00 UTC).

For each symbol with ≥ MIN_TRADES executions:
  1. Label trades with 3-tier profit-aware scheme (TP/TRAIL/SL + sample_weight)
  2. Expand 27 → 105 features
  3. Retrain XGBoost, LightGBM, CatBoost, SimpleTransformer
  4. Only replace a model if new val_acc ≥ existing val_acc
  5. After all symbols: git commit + push updated models to GitHub
     so Colab picks them up on next session start.

Model save paths
----------------
  XGBoost     → FTMO_System/data/models/{SYM}_xgboost_CLEAN27.joblib   (local)
  LightGBM    → GITHUB_MODELS_DIR/{SYM}_lightgbm.joblib
  CatBoost    → GITHUB_MODELS_DIR/{SYM}_catboost.joblib
  Transformer → GITHUB_MODELS_DIR/transformer/{SYM}_transformer.pth
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

from training.data_labeler import (                        # noqa: E402
    label_dataframe, LABEL_SELL, LABEL_HOLD, LABEL_BUY,
)

logger = logging.getLogger(__name__)

# ── Default GitHub models directory ──────────────────────────────────────
# Override via config["paths"]["github_models_dir"]
_DEFAULT_GITHUB_MODELS = (
    r"C:\Users\mt5-admin\Documents\GitHub\AI-Trading-System\models\current"
)

# ── Required execution-log columns ───────────────────────────────────────
REQUIRED_TRADE_COLS = ["symbol", "direction", "outcome", "entry_time", "exit_time"]

FEATURE_27 = [
    "close", "high", "low", "volume",
    "sma_20", "sma_50", "fast_ema", "slow_ema",
    "htf_fast_ema", "htf_slow_ema", "htf_trend_direction", "htf_trend_alignment",
    "rsi", "stoch_k", "stoch_d", "momentum",
    "atr", "bb_upper", "bb_middle", "bb_lower", "volatility",
    "volume_sma", "volume_ratio", "price_volume",
    "bullish_sentiment", "bearish_sentiment", "net_sentiment",
]


# ══════════════════════════════════════════════════════════════════════════
# Data helpers
# ══════════════════════════════════════════════════════════════════════════

def load_execution_log(trades_csv: str) -> pd.DataFrame:
    if not os.path.exists(trades_csv):
        logger.warning(f"Execution log not found: {trades_csv}")
        return pd.DataFrame()
    df = pd.read_csv(trades_csv)
    missing = [c for c in REQUIRED_TRADE_COLS if c not in df.columns]
    if missing:
        logger.error(f"Execution log missing columns: {missing}")
        return pd.DataFrame()
    return df


def extract_feature_matrix(df: pd.DataFrame) -> np.ndarray | None:
    """Return raw (N, 27) float32 matrix — no expansion needed, models train on 27 CLEAN features."""
    missing = [f for f in FEATURE_27 if f not in df.columns]
    if missing:
        logger.warning(f"Feature columns missing: {missing[:5]}...")
        return None
    return df[FEATURE_27].values.astype(np.float32)


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
                    self.embedding  = nn.Linear(105, 64)
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

    def __init__(self, input_dim=105, d_model=64, nhead=4,
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

def retrain_symbol(symbol: str, symbol_df: pd.DataFrame,
                   local_model_dir: str, github_models_dir: str,
                   min_trades: int = 50, holdout_pct: float = 0.2) -> dict:

    result = {"symbol": symbol, "updated": [], "kept": [], "skipped": [], "errors": []}

    if len(symbol_df) < min_trades:
        logger.info(f"{symbol}: {len(symbol_df)} trades < {min_trades} minimum — skipping all")
        result["skipped"] = ["xgboost", "lightgbm", "catboost", "transformer"]
        return result

    df = symbol_df.copy()
    df["label"], df["weight"] = label_dataframe(df)

    X = extract_feature_matrix(df)
    if X is None:
        result["errors"].append("no_features")
        return result

    y = df["label"].values
    w = df["weight"].values

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
        ("xgboost",     train_xgboost,     os.path.join(local_model_dir,   f"{sym_clean}_xgboost_CLEAN27.joblib"), "sklearn"),
        ("lightgbm",    train_lightgbm,    os.path.join(github_models_dir, f"{sym_clean}_lightgbm.joblib"),        "sklearn"),
        ("catboost",    train_catboost,    os.path.join(github_models_dir, f"{sym_clean}_catboost.joblib"),        "sklearn"),
        ("transformer", train_transformer, os.path.join(gh_trf_dir,        f"{sym_clean}_transformer.pth"),        "transformer"),
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

    trades_csv         = r"C:\Users\mt5-admin\AppData\Roaming\MetaQuotes\Terminal\Common\Files\trades.csv"
    local_model_dir    = str(BASE_DIR / ml_cfg.get("model_dir", "data/models"))
    github_models_dir  = paths_cfg.get("github_models_dir", _DEFAULT_GITHUB_MODELS)
    min_trades         = trading_cfg.get("min_trades_for_retrain", 50)
    holdout_pct        = retrain_cfg.get("holdout_pct", 0.2)

    logger.info(f"=== Daily Retraining started {datetime.now(timezone.utc).isoformat()} ===")
    logger.info(f"Local models  : {local_model_dir}")
    logger.info(f"GitHub models : {github_models_dir}")

    df = load_execution_log(trades_csv)
    if df.empty:
        logger.info("No execution data — retraining skipped")
        return []

    results          = []
    symbols_updated  = []

    for symbol, group in df.groupby("symbol"):
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
