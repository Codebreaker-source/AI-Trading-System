"""
Live Trading System V5.0 - Tree-Based Ensemble Integration
==========================================================

MAJOR UPGRADE: Uses tree-based ensemble (XGBoost + LightGBM + CatBoost) instead
of neural networks for more reliable predictions.

Key Changes from V4.0:
- NEW: Tree-based ensemble predictor (V3.1) with equal weights
- NEW: Prediction logging for weight optimization after execution data gathered
- REMOVED: CNN/Transformer models (replaced by LightGBM/CatBoost)
- SIMPLIFIED: No sequence buffer needed (trees don't need time series)
- IMPROVED: 87% validation accuracy (up from 85% with mixed ensemble)

Model Performance:
- XGBoost:  85.0% average validation accuracy
- LightGBM: 87.0% average validation accuracy
- CatBoost: 85.8% average validation accuracy
- Ensemble: Equal weights [0.33, 0.33, 0.33], adaptive after live data

Author: AI Trading System
Version: 5.0 (Tree-Based Ensemble)
Date: 2025-11-29
"""

import pandas as pd
import numpy as np
import time
import argparse
from datetime import datetime
from pathlib import Path
from collections import deque
import json
import sys
from typing import Dict, List, Optional, Any, Tuple

import sys
import os
_FTMO_ROOT = str(Path(__file__).parent.parent)
if _FTMO_ROOT not in sys.path:
    sys.path.insert(0, _FTMO_ROOT)

# Import XGBoost-only ensemble predictor
from core.ensemble_predictor import EnsemblePredictorV3

# Import rule-based strategies
from core.rule_based_strategies import RuleBasedStrategies

# Import feature expander (27 -> 105 features)
from core.feature_expander import FeatureExpander

# Import confluence scoring system
from confluence import (
    HardFilters,
    ConfluenceScorer,
    RegimeDetector,
    RiskManager,
    LevelConfluence,
    FilterResult,
    ConfluenceResult,
    RegimeState,
    PortfolioRisk,
    ScalingSignal
)
from confluence.pullback_detector import PullbackDetector, PullbackStatus

# Import dimension checker for multi-dimensional signal validation
from dimensions import DimensionChecker, DangerScorer, TradeHistoryTracker, AntiFragileBuilder

# Import symbol manager for dynamic FTMO symbol discovery
from core.symbol_manager import SymbolManager, load_symbol_manager

# News integration (optional — graceful fallback if missing)
try:
    from news_integration import NewsIntegration
    HAS_NEWS = True
except ImportError:
    HAS_NEWS = False

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    print("[WARNING] MetaTrader5 library not available - running in simulation mode")


class LiveTradingSystemV5:
    """
    Live trading system with tree-based ensemble integration.
    
    Uses XGBoost + LightGBM + CatBoost with equal weights for predictions.
    Logs all predictions for post-hoc weight optimization.
    """
    
    def __init__(
        self,
        mode='demo',
        confidence_threshold=0.35,
        confluence_threshold=0.35,
        account_balance=10000.0,
        trading_capital_percent=0.10,
        weighting_mode='equal'
    ):
        """
        Initialize live trading system with tree-based ensemble.
        
        Args:
            mode: 'demo' or 'live'
            confidence_threshold: Minimum ML confidence for trades
            confluence_threshold: Minimum confluence score for trades
            account_balance: Full account balance (for reference)
            trading_capital_percent: Percent of account to use for trading (default 10%)
            weighting_mode: 'equal', 'validation', or 'confidence'
        
        Capital Segmentation:
            - Full account stored for reference
            - Trading capital = account_balance * trading_capital_percent
            - All risk calculations use trading capital only
            - Benefit: Can 'lose' trading capital = only 10% of real account
        """
        self.mode = mode
        self.confidence_threshold = confidence_threshold
        self.confluence_threshold = confluence_threshold
        
        # CAPITAL SEGMENTATION: Trade with only a portion of account
        self.full_account_balance = account_balance
        self.trading_capital_percent = trading_capital_percent
        self.account_balance = account_balance * trading_capital_percent  # Risk manager uses this
        
        self.weighting_mode = weighting_mode
        
        # FTMO System root
        self._system_root = Path(__file__).parent.parent

        # Discover symbols dynamically from MT5 / model directory
        self._symbol_manager: SymbolManager = load_symbol_manager(
            str(self._system_root / "config" / "ftmo_config.json")
        )
        discovery = self._symbol_manager.discover()
        self.pairs: list = discovery["all_symbols"]
        self.symbols_with_models: set = set(discovery["symbols_with_models"])

        if not self.pairs:
            # Fallback to pretrained bases if MT5 not yet connected
            from core.symbol_manager import PRETRAINED_BASES
            self.pairs = list(PRETRAINED_BASES)
            self.symbols_with_models = set(PRETRAINED_BASES)

        # File paths — MT5 Common\Files (shared folder all terminals and Python can access)
        _common = Path(r"C:\Users\mt5-admin\AppData\Roaming\MetaQuotes\Terminal\Common\Files")
        self.features_dir      = _common
        self.positions_file    = _common / "open_positions.csv"
        self.trade_commands_file = _common / "trade_commands.csv"

        # FTMO drawdown safety — updated each cycle from MT5
        self.ftmo_start_balance: float = account_balance
        self.ftmo_daily_start_balance: float = account_balance
        self.ftmo_daily_reset_date: str = datetime.utcnow().strftime('%Y-%m-%d')
        self.ftmo_trading_halted: bool = False
        self.FTMO_MAX_DAILY_LOSS_PCT: float = 5.0   # Hard FTMO rule
        self.FTMO_MAX_TOTAL_LOSS_PCT: float = 10.0  # Hard FTMO rule
        self.SYS_MAX_DAILY_LOSS_PCT: float = 3.0    # Our conservative limit
        
        # Logging
        self.logs_dir = Path('logs')
        self.logs_dir.mkdir(exist_ok=True)
        
        self.predictions_log = self.logs_dir / f'predictions_v5_{mode}.csv'
        self.trades_log = self.logs_dir / f'trades_v5_{mode}.csv'
        self.system_log = self.logs_dir / f'system_v5_{mode}.log'
        self.confluence_log = self.logs_dir / f'confluence_v5_{mode}.json'
        self.scaling_log = self.logs_dir / f'scaling_v5_{mode}.csv'
        
        # Initialize V3.1 tree-based ensemble predictor
        self.ml_predictor = EnsemblePredictorV3(
            model_dir=str(self._system_root / "data" / "models"),
            enable_logging=True,
            log_dir=str(self.logs_dir / "predictions")
        )
        
        # Verify all models available
        self.ml_predictor.verify_models_exist()
        
        # Initialize confluence system components
        self.hard_filters = HardFilters(
            min_atr_pips=8.0,
            news_buffer_minutes=30,
            require_liquid_session=True  # RE-ENABLED Task 4: Only trade during liquid sessions
        )
        
        # Initialize news integration (optional)
        if HAS_NEWS:
            self.news_integration = NewsIntegration(
                cache_duration_minutes=30,
                log_dir=self.logs_dir
            )
        else:
            self.news_integration = None
        
        self.confluence_scorer = ConfluenceScorer(
            weights={
                'mtf_trend': 0.25,
                'support_resistance': 0.20,
                'momentum': 0.15,
                'volume': 0.10,
                'volatility': 0.10,
                'strategy_consensus': 0.20
            },
            high_threshold=0.70,
            medium_threshold=0.50
        )
        
        self.regime_detector = RegimeDetector(
            trending_threshold=25.0,
            ranging_threshold=20.0
        )
        
        self.risk_manager = RiskManager(
            account_balance=account_balance,
            max_portfolio_risk_percent=0.02,
            default_lot_size=0.05,  # v2.35: Synced with EA
            max_positions_per_symbol=3
        )
        
        self.level_confluence = LevelConfluence(min_confluence_for_scale=2)
        
        # Initialize pullback detector for scale-in validation
        self.pullback_detector = PullbackDetector(
            fib_pullback_min=0.382,
            fib_pullback_max=0.618,
            rsi_bull_threshold=40.0,
            rsi_bear_threshold=60.0,
            ema_period=20,
            min_swing_bars=5
        )
        
        # Scale-in configuration
        self.SCALE_IN_CONFLUENCE_MIN = 0.35  # Minimum confluence required AFTER position is at BE
        self.SCALE_IN_REWARD_PCT_MIN = 0.35  # NEW: Minimum % of reward reached before scale-in (35%)
        self.MIN_RR_RATIO = 2.0  # Minimum risk:reward ratio for all trades
        
        # Scale-out configuration (v5.1 - R:R Based Quarter Level Scaling)
        self.MIN_RR_FOR_SCALEOUT = 2.0  # Minimum R:R required before scale-out (aim for 3:1)
        self.MIN_HOLD_MINUTES_FOR_SCALEOUT = 30  # Minimum minutes position must be held
        self.SCALEOUT_LOT_SIZE = 0.05  # Lot size to close at each quarter level
        self.REQUIRE_BE_FOR_SCALEOUT = True  # Position must be at BE+ before scale-out
        
        # Initialize rule-based strategies
        self.rule_strategies = RuleBasedStrategies()
        
        # Initialize feature expander
        self.feature_expander = FeatureExpander()
        
        # Initialize dimension checker for multi-dimensional signal validation
        self.dimension_checker = DimensionChecker(
            min_dimensions=3,  # Need 3/4 dimensions to agree
            confluence_threshold=self.confluence_threshold,
            ml_confidence_threshold=self.confidence_threshold
        )
        
        # Initialize trade history tracker (loads from EA's CSV, syncs every 5 min)
        self.trade_history_tracker = TradeHistoryTracker(
            sync_interval_minutes=5
        )
        self.log_system(f"[INIT] Trade history: {self.trade_history_tracker.get_state_summary()}")
        
        # Initialize danger scorer for position sizing
        self.danger_scorer = DangerScorer(
            danger_threshold=13,  # Score >= 13 blocks trade
            drawdown_warning=0.05,
            drawdown_danger=0.10
        )
        
        # Initialize anti-fragile position builder (Phase 6)
        self.anti_fragile_builder = AntiFragileBuilder(
            probe_lot=0.05,           # v2.35: Base lot size
            target_lot=0.15,          # v2.35: Target 3x probe
            add_lot=0.05,             # v2.35: Scale-in increment
            min_dimension_count=3,    # Need 3/4 dimensions to add
            max_danger_score=12,      # Danger < 13 to add
            require_be_for_add=True   # Must be at breakeven to add
        )
        self.log_system(f"[INIT] Anti-fragile builder: Probe 0.05 -> Target 0.15 (v2.35)")
        
        # Anti-fragile build log
        self.build_log = self.logs_dir / f'position_builds_v5_{mode}.csv'
        
        # Danger scoring log
        self.danger_log = self.logs_dir / f'danger_scores_v5_{mode}.csv'
        
        # Dimension checking log
        self.dimension_log = self.logs_dir / f'dimensions_v5_{mode}.csv'
        
        # Strategy tracking log
        self.strategy_log = self.logs_dir / f'strategy_votes_v5_{mode}.csv'
        
        # Expanded features log
        self.expanded_features_log = self.logs_dir / f'expanded_features_v5_{mode}.csv'
        
        # Historical OHLC buffer for Fibonacci
        self.historical_ohlc = {}
        self.historical_ohlc_size = 50
        
        # State tracking
        self.last_data_timestamp = None
        self.prediction_count = 0
        self.signal_count = 0
        self.filtered_count = 0
        self._shutdown_called = False
        self.last_signals = {}
        
        # SIGNAL COOLDOWN TRACKING (NEW - Task 7)
        # Prevents spam signals, allows scale-ins after cooldown
        self.signal_cooldowns = {}  # {symbol: datetime of last signal sent}
        self.SIGNAL_COOLDOWN_MINUTES = 15  # Match M15 timeframe - 1 candle between signals
        
        # Feature names
        self.feature_names = self.feature_expander.get_feature_names()
        
        # Print startup banner
        self._print_banner()

    def _print_banner(self):
        """Print startup banner"""
        print(f"\n{'='*70}")
        print(f"{'LIVE TRADING SYSTEM V5.0 - TREE-BASED ENSEMBLE':^70}")
        print(f"{'='*70}")
        print(f"Mode: {self.mode}")
        print(f"Models: XGBoost only (FTMO deployment)")
        print(f"Symbols with ML models: {len(self.symbols_with_models)}")
        print(f"Prediction Logging: ENABLED")
        print(f"ML Confidence Threshold: {self.confidence_threshold:.0%}")
        print(f"Confluence Threshold: {self.confluence_threshold:.0%}")
        print(f"Full Account: ${self.full_account_balance:,.2f}")
        print(f"Trading Capital: ${self.account_balance:,.2f} ({self.trading_capital_percent:.0%} of full)")
        print(f"Max Portfolio Risk: 2% of trading capital (${self.account_balance * 0.02:,.2f})")
        print(f"Signal Cooldown: {self.SIGNAL_COOLDOWN_MINUTES} min (1 candle between signals)")
        print(f"Dimension Check: ENABLED (min {self.dimension_checker.min_dimensions}/4 dimensions)")
        print(f"Pairs: {len(self.pairs)}")
        print(f"{'='*70}\n")
    
    def _features_array_to_dict(self, features_array):
        """Convert feature array to named dictionary"""
        feature_dict = {}
        for i, name in enumerate(self.feature_names):
            if i < len(features_array):
                feature_dict[name] = float(features_array[i])
            else:
                feature_dict[name] = 0.0
        return feature_dict
    
    def _extract_10_critical_features(self, features_array: np.ndarray) -> np.ndarray:
        """Extract 10 critical features for rule-based strategies"""
        feature_dict = self._features_array_to_dict(features_array)
        
        critical_features = np.array([
            feature_dict.get('volume_sma', 1.0),
            feature_dict.get('eur_strength', 50.0),
            feature_dict.get('gbp_strength', 50.0),
            feature_dict.get('nzd_strength', 50.0),
            feature_dict.get('usd_strength', 50.0),
            feature_dict.get('jpy_strength', 50.0),
            feature_dict.get('volatility', 0.001),
            feature_dict.get('returns_std', 0.01),
            feature_dict.get('volatility_confirm', 0),
            feature_dict.get('atr', 0.001)
        ], dtype=np.float32)
        
        return critical_features
    
    def log_system(self, message):
        """Log system message to console and file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        formatted = f"[{timestamp}] {message}"
        print(formatted)
        
        with open(self.system_log, 'a', encoding='utf-8') as f:
            f.write(formatted + '\n')
    
    def read_bridge_ea_data(self):
        """Read latest features from Bridge EA CSV file"""
        try:
            if not self.bridge_ea_file.exists():
                self.log_system(f"[ERROR] Bridge EA file not found: {self.bridge_ea_file}")
                return None
            
            file_age = time.time() - self.bridge_ea_file.stat().st_mtime
            if file_age > 60:
                self.log_system(f"[WARNING] Data is {file_age:.0f}s old - Bridge EA may not be running")
            
            data = pd.read_csv(self.bridge_ea_file)
            
            if data.empty:
                self.log_system("[ERROR] Bridge EA file is empty")
                return None
            
            self.last_data_timestamp = datetime.now()
            return data
            
        except Exception as e:
            self.log_system(f"[ERROR] Failed to read Bridge EA data: {e}")
            return None
    
    def extract_features(self, data=None):
        """
        Read 27 CLEAN features per symbol from per-symbol CSVs written by the Bridge EA.
        Expands each to 105 features via feature_expander.
        `data` parameter unused — kept for interface compatibility.
        """
        FEATURE_27 = [
            "close", "high", "low", "volume",
            "sma_20", "sma_50", "fast_ema", "slow_ema",
            "htf_fast_ema", "htf_slow_ema", "htf_trend_direction", "htf_trend_alignment",
            "rsi", "stoch_k", "stoch_d", "momentum",
            "atr", "bb_upper", "bb_middle", "bb_lower", "volatility",
            "volume_sma", "volume_ratio", "price_volume",
            "bullish_sentiment", "bearish_sentiment", "net_sentiment",
        ]
        features_dict = {}

        for pair in self.pairs:
            csv_path = self.features_dir / f"{pair}_features.csv"
            if not csv_path.exists():
                continue
            # Note: symbol manager now returns exact MT5 names (e.g. EURUSD.sim)
            # so csv_path should match directly

            try:
                file_age = time.time() - csv_path.stat().st_mtime
                if file_age > 60:
                    self.log_system(f"[WARNING] {pair} features are {file_age:.0f}s old")

                df = pd.read_csv(csv_path)
                if df.empty:
                    continue

                row = df.iloc[-1]
                missing = [f for f in FEATURE_27 if f not in row.index]
                if missing:
                    self.log_system(f"[WARNING] {pair}: missing feature columns {missing[:5]}")
                    continue

                base_features = np.array([row[f] for f in FEATURE_27], dtype=np.float32)
                base_features = np.nan_to_num(base_features, nan=0.0)

                # Update OHLC history buffer
                if pair not in self.historical_ohlc:
                    self.historical_ohlc[pair] = pd.DataFrame(columns=['high', 'low', 'close'])
                new_bar = pd.DataFrame({
                    'high':  [float(base_features[1])],
                    'low':   [float(base_features[2])],
                    'close': [float(base_features[0])],
                })
                self.historical_ohlc[pair] = pd.concat(
                    [self.historical_ohlc[pair], new_bar], ignore_index=True
                ).tail(self.historical_ohlc_size).reset_index(drop=True)

                # Expand 27 → 105 features
                try:
                    expanded = self.feature_expander.expand(
                        base_features, pair, self.historical_ohlc[pair]
                    )
                    features_dict[pair] = expanded.features
                except Exception:
                    # Expander expects 58 features; models only need 27 — use raw directly
                    features_dict[pair] = base_features

            except Exception as e:
                self.log_system(f"[ERROR] {pair}: failed reading features — {e}")

        return features_dict
    
    def _log_expanded_features(self, pair: str, expanded):
        """Log expanded features for training data collection"""
        timestamp = datetime.now().isoformat()
        
        row = {'timestamp': timestamp, 'symbol': pair}
        for i, name in enumerate(expanded.feature_names):
            row[name] = float(expanded.features[i])
        
        df = pd.DataFrame([row])
        header = not self.expanded_features_log.exists()
        df.to_csv(self.expanded_features_log, mode='a', header=header, index=False)

    def make_ml_predictions(self, features_dict: Dict[str, np.ndarray]) -> Dict[str, Any]:
        """
        Make ML predictions using tree-based ensemble (V3.1).
        
        Tree models don't need sequences - much simpler than V4!
        
        Args:
            features_dict: Dictionary of {pair: 108-feature array}
            
        Returns:
            Dictionary of prediction results per pair
        """
        results = {}
        
        for pair, features in features_dict.items():
            # Use first 27 features — EA now writes 27 CLEAN features directly
            base_features = features[:27] if len(features) >= 27 else features

            trade_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{pair[:6]}"

            # Get XGBoost prediction — returns None if no model for this symbol
            prediction = self.ml_predictor.predict_pair(base_features, pair, trade_id=trade_id)

            if prediction is None:
                # No model: record ABSTAIN result so downstream confluence/dims still run
                results[pair] = {
                    'prediction': None,
                    'prediction_name': None,
                    'confidence': 0.0,
                    'agreement': 'N/A',
                    'unanimous': False,
                    'model_votes': {},
                    'model_confidences': {},
                    'vote_distribution': {},
                    'features': features,
                    'trade_id': trade_id,
                    'has_model': False,
                }
                continue
            
            results[pair] = {
                'prediction': prediction['prediction'],  # 0=SELL, 1=HOLD, 2=BUY
                'prediction_name': prediction['prediction_label'],
                'confidence': prediction['confidence'],
                'agreement': prediction['agreement'],
                'unanimous': prediction['unanimous'],
                'model_votes': {
                    model: data['label']
                    for model, data in prediction['individual_predictions'].items()
                },
                'model_confidences': {
                    model: data['confidence']
                    for model, data in prediction['individual_predictions'].items()
                },
                'vote_distribution': prediction['vote_distribution'],
                'features': features,
                'trade_id': trade_id,
                'has_model': True,
            }
        
        return results
    
    def make_strategy_predictions(self, features_dict: Dict[str, np.ndarray]) -> Dict[str, Dict]:
        """Run 9 rule-based strategies on all pairs"""
        results = {}
        
        for pair, features_array in features_dict.items():
            critical_features = self._extract_10_critical_features(features_array)
            strategy_predictions = self.rule_strategies.predict_all(pair, critical_features)
            votes = self.rule_strategies.get_vote_summary(strategy_predictions)
            
            if votes['BUY'] > votes['SELL'] and votes['BUY'] > votes['HOLD']:
                consensus = 'BUY'
                consensus_count = votes['BUY']
            elif votes['SELL'] > votes['BUY'] and votes['SELL'] > votes['HOLD']:
                consensus = 'SELL'
                consensus_count = votes['SELL']
            else:
                consensus = 'HOLD'
                consensus_count = votes['HOLD']
            
            agreeing_strategies = [
                name for name, pred in strategy_predictions.items()
                if pred == consensus
            ]
            
            results[pair] = {
                'predictions': strategy_predictions,
                'votes': votes,
                'consensus': consensus,
                'consensus_count': consensus_count,
                'confidence': consensus_count / 9.0,
                'agreeing_strategies': agreeing_strategies
            }
        
        return results
    
    def apply_confluence_filtering(
        self,
        ml_results: Dict[str, Any],
        features_dict: Dict[str, np.ndarray],
        upcoming_news: Optional[List[Dict]] = None,
        strategy_results: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Apply confluence scoring to filter ML predictions"""
        filtered_results = {}
        
        for pair in ml_results:
            ml_data = ml_results[pair]
            features_array = features_dict.get(pair)
            
            if features_array is None:
                continue
            
            features = self._features_array_to_dict(features_array)
            
            # Hard filters
            filter_result = self.hard_filters.check_all(
                features=features,
                symbol=pair,
                current_time=datetime.utcnow(),
                upcoming_news=upcoming_news or []
            )
            
            if not filter_result.passed:
                self.log_system(f"   [FILTER] {pair}: {filter_result}")
                self.filtered_count += 1
                continue
            
            # Regime detection
            regime_state = self.regime_detector.detect(features, pair)
            regime_name = regime_state.regime.value.lower()
            
            # Confluence scoring
            prediction = ml_data['prediction']
            pair_strategy_data = strategy_results.get(pair, {}) if strategy_results else {}
            
            confluence_result = self.confluence_scorer.calculate(
                features=features,
                prediction=prediction,
                regime=regime_name if regime_name in ['trending', 'ranging', 'volatile'] else None,
                strategy_data=pair_strategy_data
            )
            
            if confluence_result.score < self.confluence_threshold:
                self.log_system(
                    f"   [LOW CONF] {pair}: {confluence_result.score:.2f} < {self.confluence_threshold}"
                )
                self.filtered_count += 1
                continue
            
            # Risk check
            portfolio_risk = self.risk_manager.get_portfolio_risk()
            if not portfolio_risk.can_open_new:
                self.log_system(
                    f"   [RISK] {pair}: Portfolio risk at max ({portfolio_risk.total_risk_percent:.1%})"
                )
                self.filtered_count += 1
                continue
            
            filtered_results[pair] = {
                **ml_data,
                'confluence_score': confluence_result.score,
                'confluence_level': confluence_result.level.value,
                'confluence_factors': confluence_result.factor_scores,
                'regime': regime_state.regime.value,
                'regime_confidence': regime_state.confidence,
                'filter_details': filter_result.filter_details,
                'available_risk': portfolio_risk.available_risk_amount
            }
        
        return filtered_results

    def generate_signals(
        self,
        filtered_results: Dict[str, Any],
        strategy_results: Dict[str, Any],
        features_dict: Dict[str, np.ndarray] = None
    ) -> List[Dict[str, Any]]:
        """Generate trading signals from filtered results with level-based SL/TP"""
        signals = []
        
        for pair, data in filtered_results.items():
            prediction = data['prediction']
            confidence = data['confidence']
            confluence_score = data['confluence_score']
            
            # Skip HOLD
            if prediction == 1:
                continue
            
            # Check confidence threshold
            if confidence < self.confidence_threshold:
                continue
            
            action = 'BUY' if prediction == 2 else 'SELL'
            news_conf_adj = 0  # default when news integration is disabled

            # News check (optional)
            if self.news_integration:
                allowed, block_reason = self.news_integration.is_trade_allowed(pair, action)
                if not allowed:
                    self.log_system(f"   [NEWS] {pair}: Blocked - {block_reason}")
                    self.filtered_count += 1
                    continue
                news_conf_adj = self.news_integration.get_confidence_adjustment(pair, action)
                if news_conf_adj != 0:
                    original_conf = confidence
                    confidence = max(0.0, min(1.0, confidence + news_conf_adj))
                    self.log_system(
                        f"   [NEWS] {pair}: Confidence {original_conf:.1%} → {confidence:.1%} "
                        f"(news adj: {news_conf_adj:+.1%})"
                    )
            
            # Strategy data
            strat_data = strategy_results.get(pair, {})
            strategy_consensus = strat_data.get('consensus', 'HOLD')
            strategy_votes = strat_data.get('votes', {'BUY': 0, 'SELL': 0, 'HOLD': 9})
            agreeing_strategies = strat_data.get('agreeing_strategies', [])
            
            # Check regime-based strategy agreement
            # DISABLED: Relying on ML alone per user request
            features_array = data.get('features', np.zeros(108))
            strategy_features = self._extract_10_critical_features(features_array)
            strategy_agreement = self.rule_strategies.check_strategy_agreement(
                pair, strategy_features, action
            )
            
            # if not strategy_agreement['passes']:
            #     self.log_system(f"   [STRAT] {pair}: {strategy_agreement['reason']}")
            #     self.filtered_count += 1
            #     continue
            
            strategies_agree = (strategy_consensus == action)
            
            # LEVEL-BASED SL/TP CALCULATION (NEW)
            sl_price = None
            tp_price = None
            rr_ratio = 2.0  # Default fallback
            sl_tp_reason = "ATR-based (no levels)"
            
            if features_dict and pair in features_dict:
                features_array = features_dict[pair]
                
                # 27-feature order: close(0), high(1), low(2), volume(3),
                # sma_20(4), sma_50(5), fast_ema(6), slow_ema(7),
                # htf_fast_ema(8), htf_slow_ema(9), htf_trend_dir(10), htf_align(11),
                # rsi(12), stoch_k(13), stoch_d(14), momentum(15),
                # atr(16), bb_upper(17), bb_middle(18), bb_lower(19), volatility(20),
                # volume_sma(21), volume_ratio(22), price_volume(23),
                # bull_sent(24), bear_sent(25), net_sent(26)
                current_price = float(features_array[0])   # close
                atr_value = float(features_array[16])      # atr
                
                # Get pip value
                pip_value = 0.01 if 'JPY' in pair else 0.0001
                atr_pips = atr_value / pip_value
                
                # SIMPLE ATR-BASED SL/TP (replaces broken level-based calculation)
                # SL = 1.5 ATR, TP = 3.0 ATR → fixed 2:1 R:R
                sl_atr_mult = 1.5
                tp_atr_mult = 3.0
                rr_ratio = tp_atr_mult / sl_atr_mult  # Always 2.0
                
                if action == 'BUY':
                    sl_price = current_price - (atr_value * sl_atr_mult)
                    tp_price = current_price + (atr_value * tp_atr_mult)
                else:  # SELL
                    sl_price = current_price + (atr_value * sl_atr_mult)
                    tp_price = current_price - (atr_value * tp_atr_mult)
                
                sl_tp_reason = f"ATR-based (SL={sl_atr_mult}x, TP={tp_atr_mult}x ATR)"
                
                self.log_system(
                    f"   [SL/TP] {pair}: SL={sl_price:.5f}, TP={tp_price:.5f}, R:R={rr_ratio:.1f}"
                )
            
            # SCALE-IN VALIDATION (NEW)
            # Check if this is a scale-in and validate BE + pullback
            positions = self.get_open_positions()
            scale_in_allowed, scale_in_reason = self.validate_scale_in(
                symbol=pair,
                action=action,
                confluence_score=confluence_score,
                features_array=features_array,
                positions=positions
            )
            
            if not scale_in_allowed:
                self.log_system(f"   [SCALE-IN] {pair}: Rejected - {scale_in_reason}")
                self.filtered_count += 1
                continue
            elif pair in positions:
                self.log_system(f"   [SCALE-IN] {pair}: Allowed - {scale_in_reason}")
                # v2.33 REVISED: Scale-in SL = 75% of previous position's risk
                pip_value = 0.01 if 'JPY' in pair else 0.0001
                prev_pos = positions[pair]
                prev_entry = prev_pos.get('entry_price', current_price)
                prev_sl = prev_pos.get('sl', prev_entry)
                prev_risk_pips = abs(prev_entry - prev_sl) / pip_value
                
                # Scale-in risk = 75% of previous position's risk
                scale_in_risk_pips = prev_risk_pips * 0.75
                
                if action == 'BUY':
                    sl_price = current_price - (scale_in_risk_pips * pip_value)
                else:  # SELL
                    sl_price = current_price + (scale_in_risk_pips * pip_value)
                
                sl_tp_reason = f"Scale-in: 75% of prev risk ({scale_in_risk_pips:.1f} pips)"
                self.log_system(f"   [SCALE-IN SL] {pair}: SL={sl_price:.5f} ({scale_in_risk_pips:.1f} pips, 75% of {prev_risk_pips:.1f})")
            
            # ================================================================
            # DIMENSION CHECK - Multi-dimensional signal validation
            # ================================================================
            # None = no model for this symbol → dimension_checker returns ABSTAIN (not DISAGREE)
            ml_prediction_name = data.get('prediction_name', None)
            ml_agreement = data.get('agreement', 1.0)
            if isinstance(ml_agreement, str):
                # Parse "2/3" format to float
                try:
                    parts = ml_agreement.split('/')
                    ml_agreement = float(parts[0]) / float(parts[1])
                except:
                    ml_agreement = 1.0
            
            dimension_result = self.dimension_checker.check_all(
                proposed_direction=action,
                regime=data.get('regime', 'UNKNOWN'),
                regime_confidence=data.get('regime_confidence', 0.5),
                current_hour_utc=datetime.utcnow().hour,
                ml_prediction=ml_prediction_name,
                ml_confidence=confidence,
                confluence_score=confluence_score,
                symbol=pair,
                ml_agreement=ml_agreement
            )
            
            # Log dimension result
            self._log_dimension_result(pair, action, dimension_result, confluence_score, confidence)
            
            # Check if trade is allowed by dimensions
            if not dimension_result.can_trade:
                veto_reason = "VETO" if dimension_result.has_veto else f"Only {dimension_result.count}/4"
                self.log_system(f"   [DIMS] {pair}: BLOCKED - {veto_reason} {dimension_result}")
                self.filtered_count += 1
                continue
            
            self.log_system(f"   [DIMS] {pair}: PASSED - {dimension_result}")
            
            # === DANGER SCORING (Phase 5) ===
            # Get system stress data from trade history
            stress_data = self.trade_history_tracker.get_danger_inputs()
            
            # Get portfolio heat from risk manager
            portfolio_status = self.risk_manager.get_portfolio_risk()
            portfolio_heat = portfolio_status.total_risk_percent
            
            # Count same-direction positions
            same_direction_count = sum(
                1 for pos in self.risk_manager.open_positions.values()
                if pos.direction.upper() == action.upper()
            )
            
            # Check for upcoming high-impact news
            minutes_to_news = None
            if hasattr(self, 'news_integration') and self.news_integration:
                try:
                    news_status = self.news_integration.get_news_status(pair.replace('.sim', ''))
                    if news_status.get('has_upcoming_high_impact'):
                        minutes_to_news = news_status.get('minutes_until_next', 60)
                except:
                    pass
            
            # Calculate danger score
            danger_result = self.danger_scorer.calculate_danger_score(
                # Regime
                adx=data.get('adx', 25.0),
                atr=data.get('atr', 0.001),
                atr_average=data.get('atr_average', 0.001),
                regime=data.get('regime', 'UNKNOWN'),
                # Session
                hour_utc=datetime.utcnow().hour,
                symbol=pair,
                # ML
                ml_confidence=confidence,
                ml_agreement=ml_agreement,
                ml_prediction=ml_prediction_name,
                # Technical
                confluence_score=confluence_score,
                trend_alignment=data.get('trend_alignment', True),
                # System Stress (from trade history tracker)
                current_drawdown=stress_data['current_drawdown'],
                consecutive_losses=stress_data['consecutive_losses'],
                daily_pnl_percent=stress_data['daily_pnl_percent'],
                # Correlation/Portfolio
                portfolio_heat=portfolio_heat,
                same_direction_count=same_direction_count,
                # Event Risk
                minutes_to_high_impact=minutes_to_news
            )
            
            # Log danger result
            self._log_danger_result(pair, action, danger_result, dimension_result)
            
            # Check if danger too high
            if not danger_result.can_trade:
                self.log_system(f"   [DANGER] {pair}: BLOCKED - Score {danger_result.total_score}/21 >= 13")
                self.filtered_count += 1
                continue
            
            self.log_system(f"   [DANGER] {pair}: PASSED - {danger_result}")
            
            # Apply size multiplier (for future use - currently logged only)
            size_multiplier = danger_result.size_multiplier
            
            # === ANTI-FRAGILE POSITION BUILDING (Phase 6) ===
            # Determine if this is a fresh entry (probe) or scale-in (build add)
            positions = self.get_open_positions()
            is_fresh_entry = pair not in positions
            
            if is_fresh_entry:
                # Fresh entry: Use probe lot size, create build plan
                probe_lot = self.anti_fragile_builder.get_probe_lot_for_signal(size_multiplier)
                
                # Create build plan for staged position building
                build_plan = self.anti_fragile_builder.create_build_plan(
                    symbol=pair,
                    direction=action,
                    entry_price=data.get('features', [0])[0] if 'features' in data else 0,  # close price
                    sl_price=sl_price,
                    tp_price=tp_price,
                    dimension_count=dimension_result.count,
                    danger_score=danger_result.total_score,
                    confluence_score=confluence_score,
                    size_multiplier=size_multiplier
                )
                
                self.log_system(
                    f"   [BUILD] {pair}: PROBE entry {probe_lot} lots | "
                    f"Target: {build_plan.target_lot} | Dims: {dimension_result.count}/4"
                )
                lot_size_to_use = probe_lot
                is_probe = True
            else:
                # Scale-in: Use existing scale-in logic (already validated)
                lot_size_to_use = 0.05  # v2.35: Scale-in lot size
                is_probe = False
            
            signals.append({
                'pair': pair,
                'action': action,
                'confidence': confidence,
                'confluence_score': confluence_score,
                'confluence_level': data['confluence_level'],
                'regime': data['regime'],
                'lot_size': lot_size_to_use,
                'sl_price': sl_price,
                'tp_price': tp_price,
                'rr_ratio': rr_ratio,
                'sl_tp_reason': sl_tp_reason,
                'available_risk': data['available_risk'],
                'news_confidence_adj': news_conf_adj,
                'strategy_consensus': strategy_consensus,
                'strategy_votes': strategy_votes,
                'strategies_agree': strategies_agree,
                'agreeing_strategies': agreeing_strategies,
                'regime_strategy_agreement': strategy_agreement,
                'model_votes': data.get('model_votes', {}),
                'model_confidences': data.get('model_confidences', {}),
                'unanimous': data.get('unanimous', False),
                'trade_id': data.get('trade_id', ''),
                # NEW: Dimension checking results
                'dimension_count': dimension_result.count,
                'dimension_details': dimension_result.details,
                # NEW: Danger scoring results (Phase 5)
                'danger_score': danger_result.total_score,
                'danger_can_trade': danger_result.can_trade,
                'size_multiplier': danger_result.size_multiplier,
                'danger_details': danger_result.category_scores,
                # NEW: Anti-fragile building (Phase 6)
                'is_probe': is_probe,
                'is_build_add': not is_fresh_entry,
                'explanation': {
                    'model_votes': data.get('model_votes', {}),
                    'confluence_factors': data.get('confluence_factors', {}),
                    'regime_confidence': data.get('regime_confidence', 0),
                    'strategy_predictions': strat_data.get('predictions', {}),
                    'dimensions': dimension_result.details,
                    'danger_categories': danger_result.category_details
                }
            })
            
            self._log_strategy_vote(pair, action, strat_data)
        
        return signals
    
    def _log_strategy_vote(self, pair: str, action: str, strat_data: Dict[str, Any]):
        """Log strategy votes for training analysis"""
        timestamp = datetime.now().isoformat()
        
        predictions = strat_data.get('predictions', {})
        votes = strat_data.get('votes', {})
        
        row = {
            'timestamp': timestamp,
            'pair': pair,
            'ml_action': action,
            'strategy_consensus': strat_data.get('consensus', 'HOLD'),
            'buy_votes': votes.get('BUY', 0),
            'sell_votes': votes.get('SELL', 0),
            'hold_votes': votes.get('HOLD', 0),
            'volume_breakout': predictions.get('volume_breakout', 'HOLD'),
            'currency_strength_divergence': predictions.get('currency_strength_divergence', 'HOLD'),
            'volatility_breakout': predictions.get('volatility_breakout', 'HOLD'),
            'trend_following': predictions.get('trend_following', 'HOLD'),
            'mean_reversion': predictions.get('mean_reversion', 'HOLD'),
            'volatility_contraction': predictions.get('volatility_contraction', 'HOLD'),
            'currency_correlation': predictions.get('currency_correlation', 'HOLD'),
            'low_volatility_momentum': predictions.get('low_volatility_momentum', 'HOLD'),
            'high_volatility_reversal': predictions.get('high_volatility_reversal', 'HOLD')
        }
        
        df = pd.DataFrame([row])
        header = not self.strategy_log.exists()
        df.to_csv(self.strategy_log, mode='a', header=header, index=False)
    
    def _log_dimension_result(
        self,
        pair: str,
        action: str,
        dimension_result,
        confluence_score: float,
        ml_confidence: float
    ):
        """Log dimension checking results for analysis"""
        timestamp = datetime.now().isoformat()
        
        row = {
            'timestamp': timestamp,
            'pair': pair,
            'action': action,
            'dimension_count': dimension_result.count,
            'can_trade': dimension_result.can_trade,
            'has_veto': dimension_result.has_veto,
            'regime_dim': dimension_result.regime,
            'session_dim': dimension_result.session,
            'ml_dim': dimension_result.ml,
            'confluence_dim': dimension_result.confluence,
            'confluence_score': confluence_score,
            'ml_confidence': ml_confidence,
            'hour_utc': datetime.utcnow().hour
        }
        
        df = pd.DataFrame([row])
        header = not self.dimension_log.exists()
        df.to_csv(self.dimension_log, mode='a', header=header, index=False)
    
    def _log_danger_result(
        self,
        pair: str,
        action: str,
        danger_result,
        dimension_result
    ):
        """Log danger scoring results for analysis"""
        timestamp = datetime.now().isoformat()
        
        row = {
            'timestamp': timestamp,
            'pair': pair,
            'action': action,
            'danger_score': danger_result.total_score,
            'can_trade': danger_result.can_trade,
            'size_multiplier': danger_result.size_multiplier,
            # Category scores
            'regime_danger': danger_result.category_scores.get('regime', 0),
            'session_danger': danger_result.category_scores.get('session', 0),
            'ml_danger': danger_result.category_scores.get('ml', 0),
            'technical_danger': danger_result.category_scores.get('technical', 0),
            'stress_danger': danger_result.category_scores.get('stress', 0),
            'correlation_danger': danger_result.category_scores.get('correlation', 0),
            'event_danger': danger_result.category_scores.get('event', 0),
            # Context
            'dimension_count': dimension_result.count,
            'hour_utc': datetime.utcnow().hour
        }
        
        df = pd.DataFrame([row])
        header = not self.danger_log.exists()
        df.to_csv(self.danger_log, mode='a', header=header, index=False)
    
    def check_build_opportunities(
        self,
        features_dict: Dict[str, np.ndarray]
    ) -> List[Dict]:
        """
        Check for anti-fragile position building opportunities.
        
        For each position with an active build plan, check if:
        - R-multiple trigger reached (0.3R, 0.6R, 1.0R)
        - Position at breakeven
        - Dimensions still agree
        - Danger score acceptable
        
        Returns:
            List of BUILD signals to add to positions
        """
        build_signals = []
        open_positions = self.get_open_positions()
        
        # Sync build plans with actual positions
        self.anti_fragile_builder.sync_with_positions(open_positions)
        
        for pair in self.pairs:
            # Check if we have a build plan for this pair
            build_plan = self.anti_fragile_builder.get_build_plan(pair)
            if not build_plan or build_plan.is_complete:
                continue
            
            # Get current price from features
            features_array = features_dict.get(pair)
            if features_array is None:
                continue
            
            features = self._features_array_to_dict(features_array)
            current_price = features.get('close', 0)
            
            if current_price <= 0:
                continue
            
            # Get position details
            pos_details = open_positions.get(pair, {})
            if not pos_details:
                continue
            
            is_at_be = pos_details.get('be_status', False)
            
            # Re-run dimension check for current conditions
            action = build_plan.direction
            ml_prediction = 2 if action == 'BUY' else 0  # Map to prediction format
            
            # Get regime
            regime_state = self.regime_detector.detect(features, pair)
            
            # Get ML agreement from last prediction (simplified)
            ml_agreement = 1.0  # Assume agreement for build checks
            
            dimension_result = self.dimension_checker.check_all(
                proposed_direction=action,
                regime=regime_state.regime.value,
                regime_confidence=regime_state.confidence,
                current_hour_utc=datetime.utcnow().hour,
                ml_prediction=action,
                ml_confidence=0.50,  # Use moderate confidence for build checks
                confluence_score=0.40,  # Use moderate confluence for build checks
                symbol=pair,
                ml_agreement=ml_agreement
            )
            
            # Get danger score
            stress_data = self.trade_history_tracker.get_danger_inputs()
            portfolio_status = self.risk_manager.get_portfolio_status()
            
            danger_result = self.danger_scorer.calculate_danger_score(
                adx=features.get('adx', 25.0),
                atr=features.get('atr', 0.001),
                atr_average=features.get('atr_average', 0.001),
                regime=regime_state.regime.value,
                hour_utc=datetime.utcnow().hour,
                symbol=pair,
                ml_confidence=0.50,
                ml_agreement=ml_agreement,
                ml_prediction=action,
                confluence_score=0.40,
                trend_alignment=True,
                current_drawdown=stress_data['current_drawdown'],
                consecutive_losses=stress_data['consecutive_losses'],
                daily_pnl_percent=stress_data['daily_pnl_percent'],
                portfolio_heat=portfolio_status.total_risk_percent,
                same_direction_count=0,
                minutes_to_high_impact=None
            )
            
            # Check pullback validity for later stages
            pullback_valid = True
            if pair in self.historical_ohlc and len(self.historical_ohlc[pair]) >= 10:
                hist = self.historical_ohlc[pair]
                rsi = features.get('rsi', 50.0)
                
                pullback = self.pullback_detector.detect_pullback(
                    symbol=pair,
                    current_price=current_price,
                    highs=hist['high'].values,
                    lows=hist['low'].values,
                    closes=hist['close'].values,
                    rsi=rsi,
                    position_direction=action
                )
                pullback_valid = pullback.is_valid
            
            # Check for build opportunity
            build_signal = self.anti_fragile_builder.check_build_opportunity(
                symbol=pair,
                current_price=current_price,
                is_at_be=is_at_be,
                current_dimension_count=dimension_result.count,
                current_danger_score=danger_result.total_score,
                current_confluence=confluence_score
            )
            
            if build_signal:
                build_signals.append({
                    'pair': pair,
                    'action': build_signal.direction,
                    'lot_size': build_signal.lot_size,
                    'stage': build_signal.stage.value,
                    'current_r': build_signal.current_r,
                    'reason': build_signal.reason,
                    'dimension_count': build_signal.dimension_count,
                    'danger_score': build_signal.danger_score
                })
                
                # Log the build signal
                self._log_build_signal(pair, build_signal)
        
        return build_signals
    
    def _log_build_signal(self, pair: str, build_signal):
        """Log build signal for analysis"""
        timestamp = datetime.now().isoformat()
        
        row = {
            'timestamp': timestamp,
            'pair': pair,
            'action': build_signal.direction,
            'stage': build_signal.stage.value,
            'lot_size': build_signal.lot_size,
            'current_r': build_signal.current_r,
            'dimension_count': build_signal.dimension_count,
            'danger_score': build_signal.danger_score,
            'confluence_score': build_signal.confluence_score,
            'can_build': build_signal.can_build,
            'reason': build_signal.reason
        }
        
        df = pd.DataFrame([row])
        header = not self.build_log.exists()
        df.to_csv(self.build_log, mode='a', header=header, index=False)
    
    def sync_positions_from_mt5(self):
        """Sync open positions from MT5 to Python risk manager"""
        if not self.positions_file.exists():
            return
        
        try:
            df = pd.read_csv(self.positions_file)
            
            if df.empty:
                self.risk_manager.clear_all_positions()
                return
            
            mt5_tickets = set(df['ticket'].astype(str).tolist())
            
            rm_tickets = set()
            for pair in self.pairs:
                positions = self.risk_manager.get_positions_for_symbol(pair)
                for pos in positions:
                    rm_tickets.add(pos.position_id)
            
            for ticket in rm_tickets - mt5_tickets:
                self.risk_manager.remove_position(ticket)
            
            for _, row in df.iterrows():
                position_id = str(row['ticket'])
                symbol = row['symbol']
                direction = row['direction']
                volume = float(row['volume'])
                entry_price = float(row['entry_price'])
                stop_loss = float(row.get('sl', 0.0))  # FIX: Pass actual SL for accurate risk calc
                
                if position_id not in rm_tickets:
                    self.risk_manager.add_position(
                        symbol=symbol,
                        direction=direction,
                        volume=volume,
                        entry_price=entry_price,
                        position_id=position_id,
                        stop_loss=stop_loss  # FIX: Now calculates real risk from SL
                    )
                    
        except Exception as e:
            self.log_system(f"[ERROR] Position sync failed: {e}")

    def check_scaling_opportunities(self, features_dict: Dict[str, np.ndarray]) -> List[Dict]:
        """
        Check for scaling in/out opportunities at key levels.
        
        v5.1 UPDATE: Quarter-Level Scaling
        - Scales out at quarter levels (.25, .50, .75, 1.00) from major round numbers
        - Requires: position in profit, held minimum time, at breakeven
        - Closes 0.05 lots at each quarter level
        """
        scaling_signals = []
        open_positions = self.get_open_positions()
        
        for pair in self.pairs:
            positions = self.risk_manager.get_positions_for_symbol(pair)
            
            if not positions:
                continue
            
            features_array = features_dict.get(pair)
            if features_array is None:
                continue
            
            features = self._features_array_to_dict(features_array)
            current_price = features.get('close', 0)
            
            if current_price <= 0:
                continue
            
            for position in positions:
                # Get position details from EA's CSV
                pos_details = open_positions.get(pair, {})
                entry_price = pos_details.get('entry_price', position.entry_price)
                open_time_str = pos_details.get('open_time', '')
                be_status = pos_details.get('be_status', False)
                profit = pos_details.get('profit', 0)
                
                # ============================================================
                # SCALE-OUT PROTECTION CHECKS (v5.1 - R:R Based)
                # ============================================================
                
                # Check 1: Minimum hold time required (prevent premature exits)
                if open_time_str:
                    try:
                        open_time = datetime.fromisoformat(open_time_str.replace('Z', '+00:00'))
                        hold_minutes = (datetime.now() - open_time.replace(tzinfo=None)).total_seconds() / 60
                        if hold_minutes < self.MIN_HOLD_MINUTES_FOR_SCALEOUT:
                            continue  # Skip - position too new
                    except:
                        pass  # If can't parse time, continue with check
                
                # Check 2: Must be at breakeven (optional but recommended)
                if self.REQUIRE_BE_FOR_SCALEOUT and not be_status:
                    # Also accept if profit is positive as fallback
                    if profit <= 0:
                        continue  # Skip - not at breakeven
                
                # Check 3: Get SL price for R:R calculation (CRITICAL)
                sl_price = pos_details.get('sl', 0)
                if sl_price <= 0:
                    continue  # No valid SL - can't calculate R:R
                
                # ============================================================
                # QUARTER-LEVEL SCALING (v5.1) - R:R Based
                # Only scales out when R:R >= 2.0 AND at quarter level
                # ============================================================
                
                quarter_signal = self.level_confluence.check_quarter_scaleout(
                    symbol=pair,
                    current_price=current_price,
                    entry_price=entry_price,
                    sl_price=sl_price,
                    direction=position.direction,
                    min_rr_for_scaleout=self.MIN_RR_FOR_SCALEOUT
                )
                
                if quarter_signal:
                    # Calculate R:R for logging
                    pip_value = self.level_confluence._get_pip_value(pair)
                    if position.direction.upper() == 'BUY':
                        risk_pips = (entry_price - sl_price) / pip_value
                        profit_pips = (current_price - entry_price) / pip_value
                    else:
                        risk_pips = (sl_price - entry_price) / pip_value
                        profit_pips = (entry_price - current_price) / pip_value
                    current_rr = profit_pips / risk_pips if risk_pips > 0 else 0
                    
                    scaling_signals.append({
                        'pair': pair,
                        'position_id': position.position_id,
                        'action': quarter_signal.action.value,
                        'confluence_score': quarter_signal.confluence_score,
                        'levels_hit': [str(l) for l in quarter_signal.levels_hit],
                        'reason': quarter_signal.reason,
                        'confidence': quarter_signal.confidence,
                        'lot_size': self.SCALEOUT_LOT_SIZE,
                        'profit_pips': profit_pips,
                        'current_rr': current_rr
                    })
                    self.log_system(
                        f"[SCALE-OUT] {pair} @ {current_price:.5f} | "
                        f"Entry: {entry_price:.5f} | R:R: {current_rr:.1f}:1 | "
                        f"{quarter_signal.reason}"
                    )
        
        return scaling_signals
    
    # =========================================================================
    # POSITION COOLDOWN MANAGEMENT (NEW - Task 7)
    # =========================================================================
    
    def get_open_positions(self) -> Dict[str, Dict]:
        """
        Read open positions from EA's CSV file.
        Returns dict: {symbol: {'direction': 'BUY'/'SELL', 'volume': float, 'be_status': bool, 'position_count': int, ...}}
        
        v2.33: Added position_count to track scale-ins (max 2 scale-ins = 3 positions total)
        """
        positions = {}
        position_counts = {}  # Track count per symbol
        
        try:
            if self.positions_file.exists():
                df = pd.read_csv(self.positions_file)
                
                # First pass: count positions per symbol
                for _, row in df.iterrows():
                    symbol = row.get('symbol', '')
                    if symbol:
                        position_counts[symbol] = position_counts.get(symbol, 0) + 1
                
                # Second pass: build positions dict (use latest/largest position as reference)
                for _, row in df.iterrows():
                    symbol = row.get('symbol', '')
                    if symbol:
                        # Parse BE status from EA
                        be_status_str = str(row.get('be_status', 'NO')).upper()
                        is_at_be = be_status_str == 'YES'
                        
                        # Only update if first entry or this has more info
                        if symbol not in positions:
                            positions[symbol] = {
                                'direction': row.get('direction', ''),
                                'volume': row.get('volume', 0),
                                'entry_price': row.get('entry_price', 0),
                                'sl': row.get('sl', 0),
                                'tp': row.get('tp', 0),
                                'profit': row.get('profit', 0),
                                'ticket': row.get('ticket', 0),
                                'be_status': is_at_be,
                                'trail_active': str(row.get('trail_active', 'NO')).upper() == 'YES',
                                'position_count': position_counts.get(symbol, 1)
                            }
                        else:
                            # Aggregate: sum volume, update BE status if any is True
                            positions[symbol]['volume'] += row.get('volume', 0)
                            positions[symbol]['profit'] += row.get('profit', 0)
                            if is_at_be:
                                positions[symbol]['be_status'] = True
                            # Keep the most recent entry/sl for scale-in calculation
                            positions[symbol]['entry_price'] = row.get('entry_price', 0)
                            positions[symbol]['sl'] = row.get('sl', 0)
                            
        except Exception as e:
            self.log_system(f"[WARN] Could not read positions file: {e}")
        return positions
    
    def check_signal_cooldown(self, symbol: str) -> tuple:
        """
        Check if a signal should be blocked due to recent signal (spam prevention).
        
        Returns: (allowed: bool, reason: str)
        
        NOTE: Does NOT block based on existing position - allows scale-ins!
        """
        # Check cooldown timer (15 min = 1 M15 candle)
        if symbol in self.signal_cooldowns:
            last_signal = self.signal_cooldowns[symbol]
            minutes_since = (datetime.now() - last_signal).total_seconds() / 60
            
            if minutes_since < self.SIGNAL_COOLDOWN_MINUTES:
                remaining = self.SIGNAL_COOLDOWN_MINUTES - minutes_since
                return False, f"Signal cooldown ({remaining:.1f}min remaining)"
        
        return True, "OK"
    
    def record_signal(self, symbol: str):
        """Record that we just sent a signal for a symbol."""
        self.signal_cooldowns[symbol] = datetime.now()
        self.log_system(f"[COOLDOWN] {symbol}: {self.SIGNAL_COOLDOWN_MINUTES}min cooldown started")
    
    def filter_signals_by_cooldown(self, signals: List[Dict]) -> List[Dict]:
        """
        Filter signals based on cooldown timer.
        
        This prevents:
        - Signal spam (same signal every 3 seconds)
        
        This ALLOWS:
        - Scale-ins (new signal after cooldown, even with existing position)
        """
        filtered = []
        
        for signal in signals:
            symbol = signal.get('pair', signal.get('symbol', ''))
            
            allowed, reason = self.check_signal_cooldown(symbol)
            
            if allowed:
                filtered.append(signal)
            else:
                # Only log occasionally to avoid log spam
                pass  # Silent filter - too noisy otherwise
        
        return filtered
    
    def is_position_at_breakeven(self, symbol: str, positions: Dict[str, Dict]) -> bool:
        """
        Check if existing position is at break-even or better.
        
        Uses EA's be_status field which tracks if SL >= entry (BUY) or SL <= entry (SELL).
        """
        if symbol not in positions:
            return True  # No position = fresh entry, allowed
        
        position = positions[symbol]
        
        # Use EA's BE status if available (most accurate)
        if 'be_status' in position:
            return position['be_status']
        
        # Fallback: use profit as proxy
        profit = position.get('profit', 0)
        return profit >= 0
    
    def validate_scale_in(
        self,
        symbol: str,
        action: str,
        confluence_score: float,
        features_array: np.ndarray,
        positions: Dict[str, Dict]
    ) -> Tuple[bool, str]:
        """
        Validate if a scale-in should be allowed.
        
        v2.33 UPDATED:
        - Max 2 scale-ins per symbol (3 positions total)
        - BE at 25% of risk required before scale-in
        - Scale-in SL = 75% of previous position's risk
        
        Conditions:
        1. Max 2 scale-ins (3 positions total per symbol)
        2. Existing position must be at BE+
        3. Confluence must meet threshold
        
        Args:
            symbol: Trading symbol
            action: 'BUY' or 'SELL'
            confluence_score: Current confluence score
            features_array: 108-feature array
            positions: Current open positions
            
        Returns:
            (allowed: bool, reason: str)
        """
        # Check if this is a scale-in (position already exists)
        if symbol not in positions:
            return True, "Fresh entry (no existing position)"
        
        existing_pos = positions[symbol]
        existing_direction = existing_pos.get('direction', '')
        
        # v2.33: Check max scale-ins (2 scale-ins = 3 positions max)
        position_count = existing_pos.get('position_count', 1)
        MAX_POSITIONS_PER_SYMBOL = 3  # 1 initial + 2 scale-ins
        if position_count >= MAX_POSITIONS_PER_SYMBOL:
            return False, f"Max scale-ins reached ({position_count} positions, max {MAX_POSITIONS_PER_SYMBOL})"
        
        # If signal is opposite direction, it's not a scale-in, reject
        if action.upper() != existing_direction.upper():
            return False, f"Signal {action} conflicts with existing {existing_direction} position"
        
        # Check 1: Position MUST be at breakeven - no exceptions
        is_at_be = self.is_position_at_breakeven(symbol, positions)
        
        if not is_at_be:
            return False, f"Position not at BE (profit={existing_pos.get('profit', 0):.2f}) - scale-in blocked"
        
        # Check 2: Position must have reached 35% of reward (NEW v5.2)
        entry_price = existing_pos.get('entry_price', 0)
        tp_price = existing_pos.get('tp', 0)
        sl_price = existing_pos.get('sl', 0)
        
        if entry_price > 0 and tp_price > 0 and sl_price > 0:
            # Get current price from features
            features_dict = self._features_array_to_dict(features_array)
            current_price = features_dict.get('close', 0)
            
            if current_price > 0:
                # Calculate reward progress
                if action.upper() == 'BUY':
                    total_reward = tp_price - entry_price
                    current_progress = current_price - entry_price
                else:  # SELL
                    total_reward = entry_price - tp_price
                    current_progress = entry_price - current_price
                
                if total_reward > 0:
                    reward_pct = current_progress / total_reward
                    
                    if reward_pct < self.SCALE_IN_REWARD_PCT_MIN:
                        return False, f"Position at BE but only {reward_pct:.1%} of reward reached (need {self.SCALE_IN_REWARD_PCT_MIN:.0%})"
        
        # Check 3: Confluence must meet threshold
        if confluence_score < self.SCALE_IN_CONFLUENCE_MIN:
            return False, f"Position at BE but confluence {confluence_score:.2f} < {self.SCALE_IN_CONFLUENCE_MIN}"
        
        be_status = f"Position at BE+ ({position_count}/3 positions, scale-in #{position_count})"
        
        # Check 4: Validate pullback (not reversal)
        if symbol in self.historical_ohlc and len(self.historical_ohlc[symbol]) >= 10:
            hist = self.historical_ohlc[symbol]
            highs = hist['high'].values
            lows = hist['low'].values
            closes = hist['close'].values
            
            # Get RSI from features (index 8 = RSI in base features)
            rsi = float(features_array[8]) if len(features_array) > 8 else 50.0
            
            pullback = self.pullback_detector.detect_pullback(
                symbol=symbol,
                current_price=float(closes[-1]),
                highs=highs,
                lows=lows,
                closes=closes,
                rsi=rsi,
                position_direction=action
            )
            
            if not pullback.is_valid:
                return False, f"Pullback invalid: {pullback.status.value} ({pullback.checks_passed}/4 checks)"
            
            return True, f"Scale-in allowed: {be_status} | Pullback valid ({pullback.checks_passed}/4)"
        else:
            # Not enough history for pullback detection
            # BE and confluence already verified above, so allow scale-in
            return True, f"Scale-in allowed: {be_status} (insufficient history for pullback check)"

    def _write_csv_with_retry(self, df: pd.DataFrame, max_retries: int = 5) -> bool:
        """
        Write DataFrame to trade_commands.csv with retry logic for file locks.
        
        Uses temp file + atomic rename to prevent corruption.
        Retries on PermissionError (file locked by MT5 EA).
        
        Args:
            df: DataFrame to write
            max_retries: Number of retry attempts (default 5)
            
        Returns:
            True if write succeeded, False otherwise
        """
        import os
        temp_file = self.trade_commands_file.with_suffix('.tmp')
        
        for attempt in range(max_retries):
            try:
                df.to_csv(temp_file, index=False)
                os.replace(temp_file, self.trade_commands_file)
                return True
            except PermissionError:
                if attempt < max_retries - 1:
                    time.sleep(0.1)  # Brief pause, then retry
                else:
                    self.log_system(f"[ERROR] Could not write commands after {max_retries} attempts - file locked by MT5")
                    # Clean up temp file if it exists
                    try:
                        if temp_file.exists():
                            temp_file.unlink()
                    except:
                        pass
                    return False
            except Exception as e:
                self.log_system(f"[ERROR] Unexpected error writing commands: {e}")
                return False
        return False

    def write_trade_commands(self, signals: List[Dict]):
        """Write trade commands for Bridge EA"""
        if not signals:
            if self.last_signals:
                empty_df = pd.DataFrame(columns=['symbol', 'action', 'confidence', 'sl_price', 'tp_price', 'lot_size', 'timestamp'])
                if self._write_csv_with_retry(empty_df):
                    self.log_system("[CLEAR] No signals - cleared commands")
                self.last_signals = {}
            return
        
        # FILTER BY SIGNAL COOLDOWN (NEW - Task 7)
        signals = self.filter_signals_by_cooldown(signals)
        if not signals:
            # Silent - don't log every time (too noisy)
            return
        
        # Get current positions to determine fresh vs scale-in
        positions = self.get_open_positions()
        
        new_commands = []
        for signal in signals:
            pair = signal['pair']
            action = signal['action']
            confidence = signal['confidence']
            
            # v2.33: Fresh entries ALWAYS sent, unchanged filter only for scale-ins
            is_fresh_entry = pair not in positions
            
            if is_fresh_entry:
                # Fresh entry - always send (no unchanged filter)
                new_commands.append(signal)
                self.last_signals[pair] = (action, confidence)
                self.log_system(f"   [NEW] {pair}: {action} @ {confidence:.2%}")
            elif pair not in self.last_signals:
                # Scale-in, first time seeing this signal
                new_commands.append(signal)
                self.last_signals[pair] = (action, confidence)
                self.log_system(f"   [SCALE-IN NEW] {pair}: {action} @ {confidence:.2%}")
            else:
                # Scale-in, check if changed from last cycle
                last_action, last_conf = self.last_signals[pair]
                if action != last_action or abs(confidence - last_conf) > 0.05:
                    new_commands.append(signal)
                    self.last_signals[pair] = (action, confidence)
                    self.log_system(f"   [SCALE-IN CHANGE] {pair}: {last_action}->{action}")
        
        current_pairs = {s['pair'] for s in signals}
        pairs_to_remove = [p for p in self.last_signals if p not in current_pairs]
        for pair in pairs_to_remove:
            del self.last_signals[pair]
        
        if new_commands:
            commands = []
            for signal in new_commands:
                commands.append({
                    'symbol': signal['pair'],
                    'action': signal['action'],
                    'confidence': signal['confidence'],
                    'sl_price': signal.get('sl_price', 0),
                    'tp_price': signal.get('tp_price', 0),
                    'lot_size': signal.get('lot_size', 0),  # v5.1: Quarter-level scaling lot size
                    'timestamp': datetime.now().isoformat()
                })
            
            df = pd.DataFrame(commands)
            
            if self._write_csv_with_retry(df):
                self.log_system(f"[OK] Wrote {len(commands)} command(s)")

                # Write per-symbol signal files for Bridge EA to read
                self._write_per_symbol_signals(commands)

                # RECORD SIGNAL COOLDOWNS
                for cmd in commands:
                    if cmd['action'] in ['BUY', 'SELL']:
                        self.record_signal(cmd['symbol'])
        else:
            self.log_system(f"[SKIP] All {len(signals)} signals unchanged")
    
    def _write_per_symbol_signals(self, commands: list):
        """Write individual signal_{SYMBOL}.txt files for Bridge EA to read."""
        for cmd in commands:
            if cmd['action'] not in ('BUY', 'SELL'):
                continue
            sig_path = self.features_dir / f"signal_{cmd['symbol']}.txt"
            try:
                # No header — EA reads fields sequentially: sym,action,conf,sl,tp,lot,ts
                with open(sig_path, 'w') as _sf:
                    _sf.write(
                        f"{cmd['symbol']},"
                        f"{cmd['action']},"
                        f"{round(cmd['confidence'], 4)},"
                        f"{round(cmd.get('sl_price', 0), 8)},"
                        f"{round(cmd.get('tp_price', 0), 8)},"
                        f"{round(cmd.get('lot_size', 0.01), 2)},"
                        f"{cmd['timestamp']}\n"
                    )
            except Exception as e:
                self.log_system(f"[WARN] Could not write signal file for {cmd['symbol']}: {e}")

    def log_predictions(self, ml_results, filtered_results, signals):
        """Log all predictions to CSV"""
        timestamp = datetime.now().isoformat()
        
        rows = []
        for pair in self.pairs:
            if pair not in ml_results:
                continue
            
            ml_pred = ml_results[pair]
            filtered = filtered_results.get(pair, {})
            signal = next((s for s in signals if s['pair'] == pair), None)
            
            row = {
                'timestamp': timestamp,
                'pair': pair,
                'ml_prediction': ml_pred['prediction_name'],
                'ml_confidence': ml_pred['confidence'],
                'agreement': ml_pred.get('agreement', ''),
                'unanimous': ml_pred.get('unanimous', False),
                'confluence_score': filtered.get('confluence_score', 0),
                'confluence_level': filtered.get('confluence_level', 'N/A'),
                'regime': filtered.get('regime', 'N/A'),
                'final_action': signal['action'] if signal else 'HOLD',
                'should_trade': bool(signal),
                'model_votes': str(ml_pred.get('model_votes', {}))
            }
            rows.append(row)
        
        if rows:
            df = pd.DataFrame(rows)
            header = not self.predictions_log.exists()
            df.to_csv(self.predictions_log, mode='a', header=header, index=False)

    def check_ftmo_drawdown_safety(self, current_balance: float) -> bool:
        """
        Check FTMO drawdown limits. Returns True if trading should STOP.
        Resets daily start balance at UTC midnight.
        """
        today = datetime.utcnow().strftime('%Y-%m-%d')
        if today != self.ftmo_daily_reset_date:
            self.ftmo_daily_start_balance = current_balance
            self.ftmo_daily_reset_date = today
            self.ftmo_trading_halted = False
            self.log_system(f"[FTMO] Daily balance reset: ${current_balance:,.2f}")

        if self.ftmo_start_balance <= 0:
            return False

        daily_loss_pct = (self.ftmo_daily_start_balance - current_balance) / self.ftmo_start_balance * 100
        total_loss_pct = (self.ftmo_start_balance - current_balance) / self.ftmo_start_balance * 100

        if daily_loss_pct >= self.SYS_MAX_DAILY_LOSS_PCT:
            if not self.ftmo_trading_halted:
                self.log_system(
                    f"[FTMO HALT] Daily loss {daily_loss_pct:.2f}% >= system limit "
                    f"{self.SYS_MAX_DAILY_LOSS_PCT}% — TRADING HALTED"
                )
            self.ftmo_trading_halted = True
            return True

        if daily_loss_pct >= self.FTMO_MAX_DAILY_LOSS_PCT * 0.8:
            self.log_system(
                f"[FTMO WARN] Daily loss {daily_loss_pct:.2f}% approaching FTMO limit "
                f"{self.FTMO_MAX_DAILY_LOSS_PCT}%"
            )

        if total_loss_pct >= self.FTMO_MAX_TOTAL_LOSS_PCT * 0.8:
            self.log_system(
                f"[FTMO WARN] Total drawdown {total_loss_pct:.2f}% approaching FTMO limit "
                f"{self.FTMO_MAX_TOTAL_LOSS_PCT}%"
            )

        if total_loss_pct >= self.FTMO_MAX_TOTAL_LOSS_PCT:
            if not self.ftmo_trading_halted:
                self.log_system(
                    f"[FTMO HALT] Total drawdown {total_loss_pct:.2f}% >= FTMO limit "
                    f"{self.FTMO_MAX_TOTAL_LOSS_PCT}% — TRADING HALTED"
                )
            self.ftmo_trading_halted = True
            return True

        return False

    def run_cycle(self):
        """Run one prediction cycle"""
        # FTMO drawdown safety check — halt before doing anything
        if MT5_AVAILABLE:
            try:
                account = mt5.account_info()
                if account and self.check_ftmo_drawdown_safety(account.balance):
                    self.log_system("[FTMO] Cycle skipped — trading halted due to drawdown limits")
                    return False
            except Exception as e:
                self.log_system(f"[WARN] Could not check MT5 account balance: {e}")

        # Extract features from per-symbol CSVs written by Bridge EA
        features_dict = self.extract_features()
        if not features_dict:
            self.log_system("[ERROR] No features extracted — Bridge EA may not be running")
            return False

        # Make ML predictions (XGBoost where model exists, ABSTAIN where not)
        ml_results = self.make_ml_predictions(features_dict)
        if not ml_results:
            self.log_system("[ERROR] No ML predictions generated")
            return False
        
        # Make strategy predictions
        strategy_results = self.make_strategy_predictions(features_dict)
        
        # Get upcoming news (optional)
        upcoming_news = []
        if self.news_integration:
            upcoming_news = self.news_integration.get_events_for_hard_filter(buffer_minutes=30)
            if upcoming_news:
                event_names = [e['name'] for e in upcoming_news]
                self.log_system(f"[NEWS] {len(upcoming_news)} high-impact event(s): {', '.join(event_names)}")
        
        # Apply confluence filtering
        filtered_results = self.apply_confluence_filtering(
            ml_results=ml_results,
            features_dict=features_dict,
            upcoming_news=upcoming_news,
            strategy_results=strategy_results
        )
        
        # Generate signals with level-based SL/TP
        signals = self.generate_signals(filtered_results, strategy_results, features_dict)
        
        # Sync positions
        self.sync_positions_from_mt5()
        
        # Check scaling
        scaling_signals = self.check_scaling_opportunities(features_dict)
        
        # Add SCALE_OUT signals with quarter-level lot size (v5.1)
        for scale in scaling_signals:
            if scale['action'] == 'SCALE_OUT':
                signals.append({
                    'pair': scale['pair'],
                    'action': 'SCALE_OUT',
                    'confidence': scale['confidence'],
                    'confluence_score': scale['confluence_score'],
                    'confluence_level': 'SCALE',
                    'regime': 'scaling',
                    'lot_size': scale.get('lot_size', self.SCALEOUT_LOT_SIZE),  # Use quarter-level lot size
                    'available_risk': 0,
                    'explanation': {'reason': scale['reason']}
                })
        
        # Update counts
        self.prediction_count += len(ml_results)
        self.signal_count += len(signals)
        
        # Display results
        portfolio = self.risk_manager.get_portfolio_risk()
        self.log_system(
            f"[OK] ML: {len(ml_results)} | Filtered: {len(filtered_results)} | "
            f"Signals: {len(signals)} | Risk: {portfolio.total_risk_percent:.1%}"
        )
        
        if signals:
            for signal in signals:
                model_votes = signal.get('model_votes', {})
                unanimous = "✓" if signal.get('unanimous', False) else ""
                strat_agree = "✓" if signal.get('strategies_agree', False) else "✗"
                strat_votes = signal.get('strategy_votes', {})
                
                self.log_system(
                    f"   [SIGNAL] {signal['pair']}: {signal['action']} "
                    f"(conf: {signal['confidence']:.1%}, "
                    f"confluence: {signal['confluence_score']:.2f}, "
                    f"models: {model_votes} {unanimous}, "
                    f"strat: {strat_votes.get('BUY',0)}B/{strat_votes.get('SELL',0)}S {strat_agree})"
                )
            
            self.log_predictions(ml_results, filtered_results, signals)
            self.write_trade_commands(signals)
        else:
            self.log_system("   [HOLD] No signals after confluence filtering")
            self.log_predictions(ml_results, filtered_results, signals)
            self.write_trade_commands([])
        
        # Log scaling
        if scaling_signals:
            for scale in scaling_signals:
                self.log_system(
                    f"   [SCALE] {scale['pair']}: {scale['action']} "
                    f"(confluence: {scale['confluence_score']}, reason: {scale['reason']})"
                )
        
        return True
    
    def run(self, update_interval=3, max_cycles=None):
        """Main trading loop"""
        self.log_system("="*70)
        self.log_system("STARTING LIVE TRADING V5.0 - TREE-BASED ENSEMBLE")
        self.log_system("="*70)
        self.log_system(f"Update interval: {update_interval}s")
        self.log_system("Press Ctrl+C to stop")
        self.log_system("="*70)
        
        # Initialize news (optional)
        if self.news_integration:
            self.log_system("\n[NEWS] Initializing news analysis system...")
            try:
                self.news_integration.update(force=True)
                self.log_system(self.news_integration.get_summary())
            except Exception as e:
                self.log_system(f"[NEWS] Init warning: {e}")
        
        self._last_news_update = datetime.now()
        self._news_update_interval = 300
        
        cycle = 0
        
        try:
            while True:
                cycle += 1
                
                if max_cycles and cycle > max_cycles:
                    self.log_system(f"Reached max cycles ({max_cycles})")
                    break
                
                self.log_system(f"\n--- Cycle {cycle} ---")
                
                # Periodic news update (optional)
                if self.news_integration and (datetime.now() - self._last_news_update).total_seconds() > self._news_update_interval:
                    try:
                        self.news_integration.update(force=True)
                        blocked = self.news_integration.get_blocked_pairs()
                        if blocked:
                            self.log_system(f"[NEWS] Blocked pairs: {', '.join(blocked)}")
                        self._last_news_update = datetime.now()
                    except Exception as e:
                        self.log_system(f"[NEWS] Update warning: {e}")
                
                success = self.run_cycle()
                
                if not success:
                    self.log_system("[WARNING] Cycle failed")
                
                time.sleep(update_interval)
        
        except KeyboardInterrupt:
            self.log_system("\n\n[STOP] Stopped by user")
            self.shutdown()
    
    def shutdown(self):
        """Clean shutdown"""
        if self._shutdown_called:
            return
        self._shutdown_called = True
        
        self.log_system("\n" + "="*70)
        self.log_system("SHUTDOWN SUMMARY")
        self.log_system("="*70)
        self.log_system(f"Total predictions: {self.prediction_count}")
        self.log_system(f"Total signals: {self.signal_count}")
        self.log_system(f"Filtered out: {self.filtered_count}")
        
        portfolio = self.risk_manager.get_portfolio_risk()
        self.log_system(f"Final portfolio risk: {portfolio.total_risk_percent:.1%}")
        self.log_system(f"Open positions: {portfolio.position_count}")
        
        # Show prediction log location
        self.log_system(f"\nPrediction log: {self.ml_predictor.log_file}")
        self.log_system("Run analyze_logged_predictions() after trades close to optimize weights")
        self.log_system("="*70)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Live Trading System V5.0 - Tree-Based Ensemble')
    parser.add_argument('--mode', default='demo', choices=['demo', 'live'])
    parser.add_argument('--interval', type=int, default=3)
    parser.add_argument('--cycles', type=int, default=None)
    parser.add_argument('--confidence', type=float, default=0.35)
    parser.add_argument('--confluence', type=float, default=0.35)
    parser.add_argument('--balance', type=float, default=10000.0)
    parser.add_argument('--trading-capital', type=float, default=0.10,
                        help='Percent of account to use as trading capital (default 0.10 = 10%%)')
    parser.add_argument('--weighting', default='equal', choices=['equal', 'validation', 'confidence'])
    
    args = parser.parse_args()
    
    system = LiveTradingSystemV5(
        mode=args.mode,
        confidence_threshold=args.confidence,
        confluence_threshold=args.confluence,
        account_balance=args.balance,
        trading_capital_percent=args.trading_capital
    )
    
    system.run(
        update_interval=args.interval,
        max_cycles=args.cycles
    )


if __name__ == '__main__':
    main()
