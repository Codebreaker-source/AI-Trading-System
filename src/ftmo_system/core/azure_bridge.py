"""
Azure Blob Storage Bridge
==========================
Uploads per-symbol feature CSVs to Azure so Google Colab can read them.
Downloads prediction JSONs that Colab writes back after inference.

Containers (auto-created if missing):
  trading-features    — feature CSVs uploaded by local Python every M15
  colab-predictions   — prediction JSONs uploaded by Colab every ~30 sec

Usage:
    bridge = AzureBridge()          # reads AZURE_STORAGE_CONNECTION_STRING
    bridge.upload_features("EURUSD.sim", "/path/to/EURUSD.sim_features.csv")
    preds = bridge.get_all_predictions(["EURUSD.sim", "GBPUSD.sim"])
    # preds = { "EURUSD.sim": { "lgbm": {...}, "catboost": {...}, "transformer": {...} } }
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict

logger = logging.getLogger(__name__)

try:
    from azure.storage.blob import BlobServiceClient
    AZURE_SDK_AVAILABLE = True
except ImportError:
    AZURE_SDK_AVAILABLE = False

FEATURES_CONTAINER   = "trading-features"
PREDICTIONS_CONTAINER = "colab-predictions"
PREDICTION_MAX_AGE_SEC = 1800   # 30 min — discard stale Colab predictions


class AzureBridge:

    def __init__(self, connection_string: Optional[str] = None):
        self.conn_str  = connection_string or os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "")
        self._client   = None
        self._enabled  = False

        if not AZURE_SDK_AVAILABLE:
            logger.warning("[AZURE] azure-storage-blob not installed — run: pip install azure-storage-blob")
            return

        if not self.conn_str:
            logger.warning("[AZURE] AZURE_STORAGE_CONNECTION_STRING not set — bridge disabled")
            return

        try:
            self._client = BlobServiceClient.from_connection_string(self.conn_str)
            self._ensure_containers()
            self._enabled = True
            logger.info("[AZURE] Bridge ready — containers: trading-features, colab-predictions")
        except Exception as e:
            logger.error(f"[AZURE] Connection failed: {e}")

    # ── Container setup ──────────────────────────────────────────────────

    def _ensure_containers(self):
        for name in [FEATURES_CONTAINER, PREDICTIONS_CONTAINER]:
            try:
                self._client.create_container(name)
                logger.info(f"[AZURE] Created container: {name}")
            except Exception:
                pass  # already exists — that's fine

    # ── Upload features (local → Azure) ──────────────────────────────────

    def upload_features(self, symbol: str, csv_path: str) -> bool:
        """
        Upload a single symbol's feature CSV to Azure Blob.
        Called by live_trading_system after reading each M15 candle.
        """
        if not self._enabled:
            return False
        try:
            blob_name = f"{symbol}_features.csv"
            blob = self._client.get_blob_client(container=FEATURES_CONTAINER, blob=blob_name)
            with open(csv_path, "rb") as f:
                blob.upload_blob(f, overwrite=True)
            logger.debug(f"[AZURE] Uploaded features: {blob_name}")
            return True
        except Exception as e:
            logger.debug(f"[AZURE] Upload failed {symbol}: {e}")
            return False

    def upload_features_from_string(self, symbol: str, csv_content: str) -> bool:
        """Upload feature CSV content directly as string (no temp file needed)."""
        if not self._enabled:
            return False
        try:
            blob_name = f"{symbol}_features.csv"
            blob = self._client.get_blob_client(container=FEATURES_CONTAINER, blob=blob_name)
            blob.upload_blob(csv_content.encode("utf-8"), overwrite=True)
            return True
        except Exception as e:
            logger.debug(f"[AZURE] Upload (string) failed {symbol}: {e}")
            return False

    # ── Download predictions (Azure → local) ─────────────────────────────

    def get_prediction(self, symbol: str, source: str) -> Optional[dict]:
        """
        Download one prediction blob for (symbol, source).
        Returns None if blob missing OR prediction is older than 30 minutes.

        Prediction JSON format written by Colab:
        {
          "symbol":     "EURUSD.sim",
          "source":     "lgbm",
          "action":     "BUY" | "SELL" | "HOLD",
          "confidence": 0.72,
          "timestamp":  "2026-06-09T10:30:00+00:00"
        }
        """
        if not self._enabled:
            return None
        try:
            blob_name = f"{symbol}_{source}_pred.json"
            blob = self._client.get_blob_client(container=PREDICTIONS_CONTAINER, blob=blob_name)
            raw  = blob.download_blob().readall()
            data = json.loads(raw)

            # Age check
            ts_str = data.get("timestamp", "")
            if ts_str:
                ts  = datetime.fromisoformat(ts_str)
                age = (datetime.now(timezone.utc) - ts).total_seconds()
                if age > PREDICTION_MAX_AGE_SEC:
                    logger.debug(f"[AZURE] Stale {symbol}/{source}: {age:.0f}s old — skipped")
                    return None

            return data

        except Exception:
            return None     # blob doesn't exist yet — normal at startup

    def get_all_predictions(self, symbols: list) -> Dict[str, Dict[str, dict]]:
        """
        Fetch all fresh Colab predictions for a list of symbols.

        Returns:
            {
              "EURUSD.sim": {
                "lgbm":     { action, confidence, timestamp },
                "catboost": { action, confidence, timestamp },
              },
              ...
            }
        Only symbols/sources with fresh predictions appear in the result.
        """
        results: Dict[str, Dict[str, dict]] = {}
        for sym in symbols:
            sym_preds = {}
            for src in ["lgbm", "catboost", "xgboost", "transformer"]:
                pred = self.get_prediction(sym, src)
                if pred and pred.get("action") in ("BUY", "SELL"):
                    sym_preds[src] = pred
            if sym_preds:
                results[sym] = sym_preds
        return results

    # ── Status ───────────────────────────────────────────────────────────

    @property
    def enabled(self) -> bool:
        return self._enabled

    def status(self) -> str:
        if not self._enabled:
            return "DISABLED"
        try:
            containers = [c["name"] for c in self._client.list_containers()]
            return f"CONNECTED — containers: {containers}"
        except Exception as e:
            return f"ERROR: {e}"
