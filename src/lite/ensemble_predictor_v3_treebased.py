"""
Ensemble Predictor V3.2 - Tree-Based Ensemble (XGBoost + LightGBM)
================================================================================
Two gradient boosting models with configurable weights. CatBoost EXCLUDED.

Key Changes from V3.1:
- CLEAN27 models: trained on Dukascopy data (3 years, 598K candles)
- CatBoost REMOVED (underperformed by 7%)
- 27 CLEAN features selected from 58 base features
- Model files: trained_models_CLEAN27/*.joblib

Model Performance (M15 Timeframe, 27 CLEAN Features):
- XGBoost:  70.5% average validation accuracy
- LightGBM: 70.3% average validation accuracy

Label Distribution (Clean Data):
- SELL: 21.5%, HOLD: 56.7%, BUY: 21.8%

Author: AI Trading System
Version: 3.2 (CLEAN27 Models)
Date: 2025-12-03
"""

import numpy as np
import pandas as pd
import joblib
import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import gc
import warnings
warnings.filterwarnings('ignore')

# Optional imports for LightGBM and CatBoost
try:
    import lightgbm as lgb
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False
    print("[WARNING] LightGBM not installed - will use XGBoost only")

try:
    from catboost import CatBoostClassifier
    HAS_CATBOOST = True
except ImportError:
    HAS_CATBOOST = False
    print("[WARNING] CatBoost not installed - will use XGBoost only")



class EnsemblePredictorV3:
    """
    Tree-Based Ensemble Predictor with Adaptive Weighting
    
    Uses XGBoost, LightGBM, and CatBoost with configurable weights.
    Logs all predictions for post-hoc weight optimization.
    
    Weighting Modes:
    - 'equal': All models weighted equally [0.33, 0.33, 0.33]
    - 'validation': Weights based on validation accuracy [0.29, 0.38, 0.33]
    - 'custom': User-provided weights
    - 'confidence': Dynamic weighting by prediction confidence (original V3.0 behavior)
    """
    
    # Label mapping: Class 0=SELL, Class 1=HOLD, Class 2=BUY
    LABELS = ['SELL', 'HOLD', 'BUY']
    
    # Default weights - CatBoost REMOVED
    DEFAULT_WEIGHTS = {
        'equal': {'xgboost': 0.50, 'lightgbm': 0.50},
        'validation': {'xgboost': 0.50, 'lightgbm': 0.50}
    }
    
    # 27 CLEAN feature indices from the 58 base features (ORDER MATTERS - must match training)
    # Training order: price(4), trend(8), momentum(4), volatility(5), volume(3), sentiment(3)
    CLEAN27_INDICES = [
        0, 1, 2, 3,           # close, high, low, volume
        4, 5, 6, 7,           # sma_20, sma_50, fast_ema, slow_ema
        26, 27, 28, 29,       # htf_fast_ema, htf_slow_ema, htf_trend_direction, htf_trend_alignment
        8, 13, 14, 19,        # rsi, stoch_k, stoch_d, momentum
        9, 10, 11, 12, 18,    # atr, bb_upper, bb_middle, bb_lower, volatility
        15, 16, 17,           # volume_sma, volume_ratio, price_volume
        30, 31, 32            # bullish_sentiment, bearish_sentiment, net_sentiment
    ]
    
    def __init__(self, model_dir: str = None, 
                 weighting_mode: str = 'equal',
                 custom_weights: Dict[str, float] = None,
                 enable_logging: bool = True,
                 log_dir: str = None):
        """
        Initialize tree-based ensemble predictor with configurable weighting
        
        Args:
            model_dir: Path to model directory (default: trained_models_105FEAT)
            weighting_mode: 'equal', 'validation', 'custom', or 'confidence'
            custom_weights: Dict of model weights if mode='custom'
            enable_logging: Whether to log predictions for analysis
            log_dir: Directory for prediction logs (default: logs/predictions)
        """
        if model_dir is None:
            self.model_dir = Path(__file__).parent / "trained_models_CLEAN27"
        else:
            self.model_dir = Path(model_dir)
        
        # Currency pairs
        self.pairs = [
            'EURUSD.sim', 'GBPUSD.sim', 'USDJPY.sim', 'USDCHF.sim',
            'AUDUSD.sim', 'USDCAD.sim', 'NZDUSD.sim', 'EURGBP.sim'
        ]
        
        # Model directory (flat structure - no subdirectories)
        self.xgb_dir = self.model_dir
        self.lgb_dir = self.model_dir
        
        # Feature counts
        self.n_features = 58         # Base features from EA
        self.n_clean_features = 27   # Clean features for ML models
        
        # Cached models (loaded on demand)
        self._cached_models: Dict[str, Dict] = {}
        
        # Weighting configuration
        self.weighting_mode = weighting_mode
        self._setup_weights(weighting_mode, custom_weights)
        
        # Logging configuration
        self.enable_logging = enable_logging
        if log_dir is None:
            self.log_dir = Path(__file__).parent / "logs" / "predictions"
        else:
            self.log_dir = Path(log_dir)
        
        if self.enable_logging:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self._init_log_file()
        
        print(f"\n[ENSEMBLE] Tree-Based Predictor V3.1 initialized")
        print(f"   Model directory: {self.model_dir}")
        print(f"   Weighting mode: {weighting_mode}")
        print(f"   Model weights: {self.model_weights}")
        print(f"   Prediction logging: {'ENABLED' if enable_logging else 'DISABLED'}")
        if enable_logging:
            print(f"   Log directory: {self.log_dir}")

    def _setup_weights(self, mode: str, custom_weights: Dict[str, float] = None):
        """Configure model weights based on mode"""
        if mode == 'equal':
            self.model_weights = self.DEFAULT_WEIGHTS['equal'].copy()
        elif mode == 'validation':
            self.model_weights = self.DEFAULT_WEIGHTS['validation'].copy()
        elif mode == 'custom' and custom_weights:
            # Normalize custom weights
            total = sum(custom_weights.values())
            self.model_weights = {k: v/total for k, v in custom_weights.items()}
        elif mode == 'confidence':
            # Confidence mode uses dynamic weighting per prediction
            self.model_weights = None
        else:
            print(f"[WARNING] Unknown weighting mode '{mode}', using equal weights")
            self.model_weights = self.DEFAULT_WEIGHTS['equal'].copy()
    
    def _init_log_file(self):
        """Initialize CSV log file for predictions"""
        self.log_file = self.log_dir / f"predictions_{datetime.now().strftime('%Y%m%d')}.csv"
        
        # Create header if file doesn't exist
        if not self.log_file.exists():
            headers = [
                'timestamp', 'pair', 'ensemble_pred', 'ensemble_label', 'ensemble_conf',
                'xgb_pred', 'xgb_label', 'xgb_conf', 'xgb_prob_sell', 'xgb_prob_hold', 'xgb_prob_buy',
                'lgb_pred', 'lgb_label', 'lgb_conf', 'lgb_prob_sell', 'lgb_prob_hold', 'lgb_prob_buy',
                'cat_pred', 'cat_label', 'cat_conf', 'cat_prob_sell', 'cat_prob_hold', 'cat_prob_buy',
                'agreement', 'unanimous', 'weighting_mode',
                'trade_id', 'actual_outcome', 'pnl'  # Filled later after trade closes
            ]
            with open(self.log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
    
    def _log_prediction(self, result: Dict, trade_id: str = None):
        """Log prediction to CSV for later analysis"""
        if not self.enable_logging:
            return
        
        # Extract individual model data
        indiv = result.get('individual_predictions', {})
        probs = result.get('individual_probabilities', {})
        
        row = [
            result['timestamp'],
            result['pair'],
            result['prediction'],
            result['prediction_label'],
            round(result['confidence'], 4),
        ]
        
        # XGBoost data
        if 'xgboost' in indiv:
            xgb = indiv['xgboost']
            xgb_probs = probs.get('xgboost', [0, 0, 0])
            row.extend([xgb['prediction'], xgb['label'], round(xgb['confidence'], 4),
                       round(xgb_probs[0], 4), round(xgb_probs[1], 4), round(xgb_probs[2], 4)])
        else:
            row.extend(['', '', '', '', '', ''])
        
        # LightGBM data
        if 'lightgbm' in indiv:
            lgb_data = indiv['lightgbm']
            lgb_probs = probs.get('lightgbm', [0, 0, 0])
            row.extend([lgb_data['prediction'], lgb_data['label'], round(lgb_data['confidence'], 4),
                       round(lgb_probs[0], 4), round(lgb_probs[1], 4), round(lgb_probs[2], 4)])
        else:
            row.extend(['', '', '', '', '', ''])
        
        # CatBoost data
        if 'catboost' in indiv:
            cat = indiv['catboost']
            cat_probs = probs.get('catboost', [0, 0, 0])
            row.extend([cat['prediction'], cat['label'], round(cat['confidence'], 4),
                       round(cat_probs[0], 4), round(cat_probs[1], 4), round(cat_probs[2], 4)])
        else:
            row.extend(['', '', '', '', '', ''])
        
        # Agreement info
        row.extend([result['agreement'], result['unanimous'], self.weighting_mode])
        
        # Trade tracking (empty until trade closes)
        row.extend([trade_id or '', '', ''])
        
        # Write to CSV
        with open(self.log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(row)

    def update_trade_outcome(self, trade_id: str, actual_outcome: str, pnl: float):
        """
        Update a logged prediction with the actual trade outcome
        
        Args:
            trade_id: Unique trade identifier
            actual_outcome: 'WIN', 'LOSS', or 'BREAKEVEN'
            pnl: Profit/loss in pips or currency
        """
        if not self.enable_logging or not self.log_file.exists():
            return
        
        # Read existing data
        df = pd.read_csv(self.log_file)
        
        # Find and update matching trade
        mask = df['trade_id'] == trade_id
        if mask.any():
            df.loc[mask, 'actual_outcome'] = actual_outcome
            df.loc[mask, 'pnl'] = pnl
            df.to_csv(self.log_file, index=False)
            print(f"[LOG] Updated trade {trade_id}: {actual_outcome}, PnL={pnl}")
    
    def _validate_features(self, features: np.ndarray) -> np.ndarray:
        """Validate and clean feature array"""
        if not isinstance(features, np.ndarray):
            features = np.array(features)
        
        if features.dtype == np.object_:
            features = features.astype(np.float64)
        
        features = features.astype(np.float64)
        features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)
        
        return features
    
    def load_models_for_pair(self, pair: str) -> Dict:
        """Load XGBoost and LightGBM models for a single pair"""
        if pair in self._cached_models:
            return self._cached_models[pair]
        
        models = {}
        
        # Strip .sim suffix for file lookup
        pair_clean = pair.replace('.sim', '')
        
        # Load XGBoost
        xgb_path = self.xgb_dir / f"{pair_clean}_xgboost.joblib"
        if xgb_path.exists():
            try:
                model = joblib.load(xgb_path)
                models['xgboost'] = {
                    'model': model,
                    'feature_cols': None
                }
            except Exception as e:
                print(f"   [WARNING] XGBoost load failed for {pair}: {e}")
        
        # Load LightGBM
        if HAS_LIGHTGBM:
            lgb_path = self.lgb_dir / f"{pair_clean}_lightgbm.joblib"
            if lgb_path.exists():
                try:
                    model = joblib.load(lgb_path)
                    models['lightgbm'] = {
                        'model': model,
                        'feature_cols': None
                    }
                except Exception as e:
                    print(f"   [WARNING] LightGBM load failed for {pair}: {e}")
        
        self._cached_models[pair] = models
        return models
    
    def unload_models(self, pair: str = None):
        """Free memory by unloading cached models"""
        if pair:
            if pair in self._cached_models:
                del self._cached_models[pair]
        else:
            self._cached_models.clear()
        gc.collect()

    def predict_single_model(self, model_data: Dict, features: np.ndarray) -> Tuple[int, float, np.ndarray]:
        """Get prediction from a single model"""
        model = model_data['model']
        
        if features.ndim == 1:
            features = features.reshape(1, -1)
        
        proba = model.predict_proba(features)[0]
        pred_class = int(np.argmax(proba))
        confidence = float(np.max(proba))
        
        return pred_class, confidence, proba
    
    def predict_pair(self, features: np.ndarray, pair: str, trade_id: str = None) -> Optional[Dict]:
        """
        Make ensemble prediction for a single pair using weighted voting
        
        Args:
            features: numpy array of 58 features
            pair: Currency pair name
            trade_id: Optional trade ID for logging
            
        Returns:
            Dictionary with prediction results or None if failed
        """
        features = self._validate_features(features)
        
        if len(features) != self.n_features:
            print(f"   [ERROR] Expected {self.n_features} features, got {len(features)}")
            return None
        
        # Extract 27 CLEAN features from 58 base features
        clean_features = features[self.CLEAN27_INDICES]
        
        models = self.load_models_for_pair(pair)
        
        if not models:
            print(f"   [ERROR] No models available for {pair}")
            return None
        
        # Get predictions from each model
        predictions = {}
        confidences = {}
        probabilities = {}
        
        for model_name, model_data in models.items():
            try:
                pred, conf, proba = self.predict_single_model(model_data, clean_features)
                predictions[model_name] = pred
                confidences[model_name] = conf
                probabilities[model_name] = proba.tolist()
            except Exception as e:
                print(f"   [WARNING] {model_name} prediction failed for {pair}: {e}")
        
        if not predictions:
            return None
        
        # Weighted voting
        vote_weights = {0: 0.0, 1: 0.0, 2: 0.0}
        
        if self.weighting_mode == 'confidence' or self.model_weights is None:
            # Original V3.0 behavior: weight by confidence
            for model_name, pred in predictions.items():
                conf = confidences[model_name]
                vote_weights[pred] += conf
        else:
            # Fixed weights mode (equal, validation, or custom)
            for model_name, pred in predictions.items():
                weight = self.model_weights.get(model_name, 0.333)
                vote_weights[pred] += weight
        
        # Normalize weights
        total_weight = sum(vote_weights.values())
        if total_weight > 0:
            for key in vote_weights:
                vote_weights[key] /= total_weight
        
        # Final prediction
        final_pred = max(vote_weights.keys(), key=lambda k: vote_weights[k])
        final_conf = vote_weights[final_pred]
        
        # OPTION A FIX: If HOLD wins, use strongest directional signal instead
        # Training data was 80% HOLD, causing models to over-predict it
        # BUG FIX v3.2: Preserve meaningful confidence when overriding HOLD
        if final_pred == 1:  # HOLD
            original_hold_conf = final_conf  # Save the HOLD confidence (often 0.67-1.0)
            # Pick higher of BUY vs SELL
            if vote_weights[2] >= vote_weights[0]:  # BUY >= SELL
                final_pred = 2
                # Use the better of: directional weight, scaled HOLD conf, or minimum 0.35
                final_conf = max(vote_weights[2], original_hold_conf * 0.5, 0.35)
            else:
                final_pred = 0
                final_conf = max(vote_weights[0], original_hold_conf * 0.5, 0.35)
        
        # Agreement level
        agreement_count = sum(1 for p in predictions.values() if p == final_pred)
        
        result = {
            'pair': pair,
            'prediction': final_pred,
            'prediction_label': self.LABELS[final_pred],
            'confidence': final_conf,
            'agreement': f"{agreement_count}/{len(predictions)}",
            'unanimous': agreement_count == len(predictions),
            'models_used': list(predictions.keys()),
            'individual_predictions': {
                name: {
                    'prediction': pred,
                    'label': self.LABELS[pred],
                    'confidence': confidences[name]
                }
                for name, pred in predictions.items()
            },
            'individual_probabilities': probabilities,
            'vote_distribution': {
                self.LABELS[k]: round(v, 4) for k, v in vote_weights.items()
            },
            'weighting_mode': self.weighting_mode,
            'timestamp': datetime.now().isoformat()
        }
        
        # Log prediction
        self._log_prediction(result, trade_id)
        
        return result

    def predict_all_pairs(self, features_dict: Dict[str, np.ndarray]) -> Dict[str, Dict]:
        """Make predictions for multiple pairs"""
        results = {}
        for pair, features in features_dict.items():
            if pair in self.pairs:
                result = self.predict_pair(features, pair)
                if result:
                    results[pair] = result
        return results
    
    def get_trading_signal(self, features: np.ndarray, pair: str, 
                          min_confidence: float = 0.5,
                          require_agreement: bool = True,
                          trade_id: str = None) -> Optional[Dict]:
        """
        Get trading signal with filters applied
        
        Args:
            features: Feature array
            pair: Currency pair
            min_confidence: Minimum confidence threshold
            require_agreement: Require at least 2/3 models to agree
            trade_id: Optional trade ID for logging
            
        Returns:
            Trading signal dict or None if filtered out
        """
        result = self.predict_pair(features, pair, trade_id)
        
        if result is None:
            return None
        
        # Confidence filter
        if result['confidence'] < min_confidence:
            return {
                'pair': pair,
                'signal': 'NO_TRADE',
                'reason': f"Low confidence: {result['confidence']:.2%} < {min_confidence:.2%}",
                'prediction': result
            }
        
        # Agreement filter
        if require_agreement:
            agreement_parts = result['agreement'].split('/')
            agreed = int(agreement_parts[0])
            if agreed < 2:
                return {
                    'pair': pair,
                    'signal': 'NO_TRADE',
                    'reason': f"No agreement: {result['agreement']}",
                    'prediction': result
                }
        
        # HOLD = no trade
        if result['prediction'] == 1:
            return {
                'pair': pair,
                'signal': 'HOLD',
                'reason': 'Models predict HOLD',
                'prediction': result
            }
        
        return {
            'pair': pair,
            'signal': result['prediction_label'],
            'confidence': result['confidence'],
            'agreement': result['agreement'],
            'prediction': result
        }
    
    def verify_models_exist(self) -> Dict[str, List[str]]:
        """Check which models exist for each pair"""
        available = {}
        
        for pair in self.pairs:
            pair_models = []
            pair_clean = pair.replace('.sim', '')  # Strip .sim suffix for file lookup
            
            # CLEAN27 models use flat structure with .joblib extension
            if (self.model_dir / f"{pair_clean}_xgboost.joblib").exists():
                pair_models.append('xgboost')
            
            if HAS_LIGHTGBM and (self.model_dir / f"{pair_clean}_lightgbm.joblib").exists():
                pair_models.append('lightgbm')
            
            available[pair] = pair_models
        
        print(f"\n[MODELS] Availability Check:")
        for pair, models in available.items():
            status = "OK" if len(models) == 2 else "WARN" if models else "FAIL"
            print(f"   [{status}] {pair}: {len(models)}/2 ({', '.join(models) if models else 'NONE'})")
        
        return available
    
    def get_model_stats(self) -> Dict:
        """Get statistics about loaded models"""
        return {
            'cached_pairs': list(self._cached_models.keys()),
            'total_cached': len(self._cached_models),
            'pairs_available': len(self.pairs),
            'model_types': ['xgboost', 'lightgbm'],
            'weighting_mode': self.weighting_mode,
            'model_weights': self.model_weights,
            'logging_enabled': self.enable_logging,
            'log_file': str(self.log_file) if self.enable_logging else None
        }

    def analyze_logged_predictions(self, log_file: str = None) -> Dict:
        """
        Analyze logged predictions to calculate optimal weights
        
        Args:
            log_file: Path to log CSV (default: current log file)
            
        Returns:
            Analysis results with recommended weights
        """
        if log_file is None:
            log_file = self.log_file
        
        if not Path(log_file).exists():
            print("[ANALYSIS] No log file found")
            return {}
        
        df = pd.read_csv(log_file)
        
        # Filter to trades with outcomes
        completed = df[df['actual_outcome'].notna() & (df['actual_outcome'] != '')]
        
        if len(completed) == 0:
            print("[ANALYSIS] No completed trades to analyze")
            return {'total_predictions': len(df), 'completed_trades': 0}
        
        print(f"\n[ANALYSIS] Analyzing {len(completed)} completed trades")
        
        # Calculate per-model accuracy
        model_accuracy = {}
        
        for model in ['xgb', 'lgb', 'cat']:
            pred_col = f'{model}_pred'
            if pred_col in completed.columns:
                # Model was "correct" if its prediction matched the actual outcome
                # For now, simple: WIN when signal matched market direction
                correct = 0
                total = 0
                
                for _, row in completed.iterrows():
                    if pd.notna(row[pred_col]) and row[pred_col] != '':
                        total += 1
                        model_pred = int(row[pred_col])
                        outcome = row['actual_outcome']
                        
                        # Simple scoring: if trade was WIN and model agreed with ensemble
                        if outcome == 'WIN' and model_pred == row['ensemble_pred']:
                            correct += 1
                        elif outcome == 'LOSS' and model_pred != row['ensemble_pred']:
                            correct += 1  # Model disagreed with losing trade
                
                if total > 0:
                    model_accuracy[model] = correct / total
        
        # Calculate recommended weights
        if model_accuracy:
            total_acc = sum(model_accuracy.values())
            recommended_weights = {
                'xgboost': model_accuracy.get('xgb', 0.333) / total_acc if total_acc > 0 else 0.333,
                'lightgbm': model_accuracy.get('lgb', 0.333) / total_acc if total_acc > 0 else 0.333,
                'catboost': model_accuracy.get('cat', 0.333) / total_acc if total_acc > 0 else 0.333
            }
        else:
            recommended_weights = self.DEFAULT_WEIGHTS['equal']
        
        # Win rate analysis
        win_rate = len(completed[completed['actual_outcome'] == 'WIN']) / len(completed)
        
        results = {
            'total_predictions': len(df),
            'completed_trades': len(completed),
            'win_rate': round(win_rate, 4),
            'model_accuracy': model_accuracy,
            'current_weights': self.model_weights,
            'recommended_weights': recommended_weights,
            'by_pair': {}
        }
        
        # Per-pair breakdown
        for pair in self.pairs:
            pair_data = completed[completed['pair'] == pair]
            if len(pair_data) > 0:
                pair_wins = len(pair_data[pair_data['actual_outcome'] == 'WIN'])
                results['by_pair'][pair] = {
                    'trades': len(pair_data),
                    'wins': pair_wins,
                    'win_rate': round(pair_wins / len(pair_data), 4)
                }
        
        print(f"   Win Rate: {win_rate:.1%}")
        print(f"   Model Accuracy: {model_accuracy}")
        print(f"   Recommended Weights: {recommended_weights}")
        
        return results
    
    def set_weights(self, weights: Dict[str, float]):
        """Update model weights based on analysis"""
        total = sum(weights.values())
        self.model_weights = {k: v/total for k, v in weights.items()}
        self.weighting_mode = 'custom'
        print(f"[WEIGHTS] Updated to: {self.model_weights}")


# ==================== STANDALONE TESTING ====================

def test_predictor():
    """Test the ensemble predictor with dummy data"""
    print("\n" + "=" * 60)
    print("TESTING TREE-BASED ENSEMBLE PREDICTOR V3.1")
    print("(Equal Weights + Prediction Logging)")
    print("=" * 60)
    
    # Initialize predictor with logging
    predictor = EnsemblePredictorV3(
        weighting_mode='equal',
        enable_logging=True
    )
    
    # Check model availability
    available = predictor.verify_models_exist()
    
    # Show configuration
    print(f"\n[CONFIG]")
    print(f"   Weighting Mode: {predictor.weighting_mode}")
    print(f"   Model Weights: {predictor.model_weights}")
    print(f"   Logging: {predictor.enable_logging}")
    print(f"   Log File: {predictor.log_file}")
    
    # Create dummy features (58 features)
    dummy_features = np.random.randn(58)
    
    # Test prediction for first available pair
    for pair, models in available.items():
        if models:
            print(f"\n[TEST] Predicting for {pair}...")
            
            # Generate a unique trade ID
            trade_id = f"TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{pair[:6]}"
            
            result = predictor.predict_pair(dummy_features, pair, trade_id=trade_id)
            
            if result:
                print(f"   Ensemble Prediction: {result['prediction_label']}")
                print(f"   Ensemble Confidence: {result['confidence']:.2%}")
                print(f"   Agreement: {result['agreement']}")
                print(f"   Vote Distribution: {result['vote_distribution']}")
                print(f"\n   Individual Model Predictions:")
                for model, data in result['individual_predictions'].items():
                    print(f"      {model}: {data['label']} ({data['confidence']:.1%})")
                
                # Test trading signal
                signal = predictor.get_trading_signal(dummy_features, pair, trade_id=f"{trade_id}_sig")
                print(f"\n   Trading Signal: {signal['signal'] if signal else 'None'}")
                
                # Show logged prediction
                print(f"\n   Logged to: {predictor.log_file}")
            
            break
    
    # Test all weighting modes
    print("\n" + "-" * 40)
    print("TESTING DIFFERENT WEIGHTING MODES")
    print("-" * 40)
    
    for mode in ['equal', 'validation', 'confidence']:
        predictor_test = EnsemblePredictorV3(
            weighting_mode=mode,
            enable_logging=False
        )
        
        for pair, models in available.items():
            if models:
                result = predictor_test.predict_pair(dummy_features, pair)
                if result:
                    print(f"\n   {mode.upper()} mode:")
                    print(f"      Prediction: {result['prediction_label']}")
                    print(f"      Confidence: {result['confidence']:.2%}")
                    print(f"      Weights used: {predictor_test.model_weights}")
                break
    
    # Cleanup
    predictor.unload_models()
    print("\n[TEST] Complete!")
    print("=" * 60)


if __name__ == "__main__":
    test_predictor()
