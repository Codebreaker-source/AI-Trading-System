"""
Daily XGBoost retraining from execution log data.
Run once per day (scheduled via run_system.py or cron).
Reads trades.csv, labels outcomes (3-tier profit-aware), trains per-symbol
XGBoost models with sample_weight.  Only replaces an existing model if the
new one is at least as accurate.
"""

import os
import sys
import json
import logging
import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path

from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import LabelEncoder

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.feature_expander import expand_features          # noqa: E402
from training.data_labeler import label_dataframe, LABEL_HOLD, LABEL_BUY, LABEL_SELL  # noqa: E402

logger = logging.getLogger(__name__)

REQUIRED_TRADE_COLS = [
    "symbol", "direction", "outcome",
    "entry_time", "exit_time",
]

FEATURE_27 = [
    "close", "high", "low", "volume",
    "sma_20", "sma_50", "fast_ema", "slow_ema",
    "htf_fast_ema", "htf_slow_ema", "htf_trend_direction", "htf_trend_alignment",
    "rsi", "stoch_k", "stoch_d", "momentum",
    "atr", "bb_upper", "bb_middle", "bb_lower", "volatility",
    "volume_sma", "volume_ratio", "price_volume",
    "bullish_sentiment", "bearish_sentiment", "net_sentiment",
]



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
    """
    Build 105-feature matrix from a dataframe that has the 27 CLEAN feature columns.
    Returns None if features are missing.
    """
    missing = [f for f in FEATURE_27 if f not in df.columns]
    if missing:
        logger.warning(f"Feature columns missing from execution log: {missing[:5]}...")
        return None
    raw = df[FEATURE_27].values.astype(np.float32)
    expanded_rows = []
    for row in raw:
        feat_dict = dict(zip(FEATURE_27, row))
        try:
            expanded = expand_features(feat_dict)
            expanded_rows.append(list(expanded.values()))
        except Exception as e:
            logger.debug(f"Feature expansion failed for row: {e}")
            expanded_rows.append([np.nan] * 105)
    X = np.array(expanded_rows, dtype=np.float32)
    return X


def train_xgboost(X: np.ndarray, y: np.ndarray,
                  sample_weight: np.ndarray | None = None,
                  holdout_pct: float = 0.2):
    """
    Train XGBoost with optional sample_weight (for 3-tier labeling).
    Returns (model, train_acc, val_acc).
    """
    if len(np.unique(y)) < 2:
        logger.warning("Only one class in labels — skipping training")
        return None, 0.0, 0.0

    # Propagate sample weights through the train/val split
    if sample_weight is not None:
        X_train, X_val, y_train, y_val, w_train, w_val = train_test_split(
            X, y, sample_weight,
            test_size=holdout_pct, random_state=42, stratify=y
        )
    else:
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=holdout_pct, random_state=42, stratify=y
        )
        w_train = w_val = None

    model = XGBClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric="mlogloss",
        num_class=3,
        objective="multi:softprob",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(
        X_train, y_train,
        sample_weight=w_train,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )

    train_acc = accuracy_score(y_train, model.predict(X_train))
    val_acc   = accuracy_score(y_val,   model.predict(X_val))
    return model, train_acc, val_acc


def evaluate_existing_model(model_path: str, X: np.ndarray, y: np.ndarray, holdout_pct: float) -> float:
    """Return validation accuracy of the existing saved model on a holdout split."""
    if not os.path.exists(model_path):
        return -1.0
    try:
        existing = joblib.load(model_path)
        _, X_val, _, y_val = train_test_split(
            X, y, test_size=holdout_pct, random_state=42, stratify=y
        )
        return accuracy_score(y_val, existing.predict(X_val))
    except Exception as e:
        logger.warning(f"Could not evaluate existing model {model_path}: {e}")
        return -1.0


def retrain_symbol(
    symbol: str,
    symbol_df: pd.DataFrame,
    model_dir: str,
    min_trades: int = 50,
    holdout_pct: float = 0.2,
) -> dict:
    result = {"symbol": symbol, "status": "skipped", "train_acc": 0.0, "val_acc": 0.0}

    if len(symbol_df) < min_trades:
        logger.info(f"{symbol}: only {len(symbol_df)} trades — need {min_trades}, skipping")
        return result

    symbol_df = symbol_df.copy()

    # 3-tier profit-aware labeling → (label, sample_weight) per row
    symbol_df["label"], symbol_df["weight"] = label_dataframe(symbol_df)

    X = extract_feature_matrix(symbol_df)
    if X is None:
        result["status"] = "no_features"
        return result

    y = symbol_df["label"].values
    w = symbol_df["weight"].values

    # Remove rows with NaN features
    valid_mask = ~np.isnan(X).any(axis=1)
    X, y, w = X[valid_mask], y[valid_mask], w[valid_mask]

    if len(X) < min_trades:
        logger.info(f"{symbol}: after NaN drop only {len(X)} usable rows — skipping")
        return result

    # Log label distribution for transparency
    from collections import Counter
    dist = Counter(y.tolist())
    logger.info(
        f"{symbol}: labels SELL={dist.get(0,0)} HOLD={dist.get(1,0)} BUY={dist.get(2,0)}, "
        f"mean_weight={w.mean():.3f}"
    )

    model_filename = f"{symbol}_xgboost_CLEAN27.joblib"
    model_path = os.path.join(model_dir, model_filename)

    existing_val_acc = evaluate_existing_model(model_path, X, y, holdout_pct)

    new_model, train_acc, val_acc = train_xgboost(X, y, sample_weight=w, holdout_pct=holdout_pct)
    if new_model is None:
        result["status"] = "training_failed"
        return result

    result["train_acc"] = round(train_acc, 4)
    result["val_acc"]   = round(val_acc, 4)

    if val_acc >= existing_val_acc:
        joblib.dump(new_model, model_path)
        result["status"] = "updated"
        logger.info(
            f"{symbol}: model updated — val_acc={val_acc:.3f} (was {existing_val_acc:.3f}), "
            f"train_acc={train_acc:.3f}, n={len(X)}"
        )
    else:
        result["status"] = "kept_existing"
        logger.info(
            f"{symbol}: new model ({val_acc:.3f}) worse than existing ({existing_val_acc:.3f}) — keeping existing"
        )

    return result


def run_daily_retraining(config: dict | None = None) -> list[dict]:
    """
    Main entry point. Call once per day.
    Returns list of per-symbol result dicts.
    """
    config = config or {}
    trading_cfg  = config.get("trading", {})
    retrain_cfg  = config.get("retraining", {})
    ml_cfg       = config.get("ml", {})

    trades_csv  = r"C:\Users\mt5-admin\AppData\Roaming\MetaQuotes\Terminal\Common\Files\trades.csv"
    model_dir   = str(BASE_DIR / ml_cfg.get("model_dir", "data/models"))
    min_trades  = trading_cfg.get("min_trades_for_retrain", 50)
    holdout_pct = retrain_cfg.get("holdout_pct", 0.2)

    logger.info(f"=== Daily Retraining started at {datetime.now(timezone.utc).isoformat()} ===")

    df = load_execution_log(trades_csv)
    if df.empty:
        logger.info("No execution data — retraining skipped")
        return []

    results = []
    for symbol, group in df.groupby("symbol"):
        try:
            r = retrain_symbol(symbol, group, model_dir, min_trades, holdout_pct)
            results.append(r)
        except Exception as e:
            logger.error(f"{symbol}: retraining crashed — {e}", exc_info=True)
            results.append({"symbol": symbol, "status": "error", "error": str(e)})

    updated  = sum(1 for r in results if r["status"] == "updated")
    skipped  = sum(1 for r in results if r["status"] == "skipped")
    kept     = sum(1 for r in results if r["status"] == "kept_existing")
    logger.info(f"=== Retraining complete: {updated} updated | {kept} kept | {skipped} skipped ===")
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg_path = BASE_DIR / "config" / "ftmo_config.json"
    config = {}
    if cfg_path.exists():
        with open(cfg_path) as f:
            config = json.load(f)
    run_daily_retraining(config)
