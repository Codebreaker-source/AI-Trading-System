"""
Dynamic symbol discovery for FTMO MT5 account.
Queries all available symbols, filters to tradeable, categorizes,
and identifies which have pretrained XGBoost models.
"""

import os
import json
import logging
from pathlib import Path

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False

logger = logging.getLogger(__name__)

PRETRAINED_BASES = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD", "EURGBP"]

SUFFIX_STRIP_PATTERNS = [".i", "_SB", ".r", "_raw", ".a", ".b", ".c", ".m", ".pro"]

CATEGORY_RULES = {
    "major":  ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD", "USDJPY"],
    "metals": ["XAUUSD", "XAGUSD", "XPTUSD", "XPDUSD", "GOLD", "SILVER"],
    "crypto": ["BTC", "ETH", "LTC", "XRP", "BNB"],
    "index":  ["US30", "US500", "NAS100", "UK100", "GER40", "JPN225", "AUS200", "SPX", "NDX", "DAX"],
    "energy": ["XTIUSD", "XBRUSD", "USOIL", "UKOIL", "NGAS"],
}

MAJOR_CURRENCIES = {"USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD"}


def strip_suffix(symbol: str) -> str:
    """Strip known FTMO broker suffixes to get the base symbol name."""
    base = symbol
    for suffix in SUFFIX_STRIP_PATTERNS:
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    return base.upper()


def categorize_symbol(symbol: str) -> str:
    base = strip_suffix(symbol).upper()
    for category, patterns in CATEGORY_RULES.items():
        if any(base.startswith(p) or base == p for p in patterns):
            return category
    if len(base) == 6:
        quote = base[3:]
        base3 = base[:3]
        if base3 in MAJOR_CURRENCIES and quote in MAJOR_CURRENCIES:
            return "major"
        if base3 in MAJOR_CURRENCIES or quote in MAJOR_CURRENCIES:
            return "minor"
        return "exotic"
    return "other"


def find_model_file(base_symbol: str, model_dir: str) -> str | None:
    """Return model filepath if a pretrained XGBoost model exists for this base symbol."""
    candidates = [
        f"{base_symbol}_xgboost_CLEAN27.joblib",
        f"{base_symbol}_xgboost.joblib",
    ]
    for name in candidates:
        path = os.path.join(model_dir, name)
        if os.path.exists(path):
            return path
    return None


class SymbolManager:
    def __init__(self, model_dir: str, config: dict | None = None):
        self.model_dir = model_dir
        self.config = config or {}
        self.all_symbols: list[str] = []
        self.symbols_with_models: list[str] = []
        self.symbols_without_models: list[str] = []
        self.symbol_categories: dict[str, str] = {}
        self.symbol_model_paths: dict[str, str] = {}

    def connect_mt5(self, login: int = 0, password: str = "", server: str = "") -> bool:
        if not MT5_AVAILABLE:
            logger.error("MetaTrader5 package not installed")
            return False
        if not mt5.initialize():
            logger.error(f"MT5 initialize failed: {mt5.last_error()}")
            return False
        if login and password and server:
            if not mt5.login(login, password=password, server=server):
                logger.error(f"MT5 login failed: {mt5.last_error()}")
                mt5.shutdown()
                return False
        logger.info("MT5 connected successfully")
        return True

    def discover(self) -> dict:
        """
        Main entry point. Returns dict with:
          symbols_with_models, symbols_without_models, categories, model_paths
        """
        if MT5_AVAILABLE:
            self._discover_from_mt5()
        else:
            logger.warning("MT5 not available — using model directory to infer symbol list")
            self._discover_from_models_only()

        self._classify_by_model()
        self._log_summary()
        return {
            "all_symbols": self.all_symbols,
            "symbols_with_models": self.symbols_with_models,
            "symbols_without_models": self.symbols_without_models,
            "categories": self.symbol_categories,
            "model_paths": self.symbol_model_paths,
        }

    def _discover_from_mt5(self):
        symbols_info = mt5.symbols_get()
        if not symbols_info:
            logger.warning("mt5.symbols_get() returned nothing — falling back to feature file discovery")
            self._discover_from_models_only()
            return

        tradeable = []
        for s in symbols_info:
            name = s.name
            if not name:
                continue
            if "#" in name:   # skip synthetic/index-only instruments
                continue
            tradeable.append(name)

        self.all_symbols = sorted(tradeable)
        logger.info(f"MT5 returned {len(symbols_info)} symbols; {len(tradeable)} tradeable")

    def _discover_from_models_only(self):
        """
        Fallback when MT5 API is unavailable.
        Scans Common\\Files for existing feature CSVs written by the Bridge EA,
        then falls back to the 8 pretrained bases if none found.
        """
        common_files = r"C:\Users\mt5-admin\AppData\Roaming\MetaQuotes\Terminal\Common\Files"
        import glob, os
        pattern = os.path.join(common_files, "*_features.csv")
        found = []
        for path in glob.glob(pattern):
            name = os.path.basename(path)
            symbol = name.replace("_features.csv", "")
            if symbol:
                found.append(symbol)

        if found:
            self.all_symbols = sorted(found)
            logger.info(f"Discovered {len(found)} symbols from feature CSVs (MT5 API unavailable)")
        else:
            self.all_symbols = list(PRETRAINED_BASES)
            logger.info("No feature CSVs found — using 8 pretrained base symbols")

    def _classify_by_model(self):
        for symbol in self.all_symbols:
            base = strip_suffix(symbol)
            self.symbol_categories[symbol] = categorize_symbol(symbol)
            model_path = find_model_file(base, self.model_dir)
            if model_path:
                self.symbols_with_models.append(symbol)
                self.symbol_model_paths[symbol] = model_path
            else:
                self.symbols_without_models.append(symbol)

    def _log_summary(self):
        total = len(self.all_symbols)
        with_m = len(self.symbols_with_models)
        without_m = len(self.symbols_without_models)
        logger.info(f"Symbol discovery complete: {total} total | {with_m} with ML models | {without_m} rule-based only")
        if self.symbols_with_models:
            logger.info(f"  ML symbols : {self.symbols_with_models}")
        cat_counts = {}
        for cat in self.symbol_categories.values():
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
        logger.info(f"  Categories : {cat_counts}")

    def has_model(self, symbol: str) -> bool:
        return symbol in self.symbol_model_paths

    def get_model_path(self, symbol: str) -> str | None:
        return self.symbol_model_paths.get(symbol)

    def get_base_symbol(self, symbol: str) -> str:
        return strip_suffix(symbol)

    def shutdown_mt5(self):
        if MT5_AVAILABLE:
            mt5.shutdown()


def load_symbol_manager(config_path: str | None = None) -> SymbolManager:
    """Convenience factory: loads config and returns a ready SymbolManager."""
    config = {}
    if config_path and os.path.exists(config_path):
        with open(config_path, "r") as f:
            full = json.load(f)
        config = full.get("symbols", {})
        model_dir = full.get("ml", {}).get("model_dir", "data/models")
    else:
        model_dir = "data/models"

    base_dir = Path(__file__).parent.parent
    model_dir_abs = str(base_dir / model_dir)

    return SymbolManager(model_dir=model_dir_abs, config=config)
