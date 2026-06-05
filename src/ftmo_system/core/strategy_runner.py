"""
Strategy Runner
================
Runs all 15 independent signal sources (6 EA translations + 9 rule-based)
on every symbol every cycle. Returns all fired signals with attribution.

Signal sources:
  EA translations (6):
    sma_3crossover, tema_barrington, ama_scalper,
    sma_price_cross, dema_rsi_hf, dema_supertrend

  Rule-based (9):
    volume_breakout, currency_strength_divergence, volatility_breakout,
    trend_following, mean_reversion, volatility_contraction,
    currency_correlation, low_volatility_momentum, high_volatility_reversal
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional

from core.strategies import (
    SMA3CrossoverStrategy,
    TEMABarringtonStrategy,
    AMAScalperStrategy,
    SMAPriceCrossStrategy,
    DEMARSIHighFreqStrategy,
    DEMASuperTrendStrategy,
)
from core.rule_based_strategies import RuleBasedStrategies

logger = logging.getLogger(__name__)

# 10-feature extraction indices from 27-feature array
# Mapping used by rule_based_strategies._extract_features()
# Features needed: volume_sma(21), eur/gbp/nzd/usd/jpy strength (not in 27-feat),
# volatility(20), returns_std(not in 27), volatility_confirm(not in 27), atr(16)
# For currency strength features not available, use 0.5 (neutral) as default
_RULE_FEATURE_IDX = {
    'volume_sma':   21,
    'volatility':   20,
    'atr':          16,
}


def _build_rule_features(features_27: np.ndarray, symbol: str) -> np.ndarray:
    """
    Build the 10-feature array expected by RuleBasedStrategies from our 27-feature array.
    Currency strength features not available in 27-feat -- use 0.5 (neutral).
    """
    vol_sma    = float(features_27[21]) if len(features_27) > 21 else 1.0
    volatility = float(features_27[20]) if len(features_27) > 20 else 0.001
    atr        = float(features_27[16]) if len(features_27) > 16 else 0.001
    return np.array([
        vol_sma,   # volume_sma
        0.5,       # eur_strength (unavailable — neutral)
        0.5,       # gbp_strength
        0.5,       # nzd_strength
        0.5,       # usd_strength
        0.5,       # jpy_strength
        volatility,# volatility
        0.01,      # returns_std (unavailable — neutral)
        1.0 if volatility > 0.001 else 0.0,  # volatility_confirm
        atr,       # atr
    ], dtype=np.float32)


class StrategyRunner:
    """
    Runs all independent signal sources each cycle.
    Returns a list of signal dicts — one per (symbol, source) that fired.
    """

    def __init__(self):
        # EA-translated strategies
        self.ea_strategies = [
            SMA3CrossoverStrategy(),
            TEMABarringtonStrategy(),
            AMAScalperStrategy(),
            SMAPriceCrossStrategy(),
            DEMARSIHighFreqStrategy(),
            DEMASuperTrendStrategy(),
        ]

        # Rule-based strategy engine
        self.rule_engine = RuleBasedStrategies()

        all_names = [s.name for s in self.ea_strategies] + self.rule_engine.strategy_names
        logger.info(f"[STRATEGY RUNNER] {len(all_names)} signal sources loaded: {all_names}")

    def run(
        self,
        symbol: str,
        ohlcv: pd.DataFrame,
        features_27: np.ndarray,
        point: float = 0.00001,
    ) -> List[dict]:
        """
        Run all signal sources on one symbol.

        Args:
            symbol:      e.g. 'EURUSD.sim'
            ohlcv:       DataFrame [open, high, low, close, tick_volume], newest last
            features_27: current bar's 27-feature array
            point:       pip size for this symbol

        Returns:
            List of fired signals:
            [
              {
                'symbol':      str,
                'source':      str,
                'action':      'BUY'|'SELL',
                'sl_points':   int,
                'tp_points':   int,
                'lot':         float,
                'indicators':  dict,
                'source_type': 'ea_translation'|'rule_based',
              },
              ...
            ]
        """
        signals = []

        # --- EA-translated strategies ---
        for strategy in self.ea_strategies:
            try:
                result = strategy.generate_signal(symbol, ohlcv, point)
                if result and result.get("action") in ("BUY", "SELL"):
                    signals.append({
                        "symbol":      symbol,
                        "source":      strategy.name,
                        "source_type": "ea_translation",
                        **result,
                    })
            except Exception as e:
                logger.debug(f"[{strategy.name}] {symbol}: {e}")

        # --- Rule-based strategies ---
        try:
            rule_features = _build_rule_features(features_27, symbol)
            predictions   = self.rule_engine.predict_all(symbol, rule_features)
            for strategy_name, vote in predictions.items():
                if vote in ("BUY", "SELL"):
                    signals.append({
                        "symbol":      symbol,
                        "source":      strategy_name,
                        "source_type": "rule_based",
                        "action":      vote,
                        "sl_points":   30,
                        "tp_points":   60,
                        "lot":         0.01,
                        "indicators":  {"rule_vote": vote},
                    })
        except Exception as e:
            logger.debug(f"[rule_based] {symbol}: {e}")

        return signals

    def run_all_symbols(
        self,
        ohlcv_dict: Dict[str, pd.DataFrame],
        features_dict: Dict[str, np.ndarray],
        point_dict: Dict[str, float],
    ) -> Dict[str, List[dict]]:
        """
        Run all strategies on all symbols.

        Returns:
            { symbol: [list of fired signals] }
        """
        results = {}
        for symbol in ohlcv_dict:
            ohlcv      = ohlcv_dict.get(symbol)
            features   = features_dict.get(symbol, np.zeros(27))
            point      = point_dict.get(symbol, 0.00001)
            if ohlcv is None or len(ohlcv) < 3:
                continue
            fired = self.run(symbol, ohlcv, features, point)
            if fired:
                results[symbol] = fired
        return results
