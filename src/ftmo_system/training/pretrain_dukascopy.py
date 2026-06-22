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
