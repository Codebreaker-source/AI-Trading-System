# Source Bundle: docs/full_source_bundles/09_scripts.md


---

## `scripts/health_watchdog.py`

```py
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

```

---

## `scripts/setup_colab_task.py`

```py
"""
Windows Task Scheduler Setup — Colab Keepalive
================================================
Run this script ONCE to register the keepalive task in Windows Task Scheduler.
It will:
  1. Run every 5 minutes, all day (Colab free-tier sessions can disconnect
     after as little as 10-15 min idle, so this catches a disconnect well
     within that window)
  2. Restart if the keepalive script itself crashes

Usage:
  python scripts/setup_colab_task.py

Requires admin rights (run as administrator) or the scheduler will prompt for elevation.
"""

import subprocess
import sys
import os
from pathlib import Path

TASK_NAME   = "FTMO_Colab_Keepalive"
SCRIPT_PATH = str(Path(__file__).parent.parent / "colab" / "keepalive.py")
PYTHON_PATH = sys.executable   # uses the same Python that runs this script
LOG_DIR     = str(Path(__file__).parent.parent / "logs")

os.makedirs(LOG_DIR, exist_ok=True)

# Repetition interval — re-run continuously throughout the day
REPEAT_INTERVAL = "PT5M"

def create_task():
    print(f"Creating Task Scheduler task: {TASK_NAME}")
    print(f"Script:   {SCRIPT_PATH}")
    print(f"Python:   {PYTHON_PATH}")
    print(f"Interval: every 5 minutes")
    print()

    # Delete existing task if present
    subprocess.run(
        ["schtasks", "/delete", "/tn", TASK_NAME, "/f"],
        capture_output=True
    )

    task_xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>FTMO AI Trading — Colab keepalive. Checks and restarts Google Colab inference session every 5 minutes.</Description>
    <Author>FTMO_System</Author>
  </RegistrationInfo>
  <Triggers>
    <TimeTrigger>
      <StartBoundary>2026-01-01T00:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <Repetition>
        <Interval>{REPEAT_INTERVAL}</Interval>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
    </TimeTrigger>
  </Triggers>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT10M</ExecutionTimeLimit>
    <Priority>7</Priority>
    <RestartOnFailure>
      <Interval>PT5M</Interval>
      <Count>3</Count>
    </RestartOnFailure>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{PYTHON_PATH}</Command>
      <Arguments>"{SCRIPT_PATH}"</Arguments>
      <WorkingDirectory>{str(Path(SCRIPT_PATH).parent)}</WorkingDirectory>
    </Exec>
  </Actions>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
</Task>"""

    xml_path = str(Path(__file__).parent / "_colab_task_temp.xml")
    with open(xml_path, "w", encoding="utf-16") as f:
        f.write(task_xml)

    result = subprocess.run(
        ["schtasks", "/create", "/tn", TASK_NAME, "/xml", xml_path, "/f"],
        capture_output=True, text=True
    )

    os.remove(xml_path)

    if result.returncode == 0:
        print(f"[OK] Task '{TASK_NAME}' created successfully.")
        print()
        print("Next steps:")
        print("  1. Confirm COLAB_NOTEBOOK_URL in colab/keepalive.py points to your notebook")
        print("  2. First run requires a one-time manual Google login:")
        print("       python colab/keepalive.py")
        print("     An Edge window will open in a dedicated automation profile —")
        print("     log into the Google account that owns the Colab notebook, then close it.")
    else:
        print(f"[FAIL] Task creation failed:\n{result.stderr}")
        print("Try running this script as Administrator.")
        sys.exit(1)


def verify_task():
    result = subprocess.run(
        ["schtasks", "/query", "/tn", TASK_NAME, "/fo", "LIST"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print("\nTask details:")
        print(result.stdout)
    else:
        print("Could not query task.")


if __name__ == "__main__":
    create_task()
    verify_task()

```

---

## `scripts/setup_retrainer_task.py`

```py
"""
Windows Task Scheduler Setup — Daily Model Retrainer
=====================================================
Run this script ONCE (as Administrator) to register the daily retraining task.

What it schedules
-----------------
  Script  : training/daily_retrainer.py
  Trigger : Daily at 00:00 UTC  (02:00 local if UTC+2, adjust RUN_TIME_UTC below)
  Action  : python daily_retrainer.py  (reads ftmo_config.json automatically)
  After   : Retrained models are committed and pushed to GitHub automatically,
            so Colab picks them up on the next session start.

Usage
-----
  python scripts/setup_retrainer_task.py          # register / update task
  python scripts/setup_retrainer_task.py --delete  # remove task
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

TASK_NAME   = "FTMO_Daily_Retrainer"
SCRIPT_PATH = str(Path(__file__).parent.parent / "training" / "daily_retrainer.py")
PYTHON_PATH = sys.executable
LOG_DIR     = str(Path(__file__).parent.parent / "logs")

# ── Schedule: every Sunday at 08:00 local time ───────────────────────────
RUN_TIME_LOCAL = "08:00"
RUN_DAY        = "Sunday"


def create_task():
    print(f"Creating Task Scheduler task : {TASK_NAME}")
    print(f"Script                       : {SCRIPT_PATH}")
    print(f"Python                       : {PYTHON_PATH}")
    print(f"Schedule                     : Every {RUN_DAY} at {RUN_TIME_LOCAL}")
    print()

    os.makedirs(LOG_DIR, exist_ok=True)

    # Delete existing task if present (ignore errors)
    subprocess.run(["schtasks", "/delete", "/tn", TASK_NAME, "/f"],
                   capture_output=True)

    task_xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>FTMO AI Trading — weekly model retraining (XGBoost + LightGBM + CatBoost + Transformer). Runs every Sunday at 08:00. Pushes updated models to GitHub on completion.</Description>
    <Author>FTMO_System</Author>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-01-04T{RUN_TIME_LOCAL}:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByWeek>
        <WeeksInterval>1</WeeksInterval>
        <DaysOfWeek>
          <{RUN_DAY}/>
        </DaysOfWeek>
      </ScheduleByWeek>
    </CalendarTrigger>
  </Triggers>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT2H</ExecutionTimeLimit>
    <Priority>7</Priority>
    <RestartOnFailure>
      <Interval>PT10M</Interval>
      <Count>2</Count>
    </RestartOnFailure>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
    </IdleSettings>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{PYTHON_PATH}</Command>
      <Arguments>"{SCRIPT_PATH}"</Arguments>
      <WorkingDirectory>{str(Path(SCRIPT_PATH).parent)}</WorkingDirectory>
    </Exec>
  </Actions>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
</Task>"""

    xml_path = str(Path(__file__).parent / "_retrainer_task_temp.xml")
    with open(xml_path, "w", encoding="utf-16") as f:
        f.write(task_xml)

    result = subprocess.run(
        ["schtasks", "/create", "/tn", TASK_NAME, "/xml", xml_path, "/f"],
        capture_output=True, text=True
    )
    os.remove(xml_path)

    if result.returncode == 0:
        print(f"[OK] Task '{TASK_NAME}' created successfully.")
        print()
        print(f"The retrainer will run every {RUN_DAY} at {RUN_TIME_LOCAL}.")
        print("It trains all 4 model types and auto-pushes updated models to GitHub.")
        print()
        print("To run immediately for testing:")
        print(f"  schtasks /run /tn {TASK_NAME}")
        print()
        print("To check last run status:")
        print(f"  schtasks /query /tn {TASK_NAME} /fo LIST")
        print()
        print(f"Log output: {LOG_DIR}\\retrainer.log  (created on first run)")
    else:
        print(f"✗ Task creation failed:\n{result.stderr}")
        print("Try running this script as Administrator.")
        sys.exit(1)


def delete_task():
    result = subprocess.run(
        ["schtasks", "/delete", "/tn", TASK_NAME, "/f"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"[OK] Task '{TASK_NAME}' deleted.")
    else:
        print(f"Task not found or could not be deleted:\n{result.stderr}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage FTMO daily retrainer task")
    parser.add_argument("--delete", action="store_true", help="Remove the scheduled task")
    args = parser.parse_args()

    if args.delete:
        delete_task()
    else:
        create_task()

```

---

## `scripts/setup_trading_task.py`

```py
"""
Windows Task Scheduler Setup — Live Trading System
===================================================
Run this script ONCE (as Administrator) to register the trading system task.

What it schedules
-----------------
  Script  : run_system.py
  Trigger : Daily at 07:30 (before London open at 08:00)
  Restart : Up to 3 times if it crashes (5 min between attempts)

Usage
-----
  python scripts/setup_trading_task.py          # register / update task
  python scripts/setup_trading_task.py --delete  # remove task
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

TASK_NAME   = "FTMO_Trading_System"
SCRIPT_PATH = str(Path(__file__).parent.parent / "run_system.py")
PYTHON_PATH = sys.executable
WORK_DIR    = str(Path(__file__).parent.parent)
LOG_DIR     = str(Path(__file__).parent.parent / "logs")
RUN_TIME    = "07:30"


def create_task():
    print(f"Creating Task Scheduler task : {TASK_NAME}")
    print(f"Script                       : {SCRIPT_PATH}")
    print(f"Python                       : {PYTHON_PATH}")
    print(f"Schedule                     : Daily at {RUN_TIME}")
    print()

    os.makedirs(LOG_DIR, exist_ok=True)

    subprocess.run(["schtasks", "/delete", "/tn", TASK_NAME, "/f"],
                   capture_output=True)

    task_xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>FTMO AI Trading System — starts live_trading_system.py daily before London open.</Description>
    <Author>FTMO_System</Author>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-01-01T{RUN_TIME}:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT20H</ExecutionTimeLimit>
    <Priority>5</Priority>
    <RestartOnFailure>
      <Interval>PT5M</Interval>
      <Count>3</Count>
    </RestartOnFailure>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
    </IdleSettings>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{PYTHON_PATH}</Command>
      <Arguments>"{SCRIPT_PATH}"</Arguments>
      <WorkingDirectory>{WORK_DIR}</WorkingDirectory>
    </Exec>
  </Actions>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
</Task>"""

    xml_path = str(Path(__file__).parent / "_trading_task_temp.xml")
    with open(xml_path, "w", encoding="utf-16") as f:
        f.write(task_xml)

    result = subprocess.run(
        ["schtasks", "/create", "/tn", TASK_NAME, "/xml", xml_path, "/f"],
        capture_output=True, text=True
    )
    os.remove(xml_path)

    if result.returncode == 0:
        print(f"[OK] Task '{TASK_NAME}' created successfully.")
        print()
        print(f"Trading system will start automatically every day at {RUN_TIME}.")
        print("Restarts up to 3 times if it crashes (5 min between attempts).")
        print()
        print("To start immediately:")
        print(f"  schtasks /run /tn {TASK_NAME}")
        print()
        print("To check status:")
        print(f"  schtasks /query /tn {TASK_NAME} /fo LIST")
    else:
        print(f"[FAIL] Task creation failed:\n{result.stderr}")
        print("Try running this script as Administrator.")
        sys.exit(1)


def delete_task():
    result = subprocess.run(
        ["schtasks", "/delete", "/tn", TASK_NAME, "/f"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"[OK] Task '{TASK_NAME}' deleted.")
    else:
        print(f"Task not found or could not be deleted:\n{result.stderr}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--delete", action="store_true", help="Remove the scheduled task")
    args = parser.parse_args()

    if args.delete:
        delete_task()
    else:
        create_task()

```

---

## `scripts/setup_watchdog_task.py`

```py
"""
Windows Task Scheduler Setup — Health Watchdog
================================================
Run this script ONCE (as Administrator) to register the health watchdog task.

What it schedules
------------------
  Script  : scripts/health_watchdog.py
  Trigger : Every 10 minutes, indefinitely
  Action  : checks FTMO_Trading_System for a stale log (no writes for
            > 10 min while the task shows "Running") and does a clean
            schtasks /end + /run restart if so. Also logs MT5/Azure
            connectivity. All output -> logs/watchdog.log.

Usage
-----
  python scripts/setup_watchdog_task.py          # register / update task
  python scripts/setup_watchdog_task.py --delete  # remove task
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

TASK_NAME   = "FTMO_Health_Watchdog"
SCRIPT_PATH = str(Path(__file__).parent.parent / "scripts" / "health_watchdog.py")
PYTHON_PATH = sys.executable
LOG_DIR     = str(Path(__file__).parent.parent / "logs")


def create_task():
    print(f"Creating Task Scheduler task : {TASK_NAME}")
    print(f"Script                       : {SCRIPT_PATH}")
    print(f"Python                       : {PYTHON_PATH}")
    print(f"Schedule                     : Every 10 minutes")
    print()

    os.makedirs(LOG_DIR, exist_ok=True)

    # Delete existing task if present (ignore errors)
    subprocess.run(["schtasks", "/delete", "/tn", TASK_NAME, "/f"],
                   capture_output=True)

    task_xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>FTMO AI Trading — health watchdog. Every 10 minutes, checks if the trading system log has gone silent while the task is "Running" and restarts it if so. Also logs MT5/Azure connectivity.</Description>
    <Author>FTMO_System</Author>
  </RegistrationInfo>
  <Triggers>
    <TimeTrigger>
      <StartBoundary>2026-01-01T00:00:00</StartBoundary>
      <Enabled>true</Enabled>
      <Repetition>
        <Interval>PT10M</Interval>
        <StopAtDurationEnd>false</StopAtDurationEnd>
      </Repetition>
    </TimeTrigger>
  </Triggers>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT5M</ExecutionTimeLimit>
    <Priority>7</Priority>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
    </IdleSettings>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{PYTHON_PATH}</Command>
      <Arguments>"{SCRIPT_PATH}"</Arguments>
      <WorkingDirectory>{str(Path(SCRIPT_PATH).parent.parent)}</WorkingDirectory>
    </Exec>
  </Actions>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
</Task>"""

    xml_path = str(Path(__file__).parent / "_watchdog_task_temp.xml")
    with open(xml_path, "w", encoding="utf-16") as f:
        f.write(task_xml)

    result = subprocess.run(
        ["schtasks", "/create", "/tn", TASK_NAME, "/xml", xml_path, "/f"],
        capture_output=True, text=True
    )
    os.remove(xml_path)

    if result.returncode == 0:
        print(f"[OK] Task '{TASK_NAME}' created successfully.")
        print()
        print("The watchdog will run every 10 minutes.")
        print()
        print("To run immediately for testing:")
        print(f"  schtasks /run /tn {TASK_NAME}")
        print()
        print("To check last run status:")
        print(f"  schtasks /query /tn {TASK_NAME} /fo LIST")
        print()
        print(f"Log output: {LOG_DIR}\\watchdog.log")
    else:
        print(f"Task creation failed:\n{result.stderr}")
        print("Try running this script as Administrator.")
        sys.exit(1)


def delete_task():
    result = subprocess.run(
        ["schtasks", "/delete", "/tn", TASK_NAME, "/f"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"[OK] Task '{TASK_NAME}' deleted.")
    else:
        print(f"Task not found or could not be deleted:\n{result.stderr}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage FTMO health watchdog task")
    parser.add_argument("--delete", action="store_true", help="Remove the scheduled task")
    args = parser.parse_args()

    if args.delete:
        delete_task()
    else:
        create_task()

```
