"""
Health Watchdog
================
Run every 10 minutes via Task Scheduler (FTMO_Health_Watchdog).

Checks:
  1. Is `FTMO_Trading_System` task currently "Running"?
  2. If yes, has the active system_v5_*.log been silent > STALE_MINUTES?
     -> If stale, do a clean restart: schtasks /end then /run.
  3. MT5 connectivity (mt5.terminal_info()) — logged, not restart-triggering.
  4. Azure blob reachability (lightweight HEAD request) — logged, not
     restart-triggering.

All findings are appended to logs/watchdog.log.

Usage:
    python scripts/health_watchdog.py
"""

import logging
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

TASK_NAME = "FTMO_Trading_System"
STALE_MINUTES = 10

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "watchdog.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def get_active_log_path() -> Path:
    today = datetime.now().strftime("%Y%m%d")
    candidates = [
        LOG_DIR / f"system_v5_demo.log",
        LOG_DIR / f"system_v5_live.log",
        LOG_DIR / f"system_{today}.log",
    ]
    existing = [p for p in candidates if p.exists()]
    if not existing:
        return None
    return max(existing, key=lambda p: p.stat().st_mtime)


def get_task_status(task_name: str) -> str:
    """Returns 'Running', 'Ready', 'Disabled', or 'Unknown'."""
    try:
        result = subprocess.run(
            ["schtasks", "/query", "/tn", task_name, "/fo", "LIST"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return "Unknown"
        for line in result.stdout.splitlines():
            if line.strip().lower().startswith("status:"):
                return line.split(":", 1)[1].strip()
    except Exception as e:
        logger.error(f"schtasks query failed: {e}")
    return "Unknown"


def restart_task(task_name: str):
    logger.warning(f"[RESTART] Stopping task '{task_name}'...")
    subprocess.run(["schtasks", "/end", "/tn", task_name], capture_output=True, text=True)
    time.sleep(5)
    logger.warning(f"[RESTART] Starting task '{task_name}'...")
    result = subprocess.run(["schtasks", "/run", "/tn", task_name], capture_output=True, text=True)
    if result.returncode == 0:
        logger.info(f"[RESTART] '{task_name}' restarted successfully.")
    else:
        logger.error(f"[RESTART] Failed to restart '{task_name}': {result.stderr}")


def check_mt5():
    try:
        import MetaTrader5 as mt5
    except ImportError:
        logger.info("[MT5] MetaTrader5 module not installed — skipping check")
        return
    try:
        if not mt5.initialize():
            logger.warning(f"[MT5] initialize() failed: {mt5.last_error()}")
            return
        info = mt5.terminal_info()
        if info is None:
            logger.warning("[MT5] terminal_info() returned None — not connected")
        else:
            logger.info(f"[MT5] OK — connected={info.connected}, trade_allowed={info.trade_allowed}")
        mt5.shutdown()
    except Exception as e:
        logger.error(f"[MT5] check crashed: {e}")


def check_azure():
    try:
        import json
        cfg_path = BASE_DIR / "config" / "ftmo_config.json"
        with open(cfg_path) as f:
            config = json.load(f)
        azure_cfg = config.get("azure", {})
        account_url = azure_cfg.get("account_url") or azure_cfg.get("blob_account_url")
        if not account_url:
            logger.info("[AZURE] No account_url configured — skipping check")
            return
        import urllib.request
        req = urllib.request.Request(account_url, method="HEAD")
        with urllib.request.urlopen(req, timeout=10) as resp:
            logger.info(f"[AZURE] Reachable — HTTP {resp.status}")
    except Exception as e:
        logger.warning(f"[AZURE] unreachable or error: {e}")


def main():
    logger.info("=" * 60)
    logger.info(f"[WATCHDOG] Health check started {datetime.now(timezone.utc).isoformat()}")

    status = get_task_status(TASK_NAME)
    logger.info(f"[TASK] '{TASK_NAME}' status: {status}")

    if status.lower() == "running":
        log_path = get_active_log_path()
        if log_path is None:
            logger.warning("[LOG] No active system log found — cannot check staleness")
        else:
            age_seconds = time.time() - log_path.stat().st_mtime
            age_minutes = age_seconds / 60.0
            logger.info(f"[LOG] {log_path.name} last written {age_minutes:.1f} min ago")
            if age_minutes > STALE_MINUTES:
                logger.warning(
                    f"[STALE] {log_path.name} silent for {age_minutes:.1f} min "
                    f"(> {STALE_MINUTES} min) while task is Running — restarting"
                )
                restart_task(TASK_NAME)
            else:
                logger.info("[OK] Log is fresh — system appears healthy")
    else:
        logger.info(f"[SKIP] Task not 'Running' (status={status}) — no staleness check")

    check_mt5()
    check_azure()
    logger.info("[WATCHDOG] Health check complete")


if __name__ == "__main__":
    main()
