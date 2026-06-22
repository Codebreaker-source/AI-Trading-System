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
