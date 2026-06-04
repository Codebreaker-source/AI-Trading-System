"""
Ensemble Predictor - XGBoost Only (FTMO Deployment)
====================================================
Adapted from V3.2 (tree-based). LightGBM and CatBoost removed.
Accepts any symbol dynamically — not limited to 8 pairs.
Returns None for symbols with no trained model (caller treats as ABSTAIN).

Label encoding (matches pretrained models — DO NOT CHANGE):
  0 = SELL, 1 = HOLD, 2 = BUY

Feature input: 27 CLEAN features (EA writes 27 directly, no extraction step needed).
"""

import gc
import csv
import warnings
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

warnings.filterwarnings('ignore')


SUFFIX_STRIP = [".i", "_SB", ".r", "_raw", ".a", ".b", ".c", ".m", ".pro", ".sim"]

# Label mapping — matches training. Index 0=SELL, 1=HOLD, 2=BUY.
LABELS = ['SELL', 'HOLD', 'BUY']

MODEL_FILENAME_PATTERNS = [
    "{symbol}_xgboost_CLEAN27.joblib",
    "{symbol}_xgboost.joblib",
]


def strip_suffix(symbol: str) -> str:
    s = symbol
    for suf in SUFFIX_STRIP:
        if s.endswith(suf):
            s = s[: -len(suf)]
            break
    return s.upper()


class EnsemblePredictorV3:
    """
    XGBoost-only predictor for FTMO deployment.
    Models loaded on demand and cached to respect RAM limits.
    """

    def __init__(
        self,
        model_dir: str = None,
        enable_logging: bool = True,
        log_dir: str = None,
    ):
        if model_dir is None:
            self.model_dir = Path(__file__).parent.parent / "data" / "models"
        else:
            self.model_dir = Path(model_dir)

        self.n_features = 27  # EA writes 27 CLEAN features directly

        self._cached_models: Dict[str, Optional[object]] = {}

        self.enable_logging = enable_logging
        if log_dir is None:
            self.log_dir = Path(__file__).parent.parent / "logs" / "predictions"
        else:
            self.log_dir = Path(log_dir)

        if self.enable_logging:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self._init_log_file()

        print(f"[ENSEMBLE] XGBoost predictor initialized — model_dir: {self.model_dir}")

    # ------------------------------------------------------------------
    # Model file resolution
    # ------------------------------------------------------------------

    def _find_model_path(self, symbol: str) -> Optional[Path]:
        base = strip_suffix(symbol)
        for pattern in MODEL_FILENAME_PATTERNS:
            path = self.model_dir / pattern.format(symbol=base)
            if path.exists():
                return path
        return None

    def load_models_for_pair(self, symbol: str) -> Optional[object]:
        """
        Returns the XGBoost model for this symbol, or None if not found.
        Result is cached after first load.
        """
        cache_key = strip_suffix(symbol)
        if cache_key in self._cached_models:
            return self._cached_models[cache_key]

        model_path = self._find_model_path(symbol)
        if model_path is None:
            self._cached_models[cache_key] = None
            return None

        try:
            model = joblib.load(model_path)
            self._cached_models[cache_key] = model
            print(f"[ENSEMBLE] Loaded model for {cache_key}: {model_path.name}")
            return model
        except Exception as e:
            print(f"[ENSEMBLE] Failed to load model for {cache_key}: {e}")
            self._cached_models[cache_key] = None
            return None

    def unload_models(self, symbol: str = None):
        if symbol:
            key = strip_suffix(symbol)
            self._cached_models.pop(key, None)
        else:
            self._cached_models.clear()
        gc.collect()

    def has_model(self, symbol: str) -> bool:
        return self._find_model_path(symbol) is not None

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def _validate_features(self, features: np.ndarray) -> np.ndarray:
        if not isinstance(features, np.ndarray):
            features = np.array(features)
        features = features.astype(np.float64)
        features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)
        return features

    def predict_pair(self, features: np.ndarray, pair: str, trade_id: str = None) -> Optional[Dict]:
        """
        Make prediction for a symbol using its XGBoost model.

        Args:
            features: 27-element numpy array (27 CLEAN features from EA)
            pair: Symbol name (FTMO format, suffixes stripped internally)
            trade_id: Optional ID for prediction logging

        Returns:
            Dict with prediction results, or None if no model exists for this symbol.
        """
        features = self._validate_features(features)

        if len(features) != self.n_features:
            print(f"[ENSEMBLE] {pair}: expected {self.n_features} features, got {len(features)}")
            return None

        model = self.load_models_for_pair(pair)
        if model is None:
            return None  # Caller should treat as ABSTAIN

        if features.ndim == 1:
            features = features.reshape(1, -1)

        try:
            proba = model.predict_proba(features)[0]
        except Exception as e:
            print(f"[ENSEMBLE] {pair}: predict_proba failed — {e}")
            return None

        pred_class = int(np.argmax(proba))
        confidence = float(np.max(proba))

        # HOLD-bias fix: if HOLD wins, promote strongest directional signal.
        # Preserves meaningful confidence rather than dropping to 0.
        if pred_class == 1:  # HOLD (index 1)
            hold_conf = confidence
            if proba[2] >= proba[0]:  # BUY >= SELL
                pred_class = 2
                confidence = max(float(proba[2]), hold_conf * 0.5, 0.35)
            else:
                pred_class = 0
                confidence = max(float(proba[0]), hold_conf * 0.5, 0.35)

        result = {
            'pair': pair,
            'prediction': pred_class,
            'prediction_label': LABELS[pred_class],
            'confidence': confidence,
            'agreement': '1/1',
            'unanimous': True,
            'models_used': ['xgboost'],
            'individual_predictions': {
                'xgboost': {
                    'prediction': pred_class,
                    'label': LABELS[pred_class],
                    'confidence': confidence,
                }
            },
            'individual_probabilities': {'xgboost': proba.tolist()},
            'vote_distribution': {
                LABELS[0]: round(float(proba[0]), 4),
                LABELS[1]: round(float(proba[1]), 4),
                LABELS[2]: round(float(proba[2]), 4),
            },
            'timestamp': datetime.now().isoformat(),
        }

        self._log_prediction(result, trade_id)
        return result

    def get_trading_signal(
        self,
        features: np.ndarray,
        pair: str,
        min_confidence: float = 0.45,
        trade_id: str = None,
    ) -> Optional[Dict]:
        """
        Get a filtered trading signal.
        Returns None if no model. Returns NO_TRADE if confidence too low or HOLD.
        """
        result = self.predict_pair(features, pair, trade_id)
        if result is None:
            return None  # No model — caller handles as ABSTAIN

        if result['confidence'] < min_confidence:
            return {
                'pair': pair,
                'signal': 'NO_TRADE',
                'reason': f"Low confidence: {result['confidence']:.2%} < {min_confidence:.2%}",
                'prediction': result,
            }

        if result['prediction'] == 1:  # HOLD
            return {
                'pair': pair,
                'signal': 'HOLD',
                'reason': 'Model predicts HOLD',
                'prediction': result,
            }

        return {
            'pair': pair,
            'signal': result['prediction_label'],
            'confidence': result['confidence'],
            'agreement': result['agreement'],
            'prediction': result,
        }

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _init_log_file(self):
        self.log_file = self.log_dir / f"predictions_{datetime.now().strftime('%Y%m%d')}.csv"
        if not self.log_file.exists():
            headers = [
                'timestamp', 'pair', 'prediction', 'prediction_label', 'confidence',
                'prob_sell', 'prob_hold', 'prob_buy', 'trade_id', 'actual_outcome', 'pnl',
            ]
            with open(self.log_file, 'w', newline='') as f:
                csv.writer(f).writerow(headers)

    def _log_prediction(self, result: Dict, trade_id: str = None):
        if not self.enable_logging:
            return
        probs = result.get('individual_probabilities', {}).get('xgboost', [0, 0, 0])
        row = [
            result['timestamp'],
            result['pair'],
            result['prediction'],
            result['prediction_label'],
            round(result['confidence'], 4),
            round(probs[0], 4),
            round(probs[1], 4),
            round(probs[2], 4),
            trade_id or '', '', '',
        ]
        with open(self.log_file, 'a', newline='') as f:
            csv.writer(f).writerow(row)

    def update_trade_outcome(self, trade_id: str, actual_outcome: str, pnl: float):
        if not self.enable_logging or not self.log_file.exists():
            return
        df = pd.read_csv(self.log_file)
        mask = df['trade_id'] == trade_id
        if mask.any():
            df.loc[mask, 'actual_outcome'] = actual_outcome
            df.loc[mask, 'pnl'] = pnl
            df.to_csv(self.log_file, index=False)

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def verify_models_exist(self, symbols: List[str] = None) -> Dict[str, bool]:
        results = {}
        if symbols:
            for sym in symbols:
                results[sym] = self.has_model(sym)
        else:
            for f in self.model_dir.glob("*_xgboost*.joblib"):
                results[f.stem] = True
        print(f"[MODELS] {sum(results.values())}/{len(results)} models found")
        return results

    def get_model_stats(self) -> Dict:
        return {
            'cached_symbols': list(self._cached_models.keys()),
            'total_cached': len(self._cached_models),
            'model_dir': str(self.model_dir),
            'logging_enabled': self.enable_logging,
        }
