"""
FTMO AI Trading System - Entry Point
=====================================
Usage:
    python run_system.py [--mode demo|live] [--balance 100000] [--retrain-only]

Steps on startup:
  1. Connect MT5
  2. Discover all FTMO symbols via symbol_manager
  3. Load pretrained XGBoost models
  4. Verify feature CSVs directory
  5. Start main trading loop (M15 candle-based, 3s poll)
  6. Schedule daily retraining
"""

import sys
import io
import json

# Force UTF-8 output so Unicode characters (→, ✓ etc.) don't crash on Windows console
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
import logging
import argparse
import threading
import time
from pathlib import Path
from datetime import datetime, timezone

# --- path setup ---
SYSTEM_ROOT = Path(__file__).parent
sys.path.insert(0, str(SYSTEM_ROOT))

# --- logging setup ---
LOG_DIR = SYSTEM_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

import xgboost  # pre-import in main thread to avoid circular import in background thread

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_DIR / f"system_{datetime.now().strftime('%Y%m%d')}.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# Azure SDK logs every blob HTTP request/response at INFO — silence it
# (a single day of this reached 748MB and made log-staleness checks useless).
logging.getLogger("azure").setLevel(logging.WARNING)
logging.getLogger("azure.storage.blob").setLevel(logging.WARNING)
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    logger.warning("MetaTrader5 not installed — running in simulation mode")


def load_config() -> dict:
    cfg_path = SYSTEM_ROOT / "config" / "ftmo_config.json"
    if not cfg_path.exists():
        logger.warning(f"Config not found at {cfg_path}, using defaults")
        return {}
    with open(cfg_path) as f:
        return json.load(f)


FTMO_TERMINAL_PATH = r"C:\Program Files\OANDA MetaTrader 5\terminal64.exe"

def connect_mt5(config: dict) -> bool:
    if not MT5_AVAILABLE:
        return False
    acct = config.get("account", {})
    login = acct.get("login", 0)
    password = acct.get("password", "")
    server = acct.get("server", "")

    import os
    path = FTMO_TERMINAL_PATH if os.path.exists(FTMO_TERMINAL_PATH) else None

    init_ok = mt5.initialize(path=path) if path else mt5.initialize()
    if not init_ok:
        logger.error(f"MT5 initialize() failed: {mt5.last_error()}")
        return False

    if login and password and server:
        if not mt5.login(login, password=password, server=server):
            logger.error(f"MT5 login failed: {mt5.last_error()}")
            mt5.shutdown()
            return False

    info = mt5.account_info()
    if info:
        logger.info(f"MT5 connected — account: {info.login}, balance: {info.balance:.2f} {info.currency} | trade_allowed: {info.trade_allowed}")
    return True


def verify_feature_directory(config: dict):
    feat_dir = SYSTEM_ROOT / "data" / "features"
    feat_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Feature CSV directory: {feat_dir}")
    existing = list(feat_dir.glob("*_features.csv"))
    if existing:
        logger.info(f"  {len(existing)} feature CSV(s) already present")
    else:
        logger.info("  No feature CSVs yet — waiting for Bridge EA to start writing")


def run_daily_retrain_loop(config: dict, stop_event: threading.Event):
    """Background thread: runs daily retrainer once per day at configured time."""
    from training.daily_retrainer import run_daily_retraining

    retrain_cfg = config.get("retraining", {})
    schedule_utc = retrain_cfg.get("schedule_utc", "00:00")
    retrain_hour, retrain_minute = (int(x) for x in schedule_utc.split(":"))
    last_retrain_date = None

    logger.info(f"[RETRAIN] Daily retrainer thread started — scheduled at {schedule_utc} UTC")

    while not stop_event.is_set():
        now = datetime.now(timezone.utc)
        today = now.strftime("%Y-%m-%d")

        if (
            now.hour == retrain_hour
            and now.minute == retrain_minute
            and last_retrain_date != today
        ):
            logger.info("[RETRAIN] Starting daily retraining...")
            try:
                results = run_daily_retraining(config)
                updated = sum(1 for r in results if r.get("status") == "updated")
                logger.info(f"[RETRAIN] Done — {updated} model(s) updated")
            except Exception as e:
                logger.error(f"[RETRAIN] Failed: {e}", exc_info=True)
            last_retrain_date = today

        stop_event.wait(30)  # Check every 30 seconds


def run_outcome_simulator_loop(unified_trades_path: str, stop_event: threading.Event):
    """Background thread: replays MT5 ticks to label simulated trade outcomes."""
    from core.trade_outcome_simulator import TradeOutcomeSimulator

    sim = TradeOutcomeSimulator(unified_trades_path)
    logger.info("[SIM] Outcome simulator thread started")
    while not stop_event.is_set():
        try:
            sim.process_pending()
        except Exception as e:
            logger.error(f"[SIM] cycle error: {e}", exc_info=True)
        stop_event.wait(30)


def main():
    parser = argparse.ArgumentParser(description="FTMO AI Trading System")
    parser.add_argument("--mode", choices=["demo", "live"], default="demo")
    parser.add_argument("--balance", type=float, default=None,
                        help="Override account balance (for testing without MT5)")
    parser.add_argument("--retrain-only", action="store_true",
                        help="Run daily retrainer once and exit")
    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info("  FTMO AI TRADING SYSTEM — Phase 4 LITE")
    logger.info(f"  Mode: {args.mode.upper()}  |  {datetime.now(timezone.utc).isoformat()}")
    logger.info("=" * 70)

    # Load config
    config = load_config()

    # Retrain-only shortcut
    if args.retrain_only:
        from training.daily_retrainer import run_daily_retraining
        logger.info("[RETRAIN-ONLY] Running retrainer and exiting...")
        results = run_daily_retraining(config)
        for r in results:
            logger.info(
                f"  {r.get('source','?')}/{r.get('symbol','?')}: "
                f"updated={r.get('updated', [])} kept={r.get('kept', [])} "
                f"skipped={r.get('skipped', [])} errors={r.get('errors', [])}"
            )
        return

    # Step 1: Connect MT5
    logger.info("[STEP 1] Connecting to MT5...")
    mt5_ok = connect_mt5(config)
    if not mt5_ok:
        logger.warning("  MT5 not connected — running in simulation mode (no live trading)")

    # Step 2: Symbol discovery
    logger.info("[STEP 2] Discovering FTMO symbols...")
    from core.symbol_manager import load_symbol_manager
    sym_manager = load_symbol_manager(str(SYSTEM_ROOT / "config" / "ftmo_config.json"))
    discovery = sym_manager.discover()
    logger.info(
        f"  Total: {len(discovery['all_symbols'])} symbols | "
        f"ML-enabled: {len(discovery['symbols_with_models'])} | "
        f"Rule-based: {len(discovery['symbols_without_models'])}"
    )

    # Step 3: Load ensemble predictor (verifies models exist)
    logger.info("[STEP 3] Loading pretrained XGBoost models...")
    from core.ensemble_predictor import EnsemblePredictorV3
    model_dir = str(SYSTEM_ROOT / config.get("ml", {}).get("model_dir", "data/models"))
    predictor = EnsemblePredictorV3(model_dir=model_dir, enable_logging=True,
                                    log_dir=str(LOG_DIR / "predictions"))
    predictor.verify_models_exist(discovery["symbols_with_models"])

    # Step 4: Verify feature directory
    logger.info("[STEP 4] Verifying data directories...")
    verify_feature_directory(config)

    # Step 5: Initialise main trading system
    logger.info("[STEP 5] Initialising main trading system...")
    account_balance = args.balance
    if account_balance is None and mt5_ok and MT5_AVAILABLE:
        info = mt5.account_info()
        account_balance = info.balance if info else 100_000.0
    elif account_balance is None:
        account_balance = 100_000.0

    from core.live_trading_system import LiveTradingSystemV5
    system = LiveTradingSystemV5(
        mode=args.mode,
        confidence_threshold=config.get("ml", {}).get("min_confidence", 0.45),
        confluence_threshold=config.get("confluence", {}).get("min_score_to_trade", 0.55),
        account_balance=account_balance,
        trading_capital_percent=config.get("risk", {}).get("trading_capital_percent", 0.10),
    )

    # Step 6: Start daily retrainer background thread (gated by config)
    stop_event = threading.Event()
    if config.get("retraining", {}).get("enabled", True):
        logger.info("[STEP 6] Starting daily retrainer background thread...")
        retrain_thread = threading.Thread(
            target=run_daily_retrain_loop,
            args=(config, stop_event),
            daemon=True,
            name="DailyRetrainer",
        )
        retrain_thread.start()
    else:
        logger.info("[STEP 6] Daily retrainer DISABLED via config (retraining.enabled=false) — skipping")

    # Step 6b: Start tick-based outcome simulator background thread
    logger.info("[STEP 6b] Starting trade outcome simulator background thread...")
    unified_trades_path = str(SYSTEM_ROOT / "data" / "unified_trades.csv")
    sim_thread = threading.Thread(
        target=run_outcome_simulator_loop,
        args=(unified_trades_path, stop_event),
        daemon=True,
        name="OutcomeSimulator",
    )
    sim_thread.start()

    # Step 7: Main trading loop
    logger.info("[STEP 7] Entering main trading loop...")
    loop_interval = config.get("trading", {}).get("loop_interval_seconds", 3)

    try:
        system.run()  # live_trading_system.run() contains its own loop
    except KeyboardInterrupt:
        logger.info("\n[SHUTDOWN] Keyboard interrupt — shutting down gracefully...")
    except Exception as e:
        logger.error(f"[FATAL] Main loop crashed: {e}", exc_info=True)
    finally:
        stop_event.set()
        if MT5_AVAILABLE and mt5_ok:
            mt5.shutdown()
        logger.info("[SHUTDOWN] Complete")


if __name__ == "__main__":
    main()
